"""Opt-in helper for trying the bundled Rust CLI under an isolated home."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence

TRIAL_HOME_ENV = "AMPLIHACK_RUST_TRIAL_HOME"
TRIAL_BINARY_ENV = "AMPLIHACK_RUST_TRIAL_BINARY"
TRIAL_HOME_NAME = ".amplihack-rust-trial"
USAGE = (
    "Usage: amplihack-rust-trial [--trial-home PATH] [--] [rust-cli args...]\n"
    "Runs the bundled Rust amplihack CLI with an isolated HOME."
)


def default_trial_home() -> Path:
    """Return the default isolated home for Rust CLI trials."""
    configured = os.environ.get(TRIAL_HOME_ENV)
    if configured:
        return Path(configured).expanduser()
    return Path.home() / TRIAL_HOME_NAME


def _bundled_binary_path() -> Path:
    """Return the expected bundled Rust CLI binary path inside the package."""
    binary_name = "amplihack.exe" if os.name == "nt" else "amplihack"
    return Path(__file__).resolve().parent / ".claude" / "bin" / binary_name


def find_rust_cli_binary() -> Path | None:
    """Locate the Rust CLI binary for the opt-in trial helper.

    Search order:
    1. AMPLIHACK_RUST_TRIAL_BINARY
    2. Bundled package path amplihack/.claude/bin/amplihack
    3. ~/.amplihack/.claude/bin/amplihack
    4. PATH
    """
    candidates: list[Path] = []

    configured = os.environ.get(TRIAL_BINARY_ENV)
    if configured:
        candidates.append(Path(configured).expanduser())

    candidates.append(_bundled_binary_path())

    binary_name = "amplihack.exe" if os.name == "nt" else "amplihack"
    candidates.append(Path.home() / ".amplihack" / ".claude" / "bin" / binary_name)

    on_path = shutil.which("amplihack")
    if on_path:
        candidates.append(Path(on_path))

    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate.resolve()

    return None


def build_trial_env(trial_home: Path) -> dict[str, str]:
    """Create the isolated environment for the Rust CLI trial."""
    home = trial_home.expanduser().resolve()
    config_home = home / ".config"
    home.mkdir(parents=True, exist_ok=True)
    config_home.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["HOME"] = str(home)
    env["XDG_CONFIG_HOME"] = str(config_home)
    env[TRIAL_HOME_ENV] = str(home)
    return env


def parse_trial_args(argv: Sequence[str]) -> tuple[Path, list[str]]:
    """Parse helper options and return (trial_home, rust_cli_args)."""
    args = list(argv)
    trial_home = default_trial_home()
    forwarded: list[str] = []
    idx = 0

    while idx < len(args):
        arg = args[idx]
        if arg == "--":
            forwarded.extend(args[idx + 1 :])
            break
        if arg == "--trial-home":
            idx += 1
            if idx >= len(args):
                raise ValueError("--trial-home requires a path")
            trial_home = Path(args[idx]).expanduser()
        elif arg.startswith("--trial-home="):
            trial_home = Path(arg.split("=", 1)[1]).expanduser()
        else:
            forwarded.append(arg)
        idx += 1

    if not forwarded:
        forwarded = ["--help"]

    return trial_home, forwarded


def run_rust_trial(rust_args: Sequence[str], trial_home: Path) -> int:
    """Run the Rust CLI inside the isolated trial home."""
    binary = find_rust_cli_binary()
    if binary is None:
        raise FileNotFoundError(
            "Rust CLI binary not found. Reinstall amplihack from a build that "
            "stages .claude/bin/amplihack, or set AMPLIHACK_RUST_TRIAL_BINARY "
            "to an explicit Rust binary path."
        )

    env = build_trial_env(trial_home)
    print(
        f"[amplihack-rust-trial] Using isolated HOME={env['HOME']}",
        file=sys.stderr,
    )
    result = subprocess.run([str(binary), *rust_args], env=env, check=False)
    return result.returncode


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint for the opt-in Rust trial helper."""
    try:
        trial_home, rust_args = parse_trial_args(argv or sys.argv[1:])
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        print(USAGE, file=sys.stderr)
        return 2

    try:
        return run_rust_trial(rust_args, trial_home)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
