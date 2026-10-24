"""Shared file lifecycle, callable only AFTER trusted domain authorization.

No resource UUID, owner match, policy or lease grants byte access. Domain adapters
must resolve typed bindings and recheck current permission before constructing an
AuthorizedFileContext. Worker entry points are internal, not generic user APIs.
"""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, BinaryIO, cast
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.files.models import FileObject, FilePolicy
from app.modules.files.schemas import (
    FileCreate,
    FilePolicyCommand,
    FilePolicyCreate,
    FilePolicyList,
    FilePolicyRules,
    FilePolicyUpdate,
    FilePolicyView,
    FilePurpose,
    FileState,
    FileView,
    MediaType,
)
from app.modules.identity.models import AuditLog, Organization, User, now
from app.modules.identity.security import AuthError
from app.modules.identity.service import require_permission

if TYPE_CHECKING:
    from app.modules.files.scanner import FileScanner, ScanResult
    from app.modules.files.storage import PrivateStorage, StoredObject


@dataclass(frozen=True)
class AuthorizedFileContext:
    actor_user_id: UUID
    organization_id: UUID
    owner_person_id: UUID
    purpose: FilePurpose
    resource_id: UUID


@dataclass(frozen=True)
class FileLease:
    file_id: UUID
    organization_id: UUID
    version: int
    token: str
    expires_at: datetime


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _fingerprint(values: dict[str, object]) -> str:
    return _digest(json.dumps(values, sort_keys=True, separators=(",", ":"), default=str))


def _audit(
    db: Session,
    row: FilePolicy | FileObject,
    actor: User | None,
    action: str,
    request_id: str,
    fields: str,
    reason: str | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor.id if actor else None,
            organization_id=row.organization_id,
            resource_id=row.id,
            action="files." + action,
            request_id=request_id,
            resource_version=row.version,
            changed_fields=fields,
            reason=reason,
        )
    )


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("file_conflict", 409) from exc


def policy_view(row: FilePolicy) -> FilePolicyView:
    rules = {name: getattr(row, name) for name in FilePolicyRules.model_fields}
    return FilePolicyView(
        **rules,
        id=row.id,
        organization_id=row.organization_id,
        client_request_id=row.client_request_id,
        purpose=cast(FilePurpose, row.purpose),
        edition=row.edition,
        version=row.version,
        state=row.state,
        copy_from=row.copy_from,
        published_at=row.published_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _policy(db: Session, org: UUID, policy_id: UUID, lock: bool = False) -> FilePolicy:
    query = (
        select(FilePolicy)
        .where(FilePolicy.organization_id == org, FilePolicy.id == policy_id)
        .execution_options(populate_existing=True)
    )
    row = db.scalar(query.with_for_update() if lock else query)
    if row is None:
        raise AuthError("not_found", 404)
    return row


def _manage_policy(db: Session, org: UUID, actor: User) -> None:
    require_permission(db, actor, org, "files.policy.view")
    require_permission(db, actor, org, "files.policy.manage")


def list_policies(
    db: Session,
    org: UUID,
    actor: User,
    purpose: FilePurpose | None = None,
    cursor: UUID | None = None,
    limit: int = 25,
) -> FilePolicyList:
    require_permission(db, actor, org, "files.policy.view")
    if not 1 <= limit <= 100:
        raise AuthError("invalid_request", 422)
    query = select(FilePolicy).where(FilePolicy.organization_id == org)
    if purpose is not None:
        query = query.where(FilePolicy.purpose == purpose)
    if cursor is not None:
        if db.scalar(query.where(FilePolicy.id == cursor)) is None:
            raise AuthError("invalid_cursor", 422)
        query = query.where(FilePolicy.id > cursor)
    rows = list(db.scalars(query.order_by(FilePolicy.id).limit(limit + 1)))
    return FilePolicyList(
        items=[policy_view(row) for row in rows[:limit]],
        next_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )


def get_policy(db: Session, org: UUID, policy_id: UUID, actor: User) -> FilePolicyView:
    require_permission(db, actor, org, "files.policy.view")
    return policy_view(_policy(db, org, policy_id))


def create_policy(
    db: Session, org: UUID, actor: User, data: FilePolicyCreate, request_id: str
) -> FilePolicyView:
    _manage_policy(db, org, actor)
    if not db.scalar(select(Organization.id).where(Organization.id == org).with_for_update()):
        raise AuthError("not_found", 404)
    fingerprint = _fingerprint(data.model_dump(mode="json"))
    existing = db.scalar(
        select(FilePolicy).where(
            FilePolicy.organization_id == org,
            FilePolicy.client_request_id == data.client_request_id,
        )
    )
    if existing:
        if existing.request_digest != fingerprint:
            raise AuthError("idempotency_conflict", 409)
        return policy_view(existing)
    if data.copy_from is not None:
        source = _policy(db, org, data.copy_from)
        if source.purpose != data.purpose or source.state == "draft":
            raise AuthError("file_policy_copy_invalid", 422)
    if db.scalar(
        select(FilePolicy.id).where(
            FilePolicy.organization_id == org,
            FilePolicy.purpose == data.purpose,
            FilePolicy.state == "draft",
        )
    ):
        raise AuthError("file_policy_draft_exists", 409)
    edition = (
        int(
            db.scalar(
                select(func.coalesce(func.max(FilePolicy.edition), 0)).where(
                    FilePolicy.organization_id == org,
                    FilePolicy.purpose == data.purpose,
                )
            )
            or 0
        )
        + 1
    )
    row = FilePolicy(
        organization_id=org,
        client_request_id=data.client_request_id,
        request_digest=fingerprint,
        purpose=data.purpose,
        edition=edition,
        copy_from=data.copy_from,
        **data.model_dump(include=set(FilePolicyRules.model_fields)),
    )
    db.add(row)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("file_conflict", 409) from exc
    _audit(db, row, actor, "policy.created", request_id, "purpose,edition,rules,state", data.reason)
    _commit(db)
    return policy_view(row)


def update_policy(
    db: Session, org: UUID, policy_id: UUID, actor: User, data: FilePolicyUpdate, request_id: str
) -> FilePolicyView:
    _manage_policy(db, org, actor)
    row = _policy(db, org, policy_id, True)
    if row.state != "draft":
        raise AuthError("file_policy_immutable", 409)
    if row.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    for key, value in data.model_dump(include=set(FilePolicyRules.model_fields)).items():
        setattr(row, key, value)
    row.version += 1
    row.updated_at = now()
    _audit(db, row, actor, "policy.updated", request_id, "rules,version", data.reason)
    _commit(db)
    return policy_view(row)


def publish_policy(
    db: Session, org: UUID, policy_id: UUID, actor: User, data: FilePolicyCommand, request_id: str
) -> FilePolicyView:
    _manage_policy(db, org, actor)
    db.scalar(select(Organization.id).where(Organization.id == org).with_for_update())
    row = _policy(db, org, policy_id, True)
    if row.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    if row.state != "draft":
        raise AuthError("invalid_transition", 409)
    for previous in db.scalars(
        select(FilePolicy)
        .where(
            FilePolicy.organization_id == org,
            FilePolicy.purpose == row.purpose,
            FilePolicy.state == "published",
        )
        .with_for_update()
    ):
        previous.state = "retired"
        previous.version += 1
        previous.updated_at = now()
        _audit(db, previous, actor, "policy.retired", request_id, "state,version", data.reason)
    db.flush()
    row.state = "published"
    row.published_at = now()
    row.updated_at = now()
    row.version += 1
    _audit(
        db, row, actor, "policy.published", request_id, "state,published_at,version", data.reason
    )
    _commit(db)
    return policy_view(row)


def retire_policy(
    db: Session, org: UUID, policy_id: UUID, actor: User, data: FilePolicyCommand, request_id: str
) -> FilePolicyView:
    _manage_policy(db, org, actor)
    row = _policy(db, org, policy_id, True)
    if row.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    if row.state not in {"draft", "published"}:
        raise AuthError("invalid_transition", 409)
    row.state = "retired"
    row.version += 1
    row.updated_at = now()
    _audit(db, row, actor, "policy.retired", request_id, "state,version", data.reason)
    _commit(db)
    return policy_view(row)


def file_view(row: FileObject) -> FileView:
    return FileView(
        id=row.id,
        organization_id=row.organization_id,
        owner_person_id=row.owner_person_id,
        purpose=cast(FilePurpose, row.purpose),
        resource_id=row.resource_id,
        policy_id=row.policy_id,
        client_request_id=row.client_request_id,
        media_type=cast(MediaType, row.expected_media_type),
        byte_size=row.expected_byte_size,
        sha256=row.expected_sha256,
        state=cast(FileState, row.state),
        version=row.version,
        verified_at=row.verified_at,
        scanned_at=row.scanned_at,
        scan_attempts=row.scan_attempts,
        failure_code=row.failure_code,
        retention_until=row.retention_until,
        legal_hold=row.legal_hold,
        evidence_frozen=row.evidence_frozen,
        deleted_at=row.deleted_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _context(ctx: AuthorizedFileContext, actor: User) -> None:
    if ctx.actor_user_id != actor.id or actor.status != "active":
        raise AuthError("file_context_denied", 403)


def _file(db: Session, org: UUID, file_id: UUID, lock: bool = False) -> FileObject:
    query = (
        select(FileObject)
        .where(FileObject.organization_id == org, FileObject.id == file_id)
        .execution_options(populate_existing=True)
    )
    row = db.scalar(query.with_for_update() if lock else query)
    if row is None:
        raise AuthError("not_found", 404)
    return row


def _owned(
    db: Session, ctx: AuthorizedFileContext, actor: User, file_id: UUID, lock: bool = False
) -> FileObject:
    _context(ctx, actor)
    row = _file(db, ctx.organization_id, file_id, lock)
    if (row.owner_person_id, row.purpose, row.resource_id) != (
        ctx.owner_person_id,
        ctx.purpose,
        ctx.resource_id,
    ):
        raise AuthError("not_found", 404)
    return row


def create_file(
    db: Session,
    ctx: AuthorizedFileContext,
    actor: User,
    data: FileCreate,
    request_id: str,
    *,
    commit: bool = True,
    allow_retired_policy: bool = False,
) -> FileView:
    """Create after domain authorization; a domain unit of work may own the commit.

    Retired editions require the domain to prove an immutable published policy pin.
    These internal switches must never be copied from a browser request.
    """
    _context(ctx, actor)
    if not db.scalar(
        select(Organization.id)
        .where(
            Organization.id == ctx.organization_id,
        )
        .with_for_update()
    ):
        raise AuthError("not_found", 404)
    fingerprint = _fingerprint(
        {
            **data.model_dump(mode="json"),
            "owner_person_id": ctx.owner_person_id,
            "purpose": ctx.purpose,
            "resource_id": ctx.resource_id,
        }
    )
    existing = db.scalar(
        select(FileObject).where(
            FileObject.organization_id == ctx.organization_id,
            FileObject.client_request_id == data.client_request_id,
        )
    )
    if existing:
        if existing.request_digest != fingerprint:
            raise AuthError("idempotency_conflict", 409)
        return file_view(existing)
    policy = _policy(db, ctx.organization_id, data.policy_id, True)
    usable = policy.state == "published" or (
        allow_retired_policy and policy.state == "retired" and policy.published_at is not None
    )
    if not usable or policy.purpose != ctx.purpose:
        raise AuthError("file_policy_unavailable", 409)
    if data.media_type not in policy.allowed_mime_types or data.byte_size > policy.max_file_bytes:
        raise AuthError("file_policy_rejected", 422)
    count = int(
        db.scalar(
            select(func.count())
            .select_from(FileObject)
            .where(
                FileObject.organization_id == ctx.organization_id,
                FileObject.owner_person_id == ctx.owner_person_id,
                FileObject.purpose == ctx.purpose,
                FileObject.resource_id == ctx.resource_id,
                FileObject.state.in_(("pending", "uploading", "quarantined", "scanning", "clean")),
            )
        )
        or 0
    )
    if count >= policy.max_files:
        raise AuthError("file_count_exceeded", 409)
    created_at = now()
    row = FileObject(
        organization_id=ctx.organization_id,
        owner_person_id=ctx.owner_person_id,
        purpose=ctx.purpose,
        resource_id=ctx.resource_id,
        policy_id=policy.id,
        client_request_id=data.client_request_id,
        request_digest=fingerprint,
        object_key=f"quarantine/{ctx.organization_id}/{uuid4()}",
        expected_media_type=data.media_type,
        expected_byte_size=data.byte_size,
        expected_sha256=data.sha256,
        created_at=created_at,
        retention_until=created_at + timedelta(days=policy.retention_days),
    )
    db.add(row)
    db.flush()
    _audit(db, row, actor, "object.created", request_id, "purpose,policy_id,state")
    if commit:
        _commit(db)
    else:
        db.flush()
    return file_view(row)


def get_file(db: Session, ctx: AuthorizedFileContext, actor: User, file_id: UUID) -> FileView:
    return file_view(_owned(db, ctx, actor, file_id))


def _touch(row: FileObject) -> None:
    row.version += 1
    row.updated_at = now()


def _check_lease(row: FileObject, lease: FileLease, mode: str) -> None:
    expires = row.upload_lease_until if mode == "uploading" else row.scan_lease_until
    token_digest = row.upload_token_digest if mode == "uploading" else row.scan_token_digest
    if (
        row.id != lease.file_id
        or row.organization_id != lease.organization_id
        or row.state != mode
        or row.version != lease.version
        or expires is None
        or expires <= now()
        or token_digest is None
        or not secrets.compare_digest(token_digest, _digest(lease.token))
    ):
        raise AuthError("file_lease_lost", 409)


def begin_upload(
    db: Session,
    ctx: AuthorizedFileContext,
    actor: User,
    file_id: UUID,
    expected_version: int,
    request_id: str,
    lease_seconds: int = 120,
) -> FileLease:
    if not 10 <= lease_seconds <= 900:
        raise AuthError("invalid_request", 422)
    row = _owned(db, ctx, actor, file_id, True)
    if row.version != expected_version:
        raise AuthError("version_conflict", 409)
    if row.state != "pending" and not (
        row.state == "uploading"
        and row.upload_lease_until is not None
        and row.upload_lease_until <= now()
    ):
        raise AuthError("file_upload_unavailable", 409)
    token = secrets.token_urlsafe(32)
    row.state = "uploading"
    row.upload_token_digest = _digest(token)
    row.upload_lease_until = now() + timedelta(seconds=lease_seconds)
    _touch(row)
    _audit(db, row, actor, "upload.claimed", request_id, "state,version,upload_lease_until")
    _commit(db)
    assert row.upload_lease_until is not None
    return FileLease(row.id, row.organization_id, row.version, token, row.upload_lease_until)


def _reject(row: FileObject, policy: FilePolicy, code: str) -> None:
    row.state = "rejected"
    row.failure_code = code
    row.retention_until = now() + timedelta(days=policy.rejected_retention_days)
    row.upload_token_digest = None
    row.upload_lease_until = None
    row.scan_token_digest = None
    row.scan_lease_until = None
    row.scan_retry_at = None
    _touch(row)


def receive_upload(
    db: Session,
    ctx: AuthorizedFileContext,
    actor: User,
    lease: FileLease,
    source: BinaryIO,
    storage: PrivateStorage,
    request_id: str,
) -> FileView:
    row = _owned(db, ctx, actor, lease.file_id)
    _check_lease(row, lease, "uploading")
    key, mime, size, digest = (
        row.object_key,
        row.expected_media_type,
        row.expected_byte_size,
        row.expected_sha256,
    )
    db.commit()  # Do not hold a database lock across the bounded upload operation.
    try:
        ref = storage.put(key, source, mime, size, digest)
        if (
            ref.key != key
            or ref.media_type != mime
            or ref.byte_size != size
            or ref.sha256 != digest
            or not ref.version_id
            or len(ref.version_id) > 1024
            or any(ord(char) < 32 for char in ref.version_id)
        ):
            raise ValueError("invalid_storage_attestation")
    except Exception as exc:
        row = _owned(db, ctx, actor, lease.file_id, True)
        _check_lease(row, lease, "uploading")
        _reject(row, _policy(db, ctx.organization_id, row.policy_id), "upload_verification_failed")
        _audit(db, row, actor, "upload.rejected", request_id, "state,failure_code,retention_until")
        _commit(db)
        raise AuthError("file_upload_failed", 422) from exc
    row = _owned(db, ctx, actor, lease.file_id, True)
    _check_lease(row, lease, "uploading")
    row.storage_version = ref.version_id
    row.stored_byte_size = ref.byte_size
    row.stored_sha256 = ref.sha256
    row.verified_at = now()
    row.state = "quarantined"
    row.upload_token_digest = None
    row.upload_lease_until = None
    _touch(row)
    _audit(db, row, actor, "upload.verified", request_id, "state,verified_at,version")
    _commit(db)
    return file_view(row)


def scan_candidates(db: Session, limit: int = 25) -> list[tuple[UUID, UUID]]:
    if not 1 <= limit <= 100:
        raise AuthError("invalid_request", 422)
    return list(
        db.execute(
            select(FileObject.organization_id, FileObject.id)
            .where(
                or_(
                    (FileObject.state == "quarantined")
                    & or_(FileObject.scan_retry_at.is_(None), FileObject.scan_retry_at <= now()),
                    (FileObject.state == "scanning") & (FileObject.scan_lease_until <= now()),
                )
            )
            .order_by(FileObject.id)
            .limit(limit)
        ).tuples()
    )


def claim_scan(
    db: Session,
    org: UUID,
    file_id: UUID,
    request_id: str,
    lease_seconds: int = 120,
    max_attempts: int = 3,
) -> FileLease:
    if not 10 <= lease_seconds <= 900 or not 1 <= max_attempts <= 10:
        raise AuthError("invalid_request", 422)
    row = _file(db, org, file_id, True)
    ready = row.state == "quarantined" and (row.scan_retry_at is None or row.scan_retry_at <= now())
    expired = (
        row.state == "scanning"
        and row.scan_lease_until is not None
        and row.scan_lease_until <= now()
    )
    if not (ready or expired):
        raise AuthError("file_scan_unavailable", 409)
    if row.scan_attempts >= max_attempts:
        _reject(row, _policy(db, org, row.policy_id), "scan_attempts_exhausted")
        _audit(db, row, None, "scan.rejected", request_id, "state,failure_code,version")
        _commit(db)
        raise AuthError("file_scan_unavailable", 409)
    token = secrets.token_urlsafe(32)
    row.state = "scanning"
    row.scan_attempts += 1
    row.scan_token_digest = _digest(token)
    row.scan_lease_until = now() + timedelta(seconds=lease_seconds)
    row.scan_retry_at = None
    _touch(row)
    _audit(db, row, None, "scan.claimed", request_id, "state,scan_attempts,scan_lease_until")
    _commit(db)
    assert row.scan_lease_until is not None
    return FileLease(row.id, org, row.version, token, row.scan_lease_until)


def _stored(row: FileObject) -> StoredObject:
    from app.modules.files.storage import StoredObject

    if not row.storage_version or not row.stored_sha256 or row.stored_byte_size is None:
        raise AuthError("file_integrity_error", 503)
    return StoredObject(
        row.object_key,
        row.storage_version,
        row.expected_media_type,
        row.stored_byte_size,
        row.stored_sha256,
    )


def _recover_unverified(row: FileObject, storage: PrivateStorage) -> None:
    if row.storage_version is not None:
        return
    ref = storage.recover(
        row.object_key, row.expected_media_type, row.expected_byte_size, row.expected_sha256
    )
    if ref is None:
        return
    if (
        ref.key != row.object_key
        or ref.media_type != row.expected_media_type
        or ref.byte_size != row.expected_byte_size
        or ref.sha256 != row.expected_sha256
        or not ref.version_id
        or len(ref.version_id) > 1024
        or any(ord(char) < 32 for char in ref.version_id)
    ):
        raise AuthError("file_integrity_error", 503)
    row.storage_version = ref.version_id
    row.stored_byte_size = ref.byte_size
    row.stored_sha256 = ref.sha256
    row.verified_at = now()


def finish_scan(
    db: Session,
    org: UUID,
    lease: FileLease,
    result: ScanResult,
    request_id: str,
    max_attempts: int = 3,
) -> FileView:
    if not 1 <= max_attempts <= 10:
        raise AuthError("invalid_request", 422)
    row = _file(db, org, lease.file_id, True)
    _check_lease(row, lease, "scanning")
    policy = _policy(db, org, row.policy_id)
    if result.status not in {"clean", "infected"}:
        if row.scan_attempts >= max_attempts:
            _reject(row, policy, "scan_unavailable")
        else:
            row.state = "quarantined"
            row.failure_code = "scan_unavailable"
            row.scan_retry_at = now() + timedelta(seconds=min(300, 2**row.scan_attempts))
            row.scan_token_digest = None
            row.scan_lease_until = None
            _touch(row)
    elif result.sha256 != row.stored_sha256 or result.byte_size != row.stored_byte_size:
        _reject(row, policy, "scan_integrity_mismatch")
    else:
        row.state = result.status
        row.scan_storage_version = row.storage_version
        row.scan_sha256 = result.sha256
        row.scan_byte_size = result.byte_size
        row.scanned_at = now()
        row.failure_code = "malware_detected" if result.status == "infected" else None
        if result.status == "infected":
            row.retention_until = now() + timedelta(days=policy.rejected_retention_days)
        row.scan_token_digest = None
        row.scan_lease_until = None
        _touch(row)
    _audit(db, row, None, "scan.completed", request_id, "state,scanned_at,failure_code,version")
    _commit(db)
    return file_view(row)


def scan_with_lease(
    db: Session,
    org: UUID,
    lease: FileLease,
    storage: PrivateStorage,
    scanner: FileScanner,
    request_id: str,
    max_attempts: int = 3,
) -> FileView:
    from app.modules.files.scanner import ScanResult

    row = _file(db, org, lease.file_id)
    _check_lease(row, lease, "scanning")
    ref = _stored(row)
    db.commit()
    try:
        with storage.open(ref) as source:
            result = scanner.scan(source, max_bytes=ref.byte_size)
    except Exception:
        result = ScanResult("error", "", 0, "scan_unavailable")
    return finish_scan(db, org, lease, result, request_id, max_attempts)


def set_legal_hold(
    db: Session,
    ctx: AuthorizedFileContext,
    actor: User,
    file_id: UUID,
    expected_version: int,
    hold: bool,
    request_id: str,
) -> FileView:
    row = _owned(db, ctx, actor, file_id, True)
    if row.version != expected_version or row.state == "deleted":
        raise AuthError("version_conflict", 409)
    row.legal_hold = hold
    _touch(row)
    _audit(db, row, actor, "hold.changed", request_id, "legal_hold,version")
    _commit(db)
    return file_view(row)


def freeze_evidence(
    db: Session,
    ctx: AuthorizedFileContext,
    actor: User,
    file_id: UUID,
    expected_version: int,
    request_id: str,
    *,
    commit: bool = True,
) -> FileView:
    row = _owned(db, ctx, actor, file_id, True)
    if row.version != expected_version or row.state != "clean":
        raise AuthError("file_not_clean", 409)
    row.evidence_frozen = True
    _touch(row)
    _audit(db, row, actor, "evidence.frozen", request_id, "evidence_frozen,version")
    if commit:
        _commit(db)
    else:
        db.flush()
    return file_view(row)


def cleanup_file(
    db: Session,
    org: UUID,
    file_id: UUID,
    expected_version: int,
    storage: PrivateStorage,
    request_id: str,
) -> FileView:
    # Keep the lock across bounded deletion: a concurrent hold cannot race the
    # eligibility check and delete bytes after the hold has taken effect.
    row = _file(db, org, file_id, True)
    policy = _policy(db, org, row.policy_id)
    if row.version != expected_version:
        raise AuthError("version_conflict", 409)
    if (
        row.state not in {"clean", "infected", "rejected"}
        or row.retention_until > now()
        or row.legal_hold
        or (row.evidence_frozen and not policy.allow_frozen_disposal)
        or policy.published_at is None
    ):
        raise AuthError("file_disposal_denied", 409)
    try:
        _recover_unverified(row, storage)
        if row.storage_version is not None:
            storage.delete(_stored(row))
    except Exception as exc:
        db.rollback()
        raise AuthError("file_disposal_unavailable", 503) from exc
    row.state = "deleted"
    row.deleted_at = now()
    _touch(row)
    _audit(db, row, None, "object.disposed", request_id, "state,deleted_at,version")
    _commit(db)
    return file_view(row)


def cleanup_candidates(db: Session, limit: int = 25) -> list[tuple[UUID, UUID, int]]:
    if not 1 <= limit <= 100:
        raise AuthError("invalid_request", 422)
    return list(
        db.execute(
            select(
                FileObject.organization_id,
                FileObject.id,
                FileObject.version,
            )
            .join(FilePolicy, FilePolicy.id == FileObject.policy_id)
            .where(
                FileObject.state.in_(("clean", "infected", "rejected")),
                FileObject.retention_until <= now(),
                FileObject.legal_hold.is_(False),
                or_(
                    FileObject.evidence_frozen.is_(False),
                    FilePolicy.allow_frozen_disposal.is_(True),
                ),
                FilePolicy.published_at.is_not(None),
            )
            .order_by(FileObject.id)
            .limit(limit)
        ).tuples()
    )


def abandoned_candidates(db: Session, limit: int = 25) -> list[tuple[UUID, UUID, int]]:
    if not 1 <= limit <= 100:
        raise AuthError("invalid_request", 422)
    return list(
        db.execute(
            select(
                FileObject.organization_id,
                FileObject.id,
                FileObject.version,
            )
            .where(
                FileObject.retention_until <= now(),
                FileObject.legal_hold.is_(False),
                or_(
                    FileObject.state == "pending",
                    (FileObject.state == "uploading") & (FileObject.upload_lease_until <= now()),
                ),
            )
            .order_by(FileObject.id)
            .limit(limit)
        ).tuples()
    )


def reject_abandoned(
    db: Session,
    org: UUID,
    file_id: UUID,
    expected_version: int,
    request_id: str,
    *,
    storage: PrivateStorage,
) -> FileView:
    row = _file(db, org, file_id, True)
    if row.version != expected_version:
        raise AuthError("version_conflict", 409)
    if (
        row.retention_until > now()
        or row.legal_hold
        or row.state not in {"pending", "uploading"}
        or (
            row.state == "uploading"
            and row.upload_lease_until is not None
            and row.upload_lease_until > now()
        )
    ):
        raise AuthError("file_disposal_denied", 409)
    policy = _policy(db, org, row.policy_id)
    try:
        _recover_unverified(row, storage)
    except Exception as exc:
        db.rollback()
        raise AuthError("file_disposal_unavailable", 503) from exc
    _reject(row, policy, "upload_abandoned")
    _audit(db, row, None, "upload.abandoned", request_id, "state,failure_code,retention_until")
    _commit(db)
    return file_view(row)
