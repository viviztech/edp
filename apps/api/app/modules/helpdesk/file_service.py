"""Current ticket access and immutable message visibility govern every file operation."""

import hashlib
import json
from typing import BinaryIO, Literal, cast
from uuid import UUID, uuid4

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.core.config import get_settings
from app.modules.files import service as files
from app.modules.files.models import FileObject, FilePolicy
from app.modules.files.runtime import require_files_enabled
from app.modules.files.schemas import FileCreate, MediaType
from app.modules.files.storage import PrivateStorage, StoredObject
from app.modules.helpdesk import service as desk
from app.modules.helpdesk.file_models import HelpdeskFile
from app.modules.helpdesk.file_schemas import (
    HelpdeskFileEvidence,
    HelpdeskFileIntent,
    HelpdeskFileList,
    HelpdeskFilePolicyView,
    HelpdeskFileView,
)
from app.modules.helpdesk.models import HelpdeskMessage, HelpdeskTicket
from app.modules.identity.models import AuditLog, User, now
from app.modules.identity.security import AuthError
from app.modules.identity.service import throttle


def context(
    db: Session,
    org: UUID,
    ticket_id: UUID,
    actor: User,
    *,
    writing: bool = False,
    lock: bool = False,
) -> tuple[HelpdeskTicket, Literal["owner", "staff"]]:
    current = db.get(User, actor.id, populate_existing=True)
    if current is None or current.status != "active":
        raise AuthError("forbidden", 403)
    query = (
        select(HelpdeskTicket)
        .where(
            HelpdeskTicket.id == ticket_id,
            HelpdeskTicket.organization_id == org,
        )
        .execution_options(populate_existing=True)
    )
    ticket = db.scalar(query.with_for_update() if lock else query)
    if ticket is None:
        raise AuthError("not_found", 404)
    audience = desk.access(db, ticket, actor, write=writing)
    if writing and ticket.status in {"resolved", "closed"}:
        raise AuthError("helpdesk_reopen_required", 409)
    return ticket, audience


def _file(db: Session, row: HelpdeskFile, *, lock: bool = False) -> FileObject:
    query = (
        select(FileObject)
        .where(
            FileObject.id == row.file_id,
            FileObject.organization_id == row.organization_id,
            FileObject.owner_person_id == row.owner_person_id,
            FileObject.purpose == "helpdesk_attachment",
            FileObject.resource_id == row.id,
        )
        .execution_options(populate_existing=True)
    )
    item = db.scalar(query.with_for_update() if lock else query)
    if item is None:
        raise AuthError("file_integrity_error", 503)
    return item


def file_context(row: HelpdeskFile, actor: User) -> files.AuthorizedFileContext:
    return files.AuthorizedFileContext(
        actor.id,
        row.organization_id,
        row.owner_person_id,
        "helpdesk_attachment",
        row.id,
    )


def _clean(file: FileObject) -> bool:
    return bool(
        file.state == "clean"
        and file.retention_until > now()
        and file.storage_version
        and file.verified_at
        and file.scanned_at
        and file.stored_sha256 == file.expected_sha256
        and file.stored_byte_size == file.expected_byte_size
        and file.scan_storage_version == file.storage_version
        and file.scan_sha256 == file.stored_sha256
        and file.scan_byte_size == file.stored_byte_size
    )


def file_view(db: Session, row: HelpdeskFile) -> HelpdeskFileView:
    file = _file(db, row)
    policy = db.get(FilePolicy, row.policy_id)
    if policy is None:
        raise AuthError("file_integrity_error", 503)
    pinned = (row.frozen_storage_version, row.frozen_sha256, row.frozen_byte_size) == (
        file.storage_version,
        file.stored_sha256,
        file.stored_byte_size,
    )
    usable = (
        row.state != "removed"
        and _clean(file)
        and (
            row.state == "staged" or (file.evidence_frozen and pinned and row.frozen_at is not None)
        )
    )
    return HelpdeskFileView(
        id=row.id,
        message_id=row.message_id,
        internal=row.internal,
        state=cast("Literal['staged','removed','posted']", row.state),
        version=row.version,
        file=files.file_view(file),
        policy=_policy_view(policy),
        usable=usable,
        evidence=HelpdeskFileEvidence(
            file_id=row.file_id,
            file_version=row.frozen_file_version,
            sha256=row.frozen_sha256,
            byte_size=row.frozen_byte_size,
            frozen_at=row.frozen_at,
        )
        if row.frozen_at
        else None,
    )


def _visible(actor: User, audience: str) -> ColumnElement[bool]:
    # Staging is private to its author, even when another administrator has ticket access.
    own = and_(HelpdeskFile.author_user_id == actor.id, HelpdeskFile.state != "posted")
    posted: ColumnElement[bool] = HelpdeskFile.state == "posted"
    if audience == "owner":
        own = and_(own, HelpdeskFile.internal.is_(False))
        posted = and_(posted, HelpdeskFile.internal.is_(False))
    return or_(own, posted)


def binding(
    db: Session,
    org: UUID,
    ticket_id: UUID,
    binding_id: UUID,
    actor: User,
    *,
    writing: bool = False,
    lock: bool = False,
) -> tuple[HelpdeskFile, FileObject]:
    _, audience = context(db, org, ticket_id, actor, writing=writing, lock=lock)
    query = (
        select(HelpdeskFile)
        .where(
            HelpdeskFile.id == binding_id,
            HelpdeskFile.organization_id == org,
            HelpdeskFile.ticket_id == ticket_id,
            _visible(actor, audience),
        )
        .execution_options(populate_existing=True)
    )
    row = db.scalar(query.with_for_update() if lock else query)
    if row is None:
        raise AuthError("not_found", 404)
    item = _file(db, row, lock=lock)
    if writing and (
        row.state != "staged" or row.author_user_id != actor.id or item.retention_until <= now()
    ):
        raise AuthError("helpdesk_file_read_only", 409)
    return row, item


def _policy_view(row: FilePolicy) -> HelpdeskFilePolicyView:
    return HelpdeskFilePolicyView(
        id=row.id,
        edition=row.edition,
        name=row.name,
        allowed_mime_types=cast(list[MediaType], row.allowed_mime_types),
        max_file_bytes=row.max_file_bytes,
        max_upload_bytes=min(row.max_file_bytes, get_settings().files_max_bytes),
        max_files=row.max_files,
        retention_days=row.retention_days,
        rejected_retention_days=row.rejected_retention_days,
        notice_en=row.notice_en,
        notice_ta=row.notice_ta,
        allow_frozen_disposal=row.allow_frozen_disposal,
    )


def listing(
    db: Session,
    org: UUID,
    ticket_id: UUID,
    actor: User,
    cursor: UUID | None = None,
    limit: int = 25,
) -> HelpdeskFileList:
    _, audience = context(db, org, ticket_id, actor)
    if not 1 <= limit <= 100:
        raise AuthError("invalid_request", 422)
    query = select(HelpdeskFile).where(
        HelpdeskFile.organization_id == org,
        HelpdeskFile.ticket_id == ticket_id,
        HelpdeskFile.state != "removed",
        _visible(actor, audience),
    )
    if cursor:
        if db.scalar(query.where(HelpdeskFile.id == cursor)) is None:
            raise AuthError("invalid_cursor", 400)
        query = query.where(HelpdeskFile.id > cursor)
    rows = list(db.scalars(query.order_by(HelpdeskFile.id).limit(limit + 1)))
    policy = db.scalar(
        select(FilePolicy).where(
            FilePolicy.organization_id == org,
            FilePolicy.purpose == "helpdesk_attachment",
            FilePolicy.state == "published",
        )
    )
    return HelpdeskFileList(
        collection_enabled=get_settings().files_enabled,
        max_upload_bytes=get_settings().files_max_bytes,
        policy=_policy_view(policy) if policy else None,
        items=[file_view(db, row) for row in rows[:limit]],
        next_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )


def _audit(db: Session, row: HelpdeskFile, actor: User, action: str, request_id: str) -> None:
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=row.organization_id,
            resource_id=row.id,
            resource_version=row.version,
            action="helpdesk.file." + action,
            request_id=request_id,
            changed_fields="file_id,state,version",
        )
    )


def create(
    db: Session, org: UUID, ticket_id: UUID, actor: User, data: HelpdeskFileIntent, request_id: str
) -> HelpdeskFileView:
    settings = require_files_enabled()
    _, audience = context(db, org, ticket_id, actor)
    if data.internal and audience != "staff":
        raise AuthError("forbidden", 403)
    fingerprint = hashlib.sha256(
        json.dumps(data.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

    def existing() -> HelpdeskFile | None:
        row = db.scalar(
            select(HelpdeskFile).where(
                HelpdeskFile.organization_id == org,
                HelpdeskFile.client_request_id == data.client_request_id,
            )
        )
        if row and (
            row.ticket_id != ticket_id
            or row.author_user_id != actor.id
            or row.request_digest != fingerprint
        ):
            raise AuthError("idempotency_conflict", 409)
        return row

    prior = existing()
    if prior:
        return file_view(db, prior)
    context(db, org, ticket_id, actor, writing=True)
    throttle(db, "files.intent", f"{org}:{actor.id}", settings.files_intent_limit_per_window)
    _, audience = context(db, org, ticket_id, actor, writing=True, lock=True)
    if data.internal and audience != "staff":
        raise AuthError("forbidden", 403)
    prior = existing()
    if prior:
        return file_view(db, prior)
    policy = db.scalar(
        select(FilePolicy).where(
            FilePolicy.id == data.policy_id,
            FilePolicy.organization_id == org,
            FilePolicy.purpose == "helpdesk_attachment",
            FilePolicy.state == "published",
        )
    )
    if policy is None or policy.published_at is None:
        raise AuthError("file_policy_unavailable", 409)
    if data.byte_size > min(policy.max_file_bytes, settings.files_max_bytes):
        raise AuthError("file_policy_rejected", 422)
    count = (
        db.scalar(
            select(func.count())
            .select_from(HelpdeskFile)
            .where(
                HelpdeskFile.ticket_id == ticket_id,
                HelpdeskFile.author_user_id == actor.id,
                HelpdeskFile.state == "staged",
            )
        )
        or 0
    )
    if count >= policy.max_files:
        raise AuthError("file_count_exceeded", 409)
    binding_id = uuid4()
    ctx = files.AuthorizedFileContext(
        actor.id, org, actor.person_id, "helpdesk_attachment", binding_id
    )
    item = files.create_file(
        db,
        ctx,
        actor,
        FileCreate(**data.model_dump(exclude={"internal"})),
        request_id,
        commit=False,
    )
    row = HelpdeskFile(
        id=binding_id,
        organization_id=org,
        ticket_id=ticket_id,
        author_user_id=actor.id,
        owner_person_id=actor.person_id,
        policy_id=policy.id,
        file_id=item.id,
        client_request_id=data.client_request_id,
        request_digest=fingerprint,
        internal=data.internal,
    )
    db.add(row)
    db.flush()
    _audit(db, row, actor, "staged", request_id)
    desk.commit(db)
    return file_view(db, row)


def remove(
    db: Session,
    org: UUID,
    ticket_id: UUID,
    binding_id: UUID,
    actor: User,
    expected_version: int,
    request_id: str,
) -> HelpdeskFileView:
    require_files_enabled()
    row, _ = binding(db, org, ticket_id, binding_id, actor, lock=True)
    if row.state == "removed" and row.author_user_id == actor.id:
        return file_view(db, row)
    context(db, org, ticket_id, actor, writing=True)
    if row.author_user_id != actor.id or row.state != "staged":
        raise AuthError("helpdesk_file_read_only", 409)
    if row.version != expected_version:
        raise AuthError("version_conflict", 409)
    row.state, row.version = "removed", row.version + 1
    _audit(db, row, actor, "removed", request_id)
    desk.commit(db)
    return file_view(db, row)


def upload(
    db: Session,
    org: UUID,
    ticket_id: UUID,
    binding_id: UUID,
    actor: User,
    version: int,
    source: BinaryIO,
    storage: PrivateStorage,
    request_id: str,
) -> HelpdeskFileView:
    settings = require_files_enabled()
    row, item = binding(db, org, ticket_id, binding_id, actor, writing=True, lock=True)
    ctx = file_context(row, actor)
    lease = files.begin_upload(
        db, ctx, actor, item.id, version, request_id, settings.files_upload_lease_seconds
    )
    files.receive_upload(db, ctx, actor, lease, source, storage, request_id)
    return file_view(db, row)


def download_reference(
    db: Session, org: UUID, ticket_id: UUID, binding_id: UUID, actor: User
) -> tuple[UUID, StoredObject]:
    require_files_enabled()
    row, item = binding(db, org, ticket_id, binding_id, actor)
    if not file_view(db, row).usable or not item.storage_version:
        raise AuthError("helpdesk_file_unavailable", 409)
    return item.id, StoredObject(
        item.object_key,
        item.storage_version,
        item.expected_media_type,
        item.expected_byte_size,
        item.expected_sha256,
    )


def record_download(
    db: Session, org: UUID, ticket_id: UUID, binding_id: UUID, actor: User, request_id: str
) -> None:
    download_reference(db, org, ticket_id, binding_id, actor)
    row, _ = binding(db, org, ticket_id, binding_id, actor)
    _audit(db, row, actor, "downloaded", request_id)
    desk.commit(db)


def posted_message_files(db: Session, org: UUID, message_id: UUID) -> list[HelpdeskFileView]:
    """Internal projection; callers first authorize/filter the immutable messages."""
    rows = list(
        db.scalars(
            select(HelpdeskFile)
            .where(
                HelpdeskFile.organization_id == org,
                HelpdeskFile.message_id == message_id,
                HelpdeskFile.state == "posted",
            )
            .order_by(HelpdeskFile.id)
            .limit(101)
        )
    )
    if len(rows) > 100:
        raise AuthError("file_integrity_error", 503)
    return [file_view(db, row) for row in rows]


def validate_message_files(
    db: Session,
    ticket: HelpdeskTicket,
    actor: User,
    file_ids: list[UUID],
    internal: bool,
) -> list[tuple[HelpdeskFile, FileObject]]:
    if not file_ids:
        return []
    require_files_enabled()
    selected = []
    for binding_id in sorted(file_ids):
        row, item = binding(
            db, ticket.organization_id, ticket.id, binding_id, actor, writing=True, lock=True
        )
        if row.internal != internal or not _clean(item):
            raise AuthError("helpdesk_file_unavailable", 409)
        selected.append((row, item))
    policies = {row.policy_id for row, _ in selected}
    if len(policies) != 1:
        raise AuthError("helpdesk_file_policy_mismatch", 409)
    policy = db.get(FilePolicy, next(iter(policies)))
    if policy is None or len(selected) > policy.max_files:
        raise AuthError("file_count_exceeded", 409)
    return selected


def freeze_message(
    db: Session, ticket: HelpdeskTicket, message: HelpdeskMessage, actor: User, request_id: str
) -> None:
    selected = validate_message_files(db, ticket, actor, message.shared_file_ids, message.internal)
    for row, item in selected:
        files.freeze_evidence(
            db, file_context(row, actor), actor, item.id, item.version, request_id, commit=False
        )
        row.state, row.version, row.message_id = "posted", row.version + 1, message.id
        row.frozen_file_version, row.frozen_storage_version = item.version, item.storage_version
        row.frozen_sha256, row.frozen_byte_size = item.stored_sha256, item.stored_byte_size
        row.frozen_at = now()
        db.flush()
        _audit(db, row, actor, "posted", request_id)
