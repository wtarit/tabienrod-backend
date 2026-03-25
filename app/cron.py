from datetime import date, datetime, timezone

from sqlmodel import and_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import Settings
from app.email_service import send_notification_email
from app.models import CronRun, Notification, Schedule, Subscriber
from app.s3 import upload_pdf_to_s3
from app.scraper import fetch_and_parse_schedule


async def run_cron_job(session: AsyncSession, settings: Settings) -> None:
    """Fetch DLT schedule, match subscribers, send notifications."""
    now = datetime.now(timezone.utc)

    cron_run = CronRun(started_at=now)
    session.add(cron_run)
    await session.commit()
    await session.refresh(cron_run)

    schedules_found = 0
    notifications_sent = 0
    error_msg = None

    try:
        schedules, pdf_bytes = await fetch_and_parse_schedule()
        schedules_found = len(schedules)

        if pdf_bytes:
            s3_key = f"schedules/{date.today().isoformat()}/{cron_run.id}.pdf"
            await upload_pdf_to_s3(settings, pdf_bytes, s3_key)

        if not schedules:
            print("No schedules found")
            error_msg = "No schedules parsed from PDF"
        else:
            for s in schedules:
                schedule = Schedule(
                    reservation_date=s['reservation_date'],
                    letter_series=s['letter_series'],
                    number_range_start=s['number_range_start'],
                    number_range_end=s['number_range_end'],
                    vehicle_type=s['vehicle_type'],
                    registration_deadline=s.get('registration_deadline'),
                )
                session.add(schedule)
            await session.commit()

            # Find matching subscribers who haven't been notified
            today = date.today().isoformat()
            stmt = (
                select(Schedule, Subscriber)
                .join(
                    Subscriber,
                    and_(
                        Subscriber.vehicle_type == Schedule.vehicle_type,
                        Subscriber.desired_number >= Schedule.number_range_start,
                        Subscriber.desired_number <= Schedule.number_range_end,
                        Subscriber.confirmed == True,  # noqa: E712
                    ),
                )
                .outerjoin(
                    Notification,
                    and_(
                        Notification.subscriber_id == Subscriber.id,
                        Notification.schedule_id == Schedule.id,
                    ),
                )
                .where(Notification.id == None)  # noqa: E711
                .where(Schedule.reservation_date >= today)
            )
            results = (await session.exec(stmt)).all()

            for schedule, subscriber in results:
                try:
                    sent = await send_notification_email(
                        settings,
                        email=subscriber.email,
                        desired_number=subscriber.desired_number,
                        reservation_date=schedule.reservation_date,
                        letter_series=schedule.letter_series,
                        number_range_start=schedule.number_range_start,
                        number_range_end=schedule.number_range_end,
                        unsubscribe_token=subscriber.unsubscribe_token,
                    )
                    if sent:
                        notification = Notification(
                            subscriber_id=subscriber.id,
                            schedule_id=schedule.id,
                        )
                        session.add(notification)
                        await session.commit()
                        notifications_sent += 1
                    else:
                        print(f"Failed to send notification to {subscriber.email}")
                except Exception as e:
                    print(f"Error sending notification to {subscriber.email}: {e}")

    except Exception as e:
        error_msg = str(e)
        print(f"Cron job error: {e}")

    cron_run.completed_at = datetime.now(timezone.utc)
    cron_run.status = "error" if error_msg else "completed"
    cron_run.schedules_found = schedules_found
    cron_run.notifications_sent = notifications_sent
    cron_run.error_message = error_msg
    session.add(cron_run)
    await session.commit()

    print(f"Cron complete: {schedules_found} schedules, {notifications_sent} notifications sent")
