#!/usr/bin/env python
"""
Verification script for PR #4: Subagent Mapper Tool

Verifies all requirements are met.
"""

import sys
from pathlib import Path


def verify_module_structure():
    """Verify module structure matches specification."""
    print("Verifying module structure...")

    base_path = Path("src/amplihack/analytics")

    required_files = [
        "__init__.py",
        "metrics_reader.py",
        "visualization.py",
        "subagent_mapper.py",
        "README.md",
        "tests/__init__.py",
        "tests/test_metrics_reader.py",
        "tests/test_visualization.py",
        "tests/test_subagent_mapper.py",
    ]

    all_exist = True
    for file_path in required_files:
        full_path = base_path / file_path
        if full_path.exists():
            print(f"  ✓ {file_path}")
        else:
            print(f"  ✗ {file_path} MISSING")
            all_exist = False

    return all_exist


def verify_public_api():
    """Verify public API exports."""
    print("\nVerifying public API...")

    try:
        from src.amplihack.analytics import (
            MetricsReader,
            SubagentEvent,
            SubagentExecution,
            ReportGenerator,
            ExecutionTreeBuilder,
            PatternDetector,
            AsciiTreeRenderer,
            AgentNode,
            Pattern,
            main,
        )

        exports = [
            "MetricsReader",
            "SubagentEvent",
            "SubagentExecution",
            "ReportGenerator",
            "ExecutionTreeBuilder",
            "PatternDetector",
            "AsciiTreeRenderer",
            "AgentNode",
            "Pattern",
            "main",
        ]

        for export in exports:
            print(f"  ✓ {export}")

        return True
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        return False


def verify_cli_interface():
    """Verify CLI interface works."""
    print("\nVerifying CLI interface...")

    try:
        from src.amplihack.analytics.subagent_mapper import parse_args

        # Test basic argument parsing
        args = parse_args([])
        print(f"  ✓ Default args parsed")

        args = parse_args(["--session-id", "test"])
        assert args.session_id == "test"
        print(f"  ✓ --session-id works")

        args = parse_args(["--agent", "architect"])
        assert args.agent == "architect"
        print(f"  ✓ --agent works")

        args = parse_args(["--output", "json"])
        assert args.output == "json"
        print(f"  ✓ --output works")

        args = parse_args(["--stats"])
        assert args.stats is True
        print(f"  ✓ --stats works")

        args = parse_args(["--list-sessions"])
        assert args.list_sessions is True
        print(f"  ✓ --list-sessions works")

        return True
    except Exception as e:
        print(f"  ✗ CLI test failed: {e}")
        return False


def verify_functionality():
    """Verify core functionality works."""
    print("\nVerifying core functionality...")

    try:
        import tempfile
        import json
        from src.amplihack.analytics import MetricsReader, ReportGenerator

        # Create test metrics
        with tempfile.TemporaryDirectory() as tmpdir:
            metrics_dir = Path(tmpdir)

            # Write test data
            with open(metrics_dir / "subagent_start.jsonl", "w") as f:
                f.write(json.dumps({
                    "event": "start",
                    "agent_name": "test_agent",
                    "session_id": "test_session",
                    "timestamp": "2025-11-02T14:30:00.000Z",
                    "execution_id": "exec_001"
                }) + "\n")

            with open(metrics_dir / "subagent_stop.jsonl", "w") as f:
                f.write(json.dumps({
                    "event": "stop",
                    "agent_name": "test_agent",
                    "session_id": "test_session",
                    "timestamp": "2025-11-02T14:30:05.000Z",
                    "execution_id": "exec_001",
                    "duration_ms": 5000.0
                }) + "\n")

            # Test reading
            reader = MetricsReader(metrics_dir=metrics_dir)
            events = reader.read_events()
            assert len(events) == 2
            print(f"  ✓ MetricsReader.read_events() works")

            executions = reader.build_executions()
            assert len(executions) == 1
            print(f"  ✓ MetricsReader.build_executions() works")

            # Test reporting
            generator = ReportGenerator(reader)
            text_report = generator.generate_text_report(session_id="test_session")
            assert "test_agent" in text_report
            print(f"  ✓ ReportGenerator.generate_text_report() works")

            json_report = generator.generate_json_report(session_id="test_session")
            assert json_report["session_id"] == "test_session"
            print(f"  ✓ ReportGenerator.generate_json_report() works")

        return True
    except Exception as e:
        print(f"  ✗ Functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all verification checks."""
    print("=" * 64)
    print("Subagent Mapper Tool - Implementation Verification")
    print("=" * 64)
    print()

    checks = [
        ("Module Structure", verify_module_structure),
        ("Public API", verify_public_api),
        ("CLI Interface", verify_cli_interface),
        ("Core Functionality", verify_functionality),
    ]

    results = []
    for name, check_func in checks:
        result = check_func()
        results.append((name, result))
        print()

    # Summary
    print("=" * 64)
    print("Summary")
    print("=" * 64)

    all_passed = True
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} {name}")
        if not result:
            all_passed = False

    print()
    if all_passed:
        print("✓ All verification checks passed!")
        return 0
    else:
        print("✗ Some verification checks failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
