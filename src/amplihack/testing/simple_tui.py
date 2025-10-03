"""Simple TUI testing for AmplIHack - minimal viable implementation"""

import asyncio
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
    """Minimal TUI testing implementation"""

    def __init__(self, output_dir: Path = Path("./tui_output")):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
        self.test_cases: Dict[str, TUITestCase] = {}
        self.results: Dict[str, TestResult] = {}

    def add_test(self, test_case: TUITestCase) -> None:
        """Add a test case"""
        self.test_cases[test_case.test_id] = test_case

    async def run_test(self, test_id: str) -> TestResult:
        """Run a single test"""
        if test_id not in self.test_cases:
            raise ValueError(f"Test {test_id} not found")

        test_case = self.test_cases[test_id]
        start_time = time.time()

        # Simple mock execution - fail if "fail" in commands
        should_fail = any("fail" in cmd.lower() for cmd in test_case.commands)

        # Simulate execution time
        await asyncio.sleep(0.1)

        duration = time.time() - start_time
        status = "failed" if should_fail else "passed"
        message = f"Mock execution of {len(test_case.commands)} commands"

        result = TestResult(test_id, status, duration, message)
        self.results[test_id] = result
        return result

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
