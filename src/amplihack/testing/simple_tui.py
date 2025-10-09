"""Simple TUI testing for AmplIHack - using gadugi-agentic-test framework"""

import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class TestResult:
    """Simple test result"""

    test_id: str
    status: str  # "passed", "failed"
    duration: float
    message: str = ""


@dataclass
class TUITestCase:
    """Simple test case"""

    test_id: str
    name: str
    commands: List[str]
    timeout: int = 10  # Reduce default timeout for CI friendliness


class SimpleTUITester:
    """TUI testing implementation using gadugi-agentic-test framework via subprocess"""

    def __init__(self, output_dir: Path = Path("./tui_output")):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
        self.test_cases: Dict[str, TUITestCase] = {}
        self.results: Dict[str, TestResult] = {}

    def add_test(self, test_case: TUITestCase) -> None:
        """Add a test case"""
        self.test_cases[test_case.test_id] = test_case

    def _check_gadugi_available(self) -> bool:
        """Check if gadugi-agentic-test is available"""
        # In CI environments, we want to avoid hanging on npx downloads
        # Check if we're in a CI environment and disable gadugi to prevent hangs
        ci_env_vars = ["CI", "GITHUB_ACTIONS", "TRAVIS", "CIRCLECI", "JENKINS_URL"]
        if any(os.environ.get(var) for var in ci_env_vars):
            return False

        try:
            # First check if npx is available at all
            npx_check = subprocess.run(
                ["npx", "--version"], capture_output=True, text=True, timeout=3
            )
            if npx_check.returncode != 0:
                return False

            # Then check gadugi-test with a short timeout to avoid CI hangs
            result = subprocess.run(
                ["npx", "gadugi-test", "--help"],
                capture_output=True,
                text=True,
                timeout=3,
                # Prevent npx from auto-installing packages in CI
                env={**os.environ, "NPX_NO_INSTALL": "1"},
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False

    async def run_test(self, test_id: str) -> TestResult:
        """Run a single test using gadugi-agentic-test framework or fallback"""
        if test_id not in self.test_cases:
            raise ValueError(f"Test {test_id} not found")

        test_case = self.test_cases[test_id]
        start_time = time.time()

        try:
            # Check if gadugi is available
            if self._check_gadugi_available():
                # Create a temporary test configuration for gadugi
                test_config = {
                    "testId": test_case.test_id,
                    "name": test_case.name,
                    "commands": test_case.commands,
                    "timeout": test_case.timeout,
                }

                config_file = self.output_dir / f"{test_id}_config.json"
                with open(config_file, "w") as f:
                    json.dump(test_config, f)

                # Run the test using gadugi with reduced timeout for CI
                try:
                    gadugi_timeout = min(test_case.timeout + 10, 30)  # Cap gadugi timeout
                    result = subprocess.run(
                        ["npx", "gadugi-test", "run", str(config_file)],
                        capture_output=True,
                        text=True,
                        timeout=gadugi_timeout,
                        cwd=self.output_dir,
                        env={**os.environ, "CI": "true"},
                    )

                    duration = time.time() - start_time

                    if result.returncode == 0:
                        return TestResult(
                            test_id,
                            "passed",
                            duration,
                            f"gadugi-test completed successfully: {result.stdout.strip()}",
                        )
                    return TestResult(
                        test_id,
                        "failed",
                        duration,
                        f"gadugi-test failed: {result.stderr.strip()}",
                    )

                except subprocess.TimeoutExpired:
                    duration = time.time() - start_time
                    return TestResult(
                        test_id,
                        "failed",
                        duration,
                        f"Test timed out after {test_case.timeout + 30} seconds",
                    )
                finally:
                    # Clean up config file
                    config_file.unlink(missing_ok=True)
            else:
                # Fallback to simplified execution using basic subprocess
                duration = 0
                for command in test_case.commands:
                    cmd_start = time.time()
                    # Use a shorter timeout for individual commands to prevent CI hangs
                    cmd_timeout = min(test_case.timeout, 5)  # Cap at 5 seconds per command in CI

                    # Split command into parts for validation
                    cmd_parts = command.split()
                    if not cmd_parts:
                        return TestResult(
                            test_id, "failed", duration, f"Empty command provided: '{command}'"
                        )

                    # Check if command exists first (prevent hanging on non-existent commands)
                    command_exists = False
                    try:
                        which_result = subprocess.run(
                            ["which", cmd_parts[0]],
                            capture_output=True,
                            text=True,
                            timeout=2,
                            env={**os.environ, "PATH": os.environ.get("PATH", "")},
                        )
                        command_exists = which_result.returncode == 0
                    except (subprocess.TimeoutExpired, FileNotFoundError):
                        command_exists = False

                    # If command doesn't exist, fail fast instead of hanging
                    if not command_exists:
                        return TestResult(
                            test_id,
                            "failed",
                            duration,
                            f"Command '{cmd_parts[0]}' not found in PATH. Available commands can be checked with 'which {cmd_parts[0]}'",
                        )

                    try:
                        result = subprocess.run(
                            cmd_parts,
                            capture_output=True,
                            text=True,
                            timeout=cmd_timeout,
                            # Add environment variables to prevent interactive prompts
                            env={**os.environ, "CI": "true", "DEBIAN_FRONTEND": "noninteractive"},
                        )
                        duration += time.time() - cmd_start

                        if result.returncode != 0:
                            return TestResult(
                                test_id,
                                "failed",
                                duration,
                                f"Command '{command}' failed with exit code {result.returncode}: {result.stderr.strip()}",
                            )
                    except subprocess.TimeoutExpired:
                        duration += time.time() - cmd_start
                        return TestResult(
                            test_id,
                            "failed",
                            duration,
                            f"Command '{command}' timed out after {cmd_timeout} seconds",
                        )
                    except FileNotFoundError:
                        duration += time.time() - cmd_start
                        return TestResult(
                            test_id,
                            "failed",
                            duration,
                            f"Command '{cmd_parts[0]}' not found",
                        )
                    except Exception as e:
                        duration += time.time() - cmd_start
                        return TestResult(
                            test_id,
                            "failed",
                            duration,
                            f"Command '{command}' failed with error: {e!s}",
                        )

                # All commands succeeded
                total_duration = time.time() - start_time
                return TestResult(
                    test_id,
                    "passed",
                    total_duration,
                    f"Successfully executed {len(test_case.commands)} commands via subprocess",
                )

        except Exception as e:
            duration = time.time() - start_time
            return TestResult(test_id, "failed", duration, f"Test execution failed: {e!s}")

    async def run_all(self) -> Dict[str, TestResult]:
        """Run all tests"""
        results = {}
        for test_id in self.test_cases:
            results[test_id] = await self.run_test(test_id)
        return results


# Simple factory function
def create_tui_tester(output_dir: Optional[Path] = None) -> SimpleTUITester:
    """Create a simple TUI tester"""
    return SimpleTUITester(output_dir or Path("./tui_output"))


# Convenience functions for AmplIHack CLI testing
def create_amplihack_test(test_id: str, args: str) -> TUITestCase:
    """Create an AmplIHack CLI test"""
    return TUITestCase(test_id=test_id, name=f"AmplIHack {args}", commands=[f"amplihack {args}"])


async def run_amplihack_basics() -> Dict[str, TestResult]:
    """Test basic AmplIHack commands"""
    tester = create_tui_tester()

    # Add basic tests - only use commands that actually exist
    tester.add_test(create_amplihack_test("help", "--help"))
    # Replace --version with install --help since --version doesn't exist
    tester.add_test(create_amplihack_test("install_help", "install --help"))

    return await tester.run_all()
