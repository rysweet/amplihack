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
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

TRIAL_HOME_ENV = "AMPLIHACK_RUST_TRIAL_HOME"
TRIAL_BINARY_ENV = "AMPLIHACK_RUST_TRIAL_BINARY"
TRIAL_HOME_NAME = ".amplihack-rust-trial"
RUST_RELEASES_API = "https://api.github.com/repos/rysweet/amplihack-rs/releases?per_page=20"
USAGE = (
    "Usage: amplihack-rust-trial [--trial-home PATH] install [--install-dir PATH] [--force] [--no-bootstrap]\n"
    "       amplihack-rust-trial [--trial-home PATH] [--] [rust-cli args...]\n"
    "Runs the bundled Rust amplihack CLI with an isolated HOME, or installs the latest\n"
    "published Rust binary for daily use."
)


@dataclass(frozen=True)
class InstallOptions:
    install_dir: Path
    force: bool = False
    bootstrap: bool = True


def _binary_name() -> str:
    return "amplihack.exe" if os.name == "nt" else "amplihack"


def default_trial_home() -> Path:
    """Return the default isolated home for Rust CLI trials."""
    configured = os.environ.get(TRIAL_HOME_ENV)
    if configured:
        return Path(configured).expanduser()
    return Path.home() / TRIAL_HOME_NAME


def default_install_dir() -> Path:
    """Return the default user-local install directory for the Rust CLI."""
    return Path.home() / ".local" / "bin"


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
    elif sys.platform == "win32":
        suffix = "pc-windows-msvc"
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

    matches: list[tuple[tuple[datetime, datetime, int], str, str]] = []

    for index, release in enumerate(releases):
        if not isinstance(release, dict):
            continue
        if release.get("draft") is True:
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
                matches.append(
                    (_release_sort_key(release, index), tag_name, asset["browser_download_url"])
                )
                break

    if matches:
        _sort_key, tag_name, asset_url = max(matches, key=lambda match: match[0])
        return tag_name, asset_url

    raise FileNotFoundError(
        f"No published amplihack-rs release contains asset {asset_name}. "
        "Wait for the snapshot release workflow to publish binaries, or set "
        "AMPLIHACK_RUST_TRIAL_BINARY explicitly."
    )


def _release_sort_key(release: dict[str, object], index: int) -> tuple[datetime, datetime, int]:
    created_at = _parse_release_timestamp(release.get("created_at"))
    published_at = _parse_release_timestamp(release.get("published_at"))
    # Prefer the newest actual snapshot build first; later publish time only
    # breaks ties for releases created at the same instant.
    return created_at, published_at, -index


def _parse_release_timestamp(value: object) -> datetime:
    if not isinstance(value, str) or not value:
        return datetime.min.replace(tzinfo=UTC)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.min.replace(tzinfo=UTC)


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
    npm_bin = home / ".npm-global" / "bin"
    home.mkdir(parents=True, exist_ok=True)
    config_home.mkdir(parents=True, exist_ok=True)
    npm_bin.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["HOME"] = str(home)
    env["XDG_CONFIG_HOME"] = str(config_home)
    env[TRIAL_HOME_ENV] = str(home)
    path_env = env.get("PATH", "")
    env["PATH"] = f"{npm_bin}{os.pathsep}{path_env}" if path_env else str(npm_bin)
    return env


def _prepend_path(directory: Path, env: dict[str, str] | None = None) -> None:
    """Prepend a directory to PATH in both the provided env and current process."""
    target = env if env is not None else os.environ
    directory_str = str(directory.expanduser().resolve())
    current_entries = [entry for entry in target.get("PATH", "").split(os.pathsep) if entry]
    if directory_str not in current_entries:
        target["PATH"] = (
            f"{directory_str}{os.pathsep}{target['PATH']}" if target.get("PATH") else directory_str
        )
    current_process_entries = [
        entry for entry in os.environ.get("PATH", "").split(os.pathsep) if entry
    ]
    if directory_str not in current_process_entries:
        os.environ["PATH"] = (
            f"{directory_str}{os.pathsep}{os.environ['PATH']}"
            if os.environ.get("PATH")
            else directory_str
        )


def _shell_profile_path() -> Path | None:
    if os.name == "nt":
        return None
    shell = os.environ.get("SHELL", "")
    if shell.endswith("/zsh") or shell.endswith("/zsh5"):
        return Path.home() / ".zshrc"
    return Path.home() / ".bashrc"


def _path_export_line(directory: Path) -> str:
    resolved = directory.expanduser().resolve()
    if resolved == default_install_dir().resolve():
        return 'export PATH="$HOME/.local/bin:$PATH"'
    return f'export PATH="{resolved}:$PATH"'


def _update_shell_profile_path(directory: Path) -> bool:
    """Persist a PATH entry across shell sessions in an idempotent way."""
    profile_path = _shell_profile_path()
    if profile_path is None:
        return False

    export_line = _path_export_line(directory)
    try:
        if profile_path.exists():
            content = profile_path.read_text(encoding="utf-8")
            if export_line in content:
                return True
        with profile_path.open("a", encoding="utf-8") as handle:
            handle.write(f"\n# Added by amplihack\n{export_line}\n")
        return True
    except OSError:
        return False


def parse_install_args(argv: Sequence[str]) -> InstallOptions:
    """Parse helper-specific install options."""
    args = list(argv)
    install_dir = default_install_dir()
    force = False
    bootstrap = True
    idx = 0
    while idx < len(args):
        arg = args[idx]
        if arg == "--install-dir":
            idx += 1
            if idx >= len(args):
                raise ValueError("--install-dir requires a path")
            install_dir = Path(args[idx]).expanduser()
        elif arg.startswith("--install-dir="):
            install_dir = Path(arg.split("=", 1)[1]).expanduser()
        elif arg == "--force":
            force = True
        elif arg == "--no-bootstrap":
            bootstrap = False
        else:
            raise ValueError(f"Unknown install option: {arg}")
        idx += 1
    return InstallOptions(install_dir=install_dir, force=force, bootstrap=bootstrap)


def install_rust_cli(trial_home: Path, options: InstallOptions) -> Path:
    """Install the latest published Rust CLI into the user's local bin directory."""
    source_binary = download_latest_release_binary(trial_home)
    install_dir = options.install_dir.expanduser().resolve()
    install_dir.mkdir(parents=True, exist_ok=True)
    destination = install_dir / _binary_name()

    if destination.exists() and destination.is_dir():
        raise RuntimeError(f"Install path {destination} is a directory, not a binary")

    if destination.exists() and not options.force and not _is_rust_cli_binary(destination):
        raise RuntimeError(
            f"Refusing to overwrite non-amplihack binary at {destination}; rerun with --force "
            "if you really want to replace it."
        )

    shutil.copy2(source_binary, destination)
    destination.chmod(0o755)
    _prepend_path(install_dir)
    _update_shell_profile_path(install_dir)

    if options.bootstrap:
        result = subprocess.run([str(destination), "install"], check=False)
        if result.returncode != 0:
            raise RuntimeError(
                f"Installed Rust CLI at {destination}, but `amplihack install` failed "
                f"with exit code {result.returncode}"
            )

    return destination


def _ensure_trial_copilot_config(trial_home: Path, source_home: Path | None = None) -> Path:
    """Ensure the isolated trial home has a visible Copilot config file.

    Copilot CLI interactive startup can hang with no visible terminal output when
    ~/.copilot/config.json is missing in a brand-new HOME. Seed the trial home
    from the user's existing config when available; otherwise create a minimal
    empty config.
    """
    copilot_home = trial_home.expanduser().resolve() / ".copilot"
    config_path = copilot_home / "config.json"
    if config_path.exists():
        return config_path

    copilot_home.mkdir(parents=True, exist_ok=True)
    host_home = Path.home() if source_home is None else source_home.expanduser().resolve()
    source_config = host_home / ".copilot" / "config.json"
    if source_config.is_file():
        shutil.copy2(source_config, config_path)
    else:
        config_path.write_text("{}\n", encoding="utf-8")
    return config_path


def ensure_trial_dependencies(
    rust_args: Sequence[str], trial_home: Path, env: dict[str, str]
) -> None:
    """Install subcommand-specific dependencies inside the isolated trial home."""
    if not rust_args or rust_args[0] != "copilot":
        return

    from .launcher.copilot import check_copilot, ensure_latest_copilot, install_copilot

    _ensure_trial_copilot_config(trial_home)

    # Update to latest if already installed (fixes #3097)
    try:
        ensure_latest_copilot(env=env, home=trial_home)
    except Exception:
        pass  # non-critical — continue with current version

    if check_copilot(env=env, home=trial_home):
        return
    if not install_copilot(env=env, home=trial_home):
        raise RuntimeError("Failed to install GitHub Copilot CLI into the isolated trial home")


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
    ensure_trial_dependencies(rust_args, trial_home, env)
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
        if rust_args and rust_args[0] == "install":
            options = parse_install_args(rust_args[1:])
            installed = install_rust_cli(trial_home, options)
            print(
                f"[amplihack-rust-trial] Installed Rust CLI at {installed}",
                file=sys.stderr,
            )
            if options.bootstrap:
                print(
                    "[amplihack-rust-trial] Ran `amplihack install` automatically.",
                    file=sys.stderr,
                )
            return 0
        return run_rust_trial(rust_args, trial_home)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
