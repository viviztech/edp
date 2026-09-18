from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response
from sqlalchemy import select

from app.modules.cms import repository, service
from app.modules.cms.models import Page, Revision, Translation
from app.modules.cms.schemas import (
    Command,
    CreatePage,
    Edit,
    History,
    Locale,
    NewTranslation,
    PageList,
    PageView,
    PublicList,
    PublicPage,
)
from app.modules.identity.routes import DB, Principal
from app.modules.identity.security import AuthError
from app.modules.identity.service import require_permission

router = APIRouter(prefix="/api/v1", tags=["cms"])
STAFF = "/cms/organizations/{org}/pages"
PUBLIC = "/public/organizations/{org}/pages"
Limit = Annotated[int, Query(ge=1, le=100)]


@router.post(STAFF, response_model=PageView, status_code=201)
def create(org: UUID, data: CreatePage, request: Request, db: DB, identity: Principal) -> PageView:
    return service.create(db, org, identity[0], data, request.state.request_id)


@router.get(STAFF, response_model=PageList)
def pages(
    org: UUID, db: DB, identity: Principal, cursor: UUID | None = None, limit: Limit = 25
) -> PageList:
    require_permission(db, identity[0], org, "cms.page.view")
    query = select(Page).where(Page.organization_id == org)
    if cursor:
        query = query.where(Page.id > cursor)
    rows = list(db.scalars(query.order_by(Page.id).limit(limit + 1)))
    grouped: dict[UUID, list[Translation]] = {}
    for translation in db.scalars(
        select(Translation)
        .where(Translation.page_id.in_([p.id for p in rows[:limit]]))
        .order_by(Translation.locale)
    ):
        grouped.setdefault(translation.page_id, []).append(translation)
    return PageList(
        items=[service.view(db, p, grouped.get(p.id, [])) for p in rows[:limit]],
        next_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )


@router.get(STAFF + "/{page_id}", response_model=PageView)
def detail(org: UUID, page_id: UUID, db: DB, identity: Principal) -> PageView:
    require_permission(db, identity[0], org, "cms.page.view")
    return service.view(db, repository.page(db, org, page_id))


@router.post(STAFF + "/{page_id}/translations", response_model=PageView, status_code=201)
def add_locale(
    org: UUID, page_id: UUID, data: NewTranslation, request: Request, db: DB, identity: Principal
) -> PageView:
    return service.add_locale(db, org, page_id, identity[0], data, request.state.request_id)


@router.patch(STAFF + "/{page_id}/translations/{locale}", response_model=PageView)
def edit(
    org: UUID,
    page_id: UUID,
    locale: Locale,
    data: Edit,
    request: Request,
    db: DB,
    identity: Principal,
) -> PageView:
    return service.mutate(
        db, org, page_id, locale, identity[0], data, "update", request.state.request_id
    )


@router.post(STAFF + "/{page_id}/translations/{locale}/publish", response_model=PageView)
def publish(
    org: UUID,
    page_id: UUID,
    locale: Locale,
    data: Command,
    request: Request,
    db: DB,
    identity: Principal,
) -> PageView:
    return service.mutate(
        db, org, page_id, locale, identity[0], data, "publish", request.state.request_id
    )


@router.post(STAFF + "/{page_id}/translations/{locale}/archive", response_model=PageView)
def archive(
    org: UUID,
    page_id: UUID,
    locale: Locale,
    data: Command,
    request: Request,
    db: DB,
    identity: Principal,
) -> PageView:
    return service.mutate(
        db, org, page_id, locale, identity[0], data, "archive", request.state.request_id
    )


@router.post(STAFF + "/{page_id}/translations/{locale}/restore", response_model=PageView)
def restore(
    org: UUID,
    page_id: UUID,
    locale: Locale,
    data: Command,
    request: Request,
    db: DB,
    identity: Principal,
) -> PageView:
    return service.mutate(
        db, org, page_id, locale, identity[0], data, "restore", request.state.request_id
    )


@router.get(STAFF + "/{page_id}/translations/{locale}/preview", response_model=PageView)
def preview(
    org: UUID,
    page_id: UUID,
    locale: Locale,
    request: Request,
    response: Response,
    db: DB,
    identity: Principal,
) -> PageView:
    require_permission(db, identity[0], org, "cms.page.view")
    page = repository.page(db, org, page_id)
    t = repository.translation(db, org, page_id, locale)
    service.record(db, identity[0], org, page.id, "previewed", request.state.request_id, t.version)
    db.commit()
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return service.view(db, page)


@router.get(STAFF + "/{page_id}/translations/{locale}/revisions", response_model=History)
def history(
    org: UUID,
    page_id: UUID,
    locale: Locale,
    db: DB,
    identity: Principal,
    cursor: UUID | None = None,
    limit: Limit = 25,
) -> History:
    require_permission(db, identity[0], org, "cms.page.view")
    page = repository.page(db, org, page_id)
    t = repository.translation(db, org, page_id, locale)
    query = select(Revision).where(Revision.translation_id == t.id)
    if cursor:
        query = query.where(Revision.id > cursor)
    rows = list(db.scalars(query.order_by(Revision.id).limit(limit + 1)))
    return History(
        items=[service.snapshot(page, t, r) for r in rows[:limit]],
        next_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )


@router.get(PUBLIC, response_model=PublicList)
def public_list(
    org: UUID, db: DB, locale: Locale = "en", cursor: UUID | None = None, limit: Limit = 25
) -> PublicList:
    query = (
        select(Page, Translation, Revision)
        .join(Translation, Translation.page_id == Page.id)
        .join(Revision, Revision.id == Translation.published_revision_id)
        .where(
            Page.organization_id == org,
            Translation.locale == locale,
            Translation.state == "published",
        )
    )
    if cursor:
        query = query.where(Page.id > cursor)
    rows = list(db.execute(query.order_by(Page.id).limit(limit + 1)))
    return PublicList(
        items=[service.snapshot(p, t, r) for p, t, r in rows[:limit]],
        next_cursor=rows[limit - 1][0].id if len(rows) > limit else None,
    )


@router.get(
    PUBLIC + "/{slug}",
    response_model=PublicPage,
    responses={304: {"description": "Published revision unchanged"}},
)
def public_page(
    org: UUID, slug: str, request: Request, response: Response, db: DB, locale: Locale = "en"
) -> PublicPage | Response:
    row = db.execute(
        select(Page, Translation, Revision)
        .join(Translation, Translation.page_id == Page.id)
        .join(Revision, Revision.id == Translation.published_revision_id)
        .where(
            Page.organization_id == org,
            Page.slug == slug,
            Translation.locale == locale,
            Translation.state == "published",
        )
    ).first()
    if row is None:
        raise AuthError("not_found", 404)
    data = service.snapshot(*row)
    headers = {
        "ETag": '"' + str(data.revision_id) + '"',
        "Cache-Control": "public, max-age=0, must-revalidate",
    }
    if request.headers.get("If-None-Match") == headers["ETag"]:
        return Response(status_code=304, headers=headers)
    response.headers.update(headers)
    return data
