from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.identity.models import Record, now


class NotificationPreference(Record, Base):
    __tablename__ = "notification_preferences"
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    topic: Mapped[str] = mapped_column(String(40))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", "topic"),
        CheckConstraint(
            "topic IN ('lead_assignment','followup_due')", name="notification_preference_topic"
        ),
        CheckConstraint("version > 0", name="notification_preference_version"),
    )


class NotificationIntent(Record, Base):
    __tablename__ = "notification_intents"
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    recipient_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    topic: Mapped[str] = mapped_column(String(40))
    resource_id: Mapped[UUID] = mapped_column(ForeignKey("crm_leads.id", ondelete="RESTRICT"))
    source_activity_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("crm_lead_activities.id", ondelete="RESTRICT"), nullable=True
    )
    event_key: Mapped[str] = mapped_column(String(160))
    state: Mapped[str] = mapped_column(String(16), default="pending")
    version: Mapped[int] = mapped_column(Integer, default=1)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        UniqueConstraint("organization_id", "recipient_user_id", "event_key"),
        CheckConstraint(
            "topic IN ('lead_assignment','followup_due')", name="notification_intent_topic"
        ),
        CheckConstraint(
            "(topic = 'lead_assignment' AND source_activity_id IS NULL) OR "
            "(topic = 'followup_due' AND source_activity_id IS NOT NULL)",
            name="notification_intent_source",
        ),
        UniqueConstraint(
            "source_activity_id", "recipient_user_id", name="uq_notification_activity_recipient"
        ),
        CheckConstraint(
            "state IN ('pending','delivered','suppressed')", name="notification_intent_state"
        ),
        CheckConstraint("version > 0", name="notification_intent_version"),
        Index("ix_notification_dispatch", "state", "created_at"),
        Index("ix_notification_inbox", "organization_id", "recipient_user_id", "state", "id"),
        Index("ix_notification_retention", "created_at", "id"),
    )
