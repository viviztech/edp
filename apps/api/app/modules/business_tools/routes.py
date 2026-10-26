from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse

from app.modules.business_tools import schemas as s
from app.modules.business_tools import service
from app.modules.business_tools.models import CatalogueItem, CustomerContact, CustomerTask
from app.modules.identity.routes import DB, Principal

router = APIRouter(
    prefix="/api/v1/business-tools/organizations/{org}/profiles/{profile_id}",
    tags=["business-tools"],
)
public_router = APIRouter(prefix="/api/v1/public/business-tools", tags=["public-business-tools"])
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0, le=10000)]


@router.get("/card", response_model=s.CardView | None)
def card(org: UUID, profile_id: UUID, db: DB, identity: Principal) -> s.CardView | None:
    row = service.card(db, org, identity[0], profile_id)
    return s.CardView.model_validate(row) if row else None


@router.post("/card", response_model=s.CardView)
def save_card(
    org: UUID, profile_id: UUID, data: s.SaveCard, request: Request, db: DB, identity: Principal
) -> s.CardView:
    return s.CardView.model_validate(
        service.save_card(db, org, identity[0], profile_id, data, request.state.request_id)
    )


@router.post("/card/sharing", response_model=s.CardView)
def share_card(
    org: UUID, profile_id: UUID, data: s.Sharing, request: Request, db: DB, identity: Principal
) -> s.CardView:
    return s.CardView.model_validate(
        service.share_card(db, org, identity[0], profile_id, data, request.state.request_id)
    )


def artifact(content: str, filename: str) -> HTMLResponse:
    return HTMLResponse(
        content,
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; "
            "base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/card/artifact", response_class=HTMLResponse)
def download_card(
    org: UUID, profile_id: UUID, request: Request, db: DB, identity: Principal
) -> HTMLResponse:
    return artifact(
        service.card_artifact(db, org, identity[0], profile_id, request.state.request_id),
        "business-card.html",
    )


@router.get("/catalogue", response_model=s.CataloguePage)
def catalogue(
    org: UUID, profile_id: UUID, db: DB, identity: Principal, limit: Limit = 25, offset: Offset = 0
) -> s.CataloguePage:
    return service.catalogue(db, org, identity[0], profile_id, limit, offset)


@router.post("/catalogue/sharing", response_model=s.CatalogueView)
def share_catalogue(
    org: UUID, profile_id: UUID, data: s.Sharing, request: Request, db: DB, identity: Principal
) -> s.CatalogueView:
    return s.CatalogueView.model_validate(
        service.share_catalogue(db, org, identity[0], profile_id, data, request.state.request_id)
    )


@router.post("/catalogue/items", response_model=s.CatalogueItemView, status_code=201)
def create_item(
    org: UUID,
    profile_id: UUID,
    data: s.CreateCatalogueItem,
    request: Request,
    db: DB,
    identity: Principal,
) -> s.CatalogueItemView:
    return s.CatalogueItemView.model_validate(
        service.save_item(db, org, identity[0], profile_id, data, request.state.request_id)
    )


@router.post("/catalogue/items/{identifier}/update", response_model=s.CatalogueItemView)
def update_item(
    org: UUID,
    profile_id: UUID,
    identifier: UUID,
    data: s.UpdateCatalogueItem,
    request: Request,
    db: DB,
    identity: Principal,
) -> s.CatalogueItemView:
    return s.CatalogueItemView.model_validate(
        service.save_item(
            db, org, identity[0], profile_id, data, request.state.request_id, identifier
        )
    )


@router.get("/catalogue/items/{identifier}", response_model=s.CatalogueItemView)
def item(
    org: UUID, profile_id: UUID, identifier: UUID, db: DB, identity: Principal
) -> s.CatalogueItemView:
    return s.CatalogueItemView.model_validate(
        service.owned_resource(db, CatalogueItem, org, identity[0], profile_id, identifier)
    )


@router.get("/quotes", response_model=s.QuotationPage)
def quotes(
    org: UUID, profile_id: UUID, db: DB, identity: Principal, limit: Limit = 25, offset: Offset = 0
) -> s.QuotationPage:
    return service.quotes(db, org, identity[0], profile_id, limit, offset)


@router.post("/quotes", response_model=s.QuotationView, status_code=201)
def create_quote(
    org: UUID,
    profile_id: UUID,
    data: s.CreateQuotation,
    request: Request,
    db: DB,
    identity: Principal,
) -> s.QuotationView:
    return service.save_quote(db, org, identity[0], profile_id, data, request.state.request_id)


@router.get("/quotes/{identifier}", response_model=s.QuotationView)
def quote(
    org: UUID, profile_id: UUID, identifier: UUID, db: DB, identity: Principal
) -> s.QuotationView:
    return service.quote(db, org, identity[0], profile_id, identifier)


@router.post("/quotes/{identifier}/update", response_model=s.QuotationView)
def update_quote(
    org: UUID,
    profile_id: UUID,
    identifier: UUID,
    data: s.UpdateQuotation,
    request: Request,
    db: DB,
    identity: Principal,
) -> s.QuotationView:
    return service.save_quote(
        db, org, identity[0], profile_id, data, request.state.request_id, identifier
    )


@router.post("/quotes/{identifier}/issue", response_model=s.QuotationView)
def issue_quote(
    org: UUID,
    profile_id: UUID,
    identifier: UUID,
    data: s.VersionCommand,
    request: Request,
    db: DB,
    identity: Principal,
) -> s.QuotationView:
    return service.issue_quote(
        db, org, identity[0], profile_id, identifier, data, request.state.request_id
    )


@router.get("/quotes/{identifier}/artifact", response_class=HTMLResponse)
def download_quote(
    org: UUID, profile_id: UUID, identifier: UUID, request: Request, db: DB, identity: Principal
) -> HTMLResponse:
    return artifact(
        service.quote_artifact(
            db, org, identity[0], profile_id, identifier, request.state.request_id
        ),
        "quotation.html",
    )


@router.get("/contacts", response_model=s.CustomerContactPage)
def contacts(
    org: UUID,
    profile_id: UUID,
    db: DB,
    identity: Principal,
    limit: Limit = 25,
    offset: Offset = 0,
    status: Literal["lead", "customer", "archived"] | None = None,
    search: Annotated[str | None, Query(min_length=1, max_length=160)] = None,
) -> s.CustomerContactPage:
    return service.contacts(db, org, identity[0], profile_id, limit, offset, status, search)


@router.post("/contacts", response_model=s.CustomerContactView, status_code=201)
def create_contact(
    org: UUID,
    profile_id: UUID,
    data: s.CreateContact,
    request: Request,
    db: DB,
    identity: Principal,
) -> s.CustomerContactView:
    return s.CustomerContactView.model_validate(
        service.save_contact(db, org, identity[0], profile_id, data, request.state.request_id)
    )


@router.post("/contacts/{identifier}/update", response_model=s.CustomerContactView)
def update_contact(
    org: UUID,
    profile_id: UUID,
    identifier: UUID,
    data: s.UpdateContact,
    request: Request,
    db: DB,
    identity: Principal,
) -> s.CustomerContactView:
    return s.CustomerContactView.model_validate(
        service.save_contact(
            db, org, identity[0], profile_id, data, request.state.request_id, identifier
        )
    )


@router.get("/contacts/{identifier}", response_model=s.CustomerContactView)
def contact(
    org: UUID, profile_id: UUID, identifier: UUID, db: DB, identity: Principal
) -> s.CustomerContactView:
    return s.CustomerContactView.model_validate(
        service.owned_resource(db, CustomerContact, org, identity[0], profile_id, identifier)
    )


@router.get("/tasks", response_model=s.CustomerTaskPage)
def tasks(
    org: UUID,
    profile_id: UUID,
    db: DB,
    identity: Principal,
    limit: Limit = 25,
    offset: Offset = 0,
    contact_id: UUID | None = None,
    status: Literal["pending", "completed", "cancelled"] | None = None,
) -> s.CustomerTaskPage:
    return service.tasks(db, org, identity[0], profile_id, limit, offset, contact_id, status)


@router.post("/tasks", response_model=s.CustomerTaskView, status_code=201)
def create_task(
    org: UUID, profile_id: UUID, data: s.CreateTask, request: Request, db: DB, identity: Principal
) -> s.CustomerTaskView:
    return s.CustomerTaskView.model_validate(
        service.save_task(db, org, identity[0], profile_id, data, request.state.request_id)
    )


@router.post("/tasks/{identifier}/update", response_model=s.CustomerTaskView)
def update_task(
    org: UUID,
    profile_id: UUID,
    identifier: UUID,
    data: s.UpdateTask,
    request: Request,
    db: DB,
    identity: Principal,
) -> s.CustomerTaskView:
    return s.CustomerTaskView.model_validate(
        service.save_task(
            db, org, identity[0], profile_id, data, request.state.request_id, identifier
        )
    )


@router.get("/tasks/{identifier}", response_model=s.CustomerTaskView)
def task(
    org: UUID, profile_id: UUID, identifier: UUID, db: DB, identity: Principal
) -> s.CustomerTaskView:
    return s.CustomerTaskView.model_validate(
        service.owned_resource(db, CustomerTask, org, identity[0], profile_id, identifier)
    )


@router.get("/history", response_model=s.ToolHistoryPage)
def history(
    org: UUID,
    profile_id: UUID,
    db: DB,
    identity: Principal,
    limit: Limit = 25,
    offset: Offset = 0,
    kind: s.HistoryKind | None = None,
    resource_id: UUID | None = None,
) -> s.ToolHistoryPage:
    return service.history(db, org, identity[0], profile_id, limit, offset, kind, resource_id)


@public_router.get("/cards/{share}", response_model=s.PublicCard)
def public_card(share: UUID, db: DB) -> s.PublicCard:
    return service.public_card(db, share)


@public_router.get("/catalogues/{share}", response_model=s.PublicCatalogue)
def public_catalogue(
    share: UUID, db: DB, limit: Limit = 25, offset: Offset = 0
) -> s.PublicCatalogue:
    return service.public_catalogue(db, share, limit, offset)
