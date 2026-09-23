from uuid import UUID

from fastapi import APIRouter, Request

from app.modules.identity.routes import DB, Principal
from app.modules.programs import service
from app.modules.programs.schemas import (
    CatalogView,
    CenterCreate,
    CenterUpdate,
    CenterView,
    CohortCreate,
    CohortUpdate,
    CohortView,
    CycleCreate,
    CycleUpdate,
    CycleView,
    NamedCreate,
    NamedUpdate,
    ProgramView,
    StateCommand,
)

router = APIRouter(prefix="/api/v1/programs/organizations/{org}", tags=["programs"])


@router.get("/catalog", response_model=CatalogView)
def catalog(org: UUID, db: DB, identity: Principal) -> CatalogView:
    return service.catalog(db, org, identity[0])


@router.post("/programs", response_model=ProgramView, status_code=201)
def create_program(
    org: UUID, data: NamedCreate, request: Request, db: DB, identity: Principal
) -> ProgramView:
    return service.create_program(db, org, identity[0], data, request.state.request_id)


@router.patch("/programs/{item_id}", response_model=ProgramView)
def update_program(
    org: UUID, item_id: UUID, data: NamedUpdate, request: Request, db: DB, identity: Principal
) -> ProgramView:
    return service.update_program(db, org, item_id, identity[0], data, request.state.request_id)


@router.post("/programs/{item_id}/state", response_model=ProgramView)
def transition_program(
    org: UUID, item_id: UUID, data: StateCommand, request: Request, db: DB, identity: Principal
) -> ProgramView:
    return service.transition_program(db, org, item_id, identity[0], data, request.state.request_id)


@router.post("/centers", response_model=CenterView, status_code=201)
def create_center(
    org: UUID, data: CenterCreate, request: Request, db: DB, identity: Principal
) -> CenterView:
    return service.create_center(db, org, identity[0], data, request.state.request_id)


@router.patch("/centers/{item_id}", response_model=CenterView)
def update_center(
    org: UUID, item_id: UUID, data: CenterUpdate, request: Request, db: DB, identity: Principal
) -> CenterView:
    return service.update_center(db, org, item_id, identity[0], data, request.state.request_id)


@router.post("/centers/{item_id}/state", response_model=CenterView)
def transition_center(
    org: UUID, item_id: UUID, data: StateCommand, request: Request, db: DB, identity: Principal
) -> CenterView:
    return service.transition_center(db, org, item_id, identity[0], data, request.state.request_id)


@router.post("/cohorts", response_model=CohortView, status_code=201)
def create_cohort(
    org: UUID, data: CohortCreate, request: Request, db: DB, identity: Principal
) -> CohortView:
    return service.create_cohort(db, org, identity[0], data, request.state.request_id)


@router.patch("/cohorts/{item_id}", response_model=CohortView)
def update_cohort(
    org: UUID, item_id: UUID, data: CohortUpdate, request: Request, db: DB, identity: Principal
) -> CohortView:
    return service.update_cohort(db, org, item_id, identity[0], data, request.state.request_id)


@router.post("/cohorts/{item_id}/state", response_model=CohortView)
def transition_cohort(
    org: UUID, item_id: UUID, data: StateCommand, request: Request, db: DB, identity: Principal
) -> CohortView:
    return service.transition_cohort(db, org, item_id, identity[0], data, request.state.request_id)


@router.post("/cycles", response_model=CycleView, status_code=201)
def create_cycle(
    org: UUID, data: CycleCreate, request: Request, db: DB, identity: Principal
) -> CycleView:
    return service.create_cycle(db, org, identity[0], data, request.state.request_id)


@router.patch("/cycles/{item_id}", response_model=CycleView)
def update_cycle(
    org: UUID, item_id: UUID, data: CycleUpdate, request: Request, db: DB, identity: Principal
) -> CycleView:
    return service.update_cycle(db, org, item_id, identity[0], data, request.state.request_id)


@router.post("/cycles/{item_id}/state", response_model=CycleView)
def transition_cycle(
    org: UUID, item_id: UUID, data: StateCommand, request: Request, db: DB, identity: Principal
) -> CycleView:
    return service.transition_cycle(db, org, item_id, identity[0], data, request.state.request_id)
