from uuid import UUID

from fastapi import APIRouter, Request

from app.modules.identity.routes import DB, Principal
from app.modules.mentoring import service
from app.modules.mentoring.schemas import (
    ActionCreate,
    ActionView,
    AssignmentCreate,
    AssignmentEnd,
    AvailabilityCreate,
    AvailabilityView,
    ExpertiseCreate,
    ExpertiseView,
    FeedbackCreate,
    FeedbackView,
    FollowUpCreate,
    FollowUpView,
    GoalCreate,
    GoalUpdate,
    GoalView,
    MentorAssignmentView,
    MyMentoring,
    NoteCreate,
    NoteView,
    ProfileCreate,
    ProfileView,
    SessionCreate,
    SessionView,
    StateCommand,
    Workspace,
)

router = APIRouter(prefix="/api/v1/mentoring/organizations/{org}", tags=["mentoring"])


@router.get("/workspace", response_model=Workspace)
def workspace(org: UUID, db: DB, identity: Principal) -> Workspace:
    return service.workspace(db, org, identity[0])


@router.get("/my-mentoring", response_model=MyMentoring)
def my_mentoring(org: UUID, db: DB, identity: Principal) -> MyMentoring:
    return service.my_mentoring(db, org, identity[0])


@router.post("/profiles", response_model=ProfileView, status_code=201)
def create_profile(
    org: UUID, data: ProfileCreate, request: Request, db: DB, identity: Principal
) -> ProfileView:
    return service.create_profile(db, org, identity[0], data, request.state.request_id)


@router.post("/expertise", response_model=ExpertiseView, status_code=201)
def add_expertise(
    org: UUID, data: ExpertiseCreate, request: Request, db: DB, identity: Principal
) -> ExpertiseView:
    return service.add_expertise(db, org, identity[0], data, request.state.request_id)


@router.post("/availability", response_model=AvailabilityView, status_code=201)
def add_availability(
    org: UUID, data: AvailabilityCreate, request: Request, db: DB, identity: Principal
) -> AvailabilityView:
    return service.add_availability(db, org, identity[0], data, request.state.request_id)


@router.post("/assignments", response_model=MentorAssignmentView, status_code=201)
def create_assignment(
    org: UUID, data: AssignmentCreate, request: Request, db: DB, identity: Principal
) -> MentorAssignmentView:
    return service.create_assignment(db, org, identity[0], data, request.state.request_id)


@router.post("/assignments/{assignment_id}/end", response_model=MentorAssignmentView)
def end_assignment(
    org: UUID,
    assignment_id: UUID,
    data: AssignmentEnd,
    request: Request,
    db: DB,
    identity: Principal,
) -> MentorAssignmentView:
    return service.end_assignment(
        db, org, assignment_id, identity[0], data, request.state.request_id
    )


@router.post("/sessions", response_model=SessionView, status_code=201)
def create_session(
    org: UUID, data: SessionCreate, request: Request, db: DB, identity: Principal
) -> SessionView:
    return service.create_session(db, org, identity[0], data, request.state.request_id)


@router.post("/sessions/{session_id}/state", response_model=SessionView)
def transition_session(
    org: UUID, session_id: UUID, data: StateCommand, request: Request, db: DB, identity: Principal
) -> SessionView:
    return service.transition_session(
        db, org, session_id, identity[0], data, request.state.request_id
    )


@router.post("/notes", response_model=NoteView, status_code=201)
def create_note(
    org: UUID, data: NoteCreate, request: Request, db: DB, identity: Principal
) -> NoteView:
    return service.create_note(db, org, identity[0], data, request.state.request_id)


@router.post("/goals", response_model=GoalView, status_code=201)
def create_goal(
    org: UUID, data: GoalCreate, request: Request, db: DB, identity: Principal
) -> GoalView:
    return service.create_goal(db, org, identity[0], data, request.state.request_id)


@router.post("/goals/{goal_id}/state", response_model=GoalView)
def update_goal(
    org: UUID, goal_id: UUID, data: GoalUpdate, request: Request, db: DB, identity: Principal
) -> GoalView:
    return service.update_goal(db, org, goal_id, identity[0], data, request.state.request_id)


@router.post("/action-items", response_model=ActionView, status_code=201)
def create_action(
    org: UUID, data: ActionCreate, request: Request, db: DB, identity: Principal
) -> ActionView:
    return service.create_action(db, org, identity[0], data, request.state.request_id)


@router.post("/action-items/{action_id}/state", response_model=ActionView)
def transition_action(
    org: UUID, action_id: UUID, data: StateCommand, request: Request, db: DB, identity: Principal
) -> ActionView:
    return service.transition_action(
        db, org, action_id, identity[0], data, request.state.request_id
    )


@router.post("/follow-ups", response_model=FollowUpView, status_code=201)
def create_follow_up(
    org: UUID, data: FollowUpCreate, request: Request, db: DB, identity: Principal
) -> FollowUpView:
    return service.create_follow_up(db, org, identity[0], data, request.state.request_id)


@router.post("/follow-ups/{follow_id}/state", response_model=FollowUpView)
def transition_follow_up(
    org: UUID, follow_id: UUID, data: StateCommand, request: Request, db: DB, identity: Principal
) -> FollowUpView:
    return service.transition_follow_up(
        db, org, follow_id, identity[0], data, request.state.request_id
    )


@router.post("/feedback", response_model=FeedbackView, status_code=201)
def create_feedback(
    org: UUID, data: FeedbackCreate, request: Request, db: DB, identity: Principal
) -> FeedbackView:
    return service.create_feedback(db, org, identity[0], data, request.state.request_id)
