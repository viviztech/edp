"""Local fault/recovery samples stay bounded, sanitized and non-delivering."""

import copy
import json
import sys
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from deployment_contract import ROOT, ContractError
from operations_monitor import evaluate


class MonitorTests(unittest.TestCase):
    def setUp(self):
        self.catalog = json.loads((ROOT / "infra/monitoring/signals.json").read_text())
        self.now = datetime.now(UTC)
        self.data = {
            "schema_version": 1,
            "synthetic_only": True,
            "sampled_at": self.now.isoformat(),
            "samples": {
                "database_ready": 0,
                "redis_ready": 0,
                "worker_roundtrip_ok": None,
                "scheduler_instances": 2,
                "outbox_pending_age_seconds": 200,
                "backup_age_seconds": 100,
            },
            "thresholds": {"outbox_pending_age_seconds": 120},
        }

    def test_failure_recovery_and_unknown_are_separate(self):
        failure = evaluate(self.data, self.catalog, self.now)
        self.assertEqual(len(failure["alerts"]), 4)
        self.assertEqual(failure["unavailable"], ["worker_roundtrip_ok"])
        self.assertEqual(failure["unconfigured"], ["backup_age_seconds"])
        self.assertFalse(failure["external_delivery"])
        self.data["samples"].update(
            database_ready=1,
            redis_ready=1,
            scheduler_instances=1,
            outbox_pending_age_seconds=0,
        )
        self.assertEqual(evaluate(self.data, self.catalog, self.now)["alerts"], [])

    def test_untrusted_labels_values_stale_samples_and_real_delivery_rejected(self):
        for name, value in [
            ("email", "private@example.org"),
            ("database_ready", 2),
            ("backup_age_seconds", float("nan")),
            ("api_error_ratio", 2),
            ("redis_ready", "0"),
        ]:
            data = copy.deepcopy(self.data)
            data["samples"][name] = value
            with self.subTest(name=name), self.assertRaises(ContractError):
                evaluate(data, self.catalog, self.now)
        for field, value in [
            ("synthetic_only", False),
            ("sampled_at", (self.now - timedelta(minutes=6)).isoformat()),
        ]:
            data = copy.deepcopy(self.data)
            data[field] = value
            with self.assertRaises(ContractError):
                evaluate(data, self.catalog, self.now)
        self.catalog["external_delivery_enabled"] = True
        with self.assertRaises(ContractError):
            evaluate(self.data, self.catalog, self.now)


if __name__ == "__main__":
    unittest.main()
