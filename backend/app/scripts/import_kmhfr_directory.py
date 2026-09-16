from __future__ import annotations

import concurrent.futures
import html
import json
import os
import re
import tempfile
import urllib.error
import urllib.request
from html.parser import HTMLParser

ENDPOINT = "https://kmhfr.health.go.ke/public/facilities"
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/kmhfr_facilities.json"))
PAGE_SIZE = 30
WORKERS = 12
TIMEOUT = 20
MIN_RECORDS = 10000
HEADERS = {
    "User-Agent": "Mozilla/5.0 AfyaSync/1.0 national-registry-import",
    "Accept": "text/html,application/xhtml+xml",
    "Connection": "close",
}


class TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._link_text: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() == "a":
            attrs_map = dict(attrs)
            href = attrs_map.get("href")
            if href:
                self._href = href
                self._link_text = []

    def handle_data(self, data: str) -> None:
        value = re.sub(r"\s+", " ", html.unescape(data)).strip()
        if value:
            self.parts.append(value)
            if self._href is not None:
                self._link_text.append(value)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href is not None:
            self.links.append((self._href, " ".join(self._link_text).strip()))
            self._href = None
            self._link_text = []


def fetch(page: int) -> str:
    req = urllib.request.Request(f"{ENDPOINT}?page={page}", headers=HEADERS)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        return response.read().decode("utf-8", errors="replace")


def clean_text(fragment: str) -> str:
    parser = TextParser()
    parser.feed(fragment)
    return " ".join(parser.parts)


def parse_page(body: str) -> tuple[list[dict], int]:
    visible = clean_text(body)
    counts = re.findall(r"\bof\s+([0-9][0-9,]*)\b", visible, flags=re.I)
    count = int(counts[-1].replace(",", "")) if counts else 0

    # Each facility card links to /public/facilities/<UUID>. The card text
    # contains the facility name, MFL code, type, level, status and geography.
    link_re = re.compile(
        r'<a[^>]+href=["\'](?:https?://[^/]+)?/public/facilities/([0-9a-f-]{36})[^"\']*["\'][^>]*>(.*?)</a>',
        flags=re.I | re.S,
    )
    matches = list(link_re.finditer(body))
    records: list[dict] = []
    for i, match in enumerate(matches):
        name = clean_text(match.group(2)).strip()
        if not name or name.lower() in {"home", "facilities"}:
            continue
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        card = clean_text(body[start:end])
        code_match = re.search(r"#\s*([0-9]{2,8})\b", card)
        if not code_match:
            continue
        code = code_match.group(1)

        def field(label: str) -> str | None:
            m = re.search(rf"{label}\s*:\s*(.*?)(?=\s+(?:County|Sub-County|Ward|Constituency|$))", card, flags=re.I)
            return m.group(1).strip() if m else None

        county = field("County")
        sub_county = field("Sub-County")
        ward = field("Ward")
        constituency = field("Constituency")
        status = "Operational" if re.search(r"\bOperational\b", card, flags=re.I) else None
        level = re.search(r"\b(Level\s+[1-6])\b", card, flags=re.I)

        # The listing card order is stable: name, code, facility type, level,
        # status, then administrative fields. Remove known labels to isolate type.
        tail = card[card.find(code) + len(code):]
        tail = re.sub(r"\bLevel\s+[1-6]\b", " ", tail, flags=re.I)
        tail = re.sub(r"\bOperational\b", " ", tail, flags=re.I)
        tail = re.sub(r"County\s*:\s*.*?(?=\s+Sub-County|\s+Ward|\s+Constituency|$)", " ", tail, flags=re.I)
        tail = re.sub(r"Sub-County\s*:\s*.*?(?=\s+Ward|\s+Constituency|$)", " ", tail, flags=re.I)
        tail = re.sub(r"Ward\s*:\s*.*?(?=\s+Constituency|$)", " ", tail, flags=re.I)
        tail = re.sub(r"Constituency\s*:\s*.*$", " ", tail, flags=re.I)
        facility_type = re.sub(r"\s+", " ", tail).strip() or None

        records.append({
            "id": match.group(1),
            "code": code,
            "name": name,
            "facility_type": facility_type,
            "operation_status": status,
            "county": county,
            "sub_county": sub_county,
            "constituency": constituency,
            "ward": ward,
            "keph_level": level.group(1) if level else None,
            "owner": None,
            "latitude": None,
            "longitude": None,
            "registration_number": None,
        })

    return records, count


def write(records: list[dict], count: int, pages: int) -> None:
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
                "source": ENDPOINT,
                "api_count": count,
                "api_pages": pages,
                "records": records,
            }, fh, ensure_ascii=False, separators=(",", ":"))
            fh.write("\n")
        os.replace(tmp, OUT)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    print(f"KMHFR: published {len(records)} facilities from official directory", flush=True)


def main() -> None:
    print("KMHFR: using official Ministry of Health public directory", flush=True)
    first_body = fetch(1)
    first, count = parse_page(first_body)
    if not first or not count:
        raise RuntimeError(f"KMHFR_DIRECTORY_FIRST_PAGE_INVALID records={len(first)} count={count}")
    pages = (count + PAGE_SIZE - 1) // PAGE_SIZE
    print(f"KMHFR: directory reports {count} facilities across {pages} pages", flush=True)
    all_records = list(first)

    def one(page: int) -> tuple[int, list[dict]]:
        body = fetch(page)
        rows, page_count = parse_page(body)
        if page_count and page_count != count:
            print(f"KMHFR: page={page} reported_count={page_count}", flush=True)
        if not rows:
            raise RuntimeError(f"KMHFR_DIRECTORY_PAGE_EMPTY page={page}")
        return page, rows

    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(one, page) for page in range(2, pages + 1)]
        for done, future in enumerate(concurrent.futures.as_completed(futures), start=2):
            page, rows = future.result()
            all_records.extend(rows)
            if done % 25 == 0 or done == pages:
                print(f"KMHFR: progress {done}/{pages} pages, raw_records={len(all_records)}", flush=True)

    write(all_records, count, pages)


if __name__ == "__main__":
    main()
