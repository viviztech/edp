from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response

from app.modules.helpdesk import service
from app.modules.helpdesk.schemas import (
    AssigneeList,
    AssignmentChange,
    Category,
    HelpdeskPreferenceView,
    HistoryList,
    MessageCreate,
    MessageList,
    NoticeList,
    NoticeView,
    PreferenceChange,
    Priority,
    PriorityChange,
    ReadNotice,
    StatusChange,
    TicketCommand,
    TicketCreate,
    TicketList,
    TicketStatus,
    TicketView,
)
from app.modules.identity.routes import DB, Principal

router = APIRouter(prefix="/api/v1/helpdesk/organizations/{org}", tags=["helpdesk"])
Limit = Annotated[int, Query(ge=1, le=100)]


@router.get("/tickets", response_model=TicketList)
def listing(
    org: UUID,
    db: DB,
    identity: Principal,
    queue: Literal["mine", "assigned", "unassigned", "organization"] = "assigned",
    status: TicketStatus | None = None,
    category: Category | None = None,
    priority: Priority | None = None,
    cursor: UUID | None = None,
    limit: Limit = 25,
) -> TicketList:
    return service.listing(db, org, identity[0], queue, status, category, priority, cursor, limit)


@router.post("/tickets", response_model=TicketView, status_code=201)
def create(
    org: UUID, data: TicketCreate, request: Request, db: DB, identity: Principal
) -> TicketView:
    return service.create(db, org, identity[0], data, request.state.request_id)


@router.get("/tickets/{ticket_id}", response_model=TicketView)
def detail(org: UUID, ticket_id: UUID, db: DB, identity: Principal) -> TicketView:
    return service.detail(db, org, ticket_id, identity[0])


@router.get("/tickets/{ticket_id}/messages", response_model=MessageList)
def messages(
    org: UUID,
    ticket_id: UUID,
    db: DB,
    identity: Principal,
    cursor: UUID | None = None,
    limit: Limit = 25,
) -> MessageList:
    return service.messages(db, org, ticket_id, identity[0], cursor, limit)


@router.post("/tickets/{ticket_id}/messages", response_model=TicketView)
def reply(
    org: UUID, ticket_id: UUID, data: MessageCreate, request: Request, db: DB, identity: Principal
) -> TicketView:
    return service.reply(db, org, ticket_id, identity[0], data, request.state.request_id)


@router.get("/tickets/{ticket_id}/history", response_model=HistoryList)
def history(
    org: UUID,
    ticket_id: UUID,
    db: DB,
    identity: Principal,
    cursor: UUID | None = None,
    limit: Limit = 25,
) -> HistoryList:
    return service.history(db, org, ticket_id, identity[0], cursor, limit)


@router.post("/tickets/{ticket_id}/assignment", response_model=TicketView)
def assignment(
    org: UUID,
    ticket_id: UUID,
    data: AssignmentChange,
    request: Request,
    db: DB,
    identity: Principal,
) -> TicketView:
    return service.assign(db, org, ticket_id, identity[0], data, request.state.request_id)


@router.post("/tickets/{ticket_id}/priority", response_model=TicketView)
def priority(
    org: UUID, ticket_id: UUID, data: PriorityChange, request: Request, db: DB, identity: Principal
) -> TicketView:
    return service.priority_change(db, org, ticket_id, identity[0], data, request.state.request_id)


@router.post("/tickets/{ticket_id}/status", response_model=TicketView)
def status(
    org: UUID, ticket_id: UUID, data: StatusChange, request: Request, db: DB, identity: Principal
) -> TicketView:
    return service.status_change(db, org, ticket_id, identity[0], data, request.state.request_id)


@router.post("/tickets/{ticket_id}/reopen", response_model=TicketView)
def reopen(
    org: UUID, ticket_id: UUID, data: TicketCommand, request: Request, db: DB, identity: Principal
) -> TicketView:
    return service.reopen(db, org, ticket_id, identity[0], data, request.state.request_id)


@router.get(
    "/tickets/{ticket_id}/attachments/{attachment_id}",
    response_class=Response,
    responses={200: {"content": {"text/plain": {"schema": {"type": "string"}}}}},
)
def attachment(
    org: UUID, ticket_id: UUID, attachment_id: UUID, request: Request, db: DB, identity: Principal
) -> Response:
    row = service.attachment(
        db, org, ticket_id, attachment_id, identity[0], request.state.request_id
    )
    return Response(
        content=row.content.encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="helpdesk-attachment.txt"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/assignees", response_model=AssigneeList)
def assignees(
    org: UUID, db: DB, identity: Principal, cursor: UUID | None = None, limit: Limit = 25
) -> AssigneeList:
    return service.assignees(db, org, identity[0], cursor, limit)


@router.get("/notices", response_model=NoticeList)
def notices(
    org: UUID, db: DB, identity: Principal, cursor: UUID | None = None, limit: Limit = 25
) -> NoticeList:
    return service.notices(db, org, identity[0], cursor, limit)


@router.post("/notices/{notice_id}/read", response_model=NoticeView)
def read_notice(
    org: UUID, notice_id: UUID, data: ReadNotice, request: Request, db: DB, identity: Principal
) -> NoticeView:
    return service.read_notice(
        db, org, identity[0], notice_id, data.expected_version, request.state.request_id
    )


@router.get("/preference", response_model=HelpdeskPreferenceView)
def preference(org: UUID, db: DB, identity: Principal) -> HelpdeskPreferenceView:
    return service.preference(db, org, identity[0])


@router.post("/preference", response_model=HelpdeskPreferenceView)
def preference_change(
    org: UUID, data: PreferenceChange, request: Request, db: DB, identity: Principal
) -> HelpdeskPreferenceView:
    return service.preference(db, org, identity[0], data, request.state.request_id)
