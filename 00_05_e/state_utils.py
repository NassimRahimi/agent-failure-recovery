"""State helpers for snapshots, atomic writes, and generated folders."""

from __future__ import annotations

import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def utc_stamp() -> str:
    """Filename-safe UTC timestamp with microseconds."""

    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def ensure_runtime_dirs(base_dir: str | Path) -> dict[str, Path]:
    base = Path(base_dir)
    dirs = {
        "out": base / "out",
        "logs": base / "logs",
        "snapshot": base / "snapshot",
        "quarantine": base / "quarantine",
        "impact": base / "impact",
    }
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def load_json(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)


def atomic_write_json(path: str | Path, payload: dict) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=target.parent, suffix=".tmp") as tmp:
        json.dump(payload, tmp, indent=2, sort_keys=True)
        tmp.write("\n")
        tmp_path = Path(tmp.name)
    tmp_path.replace(target)


def latest_snapshot(snapshot_dir: str | Path) -> Path | None:
    snapshots = list(Path(snapshot_dir).glob("*.snapshot.json"))
    if not snapshots:
        snapshots = list(Path(snapshot_dir).glob("*.json"))
    if not snapshots:
        return None
    return sorted(snapshots, key=lambda p: (p.stat().st_mtime_ns, p.name), reverse=True)[0]


def create_snapshot(source_file: str | Path, snapshot_dir: str | Path, case_id: str, label: str = "known-good") -> Path:
    source = Path(source_file)
    if not source.exists():
        raise FileNotFoundError(f"Cannot snapshot missing file: {source}")
    unique = uuid4().hex[:8]
    safe_label = label.replace(" ", "-").replace("_", "-").lower()
    target = Path(snapshot_dir) / f"{case_id}.{safe_label}.{utc_stamp()}.{unique}.snapshot.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return target


def copy_to_quarantine(source_file: str | Path, quarantine_dir: str | Path, case_id: str, reason: str = "unsafe-state") -> Path:
    source = Path(source_file)
    if not source.exists():
        raise FileNotFoundError(f"Cannot quarantine missing file: {source}")
    safe_reason = reason.replace(" ", "-").replace("_", "-").lower()
    unique = uuid4().hex[:8]
    target = Path(quarantine_dir) / f"{case_id}.{safe_reason}.{utc_stamp()}.{unique}.quarantine.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return target
