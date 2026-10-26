"""Exercise release security boundaries without contacting infrastructure."""

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from deployment_contract import (
    GATES,
    ROOT,
    ContractError,
    public_host,
    render_proxy,
    validate_manifest,
    validate_operator_values,
    validate_topology,
)


def manifest():
    return {
        "schema_version": 1,
        "environment": "staging",
        "synthetic_only": True,
        "source_revision": "a" * 40,
        "source_manifest_sha256": "b" * 64,
        "configuration_sha256": "c" * 64,
        "migration_head": "m8c4d0e6f123",
        "images": {
            name: f"registry.example.org/edp/{name}@sha256:{'d' * 64}"
            for name in ("api", "web", "edge")
        },
        "web_origin": "https://staging.example.org",
        "database_roles": {name: f"edp_{name}" for name in ("migration", "api", "worker")},
        "trusted_proxy_ips": ["172.20.0.2"],
        "files_enabled": False,
        "senders_enabled": False,
        "collection_enabled": False,
        "gates": {name: "deferred" for name in GATES},
    }


class ContractTests(unittest.TestCase):
    def test_static_contract_never_authorizes_deployment(self):
        result = validate_manifest(manifest(), "a" * 40)
        self.assertFalse(result["deployment_authorized"])
        self.assertFalse(result["all_release_gates_passed"])
        declared = manifest()
        declared["gates"] = {name: "passed" for name in GATES}
        result = validate_manifest(declared, "a" * 40)
        self.assertTrue(result["declared_release_gates_passed"])
        self.assertFalse(result["all_release_gates_passed"])
        self.assertFalse(result["gate_evidence_verified"])
        validate_topology(json.loads((ROOT / "infra/deployment/staging.compose.json").read_text()))

    def test_mutable_images_shared_owner_and_enabled_delivery_rejected(self):
        for field, value in [
            ("environment", "production"),
            ("synthetic_only", False),
            ("source_revision", "e" * 40),
            ("senders_enabled", True),
            ("files_enabled", True),
            ("collection_enabled", True),
            ("trusted_proxy_ips", ["*"]),
            ("trusted_proxy_ips", ["8.8.8.8"]),
        ]:
            value_manifest = manifest()
            value_manifest[field] = value
            with self.subTest(field=field), self.assertRaises(ContractError):
                validate_manifest(value_manifest, "a" * 40)
        for image in ["edp:latest", "edp:staging", "edp@sha256:bad"]:
            value_manifest = manifest()
            value_manifest["images"]["api"] = image
            with self.assertRaises(ContractError):
                validate_manifest(value_manifest, "a" * 40)
        value_manifest = manifest()
        value_manifest["database_roles"]["api"] = "edp_migration"
        with self.assertRaises(ContractError):
            validate_manifest(value_manifest, "a" * 40)

    def test_http_local_credentials_and_config_injection_rejected(self):
        for origin in [
            "http://staging.example.org",
            "https://localhost",
            "https://u:p@example.org",
            "https://example.org/a",
            "https://example.org?q=secret",
            "https://example.org#x",
            "https://example.org;return 200",
            "https://example.org\nssl_protocols SSLv3",
        ]:
            with self.subTest(origin=origin), self.assertRaises(ContractError):
                public_host(origin)
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "nginx.conf"
            render_proxy("https://staging.example.org", output)
            content = output.read_text()
            self.assertNotIn("__PUBLIC_HOST__", content)
            self.assertNotIn("$request_uri", content)
            self.assertNotIn("$request ", content)
            self.assertIn("proxy_next_upstream off", content)
            with self.assertRaises(ContractError):
                render_proxy("https://staging.example.org", output)

    def test_public_runtime_or_missing_hardening_fails(self):
        base = json.loads((ROOT / "infra/deployment/staging.compose.json").read_text())
        for name, key, value in [
            ("api", "ports", ["8000:8000"]),
            ("worker", "privileged", True),
            ("api", "read_only", False),
            ("beat", "scale", 2),
            ("web", "cap_drop", []),
            ("api", "build", "."),
            ("api", "user", "0:0"),
            ("edge", "volumes", ["/:/host"]),
            ("worker", "logging", {}),
            ("api", "mem_limit", "0"),
        ]:
            data = copy.deepcopy(base)
            data["services"][name][key] = value
            with self.subTest(name=name, key=key), self.assertRaises(ContractError):
                validate_topology(data)

    def test_operator_config_binds_images_origins_proxies_and_distinct_private_inputs(
        self,
    ):
        with tempfile.TemporaryDirectory() as folder:
            release = manifest()
            values = {f"{name.upper()}_IMAGE": value for name, value in release["images"].items()}
            values.update(
                WEB_ORIGIN=release["web_origin"],
                CORS_ORIGINS=json.dumps([release["web_origin"]]),
                TRUSTED_PROXY_IPS="172.20.0.2",
                STAGING_BIND_IP="192.0.2.10",
                STAGING_PRIVATE_NETWORK="edp_private",
                STAGING_EDGE_NETWORK="edp_edge",
            )
            for name in (
                "API_ENV_FILE",
                "WORKER_ENV_FILE",
                "MIGRATION_ENV_FILE",
                "WEB_ENV_FILE",
                "NGINX_CONFIG_FILE",
                "TLS_CERTIFICATE_FILE",
                "TLS_PRIVATE_KEY_FILE",
            ):
                values[name] = str(Path(folder) / name.lower())
            result = validate_operator_values(values, release)
            self.assertFalse(result["deployment_authorized"])
            self.assertFalse(result["file_acl_and_network_runtime_verified"])
            for name, value in [
                ("API_IMAGE", "mutable:latest"),
                ("CORS_ORIGINS", '["*"]'),
                ("TRUSTED_PROXY_IPS", "*"),
                ("STAGING_BIND_IP", "0.0.0.0"),
                ("STAGING_EDGE_NETWORK", "edp_private"),
                ("API_ENV_FILE", values["MIGRATION_ENV_FILE"]),
                ("WEB_ENV_FILE", "relative.env"),
            ]:
                wrong = dict(values)
                wrong[name] = value
                with self.subTest(name=name), self.assertRaises(ContractError):
                    validate_operator_values(wrong, release)


if __name__ == "__main__":
    unittest.main()
