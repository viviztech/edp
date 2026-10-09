from datetime import date, timedelta
from typing import Literal, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.businesses.models import (
    BusinessFollowUp,
    BusinessOutcomeSnapshot,
    BusinessProfile,
    BusinessProfileRevision,
    FollowUpPolicy,
)
from app.modules.businesses.schemas import (
    BusinessStage,
    CreateProfile,
    EnrollmentEntry,
    FollowUpView,
    MyBusinesses,
    OutcomeCreate,
    OutcomeView,
    PolicyUpdate,
    PolicyView,
    ProfileFields,
    ProfileView,
    RevisionView,
    StaffBusinessSummary,
    StaffDashboard,
    UpdateProfile,
)
from app.modules.identity.models import AuditLog, User, now
from app.modules.identity.security import AuthError
from app.modules.identity.service import require_permission
from app.modules.programs.models import Enrollment, Participant

DEFAULT_OFFSETS = [30, 90, 180, 365, 730]
PROFILE_FIELDS = tuple(ProfileFields.model_fields)


def owned_enrollment(db: Session, org: UUID, actor: User, enrollment_id: UUID) -> Enrollment:
    require_permission(db, actor, org, "participant.self")
    row = db.scalar(
        select(Enrollment)
        .join(Participant, Participant.id == Enrollment.participant_id)
        .where(
            Enrollment.id == enrollment_id,
            Enrollment.organization_id == org,
            Enrollment.status.in_(["active", "completed"]),
            Participant.organization_id == org,
            Participant.person_id == actor.person_id,
        )
    )
    if row is None:
        raise AuthError("not_found", 404)
    return row


def profile_view(db: Session, row: BusinessProfile) -> ProfileView:
    revisions = list(
        db.scalars(
            select(BusinessProfileRevision)
            .where(
                BusinessProfileRevision.profile_id == row.id,
                BusinessProfileRevision.organization_id == row.organization_id,
            )
            .order_by(BusinessProfileRevision.version.desc())
            .limit(20)
        )
    )
    followups = list(
        db.scalars(
            select(BusinessFollowUp)
            .where(
                BusinessFollowUp.profile_id == row.id,
                BusinessFollowUp.organization_id == row.organization_id,
            )
            .order_by(BusinessFollowUp.due_on)
            .limit(12)
        )
    )
    outcomes = (
        {
            item.follow_up_id: item
            for item in db.scalars(
                select(BusinessOutcomeSnapshot).where(
                    BusinessOutcomeSnapshot.organization_id == row.organization_id,
                    BusinessOutcomeSnapshot.follow_up_id.in_([item.id for item in followups]),
                )
            )
        }
        if followups
        else {}
    )
    fields = {key: getattr(row, key) for key in PROFILE_FIELDS}
    return ProfileView(
        **fields,
        id=row.id,
        enrollment_id=row.enrollment_id,
        version=row.version,
        created_at=row.created_at,
        updated_at=row.updated_at,
        revisions=[
            RevisionView(
                id=item.id, version=item.version, snapshot=item.snapshot, created_at=item.created_at
            )
            for item in revisions
        ],
        follow_ups=[
            FollowUpView(
                id=item.id,
                offset_days=item.offset_days,
                due_on=item.due_on,
            status=cast(Literal["pending", "completed"], item.status),
                outcome=OutcomeView(
                    id=outcomes[item.id].id,
                    created_at=outcomes[item.id].created_at,
                    **{key: getattr(outcomes[item.id], key) for key in OutcomeCreate.model_fields},
                )
                if item.id in outcomes
                else None,
            )
            for item in followups
        ],
    )


def mine(db: Session, org: UUID, actor: User) -> MyBusinesses:
    require_permission(db, actor, org, "participant.self")
    enrollments = list(
        db.scalars(
            select(Enrollment)
            .join(Participant, Participant.id == Enrollment.participant_id)
            .where(
                Enrollment.organization_id == org,
                Enrollment.status.in_(["active", "completed"]),
                Participant.organization_id == org,
                Participant.person_id == actor.person_id,
            )
            .order_by(Enrollment.enrolled_at.desc())
            .limit(100)
        )
    )
    profiles = (
        {
            item.enrollment_id: item
            for item in db.scalars(
                select(BusinessProfile).where(
                    BusinessProfile.organization_id == org,
                    BusinessProfile.enrollment_id.in_([item.id for item in enrollments]),
                )
            )
        }
        if enrollments
        else {}
    )
    return MyBusinesses(
        entries=[
            EnrollmentEntry(
                enrollment_id=item.id,
                program_id=item.program_id,
                profile=profile_view(db, profiles[item.id]) if item.id in profiles else None,
            )
            for item in enrollments
        ]
    )


def create_profile(
    db: Session, org: UUID, actor: User, data: CreateProfile, request_id: str
) -> ProfileView:
    owned_enrollment(db, org, actor, data.enrollment_id)
    fields = data.model_dump(exclude={"enrollment_id"}, mode="json")
    row = BusinessProfile(organization_id=org, enrollment_id=data.enrollment_id, **fields)
    db.add(row)
    try:
        db.flush()
        db.add(
            BusinessProfileRevision(
                organization_id=org,
                profile_id=row.id,
                version=1,
                snapshot=fields,
                author_user_id=actor.id,
            )
        )
        policy = db.scalar(select(FollowUpPolicy).where(FollowUpPolicy.organization_id == org))
        for offset in policy.day_offsets if policy else DEFAULT_OFFSETS:
            db.add(
                BusinessFollowUp(
                    organization_id=org,
                    profile_id=row.id,
                    offset_days=offset,
                    due_on=date.today() + timedelta(days=offset),
                )
            )
        db.add(
            AuditLog(
                actor_id=actor.id,
                organization_id=org,
                resource_id=row.id,
                action="business.profile_created",
                request_id=request_id,
                changed_fields="enrollment_id,profile",
                resource_version=1,
            )
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("profile_exists", 409) from exc
    return profile_view(db, row)


def update_profile(
    db: Session, org: UUID, actor: User, profile_id: UUID, data: UpdateProfile, request_id: str
) -> ProfileView:
    row = db.scalar(
        select(BusinessProfile)
        .where(
            BusinessProfile.id == profile_id,
            BusinessProfile.organization_id == org,
        )
        .with_for_update()
    )
    if row is None:
        raise AuthError("not_found", 404)
    owned_enrollment(db, org, actor, row.enrollment_id)
    if row.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    fields = data.model_dump(exclude={"expected_version"}, mode="json")
    for key, value in fields.items():
        setattr(row, key, value)
    row.version += 1
    row.updated_at = now()
    db.add(
        BusinessProfileRevision(
            organization_id=org,
            profile_id=row.id,
            version=row.version,
            snapshot=fields,
            author_user_id=actor.id,
        )
    )
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=row.id,
            action="business.profile_updated",
            request_id=request_id,
            changed_fields=",".join(PROFILE_FIELDS),
            resource_version=row.version,
        )
    )
    db.commit()
    return profile_view(db, row)


def submit_outcome(
    db: Session, org: UUID, actor: User, follow_up_id: UUID, data: OutcomeCreate, request_id: str
) -> OutcomeView:
    followup = db.scalar(
        select(BusinessFollowUp)
        .where(
            BusinessFollowUp.id == follow_up_id,
            BusinessFollowUp.organization_id == org,
        )
        .with_for_update()
    )
    if followup is None:
        raise AuthError("not_found", 404)
    profile = db.scalar(
        select(BusinessProfile).where(
            BusinessProfile.id == followup.profile_id, BusinessProfile.organization_id == org
        )
    )
    if profile is None:
        raise AuthError("not_found", 404)
    owned_enrollment(db, org, actor, profile.enrollment_id)
    if followup.status != "pending":
        raise AuthError("outcome_exists", 409)
    if data.reported_on > date.today():
        raise AuthError("future_report_date", 422)
    row = BusinessOutcomeSnapshot(
        organization_id=org, follow_up_id=followup.id, author_user_id=actor.id, **data.model_dump()
    )
    db.add(row)
    followup.status = "completed"
    followup.completed_at = now()
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=followup.id,
            action="business.outcome_submitted",
            request_id=request_id,
            changed_fields="status,outcome",
            resource_version=1,
        )
    )
    db.commit()
    return OutcomeView(id=row.id, created_at=row.created_at, **data.model_dump())


def policy_view(db: Session, org: UUID) -> PolicyView:
    row = db.scalar(select(FollowUpPolicy).where(FollowUpPolicy.organization_id == org))
    return PolicyView(
        day_offsets=row.day_offsets if row else DEFAULT_OFFSETS, version=row.version if row else 0
    )


def update_policy(
    db: Session, org: UUID, actor: User, data: PolicyUpdate, request_id: str
) -> PolicyView:
    require_permission(db, actor, org, "business.track.manage")
    row = db.scalar(
        select(FollowUpPolicy).where(FollowUpPolicy.organization_id == org).with_for_update()
    )
    if (row.version if row else 0) != data.expected_version:
        raise AuthError("version_conflict", 409)
    if row is None:
        row = FollowUpPolicy(organization_id=org, day_offsets=data.day_offsets)
        db.add(row)
    else:
        row.day_offsets = data.day_offsets
        row.version += 1
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("version_conflict", 409) from exc
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=row.id,
            action="business.policy_updated",
            request_id=request_id,
            changed_fields="day_offsets",
            resource_version=row.version,
            reason=data.reason.strip(),
        )
    )
    db.commit()
    return PolicyView(day_offsets=row.day_offsets, version=row.version)


def staff_dashboard(db: Session, org: UUID, actor: User) -> StaffDashboard:
    require_permission(db, actor, org, "business.track.view")
    profiles = list(
        db.scalars(
            select(BusinessProfile)
            .where(
                BusinessProfile.organization_id == org,
            )
            .order_by(BusinessProfile.created_at.desc())
            .limit(100)
        )
    )
    followups = (
        list(
            db.scalars(
                select(BusinessFollowUp).where(
                    BusinessFollowUp.organization_id == org,
                    BusinessFollowUp.profile_id.in_([item.id for item in profiles]),
                )
            )
        )
        if profiles
        else []
    )
    return StaffDashboard(
        policy=policy_view(db, org),
        profiles=[
            StaffBusinessSummary(
                profile_id=item.id,
                enrollment_id=item.enrollment_id,
                name=item.name,
                stage=cast(BusinessStage, item.stage),
                due_count=sum(
                    f.profile_id == item.id and f.status == "pending" and f.due_on <= date.today()
                    for f in followups
                ),
                completed_count=sum(
                    f.profile_id == item.id and f.status == "completed" for f in followups
                ),
            )
            for item in profiles
        ],
    )
