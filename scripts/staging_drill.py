"""Run a fresh loopback-only synthetic database role/backup/restore drill.

Uses only the project-owned local PostgreSQL cluster and newly generated names.
Never opens a shared development/test database. Child diagnostics stay private.
"""

import hashlib
import json
import os
import secrets
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import psycopg
from collect_operations import collect
from cryptography.fernet import Fernet
from deployment_contract import ROOT, ContractError, require
from psycopg import sql
from psycopg.conninfo import make_conninfo
from recovery_guard import (
    DRILL_DATABASE,
    digest,
    restore_new_database,
    validate_recovery,
)
from sqlalchemy import URL


def subprocess_check(command: list[str], env: dict[str, str], folder: Path, name: str) -> None:
    with (folder / f"{name}.private.log").open("xb") as output:
        result = subprocess.run(
            command,
            cwd=ROOT / "apps/api",
            env=env,
            stdout=output,
            stderr=subprocess.STDOUT,
            timeout=300,
            check=False,
        )
    require(result.returncode == 0, f"{name}_failed")


def role_policy(connection: psycopg.Connection, database: str, roles: dict[str, str]) -> None:
    policy = (ROOT / "infra/deployment/database-roles.sql").read_text(encoding="utf-8")
    policy = "\n".join(line for line in policy.splitlines() if not line.startswith("\\"))
    substitutions = {
        "database": database,
        **{f"{name}_role": value for name, value in roles.items()},
    }
    for name, value in substitutions.items():
        policy = policy.replace(f':"{name}"', sql.Identifier(value).as_string(connection))
    require(':"' not in policy, "grant_substitution_invalid")
    connection.execute(policy)


def denied(connection: psycopg.Connection, statement: str) -> None:
    try:
        with connection.transaction():
            connection.execute(statement)
    except (psycopg.errors.InsufficientPrivilege, psycopg.errors.RaiseException):
        return
    raise ContractError("runtime_privilege_exceeded")


def main() -> int:
    suffix = uuid4().hex[:12]
    databases = [f"edp_ops_drill_{suffix}_source", f"edp_ops_drill_{suffix}_restore"]
    roles = {name: f"edp_ops_{suffix}_{name}" for name in ("migration", "api", "worker")}
    passwords = {name: secrets.token_urlsafe(32) for name in roles}
    folder = ROOT / ".local" / f"staging-drill-{suffix}"
    record = {
        "schema_version": 1,
        "synthetic_only": True,
        "started_at": datetime.now(UTC).isoformat(),
        "status": "failed",
        "senders_enabled": False,
        "deployment_authorized": False,
        "live_storage_verified": False,
        "cleanup": "pending",
    }
    created_databases: list[str] = []
    created_roles: list[str] = []
    admin_parameters = None
    try:
        require(
            folder.resolve().is_relative_to(ROOT / ".local") and not folder.exists(),
            "fresh_evidence_folder_required",
        )
        folder.mkdir()
        credentials = json.loads(
            (ROOT / ".local/postgres17/credentials.json").read_text(encoding="utf-8-sig")
        )
        require(
            credentials["host"] == "127.0.0.1"
            and int(credentials["port"]) == 55432
            and credentials["user"] == "edp_dev",
            "project_loopback_cluster_required",
        )
        admin_parameters = {
            "host": credentials["host"],
            "port": credentials["port"],
            "user": credentials["user"],
            "password": credentials["password"],
            "dbname": "postgres",
            "connect_timeout": 3,
        }
        pg_bin = ROOT / ".tool-cache/postgresql17/pgsql/bin"
        extension = ".exe" if os.name == "nt" else ""
        pg_dump = pg_bin / ("pg_dump" + extension)
        pg_restore = pg_bin / ("pg_restore" + extension)
        require(pg_dump.is_file() and pg_restore.is_file(), "postgres_tools_required")
        with psycopg.connect(**admin_parameters, autocommit=True) as admin:
            for name, role in roles.items():
                require(
                    admin.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,)).fetchone()
                    is None,
                    "fresh_role_required",
                )
                admin.execute(
                    sql.SQL(
                        "CREATE ROLE {} LOGIN PASSWORD {} NOINHERIT NOSUPERUSER "
                        "NOCREATEDB NOCREATEROLE NOBYPASSRLS"
                    ).format(sql.Identifier(role), sql.Literal(passwords[name]))
                )
                created_roles.append(role)
            require(
                admin.execute(
                    "SELECT 1 FROM pg_database WHERE datname=%s", (databases[0],)
                ).fetchone()
                is None,
                "fresh_source_database_required",
            )
            admin.execute(
                sql.SQL("CREATE DATABASE {} OWNER {} TEMPLATE template0").format(
                    sql.Identifier(databases[0]), sql.Identifier(roles["migration"])
                )
            )
            created_databases.append(databases[0])
        environment = dict(os.environ)
        environment.update(
            APP_ENV="test",
            REDIS_URL="redis://127.0.0.1:6379/15",
            AUTH_DELIVERY_BACKEND="development",
            AUTH_SMTP_ENABLED="false",
            FILES_ENABLED="false",
            FILES_MAINTENANCE_ENABLED="false",
            CONTACT_ENQUIRIES_ENABLED="false",
            PYTHONUTF8="1",
            PARTICIPANT_NOTIFICATION_RETENTION_DAYS="30",
            AUTH_DELIVERY_KEY=Fernet.generate_key().decode(),
        )

        def runtime_env(name: str, database: str) -> dict[str, str]:
            values = dict(environment)
            values["DATABASE_URL"] = URL.create(
                "postgresql+psycopg",
                username=roles[name],
                password=passwords[name],
                host="127.0.0.1",
                port=55432,
                database=database,
            ).render_as_string(hide_password=False)
            return values

        start = time.monotonic()
        subprocess_check(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            runtime_env("migration", databases[0]),
            folder,
            "migration",
        )
        with psycopg.connect(**{**admin_parameters, "dbname": databases[0]}, autocommit=True) as db:
            role_policy(db, databases[0], roles)
            head = db.execute("SELECT version_num FROM alembic_version").fetchone()[0]
            for name in ("api", "worker"):
                attributes = db.execute(
                    "SELECT rolsuper,rolcreatedb,rolcreaterole,rolbypassrls "
                    "FROM pg_roles WHERE rolname=%s",
                    (roles[name],),
                ).fetchone()
                require(attributes == (False, False, False, False), "role_attributes_unsafe")
        for name in ("api", "worker"):
            values = runtime_env(name, databases[0])
            values["EDP_DRILL_RUNTIME"] = name
            subprocess_check(
                [sys.executable, str(ROOT / "scripts/staging_role_probe.py")],
                values,
                folder,
                name + "_transactions",
            )
        snapshot = collect(runtime_env("api", databases[0])["DATABASE_URL"])
        require(
            snapshot["samples"]["database_ready"] == 1
            and all(
                snapshot["samples"][name] is not None
                for name in (
                    "outbox_pending_age_seconds",
                    "auth_delivery_pending_age_seconds",
                    "crm_export_pending_age_seconds",
                    "file_scan_pending_age_seconds",
                )
            ),
            "read_only_operations_probe_failed",
        )
        (folder / "operations-snapshot.json").write_text(
            json.dumps(snapshot, indent=2) + "\n", encoding="utf-8"
        )
        negative_checks = 0
        for name in ("api", "worker"):
            with psycopg.connect(
                host="127.0.0.1",
                port=55432,
                dbname=databases[0],
                user=roles[name],
                password=passwords[name],
                autocommit=True,
            ) as db:
                for statement in (
                    "CREATE TABLE public.ops_forbidden (id integer)",
                    "ALTER TABLE public.audit_logs ADD COLUMN forbidden integer",
                    "ALTER TABLE public.audit_logs DISABLE TRIGGER ALL",
                    "TRUNCATE public.audit_logs",
                    "UPDATE public.audit_logs SET action='changed'",
                    "DELETE FROM public.audit_logs",
                    "DELETE FROM public.alembic_version",
                    "CREATE ROLE ops_forbidden",
                    "CREATE SCHEMA ops_forbidden",
                    "CREATE TEMP TABLE ops_forbidden (id integer)",
                    "DROP TABLE audit_logs",
                ):
                    denied(db, statement)
                    negative_checks += 1
                denied(
                    db,
                    sql.SQL("SET ROLE {}").format(sql.Identifier(roles["migration"])).as_string(db),
                )
                negative_checks += 1
        dump_environment = dict(environment)
        dump_environment.update(
            PGHOST="127.0.0.1",
            PGPORT="55432",
            PGUSER=credentials["user"],
            PGPASSWORD=credentials["password"],
        )
        subprocess_check(
            [
                str(pg_dump),
                "--format=custom",
                "--no-owner",
                "--no-privileges",
                "--file",
                str(folder / "database.dump"),
                databases[0],
            ],
            dump_environment,
            folder,
            "backup",
        )
        (folder / "object.bin").write_bytes(b"synthetic pinned version fixture")
        manifest = {
            "schema_version": 1,
            "synthetic_only": True,
            "outbound_disabled": True,
            "scheduler_stopped": True,
            "deletion_ledger_reconciled": True,
            "outbox_reconciled": True,
            "source_database": databases[0],
            "source_revision": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "configuration_sha256": digest(ROOT / "infra/deployment/staging.compose.json"),
            "migration_head": head,
            "recovery_point": datetime.now(UTC).isoformat(),
            "database_backup": "database.dump",
            "database_sha256": digest(folder / "database.dump"),
            "objects": [
                {
                    "reference": hashlib.sha256(b"synthetic").hexdigest(),
                    "organization_id": str(uuid4()),
                    "version": "synthetic-v1",
                    "sha256": digest(folder / "object.bin"),
                    "byte_length": (folder / "object.bin").stat().st_size,
                    "encryption": "AES256",
                    "key_available": True,
                    "file": "object.bin",
                    "access": "active",
                    "legal_hold": True,
                    "retained_until": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
                }
            ],
        }
        validate_recovery(manifest, folder)
        (folder / "recovery-manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        restored_at = time.monotonic()
        restore_new_database(
            manifest,
            folder,
            databases[1],
            make_conninfo(**admin_parameters),
            pg_restore,
            on_created=created_databases.append,
        )
        restore_seconds = time.monotonic() - restored_at
        with psycopg.connect(**{**admin_parameters, "dbname": databases[1]}, autocommit=True) as db:
            role_policy(db, databases[1], roles)
            require(
                db.execute("SELECT version_num FROM alembic_version").fetchone()[0] == head,
                "restored_schema_mismatch",
            )
            require(
                db.execute("SELECT count(*) FROM audit_logs").fetchone()[0] >= 1,
                "restored_audit_missing",
            )
            require(
                db.execute("SELECT count(*) FROM users").fetchone()[0] == 1,
                "restored_identity_missing",
            )
            require(
                db.execute("SELECT state FROM domain_outbox").fetchone()[0] == "unsupported",
                "restored_outbox_settlement_missing",
            )
        with psycopg.connect(
            host="127.0.0.1",
            port=55432,
            dbname=databases[1],
            user=roles["api"],
            password=passwords["api"],
            autocommit=True,
        ) as db:
            denied(db, "UPDATE audit_logs SET action='changed'")
            denied(db, "ALTER TABLE audit_logs DISABLE TRIGGER ALL")
            require(
                db.execute("SELECT count(*) FROM users").fetchone()[0] == 1,
                "restored_runtime_read_failed",
            )
        # An existing destination can never be overwritten, even if otherwise valid.
        try:
            restore_new_database(
                manifest,
                folder,
                databases[1],
                make_conninfo(**admin_parameters),
                pg_restore,
            )
        except ContractError as error:
            require(str(error) == "fresh_database_required", "existing_target_check_failed")
        else:
            raise ContractError("existing_target_overwritten")
        record.update(
            status="passed",
            migration_head=head,
            negative_privilege_checks=negative_checks + 2,
            migration_api_worker_transactions="passed",
            backup_restore="passed",
            existing_target_refused=True,
            restore_seconds=round(restore_seconds, 3),
            total_seconds=round(time.monotonic() - start, 3),
            rpo_rto_owner_approved=False,
            offline_pinned_object_fixture="passed",
        )
    except (
        ContractError,
        OSError,
        ValueError,
        psycopg.Error,
        subprocess.SubprocessError,
    ) as error:
        record["code"] = (
            str(error) if isinstance(error, ContractError) else "synthetic_drill_failed"
        )
    finally:
        if admin_parameters:
            try:
                with psycopg.connect(**admin_parameters, autocommit=True) as admin:
                    for database in reversed(created_databases):
                        require(
                            DRILL_DATABASE.fullmatch(database) is not None,
                            "cleanup_target_invalid",
                        )
                        admin.execute(
                            sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(
                                sql.Identifier(database)
                            )
                        )
                    for role in reversed(created_roles):
                        require(
                            role.startswith(f"edp_ops_{suffix}_"),
                            "cleanup_role_invalid",
                        )
                        admin.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(role)))
                record["cleanup"] = "passed"
            except (psycopg.Error, ContractError):
                record["cleanup"] = "failed"
        record["finished_at"] = datetime.now(UTC).isoformat()
        if folder.exists():
            (folder / "report.json").write_text(
                json.dumps(record, indent=2) + "\n", encoding="utf-8"
            )
        print(json.dumps({**record, "evidence": folder.relative_to(ROOT).as_posix()}))
    return 0 if record["status"] == "passed" and record["cleanup"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
