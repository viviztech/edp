import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Query, Request, Response

from app.modules.identity.routes import DB, Principal
from app.modules.identity.security import AuthError
from app.modules.meta import service
from app.modules.meta.schemas import (
    EventList,
    IntegrationCreate,
    IntegrationList,
    IntegrationView,
    MappingCreate,
    MappingList,
    MappingView,
    WebhookAccepted,
)

router = APIRouter(prefix="/api/v1", tags=["meta"])
Limit = Annotated[int, Query(ge=1, le=100)]


@router.post(
    "/meta/organizations/{org}/integrations",
    response_model=IntegrationView,
    status_code=201,
)
def create_integration(
    org: UUID,
    data: IntegrationCreate,
    request: Request,
    db: DB,
    identity: Principal,
) -> IntegrationView:
    return service.create_integration(db, org, identity[0], data, request.state.request_id)


@router.get("/meta/organizations/{org}/integrations", response_model=IntegrationList)
def list_integrations(
    org: UUID,
    db: DB,
    identity: Principal,
    cursor: UUID | None = None,
    limit: Limit = 25,
) -> IntegrationList:
    items, next_cursor = service.integrations(db, org, identity[0], cursor, limit)
    return IntegrationList(items=items, next_cursor=next_cursor)


@router.post(
    "/meta/organizations/{org}/integrations/{integration_id}/mappings",
    response_model=MappingView,
    status_code=201,
)
def create_mapping(
    org: UUID,
    integration_id: UUID,
    data: MappingCreate,
    request: Request,
    db: DB,
    identity: Principal,
) -> MappingView:
    return service.create_mapping(
        db,
        org,
        integration_id,
        identity[0],
        data,
        request.state.request_id,
    )


@router.get(
    "/meta/organizations/{org}/integrations/{integration_id}/mappings",
    response_model=MappingList,
)
def list_mappings(org: UUID, integration_id: UUID, db: DB, identity: Principal) -> MappingList:
    return MappingList(items=service.mappings(db, org, integration_id, identity[0]))


@router.get("/meta/organizations/{org}/events", response_model=EventList)
def list_events(
    org: UUID,
    db: DB,
    identity: Principal,
    cursor: UUID | None = None,
    limit: Limit = 25,
) -> EventList:
    items, next_cursor = service.events(db, org, identity[0], cursor, limit)
    return EventList(items=items, next_cursor=next_cursor)


@router.get("/integrations/meta/webhook/{integration_id}")
def verify_webhook(
    integration_id: UUID,
    db: DB,
    mode: Annotated[str, Query(alias="hub.mode", max_length=32)],
    verify_token: Annotated[str, Query(alias="hub.verify_token", min_length=1, max_length=512)],
    challenge: Annotated[str, Query(alias="hub.challenge", min_length=1, max_length=512)],
) -> Response:
    value = service.verify_challenge(db, integration_id, mode, verify_token, challenge)
    return Response(content=value, media_type="text/plain")


@router.post(
    "/integrations/meta/webhook/{integration_id}",
    response_model=WebhookAccepted,
    status_code=202,
)
async def receive_webhook(
    integration_id: UUID,
    request: Request,
    db: DB,
    signature: Annotated[str, Header(alias="X-Hub-Signature-256", max_length=80)],
) -> WebhookAccepted:
    body = await request.body()
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise AuthError("invalid_webhook_payload", 400) from exc
    if not isinstance(payload, dict):
        raise AuthError("invalid_webhook_payload", 400)
    accepted, duplicates = service.ingest(
        db,
        integration_id,
        body,
        payload,
        signature,
        request.state.request_id,
    )
    return WebhookAccepted(accepted=accepted, duplicates=duplicates)
