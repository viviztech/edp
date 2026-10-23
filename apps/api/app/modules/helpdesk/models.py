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
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.identity.models import Record, now


class HelpdeskTicket(Record, Base):
    __tablename__ = "helpdesk_tickets"
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    owner_participant_id: Mapped[UUID] = mapped_column()
    owner_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    request_id: Mapped[UUID] = mapped_column()
    request_digest: Mapped[str] = mapped_column(String(64))
    number: Mapped[str] = mapped_column(String(40), unique=True)
    category: Mapped[str] = mapped_column(String(32))
    subject: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(24), default="open")
    priority: Mapped[str] = mapped_column(String(12), default="normal")
    assignee_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (
        ForeignKeyConstraint(
            ["owner_participant_id", "organization_id"],
            ["participants.id", "participants.organization_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("id", "organization_id"),
        UniqueConstraint("organization_id", "owner_user_id", "request_id"),
        CheckConstraint("version > 0", name="helpdesk_ticket_version"),
        CheckConstraint(
            "category IN ('funding','registration','tax_compliance','marketing','technology',"
            "'business_planning','banking','mentoring','general')",
            name="helpdesk_ticket_category",
        ),
        CheckConstraint(
            "priority IN ('low','normal','high','urgent')", name="helpdesk_ticket_priority"
        ),
        CheckConstraint(
            "status IN ('open','assigned','in_progress','waiting_for_user','resolved','closed')",
            name="helpdesk_ticket_status",
        ),
        CheckConstraint(
            "status <> 'open' OR assignee_user_id IS NULL", name="helpdesk_open_unassigned"
        ),
        CheckConstraint(
            "status NOT IN ('assigned','in_progress','waiting_for_user','resolved') "
            "OR assignee_user_id IS NOT NULL",
            name="helpdesk_assigned_required",
        ),
        Index("ix_helpdesk_owner", "organization_id", "owner_user_id", "id"),
        Index("ix_helpdesk_queue", "organization_id", "assignee_user_id", "status", "id"),
    )


class HelpdeskMessage(Record, Base):
    __tablename__ = "helpdesk_messages"
    organization_id: Mapped[UUID] = mapped_column()
    ticket_id: Mapped[UUID] = mapped_column()
    ticket_version: Mapped[int] = mapped_column(Integer)
    author_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    internal: Mapped[bool] = mapped_column(Boolean, default=False)
    body: Mapped[str] = mapped_column(Text)
    __table_args__ = (
        ForeignKeyConstraint(
            ["ticket_id", "organization_id"],
            ["helpdesk_tickets.id", "helpdesk_tickets.organization_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("id", "ticket_id", "organization_id"),
        UniqueConstraint("ticket_id", "ticket_version"),
        CheckConstraint("ticket_version > 0", name="helpdesk_message_version"),
        CheckConstraint("length(body) BETWEEN 1 AND 8000", name="helpdesk_message_body"),
        Index("ix_helpdesk_messages", "organization_id", "ticket_id", "ticket_version"),
    )


class HelpdeskAttachment(Record, Base):
    __tablename__ = "helpdesk_attachments"
    organization_id: Mapped[UUID] = mapped_column()
    ticket_id: Mapped[UUID] = mapped_column()
    message_id: Mapped[UUID] = mapped_column()
    filename: Mapped[str] = mapped_column(String(120))
    content: Mapped[str] = mapped_column(Text)
    size_bytes: Mapped[int] = mapped_column(Integer)
    __table_args__ = (
        ForeignKeyConstraint(
            ["message_id", "ticket_id", "organization_id"],
            [
                "helpdesk_messages.id",
                "helpdesk_messages.ticket_id",
                "helpdesk_messages.organization_id",
            ],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "size_bytes BETWEEN 1 AND 32768 AND size_bytes = octet_length(content)",
            name="helpdesk_attachment_size",
        ),
        Index("ix_helpdesk_attachment_message", "organization_id", "ticket_id", "message_id"),
    )


class HelpdeskHistory(Record, Base):
    __tablename__ = "helpdesk_history"
    organization_id: Mapped[UUID] = mapped_column()
    ticket_id: Mapped[UUID] = mapped_column()
    version: Mapped[int] = mapped_column(Integer)
    event: Mapped[str] = mapped_column(String(24))
    status: Mapped[str] = mapped_column(String(24))
    priority: Mapped[str] = mapped_column(String(12))
    reason: Mapped[str] = mapped_column(String(500))
    staff_only: Mapped[bool] = mapped_column(Boolean, default=False)
    private_reason: Mapped[bool] = mapped_column(Boolean, default=False)
    actor_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    __table_args__ = (
        ForeignKeyConstraint(
            ["ticket_id", "organization_id"],
            ["helpdesk_tickets.id", "helpdesk_tickets.organization_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("ticket_id", "version"),
        CheckConstraint("version > 0", name="helpdesk_history_version"),
        Index("ix_helpdesk_history", "organization_id", "ticket_id", "version"),
    )


class HelpdeskAssignment(Record, Base):
    __tablename__ = "helpdesk_assignments"
    organization_id: Mapped[UUID] = mapped_column()
    ticket_id: Mapped[UUID] = mapped_column()
    version: Mapped[int] = mapped_column(Integer)
    from_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    to_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    actor_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    reason: Mapped[str] = mapped_column(String(500))
    __table_args__ = (
        ForeignKeyConstraint(
            ["ticket_id", "organization_id"],
            ["helpdesk_tickets.id", "helpdesk_tickets.organization_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("ticket_id", "version"),
        CheckConstraint("version > 0", name="helpdesk_assignment_version"),
    )


class HelpdeskNotice(Record, Base):
    __tablename__ = "helpdesk_notices"
    organization_id: Mapped[UUID] = mapped_column()
    ticket_id: Mapped[UUID] = mapped_column()
    recipient_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    event: Mapped[str] = mapped_column(String(24))
    ticket_version: Mapped[int] = mapped_column(Integer)
    version: Mapped[int] = mapped_column(Integer, default=1)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        ForeignKeyConstraint(
            ["ticket_id", "organization_id"],
            ["helpdesk_tickets.id", "helpdesk_tickets.organization_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("ticket_id", "recipient_user_id", "event", "ticket_version"),
        CheckConstraint("version > 0 AND ticket_version > 0", name="helpdesk_notice_version"),
        Index("ix_helpdesk_notice_inbox", "organization_id", "recipient_user_id", "id"),
    )


class HelpdeskPreference(Record, Base):
    __tablename__ = "helpdesk_preferences"
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id"),
        CheckConstraint("version > 0", name="helpdesk_preference_version"),
    )
