import hashlib
from datetime import timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.crm.models import (
    DuplicateReview,
    ExportJob,
    Lead,
    LeadActivity,
    LeadConversion,
    LeadTag,
    Tag,
)
from app.modules.crm.schemas import (
    ActivityComplete,
    ActivityCreate,
    ActivityView,
    DuplicateResolve,
    DuplicateReviewCreate,
    DuplicateReviewView,
    ExportJobView,
    LeadConversionCreate,
    LeadConversionView,
    LeadCreate,
    LeadEdit,
    LeadView,
    TagCreate,
    TagView,
)
from app.modules.identity.models import AuditLog, Person, User, UserRole, now
from app.modules.identity.security import AuthError
from app.modules.identity.service import require_permission
from app.modules.notifications.models import NotificationIntent
from app.workers.celery_app import celery_app


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
    if d.status in {"merged", "converted"} or x.status in {"merged", "converted"}:
        raise AuthError("invalid_transition", 409)
    assignment_changed = d.assigned_user_id != x.assigned_user_id
    if assignment_changed:
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
    if assignment_changed and d.assigned_user_id is not None:
        db.add(
            NotificationIntent(
                organization_id=org,
                recipient_user_id=d.assigned_user_id,
                topic="lead_assignment",
                resource_id=x.id,
                event_key=f"crm.lead.assigned:{x.id}:{x.version}",
            )
        )
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
        version=a.version,
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


def complete_activity(
    db: Session,
    org: UUID,
    lead_id: UUID,
    activity_id: UUID,
    actor: User,
    data: ActivityComplete,
    request_id: str,
) -> ActivityView:
    require_permission(db, actor, org, "crm.activity.update")
    activity = db.scalar(
        select(LeadActivity)
        .where(
            LeadActivity.id == activity_id,
            LeadActivity.lead_id == lead_id,
            LeadActivity.organization_id == org,
        )
        .with_for_update()
    )
    if not activity:
        raise AuthError("not_found", 404)
    if activity.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    if activity.completed_at is not None:
        raise AuthError("invalid_transition", 409)
    activity.completed_at = now()
    activity.version += 1
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=activity.id,
            action="crm.lead.activity_completed",
            request_id=request_id,
            resource_version=activity.version,
            changed_fields="completed_at",
        )
    )
    db.commit()
    return activity_view(activity)


def normalize_tag_name(value: str) -> str:
    return " ".join(value.casefold().split())


def tag_view(tag: Tag) -> TagView:
    return TagView(id=tag.id, name=tag.name)


def create_tag(db: Session, org: UUID, actor: User, data: TagCreate, request_id: str) -> TagView:
    require_permission(db, actor, org, "crm.tag.manage")
    tag = Tag(
        organization_id=org,
        name=" ".join(data.name.split()),
        normalized_name=normalize_tag_name(data.name),
    )
    db.add(tag)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("tag_exists", 409) from exc
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=tag.id,
            action="crm.tag.created",
            request_id=request_id,
            resource_version=1,
            changed_fields="name",
        )
    )
    db.commit()
    return tag_view(tag)


def tags(db: Session, org: UUID, actor: User) -> list[TagView]:
    require_permission(db, actor, org, "crm.tag.view")
    return [
        tag_view(tag)
        for tag in db.scalars(
            select(Tag).where(Tag.organization_id == org).order_by(Tag.normalized_name)
        )
    ]


def lead_tags(db: Session, org: UUID, lead_id: UUID, actor: User) -> list[TagView]:
    require_permission(db, actor, org, "crm.tag.view")
    if not db.scalar(select(Lead.id).where(Lead.id == lead_id, Lead.organization_id == org)):
        raise AuthError("not_found", 404)
    return [
        tag_view(tag)
        for tag in db.scalars(
            select(Tag)
            .join(LeadTag, LeadTag.tag_id == Tag.id)
            .where(
                LeadTag.organization_id == org,
                LeadTag.lead_id == lead_id,
                Tag.organization_id == org,
            )
            .order_by(Tag.normalized_name)
        )
    ]


def attach_tag(
    db: Session,
    org: UUID,
    lead_id: UUID,
    tag_id: UUID,
    actor: User,
    request_id: str,
) -> TagView:
    require_permission(db, actor, org, "crm.tag.manage")
    lead = db.scalar(select(Lead).where(Lead.id == lead_id, Lead.organization_id == org))
    tag = db.scalar(select(Tag).where(Tag.id == tag_id, Tag.organization_id == org))
    if not lead or not tag:
        raise AuthError("not_found", 404)
    link = LeadTag(organization_id=org, lead_id=lead_id, tag_id=tag_id)
    db.add(link)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("tag_already_attached", 409) from exc
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=lead_id,
            action="crm.lead.tag_attached",
            request_id=request_id,
            resource_version=lead.version,
            changed_fields="tags",
        )
    )
    db.commit()
    return tag_view(tag)


def detach_tag(
    db: Session,
    org: UUID,
    lead_id: UUID,
    tag_id: UUID,
    actor: User,
    request_id: str,
) -> None:
    require_permission(db, actor, org, "crm.tag.manage")
    lead = db.scalar(select(Lead).where(Lead.id == lead_id, Lead.organization_id == org))
    link = db.scalar(
        select(LeadTag).where(
            LeadTag.organization_id == org,
            LeadTag.lead_id == lead_id,
            LeadTag.tag_id == tag_id,
        )
    )
    if not lead or not link:
        raise AuthError("not_found", 404)
    db.delete(link)
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=lead_id,
            action="crm.lead.tag_detached",
            request_id=request_id,
            resource_version=lead.version,
            changed_fields="tags",
        )
    )
    db.commit()


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


def export_view(job: ExportJob) -> ExportJobView:
    return ExportJobView(
        id=job.id,
        status=job.status,
        row_count=job.row_count,
        error_code=job.error_code,
        completed_at=job.completed_at,
        expires_at=job.expires_at,
    )


def request_export(db: Session, org: UUID, actor: User, request_id: str) -> ExportJobView:
    require_permission(db, actor, org, "crm.lead.export")
    job = ExportJob(
        organization_id=org,
        requested_by_id=actor.id,
        expires_at=now() + timedelta(hours=24),
    )
    db.add(job)
    db.flush()
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=job.id,
            action="crm.lead.export_requested",
            request_id=request_id,
            resource_version=1,
            changed_fields="status",
        )
    )
    db.commit()
    try:
        celery_app.send_task("edp.crm.export_leads", args=[str(job.id)])
    except Exception as exc:
        job.status = "failed"
        job.error_code = "queue_unavailable"
        job.completed_at = now()
        db.commit()
        raise AuthError("export_unavailable", 503) from exc
    return export_view(job)


def get_export(db: Session, org: UUID, job_id: UUID, actor: User) -> ExportJob:
    require_permission(db, actor, org, "crm.lead.export")
    job = db.scalar(
        select(ExportJob).where(
            ExportJob.id == job_id,
            ExportJob.organization_id == org,
            ExportJob.requested_by_id == actor.id,
        )
    )
    if not job:
        raise AuthError("not_found", 404)
    if job.expires_at <= now():
        if job.csv_content is not None:
            job.csv_content = None
            job.status = "failed"
            job.error_code = "expired"
            db.commit()
        raise AuthError("not_found", 404)
    return job


def download_export(db: Session, org: UUID, job_id: UUID, actor: User, request_id: str) -> str:
    job = get_export(db, org, job_id, actor)
    if job.status != "completed" or job.csv_content is None:
        raise AuthError("export_not_ready", 409)
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=job.id,
            action="crm.lead.export_downloaded",
            request_id=request_id,
            resource_version=1,
            changed_fields=None,
        )
    )
    db.commit()
    return job.csv_content


def conversion_view(link: LeadConversion) -> LeadConversionView:
    return LeadConversionView(
        id=link.id,
        lead_id=link.lead_id,
        person_id=link.person_id,
        source=link.source,
        campaign=link.campaign,
        lead_version=link.lead_version,
        reason=link.reason,
        created_at=link.created_at,
    )


def link_registration(
    db: Session,
    org: UUID,
    lead_id: UUID,
    actor: User,
    data: LeadConversionCreate,
    request_id: str,
) -> LeadConversionView:
    require_permission(db, actor, org, "crm.lead.convert")
    lead = db.scalar(
        select(Lead).where(Lead.id == lead_id, Lead.organization_id == org).with_for_update()
    )
    if not lead:
        raise AuthError("not_found", 404)
    if lead.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    if lead.status in {"merged", "converted", "not_interested"}:
        raise AuthError("invalid_transition", 409)
    if not db.get(Person, data.person_id):
        raise AuthError("not_found", 404)
    if db.scalar(select(LeadConversion.id).where(LeadConversion.lead_id == lead.id)):
        raise AuthError("conversion_exists", 409)
    lead.status = "registration_started"
    lead.version += 1
    lead.updated_at = now()
    link = LeadConversion(
        organization_id=org,
        lead_id=lead.id,
        person_id=data.person_id,
        actor_user_id=actor.id,
        source=lead.source,
        campaign=lead.campaign,
        lead_version=lead.version,
        reason=data.reason,
    )
    db.add(link)
    db.flush()
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=lead.id,
            action="crm.lead.registration_linked",
            request_id=request_id,
            resource_version=lead.version,
            reason=data.reason,
            changed_fields="status,person_id",
        )
    )
    db.commit()
    return conversion_view(link)


def get_registration_link(db: Session, org: UUID, lead_id: UUID, actor: User) -> LeadConversionView:
    require_permission(db, actor, org, "crm.lead.view")
    link = db.scalar(
        select(LeadConversion).where(
            LeadConversion.lead_id == lead_id, LeadConversion.organization_id == org
        )
    )
    if not link:
        raise AuthError("not_found", 404)
    return conversion_view(link)
