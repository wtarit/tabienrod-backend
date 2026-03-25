from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import Settings, settings
from app.database import get_session
from app.email_service import send_confirmation_email
from app.models import Subscriber
from app.schemas import SubscribeRequest, SubscribeResponse

router = APIRouter(prefix="/api")


def get_settings() -> Settings:
    return settings


def _html_page(title: str, body: str) -> HTMLResponse:
    html = f"""<!DOCTYPE html>
<html lang="th">
<head><meta charset="UTF-8"><title>{title}</title>
<style>body{{font-family:sans-serif;max-width:600px;margin:40px auto;padding:20px;text-align:center}}</style>
</head>
<body>{body}</body>
</html>"""
    return HTMLResponse(content=html)


@router.post("/subscribe", response_model=SubscribeResponse)
async def subscribe(
    body: SubscribeRequest,
    session: AsyncSession = Depends(get_session),
    cfg: Settings = Depends(get_settings),
):
    confirmation_token = str(uuid4())
    unsubscribe_token = str(uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

    existing = (
        await session.exec(
            select(Subscriber).where(
                Subscriber.email == body.email,
                Subscriber.vehicle_type == body.vehicle_type,
                Subscriber.desired_number == body.desired_number,
            )
        )
    ).first()

    if existing:
        if existing.confirmed:
            return SubscribeResponse(
                message="คุณได้ลงทะเบียนเลขนี้แล้ว",
                email=body.email,
                desired_number=body.desired_number,
                vehicle_type=body.vehicle_type,
            )
        existing.confirmation_token = confirmation_token
        existing.unsubscribe_token = unsubscribe_token
        existing.confirmation_expires_at = expires_at
        session.add(existing)
        await session.commit()
    else:
        subscriber = Subscriber(
            email=body.email,
            vehicle_type=body.vehicle_type,
            desired_number=body.desired_number,
            confirmation_token=confirmation_token,
            unsubscribe_token=unsubscribe_token,
            confirmation_expires_at=expires_at,
        )
        session.add(subscriber)
        await session.commit()

    sent = await send_confirmation_email(
        cfg, body.email, body.desired_number, body.vehicle_type, confirmation_token
    )
    if not sent:
        return SubscribeResponse(
            message="ไม่สามารถส่งอีเมลได้ กรุณาลองใหม่",
            email=body.email,
            desired_number=body.desired_number,
            vehicle_type=body.vehicle_type,
        )

    return SubscribeResponse(
        message="กรุณาตรวจสอบอีเมลเพื่อยืนยันการรับแจ้งเตือน",
        email=body.email,
        desired_number=body.desired_number,
        vehicle_type=body.vehicle_type,
    )


@router.get("/confirm/{token}")
async def confirm(token: str, session: AsyncSession = Depends(get_session)):
    row = (
        await session.exec(
            select(Subscriber).where(Subscriber.confirmation_token == token)
        )
    ).first()

    if not row:
        return _html_page("ไม่พบข้อมูล", "<h2>ลิงก์ไม่ถูกต้อง</h2><p>กรุณาลงทะเบียนใหม่</p>")

    if row.confirmed:
        return _html_page("ยืนยันแล้ว", "<h2>คุณได้ยืนยันการรับแจ้งเตือนแล้ว</h2>")

    now = datetime.now(timezone.utc)
    if now > row.confirmation_expires_at:
        return _html_page(
            "ลิงก์หมดอายุ",
            "<h2>ลิงก์ยืนยันหมดอายุแล้ว</h2><p>กรุณาลงทะเบียนใหม่อีกครั้ง (ลิงก์มีอายุ 24 ชั่วโมง)</p>",
        )

    row.confirmed = True
    session.add(row)
    await session.commit()

    return _html_page(
        "ยืนยันสำเร็จ",
        f"<h2>ยืนยันสำเร็จ!</h2><p>คุณจะได้รับแจ้งเตือนเมื่อเลข {row.desired_number} เปิดจอง</p>",
    )


@router.get("/unsubscribe/{token}")
async def unsubscribe(token: str, session: AsyncSession = Depends(get_session)):
    row = (
        await session.exec(
            select(Subscriber).where(Subscriber.unsubscribe_token == token)
        )
    ).first()

    if not row:
        return _html_page("ไม่พบข้อมูล", "<h2>ลิงก์ไม่ถูกต้องหรือยกเลิกแล้ว</h2>")

    desired_number = row.desired_number
    await session.delete(row)
    await session.commit()

    return _html_page(
        "ยกเลิกสำเร็จ",
        f"<h2>ยกเลิกการแจ้งเตือนสำเร็จ</h2><p>คุณจะไม่ได้รับแจ้งเตือนสำหรับเลข {desired_number} อีกต่อไป</p>",
    )
