"""Typed participant notices; independent of CRM lead notifications."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.identity.models import Record, now


class ParticipantNotice(Record, Base):
    __tablename__ = "participant_notices"
    organization_id: Mapped[UUID] = mapped_column()
    recipient_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    enrollment_id: Mapped[UUID] = mapped_column()
    source_event_id: Mapped[UUID] = mapped_column()
    topic: Mapped[str] = mapped_column(String(40), default="enrollment_created")
    template_version: Mapped[str] = mapped_column(String(60), default="enrollment-created-v1")
    action_kind: Mapped[str] = mapped_column(String(16), default="schedule")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = (
        ForeignKeyConstraint(
            ["enrollment_id", "organization_id"],
            ["enrollments.id", "enrollments.organization_id"],
            name="fk_participant_notice_enrollment_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["source_event_id", "organization_id"],
            ["domain_outbox.id", "domain_outbox.organization_id"],
            name="fk_participant_notice_event_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "source_event_id", "recipient_user_id", "topic", name="uq_participant_notice_source"
        ),
        CheckConstraint(
            "topic = 'enrollment_created' AND template_version = 'enrollment-created-v1' "
            "AND action_kind = 'schedule'",
            name="participant_notice_contract",
        ),
        CheckConstraint(
            "expires_at > created_at AND expires_at <= created_at + interval '3650 days'",
            name="participant_notice_expiry",
        ),
        CheckConstraint(
            "(read_at IS NULL AND version = 1) OR "
            "(read_at IS NOT NULL AND read_at >= created_at AND read_at < expires_at "
            "AND version = 2)",
            name="participant_notice_read_state",
        ),
        Index(
            "ix_participant_notice_owner",
            "organization_id",
            "recipient_user_id",
            "created_at",
            "id",
        ),
        Index("ix_participant_notice_expiry", "expires_at", "id"),
    )


class ParticipantNoticePreference(Record, Base):
    __tablename__ = "participant_notice_preferences"
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    topic: Mapped[str] = mapped_column(String(40), default="enrollment_created")
    enabled: Mapped[bool] = mapped_column(Boolean)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "user_id", "topic", name="uq_participant_notice_preference"
        ),
        CheckConstraint("topic = 'enrollment_created'", name="participant_notice_preference_topic"),
        CheckConstraint("version > 0", name="participant_notice_preference_version"),
    )
