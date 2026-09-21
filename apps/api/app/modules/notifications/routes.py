from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request

from app.modules.identity.routes import DB, Principal
from app.modules.notifications import service
from app.modules.notifications.schemas import (
    MarkRead,
    NotificationList,
    NotificationView,
    PreferenceEdit,
    PreferenceView,
)

router = APIRouter(prefix="/api/v1/notifications/organizations/{org}", tags=["notifications"])
Limit = Annotated[int, Query(ge=1, le=100)]


@router.get("/preference", response_model=PreferenceView)
def preference(org: UUID, db: DB, identity: Principal) -> PreferenceView:
    return service.preference(db, org, identity[0])


@router.post("/preference", response_model=PreferenceView)
def update_preference(
    org: UUID, data: PreferenceEdit, request: Request, db: DB, identity: Principal
) -> PreferenceView:
    return service.update_preference(db, org, identity[0], data, request.state.request_id)


@router.get("/mine", response_model=NotificationList)
def mine(
    org: UUID, db: DB, identity: Principal, cursor: UUID | None = None, limit: Limit = 25
) -> NotificationList:
    items, next_cursor = service.mine(db, org, identity[0], cursor, limit)
    return NotificationList(items=items, next_cursor=next_cursor)


@router.post("/{notification_id}/read", response_model=NotificationView)
def mark_read(
    org: UUID,
    notification_id: UUID,
    data: MarkRead,
    request: Request,
    db: DB,
    identity: Principal,
) -> NotificationView:
    return service.mark_read(db, org, identity[0], notification_id, data, request.state.request_id)
