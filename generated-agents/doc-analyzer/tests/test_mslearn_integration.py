"""
Tests for Microsoft Learn integration.

These tests verify the agent can fetch and analyze real MS Learn documentation.
"""

import sys
from pathlib import Path

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent import DocumentationAnalyzer
from mslearn_fetcher import SAMPLE_DOCS, MSLearnFetcher, get_sample_markdown


class TestMSLearnFetcher:
    """Test MS Learn document fetching."""

    def test_sample_markdown(self):
        """Test sample markdown is well-formed."""
        markdown = get_sample_markdown()

        assert markdown is not None, "Sample markdown should exist"
        assert len(markdown) > 100, "Should have substantial content"
        assert markdown.startswith("#"), "Should start with heading"
        assert "## Overview" in markdown, "Should have overview section"
        assert "```" in markdown, "Should have code examples"

    def test_fetcher_initialization(self):
        """Test fetcher can be initialized."""
        fetcher = MSLearnFetcher()

        assert fetcher is not None, "Fetcher should initialize"
        assert fetcher.timeout == 30, "Should have default timeout"
        assert fetcher.session is not None, "Should have session"

    @pytest.mark.integration
    @pytest.mark.skip(reason="Requires network access - run manually")
    def test_fetch_real_document(self):
        """Integration test: Fetch a real MS Learn document."""
        fetcher = MSLearnFetcher()

        # Try to fetch a stable MS Learn page
        url = SAMPLE_DOCS[0]
        content = fetcher.fetch_document(url)

        if content:
            assert len(content) > 0, "Should fetch content"
            assert "#" in content, "Should contain headings"
            print(f"\nFetched {len(content)} characters from {url}")
        else:
            pytest.skip("Could not fetch document - network issue")

    @pytest.mark.integration
    @pytest.mark.skip(reason="Requires network access - run manually")
    def test_fetch_multiple_documents(self):
        """Integration test: Fetch multiple documents."""
        fetcher = MSLearnFetcher()

        results = fetcher.fetch_multiple(SAMPLE_DOCS[:2])

        assert len(results) == 2, "Should attempt all fetches"
        successful = sum(1 for v in results.values() if v is not None)
        print(f"\nSuccessfully fetched {successful}/{len(results)} documents")


class TestMSLearnAnalysis:
    """Test analyzing MS Learn documentation."""

    def test_analyze_sample_document(self):
        """Test analyzing the sample MS Learn document."""
        analyzer = DocumentationAnalyzer()
        content = get_sample_markdown()

        result = analyzer.analyze_document(content, url="test://sample")

        print("\nSample Document Analysis:")
        print(f"  Title: {result.title}")
        print(f"  Sections: {result.section_count}")
        print(f"  Total Words: {result.total_words}")
        print(f"  Code Examples: {result.code_examples_count}")
        print(f"  Overall Score: {result.overall_score:.1f}/100")
        print(f"  Structure Score: {result.structure_score:.1f}/100")
        print(f"  Completeness Score: {result.completeness_score:.1f}/100")
        print(f"  Clarity Score: {result.clarity_score:.1f}/100")

        # Assertions about the sample doc
        assert result.title == "Azure Architecture Guide", "Should extract correct title"
        assert result.section_count >= 5, "Should find multiple sections"
        assert result.code_examples_count >= 1, "Should find code examples"
        assert result.overall_score >= 70, "Sample doc should score well"

        # Check for expected patterns
        assert result.pattern_matches.get("has_overview_section", 0) == 1, (
            "Should detect overview section"
        )
        assert result.pattern_matches.get("has_prerequisites", 0) == 1, (
            "Should detect prerequisites"
        )
        assert result.pattern_matches.get("has_code_examples", 0) == 1, (
            "Should detect code examples"
        )
        assert result.pattern_matches.get("has_next_steps", 0) == 1, "Should detect next steps"

    def test_section_parsing(self):
        """Test detailed section parsing."""
        analyzer = DocumentationAnalyzer()
        content = get_sample_markdown()

        result = analyzer.analyze_document(content, url="test://sections")

        # Verify section details
        assert len(result.sections) > 0, "Should parse sections"

        # Check heading levels
        levels = [s.level for s in result.sections]
        assert min(levels) >= 1, "Should have proper heading levels"
        assert max(levels) <= 4, "Should not be too deeply nested"

        # Check section content
        has_content = any(s.word_count > 10 for s in result.sections)
        assert has_content, "Sections should have content"

        print("\nSection Details:")
        for i, section in enumerate(result.sections[:5]):  # First 5 sections
            print(f"  {i + 1}. {'#' * section.level} {section.heading}")
            print(f"     Words: {section.word_count}, Code: {section.has_code_examples}")

    def test_quality_patterns(self):
        """Test quality pattern detection."""
        analyzer = DocumentationAnalyzer()
        content = get_sample_markdown()

        result = analyzer.analyze_document(content, url="test://patterns")

        print("\nPattern Detection:")
        for pattern, matched in result.pattern_matches.items():
            status = "✓" if matched else "✗"
            print(f"  {status} {pattern}")

        # Sample doc should match most quality patterns
        matched_count = sum(result.pattern_matches.values())
        total_patterns = len(result.pattern_matches)

        assert matched_count >= total_patterns * 0.6, (
            f"Should match most patterns (got {matched_count}/{total_patterns})"
        )

    def test_learned_insights(self):
        """Test insight generation."""
        analyzer = DocumentationAnalyzer()

        # Analyze multiple times to build experience
        for i in range(3):
            content = get_sample_markdown()
            result = analyzer.analyze_document(content, url=f"test://insights{i}")

        # Last result should have insights
        assert result.learned_insights is not None, "Should generate insights"
        print("\nLearned Insights:")
        for insight in result.learned_insights:
            print(f"  • {insight}")

    @pytest.mark.integration
    @pytest.mark.skip(reason="Requires network access - run manually")
    def test_analyze_real_mslearn_doc(self):
        """Integration test: Analyze a real MS Learn document."""
        fetcher = MSLearnFetcher()
        analyzer = DocumentationAnalyzer()

        url = SAMPLE_DOCS[0]
        content = fetcher.fetch_document(url)

        if not content:
            pytest.skip("Could not fetch document")

        result = analyzer.analyze_document(content, url=url)

        print("\nReal MS Learn Document Analysis:")
        print(f"  URL: {url}")
        print(f"  Title: {result.title}")
        print(f"  Overall Score: {result.overall_score:.1f}/100")
        print(f"  Sections: {result.section_count}")
        print(f"  Insights: {', '.join(result.learned_insights)}")

        assert result.overall_score > 0, "Should analyze real doc"
        assert result.section_count > 0, "Should find sections"


class TestEndToEndLearning:
    """End-to-end test of learning from MS Learn docs."""

    def test_learning_from_samples(self):
        """Test agent learns from analyzing multiple sample docs."""
        analyzer = DocumentationAnalyzer()

        # Analyze sample doc multiple times
        scores = []
        for i in range(5):
            content = get_sample_markdown()
            result = analyzer.analyze_document(content, url=f"test://learn{i}")
            scores.append(result.overall_score)

        print("\nLearning from Samples:")
        print(f"  Scores: {[f'{s:.1f}' for s in scores]}")

        # Get learning stats
        stats = analyzer.get_learning_stats()
        print(f"  Average: {stats.get('avg_quality', 0):.1f}")
        print(f"  Trend: {stats.get('trend', 'unknown')}")
        print(f"  Improvement: {stats.get('improvement', 0):+.1f}")

        # Verify consistency (same doc should get similar scores)
        score_variance = max(scores) - min(scores)
        assert score_variance < 20, f"Scores should be consistent (variance: {score_variance:.1f})"


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
