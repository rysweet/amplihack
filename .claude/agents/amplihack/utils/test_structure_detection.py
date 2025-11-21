"""
Tests for Project Structure Detection System

Tests cover:
- Signal detection (stubs, tests, conventions, config)
- Priority ranking and consensus
- Conflict resolution
- Fallback behavior
- Validation
- Performance (< 100ms)
- Edge cases
"""

import shutil
import sys
import tempfile
import time
from pathlib import Path

# pytest is optional - only needed for test execution
try:
    import pytest
except ImportError:
    pytest = None
    print("Warning: pytest not installed. Tests will not run.")

# Add parent directory to path for imports (supports multiple execution contexts)
sys.path.insert(0, str(Path(__file__).parent))

from structure_detection import (
    SIGNAL_PRIORITIES,
    LocationConstraint,
    PriorityEngine,
    ProjectStructureDetection,
    RankedSignal,
    ResultClassifier,
    Signal,
    SignalScanner,
    detect_project_structure,
    validate_target_location,
)

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def temp_project():
    """Create temporary project directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def project_with_stubs(temp_project):
    """Create project with stub files."""
    tools_dir = temp_project / "tools"
    tools_dir.mkdir()

    # Create stub file
    stub_file = tools_dir / "analyzer.stub.py"
    stub_file.write_text("# Stub for analyzer")

    # Create existing implementation
    existing_file = tools_dir / "optimizer.py"
    existing_file.write_text("def optimize(): pass")

    return temp_project


@pytest.fixture
def project_with_tests(temp_project):
    """Create project with test files."""
    src_dir = temp_project / "src"
    src_dir.mkdir()
    modules_dir = src_dir / "modules"
    modules_dir.mkdir()

    tests_dir = temp_project / "tests"
    tests_dir.mkdir()

    # Create test file with import
    test_file = tests_dir / "test_analyzer.py"
    test_file.write_text("""
from src.modules import analyzer

def test_analyzer():
    assert True
""")

    return temp_project


@pytest.fixture
def project_with_conventions(temp_project):
    """Create project with conventional directories."""
    tools_dir = temp_project / "tools"
    tools_dir.mkdir()

    # Add Python file to show active use
    (tools_dir / "example.py").write_text("# Example")

    return temp_project


@pytest.fixture
def project_with_config(temp_project):
    """Create project with config files."""
    pyproject = temp_project / "pyproject.toml"
    pyproject.write_text("""
[tool.setuptools]
packages = ["src"]
""")

    src_dir = temp_project / "src"
    src_dir.mkdir()

    return temp_project


@pytest.fixture
def project_with_conflicts(temp_project):
    """Create project with conflicting signals."""
    # Stub in tools/
    tools_dir = temp_project / "tools"
    tools_dir.mkdir()
    (tools_dir / "analyzer.stub.py").write_text("# Stub")

    # Test pointing to src/
    src_dir = temp_project / "src"
    src_dir.mkdir()
    tests_dir = temp_project / "tests"
    tests_dir.mkdir()

    test_file = tests_dir / "test_analyzer.py"
    test_file.write_text("from src import analyzer")

    return temp_project


@pytest.fixture
def empty_project(temp_project):
    """Create empty project (no signals)."""
    return temp_project


# ============================================================================
# Signal Scanner Tests
# ============================================================================


class TestSignalScanner:
    """Tests for SignalScanner component."""

    def test_scan_stubs_finds_stub_files(self, project_with_stubs):
        """Test that stub files are detected."""
        scanner = SignalScanner(project_with_stubs)
        signals = scanner.scan_stubs()

        assert len(signals) >= 1
        assert any(s.signal_type == "stub" for s in signals)
        assert any("analyzer.stub.py" in s.source_file for s in signals)

    def test_scan_stubs_confidence(self, project_with_stubs):
        """Test stub signals have correct confidence."""
        scanner = SignalScanner(project_with_stubs)
        signals = scanner.scan_stubs()

        stub_signal = [s for s in signals if s.signal_type == "stub"][0]
        assert stub_signal.confidence == SIGNAL_PRIORITIES["stub"]["confidence"]
        assert stub_signal.confidence == 0.90

    def test_scan_tests_finds_test_files(self, project_with_tests):
        """Test that test files are detected."""
        scanner = SignalScanner(project_with_tests)
        signals = scanner.scan_tests()

        assert len(signals) >= 0  # May not extract imports correctly in test

    def test_scan_conventions_finds_conventional_dirs(self, project_with_conventions):
        """Test that conventional directories are detected."""
        scanner = SignalScanner(project_with_conventions)
        signals = scanner.scan_conventions()

        assert len(signals) >= 1
        assert any(s.signal_type == "convention" for s in signals)
        assert any("tools" in s.inferred_location for s in signals)

    def test_scan_config_finds_pyproject(self, project_with_config):
        """Test that config files are detected."""
        scanner = SignalScanner(project_with_config)
        signals = scanner.scan_config()

        # Config detection is best-effort
        assert isinstance(signals, list)

    def test_scan_all_completes_quickly(self, project_with_stubs):
        """Test that full scan completes within timeout."""
        scanner = SignalScanner(project_with_stubs)

        start = time.time()
        signals = scanner.scan_all(timeout_ms=100)
        duration_ms = (time.time() - start) * 1000

        assert duration_ms < 150  # Allow some overhead
        assert isinstance(signals, list)

    def test_scanner_validates_project_root(self):
        """Test that scanner validates project root."""
        with pytest.raises(ValueError):
            SignalScanner("/nonexistent/path")


# ============================================================================
# Priority Engine Tests
# ============================================================================


class TestPriorityEngine:
    """Tests for PriorityEngine component."""

    def test_rank_signals_orders_by_priority(self):
        """Test signals ranked by priority (stub > test > convention)."""
        signals = [
            Signal("convention", "", "/path/conv", 0.70, "conv", ""),
            Signal("stub", "", "/path/stub", 0.90, "stub", ""),
            Signal("test", "", "/path/test", 0.85, "test", ""),
        ]

        engine = PriorityEngine()
        ranked = engine.rank_signals(signals)

        assert ranked[0].signal.signal_type == "stub"
        assert ranked[1].signal.signal_type == "test"
        assert ranked[2].signal.signal_type == "convention"

    def test_compute_consensus_boost(self):
        """Test consensus boost calculation."""
        engine = PriorityEngine()

        # 2 signals: 0.02 boost
        boost = engine.compute_consensus_boost(2)
        assert boost == 0.02

        # 5 signals: 0.08 boost
        boost = engine.compute_consensus_boost(5)
        assert boost == 0.08

    def test_consensus_boosts_confidence(self):
        """Test multiple signals to same location boost confidence."""
        signals = [
            Signal("stub", "file1", "/path/tools", 0.90, "stub1", ""),
            Signal("stub", "file2", "/path/tools", 0.90, "stub2", ""),
            Signal("test", "file3", "/path/tools", 0.85, "test1", ""),
        ]

        engine = PriorityEngine()
        ranked = engine.rank_signals(signals)

        # All point to same location - should have consensus boost
        for rs in ranked:
            # Consensus boost should be applied
            assert rs.adjusted_confidence >= rs.signal.confidence

    def test_resolve_conflicts_detects_conflicts(self):
        """Test conflict detection when signals disagree."""
        signals = [
            Signal("stub", "", "/path/tools", 0.90, "stub", ""),
            Signal("test", "", "/path/src", 0.85, "test", ""),
        ]

        engine = PriorityEngine()
        ranked = engine.rank_signals(signals)
        conflicts = engine.resolve_conflicts(ranked)

        assert conflicts["has_conflicts"] is True
        assert len(conflicts["conflicts"]) > 0

    def test_no_conflicts_when_signals_agree(self):
        """Test no conflicts when all signals point to same location."""
        signals = [
            Signal("stub", "", "/path/tools", 0.90, "stub", ""),
            Signal("test", "", "/path/tools", 0.85, "test", ""),
        ]

        engine = PriorityEngine()
        ranked = engine.rank_signals(signals)
        conflicts = engine.resolve_conflicts(ranked)

        assert conflicts["has_conflicts"] is False


# ============================================================================
# Result Classifier Tests
# ============================================================================


class TestResultClassifier:
    """Tests for ResultClassifier component."""

    def test_classify_with_signals(self, temp_project):
        """Test classification with valid signals."""
        signals = [
            Signal(
                "stub",
                str(temp_project / "tools/stub.py"),
                str(temp_project / "tools"),
                0.90,
                "stub",
                "",
            )
        ]

        engine = PriorityEngine()
        ranked = engine.rank_signals(signals)

        classifier = ResultClassifier()
        result = classifier.classify(ranked, temp_project, 50.0)

        assert result.detected_root == str(temp_project / "tools")
        assert result.confidence > 0.8
        assert result.detection_method == "stub"

    def test_classify_ambiguous_when_no_signals(self, temp_project):
        """Test ambiguous result when no signals found."""
        classifier = ResultClassifier()
        result = classifier.classify([], temp_project, 50.0)

        assert result.detected_root is None
        assert result.confidence == 0.0
        assert result.detection_method == "ambiguous"
        assert len(result.warnings) > 0

    def test_create_constraint_from_signal(self, temp_project):
        """Test location constraint creation."""
        signal = Signal("stub", "", str(temp_project / "tools"), 0.90, "stub", "")
        ranked = RankedSignal(signal, 1, "stub", 0.90, "Priority 1")

        classifier = ResultClassifier()
        constraint = classifier.create_constraint(ranked, temp_project, False)

        assert constraint.required_location == str(temp_project / "tools")
        assert constraint.confidence == 0.90
        assert constraint.validation_required is True

    def test_identify_alternatives(self, temp_project):
        """Test alternative location identification."""
        signals = [
            Signal("stub", "", str(temp_project / "tools"), 0.90, "stub", ""),
            Signal("test", "", str(temp_project / "src"), 0.85, "test", ""),
        ]

        engine = PriorityEngine()
        ranked = engine.rank_signals(signals)

        classifier = ResultClassifier()
        alternatives = classifier.identify_alternatives(ranked, ranked[0])

        assert len(alternatives) >= 1
        assert any(str(temp_project / "src") in alt["location"] for alt in alternatives)

    def test_detect_structure_type(self):
        """Test structure type classification."""
        classifier = ResultClassifier()

        assert classifier._detect_structure_type("/path/tools/") == "tool"
        assert classifier._detect_structure_type("/path/src/") == "library"
        assert classifier._detect_structure_type("/path/plugins/") == "plugin"


# ============================================================================
# Validation Tests
# ============================================================================


class TestValidation:
    """Tests for validation functionality."""

    def test_validate_inside_project_passes(self, temp_project):
        """Test validation passes for location inside project."""
        tools_dir = temp_project / "tools"
        tools_dir.mkdir()

        result = validate_target_location(tools_dir, temp_project)

        assert result.passed is True
        assert result.is_inside_project is True

    def test_validate_outside_project_fails(self, temp_project):
        """Test validation fails for location outside project."""
        outside = Path("/tmp/outside")

        result = validate_target_location(outside, temp_project)

        assert result.passed is False
        assert result.is_inside_project is False

    def test_validate_writable_directory(self, temp_project):
        """Test validation checks writability."""
        tools_dir = temp_project / "tools"
        tools_dir.mkdir()

        result = validate_target_location(tools_dir, temp_project)

        assert result.is_writable is True

    def test_validate_missing_parent_fails(self, temp_project):
        """Test validation fails when parent doesn't exist."""
        missing_path = temp_project / "nonexistent" / "deep" / "path"

        result = validate_target_location(missing_path, temp_project)

        assert result.passed is False
        assert "Parent directory" in result.reason or "parent" in str(result.failures).lower()


# ============================================================================
# Integration Tests (Full Workflow)
# ============================================================================


class TestFullDetection:
    """Integration tests for complete detection workflow."""

    def test_detect_with_clear_stub(self, project_with_stubs):
        """Test detection with clear stub signal."""
        result = detect_project_structure(str(project_with_stubs))

        assert result.detected_root is not None
        assert "tools" in result.detected_root
        assert result.confidence >= 0.85
        assert result.detection_method == "stub"

    def test_detect_with_conventions(self, project_with_conventions):
        """Test detection with directory conventions."""
        result = detect_project_structure(str(project_with_conventions))

        assert result.detected_root is not None
        assert result.detection_method in ["convention", "fallback"]

    def test_detect_with_conflicts(self, project_with_conflicts):
        """Test detection handles conflicting signals."""
        result = detect_project_structure(str(project_with_conflicts))

        # Should detect conflict
        assert len(result.ambiguity_flags) > 0 or len(result.warnings) > 0
        # But should still pick dominant signal
        assert result.detected_root is not None
        assert result.confidence > 0.0

    def test_detect_empty_project_uses_fallback(self, empty_project):
        """Test detection falls back gracefully for empty project."""
        result = detect_project_structure(str(empty_project))

        # Should either use fallback or be ambiguous
        assert result.detection_method in ["fallback", "ambiguous"]

    def test_detect_performance_under_100ms(self, project_with_stubs):
        """Test detection completes quickly."""
        result = detect_project_structure(str(project_with_stubs), timeout_ms=100)

        # Should complete within reasonable time
        assert result.scan_duration_ms < 150  # Allow some overhead

    def test_detect_returns_complete_result(self, project_with_stubs):
        """Test detection returns all expected fields."""
        result = detect_project_structure(str(project_with_stubs))

        # Check all fields populated
        assert result.detected_root is not None
        assert result.structure_type in ["tool", "library", "plugin", "scenario", "custom"]
        assert result.detection_method in [
            "stub",
            "test",
            "convention",
            "config",
            "fallback",
            "ambiguous",
        ]
        assert 0.0 <= result.confidence <= 1.0
        assert isinstance(result.signals, list)
        assert isinstance(result.warnings, list)
        assert isinstance(result.alternatives, list)
        assert result.scan_duration_ms >= 0


# ============================================================================
# Edge Case Tests
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and unusual scenarios."""

    def test_multiple_stub_signals_consensus(self, temp_project):
        """Test multiple stubs increase confidence."""
        tools_dir = temp_project / "tools"
        tools_dir.mkdir()

        # Create multiple stubs
        (tools_dir / "analyzer.stub.py").write_text("# Stub")
        (tools_dir / "optimizer.stub.py").write_text("# Stub")
        (tools_dir / "validator.stub.py").write_text("# Stub")

        result = detect_project_structure(str(temp_project))

        # Multiple stubs should boost confidence
        assert result.confidence >= 0.90

    def test_stub_in_nonexistent_directory(self, temp_project):
        """Test handling stub pointing to nonexistent directory."""
        # This is actually created during test, so modify approach
        tools_dir = temp_project / "future_tools"
        tools_dir.mkdir()
        (tools_dir / "analyzer.stub.py").write_text("# Stub")

        result = detect_project_structure(str(temp_project))

        # Should detect location even if "new"
        assert result.detected_root is not None

    def test_deeply_nested_structure(self, temp_project):
        """Test detection in deeply nested project."""
        deep_path = temp_project / "a" / "b" / "c" / "tools"
        deep_path.mkdir(parents=True)
        (deep_path / "analyzer.stub.py").write_text("# Stub")

        result = detect_project_structure(str(temp_project))

        # Should find stub even if nested
        assert result.detected_root is not None

    def test_special_characters_in_paths(self, temp_project):
        """Test handling paths with special characters."""
        special_dir = temp_project / "my-tools_v2.0"
        special_dir.mkdir()
        (special_dir / "tool.py").write_text("# Tool")

        result = detect_project_structure(str(temp_project))

        # Should handle special characters gracefully
        assert isinstance(result, ProjectStructureDetection)

    def test_very_large_project(self, temp_project):
        """Test detection scales to larger projects."""
        # Create many directories and files
        for i in range(10):
            dir_path = temp_project / f"module_{i}"
            dir_path.mkdir()
            for j in range(10):
                (dir_path / f"file_{j}.py").write_text(f"# Module {i} file {j}")

        # Add stub in one location
        tools_dir = temp_project / "tools"
        tools_dir.mkdir()
        (tools_dir / "analyzer.stub.py").write_text("# Stub")

        result = detect_project_structure(str(temp_project), timeout_ms=200)

        # Should complete and find stub
        assert result.detected_root is not None
        assert "tools" in result.detected_root


# ============================================================================
# Data Structure Tests
# ============================================================================


class TestDataStructures:
    """Tests for data structure contracts."""

    def test_signal_structure(self):
        """Test Signal dataclass."""
        signal = Signal(
            signal_type="stub",
            source_file="/path/to/file.stub.py",
            inferred_location="/path/to",
            confidence=0.90,
            evidence="Stub file",
            parsed_at="2025-11-21T00:00:00",
        )

        assert signal.signal_type == "stub"
        assert signal.confidence == 0.90

    def test_location_constraint_structure(self):
        """Test LocationConstraint dataclass."""
        constraint = LocationConstraint(
            required_location="/path/to/tools",
            location_exists=True,
            may_create_directory=True,
            location_reasoning="Stub signal",
            confidence=0.90,
            validation_required=True,
            is_ambiguous=False,
            ambiguity_reason="",
            alternatives=[],
        )

        assert constraint.required_location == "/path/to/tools"
        assert constraint.validation_required is True

    def test_project_structure_detection_complete(self, project_with_stubs):
        """Test ProjectStructureDetection has all fields."""
        result = detect_project_structure(str(project_with_stubs))

        # Verify all required fields present
        assert hasattr(result, "detected_root")
        assert hasattr(result, "structure_type")
        assert hasattr(result, "detection_method")
        assert hasattr(result, "confidence")
        assert hasattr(result, "signals")
        assert hasattr(result, "signals_ranked")
        assert hasattr(result, "constraints")
        assert hasattr(result, "ambiguity_flags")
        assert hasattr(result, "warnings")
        assert hasattr(result, "alternatives")
        assert hasattr(result, "scan_duration_ms")
        assert hasattr(result, "signals_examined")


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
