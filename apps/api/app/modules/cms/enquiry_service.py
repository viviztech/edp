import hashlib
import re
from uuid import UUID, uuid4
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.modules.cms.models import Enquiry
from app.modules.cms.schemas import EnquiryCreate, EnquiryReceipt, EnquiryView
from app.modules.identity.models import AuditLog, User
from app.modules.identity.security import AuthError
from app.modules.identity.service import require_permission

def _hash(data: EnquiryCreate) -> str:
    normalized = "|".join((data.email.lower(), data.phone, data.message, data.consent_version))
    return hashlib.sha256(normalized.encode()).hexdigest()
def _view(e): return EnquiryView(id=e.id,name=e.name,email=e.email,phone=e.phone,message=e.message,consent_version=e.consent_version,status=e.status)
def create(db:Session, org:UUID, data:EnquiryCreate, request_id:str):
    if data.consent_version != get_settings().contact_privacy_version: raise AuthError("consent_required",422)
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", data.email): raise AuthError("invalid_request",422)
    e=Enquiry(organization_id=org,name=data.name,email=data.email.lower(),phone=data.phone,message=data.message,consent_version=data.consent_version,dedupe_hash=_hash(data))
    db.add(e)
    try: db.flush()
    except IntegrityError:
        db.rollback(); return EnquiryReceipt(accepted=True,reference=uuid4())
    db.add(AuditLog(actor_id=None, organization_id=org, resource_id=e.id, action="enquiry.received", request_id=request_id, resource_version=1, changed_fields="status"))
    db.commit(); return EnquiryReceipt(accepted=True,reference=e.id)
def list_staff(db:Session,org:UUID,actor:User,limit:int):
    require_permission(db,actor,org,"enquiry.view")
    return [_view(e) for e in db.scalars(select(Enquiry).where(Enquiry.organization_id==org).order_by(Enquiry.created_at.desc()).limit(limit))]
