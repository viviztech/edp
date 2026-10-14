from typing import Literal, cast, get_args
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.business_plans.models import (
    BusinessPlan,
    BusinessPlanReview,
    BusinessPlanRevision,
    BusinessPlanSubmission,
)
from app.modules.business_plans.schemas import (
    MentorPlans,
    MyPlans,
    PlanEntry,
    PlanView,
    ReviewPlan,
    ReviewView,
    RevisionView,
    SaveSection,
    SectionCode,
    SubmissionView,
    SubmitPlan,
)
from app.modules.identity.models import AuditLog, User
from app.modules.identity.security import AuthError
from app.modules.identity.service import require_permission
from app.modules.mentoring.models import MentorAssignment, MentorProfile
from app.modules.programs.models import Enrollment, Participant

SECTION_CODES = get_args(SectionCode)


def submission_view(db: Session, item: BusinessPlanSubmission) -> SubmissionView:
    plan = db.get(BusinessPlan, item.plan_id)
    if plan is None:
        raise AuthError("not_found", 404)
    review = db.scalar(
        select(BusinessPlanReview).where(BusinessPlanReview.submission_id == item.id)
    )
    return SubmissionView(
        id=item.id,
        enrollment_id=plan.enrollment_id,
        plan_version=plan.version,
        number=item.number,
        snapshot={cast(SectionCode, k): v for k, v in item.snapshot.items()},
        created_at=item.created_at,
        review=ReviewView(
            id=review.id,
            decision=cast(Literal["changes_requested", "approved"], review.decision),
            reason=review.reason,
            comments={cast(SectionCode, k): v for k, v in review.comments.items()},
            created_at=review.created_at,
        )
        if review
        else None,
    )


def enrollment_for_owner(db: Session, org: UUID, actor: User, enrollment_id: UUID) -> Enrollment:
    require_permission(db, actor, org, "participant.self")
    row = db.scalar(
        select(Enrollment)
        .join(Participant, Participant.id == Enrollment.participant_id)
        .where(
            Enrollment.id == enrollment_id,
            Enrollment.organization_id == org,
            Enrollment.status == "active",
            Participant.person_id == actor.person_id,
            Participant.organization_id == org,
        )
    )
    if row is None:
        raise AuthError("not_found", 404)
    return row


def view(db: Session, plan: BusinessPlan) -> PlanView:
    latest_versions = (
        select(func.max(BusinessPlanRevision.version))
        .where(BusinessPlanRevision.plan_id == plan.id)
        .group_by(BusinessPlanRevision.section_code)
    )
    latest = list(
        db.scalars(
            select(BusinessPlanRevision).where(
                BusinessPlanRevision.plan_id == plan.id,
                BusinessPlanRevision.version.in_(latest_versions),
            )
        )
    )
    history = list(
        db.scalars(
            select(BusinessPlanRevision)
            .where(BusinessPlanRevision.plan_id == plan.id)
            .order_by(BusinessPlanRevision.version.desc())
            .limit(50)
        )
    )
    sections = {cast(SectionCode, item.section_code): item.body for item in latest}
    submissions = list(
        db.scalars(
            select(BusinessPlanSubmission)
            .where(BusinessPlanSubmission.plan_id == plan.id)
            .order_by(BusinessPlanSubmission.number.desc())
            .limit(20)
        )
    )
    return PlanView(
        id=plan.id,
        enrollment_id=plan.enrollment_id,
        status=cast(Literal["draft", "submitted", "changes_requested", "approved"], plan.status),
        version=plan.version,
        completed_sections=sum(bool(body.strip()) for body in sections.values()),
        total_sections=len(SECTION_CODES),
        sections=sections,
        revisions=[
            RevisionView(
                id=item.id,
                version=item.version,
                section_code=cast(SectionCode, item.section_code),
                body=item.body,
                created_at=item.created_at,
            )
            for item in history
        ],
        submissions=[submission_view(db, item) for item in submissions],
    )


def my_plans(db: Session, org: UUID, actor: User) -> MyPlans:
    require_permission(db, actor, org, "participant.self")
    enrollments = list(
        db.scalars(
            select(Enrollment)
            .join(Participant, Participant.id == Enrollment.participant_id)
            .where(
                Enrollment.organization_id == org,
                Enrollment.status == "active",
                Participant.person_id == actor.person_id,
                Participant.organization_id == org,
            )
            .order_by(Enrollment.enrolled_at.desc())
            .limit(100)
        )
    )
    plans = {
        row.enrollment_id: row
        for row in db.scalars(
            select(BusinessPlan).where(
                BusinessPlan.organization_id == org,
                BusinessPlan.enrollment_id.in_([x.id for x in enrollments]),
            )
        )
    }
    return MyPlans(
        entries=[
            PlanEntry(
                enrollment_id=item.id,
                program_id=item.program_id,
                plan=view(db, plans[item.id]) if item.id in plans else None,
            )
            for item in enrollments
        ]
    )


def create_plan(
    db: Session, org: UUID, actor: User, enrollment_id: UUID, request_id: str
) -> PlanView:
    enrollment_for_owner(db, org, actor, enrollment_id)
    row = BusinessPlan(organization_id=org, enrollment_id=enrollment_id)
    db.add(row)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("plan_exists", 409) from exc
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=row.id,
            action="business_plan.created",
            request_id=request_id,
            changed_fields="enrollment_id",
            resource_version=1,
        )
    )
    db.commit()
    return view(db, row)


def save_section(
    db: Session, org: UUID, actor: User, enrollment_id: UUID, data: SaveSection, request_id: str
) -> PlanView:
    enrollment_for_owner(db, org, actor, enrollment_id)
    row = db.scalar(
        select(BusinessPlan)
        .where(BusinessPlan.organization_id == org, BusinessPlan.enrollment_id == enrollment_id)
        .with_for_update()
    )
    if row is None:
        raise AuthError("not_found", 404)
    if row.status not in {"draft", "changes_requested"}:
        raise AuthError("plan_not_editable", 409)
    if row.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    row.version += 1
    revision = BusinessPlanRevision(
        organization_id=org,
        plan_id=row.id,
        version=row.version,
        section_code=data.section_code,
        body=data.body.strip(),
        author_user_id=actor.id,
    )
    db.add(revision)
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=row.id,
            action="business_plan.section_saved",
            request_id=request_id,
            changed_fields=data.section_code,
            resource_version=row.version,
        )
    )
    db.commit()
    return view(db, row)


def submit_plan(
    db: Session,
    org: UUID,
    actor: User,
    enrollment_id: UUID,
    data: SubmitPlan,
    request_id: str,
) -> PlanView:
    enrollment_for_owner(db, org, actor, enrollment_id)
    row = db.scalar(
        select(BusinessPlan)
        .where(BusinessPlan.organization_id == org, BusinessPlan.enrollment_id == enrollment_id)
        .with_for_update()
    )
    if row is None:
        raise AuthError("not_found", 404)
    if row.status not in {"draft", "changes_requested"}:
        raise AuthError("plan_not_submittable", 409)
    if row.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    current = view(db, row)
    if current.completed_sections != len(SECTION_CODES):
        raise AuthError("plan_incomplete", 422)
    count = (
        db.scalar(
            select(func.max(BusinessPlanSubmission.number)).where(
                BusinessPlanSubmission.plan_id == row.id
            )
        )
        or 0
    )
    snapshot = {str(code): body for code, body in current.sections.items()}
    submission = BusinessPlanSubmission(
        organization_id=org,
        plan_id=row.id,
        number=count + 1,
        snapshot=snapshot,
        submitted_by_user_id=actor.id,
    )
    row.status = "submitted"
    row.version += 1
    db.add(submission)
    db.flush()
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=row.id,
            action="business_plan.submitted",
            request_id=request_id,
            changed_fields="status,submission_number",
            resource_version=row.version,
        )
    )
    db.commit()
    return view(db, row)


def assigned_submissions(db: Session, org: UUID, actor: User) -> MentorPlans:
    require_permission(db, actor, org, "mentoring.manage")
    items = list(
        db.scalars(
            select(BusinessPlanSubmission)
            .join(BusinessPlan, BusinessPlan.id == BusinessPlanSubmission.plan_id)
            .join(MentorAssignment, MentorAssignment.enrollment_id == BusinessPlan.enrollment_id)
            .join(MentorProfile, MentorProfile.id == MentorAssignment.mentor_profile_id)
            .where(
                BusinessPlanSubmission.organization_id == org,
                MentorAssignment.organization_id == org,
                MentorAssignment.state == "active",
                MentorProfile.user_id == actor.id,
                MentorProfile.organization_id == org,
            )
            .order_by(BusinessPlanSubmission.created_at.desc())
            .limit(100)
        )
    )
    return MentorPlans(submissions=[submission_view(db, item) for item in items])


def review_submission(
    db: Session,
    org: UUID,
    actor: User,
    submission_id: UUID,
    data: ReviewPlan,
    request_id: str,
) -> ReviewView:
    require_permission(db, actor, org, "mentoring.manage")
    submission = db.scalar(
        select(BusinessPlanSubmission).where(
            BusinessPlanSubmission.id == submission_id,
            BusinessPlanSubmission.organization_id == org,
        )
    )
    if submission is None:
        raise AuthError("not_found", 404)
    plan = db.scalar(
        select(BusinessPlan)
        .where(BusinessPlan.id == submission.plan_id, BusinessPlan.organization_id == org)
        .with_for_update()
    )
    if plan is None:
        raise AuthError("not_found", 404)
    assigned = db.scalar(
        select(MentorAssignment.id)
        .join(MentorProfile, MentorProfile.id == MentorAssignment.mentor_profile_id)
        .where(
            MentorAssignment.enrollment_id == plan.enrollment_id,
            MentorAssignment.organization_id == org,
            MentorAssignment.state == "active",
            MentorProfile.user_id == actor.id,
            MentorProfile.organization_id == org,
        )
    )
    if not assigned:
        raise AuthError("not_found", 404)
    if plan.status != "submitted" or plan.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    latest = db.scalar(
        select(func.max(BusinessPlanSubmission.number)).where(
            BusinessPlanSubmission.plan_id == plan.id
        )
    )
    if latest != submission.number:
        raise AuthError("version_conflict", 409)
    row = BusinessPlanReview(
        organization_id=org,
        submission_id=submission.id,
        reviewer_user_id=actor.id,
        decision=data.decision,
        comments={str(k): v.strip() for k, v in data.comments.items()},
        reason=data.reason.strip(),
    )
    plan.status = data.decision
    plan.version += 1
    db.add(row)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("review_exists", 409) from exc
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=plan.id,
            action="business_plan.reviewed",
            request_id=request_id,
            changed_fields="status,review",
            resource_version=plan.version,
        )
    )
    db.commit()
    result = submission_view(db, submission).review
    assert result is not None
    return result
