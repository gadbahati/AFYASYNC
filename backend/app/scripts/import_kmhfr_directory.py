from __future__ import annotations

import concurrent.futures
import json
import os
import tempfile
import urllib.error
import urllib.parse
import urllib.request

API_ENDPOINTS = (
    "https://api.kmhfr.health.go.ke/api/public/facilities/",
    "https://api.kmhfr.health.go.ke/api/facilities/facilities/",
)
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/kmhfr_facilities.json"))
PAGE_SIZE = 100
WORKERS = 12
TIMEOUT = 30
MIN_RECORDS = 10000
HEADERS = {
    "User-Agent": "AfyaSync/1.0 national-registry-import",
    "Accept": "application/json",
    "Connection": "close",
}


def fetch_json(url: str) -> object:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def request_page(endpoint: str, page: int) -> tuple[list[dict], int]:
    query = urllib.parse.urlencode({"page": page, "page_size": PAGE_SIZE})
    payload = fetch_json(f"{endpoint}?{query}")
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)], 0
    if not isinstance(payload, dict):
        return [], 0

    data = payload.get("data")
    if isinstance(data, dict):
        results = data.get("results") or data.get("items") or data.get("data") or []
        count = data.get("count") or data.get("total") or data.get("total_count") or 0
    else:
        results = payload.get("results") or payload.get("items") or data or []
        count = payload.get("count") or payload.get("total") or payload.get("total_count") or 0

    if not isinstance(results, list):
        results = []
    try:
        count = int(count or 0)
    except (TypeError, ValueError):
        count = 0
    return [x for x in results if isinstance(x, dict)], count


def normalize(item: dict) -> dict | None:
    def value(*keys: str):
        for key in keys:
            v = item.get(key)
            if isinstance(v, dict):
                v = v.get("name") or v.get("label") or v.get("value") or v.get("code") or v.get("id")
            if v is not None and str(v).strip():
                return v
        return None

    name = value("name", "facility_name", "facility_official_name", "official_name", "facility_unique_name")
    code = value("code", "mfl_code", "facility_code", "facility_code_number", "mfl_number")
    if not name or not code:
        return None

    return {
        "id": value("id", "uuid", "facility_uuid") or str(code),
        "code": str(code).strip(),
        "name": str(name).strip(),
        "facility_type": value("facility_type_name", "facility_type", "type"),
        "operation_status": value("operation_status", "operation_status_name", "status"),
        "county": value("county_name", "county"),
        "sub_county": value("sub_county_name", "sub_county", "subcounty"),
        "constituency": value("constituency_name", "constituency"),
        "ward": value("ward_name", "ward"),
        "keph_level": value("keph_level", "keph_level_name", "level"),
        "owner": value("owner_name", "owner", "ownership_name", "ownership"),
        "latitude": value("latitude", "lat"),
        "longitude": value("longitude", "lng", "lon"),
        "registration_number": value("registration_number", "registration_no", "license_number"),
        "address": value("address", "physical_address", "location"),
        "phone": value("phone", "telephone", "phone_number", "mobile"),
        "email": value("email", "email_address"),
        "services": item.get("services") if isinstance(item.get("services"), (list, dict)) else None,
        "raw_record": item,
    }


def fetch_first_page() -> tuple[str, list[dict], int]:
    errors: list[str] = []
    for endpoint in API_ENDPOINTS:
        try:
            rows, count = request_page(endpoint, 1)
            normalized = [r for x in rows if (r := normalize(x)) is not None]
            if normalized and count:
                return endpoint, normalized, count
            errors.append(f"{endpoint}: records={len(normalized)} count={count}")
        except Exception as exc:
            errors.append(f"{endpoint}: {type(exc).__name__}: {exc}")
    raise RuntimeError("KMHFR_API_UNAVAILABLE " + " | ".join(errors))


def write(records: list[dict], count: int, pages: int, endpoint: str) -> None:
    unique: dict[str, dict] = {}
    for row in records:
        code = str(row.get("code") or "").strip()
        name = str(row.get("name") or "").strip()
        if code and name:
            unique[code] = row
    records = list(unique.values())
    expected = max(MIN_RECORDS, int(count * 0.90))
    if len(records) < expected:
        raise RuntimeError(f"KMHFR_DIRECTORY_INCOMPLETE count={count} imported={len(records)} expected_min={expected}")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="kmhfr-", suffix=".json", dir=os.path.dirname(OUT))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({
                "source": endpoint,
                "api_count": count,
                "api_pages": pages,
                "records": records,
            }, fh, ensure_ascii=False, separators=(",", ":"))
            fh.write("\n")
        os.replace(tmp, OUT)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    print(f"KMHFR: published {len(records)} official facilities", flush=True)


def main() -> None:
    print("KMHFR: using official public API", flush=True)
    endpoint, first, count = fetch_first_page()
    pages = (count + PAGE_SIZE - 1) // PAGE_SIZE
    print(f"KMHFR: API reports {count} facilities across {pages} pages", flush=True)
    all_records = list(first)

    def one(page: int) -> tuple[int, list[dict]]:
        rows, page_count = request_page(endpoint, page)
        normalized = [r for x in rows if (r := normalize(x)) is not None]
        if page_count and page_count != count:
            print(f"KMHFR: page={page} reported_count={page_count}", flush=True)
        if not normalized:
            raise RuntimeError(f"KMHFR_API_PAGE_EMPTY page={page}")
        return page, normalized

    if pages > 1:
        with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
            futures = [pool.submit(one, page) for page in range(2, pages + 1)]
            for done, future in enumerate(concurrent.futures.as_completed(futures), start=2):
                page, rows = future.result()
                all_records.extend(rows)
                if done % 25 == 0 or done == pages:
                    print(f"KMHFR: progress {done}/{pages} pages, records={len(all_records)}", flush=True)

    write(all_records, count, pages, endpoint)


if __name__ == "__main__":
    main()
