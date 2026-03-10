"""Opt-in helper for trying the bundled Rust CLI under an isolated home."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from collections.abc import Sequence
from pathlib import Path

TRIAL_HOME_ENV = "AMPLIHACK_RUST_TRIAL_HOME"
TRIAL_BINARY_ENV = "AMPLIHACK_RUST_TRIAL_BINARY"
TRIAL_HOME_NAME = ".amplihack-rust-trial"
RUST_RELEASES_API = "https://api.github.com/repos/rysweet/amplihack-rs/releases?per_page=20"
USAGE = (
    "Usage: amplihack-rust-trial [--trial-home PATH] [--] [rust-cli args...]\n"
    "Runs the bundled Rust amplihack CLI with an isolated HOME."
)


def _binary_name() -> str:
    return "amplihack.exe" if os.name == "nt" else "amplihack"


def default_trial_home() -> Path:
    """Return the default isolated home for Rust CLI trials."""
    configured = os.environ.get(TRIAL_HOME_ENV)
    if configured:
        return Path(configured).expanduser()
    return Path.home() / TRIAL_HOME_NAME


def _bundled_binary_path() -> Path:
    """Return the expected bundled Rust CLI binary path inside the package."""
    return Path(__file__).resolve().parent / ".claude" / "bin" / _binary_name()


def _is_rust_cli_binary(candidate: Path) -> bool:
    """Return True when the candidate behaves like the Rust CLI binary."""
    if not candidate.is_file() or not os.access(candidate, os.X_OK):
        return False

    try:
        result = subprocess.run(
            [str(candidate), "version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except OSError:
        return False

    combined = f"{result.stdout}\n{result.stderr}".lower()
    return "amplihack-rs" in combined or "rust core runtime" in combined


def _existing_rust_candidate(path: Path | None) -> Path | None:
    if path is None:
        return None
    resolved = path.expanduser().resolve()
    if _is_rust_cli_binary(resolved):
        return resolved
    return None


def _target_triple() -> str:
    machine = platform.machine().lower()
    if machine in {"x86_64", "amd64"}:
        arch = "x86_64"
    elif machine in {"arm64", "aarch64"}:
        arch = "aarch64"
    else:
        raise RuntimeError(f"Unsupported CPU architecture for Rust trial helper: {machine}")

    if sys.platform.startswith("linux"):
        suffix = "unknown-linux-gnu"
    elif sys.platform == "darwin":
        suffix = "apple-darwin"
    else:
        raise RuntimeError(f"Unsupported platform for Rust trial helper: {sys.platform}")

    return f"{arch}-{suffix}"


def _expected_release_asset_name() -> str:
    return f"amplihack-{_target_triple()}.tar.gz"


def _release_cache_dir(trial_home: Path, tag_name: str) -> Path:
    return (
        trial_home.expanduser().resolve()
        / ".cache"
        / "amplihack-rust-trial"
        / "releases"
        / tag_name
        / _target_triple()
    )


def _github_json(url: str) -> object:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "amplihack-rust-trial",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def _download_to_file(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "amplihack-rust-trial"})
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as handle:
        shutil.copyfileobj(response, handle)


def _select_release_asset(releases: object) -> tuple[str, str]:
    asset_name = _expected_release_asset_name()
    if not isinstance(releases, list):
        raise FileNotFoundError("GitHub release response was not a list")

    for release in releases:
        if not isinstance(release, dict):
            continue
        tag_name = release.get("tag_name")
        assets = release.get("assets", [])
        if not isinstance(tag_name, str) or not isinstance(assets, list):
            continue
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            if asset.get("name") == asset_name and isinstance(
                asset.get("browser_download_url"), str
            ):
                return tag_name, asset["browser_download_url"]

    raise FileNotFoundError(
        f"No published amplihack-rs release contains asset {asset_name}. "
        "Wait for the snapshot release workflow to publish binaries, or set "
        "AMPLIHACK_RUST_TRIAL_BINARY explicitly."
    )


def download_latest_release_binary(trial_home: Path) -> Path:
    """Download and extract the latest compatible published Rust CLI binary."""
    tag_name, asset_url = _select_release_asset(_github_json(RUST_RELEASES_API))
    cache_dir = _release_cache_dir(trial_home, tag_name)
    cached_binary = _existing_rust_candidate(cache_dir / _binary_name())
    if cached_binary is not None:
        return cached_binary

    cache_dir.mkdir(parents=True, exist_ok=True)
    archive_path = cache_dir / _expected_release_asset_name()
    _download_to_file(asset_url, archive_path)

    with tarfile.open(archive_path, "r:gz") as archive:
        archive.extractall(cache_dir)

    binary = _existing_rust_candidate(cache_dir / _binary_name())
    if binary is None:
        raise FileNotFoundError(
            f"Downloaded release {tag_name} but did not find a valid Rust CLI binary "
            f"at {cache_dir / _binary_name()}"
        )

    return binary


def find_rust_cli_binary(trial_home: Path) -> Path:
    """Locate or download the Rust CLI binary for the opt-in trial helper.

    Search order:
    1. AMPLIHACK_RUST_TRIAL_BINARY
    2. Bundled package path amplihack/.claude/bin/amplihack
    3. ~/.amplihack/.claude/bin/amplihack
    4. PATH (validated to be the Rust CLI, not the Python wrapper)
    5. Download latest compatible published release into the trial cache
    """
    candidates: list[Path | None] = []

    configured = os.environ.get(TRIAL_BINARY_ENV)
    if configured:
        candidates.append(Path(configured).expanduser())

    candidates.append(_bundled_binary_path())
    candidates.append(Path.home() / ".amplihack" / ".claude" / "bin" / _binary_name())

    on_path = shutil.which("amplihack")
    if on_path:
        candidates.append(Path(on_path))

    for candidate in candidates:
        existing = _existing_rust_candidate(candidate)
        if existing is not None:
            return existing

    return download_latest_release_binary(trial_home)


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
    binary = find_rust_cli_binary(trial_home)
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
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
