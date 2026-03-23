"""Context parsing and inference helpers for recipe CLI commands."""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

ContextArg = str | list[str]
ContextArgs = list[ContextArg]


def _iter_context_assignments(ctx_arg: ContextArg) -> Iterator[str]:
    """Yield normalized ``key=value`` assignments from raw CLI context tokens."""
    if isinstance(ctx_arg, str):
        yield ctx_arg
        return

    current: str | None = None
    for token in ctx_arg:
        if "=" in token:
            if current is not None:
                yield current
            current = token
            continue
        if current is None:
            yield token
            continue
        current = f"{current} {token}"

    if current is not None:
        yield current


def parse_context_args(context_args: ContextArgs) -> tuple[dict[str, str], list[str]]:
    """Parse context key=value arguments from direct or argparse-style inputs."""
    context: dict[str, str] = {}
    errors: list[str] = []

    for ctx_arg in context_args:
        for assignment in _iter_context_assignments(ctx_arg):
            key, sep, value = assignment.partition("=")
            if sep:
                context[key] = value
                continue
            errors.append(
                f"Invalid context format '{assignment}'. "
                "Use key=value format (e.g., -c 'question=What is X?' -c 'var=value')"
            )

    return context, errors


def validate_user_path(path_str: str, *, must_exist: bool = True) -> Path:
    """Validate and resolve a user-provided path."""
    if not path_str or not path_str.strip():
        raise ValueError("Path cannot be empty")

    try:
        path = Path(path_str).resolve()
    except (OSError, RuntimeError) as error:
        raise ValueError(f"Invalid path: {error}") from error

    if must_exist and not path.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")

    return path


def _infer_context_from_environment(key: str) -> tuple[str, str | None]:
    env_key = f"AMPLIHACK_CONTEXT_{key.upper()}"
    env_value = os.environ.get(env_key, "")
    if env_value:
        return env_value, f"{key} (from ${env_key})"

    if key == "task_description":
        task = os.environ.get("AMPLIHACK_TASK_DESCRIPTION", "")
        if task:
            return task, f"{key} (from $AMPLIHACK_TASK_DESCRIPTION)"
        return "", None

    if key == "repo_path":
        repo_path = os.environ.get("AMPLIHACK_REPO_PATH", ".")
        source = f"{key} (from $AMPLIHACK_REPO_PATH)" if repo_path != "." else None
        return repo_path, source

    return "", None


def infer_missing_context(
    recipe_defaults: dict[str, Any],
    merged: dict[str, Any],
    verbose: bool = False,
) -> dict[str, Any]:
    """Infer missing recipe context from well-known environment variables."""
    result = merged.copy()
    inferred: list[str] = []

    for key in recipe_defaults:
        if result.get(key) != "":
            continue

        inferred_value, inferred_source = _infer_context_from_environment(key)
        if inferred_value == "":
            continue

        result[key] = inferred_value
        if inferred_source:
            inferred.append(inferred_source)

    if inferred and verbose:
        print(
            f"[context] Inferred {len(inferred)} variable(s): {', '.join(inferred)}",
            file=sys.stderr,
        )

    return result


def merge_recipe_context(
    recipe_defaults: dict[str, Any],
    user_context: dict[str, Any],
    *,
    verbose: bool = False,
) -> dict[str, Any]:
    """Merge recipe defaults with user overrides and environment inference."""
    merged_context = {**recipe_defaults, **user_context}
    return infer_missing_context(recipe_defaults, merged_context, verbose=verbose)
