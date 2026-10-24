from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request

from app.modules.identity.routes import DB, Principal
from app.modules.notifications import participant_service as service
from app.modules.notifications.participant_schemas import (
    ParticipantMarkRead,
    ParticipantNoticeList,
    ParticipantNoticeView,
    ParticipantOutboxHealth,
    ParticipantPreferenceEdit,
    ParticipantPreferenceView,
)

router = APIRouter(
    prefix="/api/v1/participant-notifications/organizations/{org}",
    tags=["participant-notifications"],
)
Limit = Annotated[int, Query(ge=1, le=100)]


@router.get("/mine", response_model=ParticipantNoticeList)
def mine(
    org: UUID, db: DB, identity: Principal, cursor: UUID | None = None, limit: Limit = 25
) -> ParticipantNoticeList:
    items, next_cursor = service.mine(db, org, identity[0], cursor, limit)
    return ParticipantNoticeList(items=items, next_cursor=next_cursor)


@router.get("/preference", response_model=ParticipantPreferenceView)
def preference(org: UUID, db: DB, identity: Principal) -> ParticipantPreferenceView:
    return service.preference(db, org, identity[0])


@router.post("/preference", response_model=ParticipantPreferenceView)
def update_preference(
    org: UUID, data: ParticipantPreferenceEdit, request: Request, db: DB, identity: Principal
) -> ParticipantPreferenceView:
    return service.update_preference(db, org, identity[0], data, request.state.request_id)


@router.post("/{notice_id}/read", response_model=ParticipantNoticeView)
def mark_read(
    org: UUID,
    notice_id: UUID,
    data: ParticipantMarkRead,
    request: Request,
    db: DB,
    identity: Principal,
) -> ParticipantNoticeView:
    return service.mark_read(db, org, identity[0], notice_id, data, request.state.request_id)


@router.get("/operations/health", response_model=ParticipantOutboxHealth)
def health(org: UUID, db: DB, identity: Principal) -> ParticipantOutboxHealth:
    return service.health(db, org, identity[0])
