"""Global durable authentication intents; no organization grants or request-path I/O."""

import json
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import UUID

from cryptography.fernet import Fernet
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.modules.identity.auth_mail import Mail, MailResult, render_mail, smtp_configured
from app.modules.identity.models import AuditLog, AuthDelivery, User, VerificationToken, now
from app.modules.identity.security import AuthError, digest

TERMINAL = ("accepted", "failed", "ambiguous", "suppressed")


@dataclass(frozen=True)
class DeliveryLease:
    identity: UUID
    version: int
    attempt: int
    until: datetime
    token: str = field(repr=False)


def _locked(db: Session, identity: UUID) -> tuple[AuthDelivery, VerificationToken, User] | None:
    # Match account/challenge mutation lock order. Never hold these locks during SMTP.
    key = db.execute(
        select(AuthDelivery.token_id, VerificationToken.user_id)
        .join(VerificationToken, VerificationToken.id == AuthDelivery.token_id)
        .where(AuthDelivery.id == identity)
    ).first()
    if key is None:
        return None
    user = db.scalar(
        select(User)
        .where(User.id == key.user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    challenge = db.scalar(
        select(VerificationToken)
        .where(VerificationToken.id == key.token_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    row = db.scalar(
        select(AuthDelivery)
        .where(AuthDelivery.id == identity)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    return (row, challenge, user) if row and challenge and user else None


def _audit(db: Session, row: AuthDelivery, action: str, reason: str | None = None) -> None:
    db.add(
        AuditLog(
            actor_id=None,
            organization_id=None,
            resource_id=row.id,
            action="auth.delivery." + action,
            request_id=f"auth-delivery:{row.id}",
            resource_version=row.version,
            changed_fields="status,version,attempt_count,error_code",
            reason=reason,
        )
    )


def _eligible(challenge: VerificationToken, user: User) -> str | None:
    if challenge.consumed_at is not None:
        return "challenge_obsolete"
    if challenge.expires_at <= now():
        return "challenge_expired"
    if user.status != ("pending" if challenge.purpose == "verify" else "active"):
        return "account_ineligible"
    return None


def _terminal(db: Session, row: AuthDelivery, status: str, code: str) -> None:
    row.status, row.error_code = status, code
    row.lease_token_digest = row.lease_until = row.next_attempt_at = None
    row.completed_at = now()
    row.version += 1
    _audit(db, row, status)


def _lease(row: AuthDelivery, raw: str) -> DeliveryLease:
    assert row.lease_until
    return DeliveryLease(row.id, row.version, row.attempt_count, row.lease_until, raw)


def _fenced(row: AuthDelivery, lease: DeliveryLease, status: str) -> bool:
    return bool(
        row.status == status
        and row.version == lease.version
        and row.attempt_count == lease.attempt
        and row.lease_until == lease.until
        and row.lease_until
        and row.lease_until > now()
        and row.lease_token_digest
        and secrets.compare_digest(row.lease_token_digest, digest(lease.token))
    )


def claim(db: Session, identity: UUID, policy: Settings) -> DeliveryLease | None:
    if not smtp_configured(policy):
        return None
    found = _locked(db, identity)
    if not found:
        return None
    row, challenge, user = found
    if (
        row.status not in {"queued", "retrying"}
        or not row.next_attempt_at
        or row.next_attempt_at > now()
    ):
        db.rollback()
        return None
    reason = _eligible(challenge, user)
    if reason:
        _terminal(db, row, "suppressed", reason)
        db.commit()
        return None
    if row.attempt_count >= policy.auth_delivery_max_attempts:
        _terminal(db, row, "failed", "retry_exhausted")
        db.commit()
        return None
    raw = secrets.token_urlsafe(32)
    row.status, row.error_code = "preparing", ""
    row.attempt_count += 1
    row.version += 1
    row.next_attempt_at = None
    row.lease_token_digest = digest(raw)
    row.lease_until = now() + timedelta(seconds=policy.auth_delivery_lease_seconds)
    _audit(db, row, "claimed")
    lease = _lease(row, raw)
    db.commit()
    return lease


def prepare_mail(db: Session, lease: DeliveryLease, policy: Settings) -> Mail | None:
    found = _locked(db, lease.identity)
    if not found or not _fenced(found[0], lease, "preparing"):
        db.rollback()
        return None
    row, challenge, user = found
    if reason := _eligible(challenge, user):
        _terminal(db, row, "suppressed", reason)
        db.commit()
        return None
    try:
        assert policy.auth_delivery_key
        payload = json.loads(
            Fernet(policy.auth_delivery_key.get_secret_value().encode()).decrypt(
                row.encrypted_payload.encode()
            )
        )
        if (
            not isinstance(payload, dict)
            or set(payload) != {"email", "purpose", "token"}
            or payload["email"] != user.email
            or payload["purpose"] != challenge.purpose
            or not isinstance(payload["token"], str)
            or digest(payload["token"]) != challenge.token_hash
        ):
            raise ValueError("Invalid payload")
        message = render_mail(
            policy,
            recipient=payload["email"],
            secret=payload["token"],
            purpose=challenge.purpose,
            locale=row.locale,
            message_id=row.message_id,
            edition=row.template_version,
        )
    except Exception:
        _terminal(db, row, "failed", "payload_invalid")
        db.commit()
        return None
    db.commit()
    return message


def begin_send(db: Session, lease: DeliveryLease, policy: Settings) -> DeliveryLease | None:
    found = _locked(db, lease.identity)
    if not found or not _fenced(found[0], lease, "preparing"):
        db.rollback()
        return None
    row, challenge, user = found
    if reason := _eligible(challenge, user):
        _terminal(db, row, "suppressed", reason)
    elif not smtp_configured(policy):
        _terminal(db, row, "failed", "configuration_unavailable")
    else:
        row.status = "sending"
        row.version += 1
        _audit(db, row, "sending")
        sending = _lease(row, lease.token)
        db.commit()
        return sending
    db.commit()
    return None


def _retry(db: Session, row: AuthDelivery, code: str, policy: Settings) -> None:
    if row.attempt_count >= policy.auth_delivery_max_attempts:
        _terminal(db, row, "failed", "retry_exhausted")
        return
    row.status, row.error_code = "retrying", code
    row.lease_token_digest = row.lease_until = None
    row.next_attempt_at = now() + timedelta(seconds=min(300, 5 * 2**row.attempt_count))
    row.completed_at = None
    row.version += 1
    _audit(db, row, "retry_scheduled")


def settle(db: Session, lease: DeliveryLease, result: MailResult, policy: Settings) -> bool:
    found = _locked(db, lease.identity)
    if not found or not _fenced(found[0], lease, "sending"):
        db.rollback()
        return False
    row = found[0]
    if result.outcome == "accepted":
        row.provider_reference = "smtp_250"
        _terminal(db, row, "accepted", "")
    elif result.outcome == "ambiguous":
        _terminal(db, row, "ambiguous", result.code)
    elif result.outcome == "transient":
        _retry(db, row, result.code, policy)
    else:
        _terminal(db, row, "failed", result.code)
    db.commit()
    return True


def recover(db: Session, policy: Settings) -> tuple[list[UUID], int]:
    current = now()
    identities = list(
        db.scalars(
            select(AuthDelivery.id)
            .where(
                or_(
                    AuthDelivery.status.in_(("queued", "retrying"))
                    & (AuthDelivery.next_attempt_at <= current),
                    AuthDelivery.status.in_(("preparing", "sending"))
                    & (AuthDelivery.lease_until <= current),
                )
            )
            .order_by(AuthDelivery.created_at, AuthDelivery.id)
            .limit(policy.auth_delivery_batch_size)
        )
    )
    db.commit()
    due: list[UUID] = []
    settled = 0
    for identity in identities:
        found = _locked(db, identity)
        if not found:
            db.rollback()
            continue
        row, challenge, user = found
        if row.status == "sending" and row.lease_until and row.lease_until <= now():
            # Even a process death immediately before socket I/O has an uncertain
            # send marker. SMTP cannot safely deduplicate, so never auto-resend.
            _terminal(db, row, "ambiguous", "sending_interrupted")
            settled += 1
        elif row.status == "preparing" and row.lease_until and row.lease_until <= now():
            reason = _eligible(challenge, user)
            if reason:
                _terminal(db, row, "suppressed", reason)
            else:
                _retry(db, row, "preparation_interrupted", policy)
            settled += 1
        elif (
            row.status in {"queued", "retrying"}
            and row.next_attempt_at
            and row.next_attempt_at <= now()
        ):
            reason = _eligible(challenge, user)
            if reason:
                _terminal(db, row, "suppressed", reason)
                settled += 1
            elif row.attempt_count >= policy.auth_delivery_max_attempts:
                _terminal(db, row, "failed", "retry_exhausted")
                settled += 1
            elif smtp_configured(policy):
                due.append(row.id)
        db.commit()
    return due, settled


def dispose(db: Session, policy: Settings) -> int:
    days = policy.auth_delivery_retention_days
    if days is None:
        return 0
    current = now()
    identities = list(
        db.scalars(
            select(AuthDelivery.id)
            .join(VerificationToken)
            .where(
                AuthDelivery.disposed_at.is_(None),
                AuthDelivery.status.in_((*TERMINAL, "development")),
                VerificationToken.expires_at <= current,
                AuthDelivery.created_at <= current - timedelta(days=days),
            )
            .order_by(AuthDelivery.created_at, AuthDelivery.id)
            .limit(policy.auth_delivery_batch_size)
        )
    )
    db.commit()
    count = 0
    for identity in identities:
        found = _locked(db, identity)
        if not found:
            continue
        row, challenge, _ = found
        if (
            row.disposed_at
            or challenge.expires_at > now()
            or row.status not in (*TERMINAL, "development")
        ):
            db.rollback()
            continue
        if row.status == "development":
            _terminal(db, row, "suppressed", "challenge_expired")
            db.flush()
        row.encrypted_payload = ""
        row.disposed_at = now()
        row.version += 1
        _audit(db, row, "payload_disposed")
        db.commit()
        count += 1
    return count


def health(db: Session, policy: Settings) -> dict[str, object]:
    counts = {
        status: int(count)
        for status, count in db.execute(
            select(AuthDelivery.status, func.count()).group_by(AuthDelivery.status)
        )
    }
    oldest = db.scalar(
        select(func.min(AuthDelivery.created_at)).where(
            AuthDelivery.status.in_(("queued", "retrying")),
            AuthDelivery.next_attempt_at <= now(),
        )
    )
    return {
        "counts": counts,
        "smtp_configured": smtp_configured(policy),
        "retention_configured": policy.auth_delivery_retention_days is not None,
        "oldest_due_seconds": max(0.0, (now() - oldest).total_seconds()) if oldest else None,
        "capability": "smtp_acceptance_without_delivery_callback",
        "automatic_ambiguous_resend": False,
    }


def operator_recover(
    db: Session, identity: UUID, version: int, outcome: str, reason: str, policy: Settings
) -> None:
    reason = reason.strip()
    if not 10 <= len(reason) <= 500 or outcome not in {"retry", "accepted", "failed"}:
        raise AuthError("invalid_request", 422)
    found = _locked(db, identity)
    if not found:
        raise AuthError("not_found", 404)
    row, challenge, user = found
    if row.version != version or row.disposed_at:
        raise AuthError("version_conflict", 409)
    if row.status == "ambiguous" and outcome in {"accepted", "failed"}:
        row.provider_reference = "operator_accepted" if outcome == "accepted" else ""
        _terminal(db, row, outcome, "" if outcome == "accepted" else "operator_failed")
    elif row.status == "failed" and outcome == "retry" and row.error_code != "operator_failed":
        if (
            _eligible(challenge, user)
            or not smtp_configured(policy)
            or row.attempt_count >= policy.auth_delivery_max_attempts
        ):
            raise AuthError("recovery_unavailable", 409)
        row.status, row.error_code, row.provider_reference = "queued", "", ""
        row.completed_at = None
        row.next_attempt_at = now()
        row.version += 1
    else:
        raise AuthError("recovery_unavailable", 409)
    _audit(db, row, "operator_recovery", reason)
    db.commit()
