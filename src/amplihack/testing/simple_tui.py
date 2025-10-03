"""Simple TUI testing for AmplIHack - using gadugi-agentic-test framework"""

import json
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
    timeout: int = 30


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
        try:
            result = subprocess.run(
                ["npx", "gadugi-test", "--help"], capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
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

                # Run the test using gadugi
                try:
                    result = subprocess.run(
                        ["npx", "gadugi-test", "run", str(config_file)],
                        capture_output=True,
                        text=True,
                        timeout=test_case.timeout + 30,
                        cwd=self.output_dir,
                    )

                    duration = time.time() - start_time

                    if result.returncode == 0:
                        return TestResult(
                            test_id,
                            "passed",
                            duration,
                            f"gadugi-test completed successfully: {result.stdout.strip()}",
                        )
                    else:
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
                    try:
                        result = subprocess.run(
                            command.split(),
                            capture_output=True,
                            text=True,
                            timeout=test_case.timeout,
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
                            f"Command '{command}' timed out after {test_case.timeout} seconds",
                        )
                    except Exception as e:
                        duration += time.time() - cmd_start
                        return TestResult(
                            test_id,
                            "failed",
                            duration,
                            f"Command '{command}' failed with error: {str(e)}",
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
            return TestResult(test_id, "failed", duration, f"Test execution failed: {str(e)}")

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


async def test_amplihack_basics() -> Dict[str, TestResult]:
    """Test basic AmplIHack commands"""
    tester = create_tui_tester()

    # Add basic tests
    tester.add_test(create_amplihack_test("help", "--help"))
    tester.add_test(create_amplihack_test("version", "--version"))

    return await tester.run_all()
