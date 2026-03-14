"""Rust recipe runner integration.

Delegates recipe execution to the ``recipe-runner-rs`` binary.
No fallbacks — if the Rust engine is selected and the binary is missing,
execution fails immediately with a clear error.
"""

from __future__ import annotations

import functools
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any

from amplihack.recipes.models import RecipeResult, StepResult, StepStatus

logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=1)
def _binary_search_paths() -> list[str]:
    """Return known locations to search for the Rust binary.

    Evaluated lazily on first call so Path.home() is only resolved when needed.
    """
    return [
        "recipe-runner-rs",  # PATH
        str(Path.home() / ".cargo" / "bin" / "recipe-runner-rs"),
        str(Path.home() / ".local" / "bin" / "recipe-runner-rs"),
    ]


def _install_timeout() -> int:
    """Return the install timeout in seconds (env-configurable)."""
    return int(os.environ.get("RECIPE_RUNNER_INSTALL_TIMEOUT", "300"))


def find_rust_binary() -> str | None:
    """Find the recipe-runner-rs binary.

    Checks the RECIPE_RUNNER_RS_PATH env var first, then known locations.
    Returns the path to the binary, or None if not found.
    """
    env_path = os.environ.get("RECIPE_RUNNER_RS_PATH")
    if env_path:
        resolved = shutil.which(env_path)
        if resolved:
            return resolved

    for candidate in _binary_search_paths():
        resolved = shutil.which(candidate)
        if resolved:
            return resolved

    return None


# Minimum compatible recipe-runner-rs version (semver).
MIN_RUNNER_VERSION = "0.1.0"


def get_runner_version(binary: str | None = None) -> str | None:
    """Return the version string of the installed recipe-runner-rs, or None."""
    binary = binary or find_rust_binary()
    if not binary:
        return None
    try:
        result = subprocess.run(
            [binary, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            # Format: "recipe-runner 0.1.0"
            parts = result.stdout.strip().rsplit(" ", 1)
            return parts[-1] if len(parts) >= 2 else result.stdout.strip()
    except Exception as exc:
        logger.debug("Could not get runner version from %s: %s", binary, exc)
    return None


def _version_tuple(ver: str) -> tuple[int, ...]:
    """Parse a semver string into a comparable tuple."""
    return tuple(int(x) for x in ver.split(".") if x.isdigit())


def check_runner_version(binary: str | None = None) -> bool:
    """Check if the installed binary meets the minimum version requirement.

    Returns True if version is compatible or cannot be determined (best-effort).
    Returns False and logs a warning if the binary is too old.
    """
    version = get_runner_version(binary)
    if version is None:
        return True  # can't check, assume ok
    try:
        if _version_tuple(version) < _version_tuple(MIN_RUNNER_VERSION):
            logger.warning(
                "recipe-runner-rs version %s is older than minimum %s. "
                "Update: cargo install --git %s",
                version,
                MIN_RUNNER_VERSION,
                _REPO_URL,
            )
            return False
    except (ValueError, TypeError):
        return True  # unparseable version, assume ok
    return True


def is_rust_runner_available() -> bool:
    """Check if the Rust recipe runner binary is available."""
    return find_rust_binary() is not None


class RustRunnerNotFoundError(RuntimeError):
    """Raised when the Rust recipe runner binary is required but not found."""


_REPO_URL = "https://github.com/rysweet/amplihack-recipe-runner"


def ensure_rust_recipe_runner(*, quiet: bool = False) -> bool:
    """Ensure the recipe-runner-rs binary is installed.

    If the binary is already available, returns True immediately.
    Otherwise, attempts to install via ``cargo install --git``.

    Args:
        quiet: Suppress progress messages.

    Returns:
        True if binary is available after this call, False if installation failed.
    """
    if is_rust_runner_available():
        return True

    cargo = shutil.which("cargo")
    if cargo is None:
        if not quiet:
            logger.warning(
                "cargo not found — cannot auto-install recipe-runner-rs. "
                "Install Rust (https://rustup.rs) then run: "
                "cargo install --git %s",
                _REPO_URL,
            )
        return False

    if not quiet:
        logger.info("Installing recipe-runner-rs from %s …", _REPO_URL)

    timeout = _install_timeout()
    try:
        result = subprocess.run(
            [cargo, "install", "--git", _REPO_URL],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            if not quiet:
                logger.info("recipe-runner-rs installed successfully")
            return True

        logger.warning(
            "cargo install failed (exit %d): %s",
            result.returncode,
            result.stderr[:500] if result.stderr else "no output",
        )
        return False
    except subprocess.TimeoutExpired:
        logger.warning("cargo install timed out after %ds", timeout)
        return False
    except Exception as exc:
        logger.warning("cargo install failed: %s", exc)
        return False


# -- Helpers for run_recipe_via_rust -----------------------------------------


def _redact_command_for_log(cmd: list[str]) -> str:
    """Build a log-safe command string with context values masked."""
    parts: list[str] = []
    mask_next = False
    for token in cmd:
        if mask_next:
            key, _, _value = token.partition("=")
            parts.append(f"{key}=***")
            mask_next = False
        elif token == "--set":
            parts.append(token)
            mask_next = True
        else:
            parts.append(token)
    return " ".join(parts)


def _find_rust_binary() -> str:
    """Locate the Rust binary or raise ``RustRunnerNotFoundError``."""
    binary = find_rust_binary()
    if binary is None:
        raise RustRunnerNotFoundError(
            "recipe-runner-rs binary not found. "
            "Install it: cargo install --git https://github.com/rysweet/amplihack-recipe-runner "
            "or set RECIPE_RUNNER_RS_PATH to the binary location."
        )
    check_runner_version(binary)
    return binary


def _build_rust_command(
    binary: str,
    name: str,
    *,
    working_dir: str,
    dry_run: bool,
    auto_stage: bool,
    progress: bool,
    recipe_dirs: list[str] | None,
    user_context: dict[str, Any] | None,
) -> list[str]:
    """Assemble the CLI command list for the Rust binary."""
    abs_working_dir = str(Path(working_dir).resolve())
    cmd = [binary, name, "--output-format", "json", "-C", abs_working_dir]

    if dry_run:
        cmd.append("--dry-run")

    if not auto_stage:
        cmd.append("--no-auto-stage")

    if progress:
        cmd.append("--progress")

    # Forward active agent binary so the Rust runner spawns the correct agent
    agent_binary = os.environ.get("AMPLIHACK_AGENT_BINARY")
    if agent_binary:
        cmd.extend(["--agent-binary", agent_binary])

    if recipe_dirs:
        for d in recipe_dirs:
            cmd.extend(["-R", d])

    if user_context:
        for key, value in user_context.items():
            if isinstance(value, (dict, list)):
                cmd.extend(["--set", f"{key}={json.dumps(value)}"])
            elif isinstance(value, bool):
                cmd.extend(["--set", f"{key}={'true' if value else 'false'}"])
            else:
                cmd.extend(["--set", f"{key}={value}"])

    return cmd


_STATUS_MAP = {
    "completed": StepStatus.COMPLETED,
    "skipped": StepStatus.SKIPPED,
    "failed": StepStatus.FAILED,
    "pending": StepStatus.PENDING,
    "running": StepStatus.RUNNING,
}


def _stream_process_output(process: subprocess.Popen[str]) -> tuple[str, str, int]:
    """Collect stdout while relaying stderr live for progress-enabled runs."""
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []

    def _drain_stdout() -> None:
        if process.stdout is None:
            return
        for line in process.stdout:
            stdout_chunks.append(line)

    def _drain_stderr() -> None:
        if process.stderr is None:
            return
        for line in process.stderr:
            stderr_chunks.append(line)
            print(line, end="", file=sys.stderr, flush=True)

    stdout_thread = threading.Thread(target=_drain_stdout)
    stderr_thread = threading.Thread(target=_drain_stderr)
    stdout_thread.start()
    stderr_thread.start()
    try:
        returncode = process.wait()
    finally:
        stdout_thread.join()
        stderr_thread.join()
    return "".join(stdout_chunks), "".join(stderr_chunks), returncode


def _execute_rust_command(cmd: list[str], *, name: str, progress: bool) -> RecipeResult:
    """Run the Rust binary and parse its JSON output into a ``RecipeResult``."""
    if progress:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        stdout, stderr, returncode = _stream_process_output(process)
    else:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
        stdout = result.stdout
        stderr = result.stderr
        returncode = result.returncode

    try:
        data = json.loads(stdout)
    except (json.JSONDecodeError, TypeError):
        if returncode != 0:
            raise RuntimeError(
                f"Rust recipe runner failed (exit {returncode}): "
                f"{stderr[:1000] if stderr else 'no stderr'}"
            )
        raise RuntimeError(
            f"Rust recipe runner returned unparseable output (exit {returncode}): "
            f"{stdout[:500] if stdout else 'empty stdout'}"
        )

    step_results = [
        StepResult(
            step_id=sr.get("step_id", "unknown"),
            status=_STATUS_MAP.get(sr.get("status", "failed").lower(), StepStatus.FAILED),
            output=sr.get("output", ""),
            error=sr.get("error", ""),
        )
        for sr in data.get("step_results", [])
    ]

    return RecipeResult(
        recipe_name=data.get("recipe_name", name),
        success=data.get("success", False),
        step_results=step_results,
        context=data.get("context", {}),
    )


# -- Recipe command normalization --------------------------------------------

# Match a {{var}} placeholder where the var name is word characters only
_VAR_PLACEHOLDER_PATTERN = re.compile(r"\{\{([\w_]+)\}\}")

# Match "{{var}}" (double-quoted var)
_DOUBLE_QUOTED_VAR = re.compile(r'"(\{\{[\w_]+\}\})"')

# Match '{{var}}' (single-quoted var)
_SINGLE_QUOTED_VAR = re.compile(r"'(\{\{[\w_]+\}\})'")

# Match <<'DELIM' heredoc opener (single-quoted delimiter)
_SINGLE_QUOTED_HEREDOC = re.compile(r"<<'(\w+)'")


def normalize_command_quoting(cmd: str) -> str:
    """Normalize ``{{var}}`` quoting in a recipe bash command string.

    The Rust runner translates ``{{var}}`` to ``"$RECIPE_VAR_var"`` (with
    double quotes) outside heredocs, and to ``$RECIPE_VAR_var`` (unquoted)
    inside unquoted heredocs.  Common authoring mistakes produce broken shell:

    * ``"{{var}}"`` → runner renders ``""$RECIPE_VAR_var""`` (doubled quotes)
    * ``'{{var}}'`` → runner renders ``'"$RECIPE_VAR_var"'`` (literal quotes)
    * ``<<'DELIM'`` heredoc with ``{{var}}`` in body → shell blocks expansion

    This function normalises all three patterns to their canonical form so
    authors can write natural commands without memorising quoting rules.

    Args:
        cmd: Raw bash command string from a recipe YAML ``command:`` field.

    Returns:
        Normalised command string.  Unchanged if no problematic patterns found.
    """
    # Fix 1: "{{var}}" → {{var}}  (runner adds its own double quotes)
    cmd = _DOUBLE_QUOTED_VAR.sub(r"\1", cmd)

    # Fix 2: '{{var}}' → {{var}}  (single quotes block runner's expansion)
    cmd = _SINGLE_QUOTED_VAR.sub(r"\1", cmd)

    # Fix 3: <<'DELIM' → <<DELIM when the heredoc body contains {{var}}
    # Single-quoted heredocs block shell expansion of $RECIPE_VAR_* references.
    # Allow optional leading whitespace on the closing delimiter line because
    # YAML block scalars preserve indentation in the raw text.
    def _fix_heredoc(m: re.Match) -> str:
        delim = m.group(1)
        opener_end = m.end()
        # Find the closing delimiter on its own line (allow leading whitespace
        # for YAML block scalar indentation)
        close_re = re.compile(r"^[ \t]*" + re.escape(delim) + r"[ \t]*$", re.MULTILINE)
        close_m = close_re.search(cmd, opener_end)
        if close_m is None:
            return m.group(0)  # malformed heredoc — leave unchanged
        body = cmd[opener_end:close_m.start()]
        if _VAR_PLACEHOLDER_PATTERN.search(body):
            return f"<<{delim}"
        return m.group(0)

    cmd = _SINGLE_QUOTED_HEREDOC.sub(_fix_heredoc, cmd)
    return cmd


def normalize_recipe_yaml(yaml_content: str) -> tuple[str, bool]:
    """Apply ``normalize_command_quoting`` to every bash ``command:`` field.

    Operates on raw YAML text to preserve comments, whitespace, and block
    scalars exactly.  Only the content of ``command:`` values is changed.

    Args:
        yaml_content: Raw text of a recipe YAML file.

    Returns:
        ``(normalised_content, changed)`` where *changed* is ``True`` when at
        least one substitution was made.
    """
    # Split on lines that start a `command:` block scalar (``command: |``) or
    # inline scalar (``command: single_line``).  We find each command value by
    # locating the `command:` key and extracting its scalar content.
    #
    # Rather than a full YAML parse (which loses formatting), we use a careful
    # line-by-line approach:
    #   1. Detect a ``command:`` line.
    #   2. Collect the scalar content (block literal or single-line).
    #   3. Normalise it, replacing the original lines if changed.

    lines = yaml_content.splitlines(keepends=True)
    result: list[str] = []
    changed = False
    i = 0

    # Regex: command: | or command: > (block scalar) or command: <value>
    cmd_key_re = re.compile(r"^(\s*)command:\s*(.*)\n?$")

    while i < len(lines):
        line = lines[i]
        m = cmd_key_re.match(line)
        if m is None:
            result.append(line)
            i += 1
            continue

        indent = m.group(1)
        rest = m.group(2).strip()

        if rest in ("|", ">", "|-", ">-", "|+", ">+"):
            # Block scalar: collect continuation lines
            block_lines: list[str] = []
            j = i + 1
            while j < len(lines):
                cont = lines[j]
                # Continuation if line is blank or its leading whitespace is
                # deeper than the command key's indentation level.
                cont_indent_len = len(cont) - len(cont.lstrip())
                if cont.strip() == "" or cont_indent_len > len(indent):
                    block_lines.append(cont)
                    j += 1
                else:
                    break

            raw_block = "".join(block_lines)
            normalised = normalize_command_quoting(raw_block)
            if normalised != raw_block:
                changed = True
                result.append(line)
                result.append(normalised)
            else:
                result.append(line)
                result.extend(block_lines)
            i = j
        elif rest:
            # Inline scalar
            normalised = normalize_command_quoting(rest)
            if normalised != rest:
                changed = True
                result.append(f"{indent}command: {normalised}\n")
            else:
                result.append(line)
            i += 1
        else:
            # Empty value — nothing to normalise
            result.append(line)
            i += 1

    return "".join(result), changed


def _normalize_recipe_into_tmpdir(
    name: str,
    recipe_dirs: list[str],
    tmp_dir: Path,
) -> list[str]:
    """If the named recipe has fixable quoting issues, write a normalised copy.

    Searches *recipe_dirs* for ``{name}.yaml``, normalises its command fields,
    and — when changes are needed — writes the fixed file to *tmp_dir*.  The
    tmp_dir is then prepended to the returned recipe-dirs list so the Rust
    binary discovers the normalised copy first.

    Args:
        name: Recipe name (no ``.yaml`` suffix).
        recipe_dirs: Directories to search for the recipe.
        tmp_dir: Writable directory for the normalised copy.

    Returns:
        Effective recipe-dirs list (tmp_dir prepended when a copy was written).
    """
    try:
        from amplihack.recipes.discovery import find_recipe

        recipe_path = find_recipe(name, [Path(d) for d in recipe_dirs])
        if recipe_path is None:
            return recipe_dirs

        original = recipe_path.read_text(encoding="utf-8")
        normalised, changed = normalize_recipe_yaml(original)

        if not changed:
            return recipe_dirs

        staged = tmp_dir / recipe_path.name
        staged.write_text(normalised, encoding="utf-8")
        logger.debug(
            "Normalised recipe '%s' for Rust runner (auto-fixed quoting patterns)", name
        )
        return [str(tmp_dir)] + list(recipe_dirs)

    except Exception as exc:
        logger.debug("Could not normalise recipe '%s': %s — using original", name, exc)
        return recipe_dirs


# -- Public entry point ------------------------------------------------------


def _default_package_recipe_dirs() -> list[str]:
    """Return bundled recipe directories visible to Python discovery.

    In editable installs, ``src/amplihack/amplifier-bundle/recipes`` may exist
    but only contain a subset of recipes, while the full bundle lives at the
    repo root ``amplifier-bundle/recipes``.  The Rust runner needs both paths
    to match Python-side discovery in real environments (issue #3002).
    """
    try:
        from amplihack.recipes.discovery import _PACKAGE_BUNDLE_DIR, _REPO_ROOT_BUNDLE_DIR

        dirs: list[str] = []
        for candidate in (_PACKAGE_BUNDLE_DIR, _REPO_ROOT_BUNDLE_DIR):
            if candidate.is_dir():
                candidate_str = str(candidate)
                if candidate_str not in dirs:
                    dirs.append(candidate_str)
        if dirs:
            return dirs
    except Exception as exc:
        logger.debug("Could not resolve default recipe dirs: %s", exc)
    return []


def run_recipe_via_rust(
    name: str,
    user_context: dict[str, Any] | None = None,
    dry_run: bool = False,
    recipe_dirs: list[str] | None = None,
    working_dir: str = ".",
    auto_stage: bool = True,
    progress: bool = False,
) -> RecipeResult:
    """Execute a recipe using the Rust binary.

    When *recipe_dirs* is ``None``, the installed Python package's bundled
    recipe directory is automatically included so the Rust binary can
    discover recipes that Python discovery already knows about.

    Raises:
        RustRunnerNotFoundError: If the binary is not installed.
        RuntimeError: If the binary produces unparseable output.
    """
    binary = _find_rust_binary()

    # When no explicit recipe_dirs are provided, inject the package bundle
    # directory so the Rust binary can find the same recipes as Python
    # discovery.  This fixes the Python/Rust discovery mismatch (#3002).
    effective_recipe_dirs = recipe_dirs
    if effective_recipe_dirs is None:
        effective_recipe_dirs = _default_package_recipe_dirs() or None

    # Auto-normalise the recipe's command quoting so recipe authors don't need
    # to remember the Rust runner's quoting rules.  A normalised copy is written
    # to a temp directory (which shadows the original) only when changes are
    # needed; the temp dir is cleaned up after the run.
    tmp_dir: tempfile.TemporaryDirectory | None = None
    try:
        if effective_recipe_dirs:
            tmp_obj = tempfile.TemporaryDirectory(prefix="amplihack-recipe-norm-")
            tmp_dir = tmp_obj
            effective_recipe_dirs = _normalize_recipe_into_tmpdir(
                name, effective_recipe_dirs, Path(tmp_obj.name)
            )

        cmd = _build_rust_command(
            binary,
            name,
            working_dir=working_dir,
            dry_run=dry_run,
            auto_stage=auto_stage,
            progress=progress,
            recipe_dirs=effective_recipe_dirs,
            user_context=user_context,
        )

        logger.info(
            "Executing recipe '%s' via Rust binary: %s",
            name,
            _redact_command_for_log(cmd),
        )

        return _execute_rust_command(cmd, name=name, progress=progress)
    finally:
        if tmp_dir is not None:
            tmp_dir.cleanup()
