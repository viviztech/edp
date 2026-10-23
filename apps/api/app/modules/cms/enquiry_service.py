import hashlib
import re
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.cms.models import Enquiry
from app.modules.cms.schemas import (
    EnquiryCreate,
    EnquiryList,
    EnquiryPolicy,
    EnquiryReceipt,
    EnquiryStatus,
    EnquiryView,
    Locale,
)
from app.modules.identity.models import AuditLog, Organization, User, now
from app.modules.identity.security import AuthError
from app.modules.identity.service import require_permission, throttle


def _safe_notice(value: str) -> bool:
    if re.fullmatch(r"/(en|ta)/pages/[a-z0-9]+(?:-[a-z0-9]+)*", value):
        return True
    try:
        url = urlsplit(value)
        return bool(
            url.scheme == "https" and url.hostname and not url.username and not url.password
        )
    except ValueError:
        return False


def policy(locale: Locale) -> EnquiryPolicy:
    settings = get_settings()
    # Both channels need approved text and a notice before opening the bilingual form.
    for language in ("en", "ta"):
        notice = getattr(settings, "contact_privacy_notice_url_" + language)
        consent = getattr(settings, "contact_consent_text_" + language)
        if (
            not settings.contact_enquiries_enabled
            or not _safe_notice(notice)
            or not consent.strip()
        ):
            return EnquiryPolicy(enabled=False)
    return EnquiryPolicy(
        enabled=True,
        consent_version=settings.contact_privacy_version,
        privacy_notice_url=getattr(settings, "contact_privacy_notice_url_" + locale),
        consent_text=getattr(settings, "contact_consent_text_" + locale),
    )


def _hash(data: EnquiryCreate) -> str:
    normalized = "|".join((data.email.lower(), data.phone, data.message, data.consent_version))
    return hashlib.sha256(normalized.encode()).hexdigest()


def _view(e: Enquiry) -> EnquiryView:
    return EnquiryView(
        id=e.id,
        name=e.name,
        email=e.email,
        phone=e.phone,
        message=e.message,
        consent_version=e.consent_version,
        status=e.status,
        version=e.version,
        created_at=e.created_at,
        updated_at=e.updated_at,
    )


def create(
    db: Session, org: UUID, data: EnquiryCreate, request_id: str, source: str
) -> EnquiryReceipt:
    # Use the actual connecting peer. Untrusted forwarded headers must not evade a budget.
    throttle(db, "enquiry:source", source, 30)
    if not policy("en").enabled or not db.get(Organization, org):
        raise AuthError("enquiries_unavailable", 503)
    if data.consent_version != get_settings().contact_privacy_version:
        raise AuthError("consent_required", 422)
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", data.email):
        raise AuthError("invalid_request", 422)
    throttle(db, "enquiry:email", str(org) + ":" + data.email.lower(), 5)
    e = Enquiry(
        organization_id=org,
        name=data.name,
        email=data.email.lower(),
        phone=data.phone,
        message=data.message,
        consent_version=data.consent_version,
        dedupe_hash=_hash(data),
    )
    db.add(e)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        if constraint != "contact_enquiries_organization_id_dedupe_hash_key":
            raise
        return EnquiryReceipt(accepted=True, reference=uuid4())
    db.add(
        AuditLog(
            actor_id=None,
            organization_id=org,
            resource_id=e.id,
            action="enquiry.received",
            request_id=request_id,
            resource_version=1,
            changed_fields="status",
        )
    )
    db.commit()
    return EnquiryReceipt(accepted=True, reference=e.id)


def list_staff(db: Session, org: UUID, actor: User, limit: int) -> list[EnquiryView]:
    require_permission(db, actor, org, "enquiry.view")
    return [
        _view(e)
        for e in db.scalars(
            select(Enquiry)
            .where(Enquiry.organization_id == org)
            .order_by(Enquiry.created_at.desc())
            .limit(limit)
        )
    ]


def queue(
    db: Session, org: UUID, actor: User, limit: int, cursor: UUID | None, status: str | None
) -> EnquiryList:
    require_permission(db, actor, org, "enquiry.view")
    query = select(Enquiry).where(Enquiry.organization_id == org)
    if status:
        query = query.where(Enquiry.status == status)
    if cursor:
        query = query.where(Enquiry.id > cursor)
    rows = list(db.scalars(query.order_by(Enquiry.id).limit(limit + 1)))
    return EnquiryList(
        items=[_view(row) for row in rows[:limit]],
        next_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )


def detail(db: Session, org: UUID, enquiry_id: UUID, actor: User) -> EnquiryView:
    require_permission(db, actor, org, "enquiry.view")
    enquiry = db.scalar(
        select(Enquiry).where(Enquiry.organization_id == org, Enquiry.id == enquiry_id)
    )
    if not enquiry:
        raise AuthError("not_found", 404)
    return _view(enquiry)


def change_status(
    db: Session, org: UUID, enquiry_id: UUID, actor: User, data: EnquiryStatus, request_id: str
) -> EnquiryView:
    require_permission(db, actor, org, "enquiry.view")
    require_permission(db, actor, org, "enquiry.manage")
    enquiry = db.scalar(
        select(Enquiry)
        .where(Enquiry.organization_id == org, Enquiry.id == enquiry_id)
        .with_for_update()
    )
    if not enquiry:
        raise AuthError("not_found", 404)
    if enquiry.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    if {"new": "reviewed", "reviewed": "closed"}.get(enquiry.status) != data.status:
        raise AuthError("invalid_transition", 409)
    enquiry.status = data.status
    enquiry.version += 1
    enquiry.updated_at = now()
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=enquiry.id,
            action="enquiry.status_changed",
            request_id=request_id,
            resource_version=enquiry.version,
            changed_fields="status",
        )
    )
    db.commit()
    return _view(enquiry)
