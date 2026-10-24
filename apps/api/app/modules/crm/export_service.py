"""Database-owned CRM export claims, authorization, fencing and output disposal."""

import csv
import hashlib
import io
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.modules.crm.models import ExportJob, Lead
from app.modules.identity.models import AuditLog, RolePermission, User, UserRole, now
from app.modules.identity.security import AuthError

MAX_EXPORT_ROWS = 10000


@dataclass(frozen=True)
class ExportLease:
    job_id: UUID
    organization_id: UUID
    requester_id: UUID
    attempt: int
    version: int
    token: str
    until: datetime


@dataclass(frozen=True)
class ExportContent:
    csv: str
    row_count: int


class ExportLimitError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _safe(value: object) -> str:
    text = "" if value is None else str(value)
    # Preserve the value, but stop spreadsheet formulas after leading whitespace too.
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text


def configured(settings: Settings) -> bool:
    return settings.app_env in {"local", "test"} or settings.crm_export_retention_days is not None


def authorized_requester(db: Session, requester: UUID, org: UUID, *, lock: bool = False) -> bool:
    query = select(User).where(User.id == requester).execution_options(populate_existing=True)
    user = db.scalar(query.with_for_update() if lock else query)
    if user is None or user.status != "active":
        return False
    grant = (
        select(UserRole.id)
        .join(RolePermission, RolePermission.role_id == UserRole.role_id)
        .where(
            UserRole.user_id == requester,
            UserRole.organization_id == org,
            RolePermission.permission_code == "crm.lead.export",
        )
        .order_by(UserRole.id)
        .limit(1)
    )
    if lock:
        grant = grant.with_for_update(of=(UserRole, RolePermission))
    return db.scalar(grant) is not None


def require_requester(db: Session, requester: UUID, org: UUID) -> None:
    if not authorized_requester(db, requester, org):
        raise AuthError("forbidden", 403)


def _job(db: Session, identity: UUID) -> ExportJob | None:
    return db.scalar(
        select(ExportJob)
        .where(ExportJob.id == identity)
        .execution_options(populate_existing=True)
        .with_for_update()
    )


def _audit(db: Session, row: ExportJob, action: str) -> None:
    db.add(
        AuditLog(
            actor_id=None,
            organization_id=row.organization_id,
            resource_id=row.id,
            action="crm.lead.export_" + action,
            request_id=f"export:{row.id}",
            resource_version=row.version,
            changed_fields="status,attempt_count,version,error_code",
        )
    )


def _terminal(db: Session, row: ExportJob, code: str) -> None:
    row.status, row.error_code = "failed", code
    row.lease_token_digest = row.lease_until = row.next_attempt_at = None
    row.csv_content, row.row_count = None, 0
    row.completed_at = now()
    row.version += 1
    _audit(db, row, "failed")


def _unavailable(db: Session, row: ExportJob, settings: Settings) -> str | None:
    if row.expires_at <= now():
        return "request_expired"
    if not authorized_requester(db, row.requested_by_id, row.organization_id, lock=True):
        return "requester_unavailable"
    if row.attempt_count >= settings.crm_export_max_attempts:
        return "retry_exhausted"
    return None


def claim_export(
    db: Session, identity: UUID, settings: Settings | None = None
) -> ExportLease | None:
    policy = settings or get_settings()
    if not configured(policy):
        return None
    row = _job(db, identity)
    if row is None or row.status != "queued" or row.next_attempt_at is None:
        db.rollback()
        return None
    if row.next_attempt_at > now() and row.expires_at > now():
        db.rollback()
        return None
    reason = _unavailable(db, row, policy)
    if reason:
        _terminal(db, row, reason)
        db.commit()
        return None
    raw = secrets.token_urlsafe(32)
    row.status, row.error_code = "running", ""
    row.attempt_count += 1
    row.version += 1
    row.lease_token_digest = _digest(raw)
    row.lease_until = now() + timedelta(seconds=policy.crm_export_lease_seconds)
    row.next_attempt_at = None
    _audit(db, row, "claimed")
    db.flush()
    lease = ExportLease(
        row.id,
        row.organization_id,
        row.requested_by_id,
        row.attempt_count,
        row.version,
        raw,
        row.lease_until,
    )
    db.commit()
    return lease


def _fenced(row: ExportJob | None, lease: ExportLease) -> bool:
    return bool(
        row
        and row.status == "running"
        and row.id == lease.job_id
        and row.organization_id == lease.organization_id
        and row.requested_by_id == lease.requester_id
        and row.version == lease.version
        and row.attempt_count == lease.attempt
        and row.lease_until is not None
        and row.lease_until == lease.until
        and row.lease_until > now()
        and row.lease_token_digest
        and secrets.compare_digest(row.lease_token_digest, _digest(lease.token))
    )


def complete_export(db: Session, lease: ExportLease, output: ExportContent) -> bool:
    row = _job(db, lease.job_id)
    if not _fenced(row, lease):
        db.rollback()
        return False
    assert row is not None
    # Reload and lock account and permission; generation cannot retain cached authority.
    if row.expires_at <= now():
        _terminal(db, row, "request_expired")
    elif not authorized_requester(db, row.requested_by_id, row.organization_id, lock=True):
        _terminal(db, row, "requester_unavailable")
    else:
        row.status, row.error_code = "completed", ""
        row.csv_content, row.row_count = output.csv, output.row_count
        row.completed_at = now()
        row.lease_token_digest = row.lease_until = None
        row.version += 1
        _audit(db, row, "completed")
    db.commit()
    return row.status == "completed"


def _retry(db: Session, row: ExportJob, code: str) -> None:
    row.status, row.error_code = "queued", code
    row.lease_token_digest = row.lease_until = None
    row.next_attempt_at = now() + timedelta(seconds=min(300, 5 * 2**row.attempt_count))
    row.version += 1
    _audit(db, row, "retry_scheduled")


def fail_export(
    db: Session,
    lease: ExportLease,
    code: str,
    *,
    retryable: bool,
    settings: Settings | None = None,
) -> bool:
    policy = settings or get_settings()
    row = _job(db, lease.job_id)
    if not _fenced(row, lease):
        db.rollback()
        return False
    assert row is not None
    reason = _unavailable(db, row, policy)
    if reason or not retryable:
        _terminal(db, row, reason or code)
    else:
        _retry(db, row, "generation_failed")
    db.commit()
    return True


def recover_exports(db: Session, settings: Settings | None = None) -> tuple[list[UUID], int]:
    policy = settings or get_settings()
    if not configured(policy):
        return [], 0
    current = now()
    rows = list(
        db.scalars(
            select(ExportJob)
            .where(
                or_(
                    (ExportJob.status == "queued")
                    & or_(
                        ExportJob.next_attempt_at <= current,
                        ExportJob.expires_at <= current,
                    ),
                    (ExportJob.status == "running") & (ExportJob.lease_until <= current),
                )
            )
            .order_by(ExportJob.created_at, ExportJob.id)
            .limit(policy.crm_export_recovery_batch_size)
            .execution_options(populate_existing=True)
            .with_for_update(skip_locked=True)
        )
    )
    eligible: list[UUID] = []
    settled = 0
    for row in rows:
        reason = _unavailable(db, row, policy)
        if reason:
            _terminal(db, row, reason)
            settled += 1
        elif row.status == "running":
            _retry(db, row, "recovered_lease")
            settled += 1
        else:
            eligible.append(row.id)
    db.commit()
    return eligible, settled


def dispose_expired(db: Session, settings: Settings | None = None) -> int:
    policy = settings or get_settings()
    days = policy.crm_export_retention_days
    if days is None:
        return 0
    current = now()
    rows = list(
        db.scalars(
            select(ExportJob)
            .where(
                ExportJob.status == "completed",
                ExportJob.expires_at <= current,
                ExportJob.created_at <= current - timedelta(days=days),
            )
            .order_by(ExportJob.expires_at, ExportJob.id)
            .limit(policy.crm_export_recovery_batch_size)
            .execution_options(populate_existing=True)
            .with_for_update(skip_locked=True)
        )
    )
    for row in rows:
        row.status, row.error_code, row.csv_content = "failed", "expired", None
        row.disposed_at = current
        row.version += 1
        _audit(db, row, "disposed")
    db.commit()
    return len(rows)


def generate_csv(db: Session, org: UUID, max_bytes: int) -> ExportContent:
    parts: list[str] = []
    total = 0

    def append(values: list[object]) -> None:
        nonlocal total
        buffer = io.StringIO(newline="")
        csv.writer(buffer).writerow([_safe(value) for value in values])
        line = buffer.getvalue()
        total += len(line.encode("utf-8"))
        if total > max_bytes:
            raise ExportLimitError("output_too_large")
        parts.append(line)

    append(
        [
            "id",
            "name",
            "email",
            "phone",
            "source",
            "campaign",
            "status",
            "assigned_user_id",
            "merged_into_id",
            "created_at",
        ]
    )
    count = 0
    for lead in db.scalars(
        select(Lead)
        .where(Lead.organization_id == org)
        .order_by(Lead.id)
        .limit(MAX_EXPORT_ROWS + 1)
        .execution_options(yield_per=500)
    ):
        count += 1
        if count > MAX_EXPORT_ROWS:
            raise ExportLimitError("row_limit_exceeded")
        append(
            [
                lead.id,
                lead.name,
                lead.email,
                lead.phone,
                lead.source,
                lead.campaign,
                lead.status,
                lead.assigned_user_id,
                lead.merged_into_id,
                lead.created_at.isoformat(),
            ]
        )
    return ExportContent("".join(parts), count)
