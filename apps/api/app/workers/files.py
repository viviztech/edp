"""Durable database recovery; broker messages carry IDs, never bytes or provider keys."""

from uuid import UUID

import structlog
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.files import service
from app.modules.files.runtime import get_file_scanner, get_private_storage
from app.modules.identity.security import AuthError
from app.workers.celery_app import celery_app

settings = get_settings()
engine = create_engine(settings.database_url.get_secret_value(), pool_pre_ping=True)
log = structlog.get_logger()


@celery_app.task(name="edp.files.queue_due")  # type: ignore[untyped-decorator]
def queue_due_files() -> dict[str, int]:
    policy = get_settings()
    counts = {"scans": 0, "abandoned": 0, "disposals": 0, "dispatch_failed": 0}
    if not (policy.files_enabled or policy.files_maintenance_enabled):
        return counts
    with Session(engine) as db:
        scans = (
            service.scan_candidates(db, policy.files_cleanup_batch_size)
            if policy.files_enabled
            else []
        )
        abandoned = (
            service.abandoned_candidates(db, policy.files_cleanup_batch_size)
            if policy.files_maintenance_enabled
            else []
        )
        disposals = (
            service.cleanup_candidates(db, policy.files_cleanup_batch_size)
            if policy.files_maintenance_enabled
            else []
        )
    jobs = (
        [("scans", scan_file, [str(org), str(file_id)]) for org, file_id in scans]
        + [
            ("abandoned", reject_abandoned_file, [str(org), str(file_id), version])
            for org, file_id, version in abandoned
        ]
        + [
            ("disposals", dispose_file, [str(org), str(file_id), version])
            for org, file_id, version in disposals
        ]
    )
    for kind, task, arguments in jobs:
        try:
            task.apply_async(args=arguments, expires=120)
            counts[kind] += 1
        except Exception:
            # No database state was advanced. A later poll will rediscover this job.
            counts["dispatch_failed"] += 1
            log.warning("file_job_dispatch_unavailable", job_kind=kind)
    return counts


@celery_app.task(  # type: ignore[untyped-decorator]
    name="edp.files.scan",
    soft_time_limit=max(10, settings.files_scan_lease_seconds - 15),
    time_limit=settings.files_scan_lease_seconds,
)
def scan_file(organization_id: str, file_id: str) -> dict[str, str]:
    policy = get_settings()
    if not policy.files_enabled:
        return {"status": "disabled"}
    try:
        org, identity = UUID(organization_id), UUID(file_id)
        storage, scanner = get_private_storage(policy), get_file_scanner(policy)
        with Session(engine) as db:
            request_id = f"file-scan:{identity}"
            lease = service.claim_scan(
                db,
                org,
                identity,
                request_id,
                lease_seconds=policy.files_scan_lease_seconds,
                max_attempts=policy.files_scan_max_attempts,
            )
            result = service.scan_with_lease(
                db, org, lease, storage, scanner, request_id, policy.files_scan_max_attempts
            )
            return {"status": result.state}
    except AuthError as error:
        return {"status": "unavailable" if error.status >= 500 else "skipped"}
    except ValueError:
        return {"status": "skipped"}
    except Exception:
        # A hard worker loss or an unexpected exception leaves a fenced lease;
        # queue_due_files will recover it after expiry. Never log the exception text.
        log.warning("file_scan_interrupted")
        return {"status": "interrupted"}


@celery_app.task(name="edp.files.reject_abandoned", soft_time_limit=105, time_limit=120)  # type: ignore[untyped-decorator]
def reject_abandoned_file(organization_id: str, file_id: str, version: int) -> dict[str, str]:
    policy = get_settings()
    if not policy.files_maintenance_enabled:
        return {"status": "disabled"}
    try:
        org, identity = UUID(organization_id), UUID(file_id)
        storage = get_private_storage(policy, allow_disabled=True)
        with Session(engine) as db:
            result = service.reject_abandoned(
                db, org, identity, version, f"file-abandoned:{identity}", storage=storage
            )
            return {"status": result.state}
    except AuthError as error:
        return {"status": "unavailable" if error.status >= 500 else "skipped"}
    except ValueError:
        return {"status": "skipped"}
    except Exception:
        log.warning("file_abandoned_recovery_interrupted")
        return {"status": "interrupted"}


@celery_app.task(name="edp.files.dispose", soft_time_limit=105, time_limit=120)  # type: ignore[untyped-decorator]
def dispose_file(organization_id: str, file_id: str, version: int) -> dict[str, str]:
    policy = get_settings()
    if not policy.files_maintenance_enabled:
        return {"status": "disabled"}
    try:
        org, identity = UUID(organization_id), UUID(file_id)
        storage = get_private_storage(policy, allow_disabled=True)
        with Session(engine) as db:
            result = service.cleanup_file(
                db, org, identity, version, storage, f"file-dispose:{identity}"
            )
            return {"status": result.state}
    except AuthError as error:
        return {"status": "unavailable" if error.status >= 500 else "skipped"}
    except ValueError:
        return {"status": "skipped"}
    except Exception:
        log.warning("file_disposal_interrupted")
        return {"status": "interrupted"}
