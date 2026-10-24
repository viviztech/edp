from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Query, Request
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.modules.applications import document_service as service
from app.modules.applications.document_schemas import (
    ApplicationDocumentList,
    ApplicationDocumentResult,
    DocumentCreate,
    DocumentQuery,
    DocumentRemove,
)
from app.modules.files.http import bounded_upload, private_download
from app.modules.files.runtime import get_private_storage
from app.modules.identity.routes import DB, Principal, principal
from app.modules.identity.security import AuthError

owner_router = APIRouter(prefix="/organizations/{org}/applications/{application_id}/documents")
reviewer_router = APIRouter(
    prefix="/api/v1/selection/organizations/{org}/assignments/{assignment_id}/documents",
    tags=["application-documents"],
)


@owner_router.get("", response_model=ApplicationDocumentList)
def documents(
    org: UUID,
    application_id: UUID,
    db: DB,
    identity: Principal,
    filters: Annotated[DocumentQuery, Query()],
) -> ApplicationDocumentList:
    return service.list_documents(
        db, org, application_id, identity[0], filters.cursor, filters.limit
    )


@owner_router.post("", response_model=ApplicationDocumentResult, status_code=201)
def create(
    org: UUID,
    application_id: UUID,
    data: DocumentCreate,
    request: Request,
    db: DB,
    identity: Principal,
) -> ApplicationDocumentResult:
    return service.create_document(
        db, org, application_id, identity[0], data, request.state.request_id
    )


@owner_router.get("/{document_id}", response_model=ApplicationDocumentResult)
def detail(
    org: UUID, application_id: UUID, document_id: UUID, db: DB, identity: Principal
) -> ApplicationDocumentResult:
    return service.get_document(db, org, application_id, document_id, identity[0])


@owner_router.delete("/{document_id}", response_model=ApplicationDocumentResult)
def remove(
    org: UUID,
    application_id: UUID,
    document_id: UUID,
    data: DocumentRemove,
    request: Request,
    db: DB,
    identity: Principal,
) -> ApplicationDocumentResult:
    return service.remove_document(
        db, org, application_id, document_id, identity[0], data, request.state.request_id
    )


def _version(value: str | None) -> int:
    if (
        value is None
        or len(value) > 12
        or not value.startswith('"')
        or not value.endswith('"')
        or not value[1:-1].isascii()
        or not value[1:-1].isdecimal()
        or not 1 <= int(value[1:-1]) <= 2147483647
    ):
        raise AuthError("file_version_required", 422)
    return int(value[1:-1])


def _reauthenticate(request: Request, db: DB) -> Principal:
    # Buffered bytes and provider verification may outlive a revoked session.
    db.expire_all()
    return principal(request, db)


@owner_router.put("/{document_id}/content", response_model=ApplicationDocumentResult)
async def upload(
    org: UUID,
    application_id: UUID,
    document_id: UUID,
    request: Request,
    db: DB,
    identity: Principal,
    if_match: Annotated[str | None, Header()] = None,
) -> ApplicationDocumentResult:
    version = _version(if_match)
    _, _, file = await run_in_threadpool(
        service.authorize_upload, db, org, application_id, document_id, identity[0]
    )
    await run_in_threadpool(db.commit)  # No domain locks span the untrusted body deadline.
    async with bounded_upload(
        request, media_type=file.media_type, byte_size=file.byte_size, settings=get_settings()
    ) as source:
        current_identity = await run_in_threadpool(_reauthenticate, request, db)
        storage = await run_in_threadpool(get_private_storage)
        return await run_in_threadpool(
            service.upload_document,
            db,
            org,
            application_id,
            document_id,
            current_identity[0],
            version,
            source,
            storage,
            request.state.request_id,
        )


@owner_router.get("/{document_id}/content")
async def download(
    org: UUID,
    application_id: UUID,
    document_id: UUID,
    request: Request,
    db: DB,
    identity: Principal,
) -> StreamingResponse:
    file_id, ref = await run_in_threadpool(
        service.owner_download, db, org, application_id, document_id, identity[0]
    )
    storage = await run_in_threadpool(get_private_storage)
    response = await run_in_threadpool(private_download, storage, ref, file_id)
    try:
        current_identity = await run_in_threadpool(_reauthenticate, request, db)
        await run_in_threadpool(
            service.owner_download, db, org, application_id, document_id, current_identity[0]
        )
    except BaseException:
        if response.background:
            await response.background()
        raise
    return response


@reviewer_router.get("", response_model=ApplicationDocumentList)
def reviewer_documents(
    org: UUID,
    assignment_id: UUID,
    db: DB,
    identity: Principal,
    filters: Annotated[DocumentQuery, Query()],
) -> ApplicationDocumentList:
    return service.reviewer_documents(
        db, org, assignment_id, identity[0], filters.cursor, filters.limit
    )


@reviewer_router.get("/{document_id}/content")
async def reviewer_download(
    org: UUID, assignment_id: UUID, document_id: UUID, request: Request, db: DB, identity: Principal
) -> StreamingResponse:
    file_id, ref = await run_in_threadpool(
        service.reviewer_download, db, org, assignment_id, document_id, identity[0]
    )
    storage = await run_in_threadpool(get_private_storage)
    response = await run_in_threadpool(private_download, storage, ref, file_id)
    try:
        current_identity = await run_in_threadpool(_reauthenticate, request, db)
        await run_in_threadpool(
            service.reviewer_download, db, org, assignment_id, document_id, current_identity[0]
        )
    except BaseException:
        if response.background:
            await response.background()
        raise
    return response
