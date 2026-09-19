from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response
from sqlalchemy import select

from app.modules.crm import service
from app.modules.crm.models import DuplicateReview, Lead, LeadActivity
from app.modules.crm.schemas import (
    ActivityComplete,
    ActivityCreate,
    ActivityList,
    ActivityView,
    DuplicateResolve,
    DuplicateReviewCreate,
    DuplicateReviewList,
    DuplicateReviewView,
    ExportJobView,
    LeadConversionCreate,
    LeadConversionView,
    LeadCreate,
    LeadEdit,
    LeadList,
    LeadView,
    TagCreate,
    TagList,
    TagView,
)
from app.modules.identity.models import now
from app.modules.identity.routes import DB, Principal
from app.modules.identity.service import require_permission

router = APIRouter(prefix="/api/v1", tags=["crm"])
Limit = Annotated[int, Query(ge=1, le=100)]


@router.post("/crm/organizations/{org}/leads", response_model=LeadView, status_code=201)
def create(org: UUID, data: LeadCreate, request: Request, db: DB, identity: Principal) -> LeadView:
    return service.create(db, org, identity[0], data, request.state.request_id)


@router.get("/crm/organizations/{org}/leads", response_model=LeadList)
def list_leads(
    org: UUID,
    db: DB,
    identity: Principal,
    cursor: UUID | None = None,
    limit: Limit = 25,
    overdue: bool = False,
) -> LeadList:
    require_permission(db, identity[0], org, "crm.lead.view")
    q = select(Lead).where(Lead.organization_id == org)
    if overdue:
        q = q.where(
            select(LeadActivity.id)
            .where(
                LeadActivity.lead_id == Lead.id,
                LeadActivity.organization_id == org,
                LeadActivity.due_at < now(),
                LeadActivity.completed_at.is_(None),
            )
            .exists()
        )
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
    "/crm/organizations/{org}/leads/{lead_id}/activities/{activity_id}/complete",
    response_model=ActivityView,
)
def complete_activity(
    org: UUID,
    lead_id: UUID,
    activity_id: UUID,
    data: ActivityComplete,
    request: Request,
    db: DB,
    identity: Principal,
) -> ActivityView:
    return service.complete_activity(
        db, org, lead_id, activity_id, identity[0], data, request.state.request_id
    )


@router.post("/crm/organizations/{org}/tags", response_model=TagView, status_code=201)
def create_tag(
    org: UUID, data: TagCreate, request: Request, db: DB, identity: Principal
) -> TagView:
    return service.create_tag(db, org, identity[0], data, request.state.request_id)


@router.get("/crm/organizations/{org}/tags", response_model=TagList)
def list_tags(org: UUID, db: DB, identity: Principal) -> TagList:
    return TagList(items=service.tags(db, org, identity[0]))


@router.get(
    "/crm/organizations/{org}/leads/{lead_id}/tags",
    response_model=TagList,
)
def list_lead_tags(org: UUID, lead_id: UUID, db: DB, identity: Principal) -> TagList:
    return TagList(items=service.lead_tags(db, org, lead_id, identity[0]))


@router.post(
    "/crm/organizations/{org}/leads/{lead_id}/tags/{tag_id}/attach",
    response_model=TagView,
)
def attach_tag(
    org: UUID,
    lead_id: UUID,
    tag_id: UUID,
    request: Request,
    db: DB,
    identity: Principal,
) -> TagView:
    return service.attach_tag(db, org, lead_id, tag_id, identity[0], request.state.request_id)


@router.post(
    "/crm/organizations/{org}/leads/{lead_id}/tags/{tag_id}/detach",
    status_code=204,
)
def detach_tag(
    org: UUID,
    lead_id: UUID,
    tag_id: UUID,
    request: Request,
    db: DB,
    identity: Principal,
) -> Response:
    service.detach_tag(db, org, lead_id, tag_id, identity[0], request.state.request_id)
    return Response(status_code=204)


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


@router.post("/crm/organizations/{org}/exports", response_model=ExportJobView, status_code=202)
def request_export(org: UUID, request: Request, db: DB, identity: Principal) -> ExportJobView:
    return service.request_export(db, org, identity[0], request.state.request_id)


@router.get("/crm/organizations/{org}/exports/{job_id}", response_model=ExportJobView)
def export_status(org: UUID, job_id: UUID, db: DB, identity: Principal) -> ExportJobView:
    return service.export_view(service.get_export(db, org, job_id, identity[0]))


@router.get("/crm/organizations/{org}/exports/{job_id}/download")
def export_download(
    org: UUID, job_id: UUID, request: Request, db: DB, identity: Principal
) -> Response:
    content = service.download_export(db, org, job_id, identity[0], request.state.request_id)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="crm-leads-{job_id}.csv"',
            "Cache-Control": "private, no-store",
        },
    )


@router.post(
    "/crm/organizations/{org}/leads/{lead_id}/registration-link",
    response_model=LeadConversionView,
    status_code=201,
)
def link_registration(
    org: UUID,
    lead_id: UUID,
    data: LeadConversionCreate,
    request: Request,
    db: DB,
    identity: Principal,
) -> LeadConversionView:
    return service.link_registration(db, org, lead_id, identity[0], data, request.state.request_id)


@router.get(
    "/crm/organizations/{org}/leads/{lead_id}/registration-link",
    response_model=LeadConversionView,
)
def registration_link(org: UUID, lead_id: UUID, db: DB, identity: Principal) -> LeadConversionView:
    return service.get_registration_link(db, org, lead_id, identity[0])
