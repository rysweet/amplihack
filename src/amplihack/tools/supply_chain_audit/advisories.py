# File: src/amplihack/tools/supply_chain_audit/advisories.py
"""Built-in advisory database and custom YAML loading.

Ships with known supply chain attacks (Trivy, LiteLLM).
Supports custom advisories via YAML config files.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import yaml

from .models import VALID_ATTACK_VECTORS, Advisory, IOCSet

# ===========================================================================
# Built-in Advisories
# ===========================================================================

BUILTIN_ADVISORIES: dict[str, Advisory] = {
    "GHSA-69fq-xp46-6x23": Advisory(
        id="GHSA-69fq-xp46-6x23",
        title="Trivy Action Compromise",
        description=(
            "The aquasecurity/trivy-action GitHub Action was compromised via "
            "a malicious commit that injected code to exfiltrate CI secrets. "
            "Affected workflows that used mutable tags (not SHA-pinned) during "
            "the exposure window may have leaked environment variables and secrets."
        ),
        attack_vector="actions",
        exposure_window_start=datetime(2025, 1, 13, 0, 0, 0, tzinfo=UTC),
        exposure_window_end=datetime(2025, 1, 14, 23, 59, 59, tzinfo=UTC),
        compromised_versions=["v0.18.0", "v0.19.0", "v0.20.0"],
        package_name="aquasecurity/trivy-action",
        safe_versions=[],
        safe_shas=[],
        iocs=IOCSet(
            domains=["tpcp-docs.github.io"],
            ips=[],
            file_patterns=[],
        ),
    ),
    "PYPI-LITELLM-2025": Advisory(
        id="PYPI-LITELLM-2025",
        title="LiteLLM Malicious PyPI Release",
        description=(
            "Malicious versions 1.82.7 and 1.82.8 of the litellm PyPI package "
            "were published containing a backdoor that installed .pth files for "
            "persistent code execution. CI pipelines that installed these versions "
            "during the exposure window may have been compromised."
        ),
        attack_vector="pypi",
        exposure_window_start=datetime(2025, 3, 17, 0, 0, 0, tzinfo=UTC),
        exposure_window_end=datetime(2025, 3, 19, 23, 59, 59, tzinfo=UTC),
        compromised_versions=["1.82.7", "1.82.8"],
        package_name="litellm",
        safe_versions=["1.82.6", "1.82.9"],
        safe_shas=[],
        iocs=IOCSet(
            domains=[],
            ips=[],
            file_patterns=["*.pth"],
        ),
    ),
}


# ===========================================================================
# Lookup Functions
# ===========================================================================


def get_advisory(advisory_id: str) -> Advisory | None:
    """Look up an advisory by exact ID. Case-sensitive."""
    return BUILTIN_ADVISORIES.get(advisory_id)


def list_advisories(config: str | None = None) -> list[Advisory]:
    """List all available advisories (built-in + optional custom config)."""
    result = list(BUILTIN_ADVISORIES.values())
    if config:
        custom = load_custom_advisories(config)
        existing_ids = {a.id for a in result}
        for adv in custom:
            if adv.id not in existing_ids:
                result.append(adv)
    return result


# ===========================================================================
# Custom YAML Loading
# ===========================================================================

_MAX_YAML_SIZE = 64 * 1024  # 64KB

_REQUIRED_FIELDS = [
    "id",
    "title",
    "description",
    "attack_vector",
    "exposure_window",
    "compromised_versions",
    "package_name",
]


def _validate_path(path_str: str) -> Path:
    """Validate and resolve a YAML config path safely.

    Rejects path traversal (``..``) and symlinks that resolve to
    non-regular files.
    """
    if ".." in path_str:
        raise ValueError(f"Path traversal rejected: {path_str}")
    p = Path(path_str)
    if not p.exists():
        raise FileNotFoundError(f"Advisory config not found: {path_str}")
    resolved = p.resolve()
    if not resolved.is_file():
        raise ValueError(f"Path is not a regular file: {path_str}")
    return p


def _parse_advisory_dict(data: dict) -> Advisory:
    """Parse a single advisory dict from YAML into an Advisory object."""
    window = data.get("exposure_window", {})
    if not isinstance(window, dict):
        raise ValueError("exposure_window must be a dict with 'start' and 'end'")
    if "start" not in window:
        raise ValueError("exposure_window missing required field: 'start'")
    if "end" not in window:
        raise ValueError("exposure_window missing required field: 'end'")
    start_str = window["start"]
    end_str = window["end"]

    start = datetime.fromisoformat(str(start_str).replace("Z", "+00:00"))
    end = datetime.fromisoformat(str(end_str).replace("Z", "+00:00"))

    iocs_data = data.get("iocs", {})
    iocs = IOCSet(
        domains=iocs_data.get("domains", []),
        ips=iocs_data.get("ips", []),
        file_patterns=iocs_data.get("file_patterns", []),
    )

    return Advisory(
        id=data["id"],
        title=data["title"],
        description=data["description"],
        attack_vector=data["attack_vector"],
        exposure_window_start=start,
        exposure_window_end=end,
        compromised_versions=data["compromised_versions"],
        package_name=data["package_name"],
        safe_versions=data.get("safe_versions", []),
        safe_shas=data.get("safe_shas", []),
        iocs=iocs,
    )


def load_custom_advisories(path: str) -> list[Advisory]:
    """Load custom advisories from a YAML config file.

    Args:
        path: Path to YAML file (single advisory dict or list of dicts).

    Returns:
        List of Advisory objects.

    Raises:
        FileNotFoundError: If path doesn't exist.
        ValueError: If file exceeds 64KB, has invalid YAML, or fails schema.
    """
    p = _validate_path(path)

    size = os.path.getsize(p)
    if size > _MAX_YAML_SIZE:
        raise ValueError(f"Advisory YAML file exceeds 64KB limit ({size} bytes)")

    raw = p.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML syntax: {e}") from e

    if data is None:
        raise ValueError("YAML file is empty")

    if isinstance(data, dict):
        entries = [data]
    elif isinstance(data, list):
        entries = data
    else:
        raise ValueError("YAML must be a dict or list of dicts")

    advisories = []
    for entry in entries:
        advisories.append(_parse_advisory_dict(entry))
    return advisories


# ===========================================================================
# Schema Validation
# ===========================================================================


def validate_advisory_yaml(path: str) -> list[str]:
    """Validate a custom advisory YAML file against the schema.

    Returns:
        List of error strings. Empty list means valid.
    """
    errors: list[str] = []

    try:
        p = _validate_path(path)
    except (FileNotFoundError, ValueError) as e:
        return [str(e)]

    size = os.path.getsize(p)
    if size > _MAX_YAML_SIZE:
        return [f"File exceeds 64KB limit ({size} bytes)"]

    raw = p.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        return [f"Invalid YAML syntax: {e}"]

    if data is None:
        return ["YAML file is empty"]

    if isinstance(data, dict):
        entries = [data]
    elif isinstance(data, list):
        entries = data
    else:
        return ["YAML must be a dict or list of dicts"]

    for i, entry in enumerate(entries):
        prefix = f"Entry {i}: " if len(entries) > 1 else ""
        if not isinstance(entry, dict):
            errors.append(f"{prefix}Entry must be a dict")
            continue

        for field_name in _REQUIRED_FIELDS:
            if field_name not in entry:
                errors.append(f"{prefix}Missing required field: {field_name}")

        if "attack_vector" in entry:
            if entry["attack_vector"] not in VALID_ATTACK_VECTORS:
                errors.append(
                    f"{prefix}Invalid attack_vector: {entry['attack_vector']!r}. "
                    f"Must be one of {sorted(VALID_ATTACK_VECTORS)}"
                )

        if "exposure_window" in entry:
            window = entry["exposure_window"]
            if isinstance(window, dict):
                start_str = window.get("start", "")
                end_str = window.get("end", "")
                try:
                    start = datetime.fromisoformat(str(start_str).replace("Z", "+00:00"))
                    end = datetime.fromisoformat(str(end_str).replace("Z", "+00:00"))
                    if end < start:
                        errors.append(f"{prefix}Exposure window end is before start")
                except (ValueError, TypeError) as e:
                    errors.append(f"{prefix}Invalid exposure_window dates: {e}")

        if "compromised_versions" in entry:
            cv = entry["compromised_versions"]
            if not isinstance(cv, list) or len(cv) == 0:
                errors.append(f"{prefix}compromised_versions must be a non-empty list")

    return errors
