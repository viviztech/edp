from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.identity.models import Record


class ImpactDefinition(Record, Base):
    __tablename__ = "impact_definitions"
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    edition: Mapped[int] = mapped_column(Integer)
    title_en: Mapped[str] = mapped_column(String(200))
    title_ta: Mapped[str] = mapped_column(String(200))
    definition_en: Mapped[str] = mapped_column(Text)
    definition_ta: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(16), default="draft")
    version: Mapped[int] = mapped_column(Integer, default=1)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("id", "organization_id"),
        UniqueConstraint("organization_id", "edition"),
        CheckConstraint("edition > 0 AND version > 0", name="impact_definition_numbers"),
        CheckConstraint(
            "state IN ('draft','published','archived')", name="impact_definition_state"
        ),
        CheckConstraint(
            "(state = 'draft' AND published_at IS NULL) OR "
            "(state = 'published' AND published_at IS NOT NULL) OR state = 'archived'",
            name="impact_definition_publication",
        ),
        Index("ix_impact_definition_scope", "organization_id", "state", "id"),
    )


class ImpactDefinitionHistory(Record, Base):
    __tablename__ = "impact_definition_history"
    organization_id: Mapped[UUID] = mapped_column()
    definition_id: Mapped[UUID] = mapped_column()
    version: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(16))
    reason: Mapped[str] = mapped_column(String(500))
    actor_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    __table_args__ = (
        ForeignKeyConstraint(
            ["definition_id", "organization_id"],
            ["impact_definitions.id", "impact_definitions.organization_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("definition_id", "version"),
        CheckConstraint("version > 0", name="impact_definition_history_version"),
    )


class ImpactRecord(Record, Base):
    __tablename__ = "impact_records"
    organization_id: Mapped[UUID] = mapped_column()
    participant_id: Mapped[UUID] = mapped_column()
    enrollment_id: Mapped[UUID] = mapped_column()
    definition_id: Mapped[UUID] = mapped_column()
    actor_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    stage: Mapped[str] = mapped_column(String(16))
    observed_on: Mapped[date] = mapped_column(Date)
    business_started: Mapped[bool] = mapped_column(Boolean)
    business_active: Mapped[bool] = mapped_column(Boolean)
    jobs_created: Mapped[int] = mapped_column(Integer)
    revision: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(500))
    request_id: Mapped[UUID] = mapped_column()
    request_digest: Mapped[str] = mapped_column(String(64))
    __table_args__ = (
        ForeignKeyConstraint(
            ["participant_id", "organization_id"],
            ["participants.id", "participants.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["enrollment_id", "organization_id"],
            ["enrollments.id", "enrollments.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["definition_id", "organization_id"],
            ["impact_definitions.id", "impact_definitions.organization_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("organization_id", "actor_user_id", "request_id"),
        UniqueConstraint("enrollment_id", "stage", "observed_on", "revision"),
        CheckConstraint("stage IN ('baseline','outcome')", name="impact_record_stage"),
        CheckConstraint("revision > 0", name="impact_record_revision"),
        CheckConstraint("jobs_created BETWEEN 0 AND 100000", name="impact_record_jobs"),
        CheckConstraint("NOT business_active OR business_started", name="impact_record_active"),
        Index(
            "ix_impact_record_latest",
            "organization_id",
            "enrollment_id",
            "stage",
            "observed_on",
            "revision",
        ),
        Index("ix_impact_record_owner", "organization_id", "participant_id", "id"),
    )


class CohortImpactSnapshot(Record, Base):
    __tablename__ = "cohort_impact_snapshots"
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    requester_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    request_id: Mapped[UUID] = mapped_column()
    request_digest: Mapped[str] = mapped_column(String(64))
    filters: Mapped[dict[str, object]] = mapped_column(JSONB)
    dictionary_version: Mapped[str] = mapped_column(String(40))
    definition_ids: Mapped[list[str]] = mapped_column(JSONB)
    dashboard: Mapped[dict[str, object]] = mapped_column(JSONB)
    __table_args__ = (
        UniqueConstraint("id", "organization_id"),
        UniqueConstraint("organization_id", "requester_user_id", "request_id"),
        CheckConstraint("octet_length(dashboard::text) <= 1048576", name="impact_snapshot_bytes"),
        CheckConstraint(
            "dashboard->'filters' = filters "
            "AND dashboard->>'dictionary_version' = dictionary_version",
            name="impact_snapshot_consistency",
        ),
        Index("ix_impact_snapshot_scope", "organization_id", "id"),
    )


class ReportExport(Record, Base):
    __tablename__ = "report_exports"
    organization_id: Mapped[UUID] = mapped_column()
    snapshot_id: Mapped[UUID] = mapped_column()
    requester_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    request_id: Mapped[UUID] = mapped_column()
    request_digest: Mapped[str] = mapped_column(String(64))
    reason: Mapped[str] = mapped_column(String(500))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    csv_content: Mapped[str] = mapped_column(Text)
    row_count: Mapped[int] = mapped_column(Integer)
    byte_count: Mapped[int] = mapped_column(Integer)
    __table_args__ = (
        ForeignKeyConstraint(
            ["snapshot_id", "organization_id"],
            ["cohort_impact_snapshots.id", "cohort_impact_snapshots.organization_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("id", "organization_id", "requester_user_id"),
        UniqueConstraint("organization_id", "requester_user_id", "request_id"),
        CheckConstraint("row_count BETWEEN 1 AND 500", name="report_export_rows"),
        CheckConstraint(
            "byte_count BETWEEN 1 AND 262144 AND octet_length(csv_content) = byte_count",
            name="report_export_bytes",
        ),
        CheckConstraint("expires_at > created_at", name="report_export_expiry"),
        Index("ix_report_export_owner", "organization_id", "requester_user_id", "id"),
    )


class ReportExportCapability(Record, Base):
    __tablename__ = "report_export_capabilities"
    organization_id: Mapped[UUID] = mapped_column()
    export_id: Mapped[UUID] = mapped_column()
    requester_user_id: Mapped[UUID] = mapped_column()
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        ForeignKeyConstraint(
            ["export_id", "organization_id", "requester_user_id"],
            [
                "report_exports.id",
                "report_exports.organization_id",
                "report_exports.requester_user_id",
            ],
            ondelete="RESTRICT",
        ),
        CheckConstraint("expires_at > created_at", name="report_capability_expiry"),
        Index("ix_report_capability_job", "organization_id", "export_id", "requester_user_id"),
    )
