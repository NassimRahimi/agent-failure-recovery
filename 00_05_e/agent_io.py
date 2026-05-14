"""Controlled file IO for the demo agent."""

from __future__ import annotations

from pathlib import Path

from agent_definitions import AGENT
from guardrails import validate_read_path, validate_write_path
from state_utils import atomic_write_json


def read_agent_input(path: str | Path) -> str:
    validate_read_path(path, AGENT.allowed_reads)
    return Path(path).read_text(encoding="utf-8")


def write_agent_output(path: str | Path, payload: dict) -> None:
    validate_write_path(path, AGENT.allowed_writes)
    atomic_write_json(path, payload)
