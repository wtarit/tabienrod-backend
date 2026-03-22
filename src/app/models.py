from datetime import datetime, timezone

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel, UniqueConstraint


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Subscriber(SQLModel, table=True):
    __tablename__ = "subscribers"
    __table_args__ = (
        UniqueConstraint("email", "vehicle_type", "desired_number", name="idx_sub_email_vt_num"),
    )

    id: int | None = Field(default=None, primary_key=True)
    email: str
    vehicle_type: str
    desired_number: int
    confirmed: bool = Field(default=False)
    confirmation_token: str = Field(unique=True)
    unsubscribe_token: str = Field(unique=True)
    confirmation_expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    created_at: datetime = Field(default_factory=_utcnow, sa_column=Column(DateTime(timezone=True), nullable=False))


class Schedule(SQLModel, table=True):
    __tablename__ = "schedules"

    id: int | None = Field(default=None, primary_key=True)
    reservation_date: str
    letter_series: str
    number_range_start: int
    number_range_end: int
    vehicle_type: str
    registration_deadline: str | None = None
    fetched_at: datetime = Field(default_factory=_utcnow, sa_column=Column(DateTime(timezone=True), nullable=False))


class Notification(SQLModel, table=True):
    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint("subscriber_id", "schedule_id", name="uq_notification"),
    )

    id: int | None = Field(default=None, primary_key=True)
    subscriber_id: int = Field(foreign_key="subscribers.id")
    schedule_id: int = Field(foreign_key="schedules.id")
    sent_at: datetime = Field(default_factory=_utcnow, sa_column=Column(DateTime(timezone=True), nullable=False))


class CronRun(SQLModel, table=True):
    __tablename__ = "cron_runs"

    id: int | None = Field(default=None, primary_key=True)
    started_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    completed_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    status: str = "running"
    schedules_found: int = 0
    notifications_sent: int = 0
    error_message: str | None = None
