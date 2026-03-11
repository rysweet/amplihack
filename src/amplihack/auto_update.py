"""Auto-update check mechanism for amplihack CLI.

Philosophy:
- Fail gracefully: Never block startup, all errors return None/False
- Minimal user disruption: 5s timeout, 24h cache TTL
- Clean UX: Clear prompts with sensible defaults
- Silent failures: Log at DEBUG only, never raise exceptions

Public API:
    - check_for_updates(): Check if newer version available
    - prompt_and_upgrade(): Interactive upgrade prompt and execution
"""

import json
import logging
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

try:
    import requests
except ImportError:
    print("WARNING: requests not available, update checks disabled", file=sys.stderr)
    requests = None  # type: ignore

try:
    from packaging.version import parse as parse_version
except ImportError:
    print("WARNING: packaging not available, version comparison disabled", file=sys.stderr)
    parse_version = None  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class UpdateCheckResult:
    """Result of update check operation.

    Attributes:
        current_version: Currently installed version
        latest_version: Latest version available on GitHub
        is_newer: True if latest > current
        release_url: URL to GitHub release page
    """

    current_version: str
    latest_version: str
    is_newer: bool
    release_url: str


@dataclass
class UpdateCache:
    """Update check cache data.

    Attributes:
        last_check: ISO timestamp of last check
        latest_version: Latest version from last check
        check_interval_hours: Cache TTL in hours
    """

    last_check: str
    latest_version: str
    check_interval_hours: int = 24

    def is_expired(self) -> bool:
        """Check if cache has expired based on TTL."""
        try:
            last_check_dt = datetime.fromisoformat(self.last_check)
            expiry = last_check_dt + timedelta(hours=self.check_interval_hours)
            return datetime.now(UTC) >= expiry
        except (ValueError, TypeError):
            return True  # Invalid timestamp = expired

    def to_dict(self) -> dict:
        """Serialize to dict for JSON storage."""
        return {
            "last_check": self.last_check,
            "latest_version": self.latest_version,
            "check_interval_hours": self.check_interval_hours,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UpdateCache":
        """Deserialize from dict."""
        return cls(
            last_check=data.get("last_check", ""),
            latest_version=data.get("latest_version", ""),
            check_interval_hours=data.get("check_interval_hours", 24),
        )


def _fetch_latest_version(timeout: int = 5) -> tuple[str, str] | None:
    """Fetch latest version from GitHub Releases API.

    Args:
        timeout: Request timeout in seconds

    Returns:
        Tuple of (version, release_url) or None on error

    Error handling:
        - Missing requests library: returns None
        - Network timeout: returns None
        - API error: returns None
        - All errors logged at DEBUG level only
    """
    if requests is None:
        logger.debug("requests library not available, skipping version check")
        return None

    try:
        url = "https://api.github.com/repos/rysweet/amplihack/releases/latest"
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()

        data = response.json()
        tag_name = data.get("tag_name", "")
        release_url = data.get("html_url", "")

        if not tag_name:
            logger.debug("GitHub API returned no tag_name")
            return None

        # Strip 'v' prefix if present (v0.2.1 -> 0.2.1)
        version = tag_name.lstrip("v")

        logger.debug(f"Fetched latest version: {version}")
        return (version, release_url)

    except requests.Timeout:
        logger.debug(f"GitHub API timeout after {timeout}s")
        return None
    except requests.RequestException as e:
        logger.debug(f"GitHub API request failed: {e}")
        return None
    except (KeyError, ValueError, TypeError) as e:
        logger.debug(f"Failed to parse GitHub API response: {e}")
        return None
    except Exception as e:
        logger.debug(f"Unexpected error fetching version ({type(e).__name__}): {e}")
        return None


def _compare_versions(current: str, latest: str) -> bool:
    """Compare two version strings.

    Args:
        current: Current version string
        latest: Latest version string

    Returns:
        True if latest > current, False otherwise

    Error handling:
        - Missing packaging library: falls back to string comparison
        - Invalid version format: returns False
    """
    if parse_version is None:
        # Fallback: simple string comparison
        logger.debug("packaging library not available, using string comparison")
        return latest > current

    try:
        current_ver = parse_version(current)
        latest_ver = parse_version(latest)
        return latest_ver > current_ver
    except Exception as e:
        logger.debug(f"Version comparison failed ({type(e).__name__}): {e}")
        return False


def _load_cache(cache_file: Path) -> UpdateCache | None:
    """Load update check cache from file.

    Args:
        cache_file: Path to cache JSON file

    Returns:
        UpdateCache object or None if not found/invalid
    """
    if not cache_file.exists():
        return None

    try:
        with open(cache_file) as f:
            data = json.load(f)
        return UpdateCache.from_dict(data)
    except (json.JSONDecodeError, OSError, ValueError) as e:
        logger.debug(f"Failed to load cache: {e}")
        return None


def _save_cache(cache_file: Path, cache: UpdateCache) -> bool:
    """Save update check cache to file.

    Args:
        cache_file: Path to cache JSON file
        cache: Cache data to save

    Returns:
        True on success, False on error
    """
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w") as f:
            json.dump(cache.to_dict(), f, indent=2)
        return True
    except OSError as e:
        logger.debug(f"Failed to save cache: {e}")
        return False


def check_for_updates(
    current_version: str,
    cache_dir: Path,
    check_interval_hours: int = 24,
    timeout_seconds: int = 5,
) -> UpdateCheckResult | None:
    """Check if a newer version of amplihack is available.

    This function:
    1. Checks cache to avoid API spam (default: 24h TTL)
    2. Fetches latest version from GitHub Releases API
    3. Compares versions using semantic versioning
    4. Updates cache with results

    Args:
        current_version: Currently installed version
        cache_dir: Directory for cache file
        check_interval_hours: Cache TTL in hours (default: 24)
        timeout_seconds: API request timeout (default: 5)

    Returns:
        UpdateCheckResult if newer version available, None otherwise

    Error handling:
        - All errors return None (silent failure)
        - Errors logged at DEBUG level only
        - Never blocks startup or raises exceptions

    Example:
        >>> cache_dir = Path.home() / ".amplihack" / "cache"
        >>> result = check_for_updates("0.2.0", cache_dir)
        >>> if result and result.is_newer:
        ...     print(f"Update available: {result.latest_version}")
    """
    cache_file = cache_dir / "update_check.json"

    # Try to load cache
    cache = _load_cache(cache_file)

    # Use cached data if not expired
    if cache and not cache.is_expired():
        logger.debug(f"Using cached version check (expires in {check_interval_hours}h)")

        # Check if cached latest is newer than current
        if _compare_versions(current_version, cache.latest_version):
            return UpdateCheckResult(
                current_version=current_version,
                latest_version=cache.latest_version,
                is_newer=True,
                release_url=f"https://github.com/rysweet/amplihack/releases/tag/v{cache.latest_version}",
            )
        return None

    # Cache expired or missing - fetch from GitHub
    logger.debug("Fetching latest version from GitHub API")
    result = _fetch_latest_version(timeout=timeout_seconds)

    if result is None:
        # API call failed - return None (silent failure)
        return None

    latest_version, release_url = result

    # Update cache with fresh data
    new_cache = UpdateCache(
        last_check=datetime.now(UTC).isoformat(),
        latest_version=latest_version,
        check_interval_hours=check_interval_hours,
    )
    _save_cache(cache_file, new_cache)

    # Compare versions
    is_newer = _compare_versions(current_version, latest_version)

    if not is_newer:
        return None

    return UpdateCheckResult(
        current_version=current_version,
        latest_version=latest_version,
        is_newer=True,
        release_url=release_url,
    )


def _run_upgrade(timeout: int = 60) -> bool:
    """Execute 'uv tool upgrade amplihack'.

    Args:
        timeout: Subprocess timeout in seconds

    Returns:
        True on success, False on error
    """
    try:
        result = subprocess.run(
            ["uv", "tool", "upgrade", "amplihack"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

        if result.returncode == 0:
            logger.debug("Successfully upgraded amplihack")
            return True
        logger.debug(f"Upgrade failed with code {result.returncode}: {result.stderr}")
        return False

    except subprocess.TimeoutExpired:
        logger.debug(f"Upgrade timeout after {timeout}s")
        return False
    except FileNotFoundError:
        logger.debug("uv command not found")
        return False
    except Exception as e:
        logger.debug(f"Upgrade failed ({type(e).__name__}): {e}")
        return False


def _resolve_executable_path(executable: str) -> Path | None:
    """Resolve an executable name or path to an absolute path."""
    candidate = Path(executable).expanduser()
    if candidate.is_absolute():
        return candidate.resolve() if candidate.exists() else None

    resolved = shutil.which(executable)
    return Path(resolved).resolve() if resolved else None


def _current_cli_path() -> Path | None:
    """Resolve the currently running CLI path when possible."""
    if sys.argv and sys.argv[0]:
        current = _resolve_executable_path(sys.argv[0])
        if current is not None:
            return current
    return _resolve_executable_path("amplihack")


def _find_rust_cli() -> Path | None:
    """Return a Rust-managed amplihack binary if one is installed."""
    current = _current_cli_path()
    candidates = (
        Path.home() / ".local" / "bin" / "amplihack",
        Path.home() / ".cargo" / "bin" / "amplihack",
    )
    for candidate in candidates:
        if not candidate.exists():
            continue
        resolved = candidate.resolve()
        if current is not None and resolved == current:
            continue
        return resolved
    return None


def run_update_command() -> int:
    """Handle explicit `amplihack update` invocations.

    Prefer the managed Rust CLI when it is installed in the standard locations so a
    shadowing Python CLI can still hand off to the real Rust updater.
    """
    rust_cli = _find_rust_cli()
    if rust_cli is not None:
        print(f"Delegating update to Rust CLI at {rust_cli}")
        result = subprocess.run([str(rust_cli), "update"], check=False)
        return result.returncode

    if _run_upgrade():
        print("Updated Python amplihack.")
        return 0

    print("Update failed.")
    print(
        "If you installed the Rust CLI, run "
        "`cargo install --git https://github.com/rysweet/amplihack-rs amplihack --locked` "
        "and then `~/.cargo/bin/amplihack install`."
    )
    return 1


def _restart_cli(args: list[str]) -> None:
    """Restart amplihack CLI with same arguments.

    After uv tool upgrade, the new version is available via 'amplihack' command,
    not via 'python -m amplihack'. Use the command directly.

    Args:
        args: CLI arguments to preserve (sys.argv[1:])

    Raises:
        Does not return (exits process via sys.exit)
    """
    # Whitelist safe arguments to prevent malicious flag injection
    SAFE_ARG_PATTERNS = [
        "--auto",
        "--max-turns",
        "--ui",
        "--no-reflection",
        "--with-proxy-config",
        "--checkout-repo",
        "--docker",
        "--",
        "-p",
        "-v",
        "--verbose",
        "--help",
        "--version",
    ]
    SAFE_TOP_LEVEL_COMMANDS = {
        "launch",
        "claude",
        "RustyClawd",
        "copilot",
        "codex",
        "amplifier",
        "uvx-help",
        "plugin",
        "memory",
        "new",
        "recipe",
        "mode",
        "fleet",
        "install",
        "uninstall",
        "update",
    }
    SAFE_SUBCOMMANDS = {
        "plugin": {"install", "uninstall", "link", "verify"},
        "memory": {"tree", "export", "import", "clean"},
        "recipe": {"run", "list", "validate", "show"},
        "mode": {"detect", "to-plugin", "to-local"},
    }

    safe_args = []
    skip_next = False
    active_command = None
    for arg in args:
        if skip_next:
            skip_next = False
            safe_args.append(arg)  # This is a value for previous flag
            continue

        # Check if this arg or its prefix is in whitelist
        if any(arg.startswith(pattern) for pattern in SAFE_ARG_PATTERNS):
            safe_args.append(arg)
            # If this flag expects a value, include next arg
            if arg in ["--max-turns", "--with-proxy-config", "--checkout-repo", "-p"]:
                skip_next = True
        elif not arg.startswith("-") and not safe_args and arg in SAFE_TOP_LEVEL_COMMANDS:
            safe_args.append(arg)
            active_command = arg
        elif (
            not arg.startswith("-")
            and active_command is not None
            and arg in SAFE_SUBCOMMANDS.get(active_command, set())
        ):
            safe_args.append(arg)
        elif arg.startswith("-"):
            logger.warning(f"Skipping non-whitelisted argument: {arg}")

    args = safe_args  # Use filtered args

    restart_target = _current_cli_path()
    launch_argv = [str(restart_target), *args] if restart_target is not None else ["amplihack", *args]

    try:
        subprocess.Popen(
            launch_argv,
            start_new_session=True,
        )
        logger.debug("Restarted amplihack CLI via command")
        sys.exit(0)
    except FileNotFoundError:
        # Fallback for development installations
        logger.debug("amplihack command not found, trying python -m")
        try:
            subprocess.Popen(
                [sys.executable, "-m", "amplihack"] + args,
                start_new_session=True,
            )
            logger.debug("Restarted amplihack CLI via python -m")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Failed to restart CLI: {e}")
            print("\n⚠️  Restart failed. Please run 'amplihack' manually to use the new version.")
            sys.exit(0)
    except Exception as e:
        logger.error(f"Failed to restart CLI: {e}")
        print("\n⚠️  Restart failed. Please run 'amplihack' manually to use the new version.")
        sys.exit(0)


def prompt_and_upgrade(
    update_info: UpdateCheckResult,
    cli_args: list[str],
) -> bool:
    """Prompt user to upgrade and execute if confirmed.

    Displays:
    - Current and latest versions
    - Release URL
    - Interactive prompt (default: Yes)

    If user accepts:
    1. Runs 'uv tool upgrade amplihack'
    2. Restarts CLI with original arguments
    3. Exits current process

    If user declines:
    - Prints upgrade instructions
    - Returns False to continue with current version

    Args:
        update_info: Update check result with version details
        cli_args: Original CLI arguments for restart

    Returns:
        True if upgrade initiated (process will exit)
        False if user declined (continue with current version)

    Example:
        >>> result = check_for_updates("0.2.0", cache_dir)
        >>> if result and result.is_newer:
        ...     if prompt_and_upgrade(result, sys.argv[1:]):
        ...         # This code won't execute - process restarted
        ...         pass
    """
    try:
        # Display update notification
        print("\n" + "─" * 60)
        print("🎉 A newer version of amplihack is available!")
        print(f"\n  Current: {update_info.current_version}")
        print(f"  Latest:  {update_info.latest_version}")
        print(f"  Release: {update_info.release_url}")
        print("\n" + "─" * 60)

        # Prompt user (default: Yes)
        response = input("Would you like to upgrade now? [Y/n]: ").strip().lower()

        # Interpret response (empty = yes, y = yes, anything else = no)
        if response in ("", "y", "yes"):
            print("\n🔄 Upgrading amplihack...")

            if _run_upgrade():
                print("✅ Upgrade complete! Restarting...")
                _restart_cli(cli_args)
                # Process exits, this line won't execute
                return True
            print("❌ Upgrade failed. Continuing with current version.")
            print("\nTo upgrade manually, run:")
            print("  uv tool upgrade amplihack")
            return False
        # User declined
        print("\nTo upgrade later, run:")
        print("  uv tool upgrade amplihack")
        return False

    except KeyboardInterrupt:
        print("\n\nUpgrade cancelled. Continuing with current version.")
        return False
    except Exception as e:
        logger.debug(f"Prompt failed ({type(e).__name__}): {e}")
        return False
