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


def activity_view(a):
 from app.modules.crm.schemas import ActivityView
 return ActivityView(id=a.id,lead_id=a.lead_id,actor_user_id=a.actor_user_id,activity_type=a.activity_type,note=a.note,due_at=a.due_at,completed_at=a.completed_at)
def add_activity(db,org,lead_id,actor,data,request_id):
 from app.modules.crm.models import LeadActivity
 from app.modules.crm.schemas import ActivityCreate
 require_permission(db,actor,org,"crm.activity.create")
 lead=db.scalar(select(Lead).where(Lead.id==lead_id,Lead.organization_id==org))
 if not lead: raise AuthError("not_found",404)
 a=LeadActivity(lead_id=lead.id,organization_id=org,actor_user_id=actor.id,**data.model_dump()); db.add(a); db.flush(); db.add(AuditLog(actor_id=actor.id,organization_id=org,resource_id=lead.id,action="crm.lead.activity_added",request_id=request_id,resource_version=lead.version,changed_fields="activity_type,due_at")); db.commit(); return activity_view(a)
def activities(db,org,lead_id,actor,limit):
 from app.modules.crm.models import LeadActivity
 require_permission(db,actor,org,"crm.activity.view")
 if not db.scalar(select(Lead.id).where(Lead.id==lead_id,Lead.organization_id==org)): raise AuthError("not_found",404)
 return [activity_view(a) for a in db.scalars(select(LeadActivity).where(LeadActivity.lead_id==lead_id,LeadActivity.organization_id==org).order_by(LeadActivity.created_at.desc()).limit(limit))]
