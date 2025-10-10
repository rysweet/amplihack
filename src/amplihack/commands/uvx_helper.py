"""UVX deployment helper commands."""

import os
import sys
from pathlib import Path
from typing import Optional


def find_uvx_installation_path() -> Optional[Path]:
    """Find the UVX installation path containing framework files.

    Returns:
        Path to UVX installation with .claude directory, None if not found.
    """
    # Strategy 1: Check environment variable
    if "AMPLIHACK_ROOT" in os.environ:
        env_path = Path(os.environ["AMPLIHACK_ROOT"])
        if env_path.exists() and (env_path / ".claude").exists():
            return env_path

    # Strategy 2: Search Python paths for installed package
    for path_str in sys.path:
        path = Path(path_str)

        # Check if this is a UVX installation path
        if "uv" in str(path):
            # Look for the repository in parent directories
            current = path
            for _ in range(10):  # Limit search depth
                if (current / ".claude").exists():
                    return current
                if (current / "MicrosoftHackathon2025-AgenticCoding").exists():
                    repo_path = current / "MicrosoftHackathon2025-AgenticCoding"
                    if (repo_path / ".claude").exists():
                        return repo_path
                current = current.parent
                if current == current.parent:
                    break

    # Strategy 3: Search UVX cache directories
    cache_dirs = []

    if "UVX_CACHE" in os.environ:
        cache_dirs.append(Path(os.environ["UVX_CACHE"]))

    if os.name == "posix":
        home = Path.home()
        cache_dirs.extend(
            [
                home / ".cache" / "uv",
                home / ".local" / "share" / "uv",
            ]
        )
    elif os.name == "nt":
        cache_dirs.extend(
            [
                Path(os.environ.get("LOCALAPPDATA", "")) / "uv",
                Path(os.environ.get("APPDATA", "")) / "uv",
            ]
        )

    for cache_dir in cache_dirs:
        if not cache_dir.exists():
            continue

        # Search for our repository
        for repo_path in cache_dir.rglob("MicrosoftHackathon2025-AgenticCoding"):
            if (repo_path / ".claude").exists():
                return repo_path

    return None


def print_uvx_usage_instructions():
    """Print instructions for using UVX deployment."""
    print("🚀 AmplifyHack UVX Deployment Guide")
    print("=" * 50)

    print("\n📋 Quick Start:")
    print(
        "uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding amplihack launch"
    )

    print("\n⚠️  If @ imports don't work, use --add-dir:")
    uvx_path = find_uvx_installation_path()

    if uvx_path:
        print(f"✅ Found UVX installation: {uvx_path}")
        print("\n📁 Use this command:")
        print(f"uvx --from git+... amplihack launch --add-dir {uvx_path}")
    else:
        print("❌ UVX installation not found")
        print("\n🔍 To find your UVX path manually:")
        print('1. Run: uvx --from git+... python -c "import amplihack; print(amplihack.__file__)"')
        print("2. Navigate up from that path until you find .claude directory")
        print("3. Use that path with --add-dir")

    print("\n💡 Alternatively, install locally:")
    print("amplihack install  # Installs to ~/.claude")
    print("claude launch      # Uses local installation")


def main():
    """Main CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="UVX deployment helper")
    parser.add_argument("--find-path", action="store_true", help="Find UVX installation path")
    parser.add_argument("--usage", action="store_true", help="Show usage instructions")

    args = parser.parse_args()

    if args.find_path:
        path = find_uvx_installation_path()
        if path:
            print(str(path))
        else:
            print("UVX installation path not found", file=sys.stderr)
            sys.exit(1)
    elif args.usage:
        print_uvx_usage_instructions()
    else:
        print_uvx_usage_instructions()


if __name__ == "__main__":
    main()
