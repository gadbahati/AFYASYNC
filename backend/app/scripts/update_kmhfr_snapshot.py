from __future__ import annotations

import json
import os
import tempfile
import urllib.parse
import urllib.request

API = "https://api.kmhfr.health.go.ke/api/public/facilities/"
OUT = os.path.join(os.path.dirname(__file__), "../../data/kmhfr_facilities.json")
PAGE_SIZE = 30


def fetch(url: str) -> dict | list:
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "AfyaSync-KMHFR-Snapshot/1.0"})
    with urllib.request.urlopen(req, timeout=90) as response:
        return json.load(response)


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
    records: list[dict] = []
    pages = 0
    while url and pages < 1000:
        payload = fetch(url)
        results = payload.get("results", []) if isinstance(payload, dict) else payload
        if not isinstance(results, list):
            raise RuntimeError("KMHFR response did not contain a results list")
        records.extend(compact(item) for item in results if isinstance(item, dict) and compact(item).get("name"))
        pages += 1
        next_url = payload.get("next") if isinstance(payload, dict) else None
        if next_url:
            url = urllib.parse.urljoin(url, next_url)
        elif isinstance(payload, dict) and payload.get("total_pages") and pages < int(payload["total_pages"]):
            url = API + "?" + urllib.parse.urlencode({"page_size": PAGE_SIZE, "page": pages + 1})
        else:
            url = ""
        if pages % 25 == 0:
            print(f"KMHFR snapshot progress pages={pages} records={len(records)}", flush=True)

    if len(records) < 10000:
        raise RuntimeError(f"KMHFR snapshot unexpectedly small: {len(records)} records")

    path = os.path.abspath(OUT)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="kmhfr-", suffix=".json", dir=os.path.dirname(path))
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump({"source": API, "records": records}, handle, separators=(",", ":"), ensure_ascii=False)
        handle.write("\n")
    os.replace(tmp, path)
    print(f"KMHFR snapshot complete pages={pages} records={len(records)} path={path}", flush=True)


if __name__ == "__main__":
    main()
