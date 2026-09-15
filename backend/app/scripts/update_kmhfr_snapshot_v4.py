from __future__ import annotations

import json
import os
import random
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

API = "https://api.kmhfr.health.go.ke/api/public/facilities/"
PROXY = "https://r.jina.ai/http://api.kmhfr.health.go.ke/api/public/facilities/"
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/kmhfr_facilities.json"))
PAGE_SIZE = 100
MAX_PAGES = 1000
MAX_RETRIES = 3
DIRECT_TIMEOUT = 12
PROXY_TIMEOUT = 30
WORKERS = 4


def _decode_payload(body: bytes, source: str) -> dict | list:
    text = body.decode("utf-8-sig").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"KMHFR_NON_JSON_RESPONSE source={source} preview={text[:160]!r}") from exc
    if not isinstance(value, (dict, list)):
        raise RuntimeError(f"KMHFR_INVALID_JSON_TYPE source={source}")
    return value


def _request(url: str, timeout: int, source: str) -> dict | list:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "AfyaSync-KMHFR/5.0",
            "Connection": "close",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"KMHFR_HTTP_STATUS:{response.status} source={source}")
        return _decode_payload(response.read(), source)


def fetch_page(page: int) -> dict | list:
    params = urllib.parse.urlencode({"format": "json", "page_size": PAGE_SIZE, "page": page})
    direct_url = f"{API}?{params}"
    proxy_url = f"{PROXY}?{params}"
    last: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return _request(direct_url, DIRECT_TIMEOUT, "official")
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, RuntimeError) as exc:
            last = exc
            if attempt < MAX_RETRIES:
                time.sleep(0.75 * attempt + random.random() * 0.5)

    print(f"KMHFR page={page}: direct endpoint unreachable; using official-API transport fallback", flush=True)
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return _request(proxy_url, PROXY_TIMEOUT, "official-via-transport-fallback")
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, RuntimeError) as exc:
            last = exc
            if attempt < MAX_RETRIES:
                delay = min(8, 1.5 * attempt) + random.random()
                print(f"KMHFR page={page} fallback retry={attempt}/{MAX_RETRIES} delay={delay:.1f}s", flush=True)
                time.sleep(delay)

    raise RuntimeError(f"KMHFR_FETCH_FAILED page={page}: {last}") from last


def value(item: dict, *keys: str):
    for key in keys:
        v = item.get(key)
        if isinstance(v, dict):
            v = v.get("name") or v.get("label") or v.get("value") or v.get("code")
        if v is not None and str(v).strip():
            return v
    return None


def compact(item: dict) -> dict:
    return {
        "id": value(item, "id", "uuid", "facility_id"),
        "code": value(item, "code", "mfl_code", "facility_code", "facility_code_number"),
        "name": value(item, "name", "facility_official_name", "official_name"),
        "facility_type": value(item, "facility_type_name", "facility_type", "type"),
        "operation_status": value(item, "operation_status_name", "operation_status", "status"),
        "county": value(item, "county_name", "county"),
        "sub_county": value(item, "sub_county_name", "sub_county", "subcounty"),
        "constituency": value(item, "constituency_name", "constituency"),
        "ward": value(item, "ward_name", "ward"),
        "keph_level": value(item, "keph_level_name", "keph_level", "level"),
        "owner": value(item, "owner_name", "owner"),
        "latitude": value(item, "latitude", "lat"),
        "longitude": value(item, "longitude", "long", "lng", "lon"),
        "registration_number": value(item, "registration_number"),
    }


def main() -> None:
    print(f"KMHFR v5: starting verified national import source={API}", flush=True)
    first = fetch_page(1)
    results = first.get("results", []) if isinstance(first, dict) else first
    if not isinstance(results, list) or not results:
        raise RuntimeError("KMHFR_FIRST_PAGE_EMPTY_OR_INVALID")

    count = int(first.get("count") or 0) if isinstance(first, dict) else 0
    total_pages = first.get("total_pages") if isinstance(first, dict) else None
    if total_pages is None and count:
        total_pages = (count + PAGE_SIZE - 1) // PAGE_SIZE
    total_pages = int(total_pages or 0)
    if total_pages <= 0 or total_pages > MAX_PAGES:
        raise RuntimeError(f"KMHFR_INVALID_TOTAL_PAGES:{total_pages}")

    print(f"KMHFR v5: official API reports count={count} pages={total_pages}", flush=True)
    records: dict[str, dict] = {}

    def add(items: list):
        for raw in items:
            if not isinstance(raw, dict):
                continue
            row = compact(raw)
            name = str(row.get("name") or "").strip()
            code = str(row.get("code") or "").strip()
            identity = code or str(row.get("id") or "").strip() or "|".join(
                str(row.get(k) or "").strip().lower() for k in ("name", "county", "sub_county")
            )
            if name and identity:
                records[identity.lower()] = row

    add(results)
    pages = list(range(2, total_pages + 1))
    completed = 1
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(fetch_page, page): page for page in pages}
        for future in as_completed(futures):
            page = futures[future]
            payload = future.result()
            items = payload.get("results", []) if isinstance(payload, dict) else payload
            if not isinstance(items, list):
                raise RuntimeError(f"KMHFR_PAGE_INVALID:{page}")
            add(items)
            completed += 1
            if completed % 10 == 0 or completed == total_pages:
                print(f"KMHFR v5: progress pages={completed}/{total_pages} records={len(records)}", flush=True)

    final = list(records.values())
    if count and len(final) < max(10000, int(count * 0.90)):
        raise RuntimeError(f"KMHFR_INCOMPLETE:api_count={count} imported={len(final)}")
    if len(final) < 10000:
        raise RuntimeError(f"KMHFR_TOO_SMALL:{len(final)}")

    coded = [str(row.get("code") or "").strip() for row in final]
    coded = [code for code in coded if code]
    if len(coded) != len(set(coded)):
        raise RuntimeError("KMHFR_DUPLICATE_FACILITY_CODES")
    if not all(str(row.get("name") or "").strip() for row in final):
        raise RuntimeError("KMHFR_UNNAMED_FACILITY")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="kmhfr-", suffix=".json", dir=os.path.dirname(OUT))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"source": API, "transport": "direct-or-official-api-proxy-fallback", "api_count": count, "api_pages": total_pages, "records": final}, f, ensure_ascii=False, separators=(",", ":"))
            f.write("\n")
        os.replace(tmp, OUT)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    print(f"KMHFR v5: COMPLETE api_count={count} imported={len(final)} pages={total_pages}", flush=True)


if __name__ == "__main__":
    main()
