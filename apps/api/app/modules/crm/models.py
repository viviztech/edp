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
    Text,
    UniqueConstraint,
)
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
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
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
        ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    actor_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    activity_type: Mapped[str] = mapped_column(String(24))
    note: Mapped[str] = mapped_column(Text)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reminder_queued_for_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = (
        CheckConstraint(
            "activity_type IN ('call','email','meeting','task','note')", name="crm_activity_type"
        ),
        CheckConstraint("length(trim(note)) BETWEEN 1 AND 5000", name="crm_activity_note"),
        CheckConstraint("version > 0", name="crm_activity_version"),
        Index("ix_crm_activity_queue", "organization_id", "lead_id", "due_at"),
        Index("ix_crm_activity_due", "due_at", "id"),
    )


class Tag(Record, Base):
    __tablename__ = "crm_tags"
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(40))
    normalized_name: Mapped[str] = mapped_column(String(40))
    __table_args__ = (
        UniqueConstraint("organization_id", "normalized_name"),
        CheckConstraint("length(trim(name)) BETWEEN 1 AND 40", name="crm_tag_name"),
    )


class LeadTag(Record, Base):
    __tablename__ = "crm_lead_tags"
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    lead_id: Mapped[UUID] = mapped_column(
        ForeignKey("crm_leads.id", ondelete="CASCADE"), index=True
    )
    tag_id: Mapped[UUID] = mapped_column(ForeignKey("crm_tags.id", ondelete="CASCADE"), index=True)
    __table_args__ = (UniqueConstraint("organization_id", "lead_id", "tag_id"),)


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
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    lease_token_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=now, nullable=True
    )
    disposed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    legacy_output: Mapped[bool] = mapped_column(Boolean, default=False)
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
        CheckConstraint(
            "version > 0 AND attempt_count BETWEEN 0 AND 10", name="crm_export_version"
        ),
        CheckConstraint("row_count BETWEEN 0 AND 10000", name="crm_export_row_count"),
        CheckConstraint(
            "csv_content IS NULL OR (legacy_output AND status = 'completed') "
            "OR octet_length(csv_content) BETWEEN 1 AND 20971520",
            name="crm_export_byte_count",
        ),
        CheckConstraint(
            "(status = 'running' AND lease_token_digest IS NOT NULL "
            "AND lease_token_digest ~ '^[0-9a-f]{64}$' AND lease_until IS NOT NULL "
            "AND next_attempt_at IS NULL AND completed_at IS NULL) OR "
            "(status <> 'running' AND lease_token_digest IS NULL AND lease_until IS NULL)",
            name="crm_export_lease_state",
        ),
        CheckConstraint(
            "(status = 'queued' AND next_attempt_at IS NOT NULL AND completed_at IS NULL) OR "
            "(status IN ('completed','failed') AND next_attempt_at IS NULL "
            "AND completed_at IS NOT NULL) OR (status = 'running' AND next_attempt_at IS NULL)",
            name="crm_export_completion_state",
        ),
        CheckConstraint(
            "error_code IN ('','generation_failed','queue_unavailable','recovered_lease',"
            "'retry_exhausted','request_expired','requester_unavailable','row_limit_exceeded',"
            "'output_too_large','expired') AND (status <> 'failed' OR error_code <> '')",
            name="crm_export_error_code",
        ),
        CheckConstraint(
            "disposed_at IS NULL OR (status = 'failed' AND error_code = 'expired' "
            "AND csv_content IS NULL AND disposed_at >= expires_at)",
            name="crm_export_disposal_state",
        ),
        Index("ix_crm_export_owner", "organization_id", "requested_by_id", "created_at"),
        Index("ix_crm_export_due", "status", "next_attempt_at", "id"),
        Index("ix_crm_export_lease", "status", "lease_until", "id"),
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
