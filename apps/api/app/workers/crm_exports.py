"""Bounded export dispatch; database claims survive broker and worker loss."""

import time
from uuid import UUID

import structlog
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.crm import export_service as service
from app.modules.crm.export_service import _safe  # noqa: F401 - compatibility for CSV callers
from app.workers.celery_app import celery_app

MAX_EXPORT_ROWS = service.MAX_EXPORT_ROWS
engine = create_engine(get_settings().database_url.get_secret_value(), pool_pre_ping=True)
log = structlog.get_logger()


@celery_app.task(name="edp.crm.export_leads")  # type: ignore[untyped-decorator]
def export_leads(job_id: str) -> dict[str, object]:
    try:
        identifier = UUID(job_id)
    except (ValueError, TypeError, AttributeError):
        return {"status": "ignored"}
    policy = get_settings()
    with Session(engine) as db:
        lease = service.claim_export(db, identifier, policy)
    if lease is None:
        return {"status": "ignored"}
    try:
        with Session(engine) as db:
            output = service.generate_csv(db, lease.organization_id, policy.crm_export_max_bytes)
        with Session(engine) as db:
            accepted = service.complete_export(db, lease, output)
        return {"status": "completed" if accepted else "suppressed"}
    except Exception as error:
        code = error.code if isinstance(error, service.ExportLimitError) else "generation_failed"
        try:
            with Session(engine) as db:
                settled = service.fail_export(
                    db,
                    lease,
                    code,
                    retryable=not isinstance(error, service.ExportLimitError),
                    settings=policy,
                )
        except Exception:
            # The lease remains discoverable even if its failure could not be recorded.
            log.warning("crm_export_settlement_interrupted", job_id=str(identifier))
            return {"status": "interrupted"}
        return {"status": "settled" if settled else "stale"}


def publish_export(identity: UUID) -> None:
    # This connection is separate from request handling and global broker retries.
    with celery_app.connection_for_write(
        connect_timeout=2,
        transport_options={
            "socket_connect_timeout": 2,
            "socket_timeout": 2,
            "retry_on_timeout": False,
            "max_retries": 0,
            "connect_retries_timeout": 2,
        },
    ) as connection:
        celery_app.send_task(
            "edp.crm.export_leads",
            args=[str(identity)],
            connection=connection,
            retry=False,
            ignore_result=True,
            expires=120,
        )


@celery_app.task(name="edp.crm.recover_exports")  # type: ignore[untyped-decorator]
def recover_exports() -> dict[str, int | bool]:
    policy = get_settings()
    with Session(engine) as db:
        identities, settled = service.recover_exports(db, policy)
        disposed = service.dispose_expired(db, policy)
    published = failed = 0
    deadline = time.monotonic() + 10
    for identity in identities:
        if time.monotonic() >= deadline:
            break
        try:
            publish_export(identity)
            published += 1
        except Exception:
            failed += 1
            log.warning("crm_export_dispatch_unavailable", job_id=str(identity))
    return {
        "published": published,
        "dispatch_failed": failed,
        "settled": settled,
        "disposed": disposed,
        "retention_configured": policy.crm_export_retention_days is not None,
        "collection_configured": service.configured(policy),
    }
