"""Tests for missing extension fix strategy.

Tests verify:
- Single .md extension match (85% confidence)
- Multiple file extensions (low confidence)
- Common markdown file patterns
- Preservation of path structure
"""


class TestMissingExtensionStrategy:
    """Tests for MissingExtensionFix strategy."""

    def test_single_md_match_high_confidence(self, temp_repo):
        """Single .md file match should return 85% confidence.

        Scenario:
            - Link points to "./README"
            - File exists as "./README.md"
            - Only one matching file with extension
        """
        from link_fixer import MissingExtensionFix

        docs_dir = temp_repo / "docs"
        docs_dir.mkdir(exist_ok=True)

        # Create the target file
        readme = docs_dir / "README.md"
        readme.write_text("# README")

        strategy = MissingExtensionFix(repo_path=temp_repo)

        source_file = docs_dir / "guide.md"
        broken_path = "./README"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        assert result is not None, "Should find .md extension"
        assert result.fixed_path == "./README.md"
        assert result.confidence == 0.85
        assert result.strategy_name == "missing_extension"

    def test_multiple_extensions_low_confidence(self, temp_repo):
        """Multiple file extensions should return low confidence.

        Scenario:
            - Link points to "./README"
            - Files exist: "README.md", "README.txt", "README.html"
            - Multiple matches = ambiguous
        """
        from link_fixer import MissingExtensionFix

        docs_dir = temp_repo / "docs"
        docs_dir.mkdir(exist_ok=True)

        # Create multiple files with same base name
        (docs_dir / "README.md").write_text("# README MD")
        (docs_dir / "README.txt").write_text("README TXT")
        (docs_dir / "README.html").write_text("<h1>README HTML</h1>")

        strategy = MissingExtensionFix(repo_path=temp_repo)

        source_file = docs_dir / "guide.md"
        broken_path = "./README"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        # Should find matches but with low confidence
        if result is not None:
            assert result.confidence < 0.70, "Multiple extensions = low confidence"
        # Or might return None due to ambiguity

    def test_no_matching_files_returns_none(self, temp_repo):
        """No files with extensions should return None.

        Scenario:
            - Link points to "./nonexistent"
            - No files match with any extension
        """
        from link_fixer import MissingExtensionFix

        docs_dir = temp_repo / "docs"
        docs_dir.mkdir(exist_ok=True)

        strategy = MissingExtensionFix(repo_path=temp_repo)

        source_file = docs_dir / "guide.md"
        broken_path = "./nonexistent"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        assert result is None, "Should not find fix for missing file"

    def test_preserves_relative_paths(self, temp_repo):
        """Should preserve relative path structure.

        Scenario:
            - Link is "../other/file"
            - File exists as "../other/file.md"
            - Should preserve "../" prefix
        """
        from link_fixer import MissingExtensionFix

        # Create nested structure
        docs_dir = temp_repo / "docs"
        other_dir = temp_repo / "other"
        docs_dir.mkdir(exist_ok=True)
        other_dir.mkdir(exist_ok=True)

        target_file = other_dir / "file.md"
        target_file.write_text("# File")

        strategy = MissingExtensionFix(repo_path=temp_repo)

        source_file = docs_dir / "README.md"
        broken_path = "../other/file"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        assert result is not None
        assert result.fixed_path == "../other/file.md"

    def test_handles_anchor_fragments(self, temp_repo):
        """Should preserve anchor fragments in links.

        Scenario:
            - Link is "./guide#section"
            - File exists as "./guide.md"
            - Should add .md but preserve "#section"
        """
        from link_fixer import MissingExtensionFix

        docs_dir = temp_repo / "docs"
        docs_dir.mkdir(exist_ok=True)
        guide_file = docs_dir / "guide.md"
        guide_file.write_text("# Guide\n\n## Section")

        strategy = MissingExtensionFix(repo_path=temp_repo)

        source_file = docs_dir / "README.md"
        broken_path = "./guide#section"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        assert result is not None
        assert result.fixed_path == "./guide.md#section"
        assert ".md" in result.fixed_path
        assert "#section" in result.fixed_path

    def test_common_markdown_extensions(self, temp_repo):
        """Should try common markdown extensions (.md, .markdown).

        Scenario:
            - Link points to "./file"
            - File exists as "./file.markdown"
            - Should find .markdown extension
        """
        from link_fixer import MissingExtensionFix

        docs_dir = temp_repo / "docs"
        docs_dir.mkdir(exist_ok=True)

        # Create file with .markdown extension
        file_md = docs_dir / "file.markdown"
        file_md.write_text("# File")

        strategy = MissingExtensionFix(repo_path=temp_repo)

        source_file = docs_dir / "README.md"
        broken_path = "./file"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        assert result is not None
        assert ".markdown" in result.fixed_path or ".md" in result.fixed_path

    def test_prefers_md_over_markdown(self, temp_repo):
        """Should prefer .md over .markdown when both exist.

        Scenario:
            - Link points to "./file"
            - Files exist: "file.md" and "file.markdown"
            - Should prefer .md (more common)
        """
        from link_fixer import MissingExtensionFix

        docs_dir = temp_repo / "docs"
        docs_dir.mkdir(exist_ok=True)

        # Create both extensions
        (docs_dir / "file.md").write_text("# File MD")
        (docs_dir / "file.markdown").write_text("# File MARKDOWN")

        strategy = MissingExtensionFix(repo_path=temp_repo)

        source_file = docs_dir / "README.md"
        broken_path = "./file"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        assert result is not None
        assert result.fixed_path == "./file.md", "Should prefer .md"
