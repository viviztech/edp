from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
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


class FollowUpPolicy(Record, Base):
    __tablename__ = "business_follow_up_policies"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), unique=True, index=True
    )
    day_offsets: Mapped[list[int]] = mapped_column(JSONB)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)

    __table_args__ = (CheckConstraint("version > 0", name="business_follow_up_policy_version"),)


class BusinessProfile(Record, Base):
    __tablename__ = "business_profiles"

    organization_id: Mapped[UUID] = mapped_column(index=True)
    enrollment_id: Mapped[UUID] = mapped_column(index=True)
    name: Mapped[str] = mapped_column(String(160))
    sector: Mapped[str] = mapped_column(String(120))
    products_services: Mapped[str] = mapped_column(Text)
    stage: Mapped[str] = mapped_column(String(24))
    registration_info: Mapped[str | None] = mapped_column(String(240), nullable=True)
    started_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    team_size: Mapped[int] = mapped_column(Integer, default=1)
    investment_band: Mapped[str] = mapped_column(String(24))
    funding_status: Mapped[str] = mapped_column(String(24))
    revenue_band: Mapped[str] = mapped_column(String(24))
    support_needs: Mapped[str | None] = mapped_column(Text, nullable=True)
    public_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)
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
        CheckConstraint("version > 0", name="business_profile_version"),
        CheckConstraint(
            "team_size >= 0 AND team_size <= 100000", name="business_profile_team_size"
        ),
        CheckConstraint(
            "stage IN ('idea','starting','operating','paused','closed')",
            name="business_profile_stage",
        ),
        CheckConstraint(
            "funding_status IN ('none','seeking','applied','approved','disbursed')",
            name="business_profile_funding_status",
        ),
    )


class BusinessProfileRevision(Record, Base):
    __tablename__ = "business_profile_revisions"

    organization_id: Mapped[UUID] = mapped_column(index=True)
    profile_id: Mapped[UUID] = mapped_column(index=True)
    version: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict[str, object]] = mapped_column(JSONB)
    author_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))

    __table_args__ = (
        ForeignKeyConstraint(
            ["profile_id", "organization_id"],
            ["business_profiles.id", "business_profiles.organization_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("profile_id", "version"),
        CheckConstraint("version > 0", name="business_profile_revision_version"),
    )


class BusinessFollowUp(Record, Base):
    __tablename__ = "business_follow_ups"

    organization_id: Mapped[UUID] = mapped_column(index=True)
    profile_id: Mapped[UUID] = mapped_column(index=True)
    offset_days: Mapped[int] = mapped_column(Integer)
    due_on: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["profile_id", "organization_id"],
            ["business_profiles.id", "business_profiles.organization_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("profile_id", "offset_days"),
        UniqueConstraint("id", "organization_id"),
        CheckConstraint("offset_days > 0", name="business_follow_up_offset"),
        CheckConstraint("status IN ('pending','completed')", name="business_follow_up_status"),
    )


class BusinessOutcomeSnapshot(Record, Base):
    __tablename__ = "business_outcome_snapshots"

    organization_id: Mapped[UUID] = mapped_column(index=True)
    follow_up_id: Mapped[UUID] = mapped_column(index=True)
    author_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    reported_on: Mapped[date] = mapped_column(Date)
    business_started: Mapped[bool] = mapped_column(Boolean)
    business_active: Mapped[bool] = mapped_column(Boolean)
    jobs_created: Mapped[int] = mapped_column(Integer)
    funding_band: Mapped[str] = mapped_column(String(24))
    revenue_band: Mapped[str] = mapped_column(String(24))
    challenges: Mapped[str | None] = mapped_column(Text, nullable=True)
    support_requested: Mapped[str | None] = mapped_column(Text, nullable=True)
    mentor_interventions: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcomes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["follow_up_id", "organization_id"],
            ["business_follow_ups.id", "business_follow_ups.organization_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("follow_up_id"),
        CheckConstraint(
            "jobs_created >= 0 AND jobs_created <= 100000", name="business_outcome_jobs"
        ),
    )
