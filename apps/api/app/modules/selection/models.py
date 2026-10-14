from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.identity.models import Record, now


class SelectionCycle(Record, Base):
    __tablename__ = "selection_cycles"
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    application_cycle_id: Mapped[UUID] = mapped_column(index=True)
    code: Mapped[str] = mapped_column(String(60))
    name_en: Mapped[str] = mapped_column(String(160))
    name_ta: Mapped[str] = mapped_column(String(160))
    state: Mapped[str] = mapped_column(String(16), default="draft")
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (
        ForeignKeyConstraint(
            ["application_cycle_id", "organization_id"],
            ["application_cycles.id", "application_cycles.organization_id"],
            name="fk_selection_cycle_application_cycle_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("organization_id", "code"),
        UniqueConstraint("application_cycle_id"),
        UniqueConstraint("id", "organization_id"),
        CheckConstraint("state IN ('draft','active','closed')", name="selection_cycle_state"),
        CheckConstraint("version > 0", name="selection_cycle_version"),
        Index("ix_selection_cycle_scope_state", "organization_id", "state", "id"),
    )


class SelectionRubric(Record, Base):
    __tablename__ = "selection_rubrics"
    organization_id: Mapped[UUID] = mapped_column(index=True)
    selection_cycle_id: Mapped[UUID] = mapped_column(index=True)
    version_number: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(16), default="draft")
    edit_version: Mapped[int] = mapped_column(Integer, default=1)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (
        ForeignKeyConstraint(
            ["selection_cycle_id", "organization_id"],
            ["selection_cycles.id", "selection_cycles.organization_id"],
            name="fk_selection_rubric_cycle_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("selection_cycle_id", "version_number"),
        UniqueConstraint("id", "organization_id"),
        UniqueConstraint("id", "selection_cycle_id", "organization_id"),
        CheckConstraint("state IN ('draft','published','retired')", name="selection_rubric_state"),
        CheckConstraint("version_number > 0", name="selection_rubric_version_number"),
        CheckConstraint("edit_version > 0", name="selection_rubric_edit_version"),
        CheckConstraint(
            "(state = 'draft' AND published_at IS NULL) OR "
            "(state IN ('published','retired') AND published_at IS NOT NULL)",
            name="selection_rubric_publication",
        ),
        Index("ix_selection_rubric_cycle_state", "selection_cycle_id", "state", "id"),
        Index(
            "uq_selection_rubric_draft",
            "selection_cycle_id",
            unique=True,
            postgresql_where=text("state = 'draft'"),
        ),
        Index(
            "uq_selection_rubric_published",
            "selection_cycle_id",
            unique=True,
            postgresql_where=text("state = 'published'"),
        ),
    )


class SelectionCriterion(Record, Base):
    __tablename__ = "selection_criteria"
    rubric_id: Mapped[UUID] = mapped_column(
        ForeignKey("selection_rubrics.id", ondelete="RESTRICT"), index=True
    )
    criterion_key: Mapped[str] = mapped_column(String(80))
    label_en: Mapped[str] = mapped_column(String(300))
    label_ta: Mapped[str] = mapped_column(String(300))
    guidance_en: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    guidance_ta: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    weight: Mapped[int] = mapped_column(Integer)
    minimum_score: Mapped[int] = mapped_column(Integer, default=0)
    maximum_score: Mapped[int] = mapped_column(Integer)
    position: Mapped[int] = mapped_column(Integer)
    required: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (
        UniqueConstraint("rubric_id", "criterion_key"),
        UniqueConstraint("id", "rubric_id"),
        UniqueConstraint("rubric_id", "position"),
        CheckConstraint("weight > 0 AND weight <= 100", name="selection_criterion_weight"),
        CheckConstraint(
            "minimum_score >= 0 AND maximum_score > minimum_score AND maximum_score <= 100",
            name="selection_criterion_score_range",
        ),
        CheckConstraint("position >= 0", name="selection_criterion_position"),
    )


class ReviewAssignment(Record, Base):
    __tablename__ = "review_assignments"
    organization_id: Mapped[UUID] = mapped_column(index=True)
    selection_cycle_id: Mapped[UUID] = mapped_column(index=True)
    rubric_id: Mapped[UUID] = mapped_column(index=True)
    application_id: Mapped[UUID] = mapped_column(index=True)
    reviewer_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[str] = mapped_column(String(16), default="assigned")
    conflict_status: Mapped[str] = mapped_column(String(16), default="pending")
    conflict_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    internal_comment: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    weighted_score: Mapped[Decimal | None] = mapped_column(Numeric(7, 4), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    moderation_status: Mapped[str] = mapped_column(String(16), default="included")
    moderation_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    moderated_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    moderated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (
        ForeignKeyConstraint(
            ["selection_cycle_id", "organization_id"],
            ["selection_cycles.id", "selection_cycles.organization_id"],
            name="fk_review_assignment_cycle_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["rubric_id", "selection_cycle_id", "organization_id"],
            [
                "selection_rubrics.id",
                "selection_rubrics.selection_cycle_id",
                "selection_rubrics.organization_id",
            ],
            name="fk_review_assignment_rubric_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["application_id", "organization_id"],
            ["applications.id", "applications.organization_id"],
            name="fk_review_assignment_application_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("application_id", "reviewer_user_id"),
        UniqueConstraint("id", "rubric_id"),
        CheckConstraint(
            "status IN ('assigned','in_review','completed')", name="review_assignment_status"
        ),
        CheckConstraint(
            "conflict_status IN ('pending','clear','conflict')",
            name="review_assignment_conflict_status",
        ),
        CheckConstraint(
            "(conflict_status = 'conflict' AND conflict_note IS NOT NULL) OR "
            "(conflict_status <> 'conflict' AND conflict_note IS NULL)",
            name="review_assignment_conflict_note",
        ),
        CheckConstraint("version > 0", name="review_assignment_version"),
        CheckConstraint(
            "moderation_status IN ('included','excluded')",
            name="review_assignment_moderation_status",
        ),
        CheckConstraint(
            "(moderation_status = 'included') OR moderation_reason IS NOT NULL",
            name="review_assignment_moderation_reason",
        ),
        CheckConstraint(
            "(status = 'completed' AND weighted_score IS NOT NULL "
            "AND submitted_at IS NOT NULL) OR (status <> 'completed' "
            "AND weighted_score IS NULL AND submitted_at IS NULL)",
            name="review_assignment_completion",
        ),
        Index("ix_review_assignment_reviewer", "reviewer_user_id", "status", "id"),
    )


class ApplicationScore(Record, Base):
    __tablename__ = "application_scores"
    assignment_id: Mapped[UUID] = mapped_column(index=True)
    rubric_id: Mapped[UUID] = mapped_column(index=True)
    criterion_id: Mapped[UUID] = mapped_column(index=True)
    score: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    __table_args__ = (
        ForeignKeyConstraint(
            ["assignment_id", "rubric_id"],
            ["review_assignments.id", "review_assignments.rubric_id"],
            name="fk_application_score_assignment_rubric",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["criterion_id", "rubric_id"],
            ["selection_criteria.id", "selection_criteria.rubric_id"],
            name="fk_application_score_criterion_rubric",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("assignment_id", "criterion_id"),
        CheckConstraint("score >= 0 AND score <= 100", name="application_score_range"),
    )


class Interview(Record, Base):
    __tablename__ = "interviews"
    organization_id: Mapped[UUID] = mapped_column(index=True)
    selection_cycle_id: Mapped[UUID] = mapped_column(index=True)
    application_id: Mapped[UUID] = mapped_column(index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    mode: Mapped[str] = mapped_column(String(16))
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="scheduled")
    average_score: Mapped[Decimal | None] = mapped_column(Numeric(7, 4), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (
        ForeignKeyConstraint(
            ["selection_cycle_id", "organization_id"],
            ["selection_cycles.id", "selection_cycles.organization_id"],
            name="fk_interview_cycle_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["application_id", "organization_id"],
            ["applications.id", "applications.organization_id"],
            name="fk_interview_application_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("application_id"),
        UniqueConstraint("id", "organization_id"),
        CheckConstraint("ends_at > starts_at", name="interview_time_range"),
        CheckConstraint("mode IN ('online','in_person')", name="interview_mode"),
        CheckConstraint("status IN ('scheduled','completed')", name="interview_status"),
        CheckConstraint("(mode = 'online') OR location IS NOT NULL", name="interview_location"),
        CheckConstraint(
            "(status = 'scheduled' AND average_score IS NULL AND completed_at IS NULL) OR "
            "(status = 'completed' AND average_score IS NOT NULL AND completed_at IS NOT NULL)",
            name="interview_completion",
        ),
        CheckConstraint("version > 0", name="interview_version"),
        Index("ix_interview_cycle_status", "selection_cycle_id", "status", "starts_at"),
    )


class InterviewPanelMember(Record, Base):
    __tablename__ = "interview_panel_members"
    interview_id: Mapped[UUID] = mapped_column(
        ForeignKey("interviews.id", ondelete="RESTRICT"), index=True
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    comment: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = (
        UniqueConstraint("interview_id", "user_id"),
        CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 100)", name="interview_panel_score"
        ),
        CheckConstraint(
            "(score IS NULL AND submitted_at IS NULL) OR "
            "(score IS NOT NULL AND submitted_at IS NOT NULL)",
            name="interview_panel_submission",
        ),
        CheckConstraint("version > 0", name="interview_panel_version"),
    )


class SelectionDecision(Record, Base):
    __tablename__ = "selection_decisions"
    organization_id: Mapped[UUID] = mapped_column(index=True)
    selection_cycle_id: Mapped[UUID] = mapped_column(index=True)
    application_id: Mapped[UUID] = mapped_column(index=True)
    actor_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    from_state: Mapped[str] = mapped_column(String(24))
    to_state: Mapped[str] = mapped_column(String(24))
    reason: Mapped[str] = mapped_column(String(1000))
    is_override: Mapped[bool] = mapped_column(Boolean, default=False)
    aggregate_score_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)
    interview_score_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)
    application_version: Mapped[int] = mapped_column(Integer)
    __table_args__ = (
        ForeignKeyConstraint(
            ["selection_cycle_id", "organization_id"],
            ["selection_cycles.id", "selection_cycles.organization_id"],
            name="fk_selection_decision_cycle_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["application_id", "organization_id"],
            ["applications.id", "applications.organization_id"],
            name="fk_selection_decision_application_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("application_id", "application_version"),
        CheckConstraint(
            "from_state IN ('under_review','shortlisted','interview_scheduled',"
            "'selected','waitlisted','rejected')",
            name="selection_decision_from_state",
        ),
        CheckConstraint(
            "to_state IN ('shortlisted','selected','waitlisted','rejected')",
            name="selection_decision_to_state",
        ),
        CheckConstraint("application_version > 0", name="selection_decision_version"),
        Index(
            "ix_selection_decision_cycle_application",
            "selection_cycle_id",
            "application_id",
            "created_at",
        ),
    )
