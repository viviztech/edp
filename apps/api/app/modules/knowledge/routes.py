from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response

from app.modules.identity.routes import DB, Principal
from app.modules.identity.service import require_permission
from app.modules.knowledge import service
from app.modules.knowledge.schemas import (
    FundingCaseCreate,
    FundingCaseList,
    FundingCaseView,
    FundingStatus,
    FundingStatusChange,
    KnowledgeCommand,
    KnowledgeCreate,
    KnowledgeEdit,
    KnowledgeFilters,
    KnowledgeHistory,
    KnowledgeInterestView,
    KnowledgeList,
    KnowledgeMine,
    KnowledgeSavedView,
    KnowledgeView,
)

router = APIRouter(prefix="/api/v1/knowledge/organizations/{org}", tags=["knowledge"])
public_router = APIRouter(
    prefix="/api/v1/public/organizations/{org}/knowledge", tags=["knowledge-public"]
)
Filters = Annotated[KnowledgeFilters, Query()]
Limit = Annotated[int, Query(ge=1, le=100)]


@public_router.get("", response_model=KnowledgeList)
def public_list(org: UUID, db: DB, filters: Filters) -> KnowledgeList:
    return service.listing(db, org, audience="public", filters=filters)


@public_router.get("/{item_id}", response_model=KnowledgeView)
def public_detail(org: UUID, item_id: UUID, db: DB) -> KnowledgeView:
    return service.view(db, service.catalog_item(db, org, item_id, "public"))


@router.get("/items", response_model=KnowledgeList)
def staff_list(org: UUID, db: DB, identity: Principal, filters: Filters) -> KnowledgeList:
    require_permission(db, identity[0], org, "knowledge.manage")
    return service.listing(db, org, audience="staff", filters=filters)


@router.post("/items", response_model=KnowledgeView, status_code=201)
def create(
    org: UUID, data: KnowledgeCreate, request: Request, db: DB, identity: Principal
) -> KnowledgeView:
    return service.create(db, org, identity[0], data, request.state.request_id)


@router.get("/items/{item_id}", response_model=KnowledgeView)
def detail(org: UUID, item_id: UUID, db: DB, identity: Principal) -> KnowledgeView:
    require_permission(db, identity[0], org, "knowledge.manage")
    return service.view(db, service.item(db, org, item_id))


@router.patch("/items/{item_id}", response_model=KnowledgeView)
def edit(
    org: UUID, item_id: UUID, data: KnowledgeEdit, request: Request, db: DB, identity: Principal
) -> KnowledgeView:
    return service.edit(db, org, item_id, identity[0], data, request.state.request_id)


@router.post("/items/{item_id}/publish", response_model=KnowledgeView)
def publish(
    org: UUID, item_id: UUID, data: KnowledgeCommand, request: Request, db: DB, identity: Principal
) -> KnowledgeView:
    return service.command(
        db, org, item_id, identity[0], data, "published", request.state.request_id
    )


@router.post("/items/{item_id}/archive", response_model=KnowledgeView)
def archive(
    org: UUID, item_id: UUID, data: KnowledgeCommand, request: Request, db: DB, identity: Principal
) -> KnowledgeView:
    return service.command(
        db, org, item_id, identity[0], data, "archived", request.state.request_id
    )


@router.post("/items/{item_id}/draft", response_model=KnowledgeView)
def draft(
    org: UUID, item_id: UUID, data: KnowledgeCommand, request: Request, db: DB, identity: Principal
) -> KnowledgeView:
    return service.command(db, org, item_id, identity[0], data, "draft", request.state.request_id)


@router.get("/items/{item_id}/history", response_model=KnowledgeHistory)
def history(
    org: UUID,
    item_id: UUID,
    db: DB,
    identity: Principal,
    cursor: UUID | None = None,
    limit: Limit = 25,
) -> KnowledgeHistory:
    return service.history(db, org, item_id, identity[0], cursor, limit)


@router.get("/catalog", response_model=KnowledgeList)
def catalog(org: UUID, db: DB, identity: Principal, filters: Filters) -> KnowledgeList:
    service.participant(db, org, identity[0])
    return service.listing(db, org, audience="participants", filters=filters)


@router.get("/catalog/{item_id}", response_model=KnowledgeView)
def catalog_detail(org: UUID, item_id: UUID, db: DB, identity: Principal) -> KnowledgeView:
    service.participant(db, org, identity[0])
    return service.view(db, service.catalog_item(db, org, item_id, "participants"))


@router.get("/mine", response_model=KnowledgeMine)
def mine(
    org: UUID,
    db: DB,
    identity: Principal,
    saved_cursor: UUID | None = None,
    interest_cursor: UUID | None = None,
    case_cursor: UUID | None = None,
    limit: Limit = 25,
) -> KnowledgeMine:
    return service.mine(db, org, identity[0], saved_cursor, interest_cursor, case_cursor, limit)


@router.post("/saved/{item_id}", response_model=KnowledgeSavedView)
def save(
    org: UUID, item_id: UUID, request: Request, db: DB, identity: Principal
) -> KnowledgeSavedView:
    return service.save(db, org, identity[0], item_id, request.state.request_id)


@router.delete("/saved/{item_id}", status_code=204)
def unsave(org: UUID, item_id: UUID, request: Request, db: DB, identity: Principal) -> Response:
    service.unsave(db, org, identity[0], item_id, request.state.request_id)
    return Response(status_code=204)


@router.post("/interests/{item_id}", response_model=KnowledgeInterestView, status_code=201)
def interest(
    org: UUID, item_id: UUID, request: Request, db: DB, identity: Principal
) -> KnowledgeInterestView:
    return service.interest(db, org, identity[0], item_id, request.state.request_id)


@router.get("/funding-cases", response_model=FundingCaseList)
def cases(
    org: UUID,
    db: DB,
    identity: Principal,
    status: FundingStatus | None = None,
    cursor: UUID | None = None,
    limit: Limit = 25,
) -> FundingCaseList:
    return service.cases(db, org, identity[0], status, cursor, limit)


@router.post("/funding-cases", response_model=FundingCaseView, status_code=201)
def create_case(
    org: UUID, data: FundingCaseCreate, request: Request, db: DB, identity: Principal
) -> FundingCaseView:
    return service.create_case(db, org, identity[0], data.item_id, request.state.request_id)


@router.post("/funding-cases/{case_id}/status", response_model=FundingCaseView)
def update_case(
    org: UUID,
    case_id: UUID,
    data: FundingStatusChange,
    request: Request,
    db: DB,
    identity: Principal,
) -> FundingCaseView:
    return service.update_case(db, org, identity[0], case_id, data, request.state.request_id)
