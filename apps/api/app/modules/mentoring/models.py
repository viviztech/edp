from datetime import date, datetime, time
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.identity.models import Record, now


class MentorProfile(Record, Base):
    __tablename__ = "mentor_profiles"
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    headline: Mapped[str] = mapped_column(String(160))
    biography: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(String(16), default="active")
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id"),
        UniqueConstraint("id", "organization_id"),
        CheckConstraint("state IN ('active','inactive')", name="mentor_profile_state"),
        CheckConstraint("version > 0", name="mentor_profile_version"),
    )


class MentorExpertise(Record, Base):
    __tablename__ = "mentor_expertise"
    organization_id: Mapped[UUID] = mapped_column(index=True)
    mentor_profile_id: Mapped[UUID] = mapped_column(index=True)
    code: Mapped[str] = mapped_column(String(60))
    name_en: Mapped[str] = mapped_column(String(120))
    name_ta: Mapped[str] = mapped_column(String(120))
    __table_args__ = (
        ForeignKeyConstraint(
            ["mentor_profile_id", "organization_id"],
            ["mentor_profiles.id", "mentor_profiles.organization_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("mentor_profile_id", "code"),
        UniqueConstraint("id", "organization_id"),
    )


class MentorAvailability(Record, Base):
    __tablename__ = "mentor_availability"
    organization_id: Mapped[UUID] = mapped_column(index=True)
    mentor_profile_id: Mapped[UUID] = mapped_column(index=True)
    weekday: Mapped[int] = mapped_column(Integer)
    starts_at: Mapped[time] = mapped_column(Time)
    ends_at: Mapped[time] = mapped_column(Time)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata")
    __table_args__ = (
        ForeignKeyConstraint(
            ["mentor_profile_id", "organization_id"],
            ["mentor_profiles.id", "mentor_profiles.organization_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("mentor_profile_id", "weekday", "starts_at", "ends_at"),
        CheckConstraint("weekday BETWEEN 0 AND 6", name="mentor_availability_weekday"),
        CheckConstraint("ends_at > starts_at", name="mentor_availability_range"),
    )


class MentorAssignment(Record, Base):
    __tablename__ = "mentor_assignments"
    organization_id: Mapped[UUID] = mapped_column(index=True)
    mentor_profile_id: Mapped[UUID] = mapped_column(index=True)
    enrollment_id: Mapped[UUID] = mapped_column(index=True)
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    state: Mapped[str] = mapped_column(String(16), default="active")
    assigned_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (
        ForeignKeyConstraint(
            ["mentor_profile_id", "organization_id"],
            ["mentor_profiles.id", "mentor_profiles.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["enrollment_id", "organization_id"],
            ["enrollments.id", "enrollments.organization_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("id", "organization_id"),
        CheckConstraint("state IN ('active','ended')", name="mentor_assignment_state"),
        CheckConstraint("ends_on IS NULL OR ends_on >= starts_on", name="mentor_assignment_dates"),
        CheckConstraint("version > 0", name="mentor_assignment_version"),
        Index(
            "uq_mentor_assignment_active_enrollment",
            "enrollment_id",
            unique=True,
            postgresql_where=text("state = 'active'"),
        ),
    )


class MentoringSession(Record, Base):
    __tablename__ = "mentoring_sessions"
    organization_id: Mapped[UUID] = mapped_column(index=True)
    assignment_id: Mapped[UUID] = mapped_column(index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    mode: Mapped[str] = mapped_column(String(16))
    location_or_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    topic: Mapped[str] = mapped_column(String(240))
    status: Mapped[str] = mapped_column(String(16), default="scheduled")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (
        ForeignKeyConstraint(
            ["assignment_id", "organization_id"],
            ["mentor_assignments.id", "mentor_assignments.organization_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("id", "organization_id"),
        CheckConstraint("ends_at > starts_at", name="mentoring_session_range"),
        CheckConstraint("mode IN ('in_person','online','phone')", name="mentoring_session_mode"),
        CheckConstraint(
            "status IN ('scheduled','completed','cancelled')", name="mentoring_session_status"
        ),
        CheckConstraint("version > 0", name="mentoring_session_version"),
        Index("ix_mentoring_session_schedule", "organization_id", "starts_at", "status"),
    )


class MentoringNote(Record, Base):
    __tablename__ = "mentoring_notes"
    organization_id: Mapped[UUID] = mapped_column(index=True)
    assignment_id: Mapped[UUID] = mapped_column(index=True)
    session_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    author_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    visibility: Mapped[str] = mapped_column(String(32))
    body: Mapped[str] = mapped_column(Text)
    __table_args__ = (
        ForeignKeyConstraint(
            ["assignment_id", "organization_id"],
            ["mentor_assignments.id", "mentor_assignments.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["session_id", "organization_id"],
            ["mentoring_sessions.id", "mentoring_sessions.organization_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "visibility IN ('mentor_private','shared_with_participant')",
            name="mentoring_note_visibility",
        ),
        Index("ix_mentoring_note_assignment", "assignment_id", "created_at", "id"),
    )


class Goal(Record, Base):
    __tablename__ = "mentoring_goals"
    organization_id: Mapped[UUID] = mapped_column(index=True)
    assignment_id: Mapped[UUID] = mapped_column(index=True)
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    state: Mapped[str] = mapped_column(String(16), default="active")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (
        ForeignKeyConstraint(
            ["assignment_id", "organization_id"],
            ["mentor_assignments.id", "mentor_assignments.organization_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("id", "organization_id"),
        CheckConstraint("progress_percent BETWEEN 0 AND 100", name="mentoring_goal_progress"),
        CheckConstraint("state IN ('active','completed','cancelled')", name="mentoring_goal_state"),
        CheckConstraint("version > 0", name="mentoring_goal_version"),
    )


class ActionItem(Record, Base):
    __tablename__ = "mentoring_action_items"
    organization_id: Mapped[UUID] = mapped_column(index=True)
    assignment_id: Mapped[UUID] = mapped_column(index=True)
    goal_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(240))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    state: Mapped[str] = mapped_column(String(16), default="open")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (
        ForeignKeyConstraint(
            ["assignment_id", "organization_id"],
            ["mentor_assignments.id", "mentor_assignments.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["goal_id", "organization_id"],
            ["mentoring_goals.id", "mentoring_goals.organization_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("state IN ('open','completed','cancelled')", name="mentoring_action_state"),
        CheckConstraint("version > 0", name="mentoring_action_version"),
    )


class FollowUp(Record, Base):
    __tablename__ = "mentoring_follow_ups"
    organization_id: Mapped[UUID] = mapped_column(index=True)
    assignment_id: Mapped[UUID] = mapped_column(index=True)
    session_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    purpose: Mapped[str] = mapped_column(String(240))
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    state: Mapped[str] = mapped_column(String(16), default="scheduled")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (
        ForeignKeyConstraint(
            ["assignment_id", "organization_id"],
            ["mentor_assignments.id", "mentor_assignments.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["session_id", "organization_id"],
            ["mentoring_sessions.id", "mentoring_sessions.organization_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "state IN ('scheduled','completed','cancelled')", name="mentoring_follow_up_state"
        ),
        CheckConstraint("version > 0", name="mentoring_follow_up_version"),
        Index("ix_mentoring_follow_up_due", "organization_id", "state", "due_at"),
    )


class MentoringFeedback(Record, Base):
    __tablename__ = "mentoring_feedback"
    organization_id: Mapped[UUID] = mapped_column(index=True)
    session_id: Mapped[UUID] = mapped_column(index=True)
    participant_id: Mapped[UUID] = mapped_column(index=True)
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    __table_args__ = (
        ForeignKeyConstraint(
            ["session_id", "organization_id"],
            ["mentoring_sessions.id", "mentoring_sessions.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["participant_id", "organization_id"],
            ["participants.id", "participants.organization_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("session_id", "participant_id"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="mentoring_feedback_rating"),
    )
