import hashlib
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.modules.crm.models import Lead
from app.modules.crm.schemas import LeadCreate,LeadEdit,LeadView
from app.modules.identity.models import AuditLog,User,now
from app.modules.identity.security import AuthError
from app.modules.identity.service import require_permission
def view(x): return LeadView(id=x.id,name=x.name,email=x.email,phone=x.phone,source=x.source,campaign=x.campaign,status=x.status,assigned_user_id=x.assigned_user_id,notes=x.notes,version=x.version)
def create(db:Session,org:UUID,actor:User,d:LeadCreate,request_id:str):
 require_permission(db,actor,org,"crm.lead.create"); h=hashlib.sha256((d.email.lower()+"|"+d.phone).encode()).hexdigest(); x=Lead(organization_id=org,dedupe_hash=h,**d.model_dump()); db.add(x)
 try: db.flush()
 except IntegrityError as exc: db.rollback(); raise AuthError("duplicate_lead",409) from exc
 db.add(AuditLog(actor_id=actor.id,organization_id=org,resource_id=x.id,action="crm.lead.created",request_id=request_id,resource_version=1,changed_fields="name,email,phone,source,campaign,status")); db.commit(); return view(x)
def mutate(db,org,id,actor,d,request_id):
 require_permission(db,actor,org,"crm.lead.update"); x=db.scalar(select(Lead).where(Lead.id==id,Lead.organization_id==org).with_for_update())
 if not x: raise AuthError("not_found",404)
 if x.version!=d.expected_version: raise AuthError("version_conflict",409)
 x.status,x.assigned_user_id,x.notes=d.status,d.assigned_user_id,d.notes; x.version+=1; x.updated_at=now(); db.add(AuditLog(actor_id=actor.id,organization_id=org,resource_id=x.id,action="crm.lead.updated",request_id=request_id,resource_version=x.version,changed_fields="status,assigned_user_id,notes")); db.commit(); return view(x)
