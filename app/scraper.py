import re

import httpx

from app.constants import letter_series_to_vehicle_type

FETCH_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "th-TH,th;q=0.9,en;q=0.8",
    "Referer": "https://reserve.dlt.go.th/",
}

GDRIVE_PATTERNS = [
    r'https://drive\.google\.com/file/d/([a-zA-Z0-9_-]+)',
    r'https://docs\.google\.com/.*?/d/([a-zA-Z0-9_-]+)',
    r'https://drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)',
]

THAI_MONTHS = {
    'ม.ค.': '01', 'มกราคม': '01',
    'ก.พ.': '02', 'กุมภาพันธ์': '02',
    'มี.ค.': '03', 'มีนาคม': '03',
    'เม.ย.': '04', 'เมษายน': '04',
    'พ.ค.': '05', 'พฤษภาคม': '05',
    'มิ.ย.': '06', 'มิถุนายน': '06',
    'ก.ค.': '07', 'กรกฎาคม': '07',
    'ส.ค.': '08', 'สิงหาคม': '08',
    'ก.ย.': '09', 'กันยายน': '09',
    'ต.ค.': '10', 'ตุลาคม': '10',
    'พ.ย.': '11', 'พฤศจิกายน': '11',
    'ธ.ค.': '12', 'ธันวาคม': '12',
}


def _thai_date_to_iso(day: str, month_str: str, year_str: str) -> str | None:
    month = THAI_MONTHS.get(month_str.strip())
    if not month:
        return None
    year_int = int(year_str)
    if year_int > 2500:
        year_int -= 543
    return f"{year_int:04d}-{month}-{int(day):02d}"


def extract_gdrive_file_id(html: str) -> str | None:
    # Strip HTML comments so we don't match old/inactive links
    cleaned = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
    for pattern in GDRIVE_PATTERNS:
        match = re.search(pattern, cleaned)
        if match:
            return match.group(1)
    return None


def gdrive_download_url(file_id: str) -> str:
    return f"https://drive.google.com/uc?export=download&id={file_id}"


async def fetch_dlt_page() -> str | None:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://reserve.dlt.go.th/reserve/v2/",
                headers=FETCH_HEADERS,
                follow_redirects=True,
            )
            if resp.status_code != 200:
                print(f"DLT page fetch failed: {resp.status_code}")
                return None
            return resp.text
    except Exception as e:
        print(f"DLT page fetch error: {e}")
        return None


async def download_pdf(url: str) -> bytes | None:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, follow_redirects=True)
            if resp.status_code != 200:
                print(f"PDF download failed: {resp.status_code}")
                return None
            return resp.content
    except Exception as e:
        print(f"PDF download error: {e}")
        return None


def _parse_thai_date(text: str) -> str | None:
    """Parse a Thai date string like '16 มีนาคม 2569' into ISO format."""
    if not text:
        return None
    month_names = '|'.join(re.escape(m) for m in THAI_MONTHS.keys())
    date_pattern = rf'(\d{{1,2}})\s*({month_names})\s*(\d{{2,4}})'
    match = re.search(date_pattern, text)
    if not match:
        return None
    return _thai_date_to_iso(match.group(1), match.group(2), match.group(3))


def _parse_number_range(text: str) -> tuple[int, int] | None:
    """Parse a range like '6001 - 8000' into (start, end)."""
    if not text:
        return None
    match = re.search(r'(\d{1,4})\s*[-–]\s*(\d{1,4})', text)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def parse_schedule_pdf(pdf_bytes: bytes) -> list[dict]:
    """Extract schedule entries from PDF using table extraction."""
    import fitz

    results = []
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    for page in doc:
        tables = page.find_tables()
        for table in tables.tables:
            rows = table.extract()
            # Skip title row and header row (first 2 rows)
            for row in rows[2:]:
                if len(row) < 5:
                    continue

                # Columns: [day, date, letter_series, number_range, deadline, notes]
                date_cell = (row[1] or '').replace('\n', ' ').strip()
                series_cell = (row[2] or '').replace('\n', ' ').strip()
                range_cell = (row[3] or '').replace('\n', ' ').strip()
                deadline_cell = (row[4] or '').replace('\n', ' ').strip()

                reservation_date = _parse_thai_date(date_cell)
                if not reservation_date:
                    continue

                series_match = re.search(r'\d?[ก-ฮ]{2}', series_cell)
                if not series_match:
                    continue
                letter_series = series_match.group(0)

                number_range = _parse_number_range(range_cell)
                if not number_range or number_range[0] >= number_range[1]:
                    continue

                series_chars = re.sub(r'^\d', '', letter_series)
                vehicle_type = letter_series_to_vehicle_type(series_chars)
                if not vehicle_type:
                    continue

                deadline = _parse_thai_date(deadline_cell)

                results.append({
                    'reservation_date': reservation_date,
                    'letter_series': letter_series,
                    'number_range_start': number_range[0],
                    'number_range_end': number_range[1],
                    'vehicle_type': vehicle_type,
                    'registration_deadline': deadline,
                })

    doc.close()
    return results


async def fetch_and_parse_schedule() -> tuple[list[dict], bytes | None]:
    html = await fetch_dlt_page()
    if not html:
        print("Failed to fetch DLT page")
        return [], None

    file_id = extract_gdrive_file_id(html)
    if not file_id:
        print("No Google Drive PDF found in DLT page")
        return [], None

    pdf_url = gdrive_download_url(file_id)
    pdf_bytes = await download_pdf(pdf_url)
    if not pdf_bytes:
        print(f"Failed to download PDF from {pdf_url}")
        return [], None

    schedules = parse_schedule_pdf(pdf_bytes)
    print(f"Parsed {len(schedules)} schedule entries")
    return schedules, pdf_bytes
