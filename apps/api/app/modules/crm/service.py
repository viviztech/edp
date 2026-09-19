import hashlib
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.crm.models import DuplicateReview, Lead, LeadActivity
from app.modules.crm.schemas import (
    ActivityCreate,
    ActivityView,
    DuplicateResolve,
    DuplicateReviewCreate,
    DuplicateReviewView,
    LeadCreate,
    LeadEdit,
    LeadView,
)
from app.modules.identity.models import AuditLog, User, UserRole, now
from app.modules.identity.security import AuthError
from app.modules.identity.service import require_permission


def view(x: Lead) -> LeadView:
    return LeadView(
        id=x.id,
        name=x.name,
        email=x.email,
        phone=x.phone,
        source=x.source,
        campaign=x.campaign,
        status=x.status,
        assigned_user_id=x.assigned_user_id,
        merged_into_id=x.merged_into_id,
        notes=x.notes,
        version=x.version,
    )


def create(db: Session, org: UUID, actor: User, d: LeadCreate, request_id: str) -> LeadView:
    require_permission(db, actor, org, "crm.lead.create")
    h = hashlib.sha256((d.email.lower() + "|" + d.phone).encode()).hexdigest()
    x = Lead(organization_id=org, dedupe_hash=h, **d.model_dump())
    db.add(x)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("duplicate_lead", 409) from exc
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=x.id,
            action="crm.lead.created",
            request_id=request_id,
            resource_version=1,
            changed_fields="name,email,phone,source,campaign,status",
        )
    )
    db.commit()
    return view(x)


def mutate(
    db: Session, org: UUID, lead_id: UUID, actor: User, d: LeadEdit, request_id: str
) -> LeadView:
    require_permission(db, actor, org, "crm.lead.update")
    x = db.scalar(
        select(Lead).where(Lead.id == lead_id, Lead.organization_id == org).with_for_update()
    )
    if not x:
        raise AuthError("not_found", 404)
    if x.version != d.expected_version:
        raise AuthError("version_conflict", 409)
    if d.status == "merged" or x.status == "merged":
        raise AuthError("invalid_transition", 409)
    if d.assigned_user_id != x.assigned_user_id:
        require_permission(db, actor, org, "crm.lead.assign")
        if d.assigned_user_id is not None and not db.scalar(
            select(UserRole.id).where(
                UserRole.user_id == d.assigned_user_id, UserRole.organization_id == org
            )
        ):
            raise AuthError("not_found", 404)
    x.status, x.assigned_user_id, x.notes = d.status, d.assigned_user_id, d.notes
    x.version += 1
    x.updated_at = now()
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=x.id,
            action="crm.lead.updated",
            request_id=request_id,
            resource_version=x.version,
            changed_fields="status,assigned_user_id,notes",
        )
    )
    db.commit()
    return view(x)


def activity_view(a: LeadActivity) -> ActivityView:
    return ActivityView(
        id=a.id,
        lead_id=a.lead_id,
        actor_user_id=a.actor_user_id,
        activity_type=a.activity_type,
        note=a.note,
        due_at=a.due_at,
        completed_at=a.completed_at,
    )


def add_activity(
    db: Session,
    org: UUID,
    lead_id: UUID,
    actor: User,
    data: ActivityCreate,
    request_id: str,
) -> ActivityView:
    require_permission(db, actor, org, "crm.activity.create")
    lead = db.scalar(select(Lead).where(Lead.id == lead_id, Lead.organization_id == org))
    if not lead:
        raise AuthError("not_found", 404)
    if lead.status == "merged":
        raise AuthError("invalid_transition", 409)
    a = LeadActivity(
        lead_id=lead.id, organization_id=org, actor_user_id=actor.id, **data.model_dump()
    )
    db.add(a)
    db.flush()
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=lead.id,
            action="crm.lead.activity_added",
            request_id=request_id,
            resource_version=lead.version,
            changed_fields="activity_type,due_at",
        )
    )
    db.commit()
    return activity_view(a)


def activities(
    db: Session, org: UUID, lead_id: UUID, actor: User, limit: int
) -> list[ActivityView]:
    require_permission(db, actor, org, "crm.activity.view")
    if not db.scalar(select(Lead.id).where(Lead.id == lead_id, Lead.organization_id == org)):
        raise AuthError("not_found", 404)
    return [
        activity_view(a)
        for a in db.scalars(
            select(LeadActivity)
            .where(LeadActivity.lead_id == lead_id, LeadActivity.organization_id == org)
            .order_by(LeadActivity.created_at.desc())
            .limit(limit)
        )
    ]


def duplicate_view(review: DuplicateReview) -> DuplicateReviewView:
    return DuplicateReviewView(
        id=review.id,
        lead_a_id=review.lead_a_id,
        lead_b_id=review.lead_b_id,
        state=review.state,
        version=review.version,
        reason=review.reason,
        resolved_by_id=review.resolved_by_id,
    )


def create_duplicate_review(
    db: Session,
    org: UUID,
    actor: User,
    data: DuplicateReviewCreate,
    request_id: str,
) -> DuplicateReviewView:
    require_permission(db, actor, org, "crm.lead.merge")
    if data.lead_a_id == data.lead_b_id:
        raise AuthError("invalid_request", 400)
    ids = sorted((data.lead_a_id, data.lead_b_id), key=str)
    leads = list(db.scalars(select(Lead).where(Lead.organization_id == org, Lead.id.in_(ids))))
    if len(leads) != 2 or any(x.status == "merged" for x in leads):
        raise AuthError("not_found", 404)
    review = DuplicateReview(organization_id=org, lead_a_id=ids[0], lead_b_id=ids[1])
    db.add(review)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("duplicate_review_exists", 409) from exc
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=review.id,
            action="crm.duplicate_review.created",
            request_id=request_id,
            resource_version=1,
            changed_fields="lead_a_id,lead_b_id,state",
        )
    )
    db.commit()
    return duplicate_view(review)


def resolve_duplicate_review(
    db: Session,
    org: UUID,
    review_id: UUID,
    actor: User,
    data: DuplicateResolve,
    request_id: str,
) -> DuplicateReviewView:
    require_permission(db, actor, org, "crm.lead.merge")
    review = db.scalar(
        select(DuplicateReview)
        .where(DuplicateReview.id == review_id, DuplicateReview.organization_id == org)
        .with_for_update()
    )
    if not review:
        raise AuthError("not_found", 404)
    if review.state != "pending":
        raise AuthError("invalid_transition", 409)
    if review.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    if data.action == "merge":
        if data.survivor_id not in {review.lead_a_id, review.lead_b_id}:
            raise AuthError("invalid_request", 400)
        duplicate_id = (
            review.lead_b_id if data.survivor_id == review.lead_a_id else review.lead_a_id
        )
        rows = list(
            db.scalars(
                select(Lead)
                .where(Lead.organization_id == org, Lead.id.in_([data.survivor_id, duplicate_id]))
                .with_for_update()
            )
        )
        if len(rows) != 2 or any(x.status == "merged" for x in rows):
            raise AuthError("invalid_transition", 409)
        duplicate = next(x for x in rows if x.id == duplicate_id)
        duplicate.status = "merged"
        duplicate.merged_into_id = data.survivor_id
        duplicate.version += 1
        duplicate.updated_at = now()
        review.state = "merged"
    else:
        if data.survivor_id is not None:
            raise AuthError("invalid_request", 400)
        review.state = "rejected"
    review.reason = data.reason
    review.resolved_by_id = actor.id
    review.version += 1
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=review.id,
            action="crm.duplicate_review." + review.state,
            request_id=request_id,
            resource_version=review.version,
            reason=data.reason,
            changed_fields="state,resolved_by_id",
        )
    )
    db.commit()
    return duplicate_view(review)
