"""Quarantine unsafe state and restore the latest known-good snapshot."""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from observability import append_action
from state_utils import copy_to_quarantine, latest_snapshot, load_json

CASE_ID = "case-demo-001"


def _load_optional_json(path: Path | None) -> dict[str, Any] | None:
    if path and path.exists():
        return load_json(path)
    return None


def rollback(
    output_path: Path,
    snapshot_dir: Path,
    quarantine_dir: Path,
    action_log: Path,
    scan_report_path: Path | None = None,
) -> dict:
    snapshot = latest_snapshot(snapshot_dir)
    if snapshot is None:
        raise FileNotFoundError(f"No snapshot found in {snapshot_dir}")

    scan_report = _load_optional_json(scan_report_path)
    findings = scan_report.get("findings", []) if scan_report else []
    attribution = scan_report.get("attribution") if scan_report else None

    quarantined = copy_to_quarantine(output_path, quarantine_dir, CASE_ID, reason="sensitive-leak")
    shutil.copy2(snapshot, output_path)

    action = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "case_id": CASE_ID,
        "event_type": "recovery_performed",
        "actions": ["quarantine_state", "restore_snapshot"],
        "quarantined_file": str(quarantined),
        "restored_from": str(snapshot),
        "restored_to": str(output_path),
        "status": "completed",
        "triggered_by_findings": findings,
        "attribution": attribution,
    }
    append_action(action_log, action)
    return action


def main() -> None:
    parser = argparse.ArgumentParser(description="Rollback unsafe output to latest known-good snapshot.")
    parser.add_argument("--output", required=True)
    parser.add_argument("--snapshots", required=True)
    parser.add_argument("--quarantine", required=True)
    parser.add_argument("--actionlog", required=True)
    parser.add_argument("--scan-report", required=False, help="Optional scan_report.json to include findings in action log.")
    args = parser.parse_args()

    explicit_scan = Path(args.scan_report) if args.scan_report else None
    default_scan = Path(args.output).resolve().parent.parent / "impact" / "scan_report.json"
    scan_report = explicit_scan or (default_scan if default_scan.exists() else None)

    action = rollback(
        Path(args.output),
        Path(args.snapshots),
        Path(args.quarantine),
        Path(args.actionlog),
        scan_report,
    )
    print("Rollback completed")
    print(f"Quarantined: {action['quarantined_file']}")
    print(f"Restored from: {action['restored_from']}")
    print(f"Findings included: {len(action['triggered_by_findings'])}")


if __name__ == "__main__":
    main()
