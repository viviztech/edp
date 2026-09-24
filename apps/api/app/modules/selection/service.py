from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import cast
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.applications.models import Application, ApplicationStatusHistory
from app.modules.identity.models import (
    AuditLog,
    Person,
    RolePermission,
    User,
    UserRole,
    now,
)
from app.modules.identity.security import AuthError
from app.modules.identity.service import require_permission
from app.modules.programs.models import ApplicationCycle
from app.modules.selection.models import (
    ApplicationScore,
    Interview,
    InterviewPanelMember,
    ReviewAssignment,
    SelectionCriterion,
    SelectionCycle,
    SelectionDecision,
    SelectionRubric,
)
from app.modules.selection.schemas import (
    ApplicationAggregateView,
    AssignmentCreate,
    AssignmentView,
    ConflictCommand,
    CriterionView,
    CycleCommand,
    DecisionCommand,
    DecisionView,
    InterviewComplete,
    InterviewCreate,
    InterviewView,
    ModerationCommand,
    PanelMemberView,
    PanelScoreSubmit,
    ReviewerView,
    ReviewSave,
    ReviewSubmit,
    RubricCommand,
    RubricUpdate,
    RubricView,
    ScoreView,
    SelectionCycleCreate,
    SelectionCycleUpdate,
    SelectionCycleView,
    SelectionWorkspace,
    SubmittedApplicationSummary,
)


def _has_permission(db: Session, actor: User, org: UUID, permission: str) -> bool:
    return bool(
        db.scalar(
            select(UserRole.id)
            .join(RolePermission, RolePermission.role_id == UserRole.role_id)
            .where(
                UserRole.user_id == actor.id,
                UserRole.organization_id == org,
                RolePermission.permission_code == permission,
            )
            .limit(1)
        )
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


def _commit(db: Session, code: str = "version_conflict") -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError(code, 409) from exc


def _cycle_view(item: SelectionCycle) -> SelectionCycleView:
    return SelectionCycleView(
        id=item.id,
        organization_id=item.organization_id,
        application_cycle_id=item.application_cycle_id,
        code=item.code,
        name_en=item.name_en,
        name_ta=item.name_ta,
        state=item.state,
        version=item.version,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _criteria(db: Session, rubric_id: UUID) -> list[SelectionCriterion]:
    return list(
        db.scalars(
            select(SelectionCriterion)
            .where(SelectionCriterion.rubric_id == rubric_id)
            .order_by(SelectionCriterion.position, SelectionCriterion.id)
            .limit(26)
        )
    )


def _rubric_view(db: Session, item: SelectionRubric) -> RubricView:
    return RubricView(
        id=item.id,
        organization_id=item.organization_id,
        selection_cycle_id=item.selection_cycle_id,
        version_number=item.version_number,
        state=item.state,
        edit_version=item.edit_version,
        published_at=item.published_at,
        criteria=[
            CriterionView(
                id=criterion.id,
                key=criterion.criterion_key,
                label_en=criterion.label_en,
                label_ta=criterion.label_ta,
                guidance_en=criterion.guidance_en,
                guidance_ta=criterion.guidance_ta,
                weight=criterion.weight,
                minimum_score=criterion.minimum_score,
                maximum_score=criterion.maximum_score,
                position=criterion.position,
                required=criterion.required,
            )
            for criterion in _criteria(db, item.id)
        ],
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _assignment_view(db: Session, item: ReviewAssignment) -> AssignmentView:
    application = db.get(Application, item.application_id)
    reviewer = db.get(User, item.reviewer_user_id)
    person = db.get(Person, reviewer.person_id) if reviewer else None
    if not application or not application.application_number or not person:
        raise AuthError("selection_integrity_error", 503)
    return AssignmentView(
        id=item.id,
        organization_id=item.organization_id,
        selection_cycle_id=item.selection_cycle_id,
        rubric_id=item.rubric_id,
        application_id=item.application_id,
        application_number=application.application_number,
        reviewer_user_id=item.reviewer_user_id,
        reviewer_name=person.display_name,
        status=item.status,
        conflict_status=item.conflict_status,
        conflict_note=item.conflict_note,
        scores=[
            ScoreView(criterion_id=row.criterion_id, score=Decimal(str(row.score)))
            for row in db.scalars(
                select(ApplicationScore)
                .where(ApplicationScore.assignment_id == item.id)
                .order_by(ApplicationScore.criterion_id)
            )
        ],
        internal_comment=item.internal_comment,
        weighted_score=Decimal(str(item.weighted_score))
        if item.weighted_score is not None
        else None,
        submitted_at=item.submitted_at,
        moderation_status=item.moderation_status,
        moderation_reason=item.moderation_reason,
        moderated_at=item.moderated_at,
        version=item.version,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _aggregate_views(
    db: Session, assignments: list[ReviewAssignment]
) -> list[ApplicationAggregateView]:
    grouped: dict[tuple[UUID, UUID], list[ReviewAssignment]] = {}
    for assignment in assignments:
        grouped.setdefault((assignment.application_id, assignment.selection_cycle_id), []).append(
            assignment
        )
    result: list[ApplicationAggregateView] = []
    for (application_id, cycle_id), rows in grouped.items():
        completed = [item for item in rows if item.status == "completed"]
        included = [
            item
            for item in completed
            if item.moderation_status == "included" and item.weighted_score is not None
        ]
        application = db.get(Application, application_id)
        if not application or not application.application_number:
            raise AuthError("selection_integrity_error", 503)
        aggregate = None
        if included:
            aggregate = (
                sum((Decimal(str(item.weighted_score)) for item in included), Decimal("0"))
                / Decimal(len(included))
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        result.append(
            ApplicationAggregateView(
                application_id=application_id,
                application_number=application.application_number,
                application_state=application.state,
                application_version=application.version,
                selection_cycle_id=cycle_id,
                completed_reviews=len(completed),
                included_reviews=len(included),
                excluded_reviews=len(completed) - len(included),
                aggregate_score=aggregate,
            )
        )
    return sorted(result, key=lambda item: (item.application_number, str(item.application_id)))


def workspace(db: Session, org: UUID, actor: User) -> SelectionWorkspace:
    require_permission(db, actor, org, "selection.cycle.view")
    can_manage = _has_permission(db, actor, org, "selection.assignment.manage")
    cycles = list(
        db.scalars(
            select(SelectionCycle)
            .where(SelectionCycle.organization_id == org)
            .order_by(SelectionCycle.created_at, SelectionCycle.id)
            .limit(100)
        )
    )
    cycle_ids = [item.id for item in cycles]
    rubrics = (
        list(
            db.scalars(
                select(SelectionRubric)
                .where(SelectionRubric.selection_cycle_id.in_(cycle_ids))
                .order_by(SelectionRubric.selection_cycle_id, SelectionRubric.version_number)
                .limit(300)
            )
        )
        if cycle_ids
        else []
    )
    application_cycle_ids = [item.application_cycle_id for item in cycles]
    applications = (
        list(
            db.scalars(
                select(Application)
                .where(
                    Application.organization_id == org,
                    Application.cycle_id.in_(application_cycle_ids),
                    Application.state.in_(("submitted", "under_review")),
                )
                .order_by(Application.submitted_at, Application.id)
                .limit(500)
            )
        )
        if can_manage and application_cycle_ids
        else []
    )
    reviewer_rows = (
        db.execute(
            select(User.id, Person.display_name)
            .join(Person, Person.id == User.person_id)
            .join(UserRole, UserRole.user_id == User.id)
            .join(RolePermission, RolePermission.role_id == UserRole.role_id)
            .where(
                UserRole.organization_id == org,
                RolePermission.permission_code == "selection.review",
                User.status == "active",
            )
            .distinct()
            .order_by(Person.display_name, User.id)
            .limit(100)
        ).all()
        if can_manage
        else []
    )
    assignment_query = select(ReviewAssignment).where(ReviewAssignment.organization_id == org)
    if not can_manage:
        assignment_query = assignment_query.where(ReviewAssignment.reviewer_user_id == actor.id)
    assignments = list(
        db.scalars(assignment_query.order_by(ReviewAssignment.created_at).limit(500))
    )
    return SelectionWorkspace(
        cycles=[_cycle_view(item) for item in cycles],
        rubrics=[_rubric_view(db, item) for item in rubrics],
        applications=[
            SubmittedApplicationSummary(
                id=item.id,
                application_number=cast(str, item.application_number),
                state=item.state,
                submitted_at=cast(datetime, item.submitted_at),
            )
            for item in applications
        ],
        reviewers=[ReviewerView(id=user_id, display_name=name) for user_id, name in reviewer_rows],
        assignments=[_assignment_view(db, item) for item in assignments],
        aggregates=_aggregate_views(db, assignments) if can_manage else [],
        interviews=_workspace_interviews(db, org, actor, can_manage),
        decisions=_workspace_decisions(db, org, can_manage),
    )


def create_cycle(
    db: Session,
    org: UUID,
    actor: User,
    data: SelectionCycleCreate,
    request_id: str,
) -> SelectionCycleView:
    require_permission(db, actor, org, "selection.cycle.manage")
    source = db.scalar(
        select(ApplicationCycle).where(
            ApplicationCycle.id == data.application_cycle_id,
            ApplicationCycle.organization_id == org,
        )
    )
    if not source or source.state == "cancelled":
        raise AuthError("invalid_application_cycle", 422)
    item = SelectionCycle(
        organization_id=org,
        application_cycle_id=data.application_cycle_id,
        code=data.code,
        name_en=data.name_en,
        name_ta=data.name_ta,
    )
    db.add(item)
    db.flush()
    rubric = SelectionRubric(
        organization_id=org,
        selection_cycle_id=item.id,
        version_number=1,
    )
    db.add(rubric)
    _audit(db, actor, org, item.id, "selection.cycle.created", request_id, 1, "cycle")
    _commit(db, "selection_cycle_conflict")
    db.refresh(item)
    return _cycle_view(item)


def update_cycle(
    db: Session,
    org: UUID,
    cycle_id: UUID,
    actor: User,
    data: SelectionCycleUpdate,
    request_id: str,
) -> SelectionCycleView:
    require_permission(db, actor, org, "selection.cycle.manage")
    item = db.scalar(
        select(SelectionCycle)
        .where(SelectionCycle.id == cycle_id, SelectionCycle.organization_id == org)
        .with_for_update()
    )
    if not item:
        raise AuthError("not_found", 404)
    if item.state != "draft":
        raise AuthError("selection_cycle_immutable", 409)
    if item.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    item.name_en, item.name_ta = data.name_en, data.name_ta
    item.version += 1
    item.updated_at = now()
    _audit(db, actor, org, item.id, "selection.cycle.updated", request_id, item.version, "names")
    _commit(db)
    db.refresh(item)
    return _cycle_view(item)


def transition_cycle(
    db: Session,
    org: UUID,
    cycle_id: UUID,
    actor: User,
    data: CycleCommand,
    request_id: str,
) -> SelectionCycleView:
    require_permission(
        db,
        actor,
        org,
        "selection.finalize" if data.target == "closed" else "selection.cycle.manage",
    )
    item = db.scalar(
        select(SelectionCycle)
        .where(SelectionCycle.id == cycle_id, SelectionCycle.organization_id == org)
        .with_for_update()
    )
    if not item:
        raise AuthError("not_found", 404)
    if item.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    allowed = {"draft": "active", "active": "closed"}
    if allowed.get(item.state) != data.target:
        raise AuthError("invalid_state_transition", 409)
    if data.target == "active":
        source = db.get(ApplicationCycle, item.application_cycle_id)
        published = db.scalar(
            select(SelectionRubric.id).where(
                SelectionRubric.selection_cycle_id == item.id,
                SelectionRubric.state == "published",
            )
        )
        if not source or source.state != "closed" or not published:
            raise AuthError("selection_cycle_not_ready", 422)
    if data.target == "closed":
        has_assignment = db.scalar(
            select(ReviewAssignment.id)
            .where(ReviewAssignment.selection_cycle_id == item.id)
            .limit(1)
        )
        if not has_assignment:
            raise AuthError("selection_cycle_not_finalizable", 422)
        assigned_application_ids = select(ReviewAssignment.application_id).where(
            ReviewAssignment.selection_cycle_id == item.id
        )
        unfinished = db.scalar(
            select(Application.id)
            .where(
                Application.id.in_(assigned_application_ids),
                Application.state.notin_(("selected", "waitlisted", "rejected")),
            )
            .limit(1)
        )
        open_interview = db.scalar(
            select(Interview.id)
            .where(
                Interview.selection_cycle_id == item.id,
                Interview.status == "scheduled",
            )
            .limit(1)
        )
        if unfinished or open_interview:
            raise AuthError("selection_cycle_not_finalizable", 422)
    item.state = data.target
    item.version += 1
    item.updated_at = now()
    _audit(
        db,
        actor,
        org,
        item.id,
        "selection.cycle.state_changed",
        request_id,
        item.version,
        "state",
        data.reason,
    )
    _commit(db)
    db.refresh(item)
    return _cycle_view(item)


def update_rubric(
    db: Session,
    org: UUID,
    rubric_id: UUID,
    actor: User,
    data: RubricUpdate,
    request_id: str,
) -> RubricView:
    require_permission(db, actor, org, "selection.rubric.manage")
    rubric = db.scalar(
        select(SelectionRubric)
        .where(SelectionRubric.id == rubric_id, SelectionRubric.organization_id == org)
        .with_for_update()
    )
    if not rubric:
        raise AuthError("not_found", 404)
    if rubric.state != "draft":
        raise AuthError("rubric_immutable", 409)
    if rubric.edit_version != data.expected_edit_version:
        raise AuthError("version_conflict", 409)
    db.execute(delete(SelectionCriterion).where(SelectionCriterion.rubric_id == rubric.id))
    db.add_all(
        [
            SelectionCriterion(
                rubric_id=rubric.id,
                criterion_key=item.key,
                label_en=item.label_en,
                label_ta=item.label_ta,
                guidance_en=item.guidance_en,
                guidance_ta=item.guidance_ta,
                weight=item.weight,
                minimum_score=item.minimum_score,
                maximum_score=item.maximum_score,
                position=position,
                required=item.required,
            )
            for position, item in enumerate(data.criteria)
        ]
    )
    rubric.edit_version += 1
    rubric.updated_at = now()
    _audit(
        db,
        actor,
        org,
        rubric.id,
        "selection.rubric.updated",
        request_id,
        rubric.edit_version,
        "criteria",
    )
    _commit(db)
    db.refresh(rubric)
    return _rubric_view(db, rubric)


def publish_rubric(
    db: Session,
    org: UUID,
    rubric_id: UUID,
    actor: User,
    data: RubricCommand,
    request_id: str,
) -> RubricView:
    require_permission(db, actor, org, "selection.rubric.publish")
    rubric = db.scalar(
        select(SelectionRubric)
        .where(SelectionRubric.id == rubric_id, SelectionRubric.organization_id == org)
        .with_for_update()
    )
    if not rubric:
        raise AuthError("not_found", 404)
    if rubric.state != "draft":
        raise AuthError("rubric_immutable", 409)
    if rubric.edit_version != data.expected_edit_version:
        raise AuthError("version_conflict", 409)
    criteria = _criteria(db, rubric.id)
    if not criteria or sum(item.weight for item in criteria) != 100:
        raise AuthError("rubric_invalid", 422)
    previous = db.scalar(
        select(SelectionRubric)
        .where(
            SelectionRubric.selection_cycle_id == rubric.selection_cycle_id,
            SelectionRubric.state == "published",
        )
        .with_for_update()
    )
    if previous:
        previous.state = "retired"
        previous.updated_at = now()
        db.flush()
    rubric.state = "published"
    rubric.published_at = now()
    rubric.updated_at = rubric.published_at
    _audit(
        db,
        actor,
        org,
        rubric.id,
        "selection.rubric.published",
        request_id,
        rubric.edit_version,
        "state",
    )
    _commit(db)
    db.refresh(rubric)
    return _rubric_view(db, rubric)


def copy_rubric(
    db: Session,
    org: UUID,
    rubric_id: UUID,
    actor: User,
    request_id: str,
) -> RubricView:
    require_permission(db, actor, org, "selection.rubric.manage")
    source = db.scalar(
        select(SelectionRubric)
        .where(SelectionRubric.id == rubric_id, SelectionRubric.organization_id == org)
        .with_for_update()
    )
    if not source:
        raise AuthError("not_found", 404)
    if source.state not in {"published", "retired"}:
        raise AuthError("rubric_not_published", 409)
    existing = db.scalar(
        select(SelectionRubric.id).where(
            SelectionRubric.selection_cycle_id == source.selection_cycle_id,
            SelectionRubric.state == "draft",
        )
    )
    if existing:
        raise AuthError("rubric_draft_exists", 409)
    version_number = db.scalar(
        select(func.max(SelectionRubric.version_number)).where(
            SelectionRubric.selection_cycle_id == source.selection_cycle_id
        )
    )
    copied = SelectionRubric(
        organization_id=org,
        selection_cycle_id=source.selection_cycle_id,
        version_number=int(version_number or 0) + 1,
    )
    db.add(copied)
    db.flush()
    db.add_all(
        [
            SelectionCriterion(
                rubric_id=copied.id,
                criterion_key=item.criterion_key,
                label_en=item.label_en,
                label_ta=item.label_ta,
                guidance_en=item.guidance_en,
                guidance_ta=item.guidance_ta,
                weight=item.weight,
                minimum_score=item.minimum_score,
                maximum_score=item.maximum_score,
                position=item.position,
                required=item.required,
            )
            for item in _criteria(db, source.id)
        ]
    )
    _audit(db, actor, org, copied.id, "selection.rubric.copied", request_id, 1, "source")
    _commit(db)
    db.refresh(copied)
    return _rubric_view(db, copied)


def create_assignment(
    db: Session,
    org: UUID,
    actor: User,
    data: AssignmentCreate,
    request_id: str,
) -> AssignmentView:
    require_permission(db, actor, org, "selection.assignment.manage")
    cycle = db.scalar(
        select(SelectionCycle)
        .where(
            SelectionCycle.id == data.selection_cycle_id,
            SelectionCycle.organization_id == org,
        )
        .with_for_update()
    )
    application = db.scalar(
        select(Application)
        .where(Application.id == data.application_id, Application.organization_id == org)
        .with_for_update()
    )
    if not cycle or cycle.state != "active":
        raise AuthError("selection_cycle_not_active", 422)
    if (
        not application
        or application.cycle_id != cycle.application_cycle_id
        or application.state not in {"submitted", "under_review"}
    ):
        raise AuthError("application_not_reviewable", 422)
    reviewer = db.get(User, data.reviewer_user_id)
    if (
        not reviewer
        or reviewer.status != "active"
        or not _has_permission(db, reviewer, org, "selection.review")
    ):
        raise AuthError("reviewer_not_eligible", 422)
    rubric = db.scalar(
        select(SelectionRubric).where(
            SelectionRubric.selection_cycle_id == cycle.id,
            SelectionRubric.state == "published",
        )
    )
    if not rubric:
        raise AuthError("rubric_not_published", 422)
    assignment = ReviewAssignment(
        organization_id=org,
        selection_cycle_id=cycle.id,
        rubric_id=rubric.id,
        application_id=application.id,
        reviewer_user_id=reviewer.id,
    )
    db.add(assignment)
    if application.state == "submitted":
        old_version = application.version
        application.state = "under_review"
        application.version += 1
        application.updated_at = now()
        db.add(
            ApplicationStatusHistory(
                application_id=application.id,
                actor_user_id=actor.id,
                from_state="submitted",
                to_state="under_review",
                application_version=application.version,
                reason_code="review_assigned",
            )
        )
        if application.version != old_version + 1:
            raise AuthError("version_conflict", 409)
    db.flush()
    _audit(
        db,
        actor,
        org,
        assignment.id,
        "selection.review.assigned",
        request_id,
        1,
        "application_id,reviewer_user_id,rubric_id",
    )
    _commit(db, "assignment_conflict")
    db.refresh(assignment)
    return _assignment_view(db, assignment)


def declare_conflict(
    db: Session,
    org: UUID,
    assignment_id: UUID,
    actor: User,
    data: ConflictCommand,
    request_id: str,
) -> AssignmentView:
    require_permission(db, actor, org, "selection.review")
    assignment = db.scalar(
        select(ReviewAssignment)
        .where(
            ReviewAssignment.id == assignment_id,
            ReviewAssignment.organization_id == org,
            ReviewAssignment.reviewer_user_id == actor.id,
        )
        .with_for_update()
    )
    if not assignment:
        raise AuthError("not_found", 404)
    if assignment.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    if assignment.conflict_status != "pending":
        raise AuthError("conflict_already_declared", 409)
    assignment.conflict_status = data.status
    assignment.conflict_note = data.note
    assignment.status = "in_review" if data.status == "clear" else "assigned"
    assignment.version += 1
    assignment.updated_at = now()
    _audit(
        db,
        actor,
        org,
        assignment.id,
        "selection.review.conflict_declared",
        request_id,
        assignment.version,
        "conflict_status,status",
    )
    _commit(db)
    db.refresh(assignment)
    return _assignment_view(db, assignment)


def _review_assignment(
    db: Session, org: UUID, assignment_id: UUID, actor: User
) -> ReviewAssignment:
    assignment = db.scalar(
        select(ReviewAssignment)
        .where(
            ReviewAssignment.id == assignment_id,
            ReviewAssignment.organization_id == org,
            ReviewAssignment.reviewer_user_id == actor.id,
        )
        .with_for_update()
    )
    if not assignment:
        raise AuthError("not_found", 404)
    return assignment


def _validate_scores(
    db: Session, assignment: ReviewAssignment, data: ReviewSave, require_complete: bool
) -> tuple[list[SelectionCriterion], dict[UUID, Decimal]]:
    criteria = _criteria(db, assignment.rubric_id)
    by_id = {item.id: item for item in criteria}
    values = {item.criterion_id: item.score for item in data.scores}
    if any(criterion_id not in by_id for criterion_id in values):
        raise AuthError("invalid_review_criterion", 422)
    if require_complete and any(item.required and item.id not in values for item in criteria):
        raise AuthError("required_scores_missing", 422)
    for criterion_id, score in values.items():
        criterion = by_id[criterion_id]
        if score < criterion.minimum_score or score > criterion.maximum_score:
            raise AuthError("score_out_of_range", 422)
    return criteria, values


def _weighted_total(criteria: list[SelectionCriterion], values: dict[UUID, Decimal]) -> Decimal:
    total = Decimal("0")
    for criterion in criteria:
        score = values.get(criterion.id)
        if score is None:
            continue
        span = Decimal(criterion.maximum_score - criterion.minimum_score)
        normalized = (score - Decimal(criterion.minimum_score)) / span
        total += Decimal(criterion.weight) * normalized
    return total.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def save_review(
    db: Session,
    org: UUID,
    assignment_id: UUID,
    actor: User,
    data: ReviewSave,
    request_id: str,
) -> AssignmentView:
    require_permission(db, actor, org, "selection.review")
    assignment = _review_assignment(db, org, assignment_id, actor)
    if assignment.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    if assignment.status == "completed":
        raise AuthError("review_immutable", 409)
    if assignment.conflict_status != "clear":
        raise AuthError("review_conflict_not_clear", 409)
    cycle = db.get(SelectionCycle, assignment.selection_cycle_id)
    if not cycle or cycle.state != "active":
        raise AuthError("selection_cycle_not_active", 409)
    _, values = _validate_scores(db, assignment, data, False)
    db.execute(delete(ApplicationScore).where(ApplicationScore.assignment_id == assignment.id))
    db.add_all(
        ApplicationScore(
            assignment_id=assignment.id,
            rubric_id=assignment.rubric_id,
            criterion_id=criterion_id,
            score=score,
        )
        for criterion_id, score in values.items()
    )
    assignment.internal_comment = data.internal_comment
    assignment.status = "in_review"
    assignment.version += 1
    assignment.updated_at = now()
    _audit(
        db,
        actor,
        org,
        assignment.id,
        "selection.review.saved",
        request_id,
        assignment.version,
        "scores,internal_comment",
    )
    _commit(db)
    db.refresh(assignment)
    return _assignment_view(db, assignment)


def submit_review(
    db: Session,
    org: UUID,
    assignment_id: UUID,
    actor: User,
    data: ReviewSubmit,
    request_id: str,
) -> AssignmentView:
    require_permission(db, actor, org, "selection.review")
    assignment = _review_assignment(db, org, assignment_id, actor)
    if assignment.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    if assignment.status == "completed":
        raise AuthError("review_immutable", 409)
    if assignment.conflict_status != "clear":
        raise AuthError("review_conflict_not_clear", 409)
    cycle = db.get(SelectionCycle, assignment.selection_cycle_id)
    if not cycle or cycle.state != "active":
        raise AuthError("selection_cycle_not_active", 409)
    stored = list(
        db.scalars(select(ApplicationScore).where(ApplicationScore.assignment_id == assignment.id))
    )
    data_for_validation = ReviewSave(
        expected_version=data.expected_version,
        scores=[
            ScoreView(criterion_id=item.criterion_id, score=Decimal(str(item.score)))
            for item in stored
        ],
        internal_comment=assignment.internal_comment,
    )
    criteria, values = _validate_scores(db, assignment, data_for_validation, True)
    assignment.weighted_score = _weighted_total(criteria, values)
    assignment.status = "completed"
    assignment.submitted_at = now()
    assignment.version += 1
    assignment.updated_at = now()
    _audit(
        db,
        actor,
        org,
        assignment.id,
        "selection.review.submitted",
        request_id,
        assignment.version,
        "status,weighted_score,submitted_at",
    )
    _commit(db)
    db.refresh(assignment)
    return _assignment_view(db, assignment)


def moderate_review(
    db: Session,
    org: UUID,
    assignment_id: UUID,
    actor: User,
    data: ModerationCommand,
    request_id: str,
) -> AssignmentView:
    require_permission(db, actor, org, "selection.review.moderate")
    assignment = db.scalar(
        select(ReviewAssignment)
        .where(ReviewAssignment.id == assignment_id, ReviewAssignment.organization_id == org)
        .with_for_update()
    )
    if not assignment:
        raise AuthError("not_found", 404)
    if assignment.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    if assignment.status != "completed":
        raise AuthError("review_not_completed", 409)
    if assignment.moderation_status == data.status:
        raise AuthError("moderation_unchanged", 409)
    assignment.moderation_status = data.status
    assignment.moderation_reason = data.reason
    assignment.moderated_by_user_id = actor.id
    assignment.moderated_at = now()
    assignment.version += 1
    assignment.updated_at = now()
    _audit(
        db,
        actor,
        org,
        assignment.id,
        "selection.review.moderated",
        request_id,
        assignment.version,
        "moderation_status,moderation_reason",
        data.reason,
    )
    _commit(db)
    db.refresh(assignment)
    return _assignment_view(db, assignment)


def _panel_views(db: Session, interview_id: UUID) -> list[PanelMemberView]:
    rows = db.execute(
        select(InterviewPanelMember, Person.display_name)
        .join(User, User.id == InterviewPanelMember.user_id)
        .join(Person, Person.id == User.person_id)
        .where(InterviewPanelMember.interview_id == interview_id)
        .order_by(Person.display_name, InterviewPanelMember.id)
    ).all()
    return [
        PanelMemberView(
            id=item.id,
            user_id=item.user_id,
            display_name=name,
            score=Decimal(str(item.score)) if item.score is not None else None,
            comment=item.comment,
            submitted_at=item.submitted_at,
            version=item.version,
        )
        for item, name in rows
    ]


def _interview_view(db: Session, item: Interview) -> InterviewView:
    application = db.get(Application, item.application_id)
    if not application or not application.application_number:
        raise AuthError("selection_integrity_error", 503)
    return InterviewView(
        id=item.id,
        organization_id=item.organization_id,
        selection_cycle_id=item.selection_cycle_id,
        application_id=item.application_id,
        application_number=application.application_number,
        starts_at=item.starts_at,
        ends_at=item.ends_at,
        mode=item.mode,
        location=item.location,
        status=item.status,
        average_score=Decimal(str(item.average_score)) if item.average_score is not None else None,
        completed_at=item.completed_at,
        version=item.version,
        panel=_panel_views(db, item.id),
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _decision_view(db: Session, item: SelectionDecision) -> DecisionView:
    application = db.get(Application, item.application_id)
    if not application or not application.application_number:
        raise AuthError("selection_integrity_error", 503)
    return DecisionView(
        id=item.id,
        organization_id=item.organization_id,
        selection_cycle_id=item.selection_cycle_id,
        application_id=item.application_id,
        application_number=application.application_number,
        actor_user_id=item.actor_user_id,
        from_state=item.from_state,
        to_state=item.to_state,
        reason=item.reason,
        is_override=item.is_override,
        aggregate_score_snapshot=Decimal(str(item.aggregate_score_snapshot))
        if item.aggregate_score_snapshot is not None
        else None,
        interview_score_snapshot=Decimal(str(item.interview_score_snapshot))
        if item.interview_score_snapshot is not None
        else None,
        application_version=item.application_version,
        created_at=item.created_at,
    )


def _workspace_interviews(
    db: Session, org: UUID, actor: User, can_manage: bool
) -> list[InterviewView]:
    query = select(Interview).where(Interview.organization_id == org)
    if not can_manage:
        query = query.join(
            InterviewPanelMember, InterviewPanelMember.interview_id == Interview.id
        ).where(InterviewPanelMember.user_id == actor.id)
    rows = list(db.scalars(query.order_by(Interview.starts_at, Interview.id).limit(500)))
    return [_interview_view(db, item) for item in rows]


def _workspace_decisions(db: Session, org: UUID, can_manage: bool) -> list[DecisionView]:
    if not can_manage:
        return []
    rows = list(
        db.scalars(
            select(SelectionDecision)
            .where(SelectionDecision.organization_id == org)
            .order_by(SelectionDecision.created_at, SelectionDecision.id)
            .limit(1000)
        )
    )
    return [_decision_view(db, item) for item in rows]


def _application_aggregate(
    db: Session, selection_cycle_id: UUID, application_id: UUID
) -> Decimal | None:
    values = list(
        db.scalars(
            select(ReviewAssignment.weighted_score).where(
                ReviewAssignment.selection_cycle_id == selection_cycle_id,
                ReviewAssignment.application_id == application_id,
                ReviewAssignment.status == "completed",
                ReviewAssignment.moderation_status == "included",
            )
        )
    )
    scores = [Decimal(str(value)) for value in values if value is not None]
    if not scores:
        return None
    return (sum(scores, Decimal("0")) / Decimal(len(scores))).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def _transition_application(
    db: Session, application: Application, actor: User, target: str, reason_code: str
) -> None:
    previous = application.state
    application.state = target
    application.version += 1
    application.updated_at = now()
    db.add(
        ApplicationStatusHistory(
            application_id=application.id,
            actor_user_id=actor.id,
            from_state=previous,
            to_state=target,
            application_version=application.version,
            reason_code=reason_code,
        )
    )


def create_interview(
    db: Session, org: UUID, actor: User, data: InterviewCreate, request_id: str
) -> InterviewView:
    require_permission(db, actor, org, "selection.interview.manage")
    cycle = db.scalar(
        select(SelectionCycle)
        .where(
            SelectionCycle.id == data.selection_cycle_id,
            SelectionCycle.organization_id == org,
        )
        .with_for_update()
    )
    application = db.scalar(
        select(Application)
        .where(
            Application.id == data.application_id,
            Application.organization_id == org,
        )
        .with_for_update()
    )
    if not cycle or cycle.state != "active":
        raise AuthError("selection_cycle_not_active", 422)
    if (
        not application
        or application.cycle_id != cycle.application_cycle_id
        or application.state != "shortlisted"
    ):
        raise AuthError("application_not_shortlisted", 422)
    panel_users: list[User] = []
    for user_id in data.panel_user_ids:
        user = db.get(User, user_id)
        if (
            not user
            or user.status != "active"
            or not _has_permission(db, user, org, "selection.interview.score")
        ):
            raise AuthError("panel_member_not_eligible", 422)
        panel_users.append(user)
    interview = Interview(
        organization_id=org,
        selection_cycle_id=cycle.id,
        application_id=application.id,
        starts_at=data.starts_at,
        ends_at=data.ends_at,
        mode=data.mode,
        location=data.location,
    )
    db.add(interview)
    db.flush()
    db.add_all(
        InterviewPanelMember(interview_id=interview.id, user_id=user.id) for user in panel_users
    )
    _transition_application(db, application, actor, "interview_scheduled", "interview_scheduled")
    _audit(
        db,
        actor,
        org,
        interview.id,
        "selection.interview.scheduled",
        request_id,
        1,
        "application_id,starts_at,ends_at,mode,panel",
    )
    _commit(db, "interview_conflict")
    db.refresh(interview)
    return _interview_view(db, interview)


def submit_interview_score(
    db: Session,
    org: UUID,
    interview_id: UUID,
    actor: User,
    data: PanelScoreSubmit,
    request_id: str,
) -> InterviewView:
    require_permission(db, actor, org, "selection.interview.score")
    interview = db.scalar(
        select(Interview)
        .where(
            Interview.id == interview_id,
            Interview.organization_id == org,
        )
        .with_for_update()
    )
    if not interview:
        raise AuthError("not_found", 404)
    if interview.status != "scheduled":
        raise AuthError("interview_completed", 409)
    member = db.scalar(
        select(InterviewPanelMember)
        .where(
            InterviewPanelMember.interview_id == interview.id,
            InterviewPanelMember.user_id == actor.id,
        )
        .with_for_update()
    )
    if not member:
        raise AuthError("not_found", 404)
    if member.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    if member.submitted_at is not None:
        raise AuthError("interview_score_immutable", 409)
    member.score, member.comment, member.submitted_at = data.score, data.comment, now()
    member.version += 1
    _audit(
        db,
        actor,
        org,
        interview.id,
        "selection.interview.score_submitted",
        request_id,
        member.version,
        "score,comment,submitted_at",
    )
    _commit(db)
    db.refresh(interview)
    return _interview_view(db, interview)


def complete_interview(
    db: Session,
    org: UUID,
    interview_id: UUID,
    actor: User,
    data: InterviewComplete,
    request_id: str,
) -> InterviewView:
    require_permission(db, actor, org, "selection.interview.manage")
    interview = db.scalar(
        select(Interview)
        .where(
            Interview.id == interview_id,
            Interview.organization_id == org,
        )
        .with_for_update()
    )
    if not interview:
        raise AuthError("not_found", 404)
    if interview.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    if interview.status != "scheduled":
        raise AuthError("interview_completed", 409)
    members = list(
        db.scalars(
            select(InterviewPanelMember)
            .where(InterviewPanelMember.interview_id == interview.id)
            .with_for_update()
        )
    )
    if not members or any(item.score is None for item in members):
        raise AuthError("interview_scores_incomplete", 422)
    interview.average_score = (
        sum((Decimal(str(item.score)) for item in members), Decimal("0")) / Decimal(len(members))
    ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    interview.status, interview.completed_at = "completed", now()
    interview.version += 1
    interview.updated_at = now()
    _audit(
        db,
        actor,
        org,
        interview.id,
        "selection.interview.completed",
        request_id,
        interview.version,
        "status,average_score,completed_at",
    )
    _commit(db)
    db.refresh(interview)
    return _interview_view(db, interview)


def record_decision(
    db: Session,
    org: UUID,
    cycle_id: UUID,
    application_id: UUID,
    actor: User,
    data: DecisionCommand,
    request_id: str,
) -> DecisionView:
    permission = (
        "selection.decision.manage" if data.target == "shortlisted" else "selection.finalize"
    )
    require_permission(db, actor, org, permission)
    cycle = db.scalar(
        select(SelectionCycle)
        .where(
            SelectionCycle.id == cycle_id,
            SelectionCycle.organization_id == org,
        )
        .with_for_update()
    )
    application = db.scalar(
        select(Application)
        .where(
            Application.id == application_id,
            Application.organization_id == org,
        )
        .with_for_update()
    )
    if not cycle or cycle.state != "active":
        raise AuthError("selection_cycle_not_active", 422)
    if not application or application.cycle_id != cycle.application_cycle_id:
        raise AuthError("application_not_reviewable", 422)
    if application.version != data.expected_application_version:
        raise AuthError("version_conflict", 409)
    aggregate = _application_aggregate(db, cycle.id, application.id)
    if aggregate is None:
        raise AuthError("completed_review_required", 422)
    terminal = {"selected", "waitlisted", "rejected"}
    if application.state == data.target:
        raise AuthError("decision_unchanged", 409)
    if application.state in terminal:
        if not data.override:
            raise AuthError("decision_override_required", 409)
        require_permission(db, actor, org, "selection.decision.override")
    elif data.override:
        require_permission(db, actor, org, "selection.decision.override")
    if data.target == "shortlisted":
        if application.state != "under_review" or data.override:
            raise AuthError("invalid_decision_transition", 409)
    elif application.state not in {"under_review", "shortlisted", "interview_scheduled", *terminal}:
        raise AuthError("invalid_decision_transition", 409)
    interview = db.scalar(
        select(Interview).where(
            Interview.selection_cycle_id == cycle.id,
            Interview.application_id == application.id,
        )
    )
    if application.state == "interview_scheduled" and (
        not interview or interview.status != "completed"
    ):
        raise AuthError("interview_not_completed", 422)
    previous = application.state
    _transition_application(
        db,
        application,
        actor,
        data.target,
        "selection_override" if data.override else "selection_decision",
    )
    decision = SelectionDecision(
        organization_id=org,
        selection_cycle_id=cycle.id,
        application_id=application.id,
        actor_user_id=actor.id,
        from_state=previous,
        to_state=data.target,
        reason=data.reason,
        is_override=data.override,
        aggregate_score_snapshot=aggregate,
        interview_score_snapshot=(
            interview.average_score if interview and interview.status == "completed" else None
        ),
        application_version=application.version,
    )
    db.add(decision)
    db.flush()
    _audit(
        db,
        actor,
        org,
        decision.id,
        "selection.decision.overridden" if data.override else "selection.decision.recorded",
        request_id,
        application.version,
        "application_state,decision",
        data.reason,
    )
    _commit(db)
    db.refresh(decision)
    return _decision_view(db, decision)
