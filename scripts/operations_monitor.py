"""Validate bounded operations samples and record alerts locally without delivery."""

import argparse
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

from deployment_contract import ROOT, ContractError, read_json, require
from recovery_guard import utc_time


def evaluate(data: dict, catalog: dict, now: datetime | None = None) -> dict:
    current = now or datetime.now(UTC)
    require(
        data.get("schema_version") == 1 and data.get("synthetic_only") is True,
        "synthetic_snapshot_required",
    )
    sampled = utc_time(data.get("sampled_at"))
    require(0 <= (current - sampled).total_seconds() <= 300, "fresh_snapshot_required")
    require(catalog.get("external_delivery_enabled") is False, "external_delivery_rejected")
    signals = catalog.get("signals", {})
    samples = data.get("samples")
    require(
        isinstance(samples, dict) and 1 <= len(samples) <= len(signals),
        "sample_inventory_invalid",
    )
    thresholds = data.get("thresholds", {})
    require(
        isinstance(thresholds, dict) and set(thresholds) <= set(signals),
        "threshold_inventory_invalid",
    )
    alerts = []
    unconfigured = []
    unavailable = []
    for name, value in samples.items():
        require(name in signals, "unknown_signal_rejected")
        spec = signals[name]
        if value is None:
            unavailable.append(name)
            continue
        require(
            type(value) in {int, float} and math.isfinite(value) and value >= 0,
            "signal_value_invalid",
        )
        if spec["unit"] == "boolean":
            require(value in {0, 1}, "boolean_signal_invalid")
        if spec["unit"] == "ratio":
            require(value <= 1, "ratio_signal_invalid")
        failed = spec.get("failure") == "zero" and value == 0
        failed = failed or spec.get("failure") == "not_one" and value != 1
        if spec.get("threshold_required"):
            threshold = thresholds.get(name)
            if threshold is None:
                unconfigured.append(name)
            else:
                require(
                    type(threshold) in {int, float} and math.isfinite(threshold) and threshold > 0,
                    "threshold_value_invalid",
                )
                failed = value > threshold
        if failed:
            alerts.append({"signal": name, "runbook": spec["runbook"], "status": "firing"})
    return {
        "schema_version": 1,
        "synthetic_only": True,
        "sink": "local_recording",
        "external_delivery": False,
        "sampled_at": sampled.isoformat(),
        "alerts": alerts,
        "unavailable": unavailable,
        "unconfigured": unconfigured,
        "omitted": sorted(set(signals) - set(samples)),
        "accepted_for_live_monitoring": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        catalog = read_json(ROOT / "infra/monitoring/signals.json")
        result = evaluate(read_json(args.snapshot), catalog)
        require(
            not args.output.exists() and not args.output.is_symlink(),
            "fresh_output_required",
        )
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(
            json.dumps(
                {
                    "valid": True,
                    "alerts": len(result["alerts"]),
                    "external_delivery": False,
                }
            )
        )
        return 0
    except (ContractError, OSError, ValueError) as error:
        code = str(error) if isinstance(error, ContractError) else "monitor_check_failed"
        print(json.dumps({"valid": False, "code": code}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
