"""JSON rendering for recovery workflow results."""

from __future__ import annotations

import json
from dataclasses import fields, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import RecoveryRun


def _format_timestamp(value: datetime) -> str:
    """Render timestamps as canonical UTC ISO-8601 strings."""
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _to_jsonable(value: Any) -> Any:
    """Recursively convert dataclasses, paths, and datetimes to JSONable values."""
    if is_dataclass(value):
        return {field.name: _to_jsonable(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, datetime):
        return _format_timestamp(value)
    if isinstance(value, Path):
        return str(value.resolve())
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    return value


def recovery_run_to_json(run: RecoveryRun) -> dict[str, Any]:
    """Convert a recovery run to a machine-checkable JSON payload."""
    payload = _to_jsonable(run)
    if not isinstance(payload, dict):
        raise TypeError("RecoveryRun JSON payload must be a mapping")
    return payload


def write_recovery_ledger(run: RecoveryRun, output_path: Path) -> None:
    """Write the recovery ledger JSON to *output_path*."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = recovery_run_to_json(run)
    output_path.write_text(f"{json.dumps(payload, indent=2, sort_keys=True)}\n")


__all__ = ["recovery_run_to_json", "write_recovery_ledger"]
