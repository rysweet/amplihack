#!/usr/bin/env python3
"""
XPIA Security Health Check Module

Provides health monitoring and validation for XPIA security system integration.
Verifies that all XPIA components are properly configured and functional.

Following the bricks & studs philosophy:
- Brick: Self-contained health checking functionality
- Stud: Clear interface for health status reporting
- Regeneratable: Can be rebuilt from specification
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def check_hook_file_exists(hook_path: str) -> dict[str, Any]:
    """Check if a hook file exists and is executable"""
    path = Path(hook_path).expanduser()

    if not path.exists():
        return {"status": "missing", "path": str(path), "message": f"Hook file not found: {path}"}

    if not path.is_file():
        return {
            "status": "not_file",
            "path": str(path),
            "message": f"Hook path is not a file: {path}",
        }

    if not os.access(path, os.X_OK):
        return {
            "status": "not_executable",
            "path": str(path),
            "message": f"Hook file not executable: {path}",
        }

    return {"status": "ok", "path": str(path), "message": "Hook file exists and is executable"}


def check_settings_json_hooks(settings_path: Path | None = None) -> dict[str, Any]:
    """Check if XPIA hooks are configured in settings.json"""
    if settings_path is None:
        settings_path = Path.home() / ".claude" / "settings.json"

    if not settings_path.exists():
        return {"status": "no_settings", "message": "No settings.json found"}

    try:
        with open(settings_path) as f:
            settings = json.load(f)

        hooks = settings.get("hooks", {})

        # Check for XPIA hooks
        xpia_hooks_found = []
        expected_xpia_hooks = [
            ("SessionStart", "session_start.py"),
            ("PostToolUse", "post_tool_use.py"),
            ("PreToolUse", "pre_tool_use.py"),
        ]

        for hook_type, hook_file in expected_xpia_hooks:
            if hook_type in hooks:
                for hook_entry in hooks[hook_type]:
                    if "hooks" in hook_entry:
                        for hook in hook_entry["hooks"]:
                            command = hook.get("command", "")
                            if "xpia" in command and hook_file in command:
                                xpia_hooks_found.append(
                                    {
                                        "type": hook_type,
                                        "file": hook_file,
                                        "command": command,
                                        "status": "configured",
                                    }
                                )

        found_count = len(xpia_hooks_found)
        expected_count = len(expected_xpia_hooks)

        status = "ok" if found_count == expected_count else "missing_hooks"

        return {
            "status": status,
            "hooks_found": xpia_hooks_found,
            "total_found": found_count,
            "expected_count": expected_count,
            "message": f"Found {found_count} of {expected_count} expected XPIA hooks",
        }

    except json.JSONDecodeError as e:
        return {
            "status": "invalid_json",
            "error": str(e),
            "message": "settings.json is not valid JSON",
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "message": f"Error reading settings.json: {e}"}


def check_xpia_log_directory() -> dict[str, Any]:
    """Check if XPIA log directory exists and is writable"""
    log_dir = Path.home() / ".claude" / "logs" / "xpia"

    if not log_dir.exists():
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            return {
                "status": "created",
                "path": str(log_dir),
                "message": "XPIA log directory created successfully",
            }
        except Exception as e:
            return {
                "status": "creation_failed",
                "path": str(log_dir),
                "error": str(e),
                "message": f"Failed to create XPIA log directory: {e}",
            }

    if not log_dir.is_dir():
        return {
            "status": "not_directory",
            "path": str(log_dir),
            "message": "XPIA log path exists but is not a directory",
        }

    # Test write permission
    test_file = log_dir / "health_check_test.tmp"
    try:
        test_file.write_text("test")
        test_file.unlink()
        return {"status": "ok", "path": str(log_dir), "message": "XPIA log directory is writable"}
    except Exception as e:
        return {
            "status": "not_writable",
            "path": str(log_dir),
            "error": str(e),
            "message": f"XPIA log directory not writable: {e}",
        }


def check_xpia_modules() -> dict[str, Any]:
    """Check if XPIA modules are importable"""
    try:
        # Try to import XPIA defense interface
        project_root = Path(__file__).parents[3]
        specs_path = project_root / "Specs"

        if specs_path.exists():
            sys.path.insert(0, str(specs_path))

        try:
            import xpia_defense_interface  # noqa: F401  # type: ignore

            return {
                "status": "ok",
                "message": "XPIA defense interface module available",
                "module_path": str(specs_path / "xpia_defense_interface.py"),
            }
        except ImportError as e:
            return {
                "status": "import_failed",
                "error": str(e),
                "message": f"XPIA defense interface not importable: {e}",
            }

    except Exception as e:
        return {"status": "error", "error": str(e), "message": f"Error checking XPIA modules: {e}"}


def get_xpia_hook_paths() -> list[str]:
    """Get list of expected XPIA hook file paths"""
    home_dir = Path.home()
    # XPIA hooks are in ~/.amplihack/.claude/tools/xpia/hooks/ (not ~/.claude/)
    hook_base = home_dir / ".amplihack" / ".claude" / "tools" / "xpia" / "hooks"

    return [
        str(hook_base / "session_start.py"),
        str(hook_base / "post_tool_use.py"),
        str(hook_base / "pre_tool_use.py"),
    ]


def check_xpia_health(settings_path: Path | None = None) -> dict[str, Any]:
    """
    Comprehensive XPIA health check

    Returns:
        Dict with overall health status and component details
    """
    health_report = {
        "timestamp": datetime.now().isoformat(),
        "overall_status": "unknown",
        "components": {},
        "summary": {"total_checks": 0, "passed_checks": 0, "failed_checks": 0, "warnings": 0},
    }

    # Check 1: Settings.json hook configuration
    settings_check = check_settings_json_hooks(settings_path)
    health_report["components"]["settings_hooks"] = settings_check
    health_report["summary"]["total_checks"] += 1

    if settings_check["status"] == "ok":
        health_report["summary"]["passed_checks"] += 1
    elif settings_check["status"] == "missing_hooks":
        health_report["summary"]["failed_checks"] += 1
    else:
        health_report["summary"]["warnings"] += 1

    # Check 2: Hook file existence and permissions
    hook_files_status = []
    for hook_path in get_xpia_hook_paths():
        hook_check = check_hook_file_exists(hook_path)
        hook_files_status.append(hook_check)
        health_report["summary"]["total_checks"] += 1

        if hook_check["status"] == "ok":
            health_report["summary"]["passed_checks"] += 1
        else:
            health_report["summary"]["failed_checks"] += 1

    health_report["components"]["hook_files"] = {
        "status": "ok" if all(h["status"] == "ok" for h in hook_files_status) else "issues_found",
        "files": hook_files_status,
        "message": f"Checked {len(hook_files_status)} hook files",
    }

    # Check 3: Log directory
    log_check = check_xpia_log_directory()
    health_report["components"]["log_directory"] = log_check
    health_report["summary"]["total_checks"] += 1

    if log_check["status"] in ["ok", "created"]:
        health_report["summary"]["passed_checks"] += 1
    else:
        health_report["summary"]["failed_checks"] += 1

    # Check 4: XPIA modules
    modules_check = check_xpia_modules()
    health_report["components"]["xpia_modules"] = modules_check
    health_report["summary"]["total_checks"] += 1

    if modules_check["status"] == "ok":
        health_report["summary"]["passed_checks"] += 1
    else:
        health_report["summary"]["warnings"] += 1

    # Determine overall status
    if health_report["summary"]["failed_checks"] == 0:
        if health_report["summary"]["warnings"] == 0:
            health_report["overall_status"] = "healthy"
        else:
            health_report["overall_status"] = "healthy_with_warnings"
    elif health_report["summary"]["passed_checks"] > health_report["summary"]["failed_checks"]:
        health_report["overall_status"] = "partially_functional"
    else:
        health_report["overall_status"] = "unhealthy"

    # Add recommendations
    recommendations = []

    if settings_check["status"] == "missing_hooks":
        recommendations.append("Run installation process to configure XPIA hooks in settings.json")

    if any(h["status"] != "ok" for h in hook_files_status):
        recommendations.append("Verify XPIA hook files are installed and executable")

    if log_check["status"] not in ["ok", "created"]:
        recommendations.append("Fix XPIA log directory permissions")

    if modules_check["status"] != "ok":
        recommendations.append("Verify XPIA defense modules are properly installed")

    health_report["recommendations"] = recommendations

    return health_report


def print_health_report(health_report: dict[str, Any], verbose: bool = False) -> None:
    """Print formatted health report"""
    status_emoji = {
        "healthy": "✅",
        "healthy_with_warnings": "⚠️",
        "partially_functional": "⚡",
        "unhealthy": "❌",
        "unknown": "❓",
    }

    overall_status = health_report.get("overall_status", "unknown")
    emoji = status_emoji.get(overall_status, "❓")

    print("\nXPIA Security Health Check")
    print("=" * 50)
    print(f"Overall Status: {emoji} {overall_status.replace('_', ' ').title()}")
    print(f"Timestamp: {health_report.get('timestamp', 'unknown')}")

    summary = health_report.get("summary", {})
    print(
        f"\nSummary: {summary.get('passed_checks', 0)}/{summary.get('total_checks', 0)} checks passed"
    )

    if verbose:
        print("\nComponent Details:")
        components = health_report.get("components", {})

        for component_name, component_data in components.items():
            status = component_data.get("status", "unknown")
            message = component_data.get("message", "No details")
            print(f"  {component_name}: {status} - {message}")

    recommendations = health_report.get("recommendations", [])
    if recommendations:
        print("\nRecommendations:")
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")

    print()


def main():
    """CLI interface for XPIA health check"""
    import argparse

    parser = argparse.ArgumentParser(description="Check XPIA security system health")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed component information"
    )
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--settings", default=None, help="Path to settings.json file")

    args = parser.parse_args()

    # Run health check
    settings_path = Path(args.settings) if args.settings else None
    health_report = check_xpia_health(settings_path)

    if args.json:
        print(json.dumps(health_report, indent=2))
    else:
        print_health_report(health_report, verbose=args.verbose)

    # Exit with appropriate code
    overall_status = health_report.get("overall_status", "unknown")
    if overall_status in ["healthy", "healthy_with_warnings"]:
        sys.exit(0)
    elif overall_status == "partially_functional":
        sys.exit(1)
    else:
        sys.exit(2)


if __name__ == "__main__":
    main()
