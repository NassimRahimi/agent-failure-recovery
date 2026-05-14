"""Typed contracts for the agent failure recovery demo."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AgentRequest(BaseModel):
    """Input contract for one local demo run."""

    case_id: str = Field(..., min_length=1)
    source_path: str
    mode: Literal["safe", "unsafe"] = "unsafe"


class ShoppingItem(BaseModel):
    """A normalized shopping item extracted from notes."""

    name: str
    quantity: str = "1"
    category: str = "general"


class AgentOutput(BaseModel):
    """Source-of-truth output produced by the demo agent.

    This contract is intentionally small. Recovery validation uses it to prove
    that rollback did not break the downstream schema.
    """

    case_id: str
    status: Literal["completed", "needs_review"] = "completed"
    items: list[ShoppingItem]
    summary: str
    generated_at: str = Field(default_factory=utc_now_iso)
    risk_flags: list[str] = Field(default_factory=list)
    internal_note: str | None = None


class RecoveryEvent(BaseModel):
    """Structured runtime event for auditability and attribution."""

    timestamp: str = Field(default_factory=utc_now_iso)
    run_id: str
    operation_id: str | None = None
    case_id: str
    component: str
    event_type: str
    action: str
    status: Literal["allowed", "blocked", "failed", "completed", "warning"]
    target_path: str | None = None
    tool_name: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ScanFinding(BaseModel):
    """One detected failure signal."""

    rule_id: str
    severity: Literal["low", "medium", "high", "critical"]
    location: str
    message: str
    match: str | None = None
    value: str | None = None


class Attribution(BaseModel):
    """Best-effort attribution of an unsafe artifact to a writer event."""

    found: bool
    run_id: str | None = None
    operation_id: str | None = None
    agent_id: str | None = None
    tool_name: str | None = None
    target_path: str | None = None
    timestamp: str | None = None
    event_type: str | None = None


class ScanReport(BaseModel):
    """Scanner output persisted for incident response and rollback."""

    scanned_at: str = Field(default_factory=utc_now_iso)
    output_path: str
    log_path: str | None = None
    failed: bool
    findings: list[ScanFinding]
    attribution: Attribution | None = None
