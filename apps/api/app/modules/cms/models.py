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
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.identity.models import Record, now


class Page(Record, Base):
    __tablename__ = "cms_pages"
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    slug: Mapped[str] = mapped_column(String(120))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (
        UniqueConstraint("organization_id", "slug"),
        UniqueConstraint("id", "organization_id"),
        CheckConstraint("slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'", name="cms_slug"),
    )


class Translation(Record, Base):
    __tablename__ = "cms_page_translations"
    page_id: Mapped[UUID] = mapped_column(index=True)
    organization_id: Mapped[UUID] = mapped_column(index=True)
    locale: Mapped[str] = mapped_column(String(2))
    state: Mapped[str] = mapped_column(String(16), default="draft")
    version: Mapped[int] = mapped_column(Integer, default=1)
    draft_title: Mapped[str] = mapped_column(String(200))
    draft_body: Mapped[str] = mapped_column(Text)
    draft_seo_title: Mapped[str] = mapped_column(String(70), default="")
    draft_seo_description: Mapped[str] = mapped_column(String(200), default="")
    published_revision_id: Mapped[UUID | None] = mapped_column(index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (
        UniqueConstraint("page_id", "locale"),
        UniqueConstraint("id", "organization_id"),
        ForeignKeyConstraint(
            ["page_id", "organization_id"],
            ["cms_pages.id", "cms_pages.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["published_revision_id", "id", "organization_id"],
            [
                "cms_page_revisions.id",
                "cms_page_revisions.translation_id",
                "cms_page_revisions.organization_id",
            ],
            name="fk_cms_published_revision",
            use_alter=True,
            ondelete="RESTRICT",
        ),
        CheckConstraint("locale IN ('en','ta')", name="cms_locale"),
        CheckConstraint("version > 0", name="cms_version"),
        CheckConstraint(
            "length(trim(draft_title)) > 0 AND length(draft_body) BETWEEN 1 AND 50000",
            name="cms_content",
        ),
        CheckConstraint(
            "(state = 'published' AND published_revision_id IS NOT NULL) "
            "OR (state IN ('draft','archived') AND published_revision_id IS NULL)",
            name="cms_publication_state",
        ),
        Index("ix_cms_public_list", "organization_id", "locale", "state", "page_id"),
    )


class Revision(Record, Base):
    __tablename__ = "cms_page_revisions"
    translation_id: Mapped[UUID] = mapped_column(index=True)
    organization_id: Mapped[UUID] = mapped_column(index=True)
    revision_number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    seo_title: Mapped[str] = mapped_column(String(70))
    seo_description: Mapped[str] = mapped_column(String(200))
    actor_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    __table_args__ = (
        ForeignKeyConstraint(
            ["translation_id", "organization_id"],
            ["cms_page_translations.id", "cms_page_translations.organization_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("translation_id", "revision_number"),
        UniqueConstraint("id", "translation_id", "organization_id"),
        CheckConstraint("revision_number > 0", name="cms_revision_positive"),
    )


class EditorialEntry(Record, Base):
    __tablename__ = "cms_editorial_entries"
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    kind: Mapped[str] = mapped_column(String(20))
    slug: Mapped[str] = mapped_column(String(120))
    locale: Mapped[str] = mapped_column(String(2))
    state: Mapped[str] = mapped_column(String(16), default="draft")
    version: Mapped[int] = mapped_column(Integer, default=1)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (
        UniqueConstraint("organization_id", "kind", "slug", "locale"),
        CheckConstraint("kind IN ('news','event','faq','testimonial')", name="cms_editorial_kind"),
        CheckConstraint("locale IN ('en','ta')", name="cms_editorial_locale"),
        CheckConstraint("state IN ('draft','published','archived')", name="cms_editorial_state"),
        CheckConstraint(
            "length(trim(title)) > 0 AND length(body) BETWEEN 1 AND 50000",
            name="cms_editorial_content",
        ),
        Index(
            "ix_cms_editorial_public", "organization_id", "kind", "locale", "state", "sort_order"
        ),
    )


class Asset(Record, Base):
    __tablename__ = "cms_assets"
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    filename: Mapped[str] = mapped_column(String(255))
    media_type: Mapped[str] = mapped_column(String(100))
    byte_size: Mapped[int] = mapped_column(Integer)
    scan_status: Mapped[str] = mapped_column(String(16), default="pending")
    visibility: Mapped[str] = mapped_column(String(16), default="private")
    title: Mapped[str] = mapped_column(String(200))
    __table_args__ = (
        CheckConstraint(
            "scan_status IN ('pending','clean','infected','rejected')", name="cms_asset_scan"
        ),
        CheckConstraint("visibility IN ('private','public')", name="cms_asset_visibility"),
        CheckConstraint("byte_size BETWEEN 1 AND 10485760", name="cms_asset_size"),
        CheckConstraint(
            "media_type IN ('image/jpeg','image/png','image/webp','application/pdf')",
            name="cms_asset_type",
        ),
        Index("ix_cms_assets_public", "organization_id", "visibility", "scan_status"),
    )


class Enquiry(Record, Base):
    __tablename__ = "contact_enquiries"
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(320))
    phone: Mapped[str] = mapped_column(String(32), default="")
    message: Mapped[str] = mapped_column(Text)
    consent_version: Mapped[str] = mapped_column(String(40))
    dedupe_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="new")
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (
        UniqueConstraint("organization_id", "dedupe_hash"),
        ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        CheckConstraint("status IN ('new','reviewed','closed')", name="enquiry_status"),
        CheckConstraint("version > 0", name="enquiry_version"),
        CheckConstraint(
            "length(trim(name)) BETWEEN 1 AND 120 AND length(message) BETWEEN 1 AND 5000",
            name="enquiry_content",
        ),
        Index("ix_contact_enquiries_queue", "organization_id", "status", "id"),
    )
