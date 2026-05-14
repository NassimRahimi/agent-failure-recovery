"""Validate that recovery restored safe state and preserved audit evidence."""

from __future__ import annotations

import argparse
from pathlib import Path

from agent_models import AgentOutput
from guardrails import detect_sensitive_content
from observability import read_jsonl
from state_utils import latest_snapshot, load_json


def validate_schema(payload: dict) -> tuple[bool, str | None]:
    try:
        AgentOutput.model_validate(payload)
        return True, None
    except Exception as exc:  # pydantic provides useful details, but keep CLI compact
        return False, str(exc)


def validate(output_path: Path, snapshot_dir: Path, action_log: Path, quarantine_dir: Path) -> dict:
    if not output_path.exists():
        return {"status": "failed", "reason": "Output file is missing."}

    payload = load_json(output_path)
    schema_ok, schema_error = validate_schema(payload)
    findings = detect_sensitive_content(payload)
    actions = read_jsonl(action_log)
    snapshot = latest_snapshot(snapshot_dir)
    quarantined_files = list(quarantine_dir.glob("*.quarantine.json")) if quarantine_dir.exists() else []

    recovery_events = [
        action
        for action in actions
        if action.get("event_type") == "recovery_performed" and action.get("status") == "completed"
    ]

    restored = bool(recovery_events)
    has_quarantine = bool(quarantined_files)
    safe = not findings
    has_snapshot = snapshot is not None

    issues: list[str] = []
    if not schema_ok:
        issues.append("Recovered output does not match AgentOutput schema.")
    if not safe:
        issues.append("Recovered output still contains sensitive content.")
    if not restored:
        issues.append("No recovery_performed event found in the action log.")
    if not has_quarantine:
        issues.append("No quarantined artifact found.")
    if not has_snapshot:
        issues.append("No known-good snapshot found.")

    status = "passed" if not issues else "failed"
    return {
        "status": status,
        "schema_ok": schema_ok,
        "schema_error": schema_error,
        "safe_output": safe,
        "rollback_logged": restored,
        "quarantine_present": has_quarantine,
        "latest_snapshot": str(snapshot) if snapshot else None,
        "finding_count": len(findings),
        "issues": issues,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate rollback recovery.")
    parser.add_argument("--output", required=True)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--action-log", required=True)
    parser.add_argument("--quarantine", required=True)
    args = parser.parse_args()

    result = validate(Path(args.output), Path(args.snapshot), Path(args.action_log), Path(args.quarantine))
    print(result)
    if result["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
