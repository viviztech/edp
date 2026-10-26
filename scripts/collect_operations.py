"""Collect read-only bounded signals from an explicitly synthetic local database.

Credentials use EDP_OPERATIONS_DATABASE_URL. No arbitrary SQL, service discovery,
provider access or unbounded identifier labels. Unexecuted runtime checks stay null.
"""

import argparse
import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

import psycopg
from deployment_contract import ContractError, require
from psycopg.conninfo import conninfo_to_dict
from recovery_guard import DRILL_DATABASE

AGE_QUERIES = {
    "outbox_pending_age_seconds": "SELECT EXTRACT(EPOCH FROM (now()-min(created_at))) "
    "FROM domain_outbox WHERE state IN ('pending','retrying')",
    "auth_delivery_pending_age_seconds": "SELECT EXTRACT(EPOCH FROM (now()-min(created_at))) "
    "FROM auth_deliveries WHERE status IN ('queued','retrying','preparing','sending')",
    "crm_export_pending_age_seconds": "SELECT EXTRACT(EPOCH FROM (now()-min(created_at))) "
    "FROM crm_export_jobs WHERE status IN ('queued','processing','retrying')",
    "file_scan_pending_age_seconds": "SELECT EXTRACT(EPOCH FROM (now()-min(created_at))) "
    "FROM file_objects WHERE state IN ('quarantined','scanning')",
}


def synthetic_database(url: str) -> dict:
    parameters = conninfo_to_dict(url.replace("postgresql+psycopg://", "postgresql://", 1))
    require(
        parameters.get("host") in {"127.0.0.1", "localhost", "::1"},
        "local_probe_host_required",
    )
    require(
        not set(parameters)
        - {
            "host",
            "port",
            "user",
            "password",
            "dbname",
            "sslmode",
            "sslrootcert",
            "connect_timeout",
            "application_name",
        },
        "probe_connection_options_rejected",
    )
    parameters["hostaddr"] = (
        "127.0.0.1" if parameters["host"] == "localhost" else parameters["host"]
    )
    parameters["connect_timeout"] = 3
    name = parameters.get("dbname", "")
    require(
        name in {"edp_test", "edp_auth_test", "edp_foundation_e2e"}
        or DRILL_DATABASE.fullmatch(name) is not None,
        "synthetic_probe_database_required",
    )
    return parameters


def collect(database_url: str, redis_url: str | None = None) -> dict:
    parameters = synthetic_database(database_url)
    samples = {
        name: None
        for name in (
            *AGE_QUERIES,
            "database_ready",
            "redis_ready",
            "worker_roundtrip_ok",
            "scheduler_instances",
            "scanner_signature_age_seconds",
            "backup_age_seconds",
            "restore_verification_age_seconds",
            "api_error_ratio",
        )
    }
    try:
        with psycopg.connect(**parameters) as database:
            database.execute("SET TRANSACTION READ ONLY")
            database.execute("SET LOCAL statement_timeout = '3s'")
            database.execute("SET LOCAL lock_timeout = '1s'")
            database.execute("SELECT 1").fetchone()
            samples["database_ready"] = 1
            for name, query in AGE_QUERIES.items():
                try:
                    with database.transaction():
                        value = database.execute(query).fetchone()[0]
                        samples[name] = max(0, float(value or 0))
                except psycopg.Error:
                    samples[name] = None
    except psycopg.Error:
        # Connection/dependency failures do not expose SQL/credentials in output.
        samples["database_ready"] = 0
    if redis_url is not None:
        import redis

        value = urlsplit(redis_url)
        require(
            value.scheme in {"redis", "rediss"}
            and value.hostname in {"127.0.0.1", "localhost", "::1"},
            "local_redis_probe_required",
        )
        require(
            re.fullmatch(r"/(?:[0-9]|1[0-5])", value.path) is not None,
            "redis_database_required",
        )
        try:
            client = redis.Redis.from_url(redis_url, socket_connect_timeout=2, socket_timeout=2)
            try:
                samples["redis_ready"] = 1 if client.ping() else 0
            finally:
                client.close()
        except redis.RedisError:
            samples["redis_ready"] = 0
    return {
        "schema_version": 1,
        "synthetic_only": True,
        "sampled_at": datetime.now(UTC).isoformat(),
        "samples": samples,
        "thresholds": {},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--redis",
        action="store_true",
        help="Ping loopback EDP_OPERATIONS_REDIS_URL only",
    )
    args = parser.parse_args()
    try:
        require(
            not args.output.exists() and not args.output.is_symlink(),
            "fresh_output_required",
        )
        require(
            bool(os.environ.get("EDP_OPERATIONS_DATABASE_URL")),
            "operations_database_required",
        )
        if args.redis:
            require(bool(os.environ.get("EDP_OPERATIONS_REDIS_URL")), "operations_redis_required")
        result = collect(
            os.environ["EDP_OPERATIONS_DATABASE_URL"],
            os.environ.get("EDP_OPERATIONS_REDIS_URL") if args.redis else None,
        )
        with args.output.open("x", encoding="utf-8") as output:
            output.write(json.dumps(result, indent=2) + "\n")
        print(
            json.dumps(
                {
                    "valid": True,
                    "external_delivery": False,
                    "database_ready": result["samples"]["database_ready"],
                }
            )
        )
        return 0
    except (ContractError, OSError, ValueError, psycopg.Error) as error:
        code = str(error) if isinstance(error, ContractError) else "signal_collection_failed"
        print(json.dumps({"valid": False, "code": code}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
