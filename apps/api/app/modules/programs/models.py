from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
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


class Program(Record, Base):
    __tablename__ = "programs"
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    code: Mapped[str] = mapped_column(String(60))
    name_en: Mapped[str] = mapped_column(String(160))
    name_ta: Mapped[str] = mapped_column(String(160))
    state: Mapped[str] = mapped_column(String(16), default="draft")
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (
        UniqueConstraint("organization_id", "code"),
        UniqueConstraint("id", "organization_id"),
        CheckConstraint("state IN ('draft','active','archived')", name="program_state"),
        CheckConstraint("version > 0", name="program_version"),
        Index("ix_program_scope_state", "organization_id", "state", "id"),
    )


class TrainingCenter(Record, Base):
    __tablename__ = "training_centers"
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    code: Mapped[str] = mapped_column(String(60))
    name_en: Mapped[str] = mapped_column(String(160))
    name_ta: Mapped[str] = mapped_column(String(160))
    locality: Mapped[str] = mapped_column(String(160))
    state: Mapped[str] = mapped_column(String(16), default="active")
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (
        UniqueConstraint("organization_id", "code"),
        UniqueConstraint("id", "organization_id"),
        CheckConstraint("state IN ('active','inactive')", name="training_center_state"),
        CheckConstraint("version > 0", name="training_center_version"),
        Index("ix_training_center_scope_state", "organization_id", "state", "id"),
    )


class Cohort(Record, Base):
    __tablename__ = "cohorts"
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    program_id: Mapped[UUID] = mapped_column(index=True)
    center_id: Mapped[UUID] = mapped_column(index=True)
    code: Mapped[str] = mapped_column(String(60))
    name_en: Mapped[str] = mapped_column(String(160))
    name_ta: Mapped[str] = mapped_column(String(160))
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date] = mapped_column(Date)
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    state: Mapped[str] = mapped_column(String(16), default="planned")
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (
        ForeignKeyConstraint(
            ["program_id", "organization_id"],
            ["programs.id", "programs.organization_id"],
            name="fk_cohort_program_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["center_id", "organization_id"],
            ["training_centers.id", "training_centers.organization_id"],
            name="fk_cohort_center_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("organization_id", "code"),
        UniqueConstraint("id", "organization_id"),
        UniqueConstraint("id", "program_id", "organization_id"),
        CheckConstraint(
            "state IN ('planned','active','completed','cancelled')", name="cohort_state"
        ),
        CheckConstraint("ends_on >= starts_on", name="cohort_dates"),
        CheckConstraint("capacity IS NULL OR capacity > 0", name="cohort_capacity"),
        CheckConstraint("version > 0", name="cohort_version"),
        Index("ix_cohort_program_state", "program_id", "state", "id"),
        Index("ix_cohort_center_state", "center_id", "state", "id"),
    )


class ApplicationCycle(Record, Base):
    __tablename__ = "application_cycles"
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    program_id: Mapped[UUID] = mapped_column(index=True)
    cohort_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    form_id: Mapped[UUID] = mapped_column(index=True)
    code: Mapped[str] = mapped_column(String(60))
    name_en: Mapped[str] = mapped_column(String(160))
    name_ta: Mapped[str] = mapped_column(String(160))
    opens_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    closes_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    state: Mapped[str] = mapped_column(String(16), default="draft")
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (
        ForeignKeyConstraint(
            ["program_id", "organization_id"],
            ["programs.id", "programs.organization_id"],
            name="fk_application_cycle_program_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["cohort_id", "program_id", "organization_id"],
            ["cohorts.id", "cohorts.program_id", "cohorts.organization_id"],
            name="fk_application_cycle_cohort_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["form_id", "organization_id"],
            ["application_forms.id", "application_forms.organization_id"],
            name="fk_application_cycle_form_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("organization_id", "code"),
        UniqueConstraint("id", "organization_id"),
        UniqueConstraint(
            "id", "form_id", "organization_id", name="uq_application_cycle_form_scope"
        ),
        CheckConstraint(
            "state IN ('draft','open','closed','cancelled')", name="application_cycle_state"
        ),
        CheckConstraint("closes_at > opens_at", name="application_cycle_dates"),
        CheckConstraint("version > 0", name="application_cycle_version"),
        Index("ix_application_cycle_program_state", "program_id", "state", "id"),
    )
