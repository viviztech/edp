import base64
import secrets
from dataclasses import dataclass
from datetime import timedelta
from io import BytesIO
from typing import cast
from uuid import UUID

import qrcode
import qrcode.image.svg
from sqlalchemy import false, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.attendance.models import (
    AttendanceCorrection,
    AttendancePolicy,
    AttendanceRecord,
    AttendanceWindow,
)
from app.modules.attendance.schemas import (
    AttendanceSummary,
    CheckInCommand,
    CorrectionCommand,
    LearnerAttendanceView,
    LearnerSessionAttendance,
    ManualMark,
    MyAttendanceView,
    ParticipantAttendanceView,
    PolicyUpdate,
    PolicyView,
    RecordView,
    SessionAttendanceView,
    StaffAttendanceWorkspace,
    WindowClose,
    WindowCreate,
    WindowCreatedView,
    WindowView,
)
from app.modules.identity.models import AuditLog, Person, Role, RolePermission, User, UserRole, now
from app.modules.identity.security import AuthError, digest
from app.modules.identity.service import require_permission
from app.modules.programs.models import (
    Cohort,
    Enrollment,
    Participant,
    ProgramSession,
    ProgramStaffAssignment,
)
from app.modules.programs.schemas import SessionState

GLOBAL_ROLES = {"Super Admin", "Program Director", "Program Manager"}
DEFAULT_THRESHOLD = 75


@dataclass(frozen=True)
class AttendanceScope:
    center_ids: frozenset[UUID]
    cohort_ids: frozenset[UUID]


def _audit(
    db: Session,
    actor: User,
    org: UUID,
    resource: UUID,
    action: str,
    request_id: str,
    version: int,
    changed_fields: str,
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
            changed_fields=changed_fields,
            reason=reason,
        )
    )


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("conflict", 409) from exc


def _scope(db: Session, org: UUID, actor: User, permission: str) -> AttendanceScope | None:
    require_permission(db, actor, org, permission)
    global_role = db.scalar(
        select(UserRole.id)
        .join(Role, Role.id == UserRole.role_id)
        .join(RolePermission, RolePermission.role_id == Role.id)
        .where(
            UserRole.user_id == actor.id,
            UserRole.organization_id == org,
            Role.name.in_(GLOBAL_ROLES),
            RolePermission.permission_code == permission,
        )
        .limit(1)
    )
    if global_role:
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
        raise AuthError("staff_assignment_required", 403)
    return AttendanceScope(
        frozenset(item.center_id for item in assignments),
        frozenset(item.cohort_id for item in assignments if item.cohort_id),
    )


def _cohort(db: Session, org: UUID, cohort_id: UUID) -> Cohort:
    item = db.scalar(select(Cohort).where(Cohort.id == cohort_id, Cohort.organization_id == org))
    if not item:
        raise AuthError("not_found", 404)
    return item


def _require_cohort_scope(cohort: Cohort, scope: AttendanceScope | None) -> None:
    if scope is None:
        return
    if cohort.id not in scope.cohort_ids and cohort.center_id not in scope.center_ids:
        raise AuthError("forbidden", 403)


def _session(db: Session, org: UUID, session_id: UUID, lock: bool = False) -> ProgramSession:
    query = select(ProgramSession).where(
        ProgramSession.id == session_id, ProgramSession.organization_id == org
    )
    item = db.scalar(query.with_for_update() if lock else query)
    if not item:
        raise AuthError("not_found", 404)
    return item


def policy_view(item: AttendancePolicy) -> PolicyView:
    return PolicyView.model_validate(item, from_attributes=True)


def window_view(item: AttendanceWindow) -> WindowView:
    return WindowView.model_validate(item, from_attributes=True)


def record_view(item: AttendanceRecord) -> RecordView:
    return RecordView.model_validate(item, from_attributes=True)


def update_policy(
    db: Session,
    org: UUID,
    actor: User,
    data: PolicyUpdate,
    request_id: str,
) -> PolicyView:
    scope = _scope(db, org, actor, "attendance.manage")
    cohort = _cohort(db, org, data.cohort_id)
    _require_cohort_scope(cohort, scope)
    item = db.scalar(
        select(AttendancePolicy)
        .where(AttendancePolicy.cohort_id == cohort.id, AttendancePolicy.organization_id == org)
        .with_for_update()
    )
    values = data.model_dump(exclude={"expected_version", "reason", "cohort_id"})
    if item is None:
        if data.expected_version is not None:
            raise AuthError("version_conflict", 409)
        item = AttendancePolicy(organization_id=org, cohort_id=cohort.id, **values)
        db.add(item)
        db.flush()
        action = "attendance.policy.created"
    else:
        if data.expected_version != item.version:
            raise AuthError("version_conflict", 409)
        for key, value in values.items():
            setattr(item, key, value)
        item.version += 1
        item.updated_at = now()
        action = "attendance.policy.updated"
    _audit(
        db,
        actor,
        org,
        item.id,
        action,
        request_id,
        item.version,
        "threshold_percent,late_after_minutes,opens_before_minutes,closes_after_minutes",
        data.reason,
    )
    _commit(db)
    return policy_view(item)


def create_window(
    db: Session,
    org: UUID,
    actor: User,
    data: WindowCreate,
    request_id: str,
) -> WindowCreatedView:
    scope = _scope(db, org, actor, "attendance.manage")
    session = _session(db, org, data.session_id, True)
    cohort = _cohort(db, org, session.cohort_id)
    _require_cohort_scope(cohort, scope)
    if session.status != "scheduled":
        raise AuthError("session_not_scheduled", 409)
    policy = db.scalar(
        select(AttendancePolicy).where(
            AttendancePolicy.organization_id == org, AttendancePolicy.cohort_id == cohort.id
        )
    )
    if not policy:
        raise AuthError("attendance_policy_required", 409)
    if db.scalar(
        select(AttendanceWindow.id).where(
            AttendanceWindow.session_id == session.id, AttendanceWindow.state == "active"
        )
    ):
        raise AuthError("attendance_window_active", 409)
    raw = secrets.token_urlsafe(32)
    item = AttendanceWindow(
        organization_id=org,
        session_id=session.id,
        token_digest=digest(raw),
        opens_at=session.starts_at - timedelta(minutes=policy.opens_before_minutes),
        closes_at=session.starts_at + timedelta(minutes=policy.closes_after_minutes),
        created_by_user_id=actor.id,
    )
    db.add(item)
    db.flush()
    _audit(
        db,
        actor,
        org,
        item.id,
        "attendance.window.created",
        request_id,
        1,
        "session_id,opens_at,closes_at,state",
        data.reason,
    )
    _commit(db)
    image = qrcode.make(f"edp-attendance:{raw}", image_factory=qrcode.image.svg.SvgPathImage)
    output = BytesIO()
    image.save(output)
    qr_svg_data_url = "data:image/svg+xml;base64," + base64.b64encode(output.getvalue()).decode(
        "ascii"
    )
    return WindowCreatedView(
        **window_view(item).model_dump(),
        check_in_token=raw,
        qr_svg_data_url=qr_svg_data_url,
    )


def close_window(
    db: Session,
    org: UUID,
    window_id: UUID,
    actor: User,
    data: WindowClose,
    request_id: str,
) -> WindowView:
    scope = _scope(db, org, actor, "attendance.manage")
    item = db.scalar(
        select(AttendanceWindow)
        .where(AttendanceWindow.id == window_id, AttendanceWindow.organization_id == org)
        .with_for_update()
    )
    if not item:
        raise AuthError("not_found", 404)
    session = _session(db, org, item.session_id)
    _require_cohort_scope(_cohort(db, org, session.cohort_id), scope)
    if item.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    if item.state != "active":
        raise AuthError("attendance_window_closed", 409)
    item.state = "closed"
    item.closed_at = now()
    item.version += 1
    item.updated_at = now()
    _audit(
        db,
        actor,
        org,
        item.id,
        "attendance.window.closed",
        request_id,
        item.version,
        "state,closed_at",
        data.reason,
    )
    _commit(db)
    return window_view(item)


def _validate_enrollment(
    db: Session, org: UUID, session: ProgramSession, enrollment_id: UUID
) -> Enrollment:
    enrollment = db.scalar(
        select(Enrollment).where(
            Enrollment.id == enrollment_id,
            Enrollment.organization_id == org,
            Enrollment.cohort_id == session.cohort_id,
            Enrollment.status.in_(("active", "completed")),
        )
    )
    if not enrollment:
        raise AuthError("enrollment_not_eligible", 422)
    return enrollment


def manual_mark(
    db: Session,
    org: UUID,
    session_id: UUID,
    actor: User,
    data: ManualMark,
    request_id: str,
) -> RecordView:
    scope = _scope(db, org, actor, "attendance.manage")
    session = _session(db, org, session_id)
    _require_cohort_scope(_cohort(db, org, session.cohort_id), scope)
    if session.status == "cancelled":
        raise AuthError("session_cancelled", 409)
    _validate_enrollment(db, org, session, data.enrollment_id)
    if db.scalar(
        select(AttendanceRecord.id).where(
            AttendanceRecord.session_id == session.id,
            AttendanceRecord.enrollment_id == data.enrollment_id,
        )
    ):
        raise AuthError("attendance_already_marked", 409)
    item = AttendanceRecord(
        organization_id=org,
        session_id=session.id,
        enrollment_id=data.enrollment_id,
        status=data.status,
        source="manual",
        marked_by_user_id=actor.id,
    )
    db.add(item)
    db.flush()
    _audit(
        db,
        actor,
        org,
        item.id,
        "attendance.marked",
        request_id,
        1,
        "session_id,enrollment_id,status,source",
        data.reason,
    )
    _commit(db)
    return record_view(item)


def correct_record(
    db: Session,
    org: UUID,
    record_id: UUID,
    actor: User,
    data: CorrectionCommand,
    request_id: str,
) -> RecordView:
    scope = _scope(db, org, actor, "attendance.manage")
    item = db.scalar(
        select(AttendanceRecord)
        .where(AttendanceRecord.id == record_id, AttendanceRecord.organization_id == org)
        .with_for_update()
    )
    if not item:
        raise AuthError("not_found", 404)
    session = _session(db, org, item.session_id)
    _require_cohort_scope(_cohort(db, org, session.cohort_id), scope)
    if item.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    if item.status == data.status:
        raise AuthError("attendance_unchanged", 422)
    previous = item.status
    item.status = data.status
    item.marked_by_user_id = actor.id
    item.marked_at = now()
    item.version += 1
    item.updated_at = now()
    db.add(
        AttendanceCorrection(
            organization_id=org,
            attendance_record_id=item.id,
            actor_user_id=actor.id,
            from_status=previous,
            to_status=data.status,
            record_version=item.version,
            reason=data.reason,
        )
    )
    _audit(
        db,
        actor,
        org,
        item.id,
        "attendance.corrected",
        request_id,
        item.version,
        "status,marked_by_user_id,marked_at",
        data.reason,
    )
    _commit(db)
    return record_view(item)


def _actor_enrollment(db: Session, org: UUID, actor: User, cohort_id: UUID) -> Enrollment:
    enrollment = db.scalar(
        select(Enrollment)
        .join(Participant, Participant.id == Enrollment.participant_id)
        .where(
            Enrollment.organization_id == org,
            Enrollment.cohort_id == cohort_id,
            Enrollment.status == "active",
            Participant.person_id == actor.person_id,
        )
    )
    if not enrollment:
        raise AuthError("enrollment_not_eligible", 403)
    return enrollment


def check_in(
    db: Session,
    org: UUID,
    actor: User,
    data: CheckInCommand,
    request_id: str,
) -> RecordView:
    require_permission(db, actor, org, "participant.self")
    current = now()
    window = db.scalar(
        select(AttendanceWindow)
        .where(
            AttendanceWindow.organization_id == org,
            AttendanceWindow.token_digest == digest(data.token),
        )
        .with_for_update()
    )
    if not window:
        raise AuthError("invalid_check_in", 404)
    if window.state != "active" or current < window.opens_at or current > window.closes_at:
        raise AuthError("check_in_window_closed", 409)
    session = _session(db, org, window.session_id)
    if session.status != "scheduled":
        raise AuthError("session_not_scheduled", 409)
    enrollment = _actor_enrollment(db, org, actor, session.cohort_id)
    if db.scalar(
        select(AttendanceRecord.id).where(
            AttendanceRecord.session_id == session.id,
            AttendanceRecord.enrollment_id == enrollment.id,
        )
    ):
        raise AuthError("attendance_already_marked", 409)
    policy = db.scalar(
        select(AttendancePolicy).where(
            AttendancePolicy.organization_id == org,
            AttendancePolicy.cohort_id == session.cohort_id,
        )
    )
    if not policy:
        raise AuthError("attendance_policy_required", 409)
    status = (
        "late"
        if current > session.starts_at + timedelta(minutes=policy.late_after_minutes)
        else "present"
    )
    item = AttendanceRecord(
        organization_id=org,
        session_id=session.id,
        enrollment_id=enrollment.id,
        status=status,
        source="qr",
        marked_by_user_id=actor.id,
        marked_at=current,
    )
    db.add(item)
    db.flush()
    _audit(
        db,
        actor,
        org,
        item.id,
        "attendance.checked_in",
        request_id,
        1,
        "session_id,enrollment_id,status,source",
    )
    _commit(db)
    return record_view(item)


def _summary(
    sessions: list[ProgramSession],
    records: dict[UUID, AttendanceRecord],
    threshold: int,
) -> AttendanceSummary:
    current = now()
    countable = [
        item
        for item in sessions
        if item.status != "cancelled" and (item.status == "completed" or item.starts_at <= current)
    ]
    excused = sum(
        1 for item in countable if records.get(item.id) and records[item.id].status == "excused"
    )
    required = max(0, len(countable) - excused)
    attended = sum(
        1
        for item in countable
        if records.get(item.id) and records[item.id].status in {"present", "late"}
    )
    percent = round(attended * 100 / required) if required else 100
    return AttendanceSummary(
        attended=attended,
        required=required,
        excused=excused,
        percent=percent,
        threshold_percent=threshold,
        low_attendance=required > 0 and percent < threshold,
    )


def staff_workspace(db: Session, org: UUID, actor: User) -> StaffAttendanceWorkspace:
    scope = _scope(db, org, actor, "attendance.view")
    cohorts = list(db.scalars(select(Cohort).where(Cohort.organization_id == org)))
    allowed = {
        item.id
        for item in cohorts
        if scope is None or item.id in scope.cohort_ids or item.center_id in scope.center_ids
    }
    sessions = list(
        db.scalars(
            select(ProgramSession)
            .where(
                ProgramSession.organization_id == org,
                ProgramSession.cohort_id.in_(allowed) if allowed else false(),
            )
            .order_by(ProgramSession.starts_at, ProgramSession.id)
        )
    )
    policies = {
        item.cohort_id: item
        for item in db.scalars(
            select(AttendancePolicy).where(
                AttendancePolicy.organization_id == org,
                AttendancePolicy.cohort_id.in_(allowed) if allowed else false(),
            )
        )
    }
    session_ids = [item.id for item in sessions]
    windows = {
        item.session_id: item
        for item in db.scalars(
            select(AttendanceWindow).where(
                AttendanceWindow.organization_id == org,
                AttendanceWindow.session_id.in_(session_ids) if session_ids else false(),
                AttendanceWindow.state == "active",
            )
        )
    }
    enrollments = list(
        db.scalars(
            select(Enrollment).where(
                Enrollment.organization_id == org,
                Enrollment.cohort_id.in_(allowed) if allowed else false(),
                Enrollment.status.in_(("active", "completed")),
            )
        )
    )
    participant_ids = [item.participant_id for item in enrollments]
    names = {
        participant_id: display_name
        for participant_id, display_name in db.execute(
            select(Participant.id, Person.display_name)
            .join(Person, Person.id == Participant.person_id)
            .where(Participant.id.in_(participant_ids) if participant_ids else false())
        )
    }
    records = {
        (item.session_id, item.enrollment_id): item
        for item in db.scalars(
            select(AttendanceRecord).where(
                AttendanceRecord.organization_id == org,
                AttendanceRecord.session_id.in_(session_ids) if session_ids else false(),
            )
        )
    }
    by_cohort: dict[UUID, list[Enrollment]] = {}
    for enrollment in enrollments:
        by_cohort.setdefault(enrollment.cohort_id, []).append(enrollment)
    return StaffAttendanceWorkspace(
        sessions=[
            SessionAttendanceView(
                session_id=session.id,
                cohort_id=session.cohort_id,
                title_en=session.title_en,
                title_ta=session.title_ta,
                starts_at=session.starts_at,
                ends_at=session.ends_at,
                session_status=cast(SessionState, session.status),
                policy=policy_view(policies[session.cohort_id])
                if session.cohort_id in policies
                else None,
                window=window_view(windows[session.id]) if session.id in windows else None,
                participants=[
                    ParticipantAttendanceView(
                        enrollment_id=enrollment.id,
                        participant_id=enrollment.participant_id,
                        display_name=names[enrollment.participant_id],
                        record=record_view(records[(session.id, enrollment.id)])
                        if (session.id, enrollment.id) in records
                        else None,
                    )
                    for enrollment in by_cohort.get(session.cohort_id, [])
                ],
            )
            for session in sessions
        ]
    )


def my_attendance(db: Session, org: UUID, actor: User) -> MyAttendanceView:
    require_permission(db, actor, org, "participant.self")
    participant = db.scalar(
        select(Participant).where(
            Participant.organization_id == org, Participant.person_id == actor.person_id
        )
    )
    if not participant:
        raise AuthError("not_found", 404)
    enrollments = list(
        db.scalars(
            select(Enrollment).where(
                Enrollment.organization_id == org,
                Enrollment.participant_id == participant.id,
            )
        )
    )
    result: list[LearnerAttendanceView] = []
    for enrollment in enrollments:
        cohort = _cohort(db, org, enrollment.cohort_id)
        sessions = list(
            db.scalars(
                select(ProgramSession)
                .where(
                    ProgramSession.organization_id == org,
                    ProgramSession.cohort_id == cohort.id,
                )
                .order_by(ProgramSession.starts_at, ProgramSession.id)
            )
        )
        records = {
            item.session_id: item
            for item in db.scalars(
                select(AttendanceRecord).where(
                    AttendanceRecord.organization_id == org,
                    AttendanceRecord.enrollment_id == enrollment.id,
                )
            )
        }
        policy = db.scalar(
            select(AttendancePolicy).where(
                AttendancePolicy.organization_id == org,
                AttendancePolicy.cohort_id == cohort.id,
            )
        )
        threshold = policy.threshold_percent if policy else DEFAULT_THRESHOLD
        result.append(
            LearnerAttendanceView(
                enrollment_id=enrollment.id,
                cohort_id=cohort.id,
                cohort_name_en=cohort.name_en,
                cohort_name_ta=cohort.name_ta,
                summary=_summary(sessions, records, threshold),
                sessions=[
                    LearnerSessionAttendance(
                        session_id=session.id,
                        title_en=session.title_en,
                        title_ta=session.title_ta,
                        starts_at=session.starts_at,
                        ends_at=session.ends_at,
                        session_status=cast(SessionState, session.status),
                        record=record_view(records[session.id]) if session.id in records else None,
                    )
                    for session in sessions
                ],
            )
        )
    return MyAttendanceView(enrollments=result)
