from uuid import UUID

from fastapi import APIRouter, Request

from app.modules.identity.routes import DB, Principal
from app.modules.selection import service
from app.modules.selection.schemas import (
    AssignmentCreate,
    AssignmentView,
    ConflictCommand,
    CycleCommand,
    DecisionCommand,
    DecisionView,
    InterviewComplete,
    InterviewCreate,
    InterviewView,
    ModerationCommand,
    PanelScoreSubmit,
    ReviewSave,
    ReviewSubmit,
    RubricCommand,
    RubricUpdate,
    RubricView,
    SelectionCycleCreate,
    SelectionCycleUpdate,
    SelectionCycleView,
    SelectionWorkspace,
)

router = APIRouter(prefix="/api/v1/selection/organizations/{org}", tags=["selection"])


@router.get("/workspace", response_model=SelectionWorkspace)
def get_workspace(org: UUID, db: DB, identity: Principal) -> SelectionWorkspace:
    return service.workspace(db, org, identity[0])


@router.post("/cycles", response_model=SelectionCycleView, status_code=201)
def create_cycle(
    org: UUID, data: SelectionCycleCreate, request: Request, db: DB, identity: Principal
) -> SelectionCycleView:
    return service.create_cycle(db, org, identity[0], data, request.state.request_id)


@router.patch("/cycles/{cycle_id}", response_model=SelectionCycleView)
def update_cycle(
    org: UUID,
    cycle_id: UUID,
    data: SelectionCycleUpdate,
    request: Request,
    db: DB,
    identity: Principal,
) -> SelectionCycleView:
    return service.update_cycle(db, org, cycle_id, identity[0], data, request.state.request_id)


@router.post("/cycles/{cycle_id}/state", response_model=SelectionCycleView)
def transition_cycle(
    org: UUID,
    cycle_id: UUID,
    data: CycleCommand,
    request: Request,
    db: DB,
    identity: Principal,
) -> SelectionCycleView:
    return service.transition_cycle(db, org, cycle_id, identity[0], data, request.state.request_id)


@router.put("/rubrics/{rubric_id}", response_model=RubricView)
def update_rubric(
    org: UUID,
    rubric_id: UUID,
    data: RubricUpdate,
    request: Request,
    db: DB,
    identity: Principal,
) -> RubricView:
    return service.update_rubric(db, org, rubric_id, identity[0], data, request.state.request_id)


@router.post("/rubrics/{rubric_id}/publish", response_model=RubricView)
def publish_rubric(
    org: UUID,
    rubric_id: UUID,
    data: RubricCommand,
    request: Request,
    db: DB,
    identity: Principal,
) -> RubricView:
    return service.publish_rubric(db, org, rubric_id, identity[0], data, request.state.request_id)


@router.post("/rubrics/{rubric_id}/copy", response_model=RubricView, status_code=201)
def copy_rubric(
    org: UUID, rubric_id: UUID, request: Request, db: DB, identity: Principal
) -> RubricView:
    return service.copy_rubric(db, org, rubric_id, identity[0], request.state.request_id)


@router.post("/assignments", response_model=AssignmentView, status_code=201)
def create_assignment(
    org: UUID, data: AssignmentCreate, request: Request, db: DB, identity: Principal
) -> AssignmentView:
    return service.create_assignment(db, org, identity[0], data, request.state.request_id)


@router.post("/assignments/{assignment_id}/conflict", response_model=AssignmentView)
def declare_conflict(
    org: UUID,
    assignment_id: UUID,
    data: ConflictCommand,
    request: Request,
    db: DB,
    identity: Principal,
) -> AssignmentView:
    return service.declare_conflict(
        db, org, assignment_id, identity[0], data, request.state.request_id
    )


@router.put("/assignments/{assignment_id}/review", response_model=AssignmentView)
def save_review(
    org: UUID,
    assignment_id: UUID,
    data: ReviewSave,
    request: Request,
    db: DB,
    identity: Principal,
) -> AssignmentView:
    return service.save_review(db, org, assignment_id, identity[0], data, request.state.request_id)


@router.post("/assignments/{assignment_id}/submit", response_model=AssignmentView)
def submit_review(
    org: UUID,
    assignment_id: UUID,
    data: ReviewSubmit,
    request: Request,
    db: DB,
    identity: Principal,
) -> AssignmentView:
    return service.submit_review(
        db, org, assignment_id, identity[0], data, request.state.request_id
    )


@router.post("/assignments/{assignment_id}/moderation", response_model=AssignmentView)
def moderate_review(
    org: UUID,
    assignment_id: UUID,
    data: ModerationCommand,
    request: Request,
    db: DB,
    identity: Principal,
) -> AssignmentView:
    return service.moderate_review(
        db, org, assignment_id, identity[0], data, request.state.request_id
    )


@router.post("/interviews", response_model=InterviewView, status_code=201)
def create_interview(
    org: UUID, data: InterviewCreate, request: Request, db: DB, identity: Principal
) -> InterviewView:
    return service.create_interview(db, org, identity[0], data, request.state.request_id)


@router.post("/interviews/{interview_id}/score", response_model=InterviewView)
def submit_interview_score(
    org: UUID,
    interview_id: UUID,
    data: PanelScoreSubmit,
    request: Request,
    db: DB,
    identity: Principal,
) -> InterviewView:
    return service.submit_interview_score(
        db, org, interview_id, identity[0], data, request.state.request_id
    )


@router.post("/interviews/{interview_id}/complete", response_model=InterviewView)
def complete_interview(
    org: UUID,
    interview_id: UUID,
    data: InterviewComplete,
    request: Request,
    db: DB,
    identity: Principal,
) -> InterviewView:
    return service.complete_interview(
        db, org, interview_id, identity[0], data, request.state.request_id
    )


@router.post(
    "/cycles/{cycle_id}/applications/{application_id}/decision",
    response_model=DecisionView,
)
def record_decision(
    org: UUID,
    cycle_id: UUID,
    application_id: UUID,
    data: DecisionCommand,
    request: Request,
    db: DB,
    identity: Principal,
) -> DecisionView:
    return service.record_decision(
        db, org, cycle_id, application_id, identity[0], data, request.state.request_id
    )
