from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request
from sqlalchemy import select

from app.modules.crm import service
from app.modules.crm.models import DuplicateReview, Lead
from app.modules.crm.schemas import (
    ActivityCreate,
    ActivityList,
    ActivityView,
    DuplicateResolve,
    DuplicateReviewCreate,
    DuplicateReviewList,
    DuplicateReviewView,
    LeadCreate,
    LeadEdit,
    LeadList,
    LeadView,
)
from app.modules.identity.routes import DB, Principal
from app.modules.identity.service import require_permission

router = APIRouter(prefix="/api/v1", tags=["crm"])
Limit = Annotated[int, Query(ge=1, le=100)]


@router.post("/crm/organizations/{org}/leads", response_model=LeadView, status_code=201)
def create(org: UUID, data: LeadCreate, request: Request, db: DB, identity: Principal) -> LeadView:
    return service.create(db, org, identity[0], data, request.state.request_id)


@router.get("/crm/organizations/{org}/leads", response_model=LeadList)
def list_leads(
    org: UUID, db: DB, identity: Principal, cursor: UUID | None = None, limit: Limit = 25
) -> LeadList:
    require_permission(db, identity[0], org, "crm.lead.view")
    q = select(Lead).where(Lead.organization_id == org)
    q = q.where(Lead.id > cursor) if cursor else q
    rows = list(db.scalars(q.order_by(Lead.id).limit(limit + 1)))
    return LeadList(
        items=[service.view(x) for x in rows[:limit]],
        next_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )


@router.patch("/crm/organizations/{org}/leads/{lead_id}", response_model=LeadView)
def edit(
    org: UUID, lead_id: UUID, data: LeadEdit, request: Request, db: DB, identity: Principal
) -> LeadView:
    return service.mutate(db, org, lead_id, identity[0], data, request.state.request_id)


@router.post(
    "/crm/organizations/{org}/leads/{lead_id}/activities",
    response_model=ActivityView,
    status_code=201,
)
def add_activity(
    org: UUID, lead_id: UUID, data: ActivityCreate, request: Request, db: DB, identity: Principal
) -> ActivityView:
    return service.add_activity(db, org, lead_id, identity[0], data, request.state.request_id)


@router.get("/crm/organizations/{org}/leads/{lead_id}/activities", response_model=ActivityList)
def list_activities(
    org: UUID, lead_id: UUID, db: DB, identity: Principal, limit: Limit = 25
) -> ActivityList:
    return ActivityList(items=service.activities(db, org, lead_id, identity[0], limit))


@router.post(
    "/crm/organizations/{org}/duplicate-reviews",
    response_model=DuplicateReviewView,
    status_code=201,
)
def create_duplicate_review(
    org: UUID, data: DuplicateReviewCreate, request: Request, db: DB, identity: Principal
) -> DuplicateReviewView:
    return service.create_duplicate_review(db, org, identity[0], data, request.state.request_id)


@router.get("/crm/organizations/{org}/duplicate-reviews", response_model=DuplicateReviewList)
def list_duplicate_reviews(
    org: UUID, db: DB, identity: Principal, cursor: UUID | None = None, limit: Limit = 25
) -> DuplicateReviewList:
    require_permission(db, identity[0], org, "crm.lead.merge")
    q = select(DuplicateReview).where(DuplicateReview.organization_id == org)
    q = q.where(DuplicateReview.id > cursor) if cursor else q
    rows = list(db.scalars(q.order_by(DuplicateReview.id).limit(limit + 1)))
    return DuplicateReviewList(
        items=[service.duplicate_view(x) for x in rows[:limit]],
        next_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )


@router.post(
    "/crm/organizations/{org}/duplicate-reviews/{review_id}/resolve",
    response_model=DuplicateReviewView,
)
def resolve_duplicate_review(
    org: UUID,
    review_id: UUID,
    data: DuplicateResolve,
    request: Request,
    db: DB,
    identity: Principal,
) -> DuplicateReviewView:
    return service.resolve_duplicate_review(
        db, org, review_id, identity[0], data, request.state.request_id
    )
