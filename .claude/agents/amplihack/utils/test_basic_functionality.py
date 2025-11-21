#!/usr/bin/env python3
"""
Quick validation test for structure detection functionality.

This tests basic import and functionality without requiring pytest.
Run: python test_basic_functionality.py
"""

import tempfile
import shutil
from pathlib import Path

from structure_detection import (
    detect_project_structure,
    validate_target_location,
    Signal,
    SignalScanner,
    PriorityEngine,
    ResultClassifier
)


def test_imports():
    """Test that all exports are available."""
    print("✓ All imports successful")


def test_signal_creation():
    """Test Signal dataclass."""
    signal = Signal(
        signal_type="stub",
        source_file="/path/to/stub.py",
        inferred_location="/path/to",
        confidence=0.90,
        evidence="Stub file",
        parsed_at="2025-11-21T00:00:00"
    )
    assert signal.confidence == 0.90
    print("✓ Signal dataclass working")


def test_with_temp_project():
    """Test detection with temporary project."""
    temp_dir = tempfile.mkdtemp()
    try:
        temp_path = Path(temp_dir)

        # Create stub file
        tools_dir = temp_path / "tools"
        tools_dir.mkdir()
        stub_file = tools_dir / "analyzer.stub.py"
        stub_file.write_text("# Stub")

        # Run detection
        result = detect_project_structure(str(temp_path))

        assert result is not None
        assert result.confidence > 0.0
        print(f"✓ Detection working: {result.detection_method} at {result.detected_root}")

        # Test validation
        if result.detected_root:
            validation = validate_target_location(
                Path(result.detected_root),
                temp_path
            )
            print(f"✓ Validation working: {validation.passed}")

    finally:
        shutil.rmtree(temp_dir)


def test_scanner():
    """Test SignalScanner component."""
    temp_dir = tempfile.mkdtemp()
    try:
        temp_path = Path(temp_dir)

        # Create some structure
        tools_dir = temp_path / "tools"
        tools_dir.mkdir()
        (tools_dir / "test.py").write_text("# Test")

        scanner = SignalScanner(temp_path)
        signals = scanner.scan_conventions()

        assert isinstance(signals, list)
        print(f"✓ Scanner found {len(signals)} signals")

    finally:
        shutil.rmtree(temp_dir)


def test_priority_engine():
    """Test PriorityEngine component."""
    signals = [
        Signal("convention", "", "/path/conv", 0.70, "conv", ""),
        Signal("stub", "", "/path/stub", 0.90, "stub", ""),
        Signal("test", "", "/path/test", 0.85, "test", ""),
    ]

    engine = PriorityEngine()
    ranked = engine.rank_signals(signals)

    assert len(ranked) == 3
    assert ranked[0].signal.signal_type == "stub"  # Highest priority
    print("✓ Priority engine working")


def test_fallback():
    """Test fallback detection works (integrated into detect_project_structure)."""
    temp_dir = tempfile.mkdtemp()
    try:
        temp_path = Path(temp_dir)

        # Fallback is tested via full detection when no signals exist
        result = detect_project_structure(str(temp_path))

        # Should have fallback result
        assert result is not None
        print(f"✓ Fallback detection working: {result.detection_method}")

    finally:
        shutil.rmtree(temp_dir)


def main():
    """Run all validation tests."""
    print("Running structure detection validation tests...\n")

    tests = [
        ("Imports", test_imports),
        ("Signal Creation", test_signal_creation),
        ("Full Detection", test_with_temp_project),
        ("Scanner Component", test_scanner),
        ("Priority Engine", test_priority_engine),
        ("Fallback Detector", test_fallback),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            print(f"\n{name}:")
            test_func()
            passed += 1
        except Exception as e:
            print(f"✗ {name} failed: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*60}")

    if failed == 0:
        print("\n🎉 All validation tests passed!")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit(main())
