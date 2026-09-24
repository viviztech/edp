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
