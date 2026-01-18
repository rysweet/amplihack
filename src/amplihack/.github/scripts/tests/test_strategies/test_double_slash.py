"""Tests for double slash cleanup strategy.

Tests verify:
- Double slash removal (70% confidence)
- Multiple consecutive slashes
- Preserving protocol slashes (https://)
- Edge cases with mixed slashes
"""


class TestDoubleSlashStrategy:
    """Tests for DoubleSlashFix strategy."""

    def test_removes_double_slash(self, temp_repo):
        """Should remove double slashes from paths.

        Scenario:
            - Link is "./docs//guide.md"
            - Should clean to "./docs/guide.md"
            - Confidence: 70%
        """
        from link_fixer import DoubleSlashFix

        docs_dir = temp_repo / "docs"
        docs_dir.mkdir(exist_ok=True)

        guide = docs_dir / "guide.md"
        guide.write_text("# Guide")

        strategy = DoubleSlashFix(repo_path=temp_repo)

        source_file = temp_repo / "README.md"
        broken_path = "./docs//guide.md"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        assert result is not None
        assert result.fixed_path == "./docs/guide.md"
        assert result.confidence == 0.70
        assert result.strategy_name == "double_slash"

    def test_removes_multiple_slashes(self, temp_repo):
        """Should remove multiple consecutive slashes.

        Scenario:
            - Link is "./docs///guide///file.md"
            - Should clean to "./docs/guide/file.md"
        """
        from link_fixer import DoubleSlashFix

        guide_dir = temp_repo / "docs" / "guide"
        guide_dir.mkdir(parents=True)

        file_md = guide_dir / "file.md"
        file_md.write_text("# File")

        strategy = DoubleSlashFix(repo_path=temp_repo)

        source_file = temp_repo / "README.md"
        broken_path = "./docs///guide///file.md"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        assert result is not None
        assert result.fixed_path == "./docs/guide/file.md"

    def test_preserves_protocol_slashes(self, temp_repo):
        """Should NOT remove slashes from URLs (https://).

        Scenario:
            - Link is "https://example.com/docs/guide.md"
            - Should not modify protocol slashes
        """
        from link_fixer import DoubleSlashFix

        strategy = DoubleSlashFix(repo_path=temp_repo)

        source_file = temp_repo / "README.md"
        broken_path = "https://example.com/docs/guide.md"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        # Should not attempt to fix URLs
        assert result is None or "https://" in result.fixed_path

    def test_handles_leading_slash(self, temp_repo):
        """Should handle leading double slashes.

        Scenario:
            - Link is "//docs/guide.md"
            - Should clean to "/docs/guide.md"
        """
        from link_fixer import DoubleSlashFix

        strategy = DoubleSlashFix(repo_path=temp_repo)

        source_file = temp_repo / "README.md"
        broken_path = "//docs/guide.md"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        assert result is not None
        assert result.fixed_path == "/docs/guide.md"

    def test_handles_trailing_slash(self, temp_repo):
        """Should handle trailing double slashes.

        Scenario:
            - Link is "./docs//"
            - Should clean to "./docs/"
        """
        from link_fixer import DoubleSlashFix

        docs_dir = temp_repo / "docs"
        docs_dir.mkdir(exist_ok=True)

        strategy = DoubleSlashFix(repo_path=temp_repo)

        source_file = temp_repo / "README.md"
        broken_path = "./docs//"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        assert result is not None
        assert result.fixed_path == "./docs/"

    def test_preserves_anchor_fragments(self, temp_repo):
        """Should preserve anchor fragments during cleanup.

        Scenario:
            - Link is "./docs//guide.md#section"
            - Should clean to "./docs/guide.md#section"
        """
        from link_fixer import DoubleSlashFix

        docs_dir = temp_repo / "docs"
        docs_dir.mkdir(exist_ok=True)

        guide = docs_dir / "guide.md"
        guide.write_text("# Guide\n\n## Section")

        strategy = DoubleSlashFix(repo_path=temp_repo)

        source_file = temp_repo / "README.md"
        broken_path = "./docs//guide.md#section"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        assert result is not None
        assert result.fixed_path == "./docs/guide.md#section"
        assert "#section" in result.fixed_path

    def test_no_double_slashes_returns_none(self, temp_repo):
        """Should return None if no double slashes exist.

        Scenario:
            - Link is "./docs/guide.md" (clean)
            - No double slashes to fix
        """
        from link_fixer import DoubleSlashFix

        docs_dir = temp_repo / "docs"
        docs_dir.mkdir(exist_ok=True)

        guide = docs_dir / "guide.md"
        guide.write_text("# Guide")

        strategy = DoubleSlashFix(repo_path=temp_repo)

        source_file = temp_repo / "README.md"
        broken_path = "./docs/guide.md"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        # If no double slashes, should return None (no fix needed)
        assert result is None

    def test_mixed_with_parent_refs(self, temp_repo):
        """Should handle double slashes mixed with parent references.

        Scenario:
            - Link is "..//docs//guide.md"
            - Should clean to "../docs/guide.md"
        """
        from link_fixer import DoubleSlashFix

        docs_dir = temp_repo / "docs"
        docs_dir.mkdir(exist_ok=True)

        guide = docs_dir / "guide.md"
        guide.write_text("# Guide")

        strategy = DoubleSlashFix(repo_path=temp_repo)

        subdir = temp_repo / "subdir"
        subdir.mkdir(exist_ok=True)
        source_file = subdir / "README.md"

        broken_path = "..//docs//guide.md"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        assert result is not None
        assert result.fixed_path == "../docs/guide.md"

    def test_combines_with_normalization(self, temp_repo):
        """Double slash fix may combine with path normalization.

        Scenario:
            - Link is "./docs//.//guide.md"
            - Should clean to "./docs/guide.md"
        """
        from link_fixer import DoubleSlashFix

        docs_dir = temp_repo / "docs"
        docs_dir.mkdir(exist_ok=True)

        guide = docs_dir / "guide.md"
        guide.write_text("# Guide")

        strategy = DoubleSlashFix(repo_path=temp_repo)

        source_file = temp_repo / "README.md"
        broken_path = "./docs//.//guide.md"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        assert result is not None
        assert result.fixed_path == "./docs/guide.md"
