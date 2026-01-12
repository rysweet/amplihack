"""Tests for case sensitivity fix strategy.

Tests verify:
- Single case match detection (95% confidence)
- Multiple case matches (low confidence)
- Case-insensitive file matching
- Preservation of path structure
"""


class TestCaseSensitivityStrategy:
    """Tests for CaseSensitivityFix strategy."""

    def test_single_case_match_high_confidence(self, temp_repo):
        """Single case-insensitive match should return 95% confidence.

        Scenario:
            - Link points to "./GUIDE.MD"
            - File exists as "./guide.md"
            - Only one case-variant exists
        """
        from link_fixer import CaseSensitivityFix

        # Create the actual file with correct case
        docs_dir = temp_repo / "docs"
        docs_dir.mkdir(exist_ok=True)
        guide_file = docs_dir / "guide.md"
        guide_file.write_text("# Guide")

        strategy = CaseSensitivityFix(repo_path=temp_repo)

        # Try to fix link with wrong case
        source_file = docs_dir / "README.md"
        broken_path = "./GUIDE.MD"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        assert result is not None, "Should find a fix"
        assert result.fixed_path == "./guide.md"
        assert result.confidence == 0.95
        assert result.strategy_name == "case_sensitivity"

    def test_multiple_case_matches_low_confidence(self, temp_repo):
        """Multiple case-insensitive matches should return low confidence.

        Scenario:
            - Link points to "./readme"
            - Files exist: "README.md", "readme.txt", "Readme.html"
            - Multiple matches = ambiguous
        """
        from link_fixer import CaseSensitivityFix

        docs_dir = temp_repo / "docs"
        docs_dir.mkdir(exist_ok=True)

        # Create multiple files with different cases
        (docs_dir / "README.md").write_text("# README")
        (docs_dir / "readme.txt").write_text("readme")
        (docs_dir / "Readme.html").write_text("<h1>Readme</h1>")

        strategy = CaseSensitivityFix(repo_path=temp_repo)

        source_file = docs_dir / "index.md"
        broken_path = "./readme"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        # Should find matches but with low confidence
        if result is not None:
            assert result.confidence < 0.70, "Multiple matches = low confidence"
        # Or might return None due to ambiguity

    def test_no_case_variants_returns_none(self, temp_repo):
        """No case-insensitive matches should return None.

        Scenario:
            - Link points to "./nonexistent.md"
            - No files match (even case-insensitively)
        """
        from link_fixer import CaseSensitivityFix

        docs_dir = temp_repo / "docs"
        docs_dir.mkdir(exist_ok=True)

        strategy = CaseSensitivityFix(repo_path=temp_repo)

        source_file = docs_dir / "README.md"
        broken_path = "./nonexistent.md"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        assert result is None, "Should not find fix for truly missing file"

    def test_preserves_relative_path_structure(self, temp_repo):
        """Should preserve relative path structure (../, ./, etc).

        Scenario:
            - Link is "../OTHER/FILE.MD"
            - File exists as "../other/file.md"
            - Should preserve "../" prefix
        """
        from link_fixer import CaseSensitivityFix

        # Create nested structure
        docs_dir = temp_repo / "docs"
        other_dir = temp_repo / "other"
        docs_dir.mkdir(exist_ok=True)
        other_dir.mkdir(exist_ok=True)

        target_file = other_dir / "file.md"
        target_file.write_text("# File")

        strategy = CaseSensitivityFix(repo_path=temp_repo)

        source_file = docs_dir / "README.md"
        broken_path = "../OTHER/FILE.MD"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        assert result is not None
        assert result.fixed_path == "../other/file.md"
        assert result.confidence == 0.95

    def test_handles_anchor_fragments(self, temp_repo):
        """Should preserve anchor fragments in links.

        Scenario:
            - Link is "./GUIDE.MD#section"
            - File exists as "./guide.md"
            - Should fix case but preserve "#section"
        """
        from link_fixer import CaseSensitivityFix

        docs_dir = temp_repo / "docs"
        docs_dir.mkdir(exist_ok=True)
        guide_file = docs_dir / "guide.md"
        guide_file.write_text("# Guide\n\n## Section")

        strategy = CaseSensitivityFix(repo_path=temp_repo)

        source_file = docs_dir / "README.md"
        broken_path = "./GUIDE.MD#section"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        assert result is not None
        assert result.fixed_path == "./guide.md#section"
        assert "#section" in result.fixed_path
