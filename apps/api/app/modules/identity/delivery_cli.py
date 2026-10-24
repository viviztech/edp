"""Trusted global operator diagnostics. Never expose this CLI through an API."""

import argparse
import json
import sys
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.identity import delivery_service as service
from app.modules.identity.models import AuthDelivery


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["health", "inspect", "recover"])
    parser.add_argument("--id", type=UUID)
    parser.add_argument("--expected-version", type=int)
    parser.add_argument("--outcome", choices=["retry", "accepted", "failed"])
    parser.add_argument("--reason")
    args = parser.parse_args()
    if args.command in {"inspect", "recover"} and not args.id:
        parser.error("id is required")
    if args.command == "recover" and not (args.expected_version and args.outcome and args.reason):
        parser.error("expected-version, outcome and reason are required")
    engine = None
    try:
        policy = get_settings()
        options = "-c statement_timeout=3000"
        if args.command != "recover":
            options += " -c default_transaction_read_only=on"
        engine = create_engine(
            policy.database_url.get_secret_value(),
            connect_args={"connect_timeout": 3, "options": options},
        )
        with Session(engine) as db:
            if args.command == "health":
                result = service.health(db, policy)
            elif args.command == "inspect":
                row = db.get(AuthDelivery, args.id)
                result = (
                    {"status": "not_found"}
                    if row is None
                    else {
                        "id": str(row.id),
                        "status": row.status,
                        "version": row.version,
                        "attempt_count": row.attempt_count,
                        "error_code": row.error_code,
                        "provider_reference": row.provider_reference,
                        "payload_disposed": bool(row.disposed_at),
                    }
                )
            else:
                service.operator_recover(
                    db, args.id, args.expected_version, args.outcome, args.reason, policy
                )
                result = {"status": "operator_recovery_recorded"}
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as error:
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
