from uuid import UUID

from fastapi import APIRouter, Request

from app.modules.business_plans import service
from app.modules.business_plans.schemas import (
    MentorPlans,
    MyPlans,
    PlanView,
    ReviewPlan,
    ReviewView,
    SaveSection,
    SubmitPlan,
)
from app.modules.identity.routes import DB, Principal

router = APIRouter(prefix="/api/v1/business-plans/organizations/{org}", tags=["business-plans"])


@router.get("/mine", response_model=MyPlans)
def mine(org: UUID, db: DB, identity: Principal) -> MyPlans:
    return service.my_plans(db, org, identity[0])


@router.post("/enrollments/{enrollment_id}", response_model=PlanView, status_code=201)
def create(
    org: UUID, enrollment_id: UUID, request: Request, db: DB, identity: Principal
) -> PlanView:
    return service.create_plan(db, org, identity[0], enrollment_id, request.state.request_id)


@router.post("/enrollments/{enrollment_id}/sections", response_model=PlanView)
def save(
    org: UUID, enrollment_id: UUID, data: SaveSection,
    request: Request, db: DB, identity: Principal,
) -> PlanView:
    return service.save_section(
        db, org, identity[0], enrollment_id, data, request.state.request_id
    )


@router.post("/enrollments/{enrollment_id}/submit", response_model=PlanView)
def submit(
    org: UUID, enrollment_id: UUID, data: SubmitPlan,
    request: Request, db: DB, identity: Principal,
) -> PlanView:
    return service.submit_plan(db, org, identity[0], enrollment_id, data, request.state.request_id)


@router.get("/assigned", response_model=MentorPlans)
def assigned(org: UUID, db: DB, identity: Principal) -> MentorPlans:
    return service.assigned_submissions(db, org, identity[0])


@router.post("/submissions/{submission_id}/review", response_model=ReviewView)
def review(
    org: UUID, submission_id: UUID, data: ReviewPlan,
    request: Request, db: DB, identity: Principal,
) -> ReviewView:
    return service.review_submission(
        db, org, identity[0], submission_id, data, request.state.request_id
    )
