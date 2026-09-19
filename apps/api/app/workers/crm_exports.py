import csv
import io
from uuid import UUID

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.crm.models import ExportJob, Lead
from app.modules.identity.models import AuditLog, now
from app.workers.celery_app import celery_app

MAX_EXPORT_ROWS = 10000
engine = create_engine(get_settings().database_url.get_secret_value(), pool_pre_ping=True)


def _safe(value: object) -> str:
    text = "" if value is None else str(value)
    return "'" + text if text.startswith(("=", "+", "-", "@")) else text


@celery_app.task(name="edp.crm.export_leads")  # type: ignore[untyped-decorator]
def export_leads(job_id: str) -> dict[str, object]:
    with Session(engine) as db:
        job = db.scalar(select(ExportJob).where(ExportJob.id == UUID(job_id)).with_for_update())
        if not job or job.status != "queued":
            return {"status": "ignored"}
        job.status = "running"
        db.commit()
        try:
            leads = list(
                db.scalars(
                    select(Lead)
                    .where(Lead.organization_id == job.organization_id)
                    .order_by(Lead.id)
                    .limit(MAX_EXPORT_ROWS)
                )
            )
            output = io.StringIO(newline="")
            writer = csv.writer(output)
            writer.writerow(
                [
                    "id",
                    "name",
                    "email",
                    "phone",
                    "source",
                    "campaign",
                    "status",
                    "assigned_user_id",
                    "merged_into_id",
                    "created_at",
                ]
            )
            for lead in leads:
                writer.writerow(
                    [
                        _safe(value)
                        for value in (
                            lead.id,
                            lead.name,
                            lead.email,
                            lead.phone,
                            lead.source,
                            lead.campaign,
                            lead.status,
                            lead.assigned_user_id,
                            lead.merged_into_id,
                            lead.created_at.isoformat(),
                        )
                    ]
                )
            job.csv_content = output.getvalue()
            job.row_count = len(leads)
            job.status = "completed"
            job.completed_at = now()
            db.add(
                AuditLog(
                    actor_id=None,
                    organization_id=job.organization_id,
                    resource_id=job.id,
                    action="crm.lead.export_completed",
                    request_id=f"worker:{job.id}",
                    resource_version=1,
                    changed_fields="status,row_count",
                )
            )
            db.commit()
            return {"status": "completed", "rows": len(leads)}
        except Exception:
            db.rollback()
            failed = db.get(ExportJob, UUID(job_id))
            if failed:
                failed.status = "failed"
                failed.error_code = "generation_failed"
                failed.completed_at = now()
                db.add(
                    AuditLog(
                        actor_id=None,
                        organization_id=failed.organization_id,
                        resource_id=failed.id,
                        action="crm.lead.export_failed",
                        request_id=f"worker:{failed.id}",
                        resource_version=1,
                        changed_fields="status,error_code",
                    )
                )
                db.commit()
            raise
