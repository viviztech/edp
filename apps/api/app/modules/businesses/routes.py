from uuid import UUID

from fastapi import APIRouter, Request

from app.modules.businesses import service
from app.modules.businesses.schemas import (
    CreateProfile,
    MyBusinesses,
    OutcomeCreate,
    OutcomeView,
    PolicyUpdate,
    PolicyView,
    ProfileView,
    StaffDashboard,
    UpdateProfile,
)
from app.modules.identity.routes import DB, Principal

router = APIRouter(prefix="/api/v1/businesses/organizations/{org}", tags=["businesses"])


@router.get("/mine", response_model=MyBusinesses)
def mine(org: UUID, db: DB, identity: Principal) -> MyBusinesses:
    return service.mine(db, org, identity[0])


@router.post("/profiles", response_model=ProfileView, status_code=201)
def create(
    org: UUID, data: CreateProfile, request: Request, db: DB, identity: Principal
) -> ProfileView:
    return service.create_profile(db, org, identity[0], data, request.state.request_id)


@router.post("/profiles/{profile_id}/update", response_model=ProfileView)
def update(
    org: UUID, profile_id: UUID, data: UpdateProfile, request: Request, db: DB, identity: Principal
) -> ProfileView:
    return service.update_profile(db, org, identity[0], profile_id, data, request.state.request_id)


@router.post("/follow-ups/{follow_up_id}/outcome", response_model=OutcomeView, status_code=201)
def outcome(
    org: UUID,
    follow_up_id: UUID,
    data: OutcomeCreate,
    request: Request,
    db: DB,
    identity: Principal,
) -> OutcomeView:
    return service.submit_outcome(
        db, org, identity[0], follow_up_id, data, request.state.request_id
    )


@router.get("/staff", response_model=StaffDashboard)
def staff(org: UUID, db: DB, identity: Principal) -> StaffDashboard:
    return service.staff_dashboard(db, org, identity[0])


@router.post("/policy", response_model=PolicyView)
def policy(
    org: UUID, data: PolicyUpdate, request: Request, db: DB, identity: Principal
) -> PolicyView:
    return service.update_policy(db, org, identity[0], data, request.state.request_id)
