"""Trusted operator diagnostics; no export contents or identifiers are emitted."""

import argparse
import json
import sys
from datetime import timedelta

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.core.config import Settings, get_settings
from app.modules.crm.models import ExportJob
from app.modules.identity.models import now


def health(db: Session, settings: Settings) -> dict[str, int | bool | float | None]:
    current = now()
    due = (
        (ExportJob.status == "queued")
        & (ExportJob.next_attempt_at <= current)
        & (ExportJob.expires_at > current)
    )
    due_count, oldest = db.execute(
        select(func.count(), func.min(ExportJob.created_at)).where(due)
    ).one()

    def count(*conditions: ColumnElement[bool]) -> int:
        # Each caller supplies SQL boolean expressions, never client input.
        return int(db.scalar(select(func.count()).select_from(ExportJob).where(*conditions)) or 0)

    expired_output = (
        (ExportJob.status == "completed")
        & (ExportJob.expires_at <= current)
        & ExportJob.csv_content.is_not(None)
    )
    days = settings.crm_export_retention_days
    return {
        "queued_due": int(due_count),
        "oldest_due_seconds": max(0.0, (current - oldest).total_seconds()) if oldest else None,
        "expired_running_leases": count(
            ExportJob.status == "running", ExportJob.lease_until <= current
        ),
        "failed": count(ExportJob.status == "failed"),
        "retry_exhausted": count(
            ExportJob.status == "failed", ExportJob.error_code == "retry_exhausted"
        ),
        "retained_expired_outputs": count(expired_output),
        "disposal_due": count(
            expired_output, ExportJob.created_at <= current - timedelta(days=days)
        )
        if days is not None
        else None,
        "retention_configured": days is not None,
        "requests_configured": settings.app_env in {"local", "test"} or days is not None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["health"])
    parser.parse_args()
    engine = None
    try:
        settings = get_settings()
        engine = create_engine(
            settings.database_url.get_secret_value(),
            isolation_level="REPEATABLE READ",
            connect_args={
                "connect_timeout": 3,
                "options": "-c statement_timeout=3000 -c default_transaction_read_only=on",
            },
        )
        with Session(engine) as db:
            result = health(db, settings)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as error:
        # Driver/configuration exception text can contain credentials.
        print(
            json.dumps({"status": "unavailable", "error_type": type(error).__name__}),
            file=sys.stderr,
        )
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
