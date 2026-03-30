"""Stage 2 collect-only recovery helpers and execution."""

from __future__ import annotations

import configparser
import hashlib
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

try:
    import tomllib
except ImportError:  # pragma: no cover - Python 3.11+ in supported environments
    import tomli as tomllib  # type: ignore

from amplihack.staging_safety import validate_fix_batch
from amplihack.utils.process import run_command_with_timeout

from .models import DeltaVerdict, RecoveryBlocker, Stage2ErrorSignature, Stage2Result, StageStatus

_LOCATION_WITH_LINE_RE = re.compile(r"^(?P<path>.+?)(?::\d+)?$")
_NORMALIZED_MESSAGE_PATH_RE = re.compile(r"(/[^:\s]+)+:\d+")


def build_collect_only_command(repo_path: Path) -> list[str]:
    """Build the authoritative repo-root collect-only command."""
    pytest_ini = repo_path / "pytest.ini"
    return ["pytest", "--collect-only", "-c", str(pytest_ini)]


def detect_pytest_config_divergence(repo_path: Path) -> dict[str, str] | None:
    """Report divergent pyproject pytest config without changing the baseline source."""
    pytest_ini = repo_path / "pytest.ini"
    pyproject = repo_path / "pyproject.toml"
    if not pytest_ini.exists() or not pyproject.exists():
        return None

    parsed_ini = configparser.ConfigParser()
    parsed_ini.read(pytest_ini)
    ini_section = dict(parsed_ini["pytest"]) if parsed_ini.has_section("pytest") else {}

    pyproject_data = tomllib.loads(pyproject.read_text())
    pyproject_options = pyproject_data.get("tool", {}).get("pytest", {}).get("ini_options")
    if not isinstance(pyproject_options, dict):
        return None

    normalized_ini = {
        key: " ".join(value.split()) if isinstance(value, str) else str(value)
        for key, value in ini_section.items()
    }
    normalized_pyproject = {
        key: " ".join(str(value).split()) for key, value in pyproject_options.items()
    }

    if normalized_ini == normalized_pyproject:
        return None

    return {
        "diagnostic_code": "pytest-config-divergence",
        "authoritative_config": str(pytest_ini),
        "secondary_config": str(pyproject),
    }


def _normalize_location(raw_location: str) -> str:
    cleaned = raw_location.strip().strip("'\"")
    match = _LOCATION_WITH_LINE_RE.match(cleaned)
    return match.group("path") if match else cleaned


def _normalize_message(raw_message: str) -> str:
    message = raw_message.strip()
    return _NORMALIZED_MESSAGE_PATH_RE.sub(
        lambda match: match.group(0).rsplit(":", 1)[0],
        message,
    )


def _extract_collect_location(line: str) -> str | None:
    if not line.startswith("_") or not line.endswith("_"):
        return None
    without_prefix = line.lstrip("_")
    if without_prefix == line or not without_prefix or not without_prefix[0].isspace():
        return None

    body = without_prefix.lstrip()
    if not body.startswith("ERROR collecting "):
        return None

    location_with_suffix = body[len("ERROR collecting ") :]
    stripped_location = location_with_suffix.rstrip("_ ")
    if stripped_location == location_with_suffix:
        return None

    location = stripped_location.strip()
    if not location:
        return None
    return _normalize_location(location)


def _extract_error_message(line: str) -> str | None:
    if not line.startswith("E "):
        return None
    return line[2:].strip()


def _build_signature(
    *,
    error_type: str,
    headline: str,
    normalized_location: str,
    normalized_message: str,
    occurrences: int = 1,
) -> Stage2ErrorSignature:
    raw_id = "|".join([error_type, headline, normalized_location, normalized_message])
    signature_id = hashlib.sha1(raw_id.encode("utf-8")).hexdigest()[:12]
    return Stage2ErrorSignature(
        signature_id=signature_id,
        error_type=error_type,
        headline=headline,
        normalized_location=normalized_location,
        normalized_message=normalized_message,
        occurrences=occurrences,
    )


def _extract_error_type(message: str) -> tuple[str, str]:
    if ":" in message:
        error_type, headline = message.split(":", 1)
        return error_type.strip().split(".")[-1], headline.strip()
    return "CollectionError", message.strip()


def _record_signature(
    aggregated: dict[tuple[str, str, str, str], int],
    *,
    location: str,
    message: str,
) -> None:
    error_type, headline = _extract_error_type(message)
    normalized_message = _normalize_message(
        headline if error_type != "CollectionError" else message
    )
    key = (error_type, headline, location, normalized_message)
    aggregated[key] = aggregated.get(key, 0) + 1


def build_error_signatures(output: str) -> list[Stage2ErrorSignature]:
    """Normalize pytest collection output into stable error signatures."""
    aggregated: dict[tuple[str, str, str, str], int] = {}
    lines = [line for line in output.splitlines() if line.strip()]
    if not lines:
        return []

    current_location: str | None = None
    saw_collect_block = False
    saw_error_message = False
    for line in lines:
        location = _extract_collect_location(line)
        if location is not None:
            if current_location is not None:
                _record_signature(
                    aggregated,
                    location=current_location,
                    message="Unknown collection failure",
                )
            current_location = location
            saw_collect_block = True
            continue

        message = _extract_error_message(line)
        if message is not None:
            saw_error_message = True

        if current_location is None or message is None:
            continue

        _record_signature(
            aggregated,
            location=current_location,
            message=message,
        )
        current_location = None

    if saw_collect_block:
        if current_location is not None:
            _record_signature(
                aggregated,
                location=current_location,
                message="Unknown collection failure",
            )
    elif saw_error_message:
        location = ""
        first_line = lines[0]
        if "conftest" in first_line:
            location = _normalize_location(first_line.split("conftest", 1)[1])
        error_line = lines[1] if len(lines) > 1 else first_line
        _record_signature(aggregated, location=location, message=error_line)
    else:
        return []

    signatures = [
        _build_signature(
            error_type=error_type,
            headline=headline,
            normalized_location=location,
            normalized_message=normalized_message,
            occurrences=occurrences,
        )
        for (error_type, headline, location, normalized_message), occurrences in aggregated.items()
    ]
    return sorted(
        signatures,
        key=lambda signature: (
            -signature.occurrences,
            signature.normalized_location,
            signature.signature_id,
        ),
    )


def _cluster_root_cause(signature: Stage2ErrorSignature) -> str:
    if signature.error_type == "ModuleNotFoundError" or "No module named" in signature.headline:
        return "Missing dependency or optional dependency gating"
    if signature.error_type == "ImportPathMismatchError":
        return "Pytest import path mismatch between duplicate test packages"
    if signature.error_type in {"ImportError", "AttributeError"}:
        return "Import surface mismatch or missing export"
    return f"Collection failure: {signature.error_type}"


def cluster_signatures(signatures: list[Stage2ErrorSignature]) -> list[dict[str, Any]]:
    """Group related signatures by likely root cause."""
    grouped: dict[tuple[str, str], list[Stage2ErrorSignature]] = {}
    for signature in signatures:
        root_cause = _cluster_root_cause(signature)
        key = (root_cause, signature.normalized_message)
        grouped.setdefault(key, []).append(signature)

    clusters: list[dict[str, Any]] = []
    for (root_cause, normalized_message), items in grouped.items():
        cluster_id = hashlib.sha1(f"{root_cause}|{normalized_message}".encode()).hexdigest()[:12]
        clusters.append(
            {
                "cluster_id": f"cluster-{cluster_id}",
                "root_cause": root_cause,
                "signature_count": len(items),
                "occurrences": sum(item.occurrences for item in items),
                "signature_ids": [item.signature_id for item in items],
            }
        )

    return sorted(clusters, key=lambda cluster: (-cluster["occurrences"], cluster["cluster_id"]))


def determine_delta_verdict(
    baseline: list[Stage2ErrorSignature],
    final: list[Stage2ErrorSignature],
) -> DeltaVerdict:
    """Classify the Stage 2 delta honestly."""
    baseline_ids = {signature.signature_id for signature in baseline}
    final_ids = {signature.signature_id for signature in final}
    baseline_count = sum(signature.occurrences for signature in baseline)
    final_count = sum(signature.occurrences for signature in final)

    if final_ids == baseline_ids and final_count == baseline_count:
        return "unchanged"
    if final_ids.issubset(baseline_ids) and final_count < baseline_count:
        return "reduced"
    return "replaced"


def _candidate_collect_commands(repo_path: Path) -> list[list[str]]:
    base_command = build_collect_only_command(repo_path)
    return [
        base_command,
        [sys.executable, "-m", *base_command],
        ["uv", "run", "python", "-m", *base_command],
    ]


def _run_collect_only(repo_path: Path, *, timeout: int) -> tuple[int, str]:
    last_error: Exception | None = None
    for command in _candidate_collect_commands(repo_path):
        try:
            result = run_command_with_timeout(command, cwd=repo_path, timeout=timeout)
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            last_error = exc
            continue

        output = "\n".join(part for part in [result.stdout, result.stderr] if part).strip()
        return result.returncode, output

    assert last_error is not None
    raise last_error


def _extract_candidate_paths(fix: dict[str, Any]) -> list[str]:
    for key in ("candidate_paths", "files", "paths"):
        value = fix.get(key)
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            return list(value)
    return []


def _stage2_result(
    *,
    status: StageStatus,
    baseline_signatures: list[Stage2ErrorSignature],
    final_signatures: list[Stage2ErrorSignature],
    clusters: list[dict[str, Any]],
    applied_fixes: list[dict[str, Any]],
    diagnostics: list[dict[str, Any]],
    blockers: list[RecoveryBlocker],
) -> Stage2Result:
    return Stage2Result(
        status=status,
        baseline_collection_errors=sum(signature.occurrences for signature in baseline_signatures),
        final_collection_errors=sum(signature.occurrences for signature in final_signatures),
        delta_verdict=determine_delta_verdict(baseline_signatures, final_signatures),
        signatures=final_signatures,
        clusters=clusters,
        applied_fixes=applied_fixes,
        diagnostics=diagnostics,
        blockers=blockers,
    )


def run_stage2(
    repo_path: Path,
    protected_staged_files: list[str],
    *,
    timeout: int = 300,
    fixer: Callable[[list[dict[str, Any]], list[str]], list[dict[str, Any]]] | None = None,
) -> Stage2Result:
    """Execute Stage 2 collect-only recovery."""
    blockers: list[RecoveryBlocker] = []
    diagnostics: list[dict[str, Any]] = []
    if diagnostic := detect_pytest_config_divergence(repo_path):
        diagnostics.append(diagnostic)

    try:
        _returncode, baseline_output = _run_collect_only(repo_path, timeout=timeout)
    except FileNotFoundError as exc:
        blockers.append(
            RecoveryBlocker(
                stage="stage2",
                code="pytest-unavailable",
                message=str(exc),
                retryable=True,
            )
        )
        return _stage2_result(
            status="blocked",
            baseline_signatures=[],
            final_signatures=[],
            clusters=[],
            applied_fixes=[],
            diagnostics=diagnostics,
            blockers=blockers,
        )
    except subprocess.TimeoutExpired as exc:
        blockers.append(
            RecoveryBlocker(
                stage="stage2",
                code="collect-timeout",
                message=str(exc),
                retryable=True,
            )
        )
        return _stage2_result(
            status="blocked",
            baseline_signatures=[],
            final_signatures=[],
            clusters=[],
            applied_fixes=[],
            diagnostics=diagnostics,
            blockers=blockers,
        )

    baseline_signatures = build_error_signatures(baseline_output)
    clusters = cluster_signatures(baseline_signatures)
    applied_fixes: list[dict[str, Any]] = []

    if fixer is not None and clusters:
        for candidate_fix in fixer(clusters, list(protected_staged_files)):
            candidate_paths = _extract_candidate_paths(candidate_fix)
            if candidate_paths:
                try:
                    normalized_paths = validate_fix_batch(
                        repo_path=repo_path,
                        candidate_paths=candidate_paths,
                        protected_staged_files=protected_staged_files,
                    )
                except ValueError as exc:
                    blockers.append(
                        RecoveryBlocker(
                            stage="stage2",
                            code="protected-staged-overlap",
                            message=str(exc),
                            retryable=True,
                        )
                    )
                    return _stage2_result(
                        status="blocked",
                        baseline_signatures=baseline_signatures,
                        final_signatures=baseline_signatures,
                        clusters=clusters,
                        applied_fixes=[],
                        diagnostics=diagnostics,
                        blockers=blockers,
                    )

                if "candidate_paths" in candidate_fix:
                    candidate_fix = {**candidate_fix, "candidate_paths": normalized_paths}
                elif "files" in candidate_fix:
                    candidate_fix = {**candidate_fix, "files": normalized_paths}
                elif "paths" in candidate_fix:
                    candidate_fix = {**candidate_fix, "paths": normalized_paths}
            applied_fixes.append(candidate_fix)

    final_signatures = baseline_signatures
    if applied_fixes:
        try:
            _returncode, final_output = _run_collect_only(repo_path, timeout=timeout)
        except FileNotFoundError as exc:
            blockers.append(
                RecoveryBlocker(
                    stage="stage2",
                    code="pytest-unavailable",
                    message=str(exc),
                    retryable=True,
                )
            )
            return _stage2_result(
                status="blocked",
                baseline_signatures=baseline_signatures,
                final_signatures=baseline_signatures,
                clusters=clusters,
                applied_fixes=applied_fixes,
                diagnostics=diagnostics,
                blockers=blockers,
            )
        except subprocess.TimeoutExpired as exc:
            blockers.append(
                RecoveryBlocker(
                    stage="stage2",
                    code="collect-timeout",
                    message=str(exc),
                    retryable=True,
                )
            )
            return _stage2_result(
                status="blocked",
                baseline_signatures=baseline_signatures,
                final_signatures=baseline_signatures,
                clusters=clusters,
                applied_fixes=applied_fixes,
                diagnostics=diagnostics,
                blockers=blockers,
            )
        final_signatures = build_error_signatures(final_output)

    return _stage2_result(
        status="blocked" if blockers else "completed",
        baseline_signatures=baseline_signatures,
        final_signatures=final_signatures,
        clusters=clusters,
        applied_fixes=applied_fixes,
        diagnostics=diagnostics,
        blockers=blockers,
    )


__all__ = [
    "build_collect_only_command",
    "build_error_signatures",
    "cluster_signatures",
    "detect_pytest_config_divergence",
    "determine_delta_verdict",
    "run_stage2",
]
