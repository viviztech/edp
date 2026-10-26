from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKeyConstraint,
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


def scope_constraints(prefix: str) -> tuple[ForeignKeyConstraint, UniqueConstraint]:
    return (
        ForeignKeyConstraint(
            ["profile_id", "organization_id"],
            ["business_profiles.id", "business_profiles.organization_id"],
            ondelete="RESTRICT",
            name=f"{prefix}_profile_scope",
        ),
        UniqueConstraint("id", "profile_id", "organization_id", name=f"{prefix}_scope"),
    )


class Scoped:
    organization_id: Mapped[UUID] = mapped_column(index=True)
    profile_id: Mapped[UUID] = mapped_column(index=True)


class Versioned:
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class BusinessCard(Record, Scoped, Versioned, Base):
    __tablename__ = "tool_business_cards"
    name_en: Mapped[str] = mapped_column(String(160))
    name_ta: Mapped[str] = mapped_column(String(160), default="")
    tagline_en: Mapped[str] = mapped_column(String(240), default="")
    tagline_ta: Mapped[str] = mapped_column(String(240), default="")
    description_en: Mapped[str] = mapped_column(Text, default="")
    description_ta: Mapped[str] = mapped_column(Text, default="")
    phone: Mapped[str] = mapped_column(String(40), default="")
    email: Mapped[str] = mapped_column(String(254), default="")
    website: Mapped[str] = mapped_column(String(500), default="")
    address_en: Mapped[str] = mapped_column(String(500), default="")
    address_ta: Mapped[str] = mapped_column(String(500), default="")
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    share_id: Mapped[UUID] = mapped_column(default=uuid4, unique=True)
    __table_args__ = (
        *scope_constraints("tool_card"),
        UniqueConstraint("profile_id"),
        CheckConstraint("version > 0", name="tool_card_version"),
    )


class Catalogue(Record, Scoped, Versioned, Base):
    __tablename__ = "tool_catalogues"
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    share_id: Mapped[UUID] = mapped_column(default=uuid4, unique=True)
    __table_args__ = (
        *scope_constraints("tool_catalogue"),
        UniqueConstraint("profile_id"),
        CheckConstraint("version > 0", name="tool_catalogue_version"),
    )


class CatalogueItem(Record, Scoped, Versioned, Base):
    __tablename__ = "tool_catalogue_items"
    kind: Mapped[str] = mapped_column(String(16))
    name_en: Mapped[str] = mapped_column(String(160))
    name_ta: Mapped[str] = mapped_column(String(160), default="")
    description_en: Mapped[str] = mapped_column(Text, default="")
    description_ta: Mapped[str] = mapped_column(Text, default="")
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3))
    __table_args__ = (
        *scope_constraints("tool_item"),
        CheckConstraint("version > 0", name="tool_item_version"),
        CheckConstraint("kind IN ('product','service')", name="tool_item_kind"),
        CheckConstraint("price IS NULL OR price >= 0", name="tool_item_price"),
        CheckConstraint("currency IN ('INR','USD','EUR','GBP')", name="tool_item_currency"),
    )


class Quotation(Record, Scoped, Versioned, Base):
    __tablename__ = "tool_quotations"
    business_name: Mapped[str] = mapped_column(String(160))
    customer_name: Mapped[str] = mapped_column(String(160))
    customer_address: Mapped[str] = mapped_column(String(1000), default="")
    issued_on: Mapped[date] = mapped_column(Date)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    currency: Mapped[str] = mapped_column(String(3))
    notes: Mapped[str] = mapped_column(Text, default="")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    discount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    status: Mapped[str] = mapped_column(String(16), default="draft")
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        *scope_constraints("tool_quote"),
        CheckConstraint("version > 0", name="tool_quote_version"),
        CheckConstraint("status IN ('draft','issued')", name="tool_quote_status"),
        CheckConstraint(
            "(status = 'draft' AND issued_at IS NULL) OR "
            "(status = 'issued' AND issued_at IS NOT NULL)",
            name="tool_quote_issue_state",
        ),
        CheckConstraint(
            "subtotal >= 0 AND discount >= 0 AND discount <= subtotal "
            "AND total = subtotal - discount",
            name="tool_quote_totals",
        ),
        CheckConstraint("valid_until IS NULL OR valid_until >= issued_on", name="tool_quote_dates"),
        CheckConstraint("currency IN ('INR','USD','EUR','GBP')", name="tool_quote_currency"),
    )


class QuotationLine(Record, Scoped, Base):
    __tablename__ = "tool_quotation_lines"
    quotation_id: Mapped[UUID] = mapped_column(index=True)
    position: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(String(500))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    catalogue_item_id: Mapped[UUID | None] = mapped_column(nullable=True)
    catalogue_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    __table_args__ = (
        *scope_constraints("tool_line"),
        ForeignKeyConstraint(
            ["quotation_id", "profile_id", "organization_id"],
            ["tool_quotations.id", "tool_quotations.profile_id", "tool_quotations.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["catalogue_item_id", "profile_id", "organization_id"],
            [
                "tool_catalogue_items.id",
                "tool_catalogue_items.profile_id",
                "tool_catalogue_items.organization_id",
            ],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("quotation_id", "position"),
        CheckConstraint("position >= 0 AND position < 50", name="tool_line_position"),
        CheckConstraint(
            "quantity > 0 AND quantity <= 1000000 AND unit_price >= 0 AND line_total >= 0 "
            "AND line_total = round(quantity * unit_price, 2)",
            name="tool_line_totals",
        ),
        CheckConstraint(
            "(catalogue_item_id IS NULL AND catalogue_version IS NULL) OR "
            "(catalogue_item_id IS NOT NULL AND catalogue_version IS NOT NULL "
            "AND catalogue_version > 0)",
            name="tool_line_reference",
        ),
    )


class CustomerContact(Record, Scoped, Versioned, Base):
    __tablename__ = "tool_customer_contacts"
    name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(254), default="")
    phone: Mapped[str] = mapped_column(String(40), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="lead")
    __table_args__ = (
        *scope_constraints("tool_contact"),
        CheckConstraint("version > 0", name="tool_contact_version"),
        CheckConstraint("status IN ('lead','customer','archived')", name="tool_contact_status"),
    )


class CustomerTask(Record, Scoped, Versioned, Base):
    __tablename__ = "tool_customer_tasks"
    contact_id: Mapped[UUID] = mapped_column(index=True)
    title: Mapped[str] = mapped_column(String(240))
    notes: Mapped[str] = mapped_column(Text, default="")
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        *scope_constraints("tool_task"),
        ForeignKeyConstraint(
            ["contact_id", "profile_id", "organization_id"],
            [
                "tool_customer_contacts.id",
                "tool_customer_contacts.profile_id",
                "tool_customer_contacts.organization_id",
            ],
            ondelete="RESTRICT",
        ),
        CheckConstraint("version > 0", name="tool_task_version"),
        CheckConstraint("status IN ('pending','completed','cancelled')", name="tool_task_status"),
        CheckConstraint(
            "(status = 'completed' AND completed_at IS NOT NULL) OR "
            "(status <> 'completed' AND completed_at IS NULL)",
            name="tool_task_completed",
        ),
    )


class ToolCommand(Record, Scoped, Base):
    __tablename__ = "tool_commands"
    request_id: Mapped[UUID] = mapped_column()
    operation: Mapped[str] = mapped_column(String(64))
    digest: Mapped[str] = mapped_column(String(64))
    resource_id: Mapped[UUID] = mapped_column()
    __table_args__ = (
        *scope_constraints("tool_command"),
        UniqueConstraint("profile_id", "request_id"),
    )


class ToolHistory(Record, Scoped, Base):
    __tablename__ = "tool_history"
    kind: Mapped[str] = mapped_column(String(24), index=True)
    resource_id: Mapped[UUID] = mapped_column(index=True)
    version: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(32))
    changed_fields: Mapped[list[str]] = mapped_column(JSONB)
    __table_args__ = (
        *scope_constraints("tool_history"),
        CheckConstraint("version > 0", name="tool_history_version"),
        CheckConstraint(
            "kind IN ('card','catalogue','catalogue_item','quote','contact','task')",
            name="tool_history_kind",
        ),
    )
