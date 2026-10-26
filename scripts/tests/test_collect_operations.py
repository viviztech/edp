"""Reject live targets before connecting and preserve unavailable worker evidence."""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from collect_operations import collect, synthetic_database
from deployment_contract import ContractError


class ProbeTests(unittest.TestCase):
    def test_live_targets_are_rejected_without_connection(self):
        for url in (
            "postgresql://user@127.0.0.1/production",
            "postgresql://user@database.example.org/edp_test",
            "postgresql://user@127.0.0.1/edp_dev",
            "postgresql://user@127.0.0.1/edp_test?hostaddr=8.8.8.8",
            "postgresql://user@127.0.0.1/edp_test?service=external",
        ):
            with self.subTest(url=url), self.assertRaises(ContractError):
                synthetic_database(url)
        self.assertEqual(
            synthetic_database("postgresql://user@127.0.0.1/edp_test")["dbname"], "edp_test"
        )

    def test_dependency_failure_is_sanitized_and_does_not_invent_worker_health(self):
        with patch(
            "collect_operations.psycopg.connect", side_effect=psycopg.OperationalError("private")
        ):
            result = collect("postgresql://user@127.0.0.1/edp_test")
        self.assertEqual(result["samples"]["database_ready"], 0)
        self.assertIsNone(result["samples"]["worker_roundtrip_ok"])
        self.assertIsNone(result["samples"]["redis_ready"])
        self.assertNotIn("private", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
