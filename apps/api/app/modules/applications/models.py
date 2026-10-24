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
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.identity.models import Record, now


class ApplicationForm(Record, Base):
    __tablename__ = "application_forms"
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    version: Mapped[int] = mapped_column(Integer)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    state: Mapped[str] = mapped_column(String(16), default="draft")
    title_en: Mapped[str] = mapped_column(String(160))
    title_ta: Mapped[str] = mapped_column(String(160))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    __table_args__ = (
        UniqueConstraint("organization_id", "version"),
        UniqueConstraint("id", "organization_id", name="uq_application_form_scope"),
        CheckConstraint("version > 0", name="application_form_version"),
        CheckConstraint("revision > 0", name="application_form_revision"),
        CheckConstraint("state IN ('draft','published','retired')", name="application_form_state"),
        Index("ix_application_form_active", "organization_id", "state", "version"),
        Index(
            "uq_application_form_draft",
            "organization_id",
            unique=True,
            postgresql_where=text("state = 'draft'"),
        ),
    )


class ApplicationField(Record, Base):
    __tablename__ = "application_fields"
    form_id: Mapped[UUID] = mapped_column(
        ForeignKey("application_forms.id", ondelete="RESTRICT"), index=True
    )
    field_key: Mapped[str] = mapped_column(String(80))
    section_key: Mapped[str] = mapped_column(String(80))
    label_en: Mapped[str] = mapped_column(String(200))
    label_ta: Mapped[str] = mapped_column(String(200))
    field_type: Mapped[str] = mapped_column(String(16))
    required: Mapped[bool] = mapped_column(default=False)
    position: Mapped[int] = mapped_column(Integer)
    __table_args__ = (
        UniqueConstraint("form_id", "field_key"),
        UniqueConstraint("form_id", "position"),
        CheckConstraint(
            "field_type IN ('text','textarea','number','date','boolean')",
            name="application_field_type",
        ),
        CheckConstraint("position >= 0", name="application_field_position"),
    )


class ApplicationAcknowledgementDefinition(Record, Base):
    __tablename__ = "application_acknowledgement_definitions"
    form_id: Mapped[UUID] = mapped_column(
        ForeignKey("application_forms.id", ondelete="RESTRICT"), index=True
    )
    acknowledgement_key: Mapped[str] = mapped_column(String(80))
    kind: Mapped[str] = mapped_column(String(16))
    label_en: Mapped[str] = mapped_column(String(1000))
    label_ta: Mapped[str] = mapped_column(String(1000))
    required: Mapped[bool] = mapped_column(default=True)
    position: Mapped[int] = mapped_column(Integer)
    __table_args__ = (
        UniqueConstraint("form_id", "acknowledgement_key"),
        UniqueConstraint("form_id", "position"),
        UniqueConstraint("id", "form_id"),
        CheckConstraint("kind IN ('declaration','consent')", name="application_ack_kind"),
        CheckConstraint("position >= 0", name="application_ack_position"),
    )


class Application(Record, Base):
    __tablename__ = "applications"
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    person_id: Mapped[UUID] = mapped_column(
        ForeignKey("people.id", ondelete="RESTRICT"), index=True
    )
    form_id: Mapped[UUID] = mapped_column(ForeignKey("application_forms.id", ondelete="RESTRICT"))
    cycle_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    state: Mapped[str] = mapped_column(String(20), default="draft")
    version: Mapped[int] = mapped_column(Integer, default=1)
    current_revision_id: Mapped[UUID | None] = mapped_column(nullable=True)
    application_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (
        UniqueConstraint("id", "form_id"),
        UniqueConstraint("id", "organization_id", name="uq_application_organization_scope"),
        UniqueConstraint(
            "id",
            "form_id",
            "organization_id",
            "person_id",
            name="uq_application_document_owner_scope",
        ),
        UniqueConstraint("person_id", "cycle_id", name="uq_application_person_cycle"),
        CheckConstraint(
            "state IN ('draft','submitted','under_review','shortlisted',"
            "'interview_scheduled','selected','waitlisted','rejected','enrolled')",
            name="application_state",
        ),
        CheckConstraint("version > 0", name="application_version"),
        CheckConstraint(
            "(state = 'draft' AND application_number IS NULL AND submitted_at IS NULL) OR "
            "(state IN ('submitted','under_review','shortlisted',"
            "'interview_scheduled','selected','waitlisted','rejected','enrolled') "
            "AND cycle_id IS NOT NULL "
            "AND application_number IS NOT NULL AND submitted_at IS NOT NULL)",
            name="application_submission_evidence",
        ),
        ForeignKeyConstraint(
            ["current_revision_id", "id"],
            ["application_revisions.id", "application_revisions.application_id"],
            name="fk_application_current_revision",
            use_alter=True,
        ),
        ForeignKeyConstraint(
            ["cycle_id", "form_id", "organization_id"],
            [
                "application_cycles.id",
                "application_cycles.form_id",
                "application_cycles.organization_id",
            ],
            name="fk_application_cycle_scope",
            ondelete="RESTRICT",
        ),
        Index("ix_applications_application_number", "application_number", unique=True),
        Index("ix_application_owner", "person_id", "organization_id", "state", "id"),
    )


class ApplicationRevision(Record, Base):
    __tablename__ = "application_revisions"
    application_id: Mapped[UUID] = mapped_column(index=True)
    form_id: Mapped[UUID] = mapped_column(ForeignKey("application_forms.id", ondelete="RESTRICT"))
    revision: Mapped[int] = mapped_column(Integer)
    __table_args__ = (
        ForeignKeyConstraint(
            ["application_id", "form_id"],
            ["applications.id", "applications.form_id"],
            name="fk_application_revision_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("application_id", "revision"),
        UniqueConstraint("id", "application_id"),
        CheckConstraint("revision > 0", name="application_revision_number"),
    )


class ApplicationAnswer(Record, Base):
    __tablename__ = "application_answers"
    revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("application_revisions.id", ondelete="RESTRICT"), index=True
    )
    field_id: Mapped[UUID] = mapped_column(ForeignKey("application_fields.id", ondelete="RESTRICT"))
    value: Mapped[str] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("revision_id", "field_id"),)


class ApplicationAcknowledgement(Record, Base):
    __tablename__ = "application_acknowledgements"
    application_id: Mapped[UUID] = mapped_column(index=True)
    form_id: Mapped[UUID] = mapped_column()
    definition_id: Mapped[UUID] = mapped_column(index=True)
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (
        ForeignKeyConstraint(
            ["application_id", "form_id"],
            ["applications.id", "applications.form_id"],
            name="fk_application_ack_application_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["definition_id", "form_id"],
            [
                "application_acknowledgement_definitions.id",
                "application_acknowledgement_definitions.form_id",
            ],
            name="fk_application_ack_definition_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("application_id", "definition_id"),
    )


class ApplicationStatusHistory(Record, Base):
    __tablename__ = "application_status_history"
    application_id: Mapped[UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="RESTRICT"), index=True
    )
    actor_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    from_state: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_state: Mapped[str] = mapped_column(String(20))
    application_version: Mapped[int] = mapped_column(Integer)
    reason_code: Mapped[str] = mapped_column(String(40))
    __table_args__ = (
        UniqueConstraint("application_id", "application_version"),
        CheckConstraint(
            "from_state IS NULL OR from_state IN "
            "('draft','submitted','under_review','shortlisted',"
            "'interview_scheduled','selected','waitlisted','rejected','enrolled')",
            name="application_history_from_state",
        ),
        CheckConstraint(
            "to_state IN ('draft','submitted','under_review','shortlisted',"
            "'interview_scheduled','selected','waitlisted','rejected','enrolled')",
            name="application_history_to_state",
        ),
        CheckConstraint("application_version > 0", name="application_history_version"),
    )


class DocumentRequirement(Record, Base):
    __tablename__ = "application_document_requirements"
    organization_id: Mapped[UUID] = mapped_column(index=True)
    form_id: Mapped[UUID] = mapped_column(index=True)
    requirement_key: Mapped[str] = mapped_column(String(80))
    label_en: Mapped[str] = mapped_column(String(200))
    label_ta: Mapped[str] = mapped_column(String(200))
    instructions_en: Mapped[str] = mapped_column(String(2000))
    instructions_ta: Mapped[str] = mapped_column(String(2000))
    file_policy_id: Mapped[UUID] = mapped_column()
    purpose: Mapped[str] = mapped_column(String(32), default="application_document")
    min_files: Mapped[int] = mapped_column(Integer)
    max_files: Mapped[int] = mapped_column(Integer)
    position: Mapped[int] = mapped_column(Integer)
    __table_args__ = (
        ForeignKeyConstraint(
            ["form_id", "organization_id"],
            ["application_forms.id", "application_forms.organization_id"],
            name="fk_document_requirement_form_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["file_policy_id", "organization_id", "purpose"],
            ["file_policies.id", "file_policies.organization_id", "file_policies.purpose"],
            name="fk_document_requirement_policy_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("form_id", "requirement_key"),
        UniqueConstraint("form_id", "position"),
        UniqueConstraint(
            "id",
            "form_id",
            "organization_id",
            "file_policy_id",
            name="uq_document_requirement_scope",
        ),
        CheckConstraint("purpose = 'application_document'", name="document_requirement_purpose"),
        CheckConstraint(
            "min_files BETWEEN 0 AND 100 AND max_files BETWEEN 1 AND 100 "
            "AND min_files <= max_files AND position >= 0",
            name="document_requirement_counts",
        ),
        CheckConstraint(
            "requirement_key ~ '^[a-z][a-z0-9_]*$' AND length(trim(label_en)) > 0 "
            "AND length(trim(label_ta)) > 0 AND length(trim(instructions_en)) > 0 "
            "AND length(trim(instructions_ta)) > 0",
            name="document_requirement_text",
        ),
    )


class ApplicationDocument(Record, Base):
    __tablename__ = "application_documents"
    organization_id: Mapped[UUID] = mapped_column(index=True)
    application_id: Mapped[UUID] = mapped_column(index=True)
    form_id: Mapped[UUID] = mapped_column()
    requirement_id: Mapped[UUID] = mapped_column()
    owner_person_id: Mapped[UUID] = mapped_column()
    file_policy_id: Mapped[UUID] = mapped_column()
    file_id: Mapped[UUID] = mapped_column(unique=True)
    purpose: Mapped[str] = mapped_column(String(32), default="application_document")
    client_request_id: Mapped[UUID] = mapped_column()
    request_digest: Mapped[str] = mapped_column(String(64))
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replaced_by_id: Mapped[UUID | None] = mapped_column(nullable=True)
    __table_args__ = (
        ForeignKeyConstraint(
            ["application_id", "form_id", "organization_id", "owner_person_id"],
            [
                "applications.id",
                "applications.form_id",
                "applications.organization_id",
                "applications.person_id",
            ],
            name="fk_application_document_owner_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["requirement_id", "form_id", "organization_id", "file_policy_id"],
            [
                "application_document_requirements.id",
                "application_document_requirements.form_id",
                "application_document_requirements.organization_id",
                "application_document_requirements.file_policy_id",
            ],
            name="fk_application_document_requirement_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["file_id", "organization_id", "owner_person_id", "purpose", "id"],
            [
                "file_objects.id",
                "file_objects.organization_id",
                "file_objects.owner_person_id",
                "file_objects.purpose",
                "file_objects.resource_id",
            ],
            name="fk_application_document_file_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("organization_id", "client_request_id"),
        UniqueConstraint(
            "id", "application_id", "file_id", name="uq_application_document_evidence"
        ),
        UniqueConstraint(
            "id",
            "application_id",
            "requirement_id",
            "organization_id",
            "owner_person_id",
            name="uq_application_document_replacement_scope",
        ),
        ForeignKeyConstraint(
            [
                "replaced_by_id",
                "application_id",
                "requirement_id",
                "organization_id",
                "owner_person_id",
            ],
            [
                "application_documents.id",
                "application_documents.application_id",
                "application_documents.requirement_id",
                "application_documents.organization_id",
                "application_documents.owner_person_id",
            ],
            name="fk_application_document_replacement_scope",
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        CheckConstraint("purpose = 'application_document'", name="application_document_purpose"),
        CheckConstraint(
            "replaced_by_id IS NULL OR (removed_at IS NOT NULL AND replaced_by_id <> id)",
            name="application_document_replacement",
        ),
        CheckConstraint("request_digest ~ '^[0-9a-f]{64}$'", name="application_document_digest"),
        Index("ix_application_document_active", "application_id", "removed_at", "id"),
    )


class ApplicationDocumentEvidence(Record, Base):
    __tablename__ = "application_document_evidence"
    application_id: Mapped[UUID] = mapped_column(index=True)
    document_id: Mapped[UUID] = mapped_column(unique=True)
    file_id: Mapped[UUID] = mapped_column()
    file_version: Mapped[int] = mapped_column(Integer)
    storage_version: Mapped[str] = mapped_column(String(1024))
    byte_size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    frozen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (
        ForeignKeyConstraint(
            ["document_id", "application_id", "file_id"],
            [
                "application_documents.id",
                "application_documents.application_id",
                "application_documents.file_id",
            ],
            name="fk_application_document_evidence_scope",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "file_version > 0 AND byte_size > 0 AND length(storage_version) > 0 "
            "AND sha256 ~ '^[0-9a-f]{64}$'",
            name="application_document_evidence_values",
        ),
    )
