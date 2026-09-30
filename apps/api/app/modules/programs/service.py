import json
from typing import cast
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.applications.models import Application, ApplicationForm, ApplicationStatusHistory
from app.modules.identity.models import (
    AuditLog,
    Person,
    Role,
    RolePermission,
    User,
    UserRole,
    now,
)
from app.modules.identity.security import AuthError
from app.modules.identity.service import require_permission
from app.modules.programs.models import (
    ApplicationCycle,
    Cohort,
    DomainOutbox,
    Enrollment,
    Participant,
    ParticipantStatusHistory,
    Program,
    ProgramSession,
    ProgramStaffAssignment,
    TrainingCenter,
)
from app.modules.programs.schemas import (
    CatalogView,
    CenterCreate,
    CenterState,
    CenterUpdate,
    CenterView,
    CohortCreate,
    CohortState,
    CohortUpdate,
    CohortView,
    CycleCreate,
    CycleState,
    CycleUpdate,
    CycleView,
    EnrollmentCandidateView,
    EnrollmentConversionView,
    EnrollmentConvert,
    EnrollmentState,
    EnrollmentView,
    NamedCreate,
    NamedUpdate,
    ParticipantState,
    ParticipantStateCommand,
    ParticipantTimeline,
    ParticipantView,
    ProgramState,
    ProgramView,
    SessionCreate,
    SessionMode,
    SessionState,
    SessionStateCommand,
    SessionView,
    StaffAssignmentCreate,
    StaffAssignmentRevoke,
    StaffAssignmentState,
    StaffAssignmentView,
    StateCommand,
    TimelineEvent,
)
from app.modules.selection.models import SelectionCycle, SelectionDecision


def program_view(item: Program) -> ProgramView:
    return ProgramView(
        id=item.id,
        organization_id=item.organization_id,
        code=item.code,
        name_en=item.name_en,
        name_ta=item.name_ta,
        state=cast(ProgramState, item.state),
        version=item.version,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def center_view(item: TrainingCenter) -> CenterView:
    return CenterView(
        id=item.id,
        organization_id=item.organization_id,
        code=item.code,
        name_en=item.name_en,
        name_ta=item.name_ta,
        locality=item.locality,
        state=cast(CenterState, item.state),
        version=item.version,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def cohort_view(item: Cohort) -> CohortView:
    return CohortView(
        id=item.id,
        organization_id=item.organization_id,
        program_id=item.program_id,
        center_id=item.center_id,
        code=item.code,
        name_en=item.name_en,
        name_ta=item.name_ta,
        starts_on=item.starts_on,
        ends_on=item.ends_on,
        capacity=item.capacity,
        state=cast(CohortState, item.state),
        version=item.version,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def cycle_view(item: ApplicationCycle) -> CycleView:
    return CycleView(
        id=item.id,
        organization_id=item.organization_id,
        program_id=item.program_id,
        cohort_id=item.cohort_id,
        form_id=item.form_id,
        code=item.code,
        name_en=item.name_en,
        name_ta=item.name_ta,
        opens_at=item.opens_at,
        closes_at=item.closes_at,
        state=cast(CycleState, item.state),
        version=item.version,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _audit(
    db: Session,
    actor: User,
    org: UUID,
    resource: UUID,
    action: str,
    request_id: str,
    version: int,
    changed: str,
    reason: str | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=resource,
            action=action,
            request_id=request_id,
            resource_version=version,
            changed_fields=changed,
            reason=reason,
        )
    )


def _flush(db: Session) -> None:
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("version_conflict", 409) from exc


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("version_conflict", 409) from exc


def staff_assignment_view(db: Session, item: ProgramStaffAssignment) -> StaffAssignmentView:
    user = db.get(User, item.user_id)
    person = db.get(Person, user.person_id) if user else None
    if not user or not person:
        raise AuthError("assignment_identity_unavailable", 409)
    return StaffAssignmentView(
        id=item.id,
        organization_id=item.organization_id,
        user_id=item.user_id,
        email=user.email,
        display_name=person.display_name,
        center_id=item.center_id,
        cohort_id=item.cohort_id,
        state=cast(StaffAssignmentState, item.state),
        version=item.version,
        created_at=item.created_at,
        updated_at=item.updated_at,
        revoked_at=item.revoked_at,
    )


StaffScope = tuple[set[UUID], set[UUID]]


def _staff_scope(db: Session, org: UUID, actor: User, permission: str) -> StaffScope | None:
    require_permission(db, actor, org, permission)
    unrestricted = db.scalar(
        select(UserRole.id)
        .join(Role, Role.id == UserRole.role_id)
        .join(RolePermission, RolePermission.role_id == Role.id)
        .where(
            UserRole.user_id == actor.id,
            UserRole.organization_id == org,
            RolePermission.permission_code == permission,
            Role.name != "Training Center Coordinator",
        )
        .limit(1)
    )
    if unrestricted:
        return None
    assignments = list(
        db.scalars(
            select(ProgramStaffAssignment).where(
                ProgramStaffAssignment.organization_id == org,
                ProgramStaffAssignment.user_id == actor.id,
                ProgramStaffAssignment.state == "active",
            )
        )
    )
    if not assignments:
        raise AuthError("staff_scope_required", 403)
    center_ids = {item.center_id for item in assignments if item.cohort_id is None}
    cohort_ids = {item.cohort_id for item in assignments if item.cohort_id is not None}
    return center_ids, cohort_ids


def _cohort_in_scope(cohort: Cohort, scope: StaffScope | None) -> bool:
    return scope is None or cohort.center_id in scope[0] or cohort.id in scope[1]


def _require_cohort_scope(cohort: Cohort, scope: StaffScope | None) -> None:
    if not _cohort_in_scope(cohort, scope):
        raise AuthError("staff_scope_denied", 403)


def _require_participant_scope(
    db: Session, org: UUID, participant_id: UUID, scope: StaffScope | None
) -> None:
    if scope is None:
        return
    predicates = []
    if scope[0]:
        predicates.append(Cohort.center_id.in_(scope[0]))
    if scope[1]:
        predicates.append(Cohort.id.in_(scope[1]))
    allowed = db.scalar(
        select(Enrollment.id)
        .join(Cohort, Cohort.id == Enrollment.cohort_id)
        .where(
            Enrollment.organization_id == org,
            Enrollment.participant_id == participant_id,
            or_(*predicates),
        )
        .limit(1)
    )
    if not allowed:
        raise AuthError("staff_scope_denied", 403)


def catalog(db: Session, org: UUID, actor: User) -> CatalogView:
    scope = _staff_scope(db, org, actor, "program.view")
    programs = list(
        db.scalars(
            select(Program)
            .where(Program.organization_id == org)
            .order_by(Program.created_at, Program.id)
            .limit(100)
        )
    )
    centers = list(
        db.scalars(
            select(TrainingCenter)
            .where(TrainingCenter.organization_id == org)
            .order_by(TrainingCenter.created_at, TrainingCenter.id)
            .limit(100)
        )
    )
    cohorts = list(
        db.scalars(
            select(Cohort)
            .where(Cohort.organization_id == org)
            .order_by(Cohort.starts_on, Cohort.id)
            .limit(100)
        )
    )
    if scope is not None:
        centers = [
            item
            for item in centers
            if item.id in scope[0]
            or any(cohort.id in scope[1] and cohort.center_id == item.id for cohort in cohorts)
        ]
        cohorts = [item for item in cohorts if _cohort_in_scope(item, scope)]
    cohort_ids = {item.id for item in cohorts}
    cycles = list(
        db.scalars(
            select(ApplicationCycle)
            .where(ApplicationCycle.organization_id == org)
            .order_by(ApplicationCycle.opens_at, ApplicationCycle.id)
            .limit(100)
        )
    )
    enrollments = list(
        db.scalars(
            select(Enrollment)
            .where(Enrollment.organization_id == org)
            .order_by(Enrollment.enrolled_at, Enrollment.id)
            .limit(100)
        )
    )
    sessions = list(
        db.scalars(
            select(ProgramSession)
            .where(ProgramSession.organization_id == org)
            .order_by(ProgramSession.starts_at, ProgramSession.id)
            .limit(200)
        )
    )
    assignments = list(
        db.scalars(
            select(ProgramStaffAssignment)
            .where(ProgramStaffAssignment.organization_id == org)
            .order_by(ProgramStaffAssignment.created_at, ProgramStaffAssignment.id)
            .limit(200)
        )
    )
    candidates = _enrollment_candidates(db, org)
    participants = list(
        db.scalars(
            select(Participant)
            .where(Participant.organization_id == org)
            .order_by(Participant.created_at, Participant.id)
            .limit(100)
        )
    )
    if scope is not None:
        cycles = [item for item in cycles if item.cohort_id in cohort_ids]
        enrollments = [item for item in enrollments if item.cohort_id in cohort_ids]
        sessions = [item for item in sessions if item.cohort_id in cohort_ids]
        candidates = []
        participant_ids = {item.participant_id for item in enrollments}
        participants = [item for item in participants if item.id in participant_ids]
        assignments = [item for item in assignments if item.user_id == actor.id]
    return CatalogView(
        programs=[program_view(item) for item in programs],
        centers=[center_view(item) for item in centers],
        cohorts=[cohort_view(item) for item in cohorts],
        cycles=[cycle_view(item) for item in cycles],
        enrollment_candidates=candidates,
        participants=[participant_view(db, item) for item in participants],
        enrollments=[enrollment_view(item) for item in enrollments],
        sessions=[session_view(item) for item in sessions],
        staff_assignments=[staff_assignment_view(db, item) for item in assignments],
    )


def _program(db: Session, org: UUID, item_id: UUID, lock: bool = False) -> Program:
    query = select(Program).where(Program.id == item_id, Program.organization_id == org)
    item = db.scalar(query.with_for_update() if lock else query)
    if not item:
        raise AuthError("not_found", 404)
    return item


def _center(db: Session, org: UUID, item_id: UUID, lock: bool = False) -> TrainingCenter:
    query = select(TrainingCenter).where(
        TrainingCenter.id == item_id, TrainingCenter.organization_id == org
    )
    item = db.scalar(query.with_for_update() if lock else query)
    if not item:
        raise AuthError("not_found", 404)
    return item


def _cohort(db: Session, org: UUID, item_id: UUID, lock: bool = False) -> Cohort:
    query = select(Cohort).where(Cohort.id == item_id, Cohort.organization_id == org)
    item = db.scalar(query.with_for_update() if lock else query)
    if not item:
        raise AuthError("not_found", 404)
    return item


def _cycle(db: Session, org: UUID, item_id: UUID, lock: bool = False) -> ApplicationCycle:
    query = select(ApplicationCycle).where(
        ApplicationCycle.id == item_id, ApplicationCycle.organization_id == org
    )
    item = db.scalar(query.with_for_update() if lock else query)
    if not item:
        raise AuthError("not_found", 404)
    return item


def create_staff_assignment(
    db: Session,
    org: UUID,
    actor: User,
    data: StaffAssignmentCreate,
    request_id: str,
) -> StaffAssignmentView:
    require_permission(db, actor, org, "staff.assignment.manage")
    center = _center(db, org, data.center_id)
    if center.state != "active":
        raise AuthError("inactive_dependency", 409)
    if data.cohort_id:
        cohort = _cohort(db, org, data.cohort_id)
        if cohort.center_id != center.id or cohort.state in {"completed", "cancelled"}:
            raise AuthError("invalid_assignment_scope", 422)
    user = db.scalar(select(User).where(func.lower(User.email) == data.email.lower()))
    if not user or user.status != "active":
        raise AuthError("coordinator_not_found", 404)
    coordinator_role = db.scalar(
        select(UserRole.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(
            UserRole.user_id == user.id,
            UserRole.organization_id == org,
            Role.name.in_(["Training Center Coordinator", "Trainer"]),
        )
        .limit(1)
    )
    if not coordinator_role:
        raise AuthError("delivery_role_required", 422)
    duplicate = db.scalar(
        select(ProgramStaffAssignment.id).where(
            ProgramStaffAssignment.organization_id == org,
            ProgramStaffAssignment.user_id == user.id,
            ProgramStaffAssignment.center_id == center.id,
            ProgramStaffAssignment.cohort_id.is_(None)
            if data.cohort_id is None
            else ProgramStaffAssignment.cohort_id == data.cohort_id,
            ProgramStaffAssignment.state == "active",
        )
    )
    if duplicate:
        raise AuthError("assignment_exists", 409)
    item = ProgramStaffAssignment(
        organization_id=org,
        user_id=user.id,
        center_id=center.id,
        cohort_id=data.cohort_id,
    )
    db.add(item)
    _flush(db)
    _audit(
        db,
        actor,
        org,
        item.id,
        "program_staff_assignment.created",
        request_id,
        1,
        "user_id,center_id,cohort_id,state",
        data.reason,
    )
    _commit(db)
    return staff_assignment_view(db, item)


def revoke_staff_assignment(
    db: Session,
    org: UUID,
    assignment_id: UUID,
    actor: User,
    data: StaffAssignmentRevoke,
    request_id: str,
) -> StaffAssignmentView:
    require_permission(db, actor, org, "staff.assignment.manage")
    item = db.scalar(
        select(ProgramStaffAssignment)
        .where(
            ProgramStaffAssignment.id == assignment_id,
            ProgramStaffAssignment.organization_id == org,
        )
        .with_for_update()
    )
    if not item:
        raise AuthError("not_found", 404)
    if item.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    if item.state != "active":
        raise AuthError("invalid_transition", 409)
    item.state = "revoked"
    item.version += 1
    item.revoked_at = now()
    item.updated_at = item.revoked_at
    _audit(
        db,
        actor,
        org,
        item.id,
        "program_staff_assignment.revoked",
        request_id,
        item.version,
        "state,revoked_at",
        data.reason,
    )
    _commit(db)
    return staff_assignment_view(db, item)


def create_program(
    db: Session, org: UUID, actor: User, data: NamedCreate, request_id: str
) -> ProgramView:
    require_permission(db, actor, org, "program.manage")
    item = Program(
        organization_id=org,
        code=data.code,
        name_en=data.name_en,
        name_ta=data.name_ta,
    )
    db.add(item)
    _flush(db)
    _audit(db, actor, org, item.id, "program.created", request_id, 1, "code,name_en,name_ta")
    _commit(db)
    return program_view(item)


def update_program(
    db: Session,
    org: UUID,
    item_id: UUID,
    actor: User,
    data: NamedUpdate,
    request_id: str,
) -> ProgramView:
    require_permission(db, actor, org, "program.manage")
    item = _program(db, org, item_id, True)
    if item.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    if item.state == "archived":
        raise AuthError("invalid_transition", 409)
    item.name_en, item.name_ta = data.name_en, data.name_ta
    item.version += 1
    item.updated_at = now()
    _audit(db, actor, org, item.id, "program.updated", request_id, item.version, "name_en,name_ta")
    _commit(db)
    return program_view(item)


def transition_program(
    db: Session,
    org: UUID,
    item_id: UUID,
    actor: User,
    data: StateCommand,
    request_id: str,
) -> ProgramView:
    require_permission(db, actor, org, "program.manage")
    item = _program(db, org, item_id, True)
    allowed = {"draft": {"active"}, "active": {"archived"}, "archived": set()}
    if item.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    if data.target not in allowed[item.state]:
        raise AuthError("invalid_transition", 409)
    item.state = data.target
    item.version += 1
    item.updated_at = now()
    _audit(
        db,
        actor,
        org,
        item.id,
        "program.state_changed",
        request_id,
        item.version,
        "state",
        data.reason,
    )
    _commit(db)
    return program_view(item)


def create_center(
    db: Session, org: UUID, actor: User, data: CenterCreate, request_id: str
) -> CenterView:
    require_permission(db, actor, org, "program.manage")
    item = TrainingCenter(organization_id=org, **data.model_dump())
    db.add(item)
    _flush(db)
    _audit(
        db,
        actor,
        org,
        item.id,
        "training_center.created",
        request_id,
        1,
        "code,name_en,name_ta,locality",
    )
    _commit(db)
    return center_view(item)


def update_center(
    db: Session,
    org: UUID,
    item_id: UUID,
    actor: User,
    data: CenterUpdate,
    request_id: str,
) -> CenterView:
    require_permission(db, actor, org, "program.manage")
    item = _center(db, org, item_id, True)
    if item.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    item.name_en, item.name_ta, item.locality = data.name_en, data.name_ta, data.locality
    item.version += 1
    item.updated_at = now()
    _audit(
        db,
        actor,
        org,
        item.id,
        "training_center.updated",
        request_id,
        item.version,
        "name_en,name_ta,locality",
    )
    _commit(db)
    return center_view(item)


def transition_center(
    db: Session,
    org: UUID,
    item_id: UUID,
    actor: User,
    data: StateCommand,
    request_id: str,
) -> CenterView:
    require_permission(db, actor, org, "program.manage")
    item = _center(db, org, item_id, True)
    allowed = {"active": {"inactive"}, "inactive": {"active"}}
    if item.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    if data.target not in allowed[item.state]:
        raise AuthError("invalid_transition", 409)
    item.state = data.target
    item.version += 1
    item.updated_at = now()
    _audit(
        db,
        actor,
        org,
        item.id,
        "training_center.state_changed",
        request_id,
        item.version,
        "state",
        data.reason,
    )
    _commit(db)
    return center_view(item)


def _validate_cohort_scope(
    db: Session, org: UUID, program_id: UUID, center_id: UUID
) -> tuple[Program, TrainingCenter]:
    program, center = _program(db, org, program_id), _center(db, org, center_id)
    if program.state != "active" or center.state != "active":
        raise AuthError("inactive_dependency", 409)
    return program, center


def create_cohort(
    db: Session, org: UUID, actor: User, data: CohortCreate, request_id: str
) -> CohortView:
    scope = _staff_scope(db, org, actor, "cohort.manage")
    if scope is not None and data.center_id not in scope[0]:
        raise AuthError("staff_scope_denied", 403)
    _validate_cohort_scope(db, org, data.program_id, data.center_id)
    item = Cohort(organization_id=org, **data.model_dump())
    db.add(item)
    _flush(db)
    _audit(
        db,
        actor,
        org,
        item.id,
        "cohort.created",
        request_id,
        1,
        "code,name_en,name_ta,program_id,center_id,dates,capacity",
    )
    _commit(db)
    return cohort_view(item)


def update_cohort(
    db: Session,
    org: UUID,
    item_id: UUID,
    actor: User,
    data: CohortUpdate,
    request_id: str,
) -> CohortView:
    scope = _staff_scope(db, org, actor, "cohort.manage")
    item = _cohort(db, org, item_id, True)
    _require_cohort_scope(item, scope)
    if scope is not None and data.center_id not in scope[0] and item.id not in scope[1]:
        raise AuthError("staff_scope_denied", 403)
    if item.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    if item.state != "planned":
        raise AuthError("invalid_transition", 409)
    _validate_cohort_scope(db, org, data.program_id, data.center_id)
    item.program_id, item.center_id = data.program_id, data.center_id
    item.name_en, item.name_ta = data.name_en, data.name_ta
    item.starts_on, item.ends_on, item.capacity = data.starts_on, data.ends_on, data.capacity
    item.version += 1
    item.updated_at = now()
    _audit(
        db,
        actor,
        org,
        item.id,
        "cohort.updated",
        request_id,
        item.version,
        "name_en,name_ta,program_id,center_id,dates,capacity",
    )
    _commit(db)
    return cohort_view(item)


def transition_cohort(
    db: Session,
    org: UUID,
    item_id: UUID,
    actor: User,
    data: StateCommand,
    request_id: str,
) -> CohortView:
    scope = _staff_scope(db, org, actor, "cohort.manage")
    item = _cohort(db, org, item_id, True)
    _require_cohort_scope(item, scope)
    allowed = {
        "planned": {"active", "cancelled"},
        "active": {"completed", "cancelled"},
        "completed": set(),
        "cancelled": set(),
    }
    if item.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    if data.target not in allowed[item.state]:
        raise AuthError("invalid_transition", 409)
    if data.target == "active":
        _validate_cohort_scope(db, org, item.program_id, item.center_id)
    item.state = data.target
    item.version += 1
    item.updated_at = now()
    _audit(
        db,
        actor,
        org,
        item.id,
        "cohort.state_changed",
        request_id,
        item.version,
        "state",
        data.reason,
    )
    _commit(db)
    return cohort_view(item)


def _validate_cycle_scope(
    db: Session,
    org: UUID,
    program_id: UUID,
    cohort_id: UUID | None,
    form_id: UUID,
) -> None:
    program = _program(db, org, program_id)
    if program.state != "active":
        raise AuthError("inactive_dependency", 409)
    if cohort_id:
        cohort = _cohort(db, org, cohort_id)
        if cohort.program_id != program_id or cohort.state in {"completed", "cancelled"}:
            raise AuthError("invalid_scope", 422)
    form = db.scalar(
        select(ApplicationForm).where(
            ApplicationForm.id == form_id,
            ApplicationForm.organization_id == org,
        )
    )
    if not form:
        raise AuthError("not_found", 404)
    if form.state != "published":
        raise AuthError("inactive_dependency", 409)


def create_cycle(
    db: Session, org: UUID, actor: User, data: CycleCreate, request_id: str
) -> CycleView:
    require_permission(db, actor, org, "application.cycle.manage")
    _validate_cycle_scope(db, org, data.program_id, data.cohort_id, data.form_id)
    item = ApplicationCycle(organization_id=org, **data.model_dump())
    db.add(item)
    _flush(db)
    _audit(
        db,
        actor,
        org,
        item.id,
        "application_cycle.created",
        request_id,
        1,
        "code,name_en,name_ta,program_id,cohort_id,form_id,window",
    )
    _commit(db)
    return cycle_view(item)


def update_cycle(
    db: Session,
    org: UUID,
    item_id: UUID,
    actor: User,
    data: CycleUpdate,
    request_id: str,
) -> CycleView:
    require_permission(db, actor, org, "application.cycle.manage")
    item = _cycle(db, org, item_id, True)
    if item.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    if item.state != "draft":
        raise AuthError("invalid_transition", 409)
    _validate_cycle_scope(db, org, data.program_id, data.cohort_id, data.form_id)
    item.program_id, item.cohort_id, item.form_id = data.program_id, data.cohort_id, data.form_id
    item.name_en, item.name_ta = data.name_en, data.name_ta
    item.opens_at, item.closes_at = data.opens_at, data.closes_at
    item.version += 1
    item.updated_at = now()
    _audit(
        db,
        actor,
        org,
        item.id,
        "application_cycle.updated",
        request_id,
        item.version,
        "name_en,name_ta,program_id,cohort_id,form_id,window",
    )
    _commit(db)
    return cycle_view(item)


def transition_cycle(
    db: Session,
    org: UUID,
    item_id: UUID,
    actor: User,
    data: StateCommand,
    request_id: str,
) -> CycleView:
    require_permission(db, actor, org, "application.cycle.manage")
    item = _cycle(db, org, item_id, True)
    allowed = {
        "draft": {"open", "cancelled"},
        "open": {"closed", "cancelled"},
        "closed": set(),
        "cancelled": set(),
    }
    if item.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    if data.target not in allowed[item.state]:
        raise AuthError("invalid_transition", 409)
    if data.target == "open":
        _validate_cycle_scope(db, org, item.program_id, item.cohort_id, item.form_id)
    item.state = data.target
    item.version += 1
    item.updated_at = now()
    _audit(
        db,
        actor,
        org,
        item.id,
        "application_cycle.state_changed",
        request_id,
        item.version,
        "state",
        data.reason,
    )
    _commit(db)
    return cycle_view(item)


def participant_view(db: Session, item: Participant) -> ParticipantView:
    person = db.get(Person, item.person_id)
    if not person:
        raise AuthError("not_found", 404)
    return ParticipantView(
        id=item.id,
        organization_id=item.organization_id,
        person_id=item.person_id,
        display_name=person.display_name,
        status=cast(ParticipantState, item.status),
        version=item.version,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def enrollment_view(item: Enrollment) -> EnrollmentView:
    return EnrollmentView(
        id=item.id,
        organization_id=item.organization_id,
        participant_id=item.participant_id,
        program_id=item.program_id,
        cohort_id=item.cohort_id,
        application_id=item.application_id,
        status=cast(EnrollmentState, item.status),
        enrolled_at=item.enrolled_at,
        version=item.version,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def session_view(item: ProgramSession) -> SessionView:
    return SessionView(
        id=item.id,
        organization_id=item.organization_id,
        cohort_id=item.cohort_id,
        title_en=item.title_en,
        title_ta=item.title_ta,
        starts_at=item.starts_at,
        ends_at=item.ends_at,
        mode=cast(SessionMode, item.mode),
        location=item.location,
        status=cast(SessionState, item.status),
        version=item.version,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _enrollment_candidates(db: Session, org: UUID) -> list[EnrollmentCandidateView]:
    rows = db.execute(
        select(Application, ApplicationCycle, SelectionCycle, Person)
        .join(ApplicationCycle, Application.cycle_id == ApplicationCycle.id)
        .join(SelectionCycle, SelectionCycle.application_cycle_id == ApplicationCycle.id)
        .join(Person, Person.id == Application.person_id)
        .where(
            Application.organization_id == org,
            Application.state == "selected",
            ApplicationCycle.cohort_id.is_not(None),
            SelectionCycle.state == "closed",
        )
        .order_by(Application.updated_at, Application.id)
        .limit(100)
    )
    return [
        EnrollmentCandidateView(
            application_id=application.id,
            application_number=application.application_number or "",
            application_version=application.version,
            person_id=application.person_id,
            display_name=person.display_name,
            program_id=cycle.program_id,
            cohort_id=cast(UUID, cycle.cohort_id),
            selection_cycle_id=selection.id,
        )
        for application, cycle, selection, person in rows
    ]


def convert_enrollment(
    db: Session,
    org: UUID,
    actor: User,
    data: EnrollmentConvert,
    request_id: str,
) -> EnrollmentConversionView:
    require_permission(db, actor, org, "enrollment.manage")
    application = db.scalar(
        select(Application)
        .where(Application.id == data.application_id, Application.organization_id == org)
        .with_for_update()
    )
    if not application:
        raise AuthError("not_found", 404)
    if application.version != data.expected_application_version:
        raise AuthError("version_conflict", 409)
    if application.state != "selected":
        raise AuthError("application_not_selected", 409)
    cycle = db.scalar(
        select(ApplicationCycle)
        .where(ApplicationCycle.id == application.cycle_id, ApplicationCycle.organization_id == org)
        .with_for_update()
    )
    if not cycle or not cycle.cohort_id:
        raise AuthError("enrollment_cohort_required", 422)
    selection = db.scalar(
        select(SelectionCycle).where(
            SelectionCycle.application_cycle_id == cycle.id,
            SelectionCycle.organization_id == org,
        )
    )
    if not selection or selection.state != "closed":
        raise AuthError("selection_not_finalized", 409)
    cohort = _cohort(db, org, cycle.cohort_id, True)
    if cohort.program_id != cycle.program_id or cohort.state != "active":
        raise AuthError("cohort_not_active", 409)
    enrolled_count = (
        db.scalar(
            select(func.count())
            .select_from(Enrollment)
            .where(
                Enrollment.cohort_id == cohort.id,
                Enrollment.status == "active",
            )
        )
        or 0
    )
    if cohort.capacity is not None and enrolled_count >= cohort.capacity:
        raise AuthError("cohort_capacity_reached", 409)
    participant = db.scalar(
        select(Participant)
        .where(Participant.organization_id == org, Participant.person_id == application.person_id)
        .with_for_update()
    )
    created_participant = participant is None
    if participant is None:
        participant = Participant(organization_id=org, person_id=application.person_id)
        db.add(participant)
        db.flush()
        db.add(
            ParticipantStatusHistory(
                participant_id=participant.id,
                actor_user_id=actor.id,
                from_status=None,
                to_status="active",
                participant_version=1,
                reason=data.reason,
            )
        )
    elif participant.status != "active":
        raise AuthError("participant_not_active", 409)
    enrollment = Enrollment(
        organization_id=org,
        participant_id=participant.id,
        program_id=cycle.program_id,
        cohort_id=cohort.id,
        application_id=application.id,
    )
    db.add(enrollment)
    application.state = "enrolled"
    application.version += 1
    application.updated_at = now()
    db.add(
        ApplicationStatusHistory(
            application_id=application.id,
            actor_user_id=actor.id,
            from_state="selected",
            to_state="enrolled",
            application_version=application.version,
            reason_code="enrollment_conversion",
        )
    )
    user = db.scalar(select(User).where(User.person_id == application.person_id))
    role = db.scalar(select(Role).where(Role.name == "Participant"))
    if not user or not role:
        raise AuthError("participant_account_unavailable", 409)
    if not db.scalar(
        select(UserRole.id).where(
            UserRole.user_id == user.id,
            UserRole.role_id == role.id,
            UserRole.organization_id == org,
        )
    ):
        db.add(UserRole(user_id=user.id, role_id=role.id, organization_id=org))
    db.flush()
    db.add(
        DomainOutbox(
            event_key=f"enrollment.created:{enrollment.id}",
            event_type="enrollment.created",
            aggregate_type="enrollment",
            aggregate_id=enrollment.id,
            organization_id=org,
            payload=json.dumps(
                {
                    "enrollment_id": str(enrollment.id),
                    "application_id": str(application.id),
                    "participant_id": str(participant.id),
                },
                separators=(",", ":"),
                sort_keys=True,
            ),
        )
    )
    _audit(
        db,
        actor,
        org,
        enrollment.id,
        "enrollment.created",
        request_id,
        1,
        "participant_id,program_id,cohort_id,application_id,status",
        data.reason,
    )
    if created_participant:
        _audit(
            db,
            actor,
            org,
            participant.id,
            "participant.created",
            request_id,
            1,
            "person_id,status",
            data.reason,
        )
    _commit(db)
    db.refresh(participant)
    db.refresh(enrollment)
    return EnrollmentConversionView(
        participant=participant_view(db, participant),
        enrollment=enrollment_view(enrollment),
    )


def transition_participant(
    db: Session,
    org: UUID,
    participant_id: UUID,
    actor: User,
    data: ParticipantStateCommand,
    request_id: str,
) -> ParticipantView:
    scope = _staff_scope(db, org, actor, "participant.update")
    participant = db.scalar(
        select(Participant)
        .where(Participant.id == participant_id, Participant.organization_id == org)
        .with_for_update()
    )
    if not participant:
        raise AuthError("not_found", 404)
    _require_participant_scope(db, org, participant.id, scope)
    if participant.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    allowed = {
        "active": {"suspended", "completed", "withdrawn"},
        "suspended": {"active", "withdrawn"},
        "completed": set(),
        "withdrawn": set(),
    }
    if data.target not in allowed[participant.status]:
        raise AuthError("invalid_transition", 409)
    previous = participant.status
    participant.status = data.target
    participant.version += 1
    participant.updated_at = now()
    db.add(
        ParticipantStatusHistory(
            participant_id=participant.id,
            actor_user_id=actor.id,
            from_status=previous,
            to_status=data.target,
            participant_version=participant.version,
            reason=data.reason,
        )
    )
    _audit(
        db,
        actor,
        org,
        participant.id,
        "participant.state_changed",
        request_id,
        participant.version,
        "status",
        data.reason,
    )
    _commit(db)
    return participant_view(db, participant)


def create_session(
    db: Session,
    org: UUID,
    actor: User,
    data: SessionCreate,
    request_id: str,
) -> SessionView:
    scope = _staff_scope(db, org, actor, "schedule.manage")
    cohort = _cohort(db, org, data.cohort_id)
    _require_cohort_scope(cohort, scope)
    if cohort.state not in {"planned", "active"}:
        raise AuthError("cohort_not_schedulable", 409)
    if data.starts_at.date() < cohort.starts_on or data.ends_at.date() > cohort.ends_on:
        raise AuthError("session_outside_cohort", 422)
    item = ProgramSession(organization_id=org, **data.model_dump())
    db.add(item)
    _flush(db)
    _audit(
        db,
        actor,
        org,
        item.id,
        "program_session.created",
        request_id,
        1,
        "cohort_id,title,window,mode,location",
    )
    _commit(db)
    return session_view(item)


def transition_session(
    db: Session,
    org: UUID,
    session_id: UUID,
    actor: User,
    data: SessionStateCommand,
    request_id: str,
) -> SessionView:
    scope = _staff_scope(db, org, actor, "schedule.manage")
    item = db.scalar(
        select(ProgramSession)
        .where(ProgramSession.id == session_id, ProgramSession.organization_id == org)
        .with_for_update()
    )
    if not item:
        raise AuthError("not_found", 404)
    cohort = _cohort(db, org, item.cohort_id)
    _require_cohort_scope(cohort, scope)
    if item.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    if item.status != "scheduled":
        raise AuthError("invalid_transition", 409)
    item.status = data.target
    item.version += 1
    item.updated_at = now()
    _audit(
        db,
        actor,
        org,
        item.id,
        "program_session.state_changed",
        request_id,
        item.version,
        "status",
        data.reason,
    )
    _commit(db)
    return session_view(item)


def my_timeline(db: Session, org: UUID, actor: User) -> ParticipantTimeline:
    require_permission(db, actor, org, "participant.self")
    participant = db.scalar(
        select(Participant).where(
            Participant.organization_id == org,
            Participant.person_id == actor.person_id,
        )
    )
    if not participant:
        raise AuthError("not_found", 404)
    enrollments = list(
        db.scalars(
            select(Enrollment)
            .where(Enrollment.organization_id == org, Enrollment.participant_id == participant.id)
            .order_by(Enrollment.enrolled_at, Enrollment.id)
        )
    )
    cohort_ids = [item.cohort_id for item in enrollments]
    sessions = (
        list(
            db.scalars(
                select(ProgramSession)
                .where(
                    ProgramSession.organization_id == org, ProgramSession.cohort_id.in_(cohort_ids)
                )
                .order_by(ProgramSession.starts_at, ProgramSession.id)
            )
        )
        if cohort_ids
        else []
    )
    events: list[TimelineEvent] = []
    for enrollment in enrollments:
        application = db.get(Application, enrollment.application_id)
        if application:
            events.append(
                TimelineEvent(
                    occurred_at=application.submitted_at or application.created_at,
                    kind="application",
                    state="submitted",
                    title_en="Application submitted",
                    title_ta="\u0bb5\u0bbf\u0ba3\u0bcd\u0ba3\u0baa\u0bcd\u0baa\u0bae\u0bcd",
                    resource_id=application.id,
                )
            )
            decision = db.scalar(
                select(SelectionDecision)
                .where(
                    SelectionDecision.application_id == application.id,
                    SelectionDecision.to_state == "selected",
                )
                .order_by(SelectionDecision.created_at.desc())
                .limit(1)
            )
            if decision:
                events.append(
                    TimelineEvent(
                        occurred_at=decision.created_at,
                        kind="selection",
                        state="selected",
                        title_en="Selected",
                        title_ta="\u0ba4\u0bc7\u0bb0\u0bcd\u0ba8\u0bcd\u0ba4\u0bc6\u0b9f\u0bc1\u0b95\u0bcd\u0b95\u0baa\u0bcd\u0baa\u0b9f\u0bcd\u0b9f\u0bbe\u0bb0\u0bcd",
                        resource_id=decision.id,
                    )
                )
        events.append(
            TimelineEvent(
                occurred_at=enrollment.enrolled_at,
                kind="enrollment",
                state=enrollment.status,
                title_en="Enrollment created",
                title_ta="\u0b9a\u0bc7\u0bb0\u0bcd\u0b95\u0bcd\u0b95\u0bc8",
                resource_id=enrollment.id,
            )
        )
    for item in sessions:
        events.append(
            TimelineEvent(
                occurred_at=item.starts_at,
                kind="session",
                state=item.status,
                title_en=item.title_en,
                title_ta=item.title_ta,
                resource_id=item.id,
            )
        )
    events.sort(key=lambda event: (event.occurred_at, str(event.resource_id)))
    return ParticipantTimeline(
        participant=participant_view(db, participant),
        enrollments=[enrollment_view(item) for item in enrollments],
        sessions=[session_view(item) for item in sessions],
        events=events,
    )
