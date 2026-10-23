from secrets import compare_digest
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response
from sqlalchemy import select

from app.core.config import get_settings
from app.modules.cms import editorial_service, repository, service
from app.modules.cms.asset_service import create as create_asset
from app.modules.cms.asset_service import publish as publish_asset
from app.modules.cms.asset_service import scan_result as asset_scan_result
from app.modules.cms.asset_service import view as asset_view
from app.modules.cms.enquiry_service import create as create_enquiry
from app.modules.cms.enquiry_service import list_staff as list_enquiries
from app.modules.cms.models import Asset, EditorialEntry, Page, Revision, Translation
from app.modules.cms.schemas import (
    AssetCreate,
    AssetList,
    AssetScanResult,
    AssetView,
    Command,
    CreatePage,
    Edit,
    EditorialCommand,
    EditorialDraft,
    EditorialEdit,
    EditorialKind,
    EditorialList,
    EditorialView,
    EnquiryCreate,
    EnquiryReceipt,
    EnquiryView,
    History,
    Locale,
    NewTranslation,
    PageList,
    PageView,
    PublicEditorialList,
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


EDITORIAL_STAFF = "/cms/organizations/{org}/editorial"
EDITORIAL_PUBLIC = "/public/organizations/{org}/editorial"


@router.post(EDITORIAL_STAFF, response_model=EditorialView, status_code=201)
def editorial_create(
    org: UUID, data: EditorialDraft, request: Request, db: DB, identity: Principal
) -> EditorialView:
    return editorial_service.create(db, org, identity[0], data, request.state.request_id)


@router.get(EDITORIAL_STAFF, response_model=EditorialList)
def editorial_list(
    org: UUID,
    db: DB,
    identity: Principal,
    kind: EditorialKind | None = None,
    locale: Locale | None = None,
    cursor: UUID | None = None,
    limit: Limit = 25,
) -> EditorialList:
    require_permission(db, identity[0], org, "cms.editorial.view")
    q = select(EditorialEntry).where(EditorialEntry.organization_id == org)
    if kind:
        q = q.where(EditorialEntry.kind == kind)
    if locale:
        q = q.where(EditorialEntry.locale == locale)
    if cursor:
        q = q.where(EditorialEntry.id > cursor)
    rows = list(db.scalars(q.order_by(EditorialEntry.id).limit(limit + 1)))
    return EditorialList(
        items=[editorial_service.view(e) for e in rows[:limit]],
        next_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )


@router.get(EDITORIAL_STAFF + "/{entry_id}", response_model=EditorialView)
def editorial_detail(org: UUID, entry_id: UUID, db: DB, identity: Principal) -> EditorialView:
    require_permission(db, identity[0], org, "cms.editorial.view")
    return editorial_service.view(editorial_service.get(db, org, entry_id))


@router.patch(EDITORIAL_STAFF + "/{entry_id}", response_model=EditorialView)
def editorial_edit(
    org: UUID, entry_id: UUID, data: EditorialEdit, request: Request, db: DB, identity: Principal
) -> EditorialView:
    return editorial_service.mutate(
        db, org, entry_id, identity[0], data, "update", request.state.request_id
    )


@router.post(EDITORIAL_STAFF + "/{entry_id}/publish", response_model=EditorialView)
def editorial_publish(
    org: UUID, entry_id: UUID, data: EditorialCommand, request: Request, db: DB, identity: Principal
) -> EditorialView:
    return editorial_service.mutate(
        db, org, entry_id, identity[0], data, "publish", request.state.request_id
    )


@router.post(EDITORIAL_STAFF + "/{entry_id}/archive", response_model=EditorialView)
def editorial_archive(
    org: UUID, entry_id: UUID, data: EditorialCommand, request: Request, db: DB, identity: Principal
) -> EditorialView:
    return editorial_service.mutate(
        db, org, entry_id, identity[0], data, "archive", request.state.request_id
    )


@router.post(EDITORIAL_STAFF + "/{entry_id}/restore", response_model=EditorialView)
def editorial_restore(
    org: UUID, entry_id: UUID, data: EditorialCommand, request: Request, db: DB, identity: Principal
) -> EditorialView:
    return editorial_service.mutate(
        db, org, entry_id, identity[0], data, "restore", request.state.request_id
    )


@router.get(EDITORIAL_PUBLIC, response_model=PublicEditorialList)
def editorial_public_list(
    org: UUID,
    db: DB,
    kind: EditorialKind,
    locale: Locale = "en",
    cursor: UUID | None = None,
    limit: Limit = 25,
) -> PublicEditorialList:
    rows = editorial_service.public(db, org, kind, locale, cursor, limit)
    return PublicEditorialList(
        items=[editorial_service.view(e) for e in rows[:limit]],
        next_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )


@router.get(EDITORIAL_PUBLIC + "/{kind}/{slug}", response_model=EditorialView)
def editorial_public_detail(
    org: UUID, kind: EditorialKind, slug: str, db: DB, locale: Locale = "en"
) -> EditorialView:
    e = db.scalar(
        select(EditorialEntry).where(
            EditorialEntry.organization_id == org,
            EditorialEntry.kind == kind,
            EditorialEntry.slug == slug,
            EditorialEntry.locale == locale,
            EditorialEntry.state == "published",
        )
    )
    if not e:
        raise AuthError("not_found", 404)
    return editorial_service.view(e)


ASSET_STAFF = "/cms/organizations/{org}/assets"
ASSET_PUBLIC = "/public/organizations/{org}/assets"


@router.post(ASSET_STAFF, response_model=AssetView, status_code=201)
def asset_create(
    org: UUID, data: AssetCreate, request: Request, db: DB, identity: Principal
) -> AssetView:
    return create_asset(db, org, identity[0], data, request.state.request_id)


@router.get(ASSET_STAFF, response_model=AssetList)
def asset_list(
    org: UUID, db: DB, identity: Principal, cursor: UUID | None = None, limit: Limit = 25
) -> AssetList:
    require_permission(db, identity[0], org, "cms.asset.view")
    q = select(Asset).where(Asset.organization_id == org)
    q = q.where(Asset.id > cursor) if cursor else q
    rows = list(db.scalars(q.order_by(Asset.id).limit(limit + 1)))
    return AssetList(
        items=[asset_view(a) for a in rows[:limit]],
        next_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )


@router.post(ASSET_STAFF + "/{asset_id}/publish", response_model=AssetView)
def asset_publish(
    org: UUID, asset_id: UUID, request: Request, db: DB, identity: Principal
) -> AssetView:
    return publish_asset(db, org, asset_id, identity[0], request.state.request_id)


@router.get(ASSET_PUBLIC, response_model=AssetList)
def asset_public(org: UUID, db: DB, cursor: UUID | None = None, limit: Limit = 25) -> AssetList:
    q = select(Asset).where(
        Asset.organization_id == org, Asset.visibility == "public", Asset.scan_status == "clean"
    )
    q = q.where(Asset.id > cursor) if cursor else q
    rows = list(db.scalars(q.order_by(Asset.id).limit(limit + 1)))
    return AssetList(
        items=[asset_view(a) for a in rows[:limit]],
        next_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )


@router.post("/internal/cms/organizations/{org}/assets/{asset_id}/scan", response_model=AssetView)
def asset_scan(
    org: UUID, asset_id: UUID, data: AssetScanResult, request: Request, db: DB
) -> AssetView:
    configured = get_settings().asset_scanner_key
    supplied = request.headers.get("X-Asset-Scanner-Key", "")
    if not configured or not compare_digest(supplied, configured.get_secret_value()):
        raise AuthError("invalid_client", 403)
    return asset_scan_result(db, org, asset_id, data.clean, data.reason, request.state.request_id)


@router.post(
    "/public/organizations/{org}/enquiries", response_model=EnquiryReceipt, status_code=202
)
def enquiry_create(org: UUID, data: EnquiryCreate, request: Request, db: DB) -> EnquiryReceipt:
    return create_enquiry(db, org, data, request.state.request_id)


@router.get("/cms/organizations/{org}/enquiries", response_model=list[EnquiryView])
def enquiry_list(org: UUID, db: DB, identity: Principal, limit: Limit = 25) -> list[EnquiryView]:
    return list_enquiries(db, org, identity[0], limit)
