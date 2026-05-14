"""Agent and policy metadata for the recovery demo."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class AgentDefinition:
    agent_id: str
    name: str
    purpose: str
    allowed_reads: tuple[Path, ...]
    allowed_writes: tuple[Path, ...]
    max_recovery_attempts: int = 1
    risk_tier: str = "demo"


@dataclass(frozen=True)
class RuntimePolicy:
    blocked_terms: tuple[str, ...] = (
        "password",
        "secret",
        "api_key",
        "token",
        "confidential",
        "ssn",
    )
    allowed_output_extensions: tuple[str, ...] = (".json",)
    required_event_fields: tuple[str, ...] = (
        "timestamp",
        "run_id",
        "case_id",
        "component",
        "event_type",
        "action",
        "status",
    )
    recovery_actions: tuple[str, ...] = (
        "detect_failure",
        "attribute_writer",
        "assess_impact",
        "quarantine_state",
        "restore_snapshot",
        "validate_recovery",
    )


AGENT = AgentDefinition(
    agent_id="agent.recovery-demo.v1",
    name="Recovery Demo Agent",
    purpose="Demonstrates controlled agent execution, failure detection, rollback, and validation.",
    allowed_reads=(BASE_DIR / "data",),
    allowed_writes=(
        BASE_DIR / "out",
        BASE_DIR / "logs",
        BASE_DIR / "snapshot",
        BASE_DIR / "impact",
        BASE_DIR / "quarantine",
    ),
)

POLICY = RuntimePolicy()
