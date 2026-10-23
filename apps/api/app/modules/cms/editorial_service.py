from typing import cast
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.cms.models import EditorialEntry
from app.modules.cms.schemas import (
    EditorialCommand,
    EditorialDraft,
    EditorialEdit,
    EditorialKind,
    EditorialView,
    Locale,
)
from app.modules.identity.models import AuditLog, User, now
from app.modules.identity.security import AuthError
from app.modules.identity.service import require_permission

KINDS = {"news", "event", "faq", "testimonial"}


def view(e: EditorialEntry) -> EditorialView:
    return EditorialView(
        id=e.id,
        kind=e.kind,
        slug=e.slug,
        locale=e.locale,
        title=e.title,
        body=e.body,
        starts_at=e.starts_at,
        ends_at=e.ends_at,
        sort_order=e.sort_order,
        state=e.state,
        version=e.version,
        published_at=e.published_at,
    )


def record(
    db: Session,
    actor: User,
    org: UUID,
    e: EditorialEntry,
    action: str,
    request_id: str,
    reason: str = "",
) -> None:
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=e.id,
            action="cms.editorial." + action,
            request_id=request_id,
            resource_version=e.version,
            reason=reason or None,
            changed_fields="kind,slug,locale,title,body,starts_at,ends_at,sort_order"
            if action in {"created", "updated"}
            else "state,published_at",
        )
    )


def commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("content_conflict", 409) from exc


def create(
    db: Session, org: UUID, actor: User, data: EditorialDraft, request_id: str
) -> EditorialView:
    require_permission(db, actor, org, "cms.editorial.create")
    e = EditorialEntry(organization_id=org, **data.model_dump())
    db.add(e)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("content_conflict", 409) from exc
    record(db, actor, org, e, "created", request_id)
    commit(db)
    return view(e)


def get(db: Session, org: UUID, id: UUID) -> EditorialEntry:
    e = db.scalar(
        select(EditorialEntry)
        .where(EditorialEntry.id == id, EditorialEntry.organization_id == org)
        .with_for_update()
    )
    if not e:
        raise AuthError("not_found", 404)
    return e


def mutate(
    db: Session,
    org: UUID,
    id: UUID,
    actor: User,
    data: EditorialEdit | EditorialCommand,
    action: str,
    request_id: str,
) -> EditorialView:
    permission = action if action in {"publish", "archive"} else "update"
    require_permission(db, actor, org, "cms.editorial." + permission)
    e = get(db, org, id)
    if e.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    if action == "update":
        if e.state == "published":
            raise AuthError("published_entry_read_only", 409)
        if e.state == "archived":
            raise AuthError("invalid_transition", 409)
        for k in ("title", "body", "starts_at", "ends_at", "sort_order"):
            setattr(e, k, getattr(data, k))
    elif action == "publish":
        if e.state == "archived":
            raise AuthError("invalid_transition", 409)
        e.state = "published"
        e.published_at = now()
    elif action == "archive":
        if not cast(EditorialCommand, data).reason or e.state == "archived":
            raise AuthError("invalid_transition", 409)
        e.state = "archived"
        e.published_at = None
    elif action == "restore":
        if e.state != "archived":
            raise AuthError("invalid_transition", 409)
        e.state = "draft"
    else:
        raise AuthError("invalid_request", 400)
    e.version += 1
    e.updated_at = now()
    record(
        db,
        actor,
        org,
        e,
        {"update": "updated", "publish": "published", "archive": "archived", "restore": "restored"}[
            action
        ],
        request_id,
        getattr(data, "reason", ""),
    )
    commit(db)
    return view(e)


def public(
    db: Session,
    org: UUID,
    kind: EditorialKind,
    locale: Locale,
    cursor: UUID | None,
    limit: int,
) -> list[EditorialEntry]:
    q = select(EditorialEntry).where(
        EditorialEntry.organization_id == org,
        EditorialEntry.kind == kind,
        EditorialEntry.locale == locale,
        EditorialEntry.state == "published",
    )
    if cursor:
        previous = db.scalar(q.where(EditorialEntry.id == cursor))
        if previous is None:
            raise AuthError("invalid_cursor", 400)
        after_order = or_(
            EditorialEntry.sort_order > previous.sort_order,
            and_(
                EditorialEntry.sort_order == previous.sort_order,
                EditorialEntry.id > previous.id,
            ),
        )
        if kind == "event":
            if previous.starts_at is None:
                q = q.where(and_(EditorialEntry.starts_at.is_(None), after_order))
            else:
                q = q.where(
                    or_(
                        EditorialEntry.starts_at > previous.starts_at,
                        EditorialEntry.starts_at.is_(None),
                        and_(EditorialEntry.starts_at == previous.starts_at, after_order),
                    )
                )
        else:
            q = q.where(after_order)
    order = (
        (
            EditorialEntry.starts_at.asc().nulls_last(),
            EditorialEntry.sort_order.asc(),
            EditorialEntry.id.asc(),
        )
        if kind == "event"
        else (EditorialEntry.sort_order.asc(), EditorialEntry.id.asc())
    )
    rows = list(db.scalars(q.order_by(*order).limit(limit + 1)))
    return rows
