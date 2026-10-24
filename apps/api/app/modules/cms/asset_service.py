"""CMS byte authority comes from typed bindings, never legacy scan metadata."""

import hashlib
import json
from typing import BinaryIO
from uuid import UUID, uuid4, uuid5

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.modules.cms.models import Asset, AssetFile
from app.modules.cms.schemas import AssetCommand, AssetCreate, AssetSourceCreate, AssetView
from app.modules.files import service as files
from app.modules.files.models import FileObject, FilePolicy
from app.modules.files.schemas import FileCreate
from app.modules.files.storage import PrivateStorage, StorageError, StoredObject
from app.modules.identity.models import AuditLog, Organization, User, now
from app.modules.identity.security import AuthError
from app.modules.identity.service import require_permission, throttle

ALLOWED = {"image/jpeg", "image/png", "image/webp", "application/pdf"}


def authorize(db: Session, org: UUID, actor: User, action: str) -> None:
    if actor.status != "active":
        raise AuthError("invalid_session", 401)
    require_permission(db, actor, org, "cms.asset.view")
    require_permission(db, actor, org, "cms.asset." + action)


def _audit(
    db: Session, a: Asset, actor: User, action: str, request_id: str, reason: str = ""
) -> None:
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=a.organization_id,
            resource_id=a.id,
            action="cms.asset." + action,
            request_id=request_id,
            resource_version=a.version,
            changed_fields="source,visibility,public_evidence,version",
            reason=reason or None,
        )
    )


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AuthError("asset_conflict", 409) from None


def asset(db: Session, org: UUID, asset_id: UUID, lock: bool = False) -> Asset:
    query = (
        select(Asset)
        .where(Asset.id == asset_id, Asset.organization_id == org)
        .execution_options(populate_existing=True)
    )
    row = db.scalar(query.with_for_update() if lock else query)
    if row is None:
        raise AuthError("not_found", 404)
    return row


def bound(db: Session, a: Asset, role: str, *, lock: bool = False) -> FileObject | None:
    query = (
        select(FileObject)
        .join(AssetFile, AssetFile.file_id == FileObject.id)
        .where(
            AssetFile.organization_id == a.organization_id,
            AssetFile.asset_id == a.id,
            AssetFile.role == role,
            FileObject.organization_id == a.organization_id,
            FileObject.resource_id == a.id,
            FileObject.purpose == "cms_asset",
        )
        .execution_options(populate_existing=True)
    )
    return db.scalar(query.with_for_update(of=FileObject) if lock else query)


def context(a: Asset, actor: User, owner: UUID) -> files.AuthorizedFileContext:
    return files.AuthorizedFileContext(actor.id, a.organization_id, owner, "cms_asset", a.id)


def clean(row: FileObject | None) -> bool:
    return bool(
        row
        and row.state == "clean"
        and row.deleted_at is None
        and row.retention_until > now()
        and row.verified_at
        and row.scanned_at
        and row.storage_version
        and row.stored_sha256 == row.expected_sha256
        and row.stored_byte_size == row.expected_byte_size
        and row.scan_storage_version == row.storage_version
        and row.scan_sha256 == row.stored_sha256
        and row.scan_byte_size == row.stored_byte_size
    )


def stored(row: FileObject) -> StoredObject:
    if not clean(row):
        raise AuthError("asset_not_clean", 409)
    assert row.storage_version and row.stored_sha256 and row.stored_byte_size
    return StoredObject(
        row.object_key,
        row.storage_version,
        row.expected_media_type,
        row.stored_byte_size,
        row.stored_sha256,
    )


def _view(
    a: Asset, source: FileObject | None, prepared: FileObject | None, *, public: bool = False
) -> AssetView:
    candidate = source if a.media_type == "application/pdf" else prepared
    available = clean(candidate)
    published = bool(
        available
        and candidate
        and a.visibility == "public"
        and a.public_file_id == candidate.id
        and a.public_storage_version == candidate.storage_version
        and a.public_sha256 == candidate.stored_sha256
        and a.public_byte_size == candidate.stored_byte_size
    )
    scan_status = (
        a.scan_status
        if source is None
        else (source.state if source.state in {"clean", "infected", "rejected"} else "pending")
    )
    return AssetView(
        id=a.id,
        filename=a.filename,
        media_type=a.media_type,
        byte_size=a.byte_size,
        title=a.title,
        scan_status=scan_status,
        visibility=a.visibility,
        version=a.version,
        byte_state=source.state if source else "unbacked",
        source=files.file_view(source) if source is not None and not public else None,
        prepared=files.file_view(prepared) if prepared is not None and not public else None,
        can_publish=available and not public,
        public_url=f"/api/v1/public/organizations/{a.organization_id}/assets/{a.id}/content"
        if published
        else None,
    )


def views(db: Session, rows: list[Asset], *, public: bool = False) -> list[AssetView]:
    if not rows:
        return []
    pairs = db.execute(
        select(AssetFile, FileObject)
        .join(FileObject, FileObject.id == AssetFile.file_id)
        .where(
            AssetFile.asset_id.in_([a.id for a in rows]),
            AssetFile.organization_id == rows[0].organization_id,
        )
    ).all()
    by_asset = {(binding.asset_id, binding.role): row for binding, row in pairs}
    return [
        _view(
            a,
            by_asset.get((a.id, "source")),
            by_asset.get((a.id, "public_derivative")),
            public=public,
        )
        for a in rows
    ]


def view(db: Session, a: Asset) -> AssetView:
    return views(db, [a])[0]


def create(db: Session, org: UUID, actor: User, data: AssetCreate, request_id: str) -> AssetView:
    authorize(db, org, actor, "create")
    if not db.scalar(select(Organization.id).where(Organization.id == org).with_for_update()):
        raise AuthError("not_found", 404)
    digest = hashlib.sha256(
        json.dumps(data.model_dump(mode="json"), sort_keys=True).encode()
    ).hexdigest()
    if data.client_request_id is not None:
        previous = db.scalar(
            select(Asset).where(
                Asset.organization_id == org, Asset.client_request_id == data.client_request_id
            )
        )
        if previous:
            if previous.request_digest != digest:
                raise AuthError("idempotency_conflict", 409)
            return view(db, previous)
    throttle(
        db, "cms-media-intent", f"{org}:{actor.id}", get_settings().files_intent_limit_per_window
    )
    a = Asset(
        organization_id=org,
        storage_key=f"legacy/{org}/{uuid4()}",
        filename=data.filename,
        media_type=data.media_type,
        byte_size=data.byte_size,
        title=data.title,
        client_request_id=data.client_request_id,
        request_digest=digest,
    )
    db.add(a)
    db.flush()
    _audit(db, a, actor, "created", request_id)
    _commit(db)
    return view(db, a)


def create_source(
    db: Session,
    org: UUID,
    asset_id: UUID,
    actor: User,
    data: AssetSourceCreate,
    request_id: str,
    settings: Settings,
) -> AssetView:
    authorize(db, org, actor, "create")
    a = asset(db, org, asset_id, True)
    metadata = FileCreate.model_validate(data.model_dump(exclude={"expected_version"}))
    existing = bound(db, a, "source")
    if existing:
        if existing.client_request_id == data.client_request_id:
            files.create_file(
                db,
                context(a, actor, existing.owner_person_id),
                actor,
                metadata,
                request_id,
                commit=False,
            )
            return view(db, a)
        raise AuthError("asset_source_immutable", 409)
    if a.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    if (
        data.media_type != a.media_type
        or data.byte_size != a.byte_size
        or data.byte_size > settings.files_max_bytes
    ):
        raise AuthError("asset_metadata_mismatch", 422)
    policy = db.scalar(
        select(FilePolicy).where(
            FilePolicy.id == data.policy_id,
            FilePolicy.organization_id == org,
            FilePolicy.purpose == "cms_asset",
        )
    )
    if policy is None or (a.media_type != "application/pdf" and policy.max_files < 2):
        raise AuthError("asset_policy_requires_derivative", 422)
    item = files.create_file(
        db, context(a, actor, actor.person_id), actor, metadata, request_id, commit=False
    )
    db.add(
        AssetFile(
            asset_id=a.id,
            organization_id=org,
            owner_person_id=actor.person_id,
            file_id=item.id,
            role="source",
        )
    )
    a.version += 1
    a.visibility = "private"
    a.scan_status = "pending"
    _audit(db, a, actor, "source.bound", request_id)
    _commit(db)
    return view(db, a)


def upload(
    db: Session,
    org: UUID,
    asset_id: UUID,
    actor: User,
    expected_version: int,
    source: BinaryIO,
    storage: PrivateStorage,
    request_id: str,
    settings: Settings,
) -> AssetView:
    authorize(db, org, actor, "create")
    a = asset(db, org, asset_id)
    row = bound(db, a, "source")
    if row is None:
        raise AuthError("not_found", 404)
    ctx = context(a, actor, row.owner_person_id)
    lease = files.begin_upload(
        db,
        ctx,
        actor,
        row.id,
        expected_version,
        request_id,
        lease_seconds=min(900, settings.files_upload_lease_seconds),
    )
    files.receive_upload(db, ctx, actor, lease, source, storage, request_id)
    return view(db, asset(db, org, asset_id))


def prepare(
    db: Session,
    org: UUID,
    asset_id: UUID,
    actor: User,
    data: AssetCommand,
    storage: PrivateStorage,
    request_id: str,
    settings: Settings,
) -> AssetView:
    from app.modules.cms.media_processor import sanitize_image

    authorize(db, org, actor, "create")
    a = asset(db, org, asset_id, True)
    if a.version != data.expected_version or a.visibility == "public":
        raise AuthError("version_conflict", 409)
    source = bound(db, a, "source")
    if not clean(source):
        raise AuthError("asset_not_clean", 409)
    assert source
    if data.expected_file_version != source.version:
        raise AuthError("version_conflict", 409)
    if a.media_type == "application/pdf":
        return view(db, a)
    prepared = bound(db, a, "public_derivative")
    if prepared and prepared.state not in {"pending", "uploading"}:
        return view(db, a)
    policy = db.get(FilePolicy, source.policy_id)
    assert policy
    if policy.state != "published" and prepared is None:
        # A new derivative is new collection. An old source does not authorize
        # bypassing the default retired-policy insert guard.
        raise AuthError("asset_policy_retired", 409)
    source_ref, source_id, owner, policy_id = (
        stored(source),
        source.id,
        source.owner_person_id,
        source.policy_id,
    )
    original_version, media_type, limit = (
        a.version,
        a.media_type,
        min(policy.max_file_bytes, settings.files_max_bytes),
    )
    db.commit()
    try:
        with storage.open(source_ref) as original:
            output = sanitize_image(original, media_type, limit)
    except StorageError:
        raise AuthError("asset_bytes_unavailable", 503) from None
    try:
        a = asset(db, org, asset_id, True)
        db.expire(actor)
        authorize(db, org, actor, "create")
        if a.version != original_version or a.visibility == "public":
            raise AuthError("version_conflict", 409)
        source = bound(db, a, "source")
        if not clean(source) or source is None or source.id != source_id:
            raise AuthError("asset_not_clean", 409)
        output.seek(0, 2)
        size = output.tell()
        output.seek(0)
        measured_digest = hashlib.sha256()
        while chunk := output.read(65536):
            measured_digest.update(chunk)
        digest = measured_digest.hexdigest()
        output.seek(0)
        ctx = context(a, actor, owner)
        item = files.create_file(
            db,
            ctx,
            actor,
            FileCreate(
                client_request_id=uuid5(source_id, "cms-public-image-v1"),
                policy_id=policy_id,
                media_type=source.expected_media_type,
                byte_size=size,
                sha256=digest,
            ),
            request_id,
            commit=False,
        )
        prepared = bound(db, a, "public_derivative")
        if prepared is None:
            db.add(
                AssetFile(
                    asset_id=a.id,
                    organization_id=org,
                    owner_person_id=owner,
                    file_id=item.id,
                    role="public_derivative",
                )
            )
            a.version += 1
            _audit(db, a, actor, "public_derivative.bound", request_id, data.reason)
        _commit(db)
        if item.state in {"pending", "uploading"}:
            lease = files.begin_upload(
                db,
                ctx,
                actor,
                item.id,
                item.version,
                request_id,
                lease_seconds=min(900, settings.files_upload_lease_seconds),
            )
            files.receive_upload(db, ctx, actor, lease, output, storage, request_id)
        return view(db, asset(db, org, asset_id))
    finally:
        output.close()


def publish(
    db: Session, org: UUID, asset_id: UUID, actor: User, data: AssetCommand, request_id: str
) -> AssetView:
    authorize(db, org, actor, "publish")
    a = asset(db, org, asset_id, True)
    if a.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    row = bound(
        db, a, "source" if a.media_type == "application/pdf" else "public_derivative", lock=True
    )
    if not clean(row):
        raise AuthError("asset_not_clean", 409)
    assert row
    if row.version != data.expected_file_version:
        raise AuthError("version_conflict", 409)
    files.freeze_evidence(
        db,
        context(a, actor, row.owner_person_id),
        actor,
        row.id,
        row.version,
        request_id,
        commit=False,
    )
    a.public_file_id, a.public_storage_version, a.public_sha256, a.public_byte_size = (
        row.id,
        row.storage_version,
        row.stored_sha256,
        row.stored_byte_size,
    )
    a.visibility, a.scan_status = "public", "clean"
    a.version += 1
    _audit(db, a, actor, "published", request_id, data.reason)
    _commit(db)
    return view(db, a)


def revoke(
    db: Session, org: UUID, asset_id: UUID, actor: User, data: AssetCommand, request_id: str
) -> AssetView:
    authorize(db, org, actor, "publish")
    a = asset(db, org, asset_id, True)
    if a.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    a.visibility = "private"
    a.public_file_id = None
    a.public_storage_version = None
    a.public_sha256 = None
    a.public_byte_size = None
    a.version += 1
    _audit(db, a, actor, "revoked", request_id, data.reason)
    _commit(db)
    return view(db, a)


def public_file(db: Session, org: UUID, asset_id: UUID) -> tuple[Asset, FileObject]:
    a = asset(db, org, asset_id)
    row = bound(db, a, "source" if a.media_type == "application/pdf" else "public_derivative")
    if (
        row is None
        or not _view(
            a,
            row if a.media_type == "application/pdf" else None,
            row if a.media_type != "application/pdf" else None,
        ).public_url
    ):
        raise AuthError("not_found", 404)
    return a, row
