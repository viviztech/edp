from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.cms import repository
from app.modules.cms.models import Page, Revision, Translation
from app.modules.cms.schemas import (
    Command,
    CreatePage,
    Draft,
    Edit,
    NewTranslation,
    PageView,
    PublicPage,
    TranslationView,
)
from app.modules.identity.models import AuditLog, User, now
from app.modules.identity.security import AuthError
from app.modules.identity.service import require_permission

PERMISSIONS = [
    "cms.page." + action for action in ("view", "create", "update", "publish", "archive")
]


def view(db: Session, page: Page, translations: list[Translation] | None = None) -> PageView:
    rows = (
        translations
        if translations is not None
        else db.scalars(
            select(Translation).where(Translation.page_id == page.id).order_by(Translation.locale)
        )
    )
    return PageView(
        id=page.id,
        slug=page.slug,
        translations=[
            TranslationView(
                id=t.id,
                locale=t.locale,
                state=t.state,
                version=t.version,
                published_revision_id=t.published_revision_id,
                title=t.draft_title,
                body=t.draft_body,
                seo_title=t.draft_seo_title,
                seo_description=t.draft_seo_description,
            )
            for t in rows
        ],
    )


def snapshot(page: Page, t: Translation, r: Revision) -> PublicPage:
    return PublicPage(
        id=page.id,
        slug=page.slug,
        locale=t.locale,
        revision_id=r.id,
        published_at=r.created_at,
        title=r.title,
        body=r.body,
        seo_title=r.seo_title,
        seo_description=r.seo_description,
    )


def save_draft(t: Translation, data: Draft) -> None:
    t.draft_title, t.draft_body = data.title, data.body
    t.draft_seo_title, t.draft_seo_description = data.seo_title, data.seo_description


def record(
    db: Session,
    actor: User,
    org: UUID,
    resource: UUID,
    action: str,
    request_id: str,
    version: int,
    reason: str = "",
) -> None:
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=resource,
            action="cms.page." + action,
            request_id=request_id,
            resource_version=version,
            reason=reason or None,
            changed_fields="title,body,seo_title,seo_description"
            if action in {"created", "updated", "locale_added"}
            else "state,published_revision_id",
        )
    )


def commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("content_conflict", 409) from exc


def create(db: Session, org: UUID, actor: User, data: CreatePage, request_id: str) -> PageView:
    require_permission(db, actor, org, "cms.page.create")
    page = Page(organization_id=org, slug=data.slug)
    db.add(page)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("content_conflict", 409) from exc
    t = Translation(page_id=page.id, organization_id=org, locale=data.locale)
    save_draft(t, data)
    db.add(t)
    record(db, actor, org, page.id, "created", request_id, 1)
    commit(db)
    return view(db, page)


def add_locale(
    db: Session, org: UUID, page_id: UUID, actor: User, data: NewTranslation, request_id: str
) -> PageView:
    require_permission(db, actor, org, "cms.page.update")
    page = repository.page(db, org, page_id)
    t = Translation(page_id=page.id, organization_id=org, locale=data.locale)
    save_draft(t, data)
    db.add(t)
    record(db, actor, org, page.id, "locale_added", request_id, 1)
    commit(db)
    return view(db, page)


def mutate(
    db: Session,
    org: UUID,
    page_id: UUID,
    locale: str,
    actor: User,
    data: Edit | Command,
    action: str,
    request_id: str,
) -> PageView:
    permission = action if action in {"publish", "archive"} else "update"
    require_permission(db, actor, org, "cms.page." + permission)
    page = repository.page(db, org, page_id)
    t = repository.translation(db, org, page_id, locale)
    if t.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    if action == "update" and isinstance(data, Edit):
        if t.state == "archived":
            raise AuthError("invalid_transition", 409)
        save_draft(t, data)
    elif action == "publish":
        if t.state == "archived":
            raise AuthError("invalid_transition", 409)
        r = Revision(
            translation_id=t.id,
            organization_id=org,
            revision_number=t.version,
            title=t.draft_title,
            body=t.draft_body,
            seo_title=t.draft_seo_title,
            seo_description=t.draft_seo_description,
            actor_user_id=actor.id,
        )
        db.add(r)
        db.flush()
        t.published_revision_id, t.state = r.id, "published"
    elif action == "archive":
        if not isinstance(data, Command) or not data.reason or t.state == "archived":
            raise AuthError("invalid_transition", 409)
        t.published_revision_id, t.state = None, "archived"
    elif action == "restore":
        if t.state != "archived":
            raise AuthError("invalid_transition", 409)
        t.state = "draft"
    else:
        if action != "update":
            raise AuthError("invalid_request", 400)
    t.version += 1
    page.updated_at = now()
    record(
        db,
        actor,
        org,
        page.id,
        {"update": "updated", "publish": "published", "archive": "archived", "restore": "restored"}[
            action
        ],
        request_id,
        t.version,
        data.reason if isinstance(data, Command) else "",
    )
    commit(db)
    return view(db, page)
