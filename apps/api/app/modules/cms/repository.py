from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.cms.models import Page, Translation
from app.modules.identity.security import AuthError


def page(db: Session, org: UUID, page_id: UUID) -> Page:
    row = db.scalar(select(Page).where(Page.id == page_id, Page.organization_id == org))
    if row is None:
        raise AuthError("not_found", 404)
    return row


def translation(db: Session, org: UUID, page_id: UUID, locale: str) -> Translation:
    row = db.scalar(
        select(Translation)
        .where(
            Translation.page_id == page_id,
            Translation.organization_id == org,
            Translation.locale == locale,
        )
        .with_for_update()
    )
    if row is None:
        raise AuthError("not_found", 404)
    return row
