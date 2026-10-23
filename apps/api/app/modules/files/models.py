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
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.identity.models import Record, now

PURPOSE_CHECK = (
    "purpose IN ('application_document','cms_asset','assignment_submission',"
    "'lms_material','helpdesk_attachment')"
)


class FilePolicy(Record, Base):
    __tablename__ = "file_policies"
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    client_request_id: Mapped[UUID] = mapped_column()
    request_digest: Mapped[str] = mapped_column(String(64))
    purpose: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(160))
    notice_en: Mapped[str] = mapped_column(Text)
    notice_ta: Mapped[str] = mapped_column(Text)
    allowed_mime_types: Mapped[list[str]] = mapped_column(ARRAY(String(64)))
    max_file_bytes: Mapped[int] = mapped_column(Integer)
    max_files: Mapped[int] = mapped_column(Integer)
    retention_days: Mapped[int] = mapped_column(Integer)
    rejected_retention_days: Mapped[int] = mapped_column(Integer)
    allow_frozen_disposal: Mapped[bool] = mapped_column(Boolean)
    edition: Mapped[int] = mapped_column(Integer)
    version: Mapped[int] = mapped_column(Integer, default=1)
    state: Mapped[str] = mapped_column(String(16), default="draft")
    copy_from: Mapped[UUID | None] = mapped_column(nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (
        ForeignKeyConstraint(
            ["copy_from", "organization_id", "purpose"],
            ["file_policies.id", "file_policies.organization_id", "file_policies.purpose"],
            name="fk_file_policy_copy_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("organization_id", "client_request_id"),
        UniqueConstraint("organization_id", "purpose", "edition"),
        UniqueConstraint("id", "organization_id", "purpose", name="uq_file_policy_scope"),
        CheckConstraint(PURPOSE_CHECK, name="file_policy_purpose"),
        CheckConstraint("state IN ('draft','published','retired')", name="file_policy_state"),
        CheckConstraint("edition > 0 AND version > 0", name="file_policy_versions"),
        CheckConstraint("max_file_bytes BETWEEN 1 AND 104857600", name="file_policy_bytes"),
        CheckConstraint("max_files BETWEEN 1 AND 100", name="file_policy_count"),
        CheckConstraint(
            "retention_days BETWEEN 1 AND 3650 AND rejected_retention_days BETWEEN 1 AND 3650",
            name="file_policy_retention",
        ),
        CheckConstraint(
            "length(trim(name)) > 0 AND length(trim(notice_en)) BETWEEN 1 AND 4000 "
            "AND length(trim(notice_ta)) BETWEEN 1 AND 4000",
            name="file_policy_notices",
        ),
        CheckConstraint(
            "cardinality(allowed_mime_types) BETWEEN 1 AND 5 AND "
            "allowed_mime_types <@ ARRAY['application/pdf','image/jpeg','image/png',"
            "'image/webp','text/plain']::varchar[]",
            name="file_policy_mime",
        ),
        Index("ix_file_policy_queue", "organization_id", "purpose", "state", "id"),
        Index(
            "uq_file_policy_draft",
            "organization_id",
            "purpose",
            unique=True,
            postgresql_where=text("state = 'draft'"),
        ),
        Index(
            "uq_file_policy_published",
            "organization_id",
            "purpose",
            unique=True,
            postgresql_where=text("state = 'published'"),
        ),
    )


class FileObject(Record, Base):
    __tablename__ = "file_objects"
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    owner_person_id: Mapped[UUID] = mapped_column(
        ForeignKey("people.id", ondelete="RESTRICT"), index=True
    )
    policy_id: Mapped[UUID] = mapped_column()
    purpose: Mapped[str] = mapped_column(String(32))
    resource_id: Mapped[UUID] = mapped_column()
    client_request_id: Mapped[UUID] = mapped_column()
    request_digest: Mapped[str] = mapped_column(String(64))
    object_key: Mapped[str] = mapped_column(String(512), unique=True)
    expected_media_type: Mapped[str] = mapped_column(String(64))
    expected_byte_size: Mapped[int] = mapped_column(Integer)
    expected_sha256: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(16), default="pending")
    version: Mapped[int] = mapped_column(Integer, default=1)
    storage_version: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    stored_byte_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stored_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scan_storage_version: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    scan_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    scan_byte_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scanned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    upload_token_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    upload_lease_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    scan_token_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    scan_lease_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    scan_attempts: Mapped[int] = mapped_column(Integer, default=0)
    scan_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    retention_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    legal_hold: Mapped[bool] = mapped_column(Boolean, default=False)
    evidence_frozen: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (
        ForeignKeyConstraint(
            ["policy_id", "organization_id", "purpose"],
            ["file_policies.id", "file_policies.organization_id", "file_policies.purpose"],
            name="fk_file_object_policy_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("organization_id", "client_request_id"),
        UniqueConstraint(
            "id",
            "organization_id",
            "owner_person_id",
            "purpose",
            "resource_id",
            name="uq_file_object_domain_scope",
        ),
        CheckConstraint(PURPOSE_CHECK, name="file_object_purpose"),
        CheckConstraint(
            "state IN ('pending','uploading','quarantined','scanning','clean',"
            "'infected','rejected','deleted')",
            name="file_object_state",
        ),
        CheckConstraint(
            "version > 0 AND scan_attempts BETWEEN 0 AND 10", name="file_object_versions"
        ),
        CheckConstraint("expected_byte_size BETWEEN 1 AND 104857600", name="file_object_bytes"),
        CheckConstraint("expected_sha256 ~ '^[0-9a-f]{64}$'", name="file_object_digest"),
        CheckConstraint(
            "expected_media_type IN ('application/pdf','image/jpeg','image/png','image/webp',"
            "'text/plain')",
            name="file_object_mime",
        ),
        CheckConstraint(
            "(storage_version IS NULL AND stored_byte_size IS NULL AND stored_sha256 IS NULL "
            "AND verified_at IS NULL) OR (storage_version IS NOT NULL "
            "AND stored_byte_size IS NOT NULL AND stored_sha256 IS NOT NULL "
            "AND length(storage_version) > 0 "
            "AND stored_byte_size = expected_byte_size AND stored_sha256 = expected_sha256 "
            "AND verified_at IS NOT NULL)",
            name="file_object_verified_evidence",
        ),
        CheckConstraint(
            "state NOT IN ('quarantined','scanning','clean','infected') OR "
            "(storage_version IS NOT NULL AND verified_at IS NOT NULL)",
            name="file_object_requires_verification",
        ),
        CheckConstraint(
            "state NOT IN ('clean','infected') OR (scanned_at IS NOT NULL "
            "AND scan_storage_version IS NOT NULL AND scan_sha256 IS NOT NULL "
            "AND scan_byte_size IS NOT NULL "
            "AND scan_storage_version = storage_version AND scan_sha256 = stored_sha256 "
            "AND scan_byte_size = stored_byte_size)",
            name="file_object_scan_evidence",
        ),
        CheckConstraint(
            "(state = 'deleted') = (deleted_at IS NOT NULL)", name="file_object_deleted"
        ),
        CheckConstraint(
            "(state = 'uploading') = (upload_token_digest IS NOT NULL "
            "AND upload_lease_until IS NOT NULL)",
            name="file_object_upload_lease",
        ),
        CheckConstraint(
            "(state = 'scanning') = (scan_token_digest IS NOT NULL "
            "AND scan_lease_until IS NOT NULL)",
            name="file_object_scan_lease",
        ),
        CheckConstraint(
            "(upload_token_digest IS NULL) = (upload_lease_until IS NULL) AND "
            "(scan_token_digest IS NULL) = (scan_lease_until IS NULL)",
            name="file_object_complete_leases",
        ),
        Index(
            "ix_file_object_context", "organization_id", "owner_person_id", "purpose", "resource_id"
        ),
        Index("ix_file_object_scan_queue", "state", "scan_retry_at", "scan_lease_until", "id"),
        Index("ix_file_object_retention", "state", "retention_until", "id"),
    )
