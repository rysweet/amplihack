"""
Test suite for check_point_in_time_docs.py

Tests the PointInTimeDocsDetector class that detects temporal references in docs.
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

# Add .claude/ci to path
ci_path = Path(__file__).resolve().parents[2] / ".claude" / "ci"
sys.path.insert(0, str(ci_path))

from check_point_in_time_docs import PointInTimeDocsDetector


class TestPointInTimeDocsDetector:
    """Test PointInTimeDocsDetector class."""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration for tests."""
        return {
            'point_in_time_indicators': [
                'Q1 2025',
                'Q2 2025',
                'Sprint',
                'Week of',
                'As of 20',
                'Current status:',
                'Today\'s',
                'This week\'s',
                'Last week\'s',
            ]
        }

    @pytest.fixture
    def temp_repo(self, tmp_path, mock_config):
        """Create a temporary repository with config."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        config_dir = repo_root / ".github"
        config_dir.mkdir()
        config_path = config_dir / "root-hygiene-config.yml"

        with open(config_path, 'w') as f:
            yaml.dump(mock_config, f)

        return repo_root, config_path

    def test_init_success(self, temp_repo):
        """Test successful initialization."""
        repo_root, config_path = temp_repo
        detector = PointInTimeDocsDetector(repo_root, config_path)

        assert detector.repo_root == repo_root
        assert detector.config_path == config_path
        assert detector.config is not None

    def test_load_config_missing_file(self, tmp_path):
        """Test loading config when file doesn't exist."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        config_path = repo_root / "missing.yml"

        with pytest.raises(SystemExit) as exc_info:
            PointInTimeDocsDetector(repo_root, config_path)

        assert exc_info.value.code == 1

    def test_is_root_file_true(self, temp_repo):
        """Test identifying root files."""
        repo_root, config_path = temp_repo
        detector = PointInTimeDocsDetector(repo_root, config_path)

        assert detector._is_root_file('README.md') is True
        assert detector._is_root_file('CHANGELOG.md') is True
        assert detector._is_root_file('STATUS.md') is True

    def test_is_root_file_false(self, temp_repo):
        """Test identifying non-root files."""
        repo_root, config_path = temp_repo
        detector = PointInTimeDocsDetector(repo_root, config_path)

        assert detector._is_root_file('docs/guide.md') is False
        assert detector._is_root_file('src/README.md') is False
        assert detector._is_root_file('.github/workflows/test.yml') is False

    def test_scan_file_for_temporal_refs_found(self, temp_repo):
        """Test scanning file with temporal references."""
        repo_root, config_path = temp_repo

        doc_file = repo_root / "STATUS.md"
        doc_file.write_text("""# Project Status

Current status: All systems operational

## Q1 2025 Goals
- Complete feature X
- Deploy to production

As of 2025-01-15, we have completed 80% of tasks.
""")

        detector = PointInTimeDocsDetector(repo_root, config_path)
        matches = detector._scan_file_for_temporal_refs(doc_file)

        assert len(matches) > 0
        # Should find "Current status:", "Q1 2025", and "As of 20"
        indicators = [m[2] for m in matches]
        assert 'Current status:' in indicators
        assert 'Q1 2025' in indicators
        assert 'As of 20' in indicators

    def test_scan_file_for_temporal_refs_not_found(self, temp_repo):
        """Test scanning file without temporal references."""
        repo_root, config_path = temp_repo

        doc_file = repo_root / "README.md"
        doc_file.write_text("""# Project Name

A timeless description of the project.

## Features
- Feature A
- Feature B
""")

        detector = PointInTimeDocsDetector(repo_root, config_path)
        matches = detector._scan_file_for_temporal_refs(doc_file)

        assert len(matches) == 0

    def test_scan_file_for_temporal_refs_case_insensitive(self, temp_repo):
        """Test case-insensitive temporal reference detection."""
        repo_root, config_path = temp_repo

        doc_file = repo_root / "STATUS.md"
        doc_file.write_text("""# Status

CURRENT STATUS: Working on features
current status: All good
Current Status: Everything is fine
""")

        detector = PointInTimeDocsDetector(repo_root, config_path)
        matches = detector._scan_file_for_temporal_refs(doc_file)

        # Should find all three variations
        assert len(matches) == 3

    def test_scan_file_for_temporal_refs_line_numbers(self, temp_repo):
        """Test correct line number reporting."""
        repo_root, config_path = temp_repo

        doc_file = repo_root / "STATUS.md"
        doc_file.write_text("""Line 1: Normal text
Line 2: Current status: Active
Line 3: More text
Line 4: Q1 2025 goals
""")

        detector = PointInTimeDocsDetector(repo_root, config_path)
        matches = detector._scan_file_for_temporal_refs(doc_file)

        line_numbers = [m[0] for m in matches]
        assert 2 in line_numbers
        assert 4 in line_numbers

    def test_scan_file_missing_file(self, temp_repo):
        """Test scanning non-existent file."""
        repo_root, config_path = temp_repo

        doc_file = repo_root / "missing.md"

        detector = PointInTimeDocsDetector(repo_root, config_path)
        matches = detector._scan_file_for_temporal_refs(doc_file)

        assert len(matches) == 0

    def test_scan_file_unicode_error(self, temp_repo):
        """Test handling of files with encoding issues."""
        repo_root, config_path = temp_repo

        doc_file = repo_root / "bad.md"
        # Write binary data that's not valid UTF-8
        doc_file.write_bytes(b'\xff\xfe invalid utf-8')

        detector = PointInTimeDocsDetector(repo_root, config_path)
        matches = detector._scan_file_for_temporal_refs(doc_file)

        # Should handle gracefully
        assert matches == []

    def test_scan_file_one_match_per_line(self, temp_repo):
        """Test only first match per line is reported."""
        repo_root, config_path = temp_repo

        doc_file = repo_root / "STATUS.md"
        doc_file.write_text("Current status: Q1 2025 Sprint Week of\n")

        detector = PointInTimeDocsDetector(repo_root, config_path)
        matches = detector._scan_file_for_temporal_refs(doc_file)

        # Should only report one match per line
        assert len(matches) == 1

    @patch('subprocess.run')
    def test_get_changed_docs_main_branch(self, mock_run, temp_repo):
        """Test getting changed docs from main branch."""
        repo_root, config_path = temp_repo

        mock_run.side_effect = [
            Mock(stdout='abc123\n', returncode=0),
            Mock(stdout='README.md\ndocs/guide.md\nsrc/main.py\n', returncode=0),
        ]

        detector = PointInTimeDocsDetector(repo_root, config_path)
        docs = detector._get_changed_docs()

        assert 'README.md' in docs
        assert 'docs/guide.md' in docs
        assert 'src/main.py' not in docs  # Not a .md file

    @patch('subprocess.run')
    def test_get_changed_docs_master_fallback(self, mock_run, temp_repo):
        """Test fallback to master branch."""
        repo_root, config_path = temp_repo

        mock_run.side_effect = [
            subprocess.CalledProcessError(1, 'git'),
            Mock(stdout='abc123\n', returncode=0),
            Mock(stdout='README.md\n', returncode=0),
        ]

        detector = PointInTimeDocsDetector(repo_root, config_path)
        docs = detector._get_changed_docs()

        assert docs == ['README.md']

    @patch('subprocess.run')
    def test_get_changed_docs_error(self, mock_run, temp_repo):
        """Test error handling when git fails."""
        repo_root, config_path = temp_repo

        mock_run.side_effect = subprocess.CalledProcessError(1, 'git')

        detector = PointInTimeDocsDetector(repo_root, config_path)
        docs = detector._get_changed_docs()

        assert docs == []

    @patch('subprocess.run')
    def test_get_changed_docs_empty(self, mock_run, temp_repo):
        """Test getting changed docs with no changes."""
        repo_root, config_path = temp_repo

        mock_run.side_effect = [
            Mock(stdout='abc123\n', returncode=0),
            Mock(stdout='', returncode=0),
        ]

        detector = PointInTimeDocsDetector(repo_root, config_path)
        docs = detector._get_changed_docs()

        assert docs == []

    @patch('subprocess.run')
    def test_analyze_no_changes(self, mock_run, temp_repo):
        """Test analysis with no changed docs."""
        repo_root, config_path = temp_repo

        mock_run.side_effect = [
            Mock(stdout='abc123\n', returncode=0),
            Mock(stdout='', returncode=0),
        ]

        detector = PointInTimeDocsDetector(repo_root, config_path)
        has_issues, warnings = detector.analyze()

        assert has_issues is False
        assert len(warnings) == 0

    @patch('subprocess.run')
    def test_analyze_no_temporal_refs(self, mock_run, temp_repo):
        """Test analysis with clean documentation."""
        repo_root, config_path = temp_repo

        doc_file = repo_root / "README.md"
        doc_file.write_text("# Clean documentation\n\nNo temporal references here.")

        mock_run.side_effect = [
            Mock(stdout='abc123\n', returncode=0),
            Mock(stdout='README.md\n', returncode=0),
        ]

        detector = PointInTimeDocsDetector(repo_root, config_path)
        has_issues, warnings = detector.analyze()

        assert has_issues is False
        assert len(warnings) == 0

    @patch('subprocess.run')
    def test_analyze_temporal_refs_in_root(self, mock_run, temp_repo):
        """Test analysis with temporal refs in root file."""
        repo_root, config_path = temp_repo

        doc_file = repo_root / "STATUS.md"
        doc_file.write_text("Current status: Working on Q1 2025 goals")

        mock_run.side_effect = [
            Mock(stdout='abc123\n', returncode=0),
            Mock(stdout='STATUS.md\n', returncode=0),
        ]

        detector = PointInTimeDocsDetector(repo_root, config_path)
        has_issues, warnings = detector.analyze()

        assert has_issues is True
        assert len(warnings) == 1
        assert warnings[0]['file'] == 'STATUS.md'
        assert warnings[0]['is_root'] is True
        assert len(warnings[0]['matches']) > 0

    @patch('subprocess.run')
    def test_analyze_temporal_refs_in_subdir(self, mock_run, temp_repo):
        """Test analysis with temporal refs in subdirectory."""
        repo_root, config_path = temp_repo

        docs_dir = repo_root / "docs"
        docs_dir.mkdir()
        doc_file = docs_dir / "status.md"
        doc_file.write_text("Sprint planning for Q1 2025")

        mock_run.side_effect = [
            Mock(stdout='abc123\n', returncode=0),
            Mock(stdout='docs/status.md\n', returncode=0),
        ]

        detector = PointInTimeDocsDetector(repo_root, config_path)
        has_issues, warnings = detector.analyze()

        assert has_issues is True
        assert len(warnings) == 1
        assert warnings[0]['file'] == 'docs/status.md'
        assert warnings[0]['is_root'] is False

    @patch('subprocess.run')
    def test_analyze_multiple_files(self, mock_run, temp_repo):
        """Test analysis with multiple files containing temporal refs."""
        repo_root, config_path = temp_repo

        # Root file
        root_doc = repo_root / "STATUS.md"
        root_doc.write_text("Current status: Active")

        # Subdirectory file
        docs_dir = repo_root / "docs"
        docs_dir.mkdir()
        sub_doc = docs_dir / "planning.md"
        sub_doc.write_text("Q1 2025 roadmap")

        mock_run.side_effect = [
            Mock(stdout='abc123\n', returncode=0),
            Mock(stdout='STATUS.md\ndocs/planning.md\n', returncode=0),
        ]

        detector = PointInTimeDocsDetector(repo_root, config_path)
        has_issues, warnings = detector.analyze()

        assert has_issues is True
        assert len(warnings) == 2

    @patch('subprocess.run')
    def test_generate_report_pass(self, mock_run, temp_repo):
        """Test report generation for passing check."""
        repo_root, config_path = temp_repo

        doc_file = repo_root / "README.md"
        doc_file.write_text("# Clean docs")

        mock_run.side_effect = [
            Mock(stdout='abc123\n', returncode=0),
            Mock(stdout='README.md\n', returncode=0),
        ]

        detector = PointInTimeDocsDetector(repo_root, config_path)
        report = detector.generate_report()

        assert "PASSED" in report
        assert "No temporal references" in report

    @patch('subprocess.run')
    def test_generate_report_warnings_root_file(self, mock_run, temp_repo):
        """Test report generation with root file warnings."""
        repo_root, config_path = temp_repo

        doc_file = repo_root / "STATUS.md"
        doc_file.write_text("Current status: Q1 2025")

        mock_run.side_effect = [
            Mock(stdout='abc123\n', returncode=0),
            Mock(stdout='STATUS.md\n', returncode=0),
        ]

        detector = PointInTimeDocsDetector(repo_root, config_path)
        report = detector.generate_report()

        assert "WARNINGS" in report
        assert "STATUS.md" in report
        assert "ROOT" in report
        assert "Should not be committed" in report

    @patch('subprocess.run')
    def test_generate_report_warnings_subdir_file(self, mock_run, temp_repo):
        """Test report generation with subdirectory warnings."""
        repo_root, config_path = temp_repo

        docs_dir = repo_root / "docs"
        docs_dir.mkdir()
        doc_file = docs_dir / "status.md"
        doc_file.write_text("Sprint goals")

        mock_run.side_effect = [
            Mock(stdout='abc123\n', returncode=0),
            Mock(stdout='docs/status.md\n', returncode=0),
        ]

        detector = PointInTimeDocsDetector(repo_root, config_path)
        report = detector.generate_report()

        assert "WARNINGS" in report
        assert "docs/status.md" in report
        # Should not have ROOT marker
        assert "ROOT" not in report or report.index("docs/status.md") > report.index("ROOT")

    @patch('subprocess.run')
    def test_generate_report_multiple_matches(self, mock_run, temp_repo):
        """Test report with multiple temporal references."""
        repo_root, config_path = temp_repo

        doc_file = repo_root / "STATUS.md"
        doc_file.write_text("""Line 1: Current status
Line 2: Q1 2025
Line 3: Sprint 1
Line 4: Week of Jan 15
Line 5: As of 2025
""")

        mock_run.side_effect = [
            Mock(stdout='abc123\n', returncode=0),
            Mock(stdout='STATUS.md\n', returncode=0),
        ]

        detector = PointInTimeDocsDetector(repo_root, config_path)
        report = detector.generate_report()

        assert "WARNINGS" in report
        assert "temporal reference(s)" in report
        # Should show first 3 matches
        assert "Line 1" in report or "Line 2" in report

    @patch('subprocess.run')
    def test_generate_report_many_matches_truncated(self, mock_run, temp_repo):
        """Test report truncates when many matches exist."""
        repo_root, config_path = temp_repo

        doc_file = repo_root / "STATUS.md"
        lines = [f"Line {i}: Current status: Active\n" for i in range(1, 11)]
        doc_file.write_text("".join(lines))

        mock_run.side_effect = [
            Mock(stdout='abc123\n', returncode=0),
            Mock(stdout='STATUS.md\n', returncode=0),
        ]

        detector = PointInTimeDocsDetector(repo_root, config_path)
        report = detector.generate_report()

        assert "WARNINGS" in report
        # Should show "... and N more"
        assert "more" in report.lower()

    @patch('subprocess.run')
    def test_generate_report_shows_indicators(self, mock_run, temp_repo):
        """Test report includes list of temporal indicators."""
        repo_root, config_path = temp_repo

        doc_file = repo_root / "STATUS.md"
        doc_file.write_text("Current status: Active")

        mock_run.side_effect = [
            Mock(stdout='abc123\n', returncode=0),
            Mock(stdout='STATUS.md\n', returncode=0),
        ]

        detector = PointInTimeDocsDetector(repo_root, config_path)
        report = detector.generate_report()

        assert "Temporal indicators checked:" in report
        assert "Q1 2025" in report or "Sprint" in report
