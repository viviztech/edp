from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.applications.models import ApplicationForm
from app.modules.identity.models import AuditLog, User, now
from app.modules.identity.security import AuthError
from app.modules.identity.service import require_permission
from app.modules.programs.models import ApplicationCycle, Cohort, Program, TrainingCenter
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
    NamedCreate,
    NamedUpdate,
    ProgramState,
    ProgramView,
    StateCommand,
)


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


def catalog(db: Session, org: UUID, actor: User) -> CatalogView:
    require_permission(db, actor, org, "program.view")
    return CatalogView(
        programs=[
            program_view(item)
            for item in db.scalars(
                select(Program)
                .where(Program.organization_id == org)
                .order_by(Program.created_at, Program.id)
                .limit(100)
            )
        ],
        centers=[
            center_view(item)
            for item in db.scalars(
                select(TrainingCenter)
                .where(TrainingCenter.organization_id == org)
                .order_by(TrainingCenter.created_at, TrainingCenter.id)
                .limit(100)
            )
        ],
        cohorts=[
            cohort_view(item)
            for item in db.scalars(
                select(Cohort)
                .where(Cohort.organization_id == org)
                .order_by(Cohort.starts_on, Cohort.id)
                .limit(100)
            )
        ],
        cycles=[
            cycle_view(item)
            for item in db.scalars(
                select(ApplicationCycle)
                .where(ApplicationCycle.organization_id == org)
                .order_by(ApplicationCycle.opens_at, ApplicationCycle.id)
                .limit(100)
            )
        ],
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
    require_permission(db, actor, org, "cohort.manage")
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
    require_permission(db, actor, org, "cohort.manage")
    item = _cohort(db, org, item_id, True)
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
    require_permission(db, actor, org, "cohort.manage")
    item = _cohort(db, org, item_id, True)
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
