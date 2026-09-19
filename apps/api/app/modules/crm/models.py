from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.identity.models import Record, now


class Lead(Record, Base):
    __tablename__ = "crm_leads"
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(320), default="")
    phone: Mapped[str] = mapped_column(String(32), default="")
    source: Mapped[str] = mapped_column(String(80), default="manual")
    campaign: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[str] = mapped_column(String(24), default="new")
    merged_into_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("crm_leads.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    assigned_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    dedupe_hash: Mapped[str] = mapped_column(String(64))
    version: Mapped[int] = mapped_column(Integer, default=1)
    notes: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(default=now, onupdate=now)
    __table_args__ = (
        UniqueConstraint("organization_id", "dedupe_hash"),
        CheckConstraint(
            "status IN ('new','contacted','interested','registration_started',"
            "'converted','not_interested','merged')",
            name="crm_lead_status",
        ),
        CheckConstraint(
            "(status = 'merged' AND merged_into_id IS NOT NULL) OR "
            "(status <> 'merged' AND merged_into_id IS NULL)",
            name="crm_lead_merge_state",
        ),
        CheckConstraint("length(trim(name)) BETWEEN 1 AND 120", name="crm_lead_name"),
        Index("ix_crm_lead_queue", "organization_id", "status", "assigned_user_id"),
    )


class LeadActivity(Record, Base):
    __tablename__ = "crm_lead_activities"
    lead_id: Mapped[UUID] = mapped_column(
        ForeignKey("crm_leads.id", ondelete="CASCADE"), index=True
    )
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    actor_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    activity_type: Mapped[str] = mapped_column(String(24))
    note: Mapped[str] = mapped_column(Text)
    due_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    __table_args__ = (
        CheckConstraint(
            "activity_type IN ('call','email','meeting','task','note')", name="crm_activity_type"
        ),
        CheckConstraint("length(trim(note)) BETWEEN 1 AND 5000", name="crm_activity_note"),
        Index("ix_crm_activity_queue", "organization_id", "lead_id", "due_at"),
    )


class DuplicateReview(Record, Base):
    __tablename__ = "crm_duplicate_reviews"
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    lead_a_id: Mapped[UUID] = mapped_column(
        ForeignKey("crm_leads.id", ondelete="RESTRICT"), index=True
    )
    lead_b_id: Mapped[UUID] = mapped_column(
        ForeignKey("crm_leads.id", ondelete="RESTRICT"), index=True
    )
    state: Mapped[str] = mapped_column(String(16), default="pending")
    version: Mapped[int] = mapped_column(Integer, default=1)
    reason: Mapped[str] = mapped_column(String(500), default="")
    resolved_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    __table_args__ = (
        UniqueConstraint("organization_id", "lead_a_id", "lead_b_id"),
        CheckConstraint("lead_a_id <> lead_b_id", name="crm_duplicate_distinct"),
        CheckConstraint("state IN ('pending','merged','rejected')", name="crm_duplicate_state"),
    )


class ExportJob(Record, Base):
    __tablename__ = "crm_export_jobs"
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    requested_by_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[str] = mapped_column(String(16), default="queued")
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    csv_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str] = mapped_column(String(40), default="")
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    expires_at: Mapped[datetime] = mapped_column(index=True)
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued','running','completed','failed')",
            name="crm_export_status",
        ),
        CheckConstraint(
            "(status = 'completed' AND csv_content IS NOT NULL) OR "
            "(status <> 'completed' AND csv_content IS NULL)",
            name="crm_export_content_state",
        ),
        Index("ix_crm_export_owner", "organization_id", "requested_by_id", "created_at"),
    )


class LeadConversion(Record, Base):
    __tablename__ = "crm_lead_conversions"
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    lead_id: Mapped[UUID] = mapped_column(
        ForeignKey("crm_leads.id", ondelete="RESTRICT"), unique=True
    )
    person_id: Mapped[UUID] = mapped_column(
        ForeignKey("people.id", ondelete="RESTRICT"), index=True
    )
    actor_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    source: Mapped[str] = mapped_column(String(80))
    campaign: Mapped[str] = mapped_column(String(120))
    lead_version: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(500))
    __table_args__ = (
        CheckConstraint("lead_version > 0", name="crm_conversion_version"),
        CheckConstraint("length(trim(reason)) BETWEEN 1 AND 500", name="crm_conversion_reason"),
    )
