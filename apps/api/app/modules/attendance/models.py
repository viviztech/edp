from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.identity.models import Record, now


class AttendancePolicy(Record, Base):
    __tablename__ = "attendance_policies"
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    cohort_id: Mapped[UUID] = mapped_column(index=True)
    threshold_percent: Mapped[int] = mapped_column(Integer, default=75)
    late_after_minutes: Mapped[int] = mapped_column(Integer, default=15)
    opens_before_minutes: Mapped[int] = mapped_column(Integer, default=15)
    closes_after_minutes: Mapped[int] = mapped_column(Integer, default=30)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (
        ForeignKeyConstraint(
            ["cohort_id", "organization_id"],
            ["cohorts.id", "cohorts.organization_id"],
            name="fk_attendance_policy_cohort_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("cohort_id"),
        UniqueConstraint("id", "organization_id"),
        CheckConstraint("threshold_percent BETWEEN 1 AND 100", name="attendance_threshold"),
        CheckConstraint("late_after_minutes BETWEEN 0 AND 240", name="attendance_late_after"),
        CheckConstraint("opens_before_minutes BETWEEN 0 AND 1440", name="attendance_opens_before"),
        CheckConstraint("closes_after_minutes BETWEEN 0 AND 1440", name="attendance_closes_after"),
        CheckConstraint("version > 0", name="attendance_policy_version"),
    )


class AttendanceWindow(Record, Base):
    __tablename__ = "attendance_windows"
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    session_id: Mapped[UUID] = mapped_column(index=True)
    token_digest: Mapped[str] = mapped_column(String(64), unique=True)
    opens_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    closes_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    state: Mapped[str] = mapped_column(String(16), default="active")
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (
        ForeignKeyConstraint(
            ["session_id", "organization_id"],
            ["program_sessions.id", "program_sessions.organization_id"],
            name="fk_attendance_window_session_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("id", "organization_id"),
        CheckConstraint("closes_at > opens_at", name="attendance_window_range"),
        CheckConstraint("state IN ('active','closed')", name="attendance_window_state"),
        CheckConstraint("version > 0", name="attendance_window_version"),
        CheckConstraint(
            "(state = 'active' AND closed_at IS NULL) OR "
            "(state = 'closed' AND closed_at IS NOT NULL)",
            name="attendance_window_close_evidence",
        ),
        Index(
            "uq_attendance_window_active_session",
            "session_id",
            unique=True,
            postgresql_where=text("state = 'active'"),
        ),
        Index("ix_attendance_window_time", "session_id", "opens_at", "closes_at"),
    )


class AttendanceRecord(Record, Base):
    __tablename__ = "attendance_records"
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    session_id: Mapped[UUID] = mapped_column(index=True)
    enrollment_id: Mapped[UUID] = mapped_column(index=True)
    status: Mapped[str] = mapped_column(String(16))
    source: Mapped[str] = mapped_column(String(16))
    marked_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    marked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (
        ForeignKeyConstraint(
            ["session_id", "organization_id"],
            ["program_sessions.id", "program_sessions.organization_id"],
            name="fk_attendance_record_session_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["enrollment_id", "organization_id"],
            ["enrollments.id", "enrollments.organization_id"],
            name="fk_attendance_record_enrollment_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("session_id", "enrollment_id"),
        UniqueConstraint("id", "organization_id"),
        CheckConstraint(
            "status IN ('present','absent','late','excused')", name="attendance_record_status"
        ),
        CheckConstraint("source IN ('manual','qr')", name="attendance_record_source"),
        CheckConstraint("version > 0", name="attendance_record_version"),
        Index("ix_attendance_record_enrollment_time", "enrollment_id", "created_at", "id"),
    )


class AttendanceCorrection(Record, Base):
    __tablename__ = "attendance_corrections"
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    attendance_record_id: Mapped[UUID] = mapped_column(index=True)
    actor_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    from_status: Mapped[str] = mapped_column(String(16))
    to_status: Mapped[str] = mapped_column(String(16))
    record_version: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(500))
    __table_args__ = (
        ForeignKeyConstraint(
            ["attendance_record_id", "organization_id"],
            ["attendance_records.id", "attendance_records.organization_id"],
            name="fk_attendance_correction_record_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("attendance_record_id", "record_version"),
        CheckConstraint(
            "from_status IN ('present','absent','late','excused')",
            name="attendance_correction_from_status",
        ),
        CheckConstraint(
            "to_status IN ('present','absent','late','excused')",
            name="attendance_correction_to_status",
        ),
        CheckConstraint("from_status <> to_status", name="attendance_correction_changed"),
        CheckConstraint("record_version > 1", name="attendance_correction_version"),
    )
