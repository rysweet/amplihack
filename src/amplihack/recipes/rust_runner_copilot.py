"""Nested Copilot CLI compatibility helpers for the Rust recipe runner."""

from __future__ import annotations

import os
import shlex
import sys
import tempfile
from pathlib import Path


def _has_explicit_copilot_permission(token: str, *, category: str) -> bool:
    """Return True when a Copilot arg already sets explicit permissions."""
    if category == "tool":
        prefixes = ("--allow-all-tools", "--allow-tool", "--deny-tool")
    elif category == "path":
        prefixes = ("--allow-all-paths", "--allow-path", "--deny-path")
    else:
        raise ValueError(f"Unsupported Copilot permission category: {category}")

    return any(token == prefix or token.startswith(f"{prefix}=") for prefix in prefixes)


def _extract_copilot_prompt_parts(
    args: list[str],
) -> tuple[list[str], list[str], list[str], bool, bool]:
    normalized: list[str] = []
    system_prompt_parts: list[str] = []
    prompt_parts: list[str] = []
    saw_tool_permissions = False
    saw_path_permissions = False
    i = 0

    while i < len(args):
        token = args[i]
        if token in {"--system-prompt", "--append-system-prompt"}:
            if i + 1 < len(args):
                system_prompt_parts.append(args[i + 1])
            i += 2
            continue
        if token.startswith("--system-prompt=") or token.startswith("--append-system-prompt="):
            _, _, value = token.partition("=")
            if value:
                system_prompt_parts.append(value)
            i += 1
            continue
        if token in {"-p", "--prompt"}:
            if i + 1 < len(args):
                prompt_parts.append(args[i + 1])
            i += 2
            continue
        if token.startswith("--prompt="):
            _, _, value = token.partition("=")
            if value:
                prompt_parts.append(value)
            i += 1
            continue
        if _has_explicit_copilot_permission(token, category="tool"):
            saw_tool_permissions = True
        if _has_explicit_copilot_permission(token, category="path"):
            saw_path_permissions = True
        normalized.append(token)
        i += 1

    return normalized, system_prompt_parts, prompt_parts, saw_tool_permissions, saw_path_permissions


def _normalize_copilot_cli_args(args: list[str]) -> list[str]:
    """Normalize Copilot CLI args for nested agent compatibility."""
    (
        normalized,
        system_prompt_parts,
        prompt_parts,
        saw_tool_permissions,
        saw_path_permissions,
    ) = _extract_copilot_prompt_parts(args)

    prefix: list[str] = []
    if not saw_tool_permissions:
        prefix.append("--allow-all-tools")
    if not saw_path_permissions:
        prefix.append("--allow-all-paths")

    merged_parts = system_prompt_parts + prompt_parts
    if merged_parts:
        merged_prompt = "\n\n".join(part for part in merged_parts if part)
        if merged_prompt:
            normalized.extend(["-p", merged_prompt])

    return prefix + normalized


def _build_copilot_wrapper_source(real_binary: str) -> str:
    module_path = Path(__file__).resolve()
    return f"""#!/usr/bin/env python3
import importlib.util
import subprocess
import sys

REAL_BINARY = {real_binary!r}
MODULE_PATH = {str(module_path)!r}

def normalize(args):
    spec = importlib.util.spec_from_file_location("amplihack_rust_runner_copilot", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load compatibility module from {{MODULE_PATH}}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._normalize_copilot_cli_args(args)


def main():
    cmd = [REAL_BINARY] + normalize(sys.argv[1:])
    completed = subprocess.run(cmd, check=False)
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
"""


def _write_wrapper_file(path: Path, content: str, *, executable: bool = False) -> None:
    if path.exists() and path.is_symlink():
        raise RuntimeError(f"Refusing to overwrite symlinked Copilot wrapper file: {path}")
    if path.parent.exists() and path.parent.is_symlink():
        raise RuntimeError(
            f"Refusing to write Copilot wrapper into symlinked directory: {path.parent}"
        )

    content_bytes = content.encode("utf-8")
    existing_content: bytes | None = None
    try:
        existing_content = path.read_bytes()
    except FileNotFoundError:
        pass

    if existing_content != content_bytes:
        fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
        try:
            with os.fdopen(fd, "wb") as tmp_file:
                tmp_file.write(content_bytes)
            os.replace(tmp_name, path)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise
    if executable and os.name != "nt":
        mode = path.stat().st_mode
        if not mode & 0o111:
            path.chmod(mode | 0o755)


def _create_copilot_compat_wrapper_dir(real_binary: str, execution_root: str) -> str:
    """Create a Copilot wrapper for nested recipe-runner agent launches."""
    root = Path(execution_root)
    if not root.is_absolute():
        raise RuntimeError("execution_root must be absolute for Copilot wrapper placement")
    wrapper_dir = root.resolve() / ".amplihack" / "copilot-compat"
    if wrapper_dir.exists() and wrapper_dir.is_symlink():
        raise RuntimeError(f"Refusing to use symlinked Copilot wrapper directory: {wrapper_dir}")
    wrapper_dir.mkdir(parents=True, exist_ok=True)
    wrapper_py_path = wrapper_dir / "copilot.py"
    wrapper_source = _build_copilot_wrapper_source(real_binary)

    _write_wrapper_file(wrapper_py_path, wrapper_source, executable=True)
    _write_wrapper_file(
        wrapper_dir / "copilot.cmd",
        f'@echo off\r\n"{sys.executable}" "%~dp0copilot.py" %*\r\n',
    )
    _write_wrapper_file(
        wrapper_dir / "copilot",
        f'#!/usr/bin/env bash\nexec {shlex.quote(sys.executable)} {shlex.quote(str(wrapper_py_path))} "$@"\n',
        executable=True,
    )
    return str(wrapper_dir)
