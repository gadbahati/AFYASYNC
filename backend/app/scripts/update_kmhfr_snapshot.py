from __future__ import annotations

import concurrent.futures
import json
import os
import random
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.kmhfr.health.go.ke/api/public/facilities/"
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/kmhfr_facilities.json"))
PAGE_SIZE = 100
MAX_PAGES = 1000
MAX_RETRIES = 8
WORKERS = 8


def fetch(url: str) -> dict | list:
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "AfyaSync-KMHFR-Snapshot/3.0",
                    "Connection": "close",
                },
            )
            with urllib.request.urlopen(req, timeout=60) as response:
                if response.status != 200:
                    raise RuntimeError(f"KMHFR_HTTP_STATUS:{response.status}")
                return json.load(response)
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, RuntimeError) as exc:
            last_error = exc
            if attempt == MAX_RETRIES:
                break
            delay = min(30, 2 ** (attempt - 1)) + random.random()
            print(f"KMHFR request retry attempt={attempt} delay={delay:.1f}s", flush=True)
            time.sleep(delay)
    raise RuntimeError(f"KMHFR_FETCH_FAILED:{last_error}") from last_error


def page_url(page: int) -> str:
    return API + "?" + urllib.parse.urlencode({"page_size": PAGE_SIZE, "page": page})


def compact(item: dict) -> dict:
    def val(*keys: str):
        for key in keys:
            value = item.get(key)
            if isinstance(value, dict):
                value = value.get("name") or value.get("label") or value.get("value") or value.get("code")
            if value is not None and str(value).strip():
                return value
        return None

    return {
        "id": val("id", "uuid", "facility_id"),
        "code": val("code", "mfl_code", "facility_code", "facility_code_number"),
        "name": val("name", "facility_official_name", "official_name"),
        "facility_type": val("facility_type_name", "facility_type", "type"),
        "operation_status": val("operation_status_name", "operation_status", "status"),
        "county": val("county_name", "county"),
        "sub_county": val("sub_county_name", "sub_county", "subcounty"),
        "constituency": val("constituency_name", "constituency"),
        "ward": val("ward_name", "ward"),
        "keph_level": val("keph_level_name", "keph_level", "level"),
        "owner": val("owner_name", "owner"),
        "latitude": val("latitude", "lat"),
        "longitude": val("longitude", "lng", "lon"),
    }


def extract(payload: dict | list) -> tuple[list[dict], int | None]:
    results = payload.get("results", []) if isinstance(payload, dict) else payload
    if not isinstance(results, list):
        raise RuntimeError("KMHFR_RESPONSE_INVALID_RESULTS")

    total_pages = None
    if isinstance(payload, dict):
        for key in ("total_pages", "num_pages", "pages"):
            if payload.get(key) is not None:
                try:
                    total_pages = int(payload[key])
                    break
                except (TypeError, ValueError):
                    pass
        if total_pages is None and payload.get("count") is not None:
            try:
                total_pages = (int(payload["count"]) + PAGE_SIZE - 1) // PAGE_SIZE
            except (TypeError, ValueError):
                pass

    return [compact(item) for item in results if isinstance(item, dict)], total_pages


def fetch_page(page: int) -> tuple[int, list[dict], int | None]:
    payload = fetch(page_url(page))
    records, total_pages = extract(payload)
    return page, records, total_pages


def main() -> None:
    print(f"Starting official KMHFR snapshot source={API}", flush=True)
    first_page, first_records, total_pages = fetch_page(1)
    if first_page != 1:
        raise RuntimeError("KMHFR_FIRST_PAGE_INVALID")

    if total_pages is None:
        # The public API normally exposes total_pages/count. Fall back safely by
        # following pages sequentially only when the API omits both.
        pages_to_fetch = None
    else:
        pages_to_fetch = total_pages
        if pages_to_fetch > MAX_PAGES:
            raise RuntimeError(f"KMHFR_SNAPSHOT_PAGE_LIMIT:{pages_to_fetch}")

    records_by_key: dict[str, dict] = {}

    def add(records: list[dict]) -> None:
        for record in records:
            if not record.get("name"):
                continue
            key = str(record.get("code") or record.get("id") or "|".join(str(record.get(k) or "") for k in ("name", "county", "sub_county"))).strip().lower()
            records_by_key[key] = record

    add(first_records)
    print(f"KMHFR first page records={len(first_records)} total_pages={total_pages}", flush=True)

    if pages_to_fetch is not None:
        remaining = range(2, pages_to_fetch + 1)
        completed = 1
        with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
            futures = {pool.submit(fetch_page, page): page for page in remaining}
            for future in concurrent.futures.as_completed(futures):
                page, records, discovered_pages = future.result()
                add(records)
                completed += 1
                if completed % 10 == 0 or completed == pages_to_fetch:
                    print(f"KMHFR snapshot progress pages={completed}/{pages_to_fetch} records={len(records_by_key)}", flush=True)
    else:
        page = 2
        while page <= MAX_PAGES:
            _, records, discovered_pages = fetch_page(page)
            add(records)
            print(f"KMHFR snapshot progress pages={page} records={len(records_by_key)}", flush=True)
            if not records or len(records) < PAGE_SIZE:
                break
            page += 1

    records = list(records_by_key.values())
    if len(records) < 10000:
        raise RuntimeError(f"KMHFR_SNAPSHOT_UNEXPECTEDLY_SMALL:{len(records)}")

    path = OUT
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="kmhfr-", suffix=".json", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump({"source": API, "records": records}, handle, separators=(",", ":"), ensure_ascii=False)
            handle.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

    print(f"KMHFR snapshot complete pages={pages_to_fetch or 'discovered'} records={len(records)} path={path}", flush=True)


if __name__ == "__main__":
    main()
