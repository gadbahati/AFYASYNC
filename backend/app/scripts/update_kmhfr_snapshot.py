from __future__ import annotations

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


def fetch(url: str) -> dict | list:
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "AfyaSync-KMHFR-Snapshot/2.0",
                    "Connection": "close",
                },
            )
            with urllib.request.urlopen(req, timeout=180) as response:
                if response.status != 200:
                    raise RuntimeError(f"KMHFR_HTTP_STATUS:{response.status}")
                return json.load(response)
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, RuntimeError) as exc:
            last_error = exc
            if attempt == MAX_RETRIES:
                break
            delay = min(60, 2 ** (attempt - 1)) + random.random()
            print(f"KMHFR request retry attempt={attempt} delay={delay:.1f}s url={url}", flush=True)
            time.sleep(delay)
    raise RuntimeError(f"KMHFR_FETCH_FAILED:{last_error}") from last_error


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


def main() -> None:
    url = API + "?" + urllib.parse.urlencode({"page_size": PAGE_SIZE, "page": 1})
    records_by_key: dict[str, dict] = {}
    pages = 0

    while url and pages < MAX_PAGES:
        payload = fetch(url)
        results = payload.get("results", []) if isinstance(payload, dict) else payload
        if not isinstance(results, list):
            raise RuntimeError("KMHFR_RESPONSE_INVALID_RESULTS")

        for item in results:
            if not isinstance(item, dict):
                continue
            record = compact(item)
            if not record.get("name"):
                continue
            key = str(record.get("code") or record.get("id") or "|".join(str(record.get(k) or "") for k in ("name", "county", "sub_county"))).strip().lower()
            records_by_key[key] = record

        pages += 1
        next_url = payload.get("next") if isinstance(payload, dict) else None
        if next_url:
            url = urllib.parse.urljoin(url, str(next_url))
        elif isinstance(payload, dict) and payload.get("total_pages"):
            total_pages = int(payload["total_pages"])
            url = API + "?" + urllib.parse.urlencode({"page_size": PAGE_SIZE, "page": pages + 1}) if pages < total_pages else ""
        elif results:
            url = API + "?" + urllib.parse.urlencode({"page_size": PAGE_SIZE, "page": pages + 1}) if len(results) >= PAGE_SIZE else ""
        else:
            url = ""

        if pages % 10 == 0:
            print(f"KMHFR snapshot progress pages={pages} records={len(records_by_key)}", flush=True)

    records = list(records_by_key.values())
    if pages >= MAX_PAGES:
        raise RuntimeError(f"KMHFR_SNAPSHOT_PAGE_LIMIT:{pages}")
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

    print(f"KMHFR snapshot complete pages={pages} records={len(records)} path={path}", flush=True)


if __name__ == "__main__":
    main()
