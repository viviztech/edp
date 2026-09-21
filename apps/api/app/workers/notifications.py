from datetime import timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.crm.models import Lead, LeadActivity
from app.modules.identity.models import AuditLog, User, now
from app.modules.identity.security import AuthError
from app.modules.identity.service import require_permission
from app.modules.notifications.models import NotificationIntent, NotificationPreference
from app.workers.celery_app import celery_app

settings = get_settings()
engine = create_engine(settings.database_url.get_secret_value(), pool_pre_ping=True)


@celery_app.task(name="edp.notifications.queue_due_followups")  # type: ignore[untyped-decorator]
def queue_due_followups() -> dict[str, int]:
    """Queue one minimal intent per due activity and current lead assignee."""
    policy = get_settings()
    if policy.app_env in {"staging", "production"} and policy.notification_retention_days is None:
        return {"queued": 0}
    current = now()
    existing = (
        select(NotificationIntent.id)
        .where(
            NotificationIntent.source_activity_id == LeadActivity.id,
            NotificationIntent.recipient_user_id == Lead.assigned_user_id,
        )
        .correlate(LeadActivity, Lead)
        .exists()
    )
    with Session(engine) as db:
        rows = list(
            db.execute(
                select(LeadActivity, Lead.assigned_user_id)
                .join(
                    Lead,
                    (Lead.id == LeadActivity.lead_id)
                    & (Lead.organization_id == LeadActivity.organization_id),
                )
                .where(
                    LeadActivity.completed_at.is_(None),
                    LeadActivity.due_at.is_not(None),
                    LeadActivity.due_at <= current,
                    LeadActivity.activity_type != "note",
                    Lead.assigned_user_id.is_not(None),
                    Lead.status.notin_(("merged", "converted")),
                    LeadActivity.reminder_queued_for_user_id.is_distinct_from(
                        Lead.assigned_user_id
                    ),
                    ~existing,
                )
                .order_by(LeadActivity.due_at, LeadActivity.id)
                .limit(100)
                .with_for_update(of=LeadActivity, skip_locked=True)
            )
        )
        for activity, recipient_id in rows:
            if recipient_id is None:
                continue
            intent = NotificationIntent(
                organization_id=activity.organization_id,
                recipient_user_id=recipient_id,
                topic="followup_due",
                resource_id=activity.lead_id,
                source_activity_id=activity.id,
                event_key=f"crm.followup.due:{activity.id}",
            )
            db.add(intent)
            activity.reminder_queued_for_user_id = recipient_id
            db.flush()
            db.add(
                AuditLog(
                    actor_id=None,
                    organization_id=activity.organization_id,
                    resource_id=intent.id,
                    action="notification.queued",
                    request_id=f"followup:{activity.id}",
                    resource_version=1,
                    changed_fields="state",
                )
            )
        db.commit()
        return {"queued": len(rows)}


@celery_app.task(name="edp.notifications.deliver_in_app")  # type: ignore[untyped-decorator]
def deliver_in_app() -> dict[str, int]:
    """Materialize pending database intents; no external provider is contacted."""
    delivered = suppressed = 0
    with Session(engine) as db:
        retention_days = get_settings().notification_retention_days
        query = select(NotificationIntent).where(NotificationIntent.state == "pending")
        if retention_days is not None:
            query = query.where(
                NotificationIntent.created_at >= now() - timedelta(days=retention_days)
            )
        rows = list(
            db.scalars(
                query.order_by(NotificationIntent.created_at, NotificationIntent.id)
                .limit(100)
                .with_for_update(skip_locked=True)
            )
        )
        for row in rows:
            if retention_days is not None and row.created_at < now() - timedelta(
                days=retention_days
            ):
                continue
            user = db.get(User, row.recipient_user_id)
            lead = db.get(Lead, row.resource_id)
            allowed = bool(user and user.status == "active")
            if allowed and user:
                try:
                    require_permission(db, user, row.organization_id, "crm.lead.view")
                except AuthError:
                    allowed = False
            pref = db.scalar(
                select(NotificationPreference).where(
                    NotificationPreference.organization_id == row.organization_id,
                    NotificationPreference.user_id == row.recipient_user_id,
                    NotificationPreference.topic == row.topic,
                )
            )
            allowed = allowed and bool(
                lead
                and lead.organization_id == row.organization_id
                and lead.assigned_user_id == row.recipient_user_id
            )
            if row.topic == "followup_due":
                activity = db.get(LeadActivity, row.source_activity_id)
                allowed = allowed and bool(
                    activity
                    and activity.organization_id == row.organization_id
                    and activity.lead_id == row.resource_id
                    and activity.completed_at is None
                    and activity.due_at is not None
                    and activity.due_at <= now()
                )
            if pref and not pref.enabled:
                allowed = False
            row.state = "delivered" if allowed else "suppressed"
            row.delivered_at = now() if allowed else None
            row.version += 1
            db.add(
                AuditLog(
                    actor_id=None,
                    organization_id=row.organization_id,
                    resource_id=row.id,
                    action="notification.delivered" if allowed else "notification.suppressed",
                    request_id=f"notification:{row.id}",
                    resource_version=row.version,
                    changed_fields="state",
                )
            )
            delivered += int(allowed)
            suppressed += int(not allowed)
        db.commit()
    return {"delivered": delivered, "suppressed": suppressed}


@celery_app.task(name="edp.notifications.purge_expired")  # type: ignore[untyped-decorator]
def purge_expired() -> dict[str, int]:
    """Delete only expired notification intents under an approved retention setting."""
    days = get_settings().notification_retention_days
    if days is None:
        return {"purged": 0}
    cutoff = now() - timedelta(days=days)
    with Session(engine) as db:
        rows = list(
            db.scalars(
                select(NotificationIntent)
                .where(NotificationIntent.created_at < cutoff)
                .order_by(NotificationIntent.created_at, NotificationIntent.id)
                .limit(100)
                .with_for_update(skip_locked=True)
            )
        )
        for row in rows:
            db.add(
                AuditLog(
                    actor_id=None,
                    organization_id=row.organization_id,
                    resource_id=row.id,
                    action="notification.retention_purged",
                    request_id=f"retention:{row.id}",
                    resource_version=row.version,
                    reason="Configured notification retention expired",
                    changed_fields="intent_deleted",
                )
            )
            db.delete(row)
        db.commit()
        return {"purged": len(rows)}
