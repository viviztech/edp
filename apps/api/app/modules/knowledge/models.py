from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.identity.models import Record, now


class KnowledgeItem(Record, Base):
    __tablename__ = "knowledge_items"
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    kind: Mapped[str] = mapped_column(String(16))
    locale: Mapped[str] = mapped_column(String(2))
    slug: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(200))
    provider: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    eligibility: Mapped[str] = mapped_column(Text)
    benefits: Mapped[str] = mapped_column(Text, default="")
    sector: Mapped[str] = mapped_column(String(120))
    geography: Mapped[str] = mapped_column(String(120))
    application_process: Mapped[str] = mapped_column(Text)
    documents: Mapped[list[str]] = mapped_column(JSONB, default=list)
    official_url: Mapped[str] = mapped_column(String(2000))
    opens_on: Mapped[date | None] = mapped_column(Date)
    closes_on: Mapped[date | None] = mapped_column(Date)
    last_verified_at: Mapped[date] = mapped_column(Date)
    visibility: Mapped[str] = mapped_column(String(16), default="public")
    contact: Mapped[str] = mapped_column(String(1000), default="")
    funding_amount_min: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    funding_amount_max: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    state: Mapped[str] = mapped_column(String(16), default="draft")
    version: Mapped[int] = mapped_column(Integer, default=1)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (
        UniqueConstraint("id", "organization_id"),
        UniqueConstraint("organization_id", "kind", "slug", "locale"),
        CheckConstraint("kind IN ('scheme','funding','opportunity')", name="knowledge_kind"),
        CheckConstraint("locale IN ('en','ta')", name="knowledge_locale"),
        CheckConstraint("state IN ('draft','published','archived')", name="knowledge_state"),
        CheckConstraint("visibility IN ('public','participants')", name="knowledge_visibility"),
        CheckConstraint("version > 0", name="knowledge_version"),
        CheckConstraint("currency = 'INR'", name="knowledge_currency"),
        CheckConstraint(
            "opens_on IS NULL OR closes_on IS NULL OR opens_on <= closes_on", name="knowledge_dates"
        ),
        CheckConstraint(
            "(funding_amount_min IS NULL OR funding_amount_min >= 0) AND "
            "(funding_amount_max IS NULL OR funding_amount_max >= 0) AND "
            "(funding_amount_min IS NULL OR funding_amount_max IS NULL OR "
            "funding_amount_min <= funding_amount_max) "
            "AND (kind = 'funding' OR (funding_amount_min IS NULL AND funding_amount_max IS NULL))",
            name="knowledge_funding_range",
        ),
        CheckConstraint(
            "(state = 'published') = (published_at IS NOT NULL)", name="knowledge_published_at"
        ),
        Index("ix_knowledge_catalog", "organization_id", "locale", "state", "visibility", "id"),
    )


class KnowledgeTag(Base):
    __tablename__ = "knowledge_item_tags"
    item_id: Mapped[UUID] = mapped_column(primary_key=True)
    organization_id: Mapped[UUID] = mapped_column()
    label: Mapped[str] = mapped_column(String(200), primary_key=True)
    __table_args__ = (
        ForeignKeyConstraint(
            ["item_id", "organization_id"],
            ["knowledge_items.id", "knowledge_items.organization_id"],
            ondelete="RESTRICT",
        ),
        Index("ix_knowledge_tag_filter", "organization_id", "label", "item_id"),
    )


class KnowledgeRevision(Record, Base):
    __tablename__ = "knowledge_revisions"
    organization_id: Mapped[UUID] = mapped_column()
    item_id: Mapped[UUID] = mapped_column()
    version: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str] = mapped_column(String(500))
    snapshot: Mapped[dict[str, object]] = mapped_column(JSONB)
    actor_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    __table_args__ = (
        ForeignKeyConstraint(
            ["item_id", "organization_id"],
            ["knowledge_items.id", "knowledge_items.organization_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("item_id", "version"),
        CheckConstraint("version > 0", name="knowledge_revision_version"),
    )


class KnowledgeSaved(Record, Base):
    __tablename__ = "knowledge_saved"
    organization_id: Mapped[UUID] = mapped_column()
    participant_id: Mapped[UUID] = mapped_column()
    item_id: Mapped[UUID] = mapped_column()
    __table_args__ = (
        ForeignKeyConstraint(
            ["participant_id", "organization_id"],
            ["participants.id", "participants.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["item_id", "organization_id"],
            ["knowledge_items.id", "knowledge_items.organization_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("participant_id", "item_id"),
        Index("ix_knowledge_saved_owner", "organization_id", "participant_id", "id"),
    )


class KnowledgeInterest(Record, Base):
    __tablename__ = "knowledge_interests"
    organization_id: Mapped[UUID] = mapped_column()
    participant_id: Mapped[UUID] = mapped_column()
    item_id: Mapped[UUID] = mapped_column()
    item_title: Mapped[str] = mapped_column(String(200))
    locale: Mapped[str] = mapped_column(String(2))
    __table_args__ = (
        ForeignKeyConstraint(
            ["participant_id", "organization_id"],
            ["participants.id", "participants.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["item_id", "organization_id"],
            ["knowledge_items.id", "knowledge_items.organization_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("participant_id", "item_id"),
        Index("ix_knowledge_interest_owner", "organization_id", "participant_id", "id"),
    )


class FundingCase(Record, Base):
    __tablename__ = "funding_cases"
    organization_id: Mapped[UUID] = mapped_column()
    participant_id: Mapped[UUID] = mapped_column()
    item_id: Mapped[UUID] = mapped_column()
    item_title: Mapped[str] = mapped_column(String(200))
    locale: Mapped[str] = mapped_column(String(2))
    source: Mapped[dict[str, object]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(24), default="interested")
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (
        ForeignKeyConstraint(
            ["participant_id", "organization_id"],
            ["participants.id", "participants.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["item_id", "organization_id"],
            ["knowledge_items.id", "knowledge_items.organization_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("participant_id", "item_id"),
        UniqueConstraint("id", "organization_id"),
        CheckConstraint("version > 0", name="funding_case_version"),
        CheckConstraint(
            "status IN ('interested','eligibility_check','document_preparation',"
            "'applied','under_review','approved','rejected','disbursed')",
            name="funding_case_status",
        ),
        Index("ix_funding_case_queue", "organization_id", "status", "id"),
    )


class FundingHistory(Record, Base):
    __tablename__ = "funding_history"
    organization_id: Mapped[UUID] = mapped_column()
    case_id: Mapped[UUID] = mapped_column()
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(24))
    reason: Mapped[str] = mapped_column(String(500))
    actor_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    __table_args__ = (
        ForeignKeyConstraint(
            ["case_id", "organization_id"],
            ["funding_cases.id", "funding_cases.organization_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("case_id", "version"),
        CheckConstraint("version > 0", name="funding_history_version"),
    )
