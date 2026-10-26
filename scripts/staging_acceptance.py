"""Record local synthetic staging preparation evidence; never deploy or enable delivery."""

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from deployment_contract import (
    ROOT,
    ContractError,
    read_json,
    require,
    validate_topology,
)


def source_identity() -> tuple[str, str]:
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    selected = (
        subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=ROOT,
        )
        .decode("utf-8")
        .split("\0")
    )
    records = []
    for name in sorted(set(filter(None, selected))):
        path = ROOT / name
        require(
            path.resolve().is_relative_to(ROOT) and not path.is_symlink(),
            "source_path_rejected",
        )
        # Git ignored secret/cache files never enter the selection. This check
        # also refuses an accidentally tracked local environment file.
        require(
            path.name == ".env.example" or not path.name.startswith(".env"),
            "secret_source_rejected",
        )
        if path.is_file():
            records.append([name, hashlib.sha256(path.read_bytes()).hexdigest()])
        else:
            records.append([name, "deleted"])
    digest = hashlib.sha256(json.dumps(records, separators=(",", ":")).encode()).hexdigest()
    return revision, digest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        require(
            not args.output.exists() and not args.output.is_symlink(),
            "fresh_output_required",
        )
        validate_topology(read_json(ROOT / "infra/deployment/staging.compose.json"))
        revision, source_hash = source_identity()
        started = datetime.now(UTC)
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "scripts/tests", "-q"],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=120,
            check=False,
        )
        # The test suite only uses synthetic fixtures; record an output digest,
        # never shell diagnostics, arbitrary commands or environment values.
        output_hash = hashlib.sha256(result.stdout).hexdigest()
        after_revision, after_hash = source_identity()
        require(
            (revision, source_hash) == (after_revision, after_hash),
            "source_changed_during_checks",
        )
        record = {
            "schema_version": 1,
            "environment": "local",
            "synthetic_only": True,
            "source_revision": revision,
            "source_manifest_sha256": source_hash,
            "started_at": started.isoformat(),
            "finished_at": datetime.now(UTC).isoformat(),
            "configuration_sha256": hashlib.sha256(
                (ROOT / "infra/deployment/staging.compose.json").read_bytes()
            ).hexdigest(),
            "checks": [
                {"name": "staging_static_contract", "status": "passed"},
                {
                    "name": "operations_security_regressions",
                    "status": "passed" if result.returncode == 0 else "failed",
                    "exit_code": result.returncode,
                    "command": "python -m unittest discover -s scripts/tests -q",
                    "output_sha256": output_hash,
                },
            ],
            "gates": {
                name: "deferred"
                for name in (
                    "remote_exact_revision_ci",
                    "immutable_image_scan_sbom",
                    "live_tls_edge",
                    "live_least_privilege",
                    "redis_worker_one_beat",
                    "live_s3_scanner",
                    "measured_backup_rpo_rto",
                    "accessibility_performance",
                    "client_uat",
                    "deployment_authorization",
                )
            },
            "deployment_authorized": False,
            "senders_enabled": False,
            "collection_enabled": False,
            "staging_accepted": False,
        }
        args.output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        print(
            json.dumps(
                {
                    "valid": result.returncode == 0,
                    "deployment_authorized": False,
                    "staging_accepted": False,
                }
            )
        )
        return 0 if result.returncode == 0 else 1
    except (ContractError, OSError, ValueError, subprocess.SubprocessError) as error:
        code = str(error) if isinstance(error, ContractError) else "acceptance_check_failed"
        print(json.dumps({"valid": False, "code": code}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
