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


class Application(Record, Base):
    __tablename__ = "applications"
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    person_id: Mapped[UUID] = mapped_column(
        ForeignKey("people.id", ondelete="RESTRICT"), index=True
    )
    form_id: Mapped[UUID] = mapped_column(ForeignKey("application_forms.id", ondelete="RESTRICT"))
    state: Mapped[str] = mapped_column(String(20), default="draft")
    version: Mapped[int] = mapped_column(Integer, default=1)
    current_revision_id: Mapped[UUID | None] = mapped_column(nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (
        UniqueConstraint("person_id", "form_id"),
        UniqueConstraint("id", "form_id"),
        CheckConstraint("state = 'draft'", name="application_draft_only"),
        CheckConstraint("version > 0", name="application_version"),
        ForeignKeyConstraint(
            ["current_revision_id", "id"],
            ["application_revisions.id", "application_revisions.application_id"],
            name="fk_application_current_revision",
            use_alter=True,
        ),
        Index("ix_application_owner", "person_id", "organization_id", "id"),
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
