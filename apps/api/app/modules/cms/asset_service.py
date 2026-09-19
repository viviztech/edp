from uuid import UUID, uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.modules.cms.models import Asset
from app.modules.cms.schemas import AssetCreate, AssetView
from app.modules.identity.models import AuditLog, User
from app.modules.identity.security import AuthError
from app.modules.identity.service import require_permission
ALLOWED={"image/jpeg","image/png","image/webp","application/pdf"}
def view(a:Asset)->AssetView: return AssetView(id=a.id,filename=a.filename,media_type=a.media_type,byte_size=a.byte_size,title=a.title,scan_status=a.scan_status,visibility=a.visibility,public_url=(f"/api/v1/public/organizations/{a.organization_id}/assets/{a.id}" if a.visibility=="public" and a.scan_status=="clean" else None))
def create(db:Session,org:UUID,actor:User,data:AssetCreate,request_id:str):
 require_permission(db,actor,org,"cms.asset.create")
 a=Asset(organization_id=org,storage_key=f"quarantine/{org}/{uuid4()}",filename=data.filename,media_type=data.media_type,byte_size=data.byte_size,title=data.title)
 db.add(a); db.flush(); db.add(AuditLog(actor_id=actor.id,organization_id=org,resource_id=a.id,action="cms.asset.created",request_id=request_id,resource_version=1,changed_fields="filename,media_type,byte_size,title,scan_status,visibility")); db.commit(); return view(a)
def publish(db,org,id,actor,request_id):
 require_permission(db,actor,org,"cms.asset.publish"); a=db.scalar(select(Asset).where(Asset.id==id,Asset.organization_id==org).with_for_update())
 if not a: raise AuthError("not_found",404)
 if a.scan_status!="clean": raise AuthError("asset_not_clean",409)
 a.visibility="public"; db.add(AuditLog(actor_id=actor.id,organization_id=org,resource_id=a.id,action="cms.asset.published",request_id=request_id,resource_version=1,changed_fields="visibility")); db.commit(); return view(a)


def scan_result(db: Session, org: UUID, asset_id: UUID, clean: bool, reason: str, request_id: str):
    a = db.scalar(select(Asset).where(Asset.id == asset_id, Asset.organization_id == org).with_for_update())
    if not a: raise AuthError("not_found", 404)
    a.scan_status = "clean" if clean else "infected"
    a.visibility = "private"
    db.add(AuditLog(actor_id=None, organization_id=org, resource_id=a.id, action="cms.asset.scan_completed", request_id=request_id, resource_version=1, reason=reason or None, changed_fields="scan_status,visibility"))
    db.commit()
    return view(a)
