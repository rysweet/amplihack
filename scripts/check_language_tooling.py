#!/usr/bin/env python3
"""Check for required language server tooling for blarify indexing.

This script detects which SCIP indexers and language servers are installed
on the system, helping diagnose why certain languages might fail validation.
"""

import shutil
import subprocess
import sys
from dataclasses import dataclass


@dataclass
class ToolingCheck:
    """Result of checking for a specific tool."""

    tool_name: str
    required_for: str
    installed: bool
    version: str | None = None
    install_command: str | None = None


def check_command_exists(command: str) -> tuple[bool, str | None]:
    """Check if a command exists and get its version.

    Args:
        command: Command to check

    Returns:
        Tuple of (exists, version_string)
    """
    if shutil.which(command) is None:
        return False, None

    # Try to get version
    try:
        result = subprocess.run(
            [command, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        version = result.stdout.split("\n")[0] if result.stdout else None
        return True, version
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        return True, None


def check_npm_package(package: str) -> tuple[bool, str | None]:
    """Check if an npm package is installed globally.

    Args:
        package: Package name to check

    Returns:
        Tuple of (installed, version)
    """
    try:
        result = subprocess.run(
            ["npm", "list", "-g", package, "--depth=0"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            # Extract version from output
            for line in result.stdout.split("\n"):
                if package in line:
                    parts = line.split("@")
                    if len(parts) >= 2:
                        return True, parts[-1].strip()
            return True, None
        return False, None
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        return False, None


def check_all_tooling() -> list[ToolingCheck]:
    """Check for all required language server tooling.

    Returns:
        List of tooling check results
    """
    checks = []

    # Python tooling
    scip_python_exists, scip_python_version = check_npm_package("@sourcegraph/scip-python")
    checks.append(
        ToolingCheck(
            tool_name="scip-python",
            required_for="Python",
            installed=scip_python_exists,
            version=scip_python_version,
            install_command="npm install -g @sourcegraph/scip-python",
        )
    )

    # TypeScript tooling
    scip_typescript_exists, scip_typescript_version = check_npm_package(
        "@sourcegraph/scip-typescript"
    )
    checks.append(
        ToolingCheck(
            tool_name="scip-typescript",
            required_for="TypeScript/JavaScript",
            installed=scip_typescript_exists,
            version=scip_typescript_version,
            install_command="npm install -g @sourcegraph/scip-typescript",
        )
    )

    # Go tooling
    gopls_exists, gopls_version = check_command_exists("gopls")
    checks.append(
        ToolingCheck(
            tool_name="gopls",
            required_for="Go",
            installed=gopls_exists,
            version=gopls_version,
            install_command="go install golang.org/x/tools/gopls@latest",
        )
    )

    # Rust tooling (rust-analyzer)
    rust_analyzer_exists, rust_analyzer_version = check_command_exists("rust-analyzer")
    checks.append(
        ToolingCheck(
            tool_name="rust-analyzer",
            required_for="Rust",
            installed=rust_analyzer_exists,
            version=rust_analyzer_version,
            install_command="rustup component add rust-analyzer",
        )
    )

    # C# tooling (OmniSharp - check system and vendored location)
    omnisharp_exists, omnisharp_version = check_command_exists("omnisharp")

    # Also check vendored multilspy location
    from pathlib import Path

    vendored_omnisharp = (
        Path(__file__).parent.parent
        / "src/amplihack/vendor/blarify/vendor/multilspy/language_servers/omnisharp/static/OmniSharp/OmniSharp"
    )
    if not omnisharp_exists and vendored_omnisharp.exists():
        omnisharp_exists = True
        omnisharp_version = "vendored"

    checks.append(
        ToolingCheck(
            tool_name="omnisharp",
            required_for="C#",
            installed=omnisharp_exists,
            version=omnisharp_version,
            install_command="Included in vendored blarify"
            if omnisharp_exists
            else "See https://www.omnisharp.net/",
        )
    )

    # C++ tooling (clangd)
    clangd_exists, clangd_version = check_command_exists("clangd")
    checks.append(
        ToolingCheck(
            tool_name="clangd",
            required_for="C++",
            installed=clangd_exists,
            version=clangd_version,
            install_command="sudo apt-get install clangd (or brew install llvm)",
        )
    )

    # Check for scip-clang
    scip_clang_exists, scip_clang_version = check_command_exists("scip-clang")
    checks.append(
        ToolingCheck(
            tool_name="scip-clang",
            required_for="C++",
            installed=scip_clang_exists,
            version=scip_clang_version,
            install_command="See https://github.com/sourcegraph/scip-clang",
        )
    )

    return checks


def print_tooling_status():
    """Print status of all language server tooling."""
    checks = check_all_tooling()

    print("🔧 Language Server Tooling Status\n")
    print("=" * 80)

    # Group by installation status
    installed = [c for c in checks if c.installed]
    missing = [c for c in checks if not c.installed]

    if installed:
        print("\n✅ Installed:")
        for check in installed:
            version_str = f" ({check.version})" if check.version else ""
            print(f"   - {check.tool_name}{version_str} - Required for: {check.required_for}")

    if missing:
        print("\n❌ Missing:")
        for check in missing:
            print(f"   - {check.tool_name} - Required for: {check.required_for}")
            print(f"     Install: {check.install_command}")
            print()

    print("=" * 80)

    # Summary
    total = len(checks)
    installed_count = len(installed)
    print(f"\nSummary: {installed_count}/{total} tools installed")

    # Language support prediction
    print("\n📊 Expected Language Support:")
    language_status = {
        "Python": any(c.tool_name == "scip-python" and c.installed for c in checks),
        "TypeScript": any(c.tool_name == "scip-typescript" and c.installed for c in checks),
        "JavaScript": any(c.tool_name == "scip-typescript" and c.installed for c in checks),
        "Go": any(c.tool_name == "gopls" and c.installed for c in checks),
        "Rust": any(c.tool_name == "rust-analyzer" and c.installed for c in checks),
        "C#": any(c.tool_name == "omnisharp" and c.installed for c in checks),
        "C++": any(
            (c.tool_name == "clangd" or c.tool_name == "scip-clang") and c.installed for c in checks
        ),
    }

    for lang, supported in language_status.items():
        status = "✅ Supported" if supported else "❌ Not Supported (missing tooling)"
        print(f"   - {lang}: {status}")

    return checks


if __name__ == "__main__":
    print_tooling_status()
    sys.exit(0)
