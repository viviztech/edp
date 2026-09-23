from uuid import UUID

from fastapi import APIRouter, Request

from app.modules.applications import service
from app.modules.applications.schemas import DraftSave, DraftView, FormView
from app.modules.identity.routes import DB, Principal

router = APIRouter(prefix="/api/v1/applications/organizations/{org}", tags=["applications"])


@router.get("/form", response_model=FormView)
def form(org: UUID, db: DB, identity: Principal) -> FormView:
    return service.get_form(db, org)


@router.post("/draft", response_model=DraftView, status_code=201)
def create_draft(org: UUID, request: Request, db: DB, identity: Principal) -> DraftView:
    return service.create_draft(db, org, identity[0], request.state.request_id)


@router.get("/draft", response_model=DraftView)
def draft(org: UUID, db: DB, identity: Principal) -> DraftView:
    return service.mine(db, org, identity[0])


@router.patch("/draft/{application_id}", response_model=DraftView)
def save(
    org: UUID,
    application_id: UUID,
    data: DraftSave,
    request: Request,
    db: DB,
    identity: Principal,
) -> DraftView:
    return service.save(db, org, application_id, identity[0], data, request.state.request_id)
