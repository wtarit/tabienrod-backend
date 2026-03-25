#!/usr/bin/env python3
"""Fetch the DLT schedule PDF and save it to S3.

Does not parse the PDF or touch the database — just downloads and uploads.
Useful for investigating when the PDF gets updated.

Usage:
    uv run python scripts/save_pdf_to_s3.py
"""
import asyncio
from datetime import datetime, timezone

from app.config import settings
from app.s3 import upload_pdf_to_s3
from app.scraper import download_pdf, extract_gdrive_file_id, fetch_dlt_page, gdrive_download_url


async def main():
    html = await fetch_dlt_page()
    if not html:
        print("Failed to fetch DLT page")
        return

    file_id = extract_gdrive_file_id(html)
    if not file_id:
        print("No Google Drive PDF found in DLT page")
        return

    pdf_url = gdrive_download_url(file_id)
    pdf_bytes = await download_pdf(pdf_url)
    if not pdf_bytes:
        print(f"Failed to download PDF from {pdf_url}")
        return

    now = datetime.now(timezone.utc)
    s3_key = f"pdf-snapshots/{now.strftime('%Y-%m-%d')}/{now.strftime('%H%M%S')}.pdf"

    uploaded = await upload_pdf_to_s3(settings, pdf_bytes, s3_key)
    if uploaded:
        print(f"Saved to s3://{settings.s3_bucket_name}/{s3_key}")
    else:
        print("Upload failed — check S3 config and credentials")


if __name__ == "__main__":
    asyncio.run(main())
