"""Validate synthetic recovery artifacts; restore only to a new isolated database.

No provider is contacted. Offline object fixtures are not S3/version/KMS acceptance.
The default command validates only. --restore requires an explicit fresh target.
"""

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from deployment_contract import HEX, ContractError, read_json, require

DRILL_DATABASE = re.compile(r"edp_ops_drill_[a-f0-9]{12}_(?:source|restore)")


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            value.update(chunk)
    return value.hexdigest()


def artifact(root: Path, name: object) -> Path:
    require(isinstance(name, str) and 0 < len(name) <= 180, "artifact_path_invalid")
    require("\\" not in name and ":" not in name, "artifact_path_invalid")
    relative = Path(name)
    require(
        not relative.is_absolute() and ".." not in relative.parts,
        "artifact_path_invalid",
    )
    path = root / relative
    require(path.resolve().is_relative_to(root.resolve()), "artifact_path_invalid")
    for item in (path, *path.parents):
        if item.exists() or item.is_symlink():
            info = item.lstat()
            require(
                not stat.S_ISLNK(info.st_mode)
                and not (
                    getattr(info, "st_file_attributes", 0)
                    & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
                ),
                "artifact_link_rejected",
            )
        if item == root:
            break
    require(path.is_file(), "artifact_unavailable")
    return path


def utc_time(value: object) -> datetime:
    require(isinstance(value, str), "recovery_time_invalid")
    try:
        result = datetime.fromisoformat(value)
        require(result.utcoffset() == UTC.utcoffset(result), "recovery_time_invalid")
        return result
    except ValueError as error:
        raise ContractError("recovery_time_invalid") from error


def validate_recovery(data: dict, folder: Path) -> dict:
    require(data.get("schema_version") == 1, "recovery_schema_invalid")
    require(data.get("synthetic_only") is True, "synthetic_recovery_required")
    require(data.get("outbound_disabled") is True, "outbound_must_remain_disabled")
    require(data.get("scheduler_stopped") is True, "scheduler_must_remain_stopped")
    require(
        data.get("deletion_ledger_reconciled") is True,
        "deletion_reconciliation_required",
    )
    require(data.get("outbox_reconciled") is True, "outbox_reconciliation_required")
    require(
        DRILL_DATABASE.fullmatch(str(data.get("source_database", ""))) is not None,
        "isolated_source_required",
    )
    require(
        re.fullmatch(r"[a-f0-9]{40}", str(data.get("source_revision", ""))) is not None,
        "source_identity_required",
    )
    require(
        HEX.fullmatch(str(data.get("configuration_sha256", ""))) is not None,
        "configuration_identity_required",
    )
    require(
        re.fullmatch(r"[a-z0-9_]{1,80}", str(data.get("migration_head", ""))) is not None,
        "migration_identity_required",
    )
    recovery_point = utc_time(data.get("recovery_point"))
    require(recovery_point <= datetime.now(UTC), "future_recovery_point_rejected")
    dump = artifact(folder, data.get("database_backup"))
    require(
        HEX.fullmatch(str(data.get("database_sha256", ""))) is not None
        and digest(dump) == data["database_sha256"],
        "database_checksum_mismatch",
    )
    require(dump.stat().st_size > 0, "empty_backup_rejected")
    objects = data.get("objects")
    require(isinstance(objects, list) and len(objects) <= 10000, "object_inventory_invalid")
    references = set()
    retained = inaccessible = 0
    for item in objects:
        require(isinstance(item, dict), "object_entry_invalid")
        reference = item.get("reference")
        require(
            isinstance(reference, str) and HEX.fullmatch(reference) is not None,
            "object_reference_invalid",
        )
        require(reference not in references, "duplicate_object_reference")
        references.add(reference)
        try:
            UUID(item.get("organization_id"))
        except (ValueError, TypeError, AttributeError) as error:
            raise ContractError("object_scope_invalid") from error
        require(
            isinstance(item.get("version"), str) and 0 < len(item["version"]) <= 200,
            "exact_version_required",
        )
        require(
            item.get("access") in {"active", "revoked", "disposed"},
            "object_access_invalid",
        )
        require(isinstance(item.get("legal_hold"), bool), "object_hold_invalid")
        utc_time(item.get("retained_until"))
        if item["access"] != "active":
            require(item.get("file") is None, "inaccessible_object_bytes_rejected")
            inaccessible += 1
            continue
        require(item.get("key_available") is True, "recovery_key_unavailable")
        require(item.get("encryption") in {"AES256", "aws:kms"}, "object_encryption_invalid")
        require(
            HEX.fullmatch(str(item.get("sha256", ""))) is not None,
            "object_checksum_invalid",
        )
        path = artifact(folder, item.get("file"))
        require(
            type(item.get("byte_length")) is int
            and item["byte_length"] >= 0
            and path.stat().st_size == item["byte_length"],
            "object_length_mismatch",
        )
        require(digest(path) == item["sha256"], "object_checksum_mismatch")
        # The version is pinned by inventory; never synthesize or replace it.
        retained += 1
    return {
        "valid": True,
        "synthetic_only": True,
        "objects_verified": retained,
        "objects_inaccessible": inaccessible,
        "outbound_disabled": True,
        "scheduler_stopped": True,
        "live_storage_verified": False,
        "backup_age_seconds": max(0, int((datetime.now(UTC) - recovery_point).total_seconds())),
    }


def restore_new_database(
    data: dict,
    folder: Path,
    target: str,
    admin_url: str,
    pg_restore: Path,
    on_created: Callable[[str], None] | None = None,
) -> None:
    """Create only a fresh owned drill DB, with no clean/drop or existing-target path."""
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import conninfo_to_dict, make_conninfo

    validate_recovery(data, folder)
    require(
        DRILL_DATABASE.fullmatch(target) is not None and target.endswith("_restore"),
        "isolated_restore_target_required",
    )
    require(target != data["source_database"], "source_target_collision")
    require(pg_restore.is_file() and not pg_restore.is_symlink(), "restore_tool_unavailable")
    parameters = conninfo_to_dict(admin_url)
    require(
        parameters.get("host") in {"127.0.0.1", "localhost", "::1"},
        "local_drill_host_required",
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
        "restore_connection_options_rejected",
    )
    parameters["hostaddr"] = (
        "127.0.0.1" if parameters["host"] == "localhost" else parameters["host"]
    )
    parameters["connect_timeout"] = 3
    parameters["dbname"] = "postgres"
    with psycopg.connect(make_conninfo(**parameters), autocommit=True) as admin:
        require(
            admin.execute("SELECT 1 FROM pg_database WHERE datname=%s", (target,)).fetchone()
            is None,
            "fresh_database_required",
        )
        admin.execute(
            sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(target))
        )
        if on_created is not None:
            on_created(target)
    # Credentials stay in the child environment; stdout/stderr are intentionally
    # discarded because PostgreSQL diagnostics may contain restored private values.
    environment = dict(os.environ)
    for name in ("PGSERVICE", "PGSERVICEFILE", "PGOPTIONS", "PGDATABASE", "PGPASSFILE"):
        environment.pop(name, None)
    for key, value in parameters.items():
        if key in {"host", "hostaddr", "port", "user", "password", "sslmode", "sslrootcert"}:
            environment["PG" + key.upper()] = str(value)
    result = subprocess.run(
        [
            str(pg_restore),
            "--exit-on-error",
            "--no-owner",
            "--no-privileges",
            "--single-transaction",
            "--dbname",
            target,
            str(artifact(folder, data["database_backup"])),
        ],
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=300,
        check=False,
    )
    require(result.returncode == 0, "restore_execution_failed")


def main() -> int:
    import psycopg

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--restore", metavar="FRESH_DRILL_DATABASE")
    parser.add_argument("--pg-restore", type=Path)
    args = parser.parse_args()
    try:
        data = read_json(args.manifest)
        result = validate_recovery(data, args.manifest.parent)
        if args.restore:
            require(args.pg_restore is not None, "restore_tool_required")
            require(
                bool(os.environ.get("EDP_RECOVERY_ADMIN_URL")),
                "recovery_identity_required",
            )
            restore_new_database(
                data,
                args.manifest.parent,
                args.restore,
                os.environ["EDP_RECOVERY_ADMIN_URL"],
                args.pg_restore,
            )
            result["database_restored"] = True
        else:
            result["database_restored"] = False
        print(json.dumps(result))
        return 0
    except (
        ContractError,
        OSError,
        ValueError,
        subprocess.SubprocessError,
        psycopg.Error,
    ) as error:
        code = str(error) if isinstance(error, ContractError) else "recovery_check_failed"
        print(json.dumps({"valid": False, "code": code}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
