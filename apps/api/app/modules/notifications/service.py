from datetime import timedelta
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.identity.models import AuditLog, User, now
from app.modules.identity.security import AuthError
from app.modules.identity.service import require_permission
from app.modules.notifications.models import NotificationIntent, NotificationPreference
from app.modules.notifications.schemas import (
    MarkRead,
    NotificationView,
    PreferenceEdit,
    PreferenceView,
)

TOPIC: Literal["lead_assignment"] = "lead_assignment"


def preference(db: Session, org: UUID, actor: User) -> PreferenceView:
    require_permission(db, actor, org, "crm.lead.view")
    row = db.scalar(
        select(NotificationPreference).where(
            NotificationPreference.organization_id == org,
            NotificationPreference.user_id == actor.id,
            NotificationPreference.topic == TOPIC,
        )
    )
    return (
        PreferenceView(enabled=row.enabled, version=row.version)
        if row
        else PreferenceView(enabled=True, version=0)
    )


def update_preference(
    db: Session, org: UUID, actor: User, data: PreferenceEdit, request_id: str
) -> PreferenceView:
    require_permission(db, actor, org, "crm.lead.view")
    row = db.scalar(
        select(NotificationPreference)
        .where(
            NotificationPreference.organization_id == org,
            NotificationPreference.user_id == actor.id,
            NotificationPreference.topic == TOPIC,
        )
        .with_for_update()
    )
    if row:
        if row.version != data.expected_version:
            raise AuthError("version_conflict", 409)
        row.enabled = data.enabled
        row.version += 1
        row.updated_at = now()
    else:
        if data.expected_version != 0:
            raise AuthError("version_conflict", 409)
        row = NotificationPreference(
            organization_id=org, user_id=actor.id, topic=TOPIC, enabled=data.enabled
        )
        db.add(row)
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
            action="notification.preference.updated",
            request_id=request_id,
            resource_version=row.version,
            changed_fields="enabled",
        )
    )
    db.commit()
    return PreferenceView(enabled=row.enabled, version=row.version)


def view(row: NotificationIntent) -> NotificationView:
    return NotificationView(
        id=row.id,
        topic=TOPIC,
        resource_id=row.resource_id,
        created_at=row.created_at,
        read_at=row.read_at,
        version=row.version,
    )


def mine(
    db: Session, org: UUID, actor: User, cursor: UUID | None, limit: int
) -> tuple[list[NotificationView], UUID | None]:
    require_permission(db, actor, org, "crm.lead.view")
    query = select(NotificationIntent).where(
        NotificationIntent.organization_id == org,
        NotificationIntent.recipient_user_id == actor.id,
        NotificationIntent.state == "delivered",
    )
    retention_days = get_settings().notification_retention_days
    if retention_days is not None:
        query = query.where(NotificationIntent.created_at >= now() - timedelta(days=retention_days))
    if cursor:
        query = query.where(NotificationIntent.id > cursor)
    rows = list(db.scalars(query.order_by(NotificationIntent.id).limit(limit + 1)))
    return [view(row) for row in rows[:limit]], rows[limit - 1].id if len(rows) > limit else None


def mark_read(
    db: Session,
    org: UUID,
    actor: User,
    notification_id: UUID,
    data: MarkRead,
    request_id: str,
) -> NotificationView:
    require_permission(db, actor, org, "crm.lead.view")
    row = db.scalar(
        select(NotificationIntent)
        .where(
            NotificationIntent.id == notification_id,
            NotificationIntent.organization_id == org,
            NotificationIntent.recipient_user_id == actor.id,
            NotificationIntent.state == "delivered",
        )
        .with_for_update()
    )
    if not row:
        raise AuthError("not_found", 404)
    retention_days = get_settings().notification_retention_days
    if retention_days is not None and row.created_at < now() - timedelta(days=retention_days):
        raise AuthError("not_found", 404)
    if row.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    if row.read_at is not None:
        raise AuthError("invalid_transition", 409)
    row.read_at = now()
    row.version += 1
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=row.id,
            action="notification.read",
            request_id=request_id,
            resource_version=row.version,
            changed_fields="read_at",
        )
    )
    db.commit()
    return view(row)
