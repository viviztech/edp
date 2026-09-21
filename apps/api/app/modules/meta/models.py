from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
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


class MetaIntegration(Record, Base):
    __tablename__ = "meta_integrations"
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    page_id: Mapped[str] = mapped_column(String(80))
    access_token_ciphertext: Mapped[str] = mapped_column(Text)
    app_secret_ciphertext: Mapped[str] = mapped_column(Text)
    verify_token_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="active")
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (
        UniqueConstraint("organization_id", "page_id"),
        CheckConstraint("status IN ('active','disabled')", name="meta_integration_status"),
        CheckConstraint("version > 0", name="meta_integration_version"),
    )


class MetaFormMapping(Record, Base):
    __tablename__ = "meta_form_mappings"
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    integration_id: Mapped[UUID] = mapped_column(
        ForeignKey("meta_integrations.id", ondelete="CASCADE"), index=True
    )
    form_id: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(120))
    campaign: Mapped[str] = mapped_column(String(120), default="")
    field_mapping: Mapped[dict[str, str]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(16), default="active")
    version: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = (
        UniqueConstraint("integration_id", "form_id"),
        CheckConstraint("status IN ('active','disabled')", name="meta_mapping_status"),
        CheckConstraint("version > 0", name="meta_mapping_version"),
    )


class MetaWebhookEvent(Record, Base):
    __tablename__ = "meta_webhook_events"
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    integration_id: Mapped[UUID] = mapped_column(
        ForeignKey("meta_integrations.id", ondelete="RESTRICT"), index=True
    )
    mapping_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("meta_form_mappings.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    provider_event_id: Mapped[str] = mapped_column(String(120))
    meta_lead_id: Mapped[str] = mapped_column(String(120), index=True)
    page_id: Mapped[str] = mapped_column(String(80))
    form_id: Mapped[str] = mapped_column(String(80))
    state: Mapped[str] = mapped_column(String(16), default="queued")
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str] = mapped_column(String(48), default="")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON)
    lead_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("crm_leads.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retention_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    __table_args__ = (
        UniqueConstraint("integration_id", "provider_event_id"),
        CheckConstraint(
            "state IN ('queued','processing','retrying','completed','failed')",
            name="meta_event_state",
        ),
        CheckConstraint("attempt_count >= 0", name="meta_event_attempt_count"),
        Index("ix_meta_event_health", "organization_id", "state", "created_at"),
    )
