#!/usr/bin/env python3
"""Tests fer GitHub Pages link validator - TDD approach.

Testing pyramid:
- 60% Unit tests (fast, heavily mocked)
- 30% Integration tests (multiple components)
- 10% E2E tests (complete workflows)
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from urllib.parse import urljoin

import pytest
import requests

# Import the module under test (will implement after tests)
import validate_gh_pages_links as validator


# ============================================================================
# UNIT TESTS (60%) - Fast, heavily mocked
# ============================================================================

class TestURLParsing:
    """Test URL parsing and normalization"""

    def test_parse_absolute_url(self):
        """Parse absolute URL correctly"""
        url = "https://example.com/page.html"
        parsed = validator.parse_url(url)
        assert parsed.scheme == "https"
        assert parsed.netloc == "example.com"
        assert parsed.path == "/page.html"

    def test_normalize_trailing_slash(self):
        """Normalize URLs with trailing slashes"""
        url1 = validator.normalize_url("https://example.com/page")
        url2 = validator.normalize_url("https://example.com/page/")
        assert url1 == url2

    def test_is_same_domain(self):
        """Identify internal vs external links"""
        base = "https://example.com/"
        assert validator.is_same_domain(base, "https://example.com/page") is True
        assert validator.is_same_domain(base, "https://other.com/page") is False

    def test_resolve_relative_url(self):
        """Resolve relative URLs correctly"""
        base = "https://example.com/docs/guide.html"
        relative = "../api/index.html"
        resolved = validator.resolve_url(base, relative)
        assert resolved == "https://example.com/api/index.html"


class TestLinkExtraction:
    """Test link extraction from HTML"""

    def test_extract_simple_links(self):
        """Extract basic anchor tags"""
        html = '<a href="/page1">Link 1</a><a href="/page2">Link 2</a>'
        links = validator.extract_links(html, "https://example.com/")
        assert len(links) == 2
        assert any(l["url"] == "https://example.com/page1" for l in links)
        assert any(l["url"] == "https://example.com/page2" for l in links)

    def test_extract_anchor_with_fragment(self):
        """Extract links with fragments (#section)"""
        html = '<a href="/page#section">Link</a>'
        links = validator.extract_links(html, "https://example.com/")
        assert len(links) == 1
        assert links[0]["url"] == "https://example.com/page#section"

    def test_skip_mailto_links(self):
        """Skip mailto: and tel: links"""
        html = '<a href="mailto:test@example.com">Email</a><a href="tel:+1234">Phone</a>'
        links = validator.extract_links(html, "https://example.com/")
        assert len(links) == 0

    def test_extract_link_text(self):
        """Capture link text for reporting"""
        html = '<a href="/page">Click Here</a>'
        links = validator.extract_links(html, "https://example.com/")
        assert links[0]["text"] == "Click Here"


class TestCrawlerState:
    """Test crawler state management"""

    def test_initialize_crawler(self):
        """Initialize crawler with base URL"""
        crawler = validator.Crawler("https://example.com/")
        assert crawler.base_url == "https://example.com/"
        assert len(crawler.visited) == 0
        assert len(crawler.queue) == 1

    def test_mark_url_visited(self):
        """Track visited URLs"""
        crawler = validator.Crawler("https://example.com/")
        crawler.mark_visited("https://example.com/page1")
        assert crawler.is_visited("https://example.com/page1") is True
        assert crawler.is_visited("https://example.com/page2") is False

    def test_queue_management(self):
        """Add and remove URLs from queue"""
        crawler = validator.Crawler("https://example.com/")
        crawler.add_to_queue("https://example.com/page1")
        crawler.add_to_queue("https://example.com/page2")
        url = crawler.get_next_url()
        assert url is not None


class TestLinkValidation:
    """Test link validation logic"""

    @patch("requests.head")
    def test_validate_200_ok(self, mock_head):
        """Valid link returns no error"""
        mock_head.return_value.status_code = 200
        error, severity = validator.validate_link("https://example.com/page")
        assert error is None
        assert severity == "ok"

    @patch("requests.head")
    def test_validate_404_not_found(self, mock_head):
        """404 returns error"""
        mock_head.return_value.status_code = 404
        error, severity = validator.validate_link("https://example.com/missing")
        assert error == "Page not found (404)"
        assert severity == "error"

    @patch("requests.head")
    def test_validate_redirect_warning(self, mock_head):
        """Redirect returns warning"""
        mock_head.return_value.status_code = 301
        mock_head.return_value.headers = {"Location": "https://example.com/new"}
        error, severity = validator.validate_link("https://example.com/old")
        assert "Redirects" in error
        assert severity == "warning"

    @patch("requests.head")
    def test_validate_timeout(self, mock_head):
        """Timeout returns warning"""
        mock_head.side_effect = requests.exceptions.Timeout()
        error, severity = validator.validate_link("https://example.com/slow")
        assert "timed out" in error.lower()
        assert severity == "warning"


class TestReportGeneration:
    """Test report formatting"""

    def test_generate_empty_report(self):
        """Generate report with no broken links"""
        results = {
            "summary": {
                "total_pages": 10,
                "total_links": 50,
                "broken_links": 0,
                "warnings": 0,
            },
            "broken_links": [],
            "warnings": [],
        }
        report = validator.generate_report(results)
        assert "Total pages crawled: 10" in report
        assert "Broken links: 0" in report

    def test_generate_report_with_errors(self):
        """Generate report with broken links"""
        results = {
            "summary": {
                "total_pages": 10,
                "total_links": 50,
                "broken_links": 2,
                "warnings": 1,
            },
            "broken_links": [
                {
                    "page_url": "https://example.com/page1",
                    "link_url": "https://example.com/missing",
                    "link_text": "Missing",
                    "error": "404 Not Found",
                    "severity": "error",
                }
            ],
            "warnings": [],
        }
        report = validator.generate_report(results)
        assert "Missing" in report
        assert "404 Not Found" in report


# ============================================================================
# INTEGRATION TESTS (30%) - Multiple components
# ============================================================================

class TestCrawlAndValidate:
    """Test crawler and validator integration"""

    @patch("requests.get")
    @patch("requests.head")
    def test_crawl_single_page_with_links(self, mock_head, mock_get):
        """Crawl page and validate its links"""
        # Mock HTML content
        html_content = """
        <html>
            <body>
                <a href="/page1">Page 1</a>
                <a href="/page2">Page 2</a>
                <a href="https://external.com">External</a>
            </body>
        </html>
        """
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = html_content
        mock_head.return_value.status_code = 200

        crawler = validator.Crawler("https://example.com/")
        results = crawler.crawl()

        assert results["summary"]["total_pages"] >= 1
        assert results["summary"]["total_links"] >= 3

    @patch("requests.get")
    def test_handle_crawl_errors_gracefully(self, mock_get):
        """Continue crawling when individual pages fail"""
        mock_get.side_effect = [
            Mock(status_code=200, text='<a href="/page2">Link</a>'),
            Mock(status_code=500),  # Error on page2
        ]

        crawler = validator.Crawler("https://example.com/")
        results = crawler.crawl()

        # Should not crash, should record the error
        assert results is not None


class TestEndToEnd:
    """Test complete validation workflow"""

    @patch("requests.get")
    @patch("requests.head")
    def test_full_validation_workflow(self, mock_head, mock_get):
        """Test complete workflow from crawl to report"""
        # Mock site structure
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = '<a href="/page">Link</a>'
        mock_head.return_value.status_code = 200

        # Run validation
        results = validator.validate_site("https://example.com/")

        # Verify results structure
        assert "summary" in results
        assert "broken_links" in results
        assert "warnings" in results
        assert results["summary"]["total_pages"] >= 0

    def test_save_results_to_json(self, tmp_path):
        """Save results to JSON file"""
        results = {
            "summary": {"total_pages": 10, "total_links": 50},
            "broken_links": [],
            "warnings": [],
        }

        output_file = tmp_path / "test_results.json"
        validator.save_results(results, str(output_file))

        # Verify file exists and is valid JSON
        assert output_file.exists()
        with open(output_file) as f:
            loaded = json.load(f)
            assert loaded["summary"]["total_pages"] == 10


# ============================================================================
# E2E TESTS (10%) - Complete scenarios with minimal mocking
# ============================================================================

class TestRealWorldScenarios:
    """Test realistic scenarios (can be slow)"""

    @pytest.mark.slow
    def test_validate_simple_static_site(self):
        """Test against a simple HTML file (no external calls)"""
        # This would use a local test server or fixture HTML
        # Skipped in fast test runs
        pass

    def test_cli_argument_parsing(self):
        """Test CLI argument parsing"""
        args = validator.parse_args([
            "--site-url", "https://example.com",
            "--output", "results.json",
            "--timeout", "30"
        ])

        assert args.site_url == "https://example.com"
        assert args.output == "results.json"
        assert args.timeout == 30

    def test_exit_code_with_broken_links(self):
        """Exit code 1 when broken links found"""
        results = {
            "summary": {"broken_links": 5},
            "broken_links": [{"error": "404"}],
        }
        exit_code = validator.get_exit_code(results)
        assert exit_code == 1

    def test_exit_code_with_only_warnings(self):
        """Exit code 0 when only warnings"""
        results = {
            "summary": {"broken_links": 0, "warnings": 3},
            "warnings": [{"error": "Redirect"}],
        }
        exit_code = validator.get_exit_code(results)
        assert exit_code == 0


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_html():
    """Sample HTML for testing"""
    return """
    <html>
        <head><title>Test Page</title></head>
        <body>
            <a href="/page1">Internal Link</a>
            <a href="https://external.com">External Link</a>
            <a href="#section">Anchor</a>
        </body>
    </html>
    """


@pytest.fixture
def mock_response():
    """Mock HTTP response"""
    response = Mock()
    response.status_code = 200
    response.headers = {}
    response.text = "<html><body>Test</body></html>"
    return response


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
