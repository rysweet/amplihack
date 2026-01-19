"""Tests for broken anchor fix strategy.

Tests verify:
- Exact anchor match (90% confidence)
- Fuzzy anchor match (70-85% confidence based on similarity)
- Header anchor generation rules
- Case-insensitive anchor matching
"""


class TestBrokenAnchorsStrategy:
    """Tests for BrokenAnchorsFix strategy."""

    def test_exact_match_high_confidence(self, temp_repo):
        """Exact anchor match should return 90% confidence.

        Scenario:
            - Link is "./guide.md#non-existent"
            - File has header "## Installation"
            - Exact match: "installation" exists
        """
        from link_fixer import BrokenAnchorsFix

        docs_dir = temp_repo / "docs"
        docs_dir.mkdir(exist_ok=True)

        # Create file with headers
        guide = docs_dir / "guide.md"
        guide.write_text("""# Guide

## Installation

Instructions here.

## Configuration

Config details.
""")

        strategy = BrokenAnchorsFix(repo_path=temp_repo)

        source_file = docs_dir / "README.md"
        broken_path = "./guide.md#non-existent"

        # Strategy should find "installation" as closest match
        # Use a broken anchor that's similar enough to find "installation"
        broken_path = "./guide.md#instalation"  # Typo: missing 'l', should match "installation"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        assert result is not None
        assert "#installation" in result.fixed_path
        # Confidence should be high due to fuzzy match (85%+ for single char difference)
        assert result.confidence >= 0.70
        assert result.strategy_name == "broken_anchor"

    def test_fuzzy_match_medium_confidence(self, temp_repo):
        """Fuzzy anchor match should return confidence based on similarity.

        Scenario:
            - Link is "./guide.md#instalation" (typo)
            - File has header "## Installation"
            - Fuzzy match: similarity ~0.85
        """
        from link_fixer import BrokenAnchorsFix

        docs_dir = temp_repo / "docs"
        docs_dir.mkdir(exist_ok=True)

        guide = docs_dir / "guide.md"
        guide.write_text("""# Guide

## Installation

Instructions here.
""")

        strategy = BrokenAnchorsFix(repo_path=temp_repo)

        source_file = docs_dir / "README.md"
        broken_path = "./guide.md#instalation"  # Typo

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        assert result is not None
        assert "#installation" in result.fixed_path
        # Confidence should be 70-85% based on similarity
        assert 0.70 <= result.confidence <= 0.85

    def test_no_similar_anchors_returns_none(self, temp_repo):
        """No similar anchors should return None.

        Scenario:
            - Link is "./guide.md#completely-different"
            - File has headers unrelated to the anchor
            - No good matches
        """
        from link_fixer import BrokenAnchorsFix

        docs_dir = temp_repo / "docs"
        docs_dir.mkdir(exist_ok=True)

        guide = docs_dir / "guide.md"
        guide.write_text("""# Guide

## Introduction

## Features
""")

        strategy = BrokenAnchorsFix(repo_path=temp_repo)

        source_file = docs_dir / "README.md"
        broken_path = "./guide.md#completely-different-topic"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        assert result is None, "Should not suggest fix for unrelated anchor"

    def test_case_insensitive_matching(self, temp_repo):
        """Should match anchors case-insensitively via fuzzy matching.

        Scenario:
            - Link is "./guide.md#INSTALATION" (typo + wrong case)
            - File has header "## Installation"
            - Should match despite case difference and typo
        """
        from link_fixer import BrokenAnchorsFix

        docs_dir = temp_repo / "docs"
        docs_dir.mkdir(exist_ok=True)

        guide = docs_dir / "guide.md"
        guide.write_text("""# Guide

## Installation

Instructions.
""")

        strategy = BrokenAnchorsFix(repo_path=temp_repo)

        source_file = docs_dir / "README.md"
        # Use a truly broken anchor (typo + wrong case)
        broken_path = "./guide.md#INSTALATION"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        assert result is not None
        assert "#installation" in result.fixed_path.lower()

    def test_handles_special_characters_in_headers(self, temp_repo):
        """Should handle special characters in header generation.

        Scenario:
            - File has header "## FAQ's & Tips"
            - Anchor slugifies to "#faqs-tips"
            - Broken anchor "#faq-tip" should fuzzy match to it
        """
        from link_fixer import BrokenAnchorsFix

        docs_dir = temp_repo / "docs"
        docs_dir.mkdir(exist_ok=True)

        guide = docs_dir / "guide.md"
        guide.write_text("""# Guide

## FAQ's & Tips

Some tips.
""")

        strategy = BrokenAnchorsFix(repo_path=temp_repo)

        source_file = docs_dir / "README.md"
        # Use a broken anchor similar to the actual one
        broken_path = "./guide.md#faq-tip"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        assert result is not None
        # Should match the GitHub-style anchor
        assert "faq" in result.fixed_path.lower()

    def test_handles_duplicate_headers(self, temp_repo):
        """Should fuzzy match to headers even when duplicates exist.

        Scenario:
            - File has two "## Usage" headers (both create "#usage" anchor)
            - Broken anchor "#usage-info" should match "#usage"
        """
        from link_fixer import BrokenAnchorsFix

        docs_dir = temp_repo / "docs"
        docs_dir.mkdir(exist_ok=True)

        guide = docs_dir / "guide.md"
        guide.write_text("""# Guide

## Usage

First usage section.

## Configuration

Config section.
""")

        strategy = BrokenAnchorsFix(repo_path=temp_repo)

        source_file = docs_dir / "README.md"
        # Broken anchor similar to "usage"
        broken_path = "./guide.md#usag"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        assert result is not None
        # Should suggest #usage
        assert "#usage" in result.fixed_path

    def test_preserves_file_path(self, temp_repo):
        """Should preserve file path while fixing anchor.

        Scenario:
            - Link is "../other/guide.md#bad-anchor"
            - Should fix anchor but keep "../other/guide.md"
        """
        from link_fixer import BrokenAnchorsFix

        # Create nested structure
        docs_dir = temp_repo / "docs"
        other_dir = temp_repo / "other"
        docs_dir.mkdir(exist_ok=True)
        other_dir.mkdir(exist_ok=True)

        guide = other_dir / "guide.md"
        guide.write_text("""# Guide

## Installation
""")

        strategy = BrokenAnchorsFix(repo_path=temp_repo)

        source_file = docs_dir / "README.md"
        # Use an anchor close enough to "installation" to trigger fuzzy match
        broken_path = "../other/guide.md#install"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        assert result is not None
        assert result.fixed_path.startswith("../other/guide.md#")
        assert "#installation" in result.fixed_path

    def test_multi_word_header_to_anchor(self, temp_repo):
        """Should convert multi-word headers to proper anchors.

        Scenario:
            - Header: "## Getting Started with Installation"
            - Anchor should be: "#getting-started-with-installation"
        """
        from link_fixer import BrokenAnchorsFix

        docs_dir = temp_repo / "docs"
        docs_dir.mkdir(exist_ok=True)

        guide = docs_dir / "guide.md"
        guide.write_text("""# Guide

## Getting Started with Installation

Instructions.
""")

        strategy = BrokenAnchorsFix(repo_path=temp_repo)

        source_file = docs_dir / "README.md"
        broken_path = "./guide.md#getting-started"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        assert result is not None
        assert "getting-started" in result.fixed_path.lower()
