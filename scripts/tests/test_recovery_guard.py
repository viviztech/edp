"""Recovery rejects missing/tampered/unsafe synthetic artifacts without mutation."""

import copy
import hashlib
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from deployment_contract import ContractError
from recovery_guard import artifact, validate_recovery


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        (self.folder / "database.dump").write_bytes(b"synthetic dump fixture")
        (self.folder / "object.bin").write_bytes(b"synthetic object fixture")
        self.data = {
            "schema_version": 1,
            "synthetic_only": True,
            "outbound_disabled": True,
            "scheduler_stopped": True,
            "deletion_ledger_reconciled": True,
            "outbox_reconciled": True,
            "source_database": "edp_ops_drill_012345abcdef_source",
            "source_revision": "a" * 40,
            "configuration_sha256": "b" * 64,
            "migration_head": "head_fixture",
            "recovery_point": datetime.now(UTC).isoformat(),
            "database_backup": "database.dump",
            "database_sha256": hashlib.sha256(
                (self.folder / "database.dump").read_bytes()
            ).hexdigest(),
            "objects": [
                {
                    "reference": "c" * 64,
                    "organization_id": str(uuid4()),
                    "version": "exact-fixture-v1",
                    "sha256": hashlib.sha256((self.folder / "object.bin").read_bytes()).hexdigest(),
                    "byte_length": 24,
                    "encryption": "aws:kms",
                    "key_available": True,
                    "file": "object.bin",
                    "access": "active",
                    "legal_hold": True,
                    "retained_until": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
                }
            ],
        }

    def tearDown(self):
        self.temp.cleanup()

    def test_held_expired_bytes_retained_but_never_claim_live_storage(self):
        self.data["objects"][0]["byte_length"] = (self.folder / "object.bin").stat().st_size
        result = validate_recovery(self.data, self.folder)
        self.assertEqual(result["objects_verified"], 1)
        self.assertFalse(result["live_storage_verified"])

    def test_wrong_checksum_missing_version_key_or_scope_fail_closed(self):
        for key, value in [
            ("sha256", "f" * 64),
            ("version", ""),
            ("key_available", False),
            ("organization_id", "wrong"),
            ("byte_length", 1),
            ("encryption", "none"),
        ]:
            data = copy.deepcopy(self.data)
            data["objects"][0][key] = value
            with self.subTest(key=key), self.assertRaises(ContractError):
                validate_recovery(data, self.folder)

    def test_revoked_and_disposed_objects_cannot_resurrect_bytes(self):
        for access in ("revoked", "disposed"):
            data = copy.deepcopy(self.data)
            data["objects"][0]["access"] = access
            with self.assertRaises(ContractError):
                validate_recovery(data, self.folder)
            data["objects"][0]["file"] = None
            result = validate_recovery(data, self.folder)
            self.assertEqual(result["objects_inaccessible"], 1)

    def test_missing_dump_tamper_target_escape_and_replay_fail(self):
        for key, value in [
            ("source_database", "production"),
            ("synthetic_only", False),
            ("outbound_disabled", False),
            ("scheduler_stopped", False),
            ("deletion_ledger_reconciled", False),
            ("outbox_reconciled", False),
            ("database_backup", "../database.dump"),
            ("database_sha256", "f" * 64),
        ]:
            data = copy.deepcopy(self.data)
            data[key] = value
            with self.subTest(key=key), self.assertRaises(ContractError):
                validate_recovery(data, self.folder)
        (self.folder / "database.dump").unlink()
        with self.assertRaises(ContractError):
            validate_recovery(self.data, self.folder)

    def test_unsafe_artifact_paths_are_refused(self):
        for name in ("/absolute", "../parent", "C:/private", "dir\\private", "missing"):
            with self.subTest(name=name), self.assertRaises(ContractError):
                artifact(self.folder, name)


if __name__ == "__main__":
    unittest.main()
