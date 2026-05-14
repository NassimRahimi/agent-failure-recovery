"""Runtime guardrails and output scanners for the recovery demo."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from agent_definitions import POLICY

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
CARD_LAST_FOUR_RE = re.compile(r"\b(?:card|credit card|payment card|ending in|last four)\D{0,30}(?P<last4>\d{4})\b", re.IGNORECASE)
SECRET_TOKEN_RE = re.compile(r"\b(?:sk|tok|key)-[A-Za-z0-9_-]{8,}\b", re.IGNORECASE)

SENSITIVE_RULES: tuple[tuple[str, str, re.Pattern[str], str], ...] = (
    ("email-address", "high", EMAIL_RE, "Email address persisted in agent output."),
    ("payment-card-last-four", "critical", CARD_LAST_FOUR_RE, "Payment card last-four digits persisted in agent output."),
    ("secret-token", "critical", SECRET_TOKEN_RE, "Secret-like token persisted in agent output."),
    ("sensitive-keyword", "high", re.compile(r"\b(password|secret|api[_-]?key|token|confidential|ssn)\b", re.IGNORECASE), "Sensitive keyword persisted in agent output."),
)


def resolve_path(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def is_within_allowed_path(path: str | Path, allowed_roots: Iterable[Path]) -> bool:
    candidate = resolve_path(path)
    for root in allowed_roots:
        try:
            candidate.relative_to(resolve_path(root))
            return True
        except ValueError:
            continue
    return False


def validate_write_path(path: str | Path, allowed_roots: Iterable[Path]) -> None:
    candidate = resolve_path(path)
    if candidate.suffix not in POLICY.allowed_output_extensions and candidate.name != "agent_events.jsonl":
        raise ValueError(f"Blocked write: unsupported file type {candidate.suffix!r}")
    if not is_within_allowed_path(candidate, allowed_roots):
        raise ValueError(f"Blocked write outside allowed paths: {candidate}")


def validate_read_path(path: str | Path, allowed_roots: Iterable[Path]) -> None:
    if not is_within_allowed_path(path, allowed_roots):
        raise ValueError(f"Blocked read outside allowed paths: {resolve_path(path)}")


def flatten_json(value: object, prefix: str = "$") -> list[tuple[str, str]]:
    flattened: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            flattened.extend(flatten_json(item, f"{prefix}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            flattened.extend(flatten_json(item, f"{prefix}[{index}]"))
    elif value is not None:
        flattened.append((prefix, str(value)))
    return flattened


def detect_sensitive_content(payload: object) -> list[dict[str, str]]:
    """Return high-signal sensitive-data findings from any JSON-like payload."""

    findings: list[dict[str, str]] = []
    for location, text in flatten_json(payload):
        for rule_id, severity, pattern, message in SENSITIVE_RULES:
            for match in pattern.finditer(text):
                value = match.groupdict().get("last4") if match.groupdict() else None
                findings.append(
                    {
                        "rule_id": rule_id,
                        "severity": severity,
                        "location": location,
                        "message": message,
                        "match": match.group(0),
                        "value": value or match.group(0),
                    }
                )
    return findings
