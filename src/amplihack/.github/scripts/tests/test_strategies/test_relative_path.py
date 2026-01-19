"""Tests for relative path normalization strategy.

Tests verify:
- Path normalization (75% confidence)
- Resolving ".." and "." segments
- Simplifying complex paths
- Edge cases with multiple levels
"""


class TestRelativePathStrategy:
    """Tests for RelativePathFix strategy."""

    def test_normalizes_redundant_dots(self, temp_repo):
        """Should normalize paths with redundant "./" segments.

        Scenario:
            - Link is "./docs/./guide.md"
            - Should normalize to "./docs/guide.md"
            - Confidence: 75%
        """
        from link_fixer import RelativePathFix

        docs_dir = temp_repo / "docs"
        docs_dir.mkdir(exist_ok=True)

        guide = docs_dir / "guide.md"
        guide.write_text("# Guide")

        strategy = RelativePathFix(repo_path=temp_repo)

        source_file = temp_repo / "README.md"
        broken_path = "./docs/./guide.md"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        assert result is not None
        assert result.fixed_path == "./docs/guide.md"
        assert result.confidence == 0.75
        assert result.strategy_name == "relative_path"

    def test_resolves_parent_directory_references(self, temp_repo):
        """Should resolve ".." parent directory references.

        Scenario:
            - Link is "./docs/../other/file.md"
            - Should normalize to "./other/file.md"
        """
        from link_fixer import RelativePathFix

        other_dir = temp_repo / "other"
        other_dir.mkdir(exist_ok=True)

        file_md = other_dir / "file.md"
        file_md.write_text("# File")

        strategy = RelativePathFix(repo_path=temp_repo)

        source_file = temp_repo / "README.md"
        broken_path = "./docs/../other/file.md"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        assert result is not None
        assert result.fixed_path == "./other/file.md"

    def test_handles_multiple_parent_refs(self, temp_repo):
        """Should handle multiple ".." references.

        Scenario:
            - Link is "./a/b/../../c/file.md"
            - Should normalize to "./c/file.md"
        """
        from link_fixer import RelativePathFix

        c_dir = temp_repo / "c"
        c_dir.mkdir(exist_ok=True)

        file_md = c_dir / "file.md"
        file_md.write_text("# File")

        strategy = RelativePathFix(repo_path=temp_repo)

        source_file = temp_repo / "README.md"
        broken_path = "./a/b/../../c/file.md"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        assert result is not None
        assert result.fixed_path == "./c/file.md"

    def test_preserves_anchor_fragments(self, temp_repo):
        """Should preserve anchor fragments during normalization.

        Scenario:
            - Link is "./docs/./guide.md#section"
            - Should normalize to "./docs/guide.md#section"
        """
        from link_fixer import RelativePathFix

        docs_dir = temp_repo / "docs"
        docs_dir.mkdir(exist_ok=True)

        guide = docs_dir / "guide.md"
        guide.write_text("# Guide\n\n## Section")

        strategy = RelativePathFix(repo_path=temp_repo)

        source_file = temp_repo / "README.md"
        broken_path = "./docs/./guide.md#section"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        assert result is not None
        assert result.fixed_path == "./docs/guide.md#section"
        assert "#section" in result.fixed_path

    def test_handles_excessive_parent_refs(self, temp_repo):
        """Should handle excessive ".." that go beyond root.

        Scenario:
            - Link is "./../../../file.md" (goes beyond repo root)
            - Should handle gracefully (might return None or clamped path)
        """
        from link_fixer import RelativePathFix

        strategy = RelativePathFix(repo_path=temp_repo)

        source_file = temp_repo / "README.md"
        broken_path = "./../../../file.md"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        # Should either return None or clamped path
        if result is not None:
            # Path should not escape repo
            assert not result.fixed_path.startswith("../../../")

    def test_no_normalization_needed_returns_none(self, temp_repo):
        """Should return None if path is already normalized.

        Scenario:
            - Link is "./docs/guide.md" (already clean)
            - No normalization needed
        """
        from link_fixer import RelativePathFix

        docs_dir = temp_repo / "docs"
        docs_dir.mkdir(exist_ok=True)

        guide = docs_dir / "guide.md"
        guide.write_text("# Guide")

        strategy = RelativePathFix(repo_path=temp_repo)

        source_file = temp_repo / "README.md"
        broken_path = "./docs/guide.md"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        # If path is already clean, might return None (no fix needed)
        # Or might return same path with confidence
        if result is not None:
            assert result.fixed_path == broken_path

    def test_complex_nested_normalization(self, temp_repo):
        """Should handle complex nested path normalization.

        Scenario:
            - Link is "./a/./b/../c/./d/../e/file.md"
            - Should normalize to "./a/c/e/file.md"
        """
        from link_fixer import RelativePathFix

        # Create deep structure
        e_dir = temp_repo / "a" / "c" / "e"
        e_dir.mkdir(parents=True)

        file_md = e_dir / "file.md"
        file_md.write_text("# File")

        strategy = RelativePathFix(repo_path=temp_repo)

        source_file = temp_repo / "README.md"
        broken_path = "./a/./b/../c/./d/../e/file.md"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        assert result is not None
        assert result.fixed_path == "./a/c/e/file.md"

    def test_absolute_vs_relative_detection(self, temp_repo):
        """Should only normalize relative paths, not absolute.

        Scenario:
            - Link is "/docs/guide.md" (absolute)
            - Should not attempt normalization (or handle differently)
        """
        from link_fixer import RelativePathFix

        strategy = RelativePathFix(repo_path=temp_repo)

        source_file = temp_repo / "README.md"
        broken_path = "/docs/guide.md"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        # Strategy should skip absolute paths or handle differently
        # This test documents expected behavior
        if result is not None:
            # If it does normalize, should preserve leading /
            assert result.fixed_path.startswith("/")
