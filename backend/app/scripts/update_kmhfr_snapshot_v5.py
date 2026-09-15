from __future__ import annotations

import concurrent.futures
import html
import json
import os
import random
import re
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

# Primary source is always the official KMHFR public API. When the API host is
# unreachable from a deployment network, fall back to the official KMHFR public
# directory itself. This is still first-party Ministry of Health data; no proxy,
# mirror, mock data, or synthetic facilities are used.
API_ENDPOINTS = [
    "https://api.kmhfr.health.go.ke/api/facilities/facilities/",
    "https://api.kmhfr.health.go.ke/api/public/facilities/",
]
DIRECTORY_ENDPOINT = "https://kmhfr.health.go.ke/public/facilities"
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/kmhfr_facilities.json"))
PAGE_SIZE = 30
MAX_PAGES = 1000
MAX_RETRIES = 3
DIRECT_TIMEOUT = 45
WORKERS = 6
HEADERS = {
    "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 AfyaSync/1.0 national-registry-import",
    "Connection": "close",
}


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
        raise RuntimeError(f"KMHFR_NON_JSON_RESPONSE source={source} preview={text[:240]!r}") from exc
    if not isinstance(payload, (dict, list)):
        raise RuntimeError(f"KMHFR_RESPONSE_INVALID source={source}")
    return payload


def request_json(url: str, timeout: int, source: str) -> dict | list:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return decode_payload(response.read(), source)
    except urllib.error.HTTPError as exc:
        body = b""
        try:
            body = exc.read(4096)
        except Exception:
            pass
        preview = body.decode("utf-8", errors="replace").strip().replace("\n", " ")
        raise RuntimeError(f"KMHFR_HTTP_ERROR source={source} status={exc.code} url={url} body={preview[:500]!r}") from exc


def request_text(url: str, timeout: int, source: str) -> str:
    req = urllib.request.Request(url, headers={**HEADERS, "Accept": "text/html,application/xhtml+xml"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"KMHFR_HTML_HTTP_ERROR source={source} status={exc.code} url={url}") from exc


def query_variants(page: int) -> list[str]:
    return [
        urllib.parse.urlencode({"page": page, "page_size": PAGE_SIZE, "format": "json"}),
        urllib.parse.urlencode({"page": page, "page_size": PAGE_SIZE}),
        urllib.parse.urlencode({"page_size": PAGE_SIZE, "page": page}),
        urllib.parse.urlencode({"page": page}),
    ]


def fetch_page(page: int) -> tuple[dict | list, str]:
    last: Exception | None = None
    for endpoint in API_ENDPOINTS:
        for query in query_variants(page):
            url = f"{endpoint}?{query}"
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    payload = request_json(url, DIRECT_TIMEOUT, "official_api")
                    if isinstance(payload, dict) and isinstance(payload.get("results"), list):
                        return payload, endpoint
                    if isinstance(payload, list):
                        return payload, endpoint
                    raise RuntimeError("KMHFR_PAGE_INVALID_RESULTS")
                except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, RuntimeError) as exc:
                    last = exc
                    if attempt < MAX_RETRIES:
                        delay = min(8, 1.0 * attempt) + random.random()
                        time.sleep(delay)
    raise RuntimeError(f"KMHFR_FETCH_FAILED page={page}: {last}") from last


class TableParser(HTMLParser):
    """Small dependency-free parser for the official directory's HTML tables."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.current: list[str] = []
        self.rows: list[list[str]] = []
        self.current_tag = ""

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag == "table":
            self.in_table = True
        elif self.in_table and tag == "tr":
            self.in_row = True
            self.current = []
        elif self.in_table and self.in_row and tag in {"td", "th"}:
            self.in_cell = True
            self.current_tag = tag

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self.in_table and self.in_row and tag in {"td", "th"}:
            self.in_cell = False
            self.current_tag = ""
        elif self.in_table and tag == "tr":
            if self.current:
                self.rows.append([re.sub(r"\\s+", " ", x).strip() for x in self.current])
            self.current = []
            self.in_row = False
        elif tag == "table":
            self.in_table = False

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            text = html.unescape(data).strip()
            if text:
                self.current.append(text)


def _norm_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def parse_directory_page(body: str) -> tuple[list[dict], int | None]:
    """Extract facility rows from the official server-rendered directory."""
    parser = TableParser()
    parser.feed(body)
    rows = [row for row in parser.rows if len(row) >= 3]
    records: list[dict] = []
    count_match = re.search(r"(?:of|/)\s*([0-9][0-9,]*)", re.sub(r"<[^>]+>", " ", body), flags=re.I)
    count = int(count_match.group(1).replace(",", "")) if count_match else None

    # Locate a header row by known KMHFR labels, then map the following rows.
    header_index = None
    headers: list[str] = []
    for idx, row in enumerate(rows):
        normalized = [_norm_header(x) for x in row]
        joined = " ".join(normalized)
        if any(k in joined for k in ("facility_name", "facility_code", "operation_status", "county")):
            header_index = idx
            headers = normalized
            break
    if header_index is None:
        # Next.js/React builds can embed a JSON data object instead of a literal table.
        for marker in ("facility_code", "facility_name", "official_name"):
            if marker not in body.lower():
                continue
            for match in re.finditer(r"\{[^{}]{0,800}\"(?:code|facility_code|mfl_code)\"[^{}]{0,800}\}", body, re.I):
                try:
                    obj = json.loads(html.unescape(match.group(0)))
                except Exception:
                    continue
                if isinstance(obj, dict) and any(k in obj for k in ("name", "facility_name", "official_name")):
                    records.append(obj)
            if records:
                break
        return records, count

    for row in rows[header_index + 1:]:
        if len(row) < 2:
            continue
        values = row + [""] * max(0, len(headers) - len(row))
        item = {headers[i]: values[i] for i in range(min(len(headers), len(values)))}
        if any(item.get(k) for k in ("facility_name", "name", "official_name", "facility_code", "code", "mfl_code")):
            records.append(item)
    return records, count


def fetch_directory_page(page: int) -> tuple[list[dict], int | None]:
    last: Exception | None = None
    url = f"{DIRECTORY_ENDPOINT}?page={page}"
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            body = request_text(url, DIRECT_TIMEOUT, "official_public_directory")
            records, count = parse_directory_page(body)
            if not records:
                raise RuntimeError(f"KMHFR_DIRECTORY_PAGE_EMPTY page={page}")
            return records, count
        except (urllib.error.URLError, TimeoutError, OSError, RuntimeError) as exc:
            last = exc
            if attempt < MAX_RETRIES:
                time.sleep(min(8, attempt) + random.random())
    raise RuntimeError(f"KMHFR_DIRECTORY_FETCH_FAILED page={page}: {last}") from last


def value(item: dict, *keys: str):
    lowered = {_norm_header(str(k)): v for k, v in item.items()}
    for key in keys:
        v = lowered.get(_norm_header(key))
        if isinstance(v, dict):
            v = v.get("name") or v.get("label") or v.get("value") or v.get("code")
        if v is not None and str(v).strip():
            return v
    return None


def compact(item: dict) -> dict:
    return {
        "id": value(item, "id", "uuid", "facility_id"),
        "code": value(item, "code", "mfl_code", "facility_code", "facility_code_number"),
        "name": value(item, "name", "facility_name", "facility_official_name", "official_name", "facility_unique_name"),
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


def write_snapshot(records: list[dict], source: str, count: int, total_pages: int) -> None:
    codes = [str(row.get("code") or "").strip() for row in records if str(row.get("code") or "").strip()]
    if len(codes) != len(set(codes)):
        raise RuntimeError("KMHFR_DUPLICATE_CODES")
    if not all(str(row.get("name") or "").strip() for row in records):
        raise RuntimeError("KMHFR_UNNAMED_FACILITY")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="kmhfr-", suffix=".json", dir=os.path.dirname(OUT))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"source": source, "api_count": count, "api_pages": total_pages, "records": records}, f, ensure_ascii=False, separators=(",", ":"))
            f.write("\n")
        os.replace(tmp, OUT)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def import_from_api() -> tuple[list[dict], str, int, int]:
    first, endpoint = fetch_page(1)
    first_items = items_from(first)
    if not first_items:
        raise RuntimeError("KMHFR_FIRST_PAGE_EMPTY_OR_INVALID")
    count = int(first.get("count") or 0) if isinstance(first, dict) else 0
    total_pages = first.get("total_pages") if isinstance(first, dict) else None
    if total_pages is None and count:
        total_pages = (count + PAGE_SIZE - 1) // PAGE_SIZE
    if total_pages is None and isinstance(first, dict) and first.get("next"):
        total_pages = MAX_PAGES
    total_pages = int(total_pages or 0)
    if total_pages <= 0 or total_pages > MAX_PAGES:
        raise RuntimeError(f"KMHFR_INVALID_TOTAL_PAGES:{total_pages}")
    records: dict[str, dict] = {}
    for raw in first_items:
        if isinstance(raw, dict):
            row = compact(raw)
            identity = str(row.get("code") or row.get("id") or "|".join(str(row.get(k) or "").lower() for k in ("name", "county", "sub_county")))
            if str(row.get("name") or "").strip() and identity:
                records[identity.lower()] = row

    def add_page(future):
        payload, _ = future.result()
        for raw in items_from(payload):
            if isinstance(raw, dict):
                row = compact(raw)
                identity = str(row.get("code") or row.get("id") or "|".join(str(row.get(k) or "").lower() for k in ("name", "county", "sub_county")))
                if str(row.get("name") or "").strip() and identity:
                    records[identity.lower()] = row

    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(fetch_page, page) for page in range(2, total_pages + 1)]
        for index, future in enumerate(concurrent.futures.as_completed(futures), start=2):
            add_page(future)
            if index % 30 == 0 or index == total_pages:
                print(f"KMHFR: API progress page={index}/{total_pages} records={len(records)}", flush=True)
    final = list(records.values())
    expected_min = max(10000, int(count * 0.90)) if count else 10000
    if len(final) < expected_min:
        raise RuntimeError(f"KMHFR_INCOMPLETE:api_count={count} imported={len(final)} expected_min={expected_min}")
    return final, endpoint, count, total_pages


def import_from_directory() -> tuple[list[dict], str, int, int]:
    print("KMHFR: API unreachable; using the official KMHFR public directory directly", flush=True)
    first, count = fetch_directory_page(1)
    total_count = int(count or 0)
    total_pages = (total_count + PAGE_SIZE - 1) // PAGE_SIZE if total_count else 0
    if total_pages <= 0 or total_pages > MAX_PAGES:
        raise RuntimeError(f"KMHFR_DIRECTORY_INVALID_TOTAL_PAGES:{total_pages}:count={total_count}")
    records: dict[str, dict] = {}

    def add(raw: dict) -> None:
        row = compact(raw)
        name = str(row.get("name") or "").strip()
        identity = str(row.get("code") or row.get("id") or "|".join(str(row.get(k) or "").lower() for k in ("name", "county", "sub_county")))
        if name and identity:
            records[identity.lower()] = row

    for raw in first:
        if isinstance(raw, dict):
            add(raw)

    def consume(future):
        page_records, _ = future.result()
        for raw in page_records:
            add(raw)

    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(fetch_directory_page, page) for page in range(2, total_pages + 1)]
        for completed, future in enumerate(concurrent.futures.as_completed(futures), start=2):
            consume(future)
            if completed % 30 == 0 or completed == total_pages:
                print(f"KMHFR: directory progress page={completed}/{total_pages} records={len(records)}", flush=True)
    final = list(records.values())
    expected_min = max(10000, int(total_count * 0.90))
    if len(final) < expected_min:
        raise RuntimeError(f"KMHFR_DIRECTORY_INCOMPLETE:directory_count={total_count} imported={len(final)} expected_min={expected_min}")
    return final, DIRECTORY_ENDPOINT, total_count, total_pages


def main() -> None:
    print("KMHFR: starting official national import", flush=True)
    try:
        final, source, count, total_pages = import_from_api()
    except Exception as api_error:
        print(f"KMHFR: official API import failed: {type(api_error).__name__}: {api_error}", flush=True)
        final, source, count, total_pages = import_from_directory()
    write_snapshot(final, source, count, total_pages)
    print(f"KMHFR: COMPLETE source={source} official_count={count} imported={len(final)} pages={total_pages}", flush=True)


if __name__ == "__main__":
    main()
