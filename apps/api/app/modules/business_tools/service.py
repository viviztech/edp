import hashlib
import html
import json
from collections.abc import Callable
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.business_tools import schemas as s
from app.modules.business_tools.models import (
    BusinessCard,
    Catalogue,
    CatalogueItem,
    CustomerContact,
    CustomerTask,
    Quotation,
    QuotationLine,
    ToolCommand,
    ToolHistory,
)
from app.modules.businesses.models import BusinessProfile
from app.modules.businesses.service import owned_enrollment
from app.modules.identity.models import AuditLog, User, now
from app.modules.identity.security import AuthError
from app.modules.programs.models import Enrollment, Participant

MAX_TOTAL = Decimal("999999999999.99")


def owner(
    db: Session, org: UUID, actor: User, profile: UUID, lock: bool = False
) -> BusinessProfile:
    query = select(BusinessProfile).where(
        BusinessProfile.id == profile, BusinessProfile.organization_id == org
    )
    row = db.scalar(query.with_for_update() if lock else query)
    if row is None:
        # Keep the participant permission response consistent for missing and existing profiles.
        from app.modules.identity.service import require_permission

        require_permission(db, actor, org, "participant.self")
        raise AuthError("not_found", 404)
    enrollment = owned_enrollment(db, org, actor, row.enrollment_id)
    if lock:
        db.execute(select(Enrollment).where(Enrollment.id == enrollment.id).with_for_update())
        db.execute(
            select(Participant).where(Participant.id == enrollment.participant_id).with_for_update()
        )
        # Recheck after locking the lifecycle rows, including concurrently withdrawn enrollments.
        db.expire(enrollment)
        owned_enrollment(db, org, actor, row.enrollment_id)
    return row


def resource[R: (BusinessCard, Catalogue, CatalogueItem, Quotation, CustomerContact, CustomerTask)](
    db: Session, model: type[R], org: UUID, profile: UUID, identifier: UUID
) -> R:
    row = db.scalar(
        select(model).where(
            model.id == identifier, model.organization_id == org, model.profile_id == profile
        )
    )
    if row is None:
        raise AuthError("not_found", 404)
    return row


def owned_resource[
    R: (BusinessCard, Catalogue, CatalogueItem, Quotation, CustomerContact, CustomerTask)
](db: Session, model: type[R], org: UUID, actor: User, profile: UUID, identifier: UUID) -> R:
    owner(db, org, actor, profile)
    return resource(db, model, org, profile, identifier)


def version[R: (BusinessCard, Catalogue, CatalogueItem, Quotation, CustomerContact, CustomerTask)](
    row: R, expected: int
) -> None:
    if row.version != expected:
        raise AuthError("version_conflict", 409)


def safe_history[
    R: (BusinessCard, Catalogue, CatalogueItem, Quotation, CustomerContact, CustomerTask)
](
    db: Session, actor: User, row: R, kind: str, action: str, fields: list[str], request_id: str
) -> None:
    db.add(
        ToolHistory(
            organization_id=row.organization_id,
            profile_id=row.profile_id,
            kind=kind,
            resource_id=row.id,
            version=row.version,
            action=action,
            changed_fields=fields,
        )
    )
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=row.organization_id,
            resource_id=row.id,
            action=f"business_tool.{kind}_{action}",
            resource_version=row.version,
            changed_fields=",".join(fields),
            request_id=request_id,
        )
    )


def command[R: (BusinessCard, Catalogue, CatalogueItem, Quotation, CustomerContact, CustomerTask)](
    db: Session,
    org: UUID,
    actor: User,
    profile_id: UUID,
    operation: str,
    data: s.Command,
    model: type[R],
    kind: str,
    action: str,
    request_id: str,
    apply: Callable[[BusinessProfile], R],
) -> R:
    profile = owner(db, org, actor, profile_id, lock=True)
    digest = hashlib.sha256(
        json.dumps(
            {"operation": operation, "input": data.model_dump(mode="json")},
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    previous = db.scalar(
        select(ToolCommand).where(
            ToolCommand.organization_id == org,
            ToolCommand.profile_id == profile_id,
            ToolCommand.request_id == data.request_id,
        )
    )
    if previous:
        if previous.digest != digest or previous.operation != operation:
            raise AuthError("request_conflict", 409)
        return resource(db, model, org, profile_id, previous.resource_id)
    try:
        row = apply(profile)
        db.flush()
        fields = sorted(set(data.model_fields_set) - {"request_id", "expected_version"})
        safe_history(db, actor, row, kind, action, fields, request_id)
        db.add(
            ToolCommand(
                organization_id=org,
                profile_id=profile_id,
                request_id=data.request_id,
                operation=operation,
                digest=digest,
                resource_id=row.id,
            )
        )
        db.commit()
        return row
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("write_conflict", 409) from exc


def apply_fields[
    R: (BusinessCard, Catalogue, CatalogueItem, Quotation, CustomerContact, CustomerTask)
](row: R, data: BaseModel, fields: type[BaseModel]) -> None:
    for field in fields.model_fields:
        setattr(row, field, getattr(data, field))


def card(db: Session, org: UUID, actor: User, profile: UUID) -> BusinessCard | None:
    owner(db, org, actor, profile)
    return db.scalar(
        select(BusinessCard).where(
            BusinessCard.profile_id == profile, BusinessCard.organization_id == org
        )
    )


def save_card(
    db: Session, org: UUID, actor: User, profile: UUID, data: s.SaveCard, request_id: str
) -> BusinessCard:
    def apply(_: BusinessProfile) -> BusinessCard:
        row = db.scalar(
            select(BusinessCard).where(
                BusinessCard.profile_id == profile, BusinessCard.organization_id == org
            )
        )
        if row:
            version(row, data.expected_version)
            apply_fields(row, data, s.CardFields)
            row.version += 1
            row.published = False
        else:
            if data.expected_version != 0:
                raise AuthError("version_conflict", 409)
            row = BusinessCard(
                organization_id=org,
                profile_id=profile,
                **data.model_dump(include=set(s.CardFields.model_fields)),
            )
            db.add(row)
        return row

    return command(
        db, org, actor, profile, "card.save", data, BusinessCard, "card", "saved", request_id, apply
    )


def share_card(
    db: Session, org: UUID, actor: User, profile: UUID, data: s.Sharing, request_id: str
) -> BusinessCard:
    def apply(_: BusinessProfile) -> BusinessCard:
        row = db.scalar(
            select(BusinessCard).where(
                BusinessCard.profile_id == profile, BusinessCard.organization_id == org
            )
        )
        if row is None:
            raise AuthError("not_found", 404)
        version(row, data.expected_version)
        row.published = data.published
        row.version += 1
        return row

    return command(
        db,
        org,
        actor,
        profile,
        "card.sharing",
        data,
        BusinessCard,
        "card",
        "sharing_changed",
        request_id,
        apply,
    )


def catalogue_settings(db: Session, org: UUID, profile: UUID) -> Catalogue | None:
    return db.scalar(
        select(Catalogue).where(Catalogue.organization_id == org, Catalogue.profile_id == profile)
    )


def catalogue(
    db: Session, org: UUID, actor: User, profile: UUID, limit: int, offset: int
) -> s.CataloguePage:
    owner(db, org, actor, profile)
    settings = catalogue_settings(db, org, profile)
    items = db.scalars(
        select(CatalogueItem)
        .where(CatalogueItem.organization_id == org, CatalogueItem.profile_id == profile)
        .order_by(CatalogueItem.created_at.desc(), CatalogueItem.id)
        .limit(limit)
        .offset(offset)
    )
    return s.CataloguePage(
        settings=s.CatalogueView.model_validate(settings) if settings else None,
        items=[s.CatalogueItemView.model_validate(item) for item in items],
        limit=limit,
        offset=offset,
    )


def share_catalogue(
    db: Session, org: UUID, actor: User, profile: UUID, data: s.Sharing, request_id: str
) -> Catalogue:
    def apply(_: BusinessProfile) -> Catalogue:
        row = catalogue_settings(db, org, profile)
        if row:
            version(row, data.expected_version)
            row.version += 1
            row.published = data.published
        else:
            if data.expected_version != 0:
                raise AuthError("version_conflict", 409)
            row = Catalogue(organization_id=org, profile_id=profile, published=data.published)
            db.add(row)
        return row

    return command(
        db,
        org,
        actor,
        profile,
        "catalogue.sharing",
        data,
        Catalogue,
        "catalogue",
        "sharing_changed",
        request_id,
        apply,
    )


def capacity[R: (BusinessCard, Catalogue, CatalogueItem, Quotation, CustomerContact, CustomerTask)](
    db: Session, model: type[R], profile: UUID, maximum: int
) -> None:
    if (
        db.scalar(select(func.count()).select_from(model).where(model.profile_id == profile)) or 0
    ) >= maximum:
        raise AuthError("capacity_reached", 409)


def save_item(
    db: Session,
    org: UUID,
    actor: User,
    profile: UUID,
    data: s.CreateCatalogueItem | s.UpdateCatalogueItem,
    request_id: str,
    identifier: UUID | None = None,
) -> CatalogueItem:
    def apply(_: BusinessProfile) -> CatalogueItem:
        if identifier:
            assert isinstance(data, s.UpdateCatalogueItem)
            row = resource(db, CatalogueItem, org, profile, identifier)
            version(row, data.expected_version)
            apply_fields(row, data, s.CatalogueItemFields)
            row.version += 1
        else:
            capacity(db, CatalogueItem, profile, 500)
            row = CatalogueItem(
                organization_id=org,
                profile_id=profile,
                **data.model_dump(include=set(s.CatalogueItemFields.model_fields)),
            )
            db.add(row)
        settings = catalogue_settings(db, org, profile)
        if settings:
            settings.version += 1
            settings.published = False
        else:
            settings = Catalogue(organization_id=org, profile_id=profile, published=False)
            db.add(settings)
        db.flush()
        safe_history(
            db, actor, settings, "catalogue", "content_changed", ["items", "published"], request_id
        )
        return row

    return command(
        db,
        org,
        actor,
        profile,
        f"item.save:{identifier or 'new'}",
        data,
        CatalogueItem,
        "catalogue_item",
        "saved",
        request_id,
        apply,
    )


def public_owner(db: Session, org: UUID, profile_id: UUID) -> None:
    profile = db.get(BusinessProfile, profile_id)
    if profile is None:
        raise AuthError("not_found", 404)
    actor = db.scalar(
        select(User)
        .join(Participant, Participant.person_id == User.person_id)
        .join(Enrollment, Enrollment.participant_id == Participant.id)
        .where(Enrollment.id == profile.enrollment_id, User.status == "active")
    )
    if actor is None:
        raise AuthError("not_found", 404)
    try:
        owner(db, org, actor, profile_id)
    except AuthError as exc:
        raise AuthError("not_found", 404) from exc


def public_card(db: Session, share: UUID) -> s.PublicCard:
    row = db.scalar(
        select(BusinessCard).where(BusinessCard.share_id == share, BusinessCard.published.is_(True))
    )
    if row is None:
        raise AuthError("not_found", 404)
    public_owner(db, row.organization_id, row.profile_id)
    return s.PublicCard(
        share_id=row.share_id, **{field: getattr(row, field) for field in s.CardFields.model_fields}
    )


def public_catalogue(db: Session, share: UUID, limit: int, offset: int) -> s.PublicCatalogue:
    row = db.scalar(
        select(Catalogue).where(Catalogue.share_id == share, Catalogue.published.is_(True))
    )
    if row is None:
        raise AuthError("not_found", 404)
    public_owner(db, row.organization_id, row.profile_id)
    items = db.scalars(
        select(CatalogueItem)
        .where(
            CatalogueItem.organization_id == row.organization_id,
            CatalogueItem.profile_id == row.profile_id,
            CatalogueItem.available.is_(True),
        )
        .order_by(CatalogueItem.created_at, CatalogueItem.id)
        .limit(limit)
        .offset(offset)
    )
    return s.PublicCatalogue(
        share_id=share,
        limit=limit,
        offset=offset,
        items=[
            s.PublicCatalogueItem(
                **{field: getattr(item, field) for field in s.CatalogueItemFields.model_fields}
            )
            for item in items
        ],
    )


def quote_view(
    db: Session, row: Quotation, lines: list[QuotationLine] | None = None
) -> s.QuotationView:
    if lines is None:
        lines = list(
            db.scalars(
                select(QuotationLine)
                .where(
                    QuotationLine.quotation_id == row.id,
                    QuotationLine.profile_id == row.profile_id,
                    QuotationLine.organization_id == row.organization_id,
                )
                .order_by(QuotationLine.position)
            )
        )
    fields = {key: getattr(row, key) for key in s.QuotationView.model_fields if key != "lines"}
    return s.QuotationView(
        **fields, lines=[s.QuotationLineView.model_validate(line) for line in lines]
    )


def quote(db: Session, org: UUID, actor: User, profile: UUID, identifier: UUID) -> s.QuotationView:
    owner(db, org, actor, profile)
    return quote_view(db, resource(db, Quotation, org, profile, identifier))


def quotes(
    db: Session, org: UUID, actor: User, profile: UUID, limit: int, offset: int
) -> s.QuotationPage:
    owner(db, org, actor, profile)
    rows = list(
        db.scalars(
            select(Quotation)
            .where(Quotation.organization_id == org, Quotation.profile_id == profile)
            .order_by(Quotation.created_at.desc(), Quotation.id)
            .limit(limit)
            .offset(offset)
        )
    )
    grouped: dict[UUID, list[QuotationLine]] = {row.id: [] for row in rows}
    if grouped:
        for line in db.scalars(
            select(QuotationLine)
            .where(
                QuotationLine.organization_id == org,
                QuotationLine.profile_id == profile,
                QuotationLine.quotation_id.in_(grouped),
            )
            .order_by(QuotationLine.position)
        ):
            grouped[line.quotation_id].append(line)
    return s.QuotationPage(
        items=[quote_view(db, row, grouped[row.id]) for row in rows], limit=limit, offset=offset
    )


def quotation_lines(
    db: Session, org: UUID, profile: UUID, data: s.QuotationFields
) -> tuple[list[dict[str, object]], Decimal]:
    subtotal = Decimal("0.00")
    lines: list[dict[str, object]] = []
    for position, line in enumerate(data.lines):
        description = line.description
        if line.catalogue_item_id:
            item = resource(db, CatalogueItem, org, profile, line.catalogue_item_id)
            if (
                item.version != line.catalogue_version
                or not item.available
                or item.price is None
                or item.price != line.unit_price
                or item.currency != data.currency
            ):
                raise AuthError("catalogue_conflict", 409)
            description = item.name_en
            if item.name_ta:
                description = (description + " / " + item.name_ta)[:500]
        total = (line.quantity * line.unit_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        subtotal += total
        if subtotal > MAX_TOTAL:
            raise AuthError("quotation_total_out_of_range", 422)
        lines.append(
            {
                **line.model_dump(),
                "description": description,
                "position": position,
                "line_total": total,
            }
        )
    if data.discount > subtotal:
        raise AuthError("discount_exceeds_subtotal", 422)
    return lines, subtotal


def save_quote(
    db: Session,
    org: UUID,
    actor: User,
    profile: UUID,
    data: s.CreateQuotation | s.UpdateQuotation,
    request_id: str,
    identifier: UUID | None = None,
) -> s.QuotationView:
    def apply(parent: BusinessProfile) -> Quotation:
        lines, subtotal = quotation_lines(db, org, profile, data)
        fields = data.model_dump(include=set(s.QuotationFields.model_fields) - {"lines"})
        if identifier:
            assert isinstance(data, s.UpdateQuotation)
            row = resource(db, Quotation, org, profile, identifier)
            version(row, data.expected_version)
            if row.status != "draft":
                raise AuthError("quotation_immutable", 409)
            for key, value in fields.items():
                setattr(row, key, value)
            row.version += 1
            # Flush the parent once, after replacing its calculated totals as well as fields.
            # An intermediate ORM autoflush would consume the version before the totals update.
            with db.no_autoflush:
                db.execute(delete(QuotationLine).where(QuotationLine.quotation_id == row.id))
        else:
            capacity(db, Quotation, profile, 1000)
            row = Quotation(organization_id=org, profile_id=profile, **fields)
            db.add(row)
        row.business_name = parent.name
        row.subtotal, row.total = subtotal, subtotal - data.discount
        db.flush()
        for line in lines:
            db.add(
                QuotationLine(organization_id=org, profile_id=profile, quotation_id=row.id, **line)
            )
        return row

    row = command(
        db,
        org,
        actor,
        profile,
        f"quote.save:{identifier or 'new'}",
        data,
        Quotation,
        "quote",
        "saved",
        request_id,
        apply,
    )
    return quote_view(db, row)


def issue_quote(
    db: Session,
    org: UUID,
    actor: User,
    profile: UUID,
    identifier: UUID,
    data: s.VersionCommand,
    request_id: str,
) -> s.QuotationView:
    def apply(_: BusinessProfile) -> Quotation:
        row = resource(db, Quotation, org, profile, identifier)
        version(row, data.expected_version)
        if row.status != "draft":
            raise AuthError("quotation_immutable", 409)
        # Catalogue prices may change after draft save. Require explicit draft reconciliation.
        for line in db.scalars(select(QuotationLine).where(QuotationLine.quotation_id == row.id)):
            if line.catalogue_item_id:
                item = resource(db, CatalogueItem, org, profile, line.catalogue_item_id)
                if (
                    item.version != line.catalogue_version
                    or not item.available
                    or item.price != line.unit_price
                    or item.currency != row.currency
                ):
                    raise AuthError("catalogue_conflict", 409)
        row.status, row.issued_at = "issued", now()
        row.version += 1
        return row

    row = command(
        db,
        org,
        actor,
        profile,
        f"quote.issue:{identifier}",
        data,
        Quotation,
        "quote",
        "issued",
        request_id,
        apply,
    )
    return quote_view(db, row)


def contacts(
    db: Session,
    org: UUID,
    actor: User,
    profile: UUID,
    limit: int,
    offset: int,
    status: str | None,
    search: str | None,
) -> s.CustomerContactPage:
    owner(db, org, actor, profile)
    query = select(CustomerContact).where(
        CustomerContact.organization_id == org, CustomerContact.profile_id == profile
    )
    if status:
        query = query.where(CustomerContact.status == status)
    if search:
        query = query.where(
            CustomerContact.name.ilike(
                "%" + search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%",
                escape="\\",
            )
        )
    rows = db.scalars(
        query.order_by(CustomerContact.created_at.desc(), CustomerContact.id)
        .limit(limit)
        .offset(offset)
    )
    return s.CustomerContactPage(
        items=[s.CustomerContactView.model_validate(row) for row in rows],
        limit=limit,
        offset=offset,
    )


def save_contact(
    db: Session,
    org: UUID,
    actor: User,
    profile: UUID,
    data: s.CreateContact | s.UpdateContact,
    request_id: str,
    identifier: UUID | None = None,
) -> CustomerContact:
    def apply(_: BusinessProfile) -> CustomerContact:
        if identifier:
            assert isinstance(data, s.UpdateContact)
            row = resource(db, CustomerContact, org, profile, identifier)
            version(row, data.expected_version)
            if row.status == "archived" and data.status != "archived":
                raise AuthError("contact_archived", 409)
            apply_fields(row, data, s.CustomerContactFields)
            row.version += 1
        else:
            capacity(db, CustomerContact, profile, 2000)
            row = CustomerContact(
                organization_id=org,
                profile_id=profile,
                **data.model_dump(include=set(s.CustomerContactFields.model_fields)),
            )
            db.add(row)
        return row

    return command(
        db,
        org,
        actor,
        profile,
        f"contact.save:{identifier or 'new'}",
        data,
        CustomerContact,
        "contact",
        "saved",
        request_id,
        apply,
    )


def tasks(
    db: Session,
    org: UUID,
    actor: User,
    profile: UUID,
    limit: int,
    offset: int,
    contact_id: UUID | None,
    status: str | None,
) -> s.CustomerTaskPage:
    owner(db, org, actor, profile)
    query = select(CustomerTask).where(
        CustomerTask.organization_id == org, CustomerTask.profile_id == profile
    )
    if contact_id:
        resource(db, CustomerContact, org, profile, contact_id)
        query = query.where(CustomerTask.contact_id == contact_id)
    if status:
        query = query.where(CustomerTask.status == status)
    rows = db.scalars(
        query.order_by(CustomerTask.due_at, CustomerTask.id).limit(limit).offset(offset)
    )
    return s.CustomerTaskPage(
        items=[s.CustomerTaskView.model_validate(row) for row in rows], limit=limit, offset=offset
    )


def save_task(
    db: Session,
    org: UUID,
    actor: User,
    profile: UUID,
    data: s.CreateTask | s.UpdateTask,
    request_id: str,
    identifier: UUID | None = None,
) -> CustomerTask:
    def apply(_: BusinessProfile) -> CustomerTask:
        if identifier:
            assert isinstance(data, s.UpdateTask)
            row = resource(db, CustomerTask, org, profile, identifier)
            version(row, data.expected_version)
            if row.status != "pending":
                raise AuthError("task_settled", 409)
            apply_fields(row, data, s.TaskFields)
            row.status = data.status
            row.completed_at = now() if data.status == "completed" else None
            row.version += 1
        else:
            assert isinstance(data, s.CreateTask)
            contact = resource(db, CustomerContact, org, profile, data.contact_id)
            if contact.status == "archived":
                raise AuthError("contact_archived", 409)
            capacity(db, CustomerTask, profile, 5000)
            row = CustomerTask(
                organization_id=org,
                profile_id=profile,
                **data.model_dump(include=set(s.TaskFields.model_fields) | {"contact_id"}),
            )
            db.add(row)
        return row

    return command(
        db,
        org,
        actor,
        profile,
        f"task.save:{identifier or 'new'}",
        data,
        CustomerTask,
        "task",
        "saved",
        request_id,
        apply,
    )


def history(
    db: Session,
    org: UUID,
    actor: User,
    profile: UUID,
    limit: int,
    offset: int,
    kind: str | None,
    resource_id: UUID | None,
) -> s.ToolHistoryPage:
    owner(db, org, actor, profile)
    query = select(ToolHistory).where(
        ToolHistory.organization_id == org, ToolHistory.profile_id == profile
    )
    if kind:
        query = query.where(ToolHistory.kind == kind)
    if resource_id:
        query = query.where(ToolHistory.resource_id == resource_id)
    rows = db.scalars(
        query.order_by(ToolHistory.created_at.desc(), ToolHistory.id).limit(limit).offset(offset)
    )
    return s.ToolHistoryPage(
        items=[s.ToolHistoryView.model_validate(row) for row in rows], limit=limit, offset=offset
    )


def document(title: str, body: str) -> str:
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{html.escape(title)}</title><style>"
        "body{font:16px system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:1rem;"
        "line-height:1.5;overflow-wrap:anywhere}table{width:100%;border-collapse:collapse}"
        "p,td{white-space:pre-wrap}"
        "th,td{padding:.5rem;border:1px solid #888;text-align:left}"
        "@media print{body{margin:0}}</style></head><body>" + body + "</body></html>"
    )


def card_artifact(db: Session, org: UUID, actor: User, profile: UUID, request_id: str) -> str:
    row = card(db, org, actor, profile)
    if row is None:
        raise AuthError("not_found", 404)
    parts = []
    for language in ("en", "ta"):
        parts.append(f'<section lang="{language}">')
        for field in ("name", "tagline", "description", "address"):
            value = getattr(row, f"{field}_{language}")
            if value:
                tag = "h1" if field == "name" else "p"
                parts.append(f"<{tag}>{html.escape(value)}</{tag}>")
        parts.append("</section>")
    for field in ("phone", "email", "website"):
        value = getattr(row, field)
        if value:
            parts.append("<p>" + html.escape(value) + "</p>")
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=row.id,
            action="business_tool.card_downloaded",
            resource_version=row.version,
            changed_fields="artifact",
            request_id=request_id,
        )
    )
    db.commit()
    return document("Business card", "".join(parts))


def quote_artifact(
    db: Session, org: UUID, actor: User, profile: UUID, identifier: UUID, request_id: str
) -> str:
    row = quote(db, org, actor, profile, identifier)
    escape = html.escape
    rows = "".join(
        f"<tr><td>{escape(line.description)}</td><td>{line.quantity}</td>"
        f"<td>{line.unit_price:.2f}</td><td>{line.line_total:.2f}</td></tr>"
        for line in row.lines
    )
    body = (
        f"<h1>Quotation / விலைப்புள்ளி</h1><h2>{escape(row.business_name)}</h2>"
        f"<p>{escape(row.status.upper())} · {row.id}</p>"
        f"<p>Date: {row.issued_on} · Valid until: {row.valid_until or '—'}</p>"
        f"<h2>{escape(row.customer_name)}</h2><p>{escape(row.customer_address)}</p>"
        "<table><thead><tr><th>Description</th><th>Quantity</th><th>Unit price</th>"
        f"<th>Total ({row.currency})</th></tr></thead><tbody>{rows}</tbody></table>"
        f"<p>Subtotal: {row.subtotal:.2f}<br>Discount: {row.discount:.2f}<br>"
        f"Total: {row.total:.2f} {row.currency}</p><p>{escape(row.notes)}</p>"
        "<p>Quotation only. This document is not a tax invoice.</p>"
    )
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=row.id,
            action="business_tool.quote_downloaded",
            resource_version=row.version,
            changed_fields="artifact",
            request_id=request_id,
        )
    )
    db.commit()
    return document("Quotation", body)
