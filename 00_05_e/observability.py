"""Small JSONL event logger used by the recovery workflow."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from agent_models import RecoveryEvent


def make_run_id() -> str:
    return f"run-{uuid4().hex}"


def make_operation_id(prefix: str) -> str:
    safe_prefix = prefix.replace(" ", "-").replace("_", "-").lower()
    return f"{safe_prefix}-{uuid4().hex[:12]}"


def append_event(log_path: str | Path, event: RecoveryEvent) -> None:
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(event.model_dump_json() + "\n")


def read_events(log_path: str | Path) -> list[dict]:
    path = Path(log_path)
    if not path.exists():
        return []

    events: list[dict] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


def append_action(action_log: str | Path, payload: dict) -> None:
    path = Path(action_log)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, sort_keys=True) + "\n")


def read_jsonl(path: str | Path) -> list[dict]:
    file_path = Path(path)
    if not file_path.exists():
        return []
    rows: list[dict] = []
    with file_path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows
