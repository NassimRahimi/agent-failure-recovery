"""Scan agent output and logs for failure signals, then attribute the writer."""

from __future__ import annotations

import argparse
from pathlib import Path

from agent_models import Attribution, ScanFinding, ScanReport
from guardrails import detect_sensitive_content
from observability import read_events
from state_utils import atomic_write_json, ensure_runtime_dirs, load_json

BASE_DIR = Path(__file__).resolve().parent


def _same_path(left: str | None, right: Path) -> bool:
    if not left:
        return False
    try:
        return Path(left).resolve() == right.resolve()
    except OSError:
        return str(left) == str(right)


def attribute_writer(output_path: Path, log_path: Path | None) -> Attribution:
    """Find the latest successful write event for the scanned output artifact."""

    if not log_path or not log_path.exists():
        return Attribution(found=False)

    events = read_events(log_path)
    for event in reversed(events):
        if (
            event.get("event_type") in {"tool_completed", "agent_output_written"}
            and event.get("action") == "write_output"
            and event.get("status") == "completed"
            and _same_path(event.get("target_path"), output_path)
        ):
            return Attribution(
                found=True,
                run_id=event.get("run_id"),
                operation_id=event.get("operation_id"),
                agent_id=event.get("component"),
                tool_name=event.get("tool_name"),
                target_path=event.get("target_path"),
                timestamp=event.get("timestamp"),
                event_type=event.get("event_type"),
            )
    return Attribution(found=False)


def scan(output_path: Path, log_path: Path | None) -> ScanReport:
    findings: list[ScanFinding] = []
    payload = load_json(output_path)

    for item in detect_sensitive_content(payload):
        findings.append(ScanFinding(**item))

    if log_path and log_path.exists():
        for index, event in enumerate(read_events(log_path)):
            if event.get("status") in {"blocked", "failed"}:
                findings.append(
                    ScanFinding(
                        rule_id="runtime-event-failure",
                        severity="high",
                        location=f"log[{index}]",
                        message="Runtime log contains a blocked or failed event.",
                        match=event.get("event_type"),
                        value=event.get("status"),
                    )
                )

    attribution = attribute_writer(output_path, log_path)
    return ScanReport(
        output_path=str(output_path),
        log_path=str(log_path) if log_path else None,
        failed=bool(findings),
        findings=findings,
        attribution=attribution,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan output and logs for unsafe agent behavior.")
    parser.add_argument("--output", required=True)
    parser.add_argument("--log", required=False)
    args = parser.parse_args()

    dirs = ensure_runtime_dirs(BASE_DIR)
    report = scan(Path(args.output), Path(args.log) if args.log else None)
    report_path = dirs["impact"] / "scan_report.json"
    atomic_write_json(report_path, report.model_dump())

    print(f"Scan failed: {report.failed}")
    print(f"Findings: {len(report.findings)}")
    if report.attribution and report.attribution.found:
        print(
            "Attribution: "
            f"agent={report.attribution.agent_id}, "
            f"tool={report.attribution.tool_name}, "
            f"run={report.attribution.run_id}, "
            f"op={report.attribution.operation_id}"
        )
    else:
        print("Attribution: not found")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
