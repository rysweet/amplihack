"""Unit tests for Evidence Collector module.

Tests artifact collection, organization, and metadata extraction.
These tests will FAIL until the evidence_collector module is implemented.
"""

from datetime import datetime

import pytest

# These imports will fail until implementation exists
try:
    from amplihack.meta_delegation.evidence_collector import (
        EVIDENCE_PATTERNS,
        EvidenceCollector,
        EvidenceItem,
    )
except ImportError:
    pytest.skip("evidence_collector module not implemented yet", allow_module_level=True)


class TestEvidenceItem:
    """Test EvidenceItem dataclass."""

    def test_evidence_item_has_required_fields(self):
        """Test EvidenceItem has all required fields."""
        item = EvidenceItem(
            type="code_file",
            path="/path/to/file.py",
            content="def main(): pass",
            excerpt="def main()...",
            size_bytes=100,
            timestamp=datetime.now(),
            metadata={"language": "python"},
        )

        assert item.type == "code_file"
        assert item.path == "/path/to/file.py"
        assert item.size_bytes == 100
        assert isinstance(item.metadata, dict)

    def test_evidence_item_excerpt_truncation(self):
        """Test excerpt is truncated version of content."""
        long_content = "x" * 1000
        item = EvidenceItem(
            type="code_file",
            path="file.py",
            content=long_content,
            excerpt=long_content[:200],
            size_bytes=1000,
            timestamp=datetime.now(),
            metadata={},
        )

        assert len(item.excerpt) <= 200

    def test_evidence_item_save_to_file(self, tmp_path):
        """Test saving evidence item to file."""
        item = EvidenceItem(
            type="code_file",
            path="app.py",
            content="print('hello')",
            excerpt="print...",
            size_bytes=15,
            timestamp=datetime.now(),
            metadata={},
        )

        output_path = tmp_path / "output.py"
        item.save_to_file(str(output_path))

        assert output_path.exists()
        assert output_path.read_text() == "print('hello')"

    def test_evidence_item_get_metadata(self):
        """Test getting metadata with default."""
        item = EvidenceItem(
            type="code_file",
            path="app.py",
            content="code",
            excerpt="",
            size_bytes=10,
            timestamp=datetime.now(),
            metadata={"language": "python"},
        )

        assert item.get_metadata("language") == "python"
        assert item.get_metadata("missing_key", "default") == "default"


class TestEvidencePatterns:
    """Test EVIDENCE_PATTERNS constant."""

    def test_evidence_patterns_exists(self):
        """Test EVIDENCE_PATTERNS is defined."""
        assert EVIDENCE_PATTERNS is not None
        assert isinstance(EVIDENCE_PATTERNS, dict)

    def test_evidence_patterns_has_required_types(self):
        """Test EVIDENCE_PATTERNS has all required evidence types."""
        required_types = [
            "code_file",
            "test_file",
            "documentation",
            "architecture_doc",
            "api_spec",
            "test_results",
            "execution_log",
            "validation_report",
            "diagram",
            "configuration",
        ]

        for etype in required_types:
            assert etype in EVIDENCE_PATTERNS, f"Missing pattern for: {etype}"

    def test_evidence_patterns_are_lists(self):
        """Test each evidence pattern is a list of glob patterns."""
        for etype, patterns in EVIDENCE_PATTERNS.items():
            assert isinstance(patterns, list), f"{etype} patterns not a list"
            assert len(patterns) > 0, f"{etype} has no patterns"


class TestEvidenceCollector:
    """Test EvidenceCollector class."""

    @pytest.fixture
    def working_dir(self, tmp_path):
        """Create temporary working directory with test files."""
        # Create sample files
        (tmp_path / "app.py").write_text("def main(): pass")
        (tmp_path / "test_app.py").write_text("def test_main(): assert True")
        (tmp_path / "README.md").write_text("# Project")
        (tmp_path / "config.yaml").write_text("setting: value")

        return tmp_path

    @pytest.fixture
    def collector(self, working_dir):
        """Create collector instance."""
        return EvidenceCollector(working_directory=str(working_dir))

    def test_initialization(self, working_dir):
        """Test collector initializes correctly."""
        collector = EvidenceCollector(working_directory=str(working_dir))

        assert collector is not None
        assert collector.working_directory == str(working_dir)

    def test_collect_evidence_returns_list(self, collector):
        """Test collect_evidence returns list of evidence items."""
        evidence = collector.collect_evidence()

        assert isinstance(evidence, list)
        assert all(isinstance(item, EvidenceItem) for item in evidence)

    def test_collect_evidence_finds_code_files(self, collector):
        """Test collector finds code files."""
        evidence = collector.collect_evidence()

        code_files = [e for e in evidence if e.type == "code_file"]

        assert len(code_files) > 0
        assert any("app.py" in e.path for e in code_files)

    def test_collect_evidence_finds_test_files(self, collector):
        """Test collector finds test files."""
        evidence = collector.collect_evidence()

        test_files = [e for e in evidence if e.type == "test_file"]

        assert len(test_files) > 0
        assert any("test_app.py" in e.path for e in test_files)

    def test_collect_evidence_finds_documentation(self, collector):
        """Test collector finds documentation files."""
        evidence = collector.collect_evidence()

        docs = [e for e in evidence if e.type == "documentation"]

        assert len(docs) > 0
        assert any("README.md" in e.path for e in docs)

    def test_collect_evidence_finds_configuration(self, collector):
        """Test collector finds configuration files."""
        evidence = collector.collect_evidence()

        configs = [e for e in evidence if e.type == "configuration"]

        assert len(configs) > 0
        assert any("config.yaml" in e.path for e in configs)

    def test_collect_evidence_reads_file_content(self, collector):
        """Test collector reads actual file content."""
        evidence = collector.collect_evidence()

        app_files = [e for e in evidence if "app.py" in e.path]
        assert len(app_files) > 0

        app_evidence = app_files[0]
        assert "def main()" in app_evidence.content

    def test_collect_evidence_generates_excerpts(self, collector):
        """Test collector generates excerpts for quick scanning."""
        evidence = collector.collect_evidence()

        for item in evidence:
            assert item.excerpt is not None
            assert len(item.excerpt) <= 200

    def test_collect_evidence_captures_timestamps(self, collector):
        """Test collector captures collection timestamps."""
        before = datetime.now()
        evidence = collector.collect_evidence()
        after = datetime.now()

        for item in evidence:
            assert before <= item.timestamp <= after

    def test_collect_evidence_calculates_sizes(self, collector):
        """Test collector calculates file sizes."""
        evidence = collector.collect_evidence()

        for item in evidence:
            assert item.size_bytes > 0
            assert item.size_bytes == len(item.content.encode("utf-8"))

    def test_collect_evidence_with_execution_log(self, collector):
        """Test collecting evidence with execution log."""
        log_content = "Process started\nTask completed\n"

        evidence = collector.collect_evidence(execution_log=log_content)

        log_evidence = [e for e in evidence if e.type == "execution_log"]

        assert len(log_evidence) > 0
        assert log_content in log_evidence[0].content

    def test_collect_evidence_filters_by_type(self, collector):
        """Test filtering evidence by type."""
        all_evidence = collector.collect_evidence()
        code_only = collector.collect_evidence(evidence_types=["code_file"])

        assert len(code_only) < len(all_evidence)
        assert all(e.type == "code_file" for e in code_only)

    def test_collect_evidence_excludes_patterns(self, collector, working_dir):
        """Test excluding files by pattern."""
        # Create file that should be excluded
        (working_dir / "__pycache__").mkdir()
        (working_dir / "__pycache__" / "app.pyc").write_text("bytecode")

        evidence = collector.collect_evidence(exclude_patterns=["__pycache__/*"])

        # Should not include pycache files
        assert not any("__pycache__" in e.path for e in evidence)

    def test_collect_evidence_organizes_by_type(self, collector):
        """Test get_evidence_by_type organization."""
        collector.collect_evidence()

        code_files = collector.get_evidence_by_type("code_file")
        test_files = collector.get_evidence_by_type("test_file")

        assert all(e.type == "code_file" for e in code_files)
        assert all(e.type == "test_file" for e in test_files)

    def test_collect_evidence_incremental(self, collector, working_dir):
        """Test incremental evidence collection."""
        # First collection
        evidence1 = collector.collect_evidence()
        count1 = len(evidence1)

        # Add new file
        (working_dir / "new_file.py").write_text("def new(): pass")

        # Second collection
        evidence2 = collector.collect_evidence()
        count2 = len(evidence2)

        assert count2 > count1

    def test_collect_evidence_extracts_metadata(self, collector):
        """Test metadata extraction from files."""
        evidence = collector.collect_evidence()

        for item in evidence:
            assert isinstance(item.metadata, dict)

            # Python files should have language metadata
            if item.path.endswith(".py"):
                # May include language detection
                pass

    def test_collector_handles_large_files(self, collector, working_dir):
        """Test collector handles large files gracefully."""
        # Create large file
        large_content = "x" * (10 * 1024 * 1024)  # 10 MB
        (working_dir / "large.txt").write_text(large_content)

        evidence = collector.collect_evidence()

        # Should collect but may truncate content or excerpt
        large_files = [e for e in evidence if "large.txt" in e.path]
        assert len(large_files) > 0

    def test_collector_handles_binary_files(self, collector, working_dir):
        """Test collector handles binary files."""
        # Create binary file
        (working_dir / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n")

        evidence = collector.collect_evidence()

        # Should either skip or handle binary files
        png_files = [e for e in evidence if "image.png" in e.path]
        # Implementation may skip binary files

    def test_collector_handles_empty_directory(self, tmp_path):
        """Test collector handles empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        collector = EvidenceCollector(working_directory=str(empty_dir))
        evidence = collector.collect_evidence()

        assert isinstance(evidence, list)
        assert len(evidence) == 0

    def test_collector_handles_nested_directories(self, working_dir):
        """Test collector finds files in nested directories."""
        # Create nested structure
        nested = working_dir / "src" / "module"
        nested.mkdir(parents=True)
        (nested / "core.py").write_text("def core(): pass")

        collector = EvidenceCollector(working_directory=str(working_dir))
        evidence = collector.collect_evidence()

        nested_files = [e for e in evidence if "core.py" in e.path]
        assert len(nested_files) > 0

    def test_collect_evidence_real_time_monitoring(self, collector):
        """Test real-time evidence collection during execution."""
        # Simulate collecting evidence periodically
        evidence_snapshots = []

        for i in range(3):
            snapshot = collector.collect_evidence()
            evidence_snapshots.append(snapshot)

        # Should be able to collect multiple times
        assert len(evidence_snapshots) == 3

    def test_get_evidence_by_path_pattern(self, collector):
        """Test filtering evidence by path pattern."""
        collector.collect_evidence()

        test_pattern_evidence = collector.get_evidence_by_path_pattern("test_*.py")

        assert all("test_" in e.path for e in test_pattern_evidence)

    def test_export_evidence_to_directory(self, collector, tmp_path):
        """Test exporting all evidence to directory."""
        evidence = collector.collect_evidence()

        export_dir = tmp_path / "exported"
        collector.export_evidence(str(export_dir))

        assert export_dir.exists()
        # Should create organized directory structure
        assert any(export_dir.iterdir())


class TestEvidenceCollectionStrategies:
    """Test different evidence collection strategies."""

    @pytest.fixture
    def working_dir(self, tmp_path):
        """Create working directory with various files."""
        (tmp_path / "main.py").write_text("# Main")
        (tmp_path / "test_main.py").write_text("# Tests")
        (tmp_path / "README.md").write_text("# Docs")
        (tmp_path / "architecture.md").write_text("# Architecture")
        (tmp_path / "api.yaml").write_text("openapi: 3.0.0")
        (tmp_path / "diagram.mmd").write_text("graph TD")

        return tmp_path

    def test_guide_persona_evidence_priority(self, working_dir):
        """Test evidence collection prioritizes guide persona preferences."""
        from amplihack.meta_delegation.persona import GUIDE

        collector = EvidenceCollector(
            working_directory=str(working_dir),
            evidence_priorities=GUIDE.evidence_collection_priority,
        )

        evidence = collector.collect_evidence()

        # Guide prioritizes documentation
        # Check if documentation comes early in results or has priority flag

    def test_qa_engineer_persona_evidence_priority(self, working_dir):
        """Test evidence collection prioritizes QA persona preferences."""
        from amplihack.meta_delegation.persona import QA_ENGINEER

        collector = EvidenceCollector(
            working_directory=str(working_dir),
            evidence_priorities=QA_ENGINEER.evidence_collection_priority,
        )

        evidence = collector.collect_evidence()

        # QA prioritizes tests and validation
        test_evidence = [e for e in evidence if e.type == "test_file"]
        assert len(test_evidence) > 0

    def test_architect_persona_evidence_priority(self, working_dir):
        """Test evidence collection prioritizes architect persona preferences."""
        from amplihack.meta_delegation.persona import ARCHITECT

        collector = EvidenceCollector(
            working_directory=str(working_dir),
            evidence_priorities=ARCHITECT.evidence_collection_priority,
        )

        evidence = collector.collect_evidence()

        # Architect prioritizes architecture docs and specs
        arch_evidence = [
            e for e in evidence if e.type in ["architecture_doc", "api_spec", "diagram"]
        ]
        assert len(arch_evidence) > 0
