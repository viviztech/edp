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
    UniqueConstraint,
    text,
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
        UniqueConstraint("id", "center_id", "organization_id", name="uq_cohort_center_scope"),
        CheckConstraint(
            "state IN ('planned','active','completed','cancelled')", name="cohort_state"
        ),
        CheckConstraint("ends_on >= starts_on", name="cohort_dates"),
        CheckConstraint("capacity IS NULL OR capacity > 0", name="cohort_capacity"),
        CheckConstraint("version > 0", name="cohort_version"),
        Index("ix_cohort_program_state", "program_id", "state", "id"),
        Index("ix_cohort_center_state", "center_id", "state", "id"),
    )


class ProgramStaffAssignment(Record, Base):
    __tablename__ = "program_staff_assignments"
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    center_id: Mapped[UUID] = mapped_column(index=True)
    cohort_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    state: Mapped[str] = mapped_column(String(16), default="active")
    version: Mapped[int] = mapped_column(Integer, default=1)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (
        ForeignKeyConstraint(
            ["center_id", "organization_id"],
            ["training_centers.id", "training_centers.organization_id"],
            name="fk_program_staff_center_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["cohort_id", "center_id", "organization_id"],
            ["cohorts.id", "cohorts.center_id", "cohorts.organization_id"],
            name="fk_program_staff_cohort_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("id", "organization_id"),
        CheckConstraint("state IN ('active','revoked')", name="program_staff_state"),
        CheckConstraint("version > 0", name="program_staff_version"),
        CheckConstraint(
            "(state = 'active' AND revoked_at IS NULL) OR "
            "(state = 'revoked' AND revoked_at IS NOT NULL)",
            name="program_staff_revocation_evidence",
        ),
        Index(
            "uq_program_staff_active_center",
            "organization_id",
            "user_id",
            "center_id",
            unique=True,
            postgresql_where=text("cohort_id IS NULL AND state = 'active'"),
        ),
        Index(
            "uq_program_staff_active_cohort",
            "organization_id",
            "user_id",
            "cohort_id",
            unique=True,
            postgresql_where=text("cohort_id IS NOT NULL AND state = 'active'"),
        ),
        Index(
            "ix_program_staff_scope",
            "organization_id",
            "center_id",
            "cohort_id",
            "state",
        ),
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


class Participant(Record, Base):
    __tablename__ = "participants"
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    person_id: Mapped[UUID] = mapped_column(
        ForeignKey("people.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[str] = mapped_column(String(16), default="active")
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (
        UniqueConstraint("organization_id", "person_id"),
        UniqueConstraint("id", "organization_id"),
        CheckConstraint(
            "status IN ('active','suspended','completed','withdrawn')", name="participant_status"
        ),
        CheckConstraint("version > 0", name="participant_version"),
        Index("ix_participant_scope_status", "organization_id", "status", "id"),
    )


class Enrollment(Record, Base):
    __tablename__ = "enrollments"
    organization_id: Mapped[UUID] = mapped_column(index=True)
    participant_id: Mapped[UUID] = mapped_column(index=True)
    program_id: Mapped[UUID] = mapped_column(index=True)
    cohort_id: Mapped[UUID] = mapped_column(index=True)
    application_id: Mapped[UUID] = mapped_column(index=True)
    status: Mapped[str] = mapped_column(String(16), default="active")
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (
        ForeignKeyConstraint(
            ["participant_id", "organization_id"],
            ["participants.id", "participants.organization_id"],
            name="fk_enrollment_participant_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["program_id", "organization_id"],
            ["programs.id", "programs.organization_id"],
            name="fk_enrollment_program_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["cohort_id", "program_id", "organization_id"],
            ["cohorts.id", "cohorts.program_id", "cohorts.organization_id"],
            name="fk_enrollment_cohort_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["application_id", "organization_id"],
            ["applications.id", "applications.organization_id"],
            name="fk_enrollment_application_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("application_id"),
        UniqueConstraint("participant_id", "cohort_id"),
        UniqueConstraint("id", "organization_id"),
        CheckConstraint("status IN ('active','completed','withdrawn')", name="enrollment_status"),
        CheckConstraint("version > 0", name="enrollment_version"),
        Index("ix_enrollment_cohort_status", "cohort_id", "status", "id"),
    )


class ProgramSession(Record, Base):
    __tablename__ = "program_sessions"
    organization_id: Mapped[UUID] = mapped_column(index=True)
    cohort_id: Mapped[UUID] = mapped_column(index=True)
    title_en: Mapped[str] = mapped_column(String(200))
    title_ta: Mapped[str] = mapped_column(String(200))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    mode: Mapped[str] = mapped_column(String(16))
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="scheduled")
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (
        ForeignKeyConstraint(
            ["cohort_id", "organization_id"],
            ["cohorts.id", "cohorts.organization_id"],
            name="fk_program_session_cohort_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("id", "organization_id"),
        CheckConstraint("ends_at > starts_at", name="program_session_time_range"),
        CheckConstraint("mode IN ('in_person','online','hybrid')", name="program_session_mode"),
        CheckConstraint("mode = 'online' OR location IS NOT NULL", name="program_session_location"),
        CheckConstraint(
            "status IN ('scheduled','completed','cancelled')", name="program_session_status"
        ),
        CheckConstraint("version > 0", name="program_session_version"),
        Index("ix_program_session_cohort_time", "cohort_id", "starts_at", "id"),
    )


class ParticipantStatusHistory(Record, Base):
    __tablename__ = "participant_status_history"
    participant_id: Mapped[UUID] = mapped_column(
        ForeignKey("participants.id", ondelete="RESTRICT"), index=True
    )
    actor_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    from_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    to_status: Mapped[str] = mapped_column(String(16))
    participant_version: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(500))
    __table_args__ = (
        UniqueConstraint("participant_id", "participant_version"),
        CheckConstraint(
            "from_status IS NULL OR from_status IN ('active','suspended','completed','withdrawn')",
            name="participant_history_from_status",
        ),
        CheckConstraint(
            "to_status IN ('active','suspended','completed','withdrawn')",
            name="participant_history_to_status",
        ),
        CheckConstraint("participant_version > 0", name="participant_history_version"),
    )


class DomainOutbox(Record, Base):
    __tablename__ = "domain_outbox"
    event_key: Mapped[str] = mapped_column(String(160), unique=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    aggregate_type: Mapped[str] = mapped_column(String(40))
    aggregate_id: Mapped[UUID] = mapped_column(index=True)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    payload: Mapped[str] = mapped_column(String(1000))
    dispatched: Mapped[bool] = mapped_column(Boolean, default=False)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        CheckConstraint(
            "(dispatched = false AND dispatched_at IS NULL) OR "
            "(dispatched = true AND dispatched_at IS NOT NULL)",
            name="domain_outbox_dispatch_state",
        ),
        Index("ix_domain_outbox_pending", "dispatched", "created_at", "id"),
    )
