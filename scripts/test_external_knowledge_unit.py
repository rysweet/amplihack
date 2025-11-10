#!/usr/bin/env python3
"""Unit tests for external knowledge that don't require Neo4j.

Tests the core functionality without database integration.
"""

import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from amplihack.memory.neo4j.external_knowledge import (
    APIReference,
    ExternalDoc,
    ExternalKnowledgeManager,
    KnowledgeSource,
)


class TestExternalKnowledgeUnit:
    """Unit tests for external knowledge."""

    def __init__(self):
        self.test_results = []

    def record_result(self, name: str, passed: bool, message: str = ""):
        """Record test result."""
        status_icon = "✅" if passed else "❌"
        print(f"{status_icon} {name}: {message}")
        self.test_results.append(
            {
                "name": name,
                "status": "PASS" if passed else "FAIL",
                "message": message,
            }
        )

    def test_external_doc_creation(self):
        """Test ExternalDoc dataclass creation."""
        print("\n[1/8] Testing ExternalDoc creation...")

        doc = ExternalDoc(
            url="https://docs.python.org/3/library/json.html",
            title="json — JSON encoder and decoder",
            content="The json module provides an API...",
            source=KnowledgeSource.PYTHON_DOCS,
            version="3.10",
            trust_score=0.95,
        )

        passed = (
            doc.url == "https://docs.python.org/3/library/json.html"
            and doc.source == KnowledgeSource.PYTHON_DOCS
            and doc.trust_score == 0.95
        )

        self.record_result(
            "external_doc_creation",
            passed,
            "ExternalDoc created with correct attributes" if passed else "Attributes mismatch",
        )

    def test_api_reference_creation(self):
        """Test APIReference dataclass creation."""
        print("\n[2/8] Testing APIReference creation...")

        api_ref = APIReference(
            name="json.loads",
            signature="json.loads(s, *, cls=None, ...)",
            doc_url="https://docs.python.org/3/library/json.html#json.loads",
            description="Deserialize JSON to Python object",
            examples=['json.loads(\'{"key": "value"}\')'],
            source=KnowledgeSource.PYTHON_DOCS,
            version="3.10",
        )

        passed = (
            api_ref.name == "json.loads"
            and api_ref.version == "3.10"
            and len(api_ref.examples) == 1
        )

        self.record_result(
            "api_reference_creation",
            passed,
            "APIReference created correctly" if passed else "Attributes mismatch",
        )

    def test_knowledge_source_enum(self):
        """Test KnowledgeSource enum."""
        print("\n[3/8] Testing KnowledgeSource enum...")

        sources = [
            KnowledgeSource.PYTHON_DOCS,
            KnowledgeSource.MS_LEARN,
            KnowledgeSource.GITHUB,
            KnowledgeSource.LIBRARY_DOCS,
            KnowledgeSource.CUSTOM,
        ]

        passed = len(sources) == 5 and all(isinstance(s, KnowledgeSource) for s in sources)

        self.record_result(
            "knowledge_source_enum",
            passed,
            f"All {len(sources)} sources valid" if passed else "Enum validation failed",
        )

    def test_cache_path_generation(self):
        """Test cache file path generation."""
        print("\n[4/8] Testing cache path generation...")

        # Create mock connector and config
        mock_conn = Mock()
        mock_config = Mock()
        temp_cache = Path(tempfile.mkdtemp())

        with patch(
            "amplihack.memory.neo4j.external_knowledge.get_config", return_value=mock_config
        ):
            manager = ExternalKnowledgeManager(
                connector=mock_conn,
                cache_dir=temp_cache,
                enable_http_cache=True,
            )

            # Test same URL generates same path
            url = "https://example.com/test"
            path1 = manager._get_cache_path(url)
            path2 = manager._get_cache_path(url)

            passed = path1 == path2 and path1.parent == temp_cache and path1.suffix == ".json"

            self.record_result(
                "cache_path_generation",
                passed,
                "Cache paths consistent and valid" if passed else "Path generation issue",
            )

    def test_local_cache_write_read(self):
        """Test local filesystem caching."""
        print("\n[5/8] Testing local cache write/read...")

        mock_conn = Mock()
        mock_config = Mock()
        temp_cache = Path(tempfile.mkdtemp())

        with patch(
            "amplihack.memory.neo4j.external_knowledge.get_config", return_value=mock_config
        ):
            manager = ExternalKnowledgeManager(
                connector=mock_conn,
                cache_dir=temp_cache,
                enable_http_cache=True,
            )

            # Create and cache document
            doc = ExternalDoc(
                url="https://example.com/test",
                title="Test Document",
                content="Test content here",
                source=KnowledgeSource.CUSTOM,
                version="1.0",
                trust_score=0.8,
                ttl_hours=24,
            )

            manager._cache_doc(doc)

            # Read back from cache
            cached_doc = manager._get_cached_doc(doc.url)

            passed = (
                cached_doc is not None
                and cached_doc.url == doc.url
                and cached_doc.title == doc.title
                and cached_doc.content == doc.content
            )

            self.record_result(
                "local_cache_write_read",
                passed,
                "Document cached and retrieved correctly" if passed else "Cache mismatch",
            )

    def test_cache_expiry(self):
        """Test cache TTL expiration."""
        print("\n[6/8] Testing cache expiry...")

        mock_conn = Mock()
        mock_config = Mock()
        temp_cache = Path(tempfile.mkdtemp())

        with patch(
            "amplihack.memory.neo4j.external_knowledge.get_config", return_value=mock_config
        ):
            manager = ExternalKnowledgeManager(
                connector=mock_conn,
                cache_dir=temp_cache,
                enable_http_cache=True,
            )

            # Create expired document
            past_date = datetime.now() - timedelta(hours=48)
            doc = ExternalDoc(
                url="https://example.com/expired",
                title="Expired Doc",
                content="Old content",
                source=KnowledgeSource.CUSTOM,
                version="old",
                trust_score=0.8,
                fetched_at=past_date,
                ttl_hours=24,  # 24 hour TTL, fetched 48 hours ago = expired
            )

            manager._cache_doc(doc)

            # Try to read expired doc
            cached_doc = manager._get_cached_doc(doc.url)

            passed = cached_doc is None  # Should be None (expired)

            self.record_result(
                "cache_expiry",
                passed,
                "Expired document correctly ignored" if passed else "Expired doc returned",
            )

    def test_title_extraction(self):
        """Test HTML title extraction."""
        print("\n[7/8] Testing title extraction...")

        mock_conn = Mock()
        mock_config = Mock()

        with patch(
            "amplihack.memory.neo4j.external_knowledge.get_config", return_value=mock_config
        ):
            manager = ExternalKnowledgeManager(connector=mock_conn)

            html_samples = [
                ("<html><title>Test Title</title></html>", "Test Title"),
                ("<HTML><TITLE>Uppercase</TITLE></HTML>", "Uppercase"),
                ("<html><head><title>  Spaced  </title></head></html>", "Spaced"),
                ("<html>No title</html>", None),
            ]

            passed = True
            for html, expected in html_samples:
                result = manager._extract_title(html)
                if result != expected:
                    passed = False
                    break

            self.record_result(
                "title_extraction",
                passed,
                f"All {len(html_samples)} title extractions correct"
                if passed
                else "Extraction mismatch",
            )

    def test_http_fetch_with_mock(self):
        """Test HTTP fetching with mocked requests."""
        print("\n[8/8] Testing HTTP fetch (mocked)...")

        mock_conn = Mock()
        mock_config = Mock()

        with patch(
            "amplihack.memory.neo4j.external_knowledge.get_config", return_value=mock_config
        ):
            manager = ExternalKnowledgeManager(connector=mock_conn)

            # Mock HTTP response
            with patch("amplihack.memory.neo4j.external_knowledge.requests") as mock_requests:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.text = "<html><title>Mock Doc</title><body>Mock content</body></html>"
                mock_response.headers = {"content-type": "text/html"}
                mock_response.raise_for_status = Mock()
                mock_requests.get.return_value = mock_response

                doc = manager.fetch_api_docs(
                    url="https://example.com/test",
                    source=KnowledgeSource.CUSTOM,
                    trust_score=0.75,
                )

                passed = (
                    doc is not None
                    and doc.url == "https://example.com/test"
                    and doc.title == "Mock Doc"
                    and "Mock content" in doc.content
                    and doc.trust_score == 0.75
                )

                self.record_result(
                    "http_fetch_mocked",
                    passed,
                    "HTTP fetch successful with mock" if passed else "Fetch failed",
                )

    def run_all_tests(self):
        """Run all unit tests."""
        print("=" * 60)
        print("EXTERNAL KNOWLEDGE UNIT TESTS (No Neo4j Required)")
        print("=" * 60)

        self.test_external_doc_creation()
        self.test_api_reference_creation()
        self.test_knowledge_source_enum()
        self.test_cache_path_generation()
        self.test_local_cache_write_read()
        self.test_cache_expiry()
        self.test_title_extraction()
        self.test_http_fetch_with_mock()

        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)

        passed = sum(1 for r in self.test_results if r["status"] == "PASS")
        failed = sum(1 for r in self.test_results if r["status"] == "FAIL")
        total = len(self.test_results)

        print(f"\nTotal: {total} | Passed: {passed} | Failed: {failed}")

        if failed > 0:
            print("\n❌ Some tests failed")
            sys.exit(1)
        else:
            print("\n✅ All tests passed!")


def main():
    """Main test entry point."""
    tester = TestExternalKnowledgeUnit()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
