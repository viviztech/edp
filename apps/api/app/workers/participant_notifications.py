"""No external effects: participant notices and outbox settlement share a transaction."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.notifications import participant_service as service
from app.workers.celery_app import celery_app

engine = create_engine(get_settings().database_url.get_secret_value(), pool_pre_ping=True)


@celery_app.task(name="edp.participant_notifications.consume_outbox")  # type: ignore[untyped-decorator]
def consume_outbox() -> dict[str, int | bool | str]:
    try:
        with Session(engine) as db:
            return dict(service.consume_pending(db))
    except Exception as error:
        # Database/configuration exceptions can contain credentials; classify only.
        return {"status": "unavailable", "error_type": type(error).__name__}


@celery_app.task(name="edp.participant_notifications.purge_expired")  # type: ignore[untyped-decorator]
def purge_expired() -> dict[str, int | bool | str]:
    try:
        with Session(engine) as db:
            count = service.purge_expired(db)
        return {
            "purged": count,
            "retention_configured": get_settings().participant_notification_retention_days
            is not None,
        }
    except Exception as error:
        return {"status": "unavailable", "error_type": type(error).__name__}
