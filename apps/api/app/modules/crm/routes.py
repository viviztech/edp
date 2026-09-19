from typing import Annotated
from uuid import UUID
from fastapi import APIRouter,Query,Request
from sqlalchemy import select
from app.modules.crm.models import Lead
from app.modules.crm.schemas import LeadCreate,LeadEdit,LeadList,LeadView
from app.modules.crm import service
from app.modules.identity.routes import DB,Principal
from app.modules.identity.service import require_permission
router=APIRouter(prefix="/api/v1",tags=["crm"])
Limit=Annotated[int,Query(ge=1,le=100)]
@router.post("/crm/organizations/{org}/leads",response_model=LeadView,status_code=201)
def create(org:UUID,data:LeadCreate,request:Request,db:DB,identity:Principal): return service.create(db,org,identity[0],data,request.state.request_id)
@router.get("/crm/organizations/{org}/leads",response_model=LeadList)
def list_leads(org:UUID,db:DB,identity:Principal,cursor:UUID|None=None,limit:Limit=25):
 require_permission(db,identity[0],org,"crm.lead.view"); q=select(Lead).where(Lead.organization_id==org); q=q.where(Lead.id>cursor) if cursor else q; rows=list(db.scalars(q.order_by(Lead.id).limit(limit+1))); return LeadList(items=[service.view(x) for x in rows[:limit]],next_cursor=rows[limit-1].id if len(rows)>limit else None)
@router.patch("/crm/organizations/{org}/leads/{lead_id}",response_model=LeadView)
def edit(org:UUID,lead_id:UUID,data:LeadEdit,request:Request,db:DB,identity:Principal): return service.mutate(db,org,lead_id,identity[0],data,request.state.request_id)
