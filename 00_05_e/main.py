"""Run a local agent simulation and intentionally create a recoverable failure.

The important design choice: every run first creates a clean known-good
baseline from the approved input. It never snapshots a previously unsafe output.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from agent_definitions import AGENT
from agent_io import read_agent_input, write_agent_output
from agent_models import AgentOutput, AgentRequest, RecoveryEvent, ShoppingItem
from observability import append_event, make_operation_id, make_run_id
from state_utils import atomic_write_json, create_snapshot, ensure_runtime_dirs

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "shopping_notes.txt"
OUTPUT_PATH = BASE_DIR / "out" / "shopping_summary.json"
LOG_PATH = BASE_DIR / "logs" / "agent_events.jsonl"
CASE_ID = "case-demo-001"


def build_safe_output(case_id: str, notes: str) -> AgentOutput:
    """Build the known-good, customer-safe output contract."""

    lower_notes = notes.lower()
    items: list[ShoppingItem] = []
    for name, category in [
        ("oats", "breakfast"),
        ("milk", "dairy"),
        ("bananas", "fruit"),
        ("dish soap", "household"),
    ]:
        if name in lower_notes:
            items.append(ShoppingItem(name=name, quantity="1", category=category))

    if not items:
        items.append(ShoppingItem(name="review shopping notes", quantity="1", category="general"))

    return AgentOutput(
        case_id=case_id,
        status="completed",
        items=items,
        summary="Shopping list extracted from the approved input note.",
        risk_flags=[],
        internal_note=None,
    )


def build_unsafe_output(case_id: str, notes: str) -> AgentOutput:
    """Build an intentionally bad output that represents a realistic leak.

    The failure is not a forbidden path. The agent writes to the correct file,
    but it persists sensitive operational context into the output artifact.
    """

    safe = build_safe_output(case_id, notes)
    return safe.model_copy(
        update={
            "status": "needs_review",
            "risk_flags": ["unsafe_internal_note", "sensitive_context_persisted"],
            "internal_note": (
                "DEMO ONLY: original context was incorrectly persisted: "
                "contact demo.customer@example.com, payment card ending in 4821, "
                "and secret token sk-demo-not-a-real-secret."
            ),
        }
    )


def create_known_good_baseline(case_id: str, notes: str, snapshot_dir: Path, run_id: str) -> Path:
    """Create a fresh known-good snapshot for this run.

    This fixes the critical bug where repeated unsafe runs could snapshot the
    already-corrupted output and later roll back to bad state.
    """

    baseline = build_safe_output(case_id, notes)
    atomic_write_json(OUTPUT_PATH, baseline.model_dump())
    snapshot = create_snapshot(OUTPUT_PATH, snapshot_dir, case_id, label="known-good")
    append_event(
        LOG_PATH,
        RecoveryEvent(
            run_id=run_id,
            operation_id=make_operation_id("snapshot"),
            case_id=case_id,
            component=AGENT.agent_id,
            event_type="snapshot_created",
            action="create_known_good_snapshot",
            status="completed",
            target_path=str(snapshot),
            tool_name="create_snapshot",
            details={"source_file": str(OUTPUT_PATH), "baseline_type": "known_good"},
        ),
    )
    return snapshot


def run(mode: str) -> None:
    dirs = ensure_runtime_dirs(BASE_DIR)
    run_id = make_run_id()
    request = AgentRequest(case_id=CASE_ID, source_path=str(DATA_PATH), mode=mode)

    append_event(
        LOG_PATH,
        RecoveryEvent(
            run_id=run_id,
            case_id=request.case_id,
            component=AGENT.agent_id,
            event_type="agent_run_started",
            action="execute_agent",
            status="allowed",
            target_path=str(DATA_PATH),
            details={"mode": mode},
        ),
    )

    read_op = make_operation_id("read")
    append_event(
        LOG_PATH,
        RecoveryEvent(
            run_id=run_id,
            operation_id=read_op,
            case_id=request.case_id,
            component=AGENT.agent_id,
            event_type="tool_invoked",
            action="read_input",
            status="allowed",
            target_path=str(DATA_PATH),
            tool_name="read_agent_input",
        ),
    )
    notes = read_agent_input(DATA_PATH)
    append_event(
        LOG_PATH,
        RecoveryEvent(
            run_id=run_id,
            operation_id=read_op,
            case_id=request.case_id,
            component=AGENT.agent_id,
            event_type="tool_completed",
            action="read_input",
            status="completed",
            target_path=str(DATA_PATH),
            tool_name="read_agent_input",
            details={"output_chars": len(notes)},
        ),
    )

    snapshot = create_known_good_baseline(request.case_id, notes, dirs["snapshot"], run_id)

    output = build_unsafe_output(request.case_id, notes) if mode == "unsafe" else build_safe_output(request.case_id, notes)
    write_op = make_operation_id("write")
    append_event(
        LOG_PATH,
        RecoveryEvent(
            run_id=run_id,
            operation_id=write_op,
            case_id=request.case_id,
            component=AGENT.agent_id,
            event_type="tool_invoked",
            action="write_output",
            status="allowed",
            target_path=str(OUTPUT_PATH),
            tool_name="write_agent_output",
            details={"mode": mode},
        ),
    )
    write_agent_output(OUTPUT_PATH, output.model_dump())
    append_event(
        LOG_PATH,
        RecoveryEvent(
            run_id=run_id,
            operation_id=write_op,
            case_id=request.case_id,
            component=AGENT.agent_id,
            event_type="tool_completed",
            action="write_output",
            status="completed",
            target_path=str(OUTPUT_PATH),
            tool_name="write_agent_output",
            details={"mode": mode, "risk_flags": output.risk_flags},
        ),
    )

    append_event(
        LOG_PATH,
        RecoveryEvent(
            run_id=run_id,
            case_id=request.case_id,
            component=AGENT.agent_id,
            event_type="agent_run_completed",
            action="execute_agent",
            status="completed",
            target_path=str(OUTPUT_PATH),
            details={"mode": mode, "snapshot": str(snapshot)},
        ),
    )

    print(f"Run ID: {run_id}")
    print(f"Mode: {mode}")
    print(f"Snapshot: {snapshot}")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the local agent recovery demo.")
    parser.add_argument("--mode", choices=["safe", "unsafe"], default="unsafe")
    args = parser.parse_args()
    run(args.mode)
