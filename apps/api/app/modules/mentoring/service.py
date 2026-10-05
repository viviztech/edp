from typing import cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.identity.models import AuditLog, Person, Role, User, UserRole, now
from app.modules.identity.security import AuthError
from app.modules.identity.service import require_permission
from app.modules.mentoring.models import (
    ActionItem,
    FollowUp,
    Goal,
    MentorAssignment,
    MentorAvailability,
    MentorExpertise,
    MentoringFeedback,
    MentoringNote,
    MentoringSession,
    MentorProfile,
)
from app.modules.mentoring.schemas import (
    ActionCreate,
    ActionView,
    AssignmentCreate,
    AssignmentEnd,
    AssignmentState,
    AvailabilityCreate,
    AvailabilityView,
    EnrollmentCandidateView,
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
    MentorCandidateView,
    MyMentoring,
    NoteCreate,
    NoteView,
    ProfileCreate,
    ProfileState,
    ProfileView,
    SessionCreate,
    SessionState,
    SessionView,
    StateCommand,
    Workspace,
)
from app.modules.programs.models import Enrollment, Participant

ADMIN_ROLES = {"Super Admin", "Program Director", "Program Manager"}


def audit(
    db: Session,
    actor: User,
    org: UUID,
    resource: UUID,
    action: str,
    request_id: str,
    changed: str,
    reason: str | None = None,
    version: int | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=resource,
            action=action,
            request_id=request_id,
            changed_fields=changed,
            reason=reason,
            resource_version=version,
        )
    )


def is_admin(db: Session, actor: User, org: UUID) -> bool:
    return bool(
        db.scalar(
            select(UserRole.id)
            .join(Role)
            .where(
                UserRole.user_id == actor.id,
                UserRole.organization_id == org,
                Role.name.in_(ADMIN_ROLES),
            )
            .limit(1)
        )
    )


def profile_name(db: Session, profile: MentorProfile) -> str:
    return (
        db.scalar(
            select(Person.display_name)
            .join(User, User.person_id == Person.id)
            .where(User.id == profile.user_id)
        )
        or "Mentor"
    )


def assignment_view(db: Session, row: MentorAssignment) -> MentorAssignmentView:
    enrollment = db.get(Enrollment, row.enrollment_id)
    profile = db.get(MentorProfile, row.mentor_profile_id)
    if not enrollment or not profile:
        raise AuthError("not_found", 404)
    participant = db.get(Participant, enrollment.participant_id)
    person = db.get(Person, participant.person_id) if participant else None
    return MentorAssignmentView(
        id=row.id,
        mentor_profile_id=row.mentor_profile_id,
        mentor_name=profile_name(db, profile),
        enrollment_id=row.enrollment_id,
        participant_id=enrollment.participant_id,
        participant_name=person.display_name if person else "Participant",
        program_id=enrollment.program_id,
        starts_on=row.starts_on,
        ends_on=row.ends_on,
        state=cast(AssignmentState, row.state),
        version=row.version,
    )


def profile_view(db: Session, row: MentorProfile) -> ProfileView:
    return ProfileView(
        id=row.id,
        user_id=row.user_id,
        display_name=profile_name(db, row),
        headline=row.headline,
        biography=row.biography,
        state=cast(ProfileState, row.state),
        version=row.version,
    )


def session_view(row: MentoringSession) -> SessionView:
    return SessionView(
        id=row.id,
        assignment_id=row.assignment_id,
        starts_at=row.starts_at,
        ends_at=row.ends_at,
        mode=row.mode,
        location_or_link=row.location_or_link,
        topic=row.topic,
        status=cast(SessionState, row.status),
        version=row.version,
    )


def note_view(row: MentoringNote) -> NoteView:
    return NoteView(
        id=row.id,
        assignment_id=row.assignment_id,
        session_id=row.session_id,
        visibility=row.visibility,
        body=row.body,
        created_at=row.created_at,
    )


def goal_view(row: Goal) -> GoalView:
    return GoalView(
        id=row.id,
        assignment_id=row.assignment_id,
        title=row.title,
        description=row.description,
        target_date=row.target_date,
        progress_percent=row.progress_percent,
        state=row.state,
        version=row.version,
    )


def action_view(row: ActionItem) -> ActionView:
    return ActionView(
        id=row.id,
        assignment_id=row.assignment_id,
        goal_id=row.goal_id,
        title=row.title,
        due_at=row.due_at,
        state=row.state,
        version=row.version,
    )


def follow_up_view(row: FollowUp) -> FollowUpView:
    return FollowUpView(
        id=row.id,
        assignment_id=row.assignment_id,
        session_id=row.session_id,
        purpose=row.purpose,
        due_at=row.due_at,
        state=row.state,
        overdue=row.state == "scheduled" and row.due_at < now(),
        version=row.version,
    )


def assignment_for_actor(
    db: Session, org: UUID, actor: User, assignment_id: UUID, *, manage: bool = True
) -> MentorAssignment:
    require_permission(db, actor, org, "mentoring.manage" if manage else "mentoring.view")
    row = db.scalar(
        select(MentorAssignment).where(
            MentorAssignment.id == assignment_id, MentorAssignment.organization_id == org
        )
    )
    if not row:
        raise AuthError("not_found", 404)
    if not is_admin(db, actor, org):
        profile = db.scalar(
            select(MentorProfile).where(
                MentorProfile.id == row.mentor_profile_id, MentorProfile.user_id == actor.id
            )
        )
        if not profile:
            raise AuthError("forbidden", 403)
    return row


def create_profile(
    db: Session, org: UUID, actor: User, data: ProfileCreate, request_id: str
) -> ProfileView:
    require_permission(db, actor, org, "mentoring.admin")
    eligible = db.scalar(
        select(UserRole.id)
        .join(Role)
        .where(
            UserRole.user_id == data.user_id,
            UserRole.organization_id == org,
            Role.name == "Mentor",
        )
    )
    if not eligible:
        raise AuthError("not_found", 404)
    row = MentorProfile(
        organization_id=org,
        user_id=data.user_id,
        headline=data.headline.strip(),
        biography=data.biography.strip() if data.biography else None,
    )
    db.add(row)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("conflict", 409) from exc
    audit(
        db,
        actor,
        org,
        row.id,
        "mentoring.profile.created",
        request_id,
        "user_id,headline,biography",
        version=1,
    )
    db.commit()
    return profile_view(db, row)


def add_expertise(
    db: Session, org: UUID, actor: User, data: ExpertiseCreate, request_id: str
) -> ExpertiseView:
    require_permission(db, actor, org, "mentoring.admin")
    if not db.scalar(
        select(MentorProfile.id).where(
            MentorProfile.id == data.mentor_profile_id, MentorProfile.organization_id == org
        )
    ):
        raise AuthError("not_found", 404)
    row = MentorExpertise(organization_id=org, **data.model_dump())
    db.add(row)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("conflict", 409) from exc
    audit(
        db,
        actor,
        org,
        row.id,
        "mentoring.expertise.created",
        request_id,
        "mentor_profile_id,code,name_en,name_ta",
    )
    db.commit()
    return ExpertiseView(id=row.id, **data.model_dump())


def add_availability(
    db: Session, org: UUID, actor: User, data: AvailabilityCreate, request_id: str
) -> AvailabilityView:
    require_permission(db, actor, org, "mentoring.admin")
    if not db.scalar(
        select(MentorProfile.id).where(
            MentorProfile.id == data.mentor_profile_id, MentorProfile.organization_id == org
        )
    ):
        raise AuthError("not_found", 404)
    overlap = db.scalar(
        select(MentorAvailability.id).where(
            MentorAvailability.mentor_profile_id == data.mentor_profile_id,
            MentorAvailability.weekday == data.weekday,
            MentorAvailability.starts_at < data.ends_at,
            MentorAvailability.ends_at > data.starts_at,
        )
    )
    if overlap:
        raise AuthError("schedule_conflict", 409)
    row = MentorAvailability(organization_id=org, **data.model_dump())
    db.add(row)
    db.flush()
    audit(
        db,
        actor,
        org,
        row.id,
        "mentoring.availability.created",
        request_id,
        "weekday,starts_at,ends_at,timezone",
    )
    db.commit()
    return AvailabilityView(id=row.id, **data.model_dump())


def create_assignment(
    db: Session, org: UUID, actor: User, data: AssignmentCreate, request_id: str
) -> MentorAssignmentView:
    require_permission(db, actor, org, "mentoring.admin")
    profile = db.scalar(
        select(MentorProfile).where(
            MentorProfile.id == data.mentor_profile_id,
            MentorProfile.organization_id == org,
            MentorProfile.state == "active",
        )
    )
    enrollment = db.scalar(
        select(Enrollment).where(
            Enrollment.id == data.enrollment_id,
            Enrollment.organization_id == org,
            Enrollment.status == "active",
        )
    )
    if not profile or not enrollment:
        raise AuthError("not_found", 404)
    row = MentorAssignment(
        organization_id=org,
        mentor_profile_id=data.mentor_profile_id,
        enrollment_id=data.enrollment_id,
        starts_on=data.starts_on,
        ends_on=data.ends_on,
        assigned_by_user_id=actor.id,
    )
    db.add(row)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("active_assignment_exists", 409) from exc
    audit(
        db,
        actor,
        org,
        row.id,
        "mentoring.assignment.created",
        request_id,
        "mentor_profile_id,enrollment_id,starts_on,ends_on",
        data.reason,
        1,
    )
    db.commit()
    return assignment_view(db, row)


def end_assignment(
    db: Session, org: UUID, assignment_id: UUID, actor: User, data: AssignmentEnd, request_id: str
) -> MentorAssignmentView:
    require_permission(db, actor, org, "mentoring.admin")
    row = db.scalar(
        select(MentorAssignment)
        .where(MentorAssignment.id == assignment_id, MentorAssignment.organization_id == org)
        .with_for_update()
    )
    if not row:
        raise AuthError("not_found", 404)
    if row.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    if row.state != "active":
        raise AuthError("invalid_transition", 409)
    row.state = "ended"
    row.ended_at = now()
    row.version += 1
    audit(
        db,
        actor,
        org,
        row.id,
        "mentoring.assignment.ended",
        request_id,
        "state,ended_at",
        data.reason,
        row.version,
    )
    db.commit()
    return assignment_view(db, row)


def create_session(
    db: Session, org: UUID, actor: User, data: SessionCreate, request_id: str
) -> SessionView:
    assignment = assignment_for_actor(db, org, actor, data.assignment_id)
    if (
        assignment.state != "active"
        or data.starts_at.date() < assignment.starts_on
        or (assignment.ends_on and data.starts_at.date() > assignment.ends_on)
    ):
        raise AuthError("outside_assignment", 409)
    assignment_ids = select(MentorAssignment.id).where(
        MentorAssignment.mentor_profile_id == assignment.mentor_profile_id
    )
    conflict = db.scalar(
        select(MentoringSession.id).where(
            MentoringSession.assignment_id.in_(assignment_ids),
            MentoringSession.status == "scheduled",
            MentoringSession.starts_at < data.ends_at,
            MentoringSession.ends_at > data.starts_at,
        )
    )
    if conflict:
        raise AuthError("schedule_conflict", 409)
    row = MentoringSession(organization_id=org, **data.model_dump())
    db.add(row)
    db.flush()
    audit(
        db,
        actor,
        org,
        row.id,
        "mentoring.session.scheduled",
        request_id,
        "assignment_id,starts_at,ends_at,mode,topic",
        version=1,
    )
    db.commit()
    return session_view(row)


def transition_session(
    db: Session, org: UUID, session_id: UUID, actor: User, data: StateCommand, request_id: str
) -> SessionView:
    row = db.scalar(
        select(MentoringSession)
        .where(MentoringSession.id == session_id, MentoringSession.organization_id == org)
        .with_for_update()
    )
    if not row:
        raise AuthError("not_found", 404)
    assignment_for_actor(db, org, actor, row.assignment_id)
    if row.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    if row.status != "scheduled" or data.target not in {"completed", "cancelled"}:
        raise AuthError("invalid_transition", 409)
    row.status = data.target
    row.version += 1
    if data.target == "completed":
        row.completed_at = now()
    else:
        row.cancelled_at = now()
    audit(
        db,
        actor,
        org,
        row.id,
        f"mentoring.session.{data.target}",
        request_id,
        f"status,{data.target}_at",
        data.reason,
        row.version,
    )
    db.commit()
    return session_view(row)


def create_note(db: Session, org: UUID, actor: User, data: NoteCreate, request_id: str) -> NoteView:
    assignment_for_actor(db, org, actor, data.assignment_id)
    if data.session_id and not db.scalar(
        select(MentoringSession.id).where(
            MentoringSession.id == data.session_id,
            MentoringSession.assignment_id == data.assignment_id,
        )
    ):
        raise AuthError("not_found", 404)
    row = MentoringNote(organization_id=org, author_user_id=actor.id, **data.model_dump())
    db.add(row)
    db.flush()
    audit(
        db,
        actor,
        org,
        row.id,
        "mentoring.note.created",
        request_id,
        "assignment_id,session_id,visibility",
    )
    db.commit()
    return note_view(row)


def create_goal(db: Session, org: UUID, actor: User, data: GoalCreate, request_id: str) -> GoalView:
    assignment_for_actor(db, org, actor, data.assignment_id)
    row = Goal(organization_id=org, **data.model_dump())
    db.add(row)
    db.flush()
    audit(
        db,
        actor,
        org,
        row.id,
        "mentoring.goal.created",
        request_id,
        "assignment_id,title,target_date",
        version=1,
    )
    db.commit()
    return goal_view(row)


def update_goal(
    db: Session, org: UUID, goal_id: UUID, actor: User, data: GoalUpdate, request_id: str
) -> GoalView:
    row = db.scalar(
        select(Goal).where(Goal.id == goal_id, Goal.organization_id == org).with_for_update()
    )
    if not row:
        raise AuthError("not_found", 404)
    assignment_for_actor(db, org, actor, row.assignment_id)
    if row.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    if row.state != "active" or data.target not in {"active", "completed", "cancelled"}:
        raise AuthError("invalid_transition", 409)
    row.progress_percent = 100 if data.target == "completed" else data.progress_percent
    row.state = data.target
    row.completed_at = now() if data.target == "completed" else None
    row.version += 1
    audit(
        db,
        actor,
        org,
        row.id,
        "mentoring.goal.updated",
        request_id,
        "progress_percent,state,completed_at",
        data.reason,
        row.version,
    )
    db.commit()
    return goal_view(row)


def create_action(
    db: Session, org: UUID, actor: User, data: ActionCreate, request_id: str
) -> ActionView:
    assignment_for_actor(db, org, actor, data.assignment_id)
    if data.goal_id and not db.scalar(
        select(Goal.id).where(Goal.id == data.goal_id, Goal.assignment_id == data.assignment_id)
    ):
        raise AuthError("not_found", 404)
    row = ActionItem(organization_id=org, **data.model_dump())
    db.add(row)
    db.flush()
    audit(
        db,
        actor,
        org,
        row.id,
        "mentoring.action.created",
        request_id,
        "assignment_id,goal_id,title,due_at",
        version=1,
    )
    db.commit()
    return action_view(row)


def transition_action(
    db: Session, org: UUID, action_id: UUID, actor: User, data: StateCommand, request_id: str
) -> ActionView:
    row = db.scalar(
        select(ActionItem)
        .where(ActionItem.id == action_id, ActionItem.organization_id == org)
        .with_for_update()
    )
    if not row:
        raise AuthError("not_found", 404)
    assignment_for_actor(db, org, actor, row.assignment_id)
    if row.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    if row.state != "open" or data.target not in {"completed", "cancelled"}:
        raise AuthError("invalid_transition", 409)
    row.state = data.target
    row.completed_at = now() if data.target == "completed" else None
    row.version += 1
    audit(
        db,
        actor,
        org,
        row.id,
        f"mentoring.action.{data.target}",
        request_id,
        "state,completed_at",
        data.reason,
        row.version,
    )
    db.commit()
    return action_view(row)


def create_follow_up(
    db: Session, org: UUID, actor: User, data: FollowUpCreate, request_id: str
) -> FollowUpView:
    assignment_for_actor(db, org, actor, data.assignment_id)
    if data.session_id and not db.scalar(
        select(MentoringSession.id).where(
            MentoringSession.id == data.session_id,
            MentoringSession.assignment_id == data.assignment_id,
        )
    ):
        raise AuthError("not_found", 404)
    row = FollowUp(organization_id=org, **data.model_dump())
    db.add(row)
    db.flush()
    audit(
        db,
        actor,
        org,
        row.id,
        "mentoring.follow_up.scheduled",
        request_id,
        "assignment_id,session_id,purpose,due_at",
        version=1,
    )
    db.commit()
    return follow_up_view(row)


def transition_follow_up(
    db: Session, org: UUID, follow_id: UUID, actor: User, data: StateCommand, request_id: str
) -> FollowUpView:
    row = db.scalar(
        select(FollowUp)
        .where(FollowUp.id == follow_id, FollowUp.organization_id == org)
        .with_for_update()
    )
    if not row:
        raise AuthError("not_found", 404)
    assignment_for_actor(db, org, actor, row.assignment_id)
    if row.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    if row.state != "scheduled" or data.target not in {"completed", "cancelled"}:
        raise AuthError("invalid_transition", 409)
    row.state = data.target
    row.completed_at = now() if data.target == "completed" else None
    row.version += 1
    audit(
        db,
        actor,
        org,
        row.id,
        f"mentoring.follow_up.{data.target}",
        request_id,
        "state,completed_at",
        data.reason,
        row.version,
    )
    db.commit()
    return follow_up_view(row)


def actor_assignment_ids(db: Session, org: UUID, actor: User) -> list[UUID]:
    query = select(MentorAssignment.id).where(MentorAssignment.organization_id == org)
    if not is_admin(db, actor, org):
        query = query.join(
            MentorProfile, MentorProfile.id == MentorAssignment.mentor_profile_id
        ).where(MentorProfile.user_id == actor.id)
    return list(db.scalars(query))


def workspace(db: Session, org: UUID, actor: User) -> Workspace:
    require_permission(db, actor, org, "mentoring.view")
    admin = is_admin(db, actor, org)
    ids = actor_assignment_ids(db, org, actor)
    profile_query = select(MentorProfile).where(MentorProfile.organization_id == org)
    if not admin:
        profile_query = profile_query.where(MentorProfile.user_id == actor.id)
    profiles = list(db.scalars(profile_query.order_by(MentorProfile.created_at)))
    expertise = (
        list(
            db.scalars(
                select(MentorExpertise).where(
                    MentorExpertise.mentor_profile_id.in_([p.id for p in profiles])
                )
            )
        )
        if profiles
        else []
    )
    availability = (
        list(
            db.scalars(
                select(MentorAvailability).where(
                    MentorAvailability.mentor_profile_id.in_([p.id for p in profiles])
                )
            )
        )
        if profiles
        else []
    )
    assignments = (
        list(
            db.scalars(
                select(MentorAssignment)
                .where(MentorAssignment.id.in_(ids))
                .order_by(MentorAssignment.created_at)
            )
        )
        if ids
        else []
    )
    sessions = (
        list(
            db.scalars(
                select(MentoringSession)
                .where(MentoringSession.assignment_id.in_(ids))
                .order_by(MentoringSession.starts_at)
            )
        )
        if ids
        else []
    )
    notes = (
        list(
            db.scalars(
                select(MentoringNote)
                .where(
                    MentoringNote.assignment_id.in_(ids), MentoringNote.author_user_id == actor.id
                )
                .order_by(MentoringNote.created_at)
            )
        )
        if ids
        else []
    )
    goals = list(db.scalars(select(Goal).where(Goal.assignment_id.in_(ids)))) if ids else []
    actions = (
        list(db.scalars(select(ActionItem).where(ActionItem.assignment_id.in_(ids)))) if ids else []
    )
    followups = (
        list(
            db.scalars(
                select(FollowUp).where(FollowUp.assignment_id.in_(ids)).order_by(FollowUp.due_at)
            )
        )
        if ids
        else []
    )
    count, avg = (
        db.execute(
            select(func.count(MentoringFeedback.id), func.avg(MentoringFeedback.rating))
            .join(MentoringSession, MentoringSession.id == MentoringFeedback.session_id)
            .where(MentoringSession.assignment_id.in_(ids))
        ).one()
        if ids
        else (0, None)
    )
    mentor_candidates: list[MentorCandidateView] = []
    enrollment_candidates: list[EnrollmentCandidateView] = []
    if admin:
        mentor_rows = db.execute(
            select(User.id, Person.display_name, MentorProfile.id)
            .join(Person, Person.id == User.person_id)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .outerjoin(
                MentorProfile,
                (MentorProfile.user_id == User.id) & (MentorProfile.organization_id == org),
            )
            .where(UserRole.organization_id == org, Role.name == "Mentor", User.status == "active")
            .order_by(Person.display_name)
        ).all()
        mentor_candidates = [
            MentorCandidateView(
                user_id=user_id, display_name=name, has_profile=profile_id is not None
            )
            for user_id, name, profile_id in mentor_rows
        ]
        enrollment_rows = db.execute(
            select(Enrollment.id, Person.display_name, Enrollment.program_id, MentorAssignment.id)
            .join(Participant, Participant.id == Enrollment.participant_id)
            .join(Person, Person.id == Participant.person_id)
            .outerjoin(
                MentorAssignment,
                (MentorAssignment.enrollment_id == Enrollment.id)
                & (MentorAssignment.state == "active"),
            )
            .where(Enrollment.organization_id == org, Enrollment.status == "active")
            .order_by(Person.display_name)
        ).all()
        enrollment_candidates = [
            EnrollmentCandidateView(
                enrollment_id=enrollment_id,
                participant_name=name,
                program_id=program_id,
                has_active_assignment=assignment_id is not None,
            )
            for enrollment_id, name, program_id, assignment_id in enrollment_rows
        ]
    return Workspace(
        mentor_candidates=mentor_candidates,
        enrollment_candidates=enrollment_candidates,
        profiles=[profile_view(db, p) for p in profiles],
        expertise=[
            ExpertiseView(
                id=x.id,
                mentor_profile_id=x.mentor_profile_id,
                code=x.code,
                name_en=x.name_en,
                name_ta=x.name_ta,
            )
            for x in expertise
        ],
        availability=[
            AvailabilityView(
                id=x.id,
                mentor_profile_id=x.mentor_profile_id,
                weekday=x.weekday,
                starts_at=x.starts_at,
                ends_at=x.ends_at,
                timezone=x.timezone,
            )
            for x in availability
        ],
        assignments=[assignment_view(db, x) for x in assignments],
        sessions=[session_view(x) for x in sessions],
        notes=[note_view(x) for x in notes],
        goals=[goal_view(x) for x in goals],
        action_items=[action_view(x) for x in actions],
        follow_ups=[follow_up_view(x) for x in followups],
        feedback_count=int(count),
        average_rating=round(float(avg), 2) if avg is not None else None,
    )


def participant_for_actor(db: Session, org: UUID, actor: User) -> Participant:
    require_permission(db, actor, org, "participant.self")
    row = db.scalar(
        select(Participant).where(
            Participant.organization_id == org, Participant.person_id == actor.person_id
        )
    )
    if not row:
        raise AuthError("not_found", 404)
    return row


def my_mentoring(db: Session, org: UUID, actor: User) -> MyMentoring:
    participant = participant_for_actor(db, org, actor)
    assignments = list(
        db.scalars(
            select(MentorAssignment)
            .join(Enrollment, Enrollment.id == MentorAssignment.enrollment_id)
            .where(
                MentorAssignment.organization_id == org, Enrollment.participant_id == participant.id
            )
            .order_by(MentorAssignment.created_at)
        )
    )
    ids = [x.id for x in assignments]
    sessions = (
        list(
            db.scalars(
                select(MentoringSession)
                .where(MentoringSession.assignment_id.in_(ids))
                .order_by(MentoringSession.starts_at)
            )
        )
        if ids
        else []
    )
    notes = (
        list(
            db.scalars(
                select(MentoringNote).where(
                    MentoringNote.assignment_id.in_(ids),
                    MentoringNote.visibility == "shared_with_participant",
                )
            )
        )
        if ids
        else []
    )
    goals = list(db.scalars(select(Goal).where(Goal.assignment_id.in_(ids)))) if ids else []
    actions = (
        list(db.scalars(select(ActionItem).where(ActionItem.assignment_id.in_(ids)))) if ids else []
    )
    followups = (
        list(db.scalars(select(FollowUp).where(FollowUp.assignment_id.in_(ids)))) if ids else []
    )
    feedback = list(
        db.scalars(
            select(MentoringFeedback).where(MentoringFeedback.participant_id == participant.id)
        )
    )
    return MyMentoring(
        assignments=[assignment_view(db, x) for x in assignments],
        sessions=[session_view(x) for x in sessions],
        notes=[note_view(x) for x in notes],
        goals=[goal_view(x) for x in goals],
        action_items=[action_view(x) for x in actions],
        follow_ups=[follow_up_view(x) for x in followups],
        feedback=[
            FeedbackView(
                id=x.id,
                session_id=x.session_id,
                rating=x.rating,
                comment=x.comment,
                created_at=x.created_at,
            )
            for x in feedback
        ],
    )


def create_feedback(
    db: Session, org: UUID, actor: User, data: FeedbackCreate, request_id: str
) -> FeedbackView:
    participant = participant_for_actor(db, org, actor)
    session = db.scalar(
        select(MentoringSession)
        .join(MentorAssignment, MentorAssignment.id == MentoringSession.assignment_id)
        .join(Enrollment, Enrollment.id == MentorAssignment.enrollment_id)
        .where(
            MentoringSession.id == data.session_id,
            MentoringSession.organization_id == org,
            MentoringSession.status == "completed",
            Enrollment.participant_id == participant.id,
        )
    )
    if not session:
        raise AuthError("not_found", 404)
    row = MentoringFeedback(organization_id=org, participant_id=participant.id, **data.model_dump())
    db.add(row)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("feedback_exists", 409) from exc
    audit(db, actor, org, row.id, "mentoring.feedback.created", request_id, "session_id,rating")
    db.commit()
    return FeedbackView(
        id=row.id,
        session_id=row.session_id,
        rating=row.rating,
        comment=row.comment,
        created_at=row.created_at,
    )
