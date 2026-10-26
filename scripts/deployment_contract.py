"""Validate a release contract without deploying or rendering secrets."""

import argparse
import ipaddress
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
IMAGE = re.compile(r"[a-z0-9][a-z0-9./:_-]{0,220}@sha256:[a-f0-9]{64}")
HEX = re.compile(r"[a-f0-9]{64}")
DNS = re.compile(r"(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}")
ROLE = re.compile(r"edp_[a-z0-9_]{1,45}")
GATES = {
    "ci",
    "migration",
    "runtime",
    "restore",
    "security",
    "accessibility",
    "performance",
    "uat",
}
STATUSES = {"passed", "failed", "deferred", "unavailable"}


class ContractError(ValueError):
    """Fixed safe error codes only; never interpolate secret-bearing input."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ContractError(code)


def read_json(path: Path) -> dict:
    require(path.is_file() and not path.is_symlink(), "contract_file_unavailable")
    require(path.stat().st_size <= 1024 * 1024, "contract_file_too_large")

    def unique_object(pairs: list[tuple[str, object]]) -> dict:
        value = {}
        for name, item in pairs:
            require(name not in value, "duplicate_contract_field")
            value[name] = item
        return value

    result = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
    require(isinstance(result, dict), "contract_object_required")
    return result


def public_host(origin: str) -> str:
    require(isinstance(origin, str) and len(origin) < 300, "origin_invalid")
    try:
        value = urlsplit(origin)
        require(
            value.scheme == "https"
            and value.path == ""
            and not value.query
            and not value.fragment
            and not value.username
            and not value.password
            and value.port in {None, 443},
            "origin_invalid",
        )
        host = value.hostname or ""
        require(DNS.fullmatch(host) is not None and host != "localhost", "origin_invalid")
        require(origin in {f"https://{host}", f"https://{host}:443"}, "origin_invalid")
        return host
    except ValueError as error:
        raise ContractError("origin_invalid") from error


def validate_manifest(data: dict, revision: str) -> dict:
    require(
        set(data)
        == {
            "schema_version",
            "environment",
            "synthetic_only",
            "source_revision",
            "source_manifest_sha256",
            "configuration_sha256",
            "migration_head",
            "images",
            "web_origin",
            "database_roles",
            "trusted_proxy_ips",
            "files_enabled",
            "senders_enabled",
            "collection_enabled",
            "gates",
        },
        "manifest_field_inventory_invalid",
    )
    require(
        type(data.get("schema_version")) is int and data["schema_version"] == 1,
        "schema_version_invalid",
    )
    require(
        data.get("environment") == "staging" and data.get("synthetic_only") is True,
        "staging_synthetic_required",
    )
    require(
        re.fullmatch(r"[a-f0-9]{40}", revision) is not None
        and data.get("source_revision") == revision,
        "source_revision_mismatch",
    )
    require(
        HEX.fullmatch(str(data.get("source_manifest_sha256", ""))) is not None,
        "source_manifest_required",
    )
    require(
        HEX.fullmatch(str(data.get("configuration_sha256", ""))) is not None,
        "configuration_identity_required",
    )
    require(
        re.fullmatch(r"[a-z0-9_]{1,80}", str(data.get("migration_head", ""))) is not None,
        "migration_head_required",
    )
    images = data.get("images")
    require(
        isinstance(images, dict) and set(images) == {"api", "web", "edge"},
        "image_set_invalid",
    )
    require(
        all(isinstance(value, str) and IMAGE.fullmatch(value) for value in images.values()),
        "immutable_images_required",
    )
    public_host(data.get("web_origin"))
    roles = data.get("database_roles")
    require(
        isinstance(roles, dict) and set(roles) == {"migration", "api", "worker"},
        "role_set_invalid",
    )
    require(
        all(isinstance(role, str) and ROLE.fullmatch(role) for role in roles.values())
        and len(set(roles.values())) == 3,
        "separate_database_roles_required",
    )
    addresses = data.get("trusted_proxy_ips")
    require(
        isinstance(addresses, list) and 1 <= len(addresses) <= 8,
        "trusted_proxy_required",
    )
    try:
        require(
            all(
                isinstance(item, str)
                and ipaddress.ip_address(item).is_private
                and not ipaddress.ip_address(item).is_loopback
                and not ipaddress.ip_address(item).is_unspecified
                and not ipaddress.ip_address(item).is_multicast
                and not ipaddress.ip_address(item).is_link_local
                for item in addresses
            )
            and len(set(addresses)) == len(addresses),
            "private_proxy_required",
        )
    except (ValueError, TypeError) as error:
        raise ContractError("private_proxy_required") from error
    require(
        data.get("files_enabled") is False
        and data.get("senders_enabled") is False
        and data.get("collection_enabled") is False,
        "initial_capabilities_disabled_required",
    )
    gates = data.get("gates")
    require(
        isinstance(gates, dict)
        and set(gates) == GATES
        and all(isinstance(value, str) and value in STATUSES for value in gates.values()),
        "gate_inventory_invalid",
    )
    return {
        "valid": True,
        "environment": "staging",
        "synthetic_only": True,
        "source_revision": revision,
        "deployment_authorized": False,
        "all_release_gates_passed": False,
        "declared_release_gates_passed": all(value == "passed" for value in gates.values()),
        "gate_evidence_verified": False,
        "gates": gates,
    }


def validate_topology(data: dict) -> None:
    services = data.get("services", {})
    require(
        isinstance(services, dict)
        and set(services) == {"migrate", "api", "worker", "beat", "web", "edge"},
        "service_set_invalid",
    )
    for name, service in services.items():
        require(isinstance(service, dict), "service_definition_invalid")
        require(
            service.get("read_only") is True
            and service.get("cap_drop") == ["ALL"]
            and service.get("security_opt") == ["no-new-privileges:true"],
            "process_hardening_required",
        )
        require(
            not service.get("privileged")
            and not service.get("network_mode")
            and not service.get("pid"),
            "host_access_rejected",
        )
        require(
            service.get("image", "").startswith("${") and ":?" in service["image"],
            "image_input_required",
        )
        require(not service.get("build"), "artifact_build_during_release_rejected")
        require(
            service.get("user") == ("101:101" if name == "edge" else "1000:1000"),
            "nonroot_identity_required",
        )
        require(
            service.get("pids_limit", 0) in range(1, 257)
            and service.get("mem_limit") in {"128m", "256m", "512m", "768m"}
            and service.get("cpus") in {"0.5", "1.0"}
            and service.get("stop_grace_period") == "120s",
            "bounded_runtime_required",
        )
        require(
            service.get("logging")
            == {"driver": "json-file", "options": {"max-size": "10m", "max-file": "3"}},
            "bounded_logging_required",
        )
        require(name == "edge" or not service.get("ports"), "private_services_required")
        volumes = service.get("volumes", [])
        require(
            not volumes
            or name == "edge"
            and volumes
            == [
                {
                    "type": "bind",
                    "source": "${NGINX_CONFIG_FILE:?Rendered reviewed config required}",
                    "target": "/etc/nginx/nginx.conf",
                    "read_only": True,
                }
            ],
            "unexpected_runtime_mount_rejected",
        )
        if name in {"api", "worker", "beat"}:
            env = service.get("environment", {})
            require(
                env.get("APP_ENV") == "staging"
                and all(
                    env.get(flag) == "false"
                    for flag in (
                        "FILES_ENABLED",
                        "FILES_MAINTENANCE_ENABLED",
                        "AUTH_SMTP_ENABLED",
                        "CONTACT_ENQUIRIES_ENABLED",
                    )
                ),
                "initial_capabilities_disabled_required",
            )
            require(
                service["env_file"] != services["migrate"]["env_file"],
                "migration_credentials_in_runtime",
            )
    require(services["beat"].get("scale") == 1, "one_scheduler_required")
    require(
        services["web"].get("environment", {}).get("COOKIE_SECURE") == "true",
        "secure_cookie_required",
    )
    require(
        set(data.get("networks", {})) == {"backend", "edge"}
        and all(network.get("external") is True for network in data.get("networks", {}).values()),
        "preprovisioned_networks_required",
    )


def validate_operator_values(data: dict, manifest: dict) -> dict:
    """Inspect non-secret Compose values without rendering resolved environment."""
    validate_manifest(manifest, manifest.get("source_revision", ""))
    for name in ("api", "web", "edge"):
        require(
            data.get(name.upper() + "_IMAGE") == manifest["images"][name],
            "configured_image_mismatch",
        )
    require(data.get("WEB_ORIGIN") == manifest["web_origin"], "configured_origin_mismatch")
    try:
        origins = json.loads(data.get("CORS_ORIGINS", ""))
    except (TypeError, ValueError) as error:
        raise ContractError("configured_origins_invalid") from error
    require(origins == [manifest["web_origin"]], "configured_origins_invalid")
    require(
        data.get("TRUSTED_PROXY_IPS") == ",".join(manifest["trusted_proxy_ips"]),
        "configured_proxy_mismatch",
    )
    try:
        address = ipaddress.ip_address(data.get("STAGING_BIND_IP", ""))
        require(
            not address.is_unspecified and not address.is_multicast,
            "explicit_bind_address_required",
        )
    except ValueError as error:
        raise ContractError("explicit_bind_address_required") from error
    networks = [data.get("STAGING_PRIVATE_NETWORK"), data.get("STAGING_EDGE_NETWORK")]
    require(
        all(
            isinstance(value, str) and re.fullmatch(r"[a-z][a-z0-9_-]{1,62}", value)
            for value in networks
        )
        and networks[0] != networks[1],
        "separate_network_names_required",
    )
    paths = []
    for name in (
        "API_ENV_FILE",
        "WORKER_ENV_FILE",
        "MIGRATION_ENV_FILE",
        "WEB_ENV_FILE",
        "NGINX_CONFIG_FILE",
        "TLS_CERTIFICATE_FILE",
        "TLS_PRIVATE_KEY_FILE",
    ):
        value = data.get(name)
        require(isinstance(value, str) and 0 < len(value) < 1024, "operator_path_required")
        path = Path(value)
        require(
            path.is_absolute() and not path.resolve().is_relative_to(ROOT),
            "external_operator_path_required",
        )
        paths.append(str(path.resolve()))
    require(len(set(paths)) == len(paths), "separate_operator_files_required")
    return {
        "valid": True,
        "resolved_secrets_printed": False,
        "file_acl_and_network_runtime_verified": False,
        "deployment_authorized": False,
    }


def render_proxy(origin: str, output: Path) -> None:
    host = public_host(origin)
    require(not output.exists() and not output.is_symlink(), "fresh_output_required")
    content = (ROOT / "infra/nginx/staging.conf.template").read_text(encoding="utf-8")
    require(content.count("__PUBLIC_HOST__") == 3, "proxy_template_invalid")
    output.write_text(content.replace("__PUBLIC_HOST__", host), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--render-proxy", type=Path)
    parser.add_argument("--origin")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--operator-values",
        type=Path,
        help="Non-secret JSON mapping of Compose input names; paths only for secret files",
    )
    args = parser.parse_args()
    try:
        validate_topology(read_json(ROOT / "infra/deployment/staging.compose.json"))
        result = {"valid": True, "topology": "static", "deployment_authorized": False}
        if args.manifest:
            revision = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip()
            result = validate_manifest(read_json(args.manifest), revision)
        if args.operator_values:
            require(args.manifest is not None, "manifest_required")
            result["operator_values"] = validate_operator_values(
                read_json(args.operator_values), read_json(args.manifest)
            )
        if args.render_proxy:
            require(args.origin is not None, "origin_required")
            render_proxy(args.origin, args.render_proxy)
        encoded = json.dumps(result, indent=2) + "\n"
        if args.output:
            require(
                not args.output.exists() and not args.output.is_symlink(),
                "fresh_output_required",
            )
            args.output.write_text(encoded, encoding="utf-8")
        print(json.dumps(result))
        return 0
    except (
        ContractError,
        OSError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
    ) as error:
        code = str(error) if isinstance(error, ContractError) else "contract_check_failed"
        print(json.dumps({"valid": False, "code": code}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
