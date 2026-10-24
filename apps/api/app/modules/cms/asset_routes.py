"""Typed CMS media commands and reauthorized, version-pinned byte delivery."""

import re
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.modules.cms import asset_service as service
from app.modules.cms.models import Asset
from app.modules.cms.schemas import (
    AssetCommand,
    AssetCreate,
    AssetList,
    AssetPolicy,
    AssetSourceCreate,
    AssetView,
)
from app.modules.files import service as files
from app.modules.files.http import bounded_upload, private_download
from app.modules.files.models import FileObject, FilePolicy
from app.modules.files.runtime import get_private_storage, require_files_enabled
from app.modules.identity.models import RefreshSession, User, now
from app.modules.identity.routes import DB, Principal
from app.modules.identity.routes import principal as authenticate_request
from app.modules.identity.security import AuthError
from app.modules.identity.service import require_permission

router = APIRouter()
STAFF = "/cms/organizations/{org}/assets"
PUBLIC = "/public/organizations/{org}/assets"
Limit = Annotated[int, Query(ge=1, le=100)]


@router.post(STAFF, response_model=AssetView, status_code=201)
def create(
    org: UUID, data: AssetCreate, request: Request, db: DB, identity: Principal
) -> AssetView:
    return service.create(db, org, identity[0], data, request.state.request_id)


@router.get(STAFF, response_model=AssetList)
def listing(
    org: UUID, db: DB, identity: Principal, cursor: UUID | None = None, limit: Limit = 25
) -> AssetList:
    require_permission(db, identity[0], org, "cms.asset.view")
    query = select(Asset).where(Asset.organization_id == org)
    if cursor:
        if db.scalar(query.where(Asset.id == cursor)) is None:
            raise AuthError("invalid_cursor", 422)
        query = query.where(Asset.id > cursor)
    rows = list(db.scalars(query.order_by(Asset.id).limit(limit + 1)))
    return AssetList(
        items=service.views(db, rows[:limit]),
        next_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )


@router.get(STAFF + "/policy", response_model=AssetPolicy)
def policy(org: UUID, db: DB, identity: Principal) -> AssetPolicy:
    require_permission(db, identity[0], org, "cms.asset.view")
    settings = get_settings()
    row = db.scalar(
        select(FilePolicy).where(
            FilePolicy.organization_id == org,
            FilePolicy.purpose == "cms_asset",
            FilePolicy.state == "published",
        )
    )
    return AssetPolicy(
        enabled=settings.files_enabled,
        policy=files.policy_view(row) if row else None,
        max_upload_bytes=settings.files_max_bytes,
    )


@router.get(STAFF + "/{asset_id}", response_model=AssetView)
def detail(org: UUID, asset_id: UUID, db: DB, identity: Principal) -> AssetView:
    require_permission(db, identity[0], org, "cms.asset.view")
    return service.view(db, service.asset(db, org, asset_id))


@router.post(STAFF + "/{asset_id}/source", response_model=AssetView, status_code=201)
def source_intent(
    org: UUID,
    asset_id: UUID,
    data: AssetSourceCreate,
    request: Request,
    db: DB,
    identity: Principal,
) -> AssetView:
    settings = require_files_enabled()
    return service.create_source(
        db, org, asset_id, identity[0], data, request.state.request_id, settings
    )


@router.put(STAFF + "/{asset_id}/source/content", response_model=AssetView)
async def source_upload(
    org: UUID, asset_id: UUID, request: Request, db: DB, identity: Principal
) -> AssetView:
    settings = require_files_enabled()
    version, media_type, byte_size = await run_in_threadpool(
        _upload_context, db, org, asset_id, request, identity[0]
    )
    async with bounded_upload(
        request, media_type=media_type, byte_size=byte_size, settings=settings
    ) as source:
        renewed_identity = await run_in_threadpool(_renew_identity, request, db)
        storage = await run_in_threadpool(get_private_storage, settings)
        return await run_in_threadpool(
            service.upload,
            db,
            org,
            asset_id,
            renewed_identity[0],
            version,
            source,
            storage,
            request.state.request_id,
            settings,
        )


def _upload_context(
    db: DB, org: UUID, asset_id: UUID, request: Request, actor: User
) -> tuple[int, str, int]:
    service.authorize(db, org, actor, "create")
    a = service.asset(db, org, asset_id)
    row = service.bound(db, a, "source")
    if row is None:
        raise AuthError("not_found", 404)
    match = request.headers.get("if-match", "")
    if not re.fullmatch(r'"[1-9][0-9]{0,9}"', match) or request.query_params:
        raise AuthError("invalid_request", 422)
    version, media_type, byte_size = (
        int(match[1:-1]),
        row.expected_media_type,
        row.expected_byte_size,
    )
    if row.version != version:
        raise AuthError("version_conflict", 409)
    db.commit()
    return version, media_type, byte_size


def _renew_identity(request: Request, db: DB) -> tuple[User, RefreshSession]:
    # The request Session uses expire_on_commit=False; otherwise reauthentication
    # can reuse the pre-provider cached session/user after a concurrent revocation.
    db.expire_all()
    return authenticate_request(request, db)


@router.get(STAFF + "/{asset_id}/source/content")
def source_download(
    org: UUID, asset_id: UUID, request: Request, db: DB, identity: Principal
) -> StreamingResponse:
    require_files_enabled()
    require_permission(db, identity[0], org, "cms.asset.view")
    a = service.asset(db, org, asset_id)
    row = service.bound(db, a, "source")
    if row is None:
        raise AuthError("not_found", 404)
    result = private_download(get_private_storage(), service.stored(row), row.id)
    db.commit()
    try:
        renewed_identity = _renew_identity(request, db)
        require_permission(db, renewed_identity[0], org, "cms.asset.view")
        current = service.bound(db, service.asset(db, org, asset_id), "source")
        if not service.clean(current):
            raise AuthError("asset_not_clean", 409)
    except Exception:
        _close(result)
        raise
    return result


def _close(result: StreamingResponse) -> None:
    if result.background:
        result.background.func(*result.background.args, **result.background.kwargs)


@router.post(STAFF + "/{asset_id}/prepare", response_model=AssetView)
def prepare(
    org: UUID, asset_id: UUID, data: AssetCommand, request: Request, db: DB, identity: Principal
) -> AssetView:
    settings = require_files_enabled()
    service.authorize(db, org, identity[0], "create")
    return service.prepare(
        db,
        org,
        asset_id,
        identity[0],
        data,
        get_private_storage(settings),
        request.state.request_id,
        settings,
    )


@router.post(STAFF + "/{asset_id}/publish", response_model=AssetView)
def publish(
    org: UUID, asset_id: UUID, data: AssetCommand, request: Request, db: DB, identity: Principal
) -> AssetView:
    require_files_enabled()
    return service.publish(db, org, asset_id, identity[0], data, request.state.request_id)


@router.post(STAFF + "/{asset_id}/revoke", response_model=AssetView)
def revoke(
    org: UUID, asset_id: UUID, data: AssetCommand, request: Request, db: DB, identity: Principal
) -> AssetView:
    return service.revoke(db, org, asset_id, identity[0], data, request.state.request_id)


@router.get(PUBLIC, response_model=AssetList)
def public_listing(org: UUID, db: DB, cursor: UUID | None = None, limit: Limit = 25) -> AssetList:
    if not get_settings().files_enabled:
        return AssetList(items=[], next_cursor=None)
    query = (
        select(Asset)
        .join(FileObject, Asset.public_file_id == FileObject.id)
        .where(
            Asset.organization_id == org,
            Asset.visibility == "public",
            FileObject.state == "clean",
            FileObject.retention_until > now(),
            FileObject.deleted_at.is_(None),
            Asset.public_storage_version == FileObject.storage_version,
            Asset.public_sha256 == FileObject.stored_sha256,
            Asset.public_byte_size == FileObject.stored_byte_size,
        )
    )
    if cursor:
        query = query.where(Asset.id > cursor)
    rows = list(db.scalars(query.order_by(Asset.id).limit(limit + 1)))
    return AssetList(
        items=service.views(db, rows[:limit], public=True),
        next_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )


@router.get(PUBLIC + "/{asset_id}/content")
def public_content(org: UUID, asset_id: UUID, db: DB) -> StreamingResponse:
    require_files_enabled()
    a, row = service.public_file(db, org, asset_id)
    version = a.version
    result = private_download(get_private_storage(), service.stored(row), row.id)
    # Provider verification may take time; recheck revocation before starting delivery.
    db.commit()
    try:
        current, _ = service.public_file(db, org, asset_id)
        if current.version != version:
            raise AuthError("not_found", 404)
    except Exception:
        _close(result)
        raise
    if a.media_type != "application/pdf":
        result.headers["Content-Disposition"] = result.headers["Content-Disposition"].replace(
            "attachment;", "inline;", 1
        )
    result.headers["Cache-Control"] = "no-store"
    return result
