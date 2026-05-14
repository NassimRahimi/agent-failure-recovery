"""Assess blast radius by comparing current state with the latest known-good snapshot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from deepdiff import DeepDiff
except ImportError:  # pragma: no cover
    DeepDiff = None

from guardrails import detect_sensitive_content
from state_utils import atomic_write_json, ensure_runtime_dirs, latest_snapshot, load_json

BASE_DIR = Path(__file__).resolve().parent


def summarize_diff(diff: object) -> dict[str, int]:
    if isinstance(diff, dict):
        return {key: len(value) if hasattr(value, "__len__") else 1 for key, value in diff.items()}
    return {"raw_diff_available": 1 if diff else 0}


def assess(snapshot_dir: Path, current_path: Path) -> dict:
    snapshot = latest_snapshot(snapshot_dir)
    if snapshot is None:
        return {
            "status": "failed",
            "reason": "No snapshot available.",
            "snapshot": None,
            "current": str(current_path),
            "impact_level": "unknown",
            "diff_summary": {},
            "sensitive_findings": [],
        }

    before = load_json(snapshot)
    after = load_json(current_path)

    if DeepDiff:
        deep_diff = DeepDiff(before, after, ignore_order=True)
        diff_payload = json.loads(deep_diff.to_json())
    else:
        diff_payload = {"before": before, "after": after}

    changed_keys = {key for key in set(before) | set(after) if before.get(key) != after.get(key)}
    sensitive_findings = detect_sensitive_content(after)
    high_risk_keys = {"internal_note", "risk_flags", "status"}

    if sensitive_findings:
        impact_level = "high"
    elif changed_keys & high_risk_keys:
        impact_level = "medium"
    elif changed_keys:
        impact_level = "low"
    else:
        impact_level = "none"

    return {
        "status": "completed",
        "snapshot": str(snapshot),
        "current": str(current_path),
        "changed_top_level_keys": sorted(changed_keys),
        "impact_level": impact_level,
        "diff_summary": summarize_diff(diff_payload),
        "sensitive_findings": sensitive_findings,
        "diff": diff_payload,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Assess impact against the latest known-good snapshot.")
    parser.add_argument("--snapshots", required=True)
    parser.add_argument("--current", required=True)
    args = parser.parse_args()

    dirs = ensure_runtime_dirs(BASE_DIR)
    report = assess(Path(args.snapshots), Path(args.current))
    report_path = dirs["impact"] / "impact_report.json"
    atomic_write_json(report_path, report)

    print(f"Impact level: {report.get('impact_level')}")
    print(f"Changed keys: {', '.join(report.get('changed_top_level_keys', [])) or 'none'}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
