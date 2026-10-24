import re
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Query, Request
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from app.modules.files.http import bounded_upload, private_download
from app.modules.files.runtime import get_private_storage, require_files_enabled
from app.modules.helpdesk import file_service as service
from app.modules.helpdesk.file_schemas import (
    HelpdeskFileIntent,
    HelpdeskFileList,
    HelpdeskFileQuery,
    HelpdeskFileRemove,
    HelpdeskFileView,
)
from app.modules.identity.routes import DB, Principal, principal
from app.modules.identity.security import AuthError

router = APIRouter(
    prefix="/api/v1/helpdesk/organizations/{org}/tickets/{ticket_id}/files",
    tags=["helpdesk-files"],
)


@router.get("", response_model=HelpdeskFileList)
def listing(
    org: UUID,
    ticket_id: UUID,
    db: DB,
    identity: Principal,
    filters: Annotated[HelpdeskFileQuery, Query()],
) -> HelpdeskFileList:
    return service.listing(db, org, ticket_id, identity[0], filters.cursor, filters.limit)


@router.post("", response_model=HelpdeskFileView, status_code=201)
def create(
    org: UUID,
    ticket_id: UUID,
    data: HelpdeskFileIntent,
    request: Request,
    db: DB,
    identity: Principal,
) -> HelpdeskFileView:
    return service.create(db, org, ticket_id, identity[0], data, request.state.request_id)


@router.get("/{binding_id}", response_model=HelpdeskFileView)
def detail(
    org: UUID, ticket_id: UUID, binding_id: UUID, db: DB, identity: Principal
) -> HelpdeskFileView:
    row, _ = service.binding(db, org, ticket_id, binding_id, identity[0])
    return service.file_view(db, row)


@router.delete("/{binding_id}", response_model=HelpdeskFileView)
def remove(
    org: UUID,
    ticket_id: UUID,
    binding_id: UUID,
    data: HelpdeskFileRemove,
    request: Request,
    db: DB,
    identity: Principal,
) -> HelpdeskFileView:
    return service.remove(
        db, org, ticket_id, binding_id, identity[0], data.expected_version, request.state.request_id
    )


def _reauthenticate(request: Request, db: DB) -> Principal:
    db.expire_all()
    return principal(request, db)


@router.put("/{binding_id}/content", response_model=HelpdeskFileView)
async def upload(
    org: UUID,
    ticket_id: UUID,
    binding_id: UUID,
    request: Request,
    db: DB,
    identity: Principal,
    if_match: Annotated[str | None, Header()] = None,
) -> HelpdeskFileView:
    settings = require_files_enabled()
    if if_match is None or not re.fullmatch(r'"[1-9][0-9]{0,9}"', if_match):
        raise AuthError("file_version_required", 422)
    version = int(if_match[1:-1])
    _, file = await run_in_threadpool(
        service.binding, db, org, ticket_id, binding_id, identity[0], writing=True
    )
    if file.version != version:
        raise AuthError("version_conflict", 409)
    await run_in_threadpool(db.commit)
    async with bounded_upload(
        request,
        media_type=file.expected_media_type,
        byte_size=file.expected_byte_size,
        settings=settings,
    ) as source:
        current = await run_in_threadpool(_reauthenticate, request, db)
        storage = await run_in_threadpool(get_private_storage)
        return await run_in_threadpool(
            service.upload,
            db,
            org,
            ticket_id,
            binding_id,
            current[0],
            version,
            source,
            storage,
            request.state.request_id,
        )


@router.get("/{binding_id}/content")
async def download(
    org: UUID, ticket_id: UUID, binding_id: UUID, request: Request, db: DB, identity: Principal
) -> StreamingResponse:
    file_id, ref = await run_in_threadpool(
        service.download_reference, db, org, ticket_id, binding_id, identity[0]
    )
    storage = await run_in_threadpool(get_private_storage)
    response = await run_in_threadpool(private_download, storage, ref, file_id)
    try:
        current = await run_in_threadpool(_reauthenticate, request, db)
        await run_in_threadpool(
            service.record_download,
            db,
            org,
            ticket_id,
            binding_id,
            current[0],
            request.state.request_id,
        )
    except BaseException:
        if response.background:
            await response.background()
        raise
    return response
