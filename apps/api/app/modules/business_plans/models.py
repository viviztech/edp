from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.identity.models import Record, now


class BusinessPlan(Record, Base):
    __tablename__ = "business_plans"

    organization_id: Mapped[UUID] = mapped_column(index=True)
    enrollment_id: Mapped[UUID] = mapped_column(index=True)
    status: Mapped[str] = mapped_column(String(24), default="draft")
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)

    __table_args__ = (
        ForeignKeyConstraint(
            ["enrollment_id", "organization_id"],
            ["enrollments.id", "enrollments.organization_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("enrollment_id"),
        UniqueConstraint("id", "organization_id"),
        CheckConstraint(
            "status IN ('draft','submitted','changes_requested','approved')",
            name="business_plan_status",
        ),
        CheckConstraint("version > 0", name="business_plan_version"),
    )


class BusinessPlanRevision(Record, Base):
    __tablename__ = "business_plan_revisions"

    organization_id: Mapped[UUID] = mapped_column(index=True)
    plan_id: Mapped[UUID] = mapped_column(index=True)
    version: Mapped[int] = mapped_column(Integer)
    section_code: Mapped[str] = mapped_column(String(40))
    body: Mapped[str] = mapped_column(Text)
    author_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))

    __table_args__ = (
        ForeignKeyConstraint(
            ["plan_id", "organization_id"],
            ["business_plans.id", "business_plans.organization_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("plan_id", "version"),
        CheckConstraint("version > 1", name="business_plan_revision_version"),
        CheckConstraint("char_length(body) <= 10000", name="business_plan_revision_body_length"),
    )


class BusinessPlanSubmission(Record, Base):
    __tablename__ = "business_plan_submissions"

    organization_id: Mapped[UUID] = mapped_column(index=True)
    plan_id: Mapped[UUID] = mapped_column(index=True)
    number: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict[str, str]] = mapped_column(JSONB)
    submitted_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))

    __table_args__ = (
        ForeignKeyConstraint(
            ["plan_id", "organization_id"],
            ["business_plans.id", "business_plans.organization_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("plan_id", "number"),
        UniqueConstraint("id", "organization_id"),
        CheckConstraint("number > 0", name="business_plan_submission_number"),
    )


class BusinessPlanReview(Record, Base):
    __tablename__ = "business_plan_reviews"

    organization_id: Mapped[UUID] = mapped_column(index=True)
    submission_id: Mapped[UUID] = mapped_column(index=True)
    reviewer_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    decision: Mapped[str] = mapped_column(String(24))
    comments: Mapped[dict[str, str]] = mapped_column(JSONB)
    reason: Mapped[str] = mapped_column(String(500))

    __table_args__ = (
        ForeignKeyConstraint(
            ["submission_id", "organization_id"],
            ["business_plan_submissions.id", "business_plan_submissions.organization_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("submission_id"),
        CheckConstraint(
            "decision IN ('changes_requested','approved')",
            name="business_plan_review_decision",
        ),
    )
