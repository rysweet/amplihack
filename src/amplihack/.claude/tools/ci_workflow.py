#!/usr/bin/env python3
"""
CI Workflow Tool

Provides higher-level CI workflow functionality for managing CI/CD processes:
- Running parallel CI diagnostics
- Iterating CI fixes with max attempts
- Polling CI status with exponential backoff
"""

import argparse
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import the existing CI status checker
try:
    from .ci_status import check_ci_status
except ImportError:
    # Running as a script
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from ci_status import check_ci_status


def run_command(cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    """
    Run a shell command with timeout.

    Args:
        cmd: Command and arguments as a list
        timeout: Command timeout in seconds

    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    try:
        result = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", f"Command timed out after {timeout} seconds"
    except FileNotFoundError:
        return 1, "", f"Command not found: {cmd[0]}"
    except Exception as e:
        return 1, "", f"Error running command: {e}"


def diagnose_ci(pr_number: int | None = None, branch: str | None = None) -> dict:
    """
    Run parallel CI diagnostics to gather comprehensive CI status information.

    Args:
        pr_number: PR number to diagnose
        branch: Branch name to diagnose (if no PR number)

    Returns:
        Dictionary with diagnostic results
    """
    diagnostics = {
        "ci_status": None,
        "lint_check": None,
        "test_check": None,
        "build_check": None,
        "errors": [],
    }

    # Determine reference for CI status
    reference = str(pr_number) if pr_number else branch

    def check_ci():
        """Check overall CI status"""
        return check_ci_status(reference)

    def check_lint():
        """Run lint checks locally"""
        # Try common linters
        for linter_cmd in [
            ["make", "lint"],
            ["npm", "run", "lint"],
            ["python", "-m", "flake8", "."],
            ["pre-commit", "run", "--all-files"],
        ]:
            code, stdout, stderr = run_command(linter_cmd, timeout=60)
            if code != 127:  # Command found
                return {
                    "command": " ".join(linter_cmd),
                    "success": code == 0,
                    "output": stdout if code == 0 else stderr,
                }
        return {"success": True, "output": "No linter configured"}

    def check_tests():
        """Run tests locally"""
        # Try common test commands
        for test_cmd in [
            ["make", "test"],
            ["npm", "test"],
            ["python", "-m", "pytest"],
            ["python", "-m", "unittest", "discover"],
        ]:
            code, stdout, stderr = run_command(test_cmd, timeout=120)
            if code != 127:  # Command found
                return {
                    "command": " ".join(test_cmd),
                    "success": code == 0,
                    "output": stdout if code == 0 else stderr,
                }
        return {"success": True, "output": "No test runner configured"}

    def check_build():
        """Check if project builds"""
        # Try common build commands
        for build_cmd in [
            ["make", "build"],
            ["npm", "run", "build"],
            ["python", "setup.py", "build"],
            ["cargo", "build"],
        ]:
            code, stdout, stderr = run_command(build_cmd, timeout=180)
            if code != 127:  # Command found
                return {
                    "command": " ".join(build_cmd),
                    "success": code == 0,
                    "output": stdout if code == 0 else stderr,
                }
        return {"success": True, "output": "No build system configured"}

    # Run all checks in parallel
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(check_ci): "ci_status",
            executor.submit(check_lint): "lint_check",
            executor.submit(check_tests): "test_check",
            executor.submit(check_build): "build_check",
        }

        for future in as_completed(futures):
            check_name = futures[future]
            try:
                result = future.result(timeout=180)
                diagnostics[check_name] = result
            except Exception as e:
                diagnostics["errors"].append(f"{check_name}: {e!s}")
                diagnostics[check_name] = {"success": False, "error": str(e)}

    # Analyze results
    diagnostics["overall_status"] = analyze_diagnostics(diagnostics)

    return diagnostics


def analyze_diagnostics(diagnostics: dict) -> str:
    """
    Analyze diagnostic results and provide overall status.

    Args:
        diagnostics: Dictionary with diagnostic results

    Returns:
        Overall status string
    """
    ci_status = diagnostics.get("ci_status", {})
    lint_check = diagnostics.get("lint_check", {})
    test_check = diagnostics.get("test_check", {})
    build_check = diagnostics.get("build_check", {})

    # Check for critical failures
    if ci_status.get("status") == "FAILING":
        return "CI_FAILING"
    if not test_check.get("success"):
        return "TESTS_FAILING"
    if not lint_check.get("success"):
        return "LINT_FAILING"
    if not build_check.get("success"):
        return "BUILD_FAILING"
    if ci_status.get("status") == "PENDING":
        return "CI_PENDING"
    if ci_status.get("status") == "PASSING":
        return "ALL_PASSING"
    return "UNKNOWN"


def iterate_fixes(max_attempts: int = 5, pr_number: int | None = None) -> dict:
    """
    Iterate on CI fixes with a maximum number of attempts.

    Args:
        max_attempts: Maximum number of fix attempts
        pr_number: PR number to fix CI for

    Returns:
        Dictionary with fix iteration results
    """
    results = {"attempts": [], "success": False, "final_status": None}

    for attempt in range(1, max_attempts + 1):
        print(f"\nAttempt {attempt}/{max_attempts}")
        print("-" * 40)

        # Run diagnostics
        diagnostics = diagnose_ci(pr_number=pr_number)
        overall_status = diagnostics["overall_status"]

        attempt_result = {
            "attempt": attempt,
            "status": overall_status,
            "diagnostics": diagnostics,
            "fixes_applied": [],
        }

        if overall_status == "ALL_PASSING":
            print("✓ All checks passing!")
            results["success"] = True
            results["final_status"] = "PASSING"
            results["attempts"].append(attempt_result)
            break

        # Apply fixes based on status
        if overall_status == "LINT_FAILING":
            print("Fixing lint issues...")
            # Try auto-fix commands
            for fix_cmd in [
                ["pre-commit", "run", "--all-files", "--hook-stage", "manual"],
                ["npm", "run", "lint", "--", "--fix"],
                ["black", "."],
                ["isort", "."],
            ]:
                code, stdout, stderr = run_command(fix_cmd, timeout=60)
                if code != 127:  # Command found
                    attempt_result["fixes_applied"].append(
                        {"type": "lint_fix", "command": " ".join(fix_cmd), "success": code == 0}
                    )
                    if code == 0:
                        # Commit the fixes
                        run_command(["git", "add", "-A"])
                        run_command(["git", "commit", "-m", "fix: auto-fix lint issues"])
                        if pr_number:
                            run_command(["git", "push"])
                        break

        elif overall_status == "TESTS_FAILING":
            print("Tests are failing - manual intervention needed")
            attempt_result["fixes_applied"].append(
                {"type": "test_analysis", "message": "Tests require manual fixing"}
            )
            # In a real implementation, could analyze test output and suggest fixes

        elif overall_status == "BUILD_FAILING":
            print("Build is failing - checking dependencies...")
            # Try to fix common build issues
            for fix_cmd in [
                ["npm", "install"],
                ["pip", "install", "-r", "requirements.txt"],
                ["cargo", "update"],
            ]:
                code, stdout, stderr = run_command(fix_cmd, timeout=120)
                if code != 127:  # Command found
                    attempt_result["fixes_applied"].append(
                        {
                            "type": "dependency_fix",
                            "command": " ".join(fix_cmd),
                            "success": code == 0,
                        }
                    )
                    if code == 0:
                        break

        elif overall_status == "CI_PENDING":
            print("CI is still running - waiting...")
            time.sleep(30)  # Wait before next attempt

        results["attempts"].append(attempt_result)

        # Small delay between attempts
        if attempt < max_attempts:
            time.sleep(5)

    if not results["success"]:
        results["final_status"] = (
            results["attempts"][-1]["status"] if results["attempts"] else "UNKNOWN"
        )

    return results


def poll_status(
    reference: str | None = None,
    timeout: int = 300,
    interval: int = 10,
    exponential_backoff: bool = True,
) -> dict:
    """
    Poll CI status with exponential backoff until completion or timeout.

    Args:
        reference: PR number or branch name
        timeout: Maximum time to wait in seconds
        interval: Initial polling interval in seconds
        exponential_backoff: Whether to use exponential backoff

    Returns:
        Dictionary with polling results
    """
    start_time = time.time()
    current_interval = interval
    max_interval = 60  # Cap at 60 seconds

    results = {"polls": [], "final_status": None, "success": False, "timed_out": False}

    poll_count = 0
    while time.time() - start_time < timeout:
        poll_count += 1
        elapsed = int(time.time() - start_time)

        # Check CI status
        status_result = check_ci_status(reference)
        status = status_result.get("status", "UNKNOWN")

        poll_result = {
            "poll": poll_count,
            "elapsed_seconds": elapsed,
            "status": status,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        results["polls"].append(poll_result)

        print(f"[{elapsed}s] Poll #{poll_count}: {status}")

        # Check if we're done
        if status in ["PASSING", "FAILING", "NO_CHECKS"]:
            results["final_status"] = status
            results["success"] = status == "PASSING"
            print(f"\n✓ CI completed with status: {status}")
            break

        # Wait before next poll
        if time.time() - start_time + current_interval < timeout:
            print(f"  Waiting {current_interval}s before next poll...")
            time.sleep(current_interval)

            # Apply exponential backoff if enabled
            if exponential_backoff:
                current_interval = min(current_interval * 1.5, max_interval)
        else:
            # Would exceed timeout
            break

    # Check if we timed out
    if results["final_status"] is None:
        results["timed_out"] = True
        results["final_status"] = results["polls"][-1]["status"] if results["polls"] else "UNKNOWN"
        print(f"\n✗ Timed out after {timeout}s. Last status: {results['final_status']}")

    return results


def main():
    """CLI interface for CI workflow tool."""
    parser = argparse.ArgumentParser(
        description="CI Workflow Tool - Higher-level CI management functionality"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Diagnose command
    diagnose_parser = subparsers.add_parser("diagnose", help="Run parallel CI diagnostics")
    diagnose_parser.add_argument("--pr", type=int, help="PR number to diagnose")
    diagnose_parser.add_argument("--branch", help="Branch name to diagnose")
    diagnose_parser.add_argument("--json", action="store_true", help="Output raw JSON")

    # Iterate fixes command
    iterate_parser = subparsers.add_parser(
        "iterate-fixes", help="Iterate CI fixes with max attempts"
    )
    iterate_parser.add_argument(
        "--max-attempts", type=int, default=5, help="Maximum number of fix attempts (default: 5)"
    )
    iterate_parser.add_argument("--pr", type=int, help="PR number to fix CI for")
    iterate_parser.add_argument("--json", action="store_true", help="Output raw JSON")

    # Poll status command
    poll_parser = subparsers.add_parser(
        "poll-status", help="Poll CI status with exponential backoff"
    )
    poll_parser.add_argument("reference", nargs="?", help="PR number or branch name")
    poll_parser.add_argument(
        "--timeout", type=int, default=300, help="Timeout in seconds (default: 300)"
    )
    poll_parser.add_argument(
        "--interval", type=int, default=10, help="Initial polling interval in seconds (default: 10)"
    )
    poll_parser.add_argument(
        "--no-backoff", action="store_true", help="Disable exponential backoff"
    )
    poll_parser.add_argument("--json", action="store_true", help="Output raw JSON")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    result = {}  # Initialize to avoid possibly unbound error

    if args.command == "diagnose":
        result = diagnose_ci(pr_number=args.pr, branch=args.branch)

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print("\nCI Diagnostics Report")
            print("=" * 50)
            print(f"Overall Status: {result['overall_status']}")

            if result.get("ci_status"):
                print(f"\nCI Status: {result['ci_status'].get('status', 'UNKNOWN')}")
                if result["ci_status"].get("summary"):
                    summary = result["ci_status"]["summary"]
                    print(f"  Passed: {summary.get('passed', 0)}")
                    print(f"  Failed: {summary.get('failed', 0)}")
                    print(f"  Pending: {summary.get('pending', 0)}")

            for check_name in ["lint_check", "test_check", "build_check"]:
                if result.get(check_name):
                    check = result[check_name]
                    status = "✓" if check.get("success") else "✗"
                    print(f"\n{check_name.replace('_', ' ').title()}: {status}")
                    if check.get("command"):
                        print(f"  Command: {check['command']}")
                    if not check.get("success") and check.get("output"):
                        print(f"  Error: {check['output'][:200]}")

            if result.get("errors"):
                print("\nErrors:")
                for error in result["errors"]:
                    print(f"  - {error}")

    elif args.command == "iterate-fixes":
        result = iterate_fixes(max_attempts=args.max_attempts, pr_number=args.pr)

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print("\nCI Fix Iteration Report")
            print("=" * 50)
            print(f"Success: {result['success']}")
            print(f"Final Status: {result['final_status']}")
            print(f"Attempts: {len(result['attempts'])}")

            for attempt in result["attempts"]:
                print(f"\nAttempt {attempt['attempt']}: {attempt['status']}")
                if attempt.get("fixes_applied"):
                    print("  Fixes applied:")
                    for fix in attempt["fixes_applied"]:
                        if fix.get("command"):
                            status = "✓" if fix.get("success") else "✗"
                            print(f"    {status} {fix['command']}")
                        elif fix.get("message"):
                            print(f"    - {fix['message']}")

    elif args.command == "poll-status":
        result = poll_status(
            reference=args.reference,
            timeout=args.timeout,
            interval=args.interval,
            exponential_backoff=not args.no_backoff,
        )

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print("\nCI Status Polling Report")
            print("=" * 50)
            print(f"Success: {result['success']}")
            print(f"Final Status: {result['final_status']}")
            print(f"Timed Out: {result['timed_out']}")
            print(f"Total Polls: {len(result['polls'])}")

            if result["polls"]:
                print("\nPolling History:")
                for poll in result["polls"][-5:]:  # Show last 5 polls
                    print(f"  [{poll['elapsed_seconds']}s] {poll['status']}")

    # Note: result is guaranteed to be defined due to the if/elif structure above
    # Set exit code based on command
    if args.command == "diagnose":
        sys.exit(0 if result.get("overall_status") == "ALL_PASSING" else 1)
    else:  # iterate-fixes or poll-status
        sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
