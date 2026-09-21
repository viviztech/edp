from celery import Celery

from app.core.config import get_settings

settings = get_settings()
celery_app = Celery(
    "edp",
    broker=settings.redis_url.get_secret_value(),
    backend=settings.redis_url.get_secret_value(),
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    result_expires=300,
    task_soft_time_limit=25,
    task_time_limit=30,
    imports=("app.workers.crm_exports", "app.workers.meta_leads"),
    beat_schedule={
        "recover-meta-events": {
            "task": "edp.meta.recover_events",
            "schedule": 60.0,
        },
        "purge-expired-meta-events": {
            "task": "edp.meta.purge_expired_events",
            "schedule": 60.0,
        },
    },
)


def probe() -> dict[str, str]:
    """No business effects; suitable for development queue round-trip verification."""
    return {"status": "ok"}


celery_app.task(name="edp.probe")(probe)
