from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def now() -> datetime:
    return datetime.now(UTC)


class Record:
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Person(Record, Base):
    __tablename__ = "people"
    display_name: Mapped[str] = mapped_column(String(120))
    locale: Mapped[str] = mapped_column(String(2), default="en")
    __table_args__ = (CheckConstraint("locale IN ('en','ta')", name="person_locale"),)


class User(Record, Base):
    __tablename__ = "users"
    person_id: Mapped[UUID] = mapped_column(
        ForeignKey("people.id", ondelete="RESTRICT"), unique=True
    )
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','active','suspended','archived')", name="user_status"
        ),
    )


class Organization(Record, Base):
    __tablename__ = "organizations"
    name: Mapped[str] = mapped_column(String(160))


class Role(Record, Base):
    __tablename__ = "roles"
    name: Mapped[str] = mapped_column(String(80), unique=True)


class Permission(Base):
    __tablename__ = "permissions"
    code: Mapped[str] = mapped_column(String(80), primary_key=True)


class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id: Mapped[UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="RESTRICT"), primary_key=True
    )
    permission_code: Mapped[str] = mapped_column(
        ForeignKey("permissions.code", ondelete="RESTRICT"), primary_key=True
    )


class UserRole(Record, Base):
    __tablename__ = "user_roles"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    role_id: Mapped[UUID] = mapped_column(ForeignKey("roles.id", ondelete="RESTRICT"), index=True)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", "organization_id", name="uq_user_role_scope"),
    )


class RefreshSession(Record, Base):
    __tablename__ = "refresh_sessions"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    channel: Mapped[str] = mapped_column(String(10))
    device_name: Mapped[str] = mapped_column(String(80))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    access_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    access_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    browser_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    csrf_hash: Mapped[str | None] = mapped_column(String(64))
    __table_args__ = (CheckConstraint("channel IN ('mobile','browser')", name="session_channel"),)


class RefreshToken(Record, Base):
    __tablename__ = "refresh_tokens"
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("refresh_sessions.id", ondelete="RESTRICT"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class VerificationToken(Record, Base):
    __tablename__ = "verification_tokens"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    purpose: Mapped[str] = mapped_column(String(10))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint("purpose IN ('verify','reset')", name="token_purpose"),)


class AuthDelivery(Record, Base):
    __tablename__ = "auth_deliveries"
    token_id: Mapped[UUID] = mapped_column(
        ForeignKey("verification_tokens.id", ondelete="RESTRICT"), unique=True
    )
    encrypted_payload: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), default="development")
    transport: Mapped[str] = mapped_column(String(16), default="development")
    locale: Mapped[str] = mapped_column(String(2), default="en")
    template_version: Mapped[str] = mapped_column(String(24), default="auth-v1")
    message_id: Mapped[str] = mapped_column(
        String(320), unique=True, default=lambda: f"<auth-{uuid4()}@development.invalid>"
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    lease_token_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_code: Mapped[str] = mapped_column(String(40), default="")
    provider_reference: Mapped[str] = mapped_column(String(40), default="")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disposed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        CheckConstraint("transport IN ('development','smtp')", name="auth_delivery_transport"),
        CheckConstraint("locale IN ('en','ta')", name="auth_delivery_locale"),
        CheckConstraint("template_version = 'auth-v1'", name="auth_delivery_template"),
        CheckConstraint(
            "version > 0 AND attempt_count BETWEEN 0 AND 10", name="auth_delivery_version"
        ),
        CheckConstraint(
            "(transport = 'development' AND status = 'development') OR "
            "(transport = 'smtp' AND status IN ('queued','preparing','sending','retrying',"
            "'accepted','failed','ambiguous','suppressed')) OR status = 'suppressed'",
            name="auth_delivery_status",
        ),
        CheckConstraint(
            "(status IN ('preparing','sending') AND lease_token_digest ~ '^[0-9a-f]{64}$' "
            "AND lease_token_digest IS NOT NULL AND lease_until IS NOT NULL "
            "AND next_attempt_at IS NULL AND completed_at IS NULL) OR "
            "(status NOT IN ('preparing','sending') AND lease_token_digest IS NULL "
            "AND lease_until IS NULL)",
            name="auth_delivery_lease",
        ),
        CheckConstraint(
            "(status IN ('queued','retrying') AND next_attempt_at IS NOT NULL "
            "AND completed_at IS NULL) OR "
            "(status IN ('accepted','failed','ambiguous','suppressed') "
            "AND next_attempt_at IS NULL AND completed_at IS NOT NULL) OR "
            "(status IN ('development','preparing','sending') AND next_attempt_at IS NULL "
            "AND completed_at IS NULL)",
            name="auth_delivery_schedule",
        ),
        CheckConstraint(
            "(disposed_at IS NULL AND length(encrypted_payload) > 0) OR "
            "(disposed_at IS NOT NULL AND encrypted_payload = '' "
            "AND status IN ('accepted','failed','ambiguous','suppressed'))",
            name="auth_delivery_disposal",
        ),
        CheckConstraint(
            "provider_reference IN ('','smtp_250','operator_accepted') "
            "AND (status <> 'accepted' OR provider_reference <> '')",
            name="auth_delivery_provider_reference",
        ),
        CheckConstraint(
            "error_code IN ('','challenge_expired','challenge_obsolete','account_ineligible',"
            "'payload_invalid','configuration_unavailable','message_invalid','tls_unverified',"
            "'provider_temporary','provider_rejected','connection_failed','acknowledgement_unknown',"
            "'sending_interrupted','preparation_interrupted','retry_exhausted','operator_failed')",
            name="auth_delivery_error",
        ),
        Index("ix_auth_delivery_due", "status", "next_attempt_at", "id"),
        Index("ix_auth_delivery_lease", "status", "lease_until", "id"),
        Index("ix_auth_delivery_retention", "created_at", "id"),
    )


class AuthThrottle(Base):
    __tablename__ = "auth_throttles"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    hits: Mapped[int] = mapped_column(Integer)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class AuditLog(Record, Base):
    __tablename__ = "audit_logs"
    actor_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    action: Mapped[str] = mapped_column(String(80), index=True)
    resource_id: Mapped[UUID | None] = mapped_column(index=True)
    request_id: Mapped[str] = mapped_column(String(80))

    resource_version: Mapped[int | None] = mapped_column(Integer)
    reason: Mapped[str | None] = mapped_column(String(500))
    changed_fields: Mapped[str | None] = mapped_column(String(200))
