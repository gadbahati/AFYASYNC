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
PROXY = "https://r.jina.ai/http://api.kmhfr.health.go.ke/api/public/facilities/"
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/kmhfr_facilities.json"))
PAGE_SIZE = 30
MAX_PAGES = 1000
MAX_RETRIES = 3
DIRECT_TIMEOUT = 20
PROXY_TIMEOUT = 45
WORKERS = 6


def decode_payload(body: bytes, source: str) -> dict | list:
    text = body.decode("utf-8-sig").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:] if lines and lines[0].startswith("```") else lines
        lines = lines[:-1] if lines and lines[-1].strip() == "```" else lines
        text = "\n".join(lines).strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"KMHFR_NON_JSON_RESPONSE source={source} preview={text[:160]!r}") from exc
    if not isinstance(payload, (dict, list)):
        raise RuntimeError(f"KMHFR_RESPONSE_INVALID source={source}")
    return payload


def request_json(url: str, timeout: int, source: str) -> dict | list:
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "AfyaSync-KMHFR/8.0", "Connection": "close"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return decode_payload(response.read(), source)


def fetch_page(page: int) -> dict | list:
    # Do not send format=json: the current public KMHFR API rejects that
    # parameter with HTTP 422 on some transports. page/page_size are sufficient.
    query = urllib.parse.urlencode({"page_size": PAGE_SIZE, "page": page})
    direct_url = f"{API}?{query}"
    proxy_url = f"{PROXY}?{query}"
    last: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return request_json(direct_url, DIRECT_TIMEOUT, "official")
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, RuntimeError) as exc:
            last = exc
            if attempt < MAX_RETRIES:
                time.sleep(0.5 * attempt + random.random() * 0.5)
    print(f"KMHFR page={page}: direct access unavailable; switching to official API transport fallback", flush=True)
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return request_json(proxy_url, PROXY_TIMEOUT, "official-via-transport-fallback")
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


def items_from(payload: dict | list) -> list:
    items = payload.get("results", []) if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        raise RuntimeError("KMHFR_PAGE_INVALID_RESULTS")
    return items


def main() -> None:
    print(f"KMHFR: starting official national import source={API}", flush=True)
    first = fetch_page(1)
    first_items = items_from(first)
    if not first_items:
        raise RuntimeError("KMHFR_FIRST_PAGE_EMPTY_OR_INVALID")
    count = int(first.get("count") or 0) if isinstance(first, dict) else 0
    total_pages = first.get("total_pages") if isinstance(first, dict) else None
    if total_pages is None and count:
        total_pages = (count + PAGE_SIZE - 1) // PAGE_SIZE
    total_pages = int(total_pages or 0)
    if total_pages <= 0 or total_pages > MAX_PAGES:
        raise RuntimeError(f"KMHFR_INVALID_TOTAL_PAGES:{total_pages}")
    print(f"KMHFR: API count={count} pages={total_pages} page_size={PAGE_SIZE} workers={WORKERS}", flush=True)
    records: dict[str, dict] = {}
    def add(items: list) -> None:
        for raw in items:
            if not isinstance(raw, dict):
                continue
            row = compact(raw)
            name = str(row.get("name") or "").strip()
            code = str(row.get("code") or "").strip()
            identity = code or str(row.get("id") or "").strip() or "|".join(str(row.get(k) or "").strip().lower() for k in ("name", "county", "sub_county"))
            if name and identity:
                records[identity.lower()] = row
    add(first_items)
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(fetch_page, page): page for page in range(2, total_pages + 1)}
        completed = 1
        for future in concurrent.futures.as_completed(futures):
            page = futures[future]
            add(items_from(future.result()))
            completed += 1
            if completed % 30 == 0 or completed == total_pages:
                print(f"KMHFR: progress page={completed}/{total_pages} records={len(records)}", flush=True)
    final = list(records.values())
    expected_min = max(10000, int(count * 0.90)) if count else 10000
    if len(final) < expected_min:
        raise RuntimeError(f"KMHFR_INCOMPLETE:api_count={count} imported={len(final)} expected_min={expected_min}")
    codes = [str(row.get("code") or "").strip() for row in final if str(row.get("code") or "").strip()]
    if len(codes) != len(set(codes)):
        raise RuntimeError("KMHFR_DUPLICATE_CODES")
    if not all(str(row.get("name") or "").strip() for row in final):
        raise RuntimeError("KMHFR_UNNAMED_FACILITY")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="kmhfr-", suffix=".json", dir=os.path.dirname(OUT))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"source": API, "api_count": count, "api_pages": total_pages, "records": final}, f, ensure_ascii=False, separators=(",", ":"))
            f.write("\n")
        os.replace(tmp, OUT)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    print(f"KMHFR: COMPLETE api_count={count} imported={len(final)} pages={total_pages}", flush=True)

if __name__ == "__main__":
    main()

# National registry deployment path: keep this importer exercised on every backend source change.