from functools import cache
from pathlib import Path

import httpx

from app.config import Settings

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"


@cache
def _load_template(name: str) -> str:
    return (TEMPLATES_DIR / name).read_text(encoding="utf-8")


async def _send_email(settings: Settings, to: str, subject: str, html_body: str) -> bool:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.mailgun.net/v3/{settings.mailgun_domain}/messages",
            auth=("api", settings.mailgun_api_key),
            data={
                "from": f"ระบบแจ้งเตือนเลขจอง <noreply@{settings.mailgun_domain}>",
                "to": to,
                "subject": subject,
                "html": html_body,
            },
        )
        return resp.is_success


async def send_confirmation_email(
    settings: Settings, email: str, desired_number: int, vehicle_type: str, token: str
) -> bool:
    confirm_url = f"{settings.base_url}/api/confirm/{token}"
    html = _load_template("confirmation.html").format(
        desired_number=desired_number,
        vehicle_type=vehicle_type,
        confirm_url=confirm_url,
    )
    return await _send_email(
        settings, email, f"ยืนยันการรับแจ้งเตือนเลขจอง {desired_number}", html
    )


async def send_notification_email(
    settings: Settings,
    email: str,
    desired_number: int,
    reservation_date: str,
    letter_series: str,
    number_range_start: int,
    number_range_end: int,
    unsubscribe_token: str,
) -> bool:
    unsubscribe_url = f"{settings.base_url}/api/unsubscribe/{unsubscribe_token}"
    html = _load_template("notification.html").format(
        desired_number=desired_number,
        reservation_date=reservation_date,
        letter_series=letter_series,
        number_range_start=number_range_start,
        number_range_end=number_range_end,
        unsubscribe_url=unsubscribe_url,
    )
    return await _send_email(
        settings, email, f"เลข {desired_number} เปิดจองแล้ว!", html
    )
