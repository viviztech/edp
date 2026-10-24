"""Private staged files become immutable evidence on an immutable ticket message."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
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
from app.modules.identity.models import Record


class HelpdeskFile(Record, Base):
    __tablename__ = "helpdesk_files"
    organization_id: Mapped[UUID] = mapped_column()
    ticket_id: Mapped[UUID] = mapped_column()
    author_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    owner_person_id: Mapped[UUID] = mapped_column()
    policy_id: Mapped[UUID] = mapped_column()
    file_id: Mapped[UUID] = mapped_column(unique=True)
    purpose: Mapped[str] = mapped_column(String(32), default="helpdesk_attachment")
    client_request_id: Mapped[UUID] = mapped_column()
    request_digest: Mapped[str] = mapped_column(String(64))
    internal: Mapped[bool] = mapped_column(Boolean)
    state: Mapped[str] = mapped_column(String(16), default="staged")
    version: Mapped[int] = mapped_column(Integer, default=1)
    message_id: Mapped[UUID | None] = mapped_column(nullable=True)
    frozen_file_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    frozen_storage_version: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    frozen_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    frozen_byte_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        ForeignKeyConstraint(
            ["ticket_id", "organization_id"],
            ["helpdesk_tickets.id", "helpdesk_tickets.organization_id"],
            ondelete="RESTRICT",
            name="fk_helpdesk_file_ticket",
        ),
        ForeignKeyConstraint(
            ["message_id", "ticket_id", "organization_id", "author_user_id", "internal"],
            [
                "helpdesk_messages.id",
                "helpdesk_messages.ticket_id",
                "helpdesk_messages.organization_id",
                "helpdesk_messages.author_user_id",
                "helpdesk_messages.internal",
            ],
            ondelete="RESTRICT",
            name="fk_helpdesk_file_message_scope",
        ),
        ForeignKeyConstraint(
            ["file_id", "organization_id", "owner_person_id", "purpose", "id"],
            [
                "file_objects.id",
                "file_objects.organization_id",
                "file_objects.owner_person_id",
                "file_objects.purpose",
                "file_objects.resource_id",
            ],
            ondelete="RESTRICT",
            name="fk_helpdesk_file_object_scope",
        ),
        ForeignKeyConstraint(
            ["policy_id", "organization_id", "purpose"],
            ["file_policies.id", "file_policies.organization_id", "file_policies.purpose"],
            ondelete="RESTRICT",
            name="fk_helpdesk_file_policy_scope",
        ),
        UniqueConstraint("organization_id", "client_request_id"),
        CheckConstraint("purpose = 'helpdesk_attachment'", name="helpdesk_file_purpose"),
        CheckConstraint(
            "state IN ('staged','removed','posted') AND version > 0",
            name="helpdesk_file_state",
        ),
        CheckConstraint("request_digest ~ '^[0-9a-f]{64}$'", name="helpdesk_file_digest"),
        CheckConstraint(
            "(state = 'posted' AND message_id IS NOT NULL AND frozen_file_version > 0 "
            "AND frozen_file_version IS NOT NULL AND frozen_storage_version IS NOT NULL "
            "AND frozen_sha256 IS NOT NULL AND frozen_byte_size > 0 "
            "AND frozen_byte_size IS NOT NULL AND frozen_at IS NOT NULL) OR "
            "(state <> 'posted' AND message_id IS NULL AND frozen_file_version IS NULL "
            "AND frozen_storage_version IS NULL AND frozen_sha256 IS NULL "
            "AND frozen_byte_size IS NULL AND frozen_at IS NULL)",
            name="helpdesk_file_frozen_evidence",
        ),
        Index("ix_helpdesk_file_ticket", "organization_id", "ticket_id", "id"),
        Index("ix_helpdesk_file_message", "organization_id", "message_id", "id"),
    )
