#!/usr/bin/env python3
"""
Improvement Workflow Validator

Provides validation functionality for the improvement workflow to ensure
changes remain simple, focused, and aligned with philosophy.
"""

import argparse
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ValidationLevel(Enum):
    """Validation severity levels"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationResult:
    """Result of a validation check"""

    passed: bool
    level: ValidationLevel
    message: str
    details: dict[str, Any] | None = None


class ComplexityDetector:
    """Detects when improvements are becoming too complex"""

    # Thresholds for complexity
    MAX_AGENTS = 3
    MAX_LOC_PER_CHANGE = 200
    MAX_TEST_RATIO = 2.0  # Tests should not be 2x the code
    MAX_ABSTRACTION_DEPTH = 3

    @classmethod
    def check_agent_count(cls, agent_count: int) -> ValidationResult:
        """Check if too many agents are being used"""
        if agent_count <= cls.MAX_AGENTS:
            return ValidationResult(
                passed=True,
                level=ValidationLevel.INFO,
                message=f"Agent count ({agent_count}) is within limits",
            )

        return ValidationResult(
            passed=False,
            level=ValidationLevel.WARNING,
            message=f"Too many agents ({agent_count} > {cls.MAX_AGENTS})",
            details={
                "suggestion": "Consider if this can be done with fewer specialized agents",
                "threshold": cls.MAX_AGENTS,
                "actual": agent_count,
            },
        )

    @classmethod
    def check_code_volume(cls, lines_of_code: int) -> ValidationResult:
        """Check if change is too large"""
        if lines_of_code <= cls.MAX_LOC_PER_CHANGE:
            return ValidationResult(
                passed=True,
                level=ValidationLevel.INFO,
                message=f"Code volume ({lines_of_code} LOC) is reasonable",
            )

        return ValidationResult(
            passed=False,
            level=ValidationLevel.WARNING,
            message=f"Change is too large ({lines_of_code} > {cls.MAX_LOC_PER_CHANGE} LOC)",
            details={
                "suggestion": "Break this into smaller, incremental improvements",
                "threshold": cls.MAX_LOC_PER_CHANGE,
                "actual": lines_of_code,
            },
        )

    @classmethod
    def check_test_ratio(cls, test_loc: int, code_loc: int) -> ValidationResult:
        """Check if tests are becoming excessive"""
        if code_loc == 0:
            return ValidationResult(
                passed=True, level=ValidationLevel.INFO, message="No code changes to test"
            )

        ratio = test_loc / code_loc
        if ratio <= cls.MAX_TEST_RATIO:
            return ValidationResult(
                passed=True,
                level=ValidationLevel.INFO,
                message=f"Test ratio ({ratio:.1f}:1) is reasonable",
            )

        return ValidationResult(
            passed=False,
            level=ValidationLevel.WARNING,
            message=f"Excessive testing ({ratio:.1f}:1 ratio)",
            details={
                "suggestion": "Focus on key behaviors, not implementation details",
                "test_loc": test_loc,
                "code_loc": code_loc,
                "ratio": ratio,
            },
        )

    @classmethod
    def check_abstraction_depth(cls, depth: int) -> ValidationResult:
        """Check if abstractions are too deep"""
        if depth <= cls.MAX_ABSTRACTION_DEPTH:
            return ValidationResult(
                passed=True,
                level=ValidationLevel.INFO,
                message=f"Abstraction depth ({depth}) is acceptable",
            )

        return ValidationResult(
            passed=False,
            level=ValidationLevel.WARNING,
            message=f"Over-abstraction detected (depth: {depth})",
            details={
                "suggestion": "Flatten the structure, prefer direct solutions",
                "threshold": cls.MAX_ABSTRACTION_DEPTH,
                "actual": depth,
            },
        )


class HardStopChecker:
    """Checks for conditions that should stop the improvement"""

    @classmethod
    def check_security(cls, has_security_issue: bool, issue_details: str = "") -> ValidationResult:
        """Check for security issues"""
        if not has_security_issue:
            return ValidationResult(
                passed=True, level=ValidationLevel.INFO, message="No security issues detected"
            )

        return ValidationResult(
            passed=False,
            level=ValidationLevel.CRITICAL,
            message="Security issue detected - STOP",
            details={
                "action": "Fix security issue before any improvements",
                "issue": issue_details,
            },
        )

    @classmethod
    def check_philosophy(
        cls, violates_philosophy: bool, violation_details: str = ""
    ) -> ValidationResult:
        """Check for philosophy violations"""
        if not violates_philosophy:
            return ValidationResult(
                passed=True, level=ValidationLevel.INFO, message="Aligned with project philosophy"
            )

        return ValidationResult(
            passed=False,
            level=ValidationLevel.ERROR,
            message="Philosophy violation detected",
            details={"action": "Realign with core principles", "violation": violation_details},
        )

    @classmethod
    def check_redundancy(cls, is_redundant: bool, existing_solution: str = "") -> ValidationResult:
        """Check if improvement duplicates existing work"""
        if not is_redundant:
            return ValidationResult(
                passed=True, level=ValidationLevel.INFO, message="No redundancy detected"
            )

        return ValidationResult(
            passed=False,
            level=ValidationLevel.ERROR,
            message="Redundant with existing solution",
            details={
                "action": "Use or improve existing solution instead",
                "existing": existing_solution,
            },
        )


class StageValidator:
    """Validates each stage of the improvement pipeline"""

    @classmethod
    def validate_stage_1_problem(cls, problem: str) -> ValidationResult:
        """Stage 1: Is this a real problem worth solving?"""
        checks = {
            "has_description": len(problem.strip()) > 10,
            "is_specific": not any(
                vague in problem.lower() for vague in ["something", "stuff", "things"]
            ),
            "is_actionable": any(
                action in problem.lower()
                for action in ["slow", "broken", "missing", "error", "fail"]
            ),
        }

        if all(checks.values()):
            return ValidationResult(
                passed=True,
                level=ValidationLevel.INFO,
                message="Problem is well-defined and worth solving",
            )

        return ValidationResult(
            passed=False,
            level=ValidationLevel.WARNING,
            message="Problem definition needs clarification",
            details={"checks": checks},
        )

    @classmethod
    def validate_stage_2_solution(cls, solution_loc: int, uses_existing: bool) -> ValidationResult:
        """Stage 2: Is the solution simple enough?"""
        if solution_loc <= 50 and uses_existing:
            return ValidationResult(
                passed=True,
                level=ValidationLevel.INFO,
                message="Solution is simple and reuses existing code",
            )

        if solution_loc > 200:
            return ValidationResult(
                passed=False,
                level=ValidationLevel.ERROR,
                message="Solution is too complex",
                details={"loc": solution_loc, "suggestion": "Break into smaller changes"},
            )

        return ValidationResult(
            passed=True,
            level=ValidationLevel.WARNING,
            message="Solution is acceptable but could be simpler",
            details={"loc": solution_loc, "uses_existing": uses_existing},
        )

    @classmethod
    def validate_stage_3_testing(cls, has_tests: bool, test_count: int) -> ValidationResult:
        """Stage 3: Are tests focused on behavior?"""
        if not has_tests:
            return ValidationResult(
                passed=False, level=ValidationLevel.ERROR, message="No tests provided"
            )

        if test_count > 10:
            return ValidationResult(
                passed=False,
                level=ValidationLevel.WARNING,
                message="Too many tests - focus on key behaviors",
                details={"test_count": test_count},
            )

        return ValidationResult(
            passed=True,
            level=ValidationLevel.INFO,
            message=f"Testing is appropriate ({test_count} tests)",
        )

    @classmethod
    def validate_stage_4_documentation(cls, has_docs: bool, doc_loc: int) -> ValidationResult:
        """Stage 4: Is documentation minimal but clear?"""
        if not has_docs:
            return ValidationResult(
                passed=False, level=ValidationLevel.WARNING, message="Missing documentation"
            )

        if doc_loc > 50:
            return ValidationResult(
                passed=False,
                level=ValidationLevel.WARNING,
                message="Over-documented - keep it concise",
                details={"doc_loc": doc_loc},
            )

        return ValidationResult(
            passed=True, level=ValidationLevel.INFO, message="Documentation is appropriate"
        )

    @classmethod
    def validate_stage_5_integration(
        cls, breaks_existing: bool, adds_deps: int
    ) -> ValidationResult:
        """Stage 5: Does it integrate cleanly?"""
        if breaks_existing:
            return ValidationResult(
                passed=False,
                level=ValidationLevel.CRITICAL,
                message="Breaks existing functionality",
                details={"action": "Fix breaking changes before proceeding"},
            )

        if adds_deps > 2:
            return ValidationResult(
                passed=False,
                level=ValidationLevel.WARNING,
                message=f"Adds too many dependencies ({adds_deps})",
                details={"suggestion": "Minimize external dependencies"},
            )

        return ValidationResult(
            passed=True,
            level=ValidationLevel.INFO,
            message="Integrates cleanly with existing system",
        )


def print_result(result: ValidationResult):
    """Print validation result with appropriate formatting"""
    symbols = {
        ValidationLevel.INFO: "✓",
        ValidationLevel.WARNING: "⚠",
        ValidationLevel.ERROR: "✗",
        ValidationLevel.CRITICAL: "⛔",
    }

    colors = {
        ValidationLevel.INFO: "\033[32m",  # Green
        ValidationLevel.WARNING: "\033[33m",  # Yellow
        ValidationLevel.ERROR: "\033[31m",  # Red
        ValidationLevel.CRITICAL: "\033[91m",  # Bright Red
    }

    reset = "\033[0m"

    print(f"{colors[result.level]}{symbols[result.level]} {result.message}{reset}")

    if result.details:
        for key, value in result.details.items():
            print(f"  {key}: {value}")


def main():
    parser = argparse.ArgumentParser(description="Improvement Workflow Validator")
    subparsers = parser.add_subparsers(dest="command", help="Validation commands")

    # Complexity checks
    complexity_parser = subparsers.add_parser(
        "check-complexity", help="Check improvement complexity"
    )
    complexity_parser.add_argument("--agents", type=int, help="Number of agents involved")
    complexity_parser.add_argument("--loc", type=int, help="Lines of code changed")
    complexity_parser.add_argument("--test-loc", type=int, help="Lines of test code")
    complexity_parser.add_argument("--code-loc", type=int, help="Lines of production code")
    complexity_parser.add_argument("--depth", type=int, help="Abstraction depth")

    # Hard stops checks
    hardstop_parser = subparsers.add_parser(
        "check-hard-stops", help="Check for hard stop conditions"
    )
    hardstop_parser.add_argument(
        "--security", action="store_true", help="Check for security issues"
    )
    hardstop_parser.add_argument(
        "--philosophy", action="store_true", help="Check philosophy alignment"
    )
    hardstop_parser.add_argument("--redundancy", action="store_true", help="Check for redundancy")
    hardstop_parser.add_argument("--details", type=str, help="Additional details for the check")

    # Stage validation
    stage_parser = subparsers.add_parser("validate-stage", help="Validate a pipeline stage")
    stage_parser.add_argument(
        "--stage", type=int, required=True, choices=[1, 2, 3, 4, 5], help="Stage number"
    )
    stage_parser.add_argument("--problem", type=str, help="Problem description (stage 1)")
    stage_parser.add_argument("--solution-loc", type=int, help="Solution lines of code (stage 2)")
    stage_parser.add_argument(
        "--uses-existing", action="store_true", help="Uses existing code (stage 2)"
    )
    stage_parser.add_argument("--has-tests", action="store_true", help="Has tests (stage 3)")
    stage_parser.add_argument("--test-count", type=int, help="Number of tests (stage 3)")
    stage_parser.add_argument("--has-docs", action="store_true", help="Has documentation (stage 4)")
    stage_parser.add_argument("--doc-loc", type=int, help="Documentation lines (stage 4)")
    stage_parser.add_argument(
        "--breaks-existing", action="store_true", help="Breaks existing code (stage 5)"
    )
    stage_parser.add_argument(
        "--adds-deps", type=int, default=0, help="Number of new dependencies (stage 5)"
    )

    # Full validation
    full_parser = subparsers.add_parser("validate-all", help="Run all validations")
    full_parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    results = []

    if args.command == "check-complexity":
        if args.agents is not None:
            results.append(ComplexityDetector.check_agent_count(args.agents))
        if args.loc is not None:
            results.append(ComplexityDetector.check_code_volume(args.loc))
        if args.test_loc is not None and args.code_loc is not None:
            results.append(ComplexityDetector.check_test_ratio(args.test_loc, args.code_loc))
        if args.depth is not None:
            results.append(ComplexityDetector.check_abstraction_depth(args.depth))

    elif args.command == "check-hard-stops":
        details = args.details or ""
        if args.security:
            results.append(HardStopChecker.check_security(True, details))
        if args.philosophy:
            results.append(HardStopChecker.check_philosophy(True, details))
        if args.redundancy:
            results.append(HardStopChecker.check_redundancy(True, details))

    elif args.command == "validate-stage":
        if args.stage == 1:
            if args.problem:
                results.append(StageValidator.validate_stage_1_problem(args.problem))
        elif args.stage == 2:
            if args.solution_loc is not None:
                results.append(
                    StageValidator.validate_stage_2_solution(args.solution_loc, args.uses_existing)
                )
        elif args.stage == 3:
            if args.test_count is not None:
                results.append(
                    StageValidator.validate_stage_3_testing(args.has_tests, args.test_count)
                )
        elif args.stage == 4:
            if args.doc_loc is not None:
                results.append(
                    StageValidator.validate_stage_4_documentation(args.has_docs, args.doc_loc)
                )
        elif args.stage == 5:
            results.append(
                StageValidator.validate_stage_5_integration(args.breaks_existing, args.adds_deps)
            )

    # Print results
    for result in results:
        print_result(result)

    # Return non-zero if any critical or error results
    if any(r.level in [ValidationLevel.ERROR, ValidationLevel.CRITICAL] for r in results):
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
