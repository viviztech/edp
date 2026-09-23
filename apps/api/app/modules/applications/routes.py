from uuid import UUID

from fastapi import APIRouter, Request

from app.modules.applications import service
from app.modules.applications.schemas import (
    CycleOpportunityList,
    DefinitionCommand,
    DefinitionCreate,
    DefinitionList,
    DefinitionUpdate,
    DefinitionView,
    DraftSave,
    DraftView,
    FormView,
    SubmitCommand,
    SubmittedView,
)
from app.modules.identity.routes import DB, Principal

router = APIRouter(prefix="/api/v1/applications/organizations/{org}", tags=["applications"])


@router.get("/form", response_model=FormView)
def form(org: UUID, db: DB, identity: Principal) -> FormView:
    return service.get_form(db, org)


@router.get("/definitions", response_model=DefinitionList)
def definitions(org: UUID, db: DB, identity: Principal) -> DefinitionList:
    return service.list_definitions(db, org, identity[0])


@router.post("/definitions", response_model=DefinitionView, status_code=201)
def create_definition(
    org: UUID,
    data: DefinitionCreate,
    request: Request,
    db: DB,
    identity: Principal,
) -> DefinitionView:
    return service.create_definition(db, org, identity[0], data, request.state.request_id)


@router.get("/definitions/{definition_id}", response_model=DefinitionView)
def definition(
    org: UUID,
    definition_id: UUID,
    db: DB,
    identity: Principal,
) -> DefinitionView:
    return service.get_definition(db, org, definition_id, identity[0])


@router.patch("/definitions/{definition_id}", response_model=DefinitionView)
def update_definition(
    org: UUID,
    definition_id: UUID,
    data: DefinitionUpdate,
    request: Request,
    db: DB,
    identity: Principal,
) -> DefinitionView:
    return service.update_definition(
        db, org, definition_id, identity[0], data, request.state.request_id
    )


@router.post("/definitions/{definition_id}/copy", response_model=DefinitionView, status_code=201)
def copy_definition(
    org: UUID,
    definition_id: UUID,
    data: DefinitionCommand,
    request: Request,
    db: DB,
    identity: Principal,
) -> DefinitionView:
    return service.copy_definition(
        db, org, definition_id, identity[0], data, request.state.request_id
    )


@router.post("/definitions/{definition_id}/publish", response_model=DefinitionView)
def publish_definition(
    org: UUID,
    definition_id: UUID,
    data: DefinitionCommand,
    request: Request,
    db: DB,
    identity: Principal,
) -> DefinitionView:
    return service.publish_definition(
        db, org, definition_id, identity[0], data, request.state.request_id
    )


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


@router.get("/cycles", response_model=CycleOpportunityList)
def cycles(org: UUID, db: DB, identity: Principal) -> CycleOpportunityList:
    return service.available_cycles(db, org)


@router.post("/cycles/{cycle_id}/draft", response_model=DraftView, status_code=201)
def create_cycle_draft(
    org: UUID,
    cycle_id: UUID,
    request: Request,
    db: DB,
    identity: Principal,
) -> DraftView:
    return service.create_cycle_draft(db, org, cycle_id, identity[0], request.state.request_id)


@router.get(
    "/cycles/{cycle_id}/application",
    response_model=DraftView | SubmittedView,
)
def cycle_application(
    org: UUID,
    cycle_id: UUID,
    db: DB,
    identity: Principal,
) -> DraftView | SubmittedView:
    return service.cycle_application(db, org, cycle_id, identity[0])


@router.post("/draft/{application_id}/submit", response_model=SubmittedView)
def submit(
    org: UUID,
    application_id: UUID,
    data: SubmitCommand,
    request: Request,
    db: DB,
    identity: Principal,
) -> SubmittedView:
    return service.submit(
        db,
        org,
        application_id,
        identity[0],
        data,
        request.state.request_id,
    )
