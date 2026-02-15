"""
Test suite for link validator security controls.

This test suite defines the contract for security enhancements to
scripts/validate_gh_pages_links.py following Test-Driven Development methodology.
All tests will fail initially until security controls are implemented.

Test Coverage:
- Path traversal attack prevention
- SSRF (Server-Side Request Forgery) prevention
- Strict internal vs pragmatic external link validation
- Markdown injection detection
- URL scheme restrictions
- Timeout and redirect limits
"""

import socket
from unittest.mock import Mock, patch

import pytest

# These imports will fail initially - that's expected for TDD
try:
    from scripts.validate_gh_pages_links import (
        LinkValidationResult,
        LinkValidator,
        MarkdownInjectionError,
        PathTraversalError,
        SSRFError,
        ValidationMode,
    )
except ImportError:
    # Mark all tests as expected to fail until implementation exists
    pytestmark = pytest.mark.xfail(reason="Security enhancements not implemented yet")

    # Create placeholder classes for test structure
    class LinkValidator:
        pass

    class ValidationMode:
        STRICT = "strict"
        PRAGMATIC = "pragmatic"

    class LinkValidationResult:
        pass

    class PathTraversalError(Exception):
        pass

    class SSRFError(Exception):
        pass

    class MarkdownInjectionError(Exception):
        pass


class TestPathTraversalPrevention:
    """Test prevention of path traversal attacks in internal links."""

    def test_reject_parent_directory_traversal(self, tmp_path):
        """Should reject links that traverse to parent directories."""
        markdown = tmp_path / "docs" / "test.md"
        markdown.parent.mkdir(parents=True)
        markdown.write_text("""
# Test

[Dangerous link](../../etc/passwd)
""")

        validator = LinkValidator(base_path=tmp_path, mode=ValidationMode.STRICT)
        result = validator.validate_file(markdown)

        assert result.success is False
        assert any("path traversal" in str(err).lower() for err in result.errors)

    def test_reject_absolute_paths_in_internal_links(self, tmp_path):
        """Should reject absolute paths in internal links."""
        markdown = tmp_path / "docs" / "test.md"
        markdown.parent.mkdir(parents=True)
        markdown.write_text("""
# Test

[Absolute link](/etc/passwd)
[Another absolute](/root/.ssh/id_rsa)
""")

        validator = LinkValidator(base_path=tmp_path, mode=ValidationMode.STRICT)
        result = validator.validate_file(markdown)

        assert result.success is False
        assert len(result.errors) >= 2
        assert all("absolute path" in str(err).lower() for err in result.errors)

    def test_canonicalize_paths_with_resolve(self, tmp_path):
        """Should canonicalize all file paths using Path.resolve()."""
        # Create structure: docs/subdir/test.md
        subdir = tmp_path / "docs" / "subdir"
        subdir.mkdir(parents=True)

        # Create target file
        target = tmp_path / "docs" / "target.md"
        target.write_text("# Target")

        # Create markdown with tricky path
        markdown = subdir / "test.md"
        markdown.write_text("""
# Test

[Tricky link](./../../docs/./target.md)
""")

        validator = LinkValidator(base_path=tmp_path, mode=ValidationMode.STRICT)
        result = validator.validate_file(markdown)

        # Should resolve to actual path and validate correctly
        assert result.success is True

    def test_detect_symlink_escaping_repository(self, tmp_path):
        """Should detect symlinks pointing outside repository."""

        # Create symlink to /etc/passwd (outside repo)
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        try:
            symlink = docs_dir / "evil_link.md"
            symlink.symlink_to("/etc/passwd")
        except OSError:
            pytest.skip("Cannot create symlinks (Windows or permissions)")

        markdown = tmp_path / "test.md"
        markdown.write_text("""
# Test

[Link via symlink](docs/evil_link.md)
""")

        validator = LinkValidator(base_path=tmp_path, mode=ValidationMode.STRICT)
        result = validator.validate_file(markdown)

        assert result.success is False
        assert any(
            "symlink" in str(err).lower() or "outside repository" in str(err).lower()
            for err in result.errors
        )

    def test_validate_paths_stay_within_repository(self, tmp_path):
        """Should validate paths stay within repository using is_relative_to()."""
        markdown = tmp_path / "docs" / "test.md"
        markdown.parent.mkdir(parents=True)

        # Create valid target outside docs/ but inside repo
        valid_target = tmp_path / "README.md"
        valid_target.write_text("# README")

        markdown.write_text("""
# Test

[Valid internal link](../README.md)
""")

        validator = LinkValidator(base_path=tmp_path, mode=ValidationMode.STRICT)
        result = validator.validate_file(markdown)

        # Should pass - file is within repository
        assert result.success is True

    def test_reject_file_protocol_urls(self, tmp_path):
        """Should reject file:// protocol URLs."""
        markdown = tmp_path / "test.md"
        markdown.write_text("""
# Test

[File protocol](file:///etc/passwd)
[File protocol Windows](file:///C:/Windows/System32/config/SAM)
""")

        validator = LinkValidator(base_path=tmp_path)
        result = validator.validate_file(markdown)

        assert result.success is False
        assert any(
            "file://" in str(err).lower() or "unsupported protocol" in str(err).lower()
            for err in result.errors
        )


class TestSSRFPrevention:
    """Test prevention of Server-Side Request Forgery attacks."""

    def test_block_localhost_urls(self, tmp_path):
        """Should block requests to localhost."""
        localhost_variants = [
            "http://localhost/admin",
            "http://127.0.0.1/admin",
            "http://127.0.0.2/secret",
            "http://[::1]/admin",
            "http://0.0.0.0/admin",
        ]

        validator = LinkValidator(base_path=tmp_path, mode=ValidationMode.PRAGMATIC)

        for url in localhost_variants:
            markdown = tmp_path / f"test_{hash(url)}.md"
            markdown.write_text(f"[Link]({url})")

            result = validator.validate_file(markdown)
            assert result.success is False, f"Should block: {url}"
            assert any(
                "private network" in str(err).lower() or "ssrf" in str(err).lower()
                for err in result.errors
            )

    def test_block_private_network_ranges(self, tmp_path):
        """Should block requests to private network ranges."""
        private_ips = [
            "http://10.0.0.1/admin",  # 10.0.0.0/8
            "http://172.16.0.1/admin",  # 172.16.0.0/12
            "http://192.168.1.1/admin",  # 192.168.0.0/16
            "http://169.254.169.254/metadata",  # Link-local (AWS metadata)
        ]

        validator = LinkValidator(base_path=tmp_path, mode=ValidationMode.PRAGMATIC)

        for url in private_ips:
            markdown = tmp_path / f"test_{hash(url)}.md"
            markdown.write_text(f"[Link]({url})")

            result = validator.validate_file(markdown)
            assert result.success is False, f"Should block: {url}"
            assert any("private network" in str(err).lower() for err in result.errors)

    def test_block_dns_rebinding_attack(self, tmp_path):
        """Should resolve DNS and block if it points to private IP."""
        markdown = tmp_path / "test.md"
        markdown.write_text("[Link](http://malicious.example.com/)")

        # Mock DNS resolution to return private IP
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.1", 80))
            ]

            validator = LinkValidator(base_path=tmp_path, mode=ValidationMode.PRAGMATIC)
            result = validator.validate_file(markdown)

            assert result.success is False
            assert any(
                "private network" in str(err).lower() or "dns" in str(err).lower()
                for err in result.errors
            )

    def test_allow_public_urls(self, tmp_path):
        """Should allow requests to public URLs."""
        public_urls = [
            "https://github.com/org/repo",
            "https://docs.python.org/3/",
            "https://www.example.com/",
        ]

        validator = LinkValidator(base_path=tmp_path, mode=ValidationMode.PRAGMATIC)

        for url in public_urls:
            markdown = tmp_path / f"test_{hash(url)}.md"
            markdown.write_text(f"[Link]({url})")

            with patch("requests.head") as mock_request:
                mock_request.return_value = Mock(status_code=200)

                result = validator.validate_file(markdown)
                assert result.success is True, f"Should allow: {url}"

    def test_enforce_timeout_on_external_requests(self, tmp_path):
        """Should enforce 10-second timeout on external requests."""
        markdown = tmp_path / "test.md"
        markdown.write_text("[Link](https://slow-site.example.com/)")

        validator = LinkValidator(base_path=tmp_path, mode=ValidationMode.PRAGMATIC)

        with patch("requests.head") as mock_request:
            import requests

            mock_request.side_effect = requests.Timeout("Request timed out")

            result = validator.validate_file(markdown)

            # In PRAGMATIC mode, timeouts should generate warnings, not failures
            assert result.success is True
            assert any("timeout" in str(warn).lower() for warn in result.warnings)

            # Verify timeout was set to 10 seconds
            mock_request.assert_called()
            call_kwargs = mock_request.call_args[1]
            assert call_kwargs.get("timeout") == 10

    def test_limit_redirects_to_3(self, tmp_path):
        """Should limit redirect following to maximum 3 redirects."""
        markdown = tmp_path / "test.md"
        markdown.write_text("[Link](https://redirect-loop.example.com/)")

        validator = LinkValidator(base_path=tmp_path, mode=ValidationMode.PRAGMATIC)

        with patch("requests.head") as mock_request:
            import requests

            mock_request.side_effect = requests.TooManyRedirects("Too many redirects")

            result = validator.validate_file(markdown)

            # Should fail or warn about redirect limit
            assert result.success is False or len(result.warnings) > 0

            # Verify max_redirects was set to 3
            call_kwargs = mock_request.call_args[1]
            assert call_kwargs.get("allow_redirects") is True
            assert call_kwargs.get("max_redirects") == 3

    def test_enforce_ssl_certificate_validation(self, tmp_path):
        """Should enforce SSL certificate validation."""
        markdown = tmp_path / "test.md"
        markdown.write_text("[Link](https://self-signed.example.com/)")

        validator = LinkValidator(base_path=tmp_path, mode=ValidationMode.PRAGMATIC)

        with patch("requests.head") as mock_request:
            import requests

            mock_request.side_effect = requests.exceptions.SSLError("SSL verification failed")

            result = validator.validate_file(markdown)

            # SSL errors should generate warnings in PRAGMATIC mode
            assert any(
                "ssl" in str(warn).lower() or "certificate" in str(warn).lower()
                for warn in result.warnings
            )

            # Verify SSL verification was enabled
            call_kwargs = mock_request.call_args[1]
            assert call_kwargs.get("verify") is not False  # Should be True or path to CA bundle

    def test_only_allow_http_https_schemes(self, tmp_path):
        """Should only allow http:// and https:// schemes for external links."""
        invalid_schemes = [
            "ftp://files.example.com/file.txt",
            "javascript:alert('XSS')",
            "data:text/html,<script>alert('XSS')</script>",
            "file:///etc/passwd",
            "gopher://old-protocol.com/",
        ]

        validator = LinkValidator(base_path=tmp_path)

        for url in invalid_schemes:
            markdown = tmp_path / f"test_{hash(url)}.md"
            markdown.write_text(f"[Link]({url})")

            result = validator.validate_file(markdown)
            assert result.success is False, f"Should reject: {url}"
            assert any(
                "scheme" in str(err).lower() or "protocol" in str(err).lower()
                for err in result.errors
            )


class TestStrictVsPragmaticModes:
    """Test strict internal vs pragmatic external link validation."""

    def test_strict_mode_fails_on_missing_internal_file(self, tmp_path):
        """STRICT mode: missing internal file should fail."""
        markdown = tmp_path / "test.md"
        markdown.write_text("[Missing](./nonexistent.md)")

        validator = LinkValidator(base_path=tmp_path, mode=ValidationMode.STRICT)
        result = validator.validate_file(markdown)

        assert result.success is False
        assert any("not found" in str(err).lower() for err in result.errors)

    def test_strict_mode_fails_on_missing_anchor(self, tmp_path):
        """STRICT mode: missing anchor in internal file should fail."""
        target = tmp_path / "target.md"
        target.write_text("""
# Existing Header

Content here.
""")

        markdown = tmp_path / "test.md"
        markdown.write_text("[Link](./target.md#nonexistent-header)")

        validator = LinkValidator(base_path=tmp_path, mode=ValidationMode.STRICT)
        result = validator.validate_file(markdown)

        assert result.success is False
        assert any(
            "anchor" in str(err).lower() or "header" in str(err).lower() for err in result.errors
        )

    def test_strict_mode_case_sensitive_validation(self, tmp_path):
        """STRICT mode: should enforce case-sensitive file names."""
        target = tmp_path / "Target.md"
        target.write_text("# Target")

        markdown = tmp_path / "test.md"
        markdown.write_text("[Link](./target.md)")  # lowercase, but file is uppercase

        validator = LinkValidator(base_path=tmp_path, mode=ValidationMode.STRICT)
        result = validator.validate_file(markdown)

        # On case-sensitive filesystems, should fail
        # On case-insensitive (Windows/macOS), might pass - that's OK
        if not (tmp_path / "target.md").exists():
            assert result.success is False

    def test_pragmatic_mode_blocks_404_external_links(self, tmp_path):
        """PRAGMATIC mode: 404 on external links should fail."""
        markdown = tmp_path / "test.md"
        markdown.write_text("[Broken](https://example.com/nonexistent)")

        validator = LinkValidator(base_path=tmp_path, mode=ValidationMode.PRAGMATIC)

        with patch("requests.head") as mock_request:
            mock_request.return_value = Mock(status_code=404)

            result = validator.validate_file(markdown)

            assert result.success is False
            assert any("404" in str(err) for err in result.errors)

    def test_pragmatic_mode_blocks_410_gone(self, tmp_path):
        """PRAGMATIC mode: 410 Gone should fail."""
        markdown = tmp_path / "test.md"
        markdown.write_text("[Gone](https://example.com/deleted)")

        validator = LinkValidator(base_path=tmp_path, mode=ValidationMode.PRAGMATIC)

        with patch("requests.head") as mock_request:
            mock_request.return_value = Mock(status_code=410)

            result = validator.validate_file(markdown)

            assert result.success is False
            assert any("410" in str(err) or "gone" in str(err).lower() for err in result.errors)

    def test_pragmatic_mode_warns_on_5xx_errors(self, tmp_path):
        """PRAGMATIC mode: 5xx server errors should warn, not fail."""
        markdown = tmp_path / "test.md"
        markdown.write_text("[Temporarily down](https://example.com/)")

        validator = LinkValidator(base_path=tmp_path, mode=ValidationMode.PRAGMATIC)

        with patch("requests.head") as mock_request:
            mock_request.return_value = Mock(status_code=503)

            result = validator.validate_file(markdown)

            # Should succeed with warning
            assert result.success is True
            assert any(
                "503" in str(warn) or "unavailable" in str(warn).lower() for warn in result.warnings
            )

    def test_pragmatic_mode_warns_on_timeout(self, tmp_path):
        """PRAGMATIC mode: timeouts should warn, not fail."""
        markdown = tmp_path / "test.md"
        markdown.write_text("[Slow site](https://slow.example.com/)")

        validator = LinkValidator(base_path=tmp_path, mode=ValidationMode.PRAGMATIC)

        with patch("requests.head") as mock_request:
            import requests

            mock_request.side_effect = requests.Timeout("Timed out")

            result = validator.validate_file(markdown)

            # Should succeed with warning
            assert result.success is True
            assert any("timeout" in str(warn).lower() for warn in result.warnings)

    def test_pragmatic_mode_accepts_2xx_3xx(self, tmp_path):
        """PRAGMATIC mode: 2xx and 3xx status codes should pass."""
        success_codes = [200, 201, 204, 301, 302, 304]

        validator = LinkValidator(base_path=tmp_path, mode=ValidationMode.PRAGMATIC)

        for status_code in success_codes:
            markdown = tmp_path / f"test_{status_code}.md"
            markdown.write_text(f"[Link](https://example.com/{status_code})")

            with patch("requests.head") as mock_request:
                mock_request.return_value = Mock(status_code=status_code)

                result = validator.validate_file(markdown)
                assert result.success is True, f"Should pass for status {status_code}"


class TestMarkdownInjection:
    """Test detection of markdown injection attempts."""

    def test_detect_script_tags(self, tmp_path):
        """Should detect <script> tags in markdown."""
        markdown = tmp_path / "test.md"
        markdown.write_text("""
# Test

<script>alert('XSS')</script>

Normal content.
""")

        validator = LinkValidator(base_path=tmp_path)
        result = validator.validate_file(markdown)

        assert result.success is False
        assert any(
            "script" in str(err).lower() or "injection" in str(err).lower() for err in result.errors
        )

    def test_detect_iframe_tags(self, tmp_path):
        """Should detect <iframe> tags in markdown."""
        markdown = tmp_path / "test.md"
        markdown.write_text("""
# Test

<iframe src="https://malicious.com/"></iframe>
""")

        validator = LinkValidator(base_path=tmp_path)
        result = validator.validate_file(markdown)

        assert result.success is False
        assert any(
            "iframe" in str(err).lower() or "injection" in str(err).lower() for err in result.errors
        )

    def test_detect_javascript_protocol(self, tmp_path):
        """Should detect javascript: protocol in links."""
        markdown = tmp_path / "test.md"
        markdown.write_text("""
# Test

[Click me](javascript:alert('XSS'))
""")

        validator = LinkValidator(base_path=tmp_path)
        result = validator.validate_file(markdown)

        assert result.success is False
        assert any(
            "javascript" in str(err).lower() or "protocol" in str(err).lower()
            for err in result.errors
        )

    def test_detect_event_handlers(self, tmp_path):
        """Should detect event handlers (onclick, onerror, etc.)."""
        event_handlers = [
            '<img src="x" onerror="alert(1)">',
            '<div onclick="malicious()">Click</div>',
            '<body onload="stealData()">',
            '<input onfocus="exploit()">',
        ]

        validator = LinkValidator(base_path=tmp_path)

        for handler in event_handlers:
            markdown = tmp_path / f"test_{hash(handler)}.md"
            markdown.write_text(f"# Test\n\n{handler}")

            result = validator.validate_file(markdown)
            assert result.success is False, f"Should detect: {handler}"
            assert any(
                "event handler" in str(err).lower() or "on" in str(err).lower()
                for err in result.errors
            )

    def test_detect_data_protocol(self, tmp_path):
        """Should detect data: protocol URLs."""
        markdown = tmp_path / "test.md"
        markdown.write_text("""
[Link](data:text/html,<script>alert('XSS')</script>)
""")

        validator = LinkValidator(base_path=tmp_path)
        result = validator.validate_file(markdown)

        assert result.success is False
        assert any(
            "data:" in str(err).lower() or "protocol" in str(err).lower() for err in result.errors
        )

    def test_allow_safe_html_in_markdown(self, tmp_path):
        """Should allow safe HTML tags like <strong>, <em>, <code>."""
        markdown = tmp_path / "test.md"
        markdown.write_text("""
# Test

This is <strong>bold</strong> and <em>italic</em>.

Inline <code>code</code> is fine.

<table>
  <tr><td>Tables are OK</td></tr>
</table>
""")

        validator = LinkValidator(base_path=tmp_path)
        result = validator.validate_file(markdown)

        # Safe HTML should not trigger injection warnings
        assert result.success is True or not any(
            "injection" in str(err).lower() for err in result.errors
        )


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_markdown_file(self, tmp_path):
        """Should handle empty markdown files gracefully."""
        markdown = tmp_path / "empty.md"
        markdown.write_text("")

        validator = LinkValidator(base_path=tmp_path)
        result = validator.validate_file(markdown)

        assert result.success is True
        assert result.links_validated == 0

    def test_markdown_with_no_links(self, tmp_path):
        """Should handle markdown with no links."""
        markdown = tmp_path / "text.md"
        markdown.write_text("""
# Just Text

This is a markdown file with no links.
Just plain text and headers.
""")

        validator = LinkValidator(base_path=tmp_path)
        result = validator.validate_file(markdown)

        assert result.success is True
        assert result.links_validated == 0

    def test_mixed_valid_and_invalid_links(self, tmp_path):
        """Should report all errors when mix of valid/invalid links."""
        valid_target = tmp_path / "valid.md"
        valid_target.write_text("# Valid")

        markdown = tmp_path / "test.md"
        markdown.write_text("""
# Test

[Valid link](./valid.md)
[Broken link](./nonexistent.md)
[Another valid](./valid.md#valid)
[Another broken](./missing.md)
""")

        validator = LinkValidator(base_path=tmp_path, mode=ValidationMode.STRICT)
        result = validator.validate_file(markdown)

        assert result.success is False
        assert len(result.errors) == 2  # Two broken links
        assert result.links_validated == 4  # All 4 links were checked

    def test_unicode_in_links(self, tmp_path):
        """Should handle Unicode characters in links."""
        target = tmp_path / "文档.md"
        target.write_text("# 文档")

        markdown = tmp_path / "test.md"
        markdown.write_text("[中文链接](./文档.md)")

        validator = LinkValidator(base_path=tmp_path, mode=ValidationMode.STRICT)
        result = validator.validate_file(markdown)

        assert result.success is True

    def test_url_encoded_links(self, tmp_path):
        """Should handle URL-encoded links."""
        target = tmp_path / "file with spaces.md"
        target.write_text("# File")

        markdown = tmp_path / "test.md"
        markdown.write_text("[Link](./file%20with%20spaces.md)")

        validator = LinkValidator(base_path=tmp_path, mode=ValidationMode.STRICT)
        result = validator.validate_file(markdown)

        assert result.success is True

    def test_relative_links_with_current_directory(self, tmp_path):
        """Should handle ./ prefix in relative links."""
        target = tmp_path / "target.md"
        target.write_text("# Target")

        markdown = tmp_path / "test.md"
        markdown.write_text("""
[With dot slash](./target.md)
[Without dot slash](target.md)
""")

        validator = LinkValidator(base_path=tmp_path, mode=ValidationMode.STRICT)
        result = validator.validate_file(markdown)

        assert result.success is True
        assert result.links_validated == 2

    def test_anchor_only_links(self, tmp_path):
        """Should validate anchor-only links (same file)."""
        markdown = tmp_path / "test.md"
        markdown.write_text("""
# Heading One

Content here.

## Heading Two

More content.

[Link to heading two](#heading-two)
[Link to heading one](#heading-one)
[Broken anchor](#nonexistent)
""")

        validator = LinkValidator(base_path=tmp_path, mode=ValidationMode.STRICT)
        result = validator.validate_file(markdown)

        assert result.success is False  # One broken anchor
        assert len(result.errors) == 1
        assert "#nonexistent" in str(result.errors[0])


class TestCLIInterface:
    """Test command-line interface enhancements."""

    def test_cli_strict_mode_flag(self, tmp_path):
        """Should support --strict mode for internal links."""
        markdown = tmp_path / "test.md"
        markdown.write_text("[Broken](./missing.md)")

        result = subprocess.run(
            ["python", "scripts/validate_gh_pages_links.py", "--strict", str(markdown)],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "strict" in result.stdout.lower() or "internal" in result.stdout.lower()

    def test_cli_pragmatic_mode_flag(self, tmp_path):
        """Should support --pragmatic mode for external links."""
        markdown = tmp_path / "test.md"
        markdown.write_text("[External](https://example.com/)")

        with patch("requests.head") as mock_request:
            mock_request.return_value = Mock(status_code=503)

            result = subprocess.run(
                ["python", "scripts/validate_gh_pages_links.py", "--pragmatic", str(markdown)],
                capture_output=True,
                text=True,
            )

            # 503 should warn but not fail in pragmatic mode
            assert result.returncode == 0
            assert "warning" in result.stdout.lower()

    def test_cli_skip_external_flag(self, tmp_path):
        """Should support --skip-external flag."""
        markdown = tmp_path / "test.md"
        markdown.write_text("""
[Internal](./README.md)
[External](https://example.com/)
""")

        (tmp_path / "README.md").write_text("# README")

        result = subprocess.run(
            ["python", "scripts/validate_gh_pages_links.py", "--skip-external", str(markdown)],
            capture_output=True,
            text=True,
        )

        # Should only check internal link
        assert result.returncode == 0
        assert "skipped" in result.stdout.lower() or "external" in result.stdout.lower()

    def test_cli_timeout_configuration(self, tmp_path):
        """Should support --timeout flag."""
        markdown = tmp_path / "test.md"
        markdown.write_text("[Link](https://example.com/)")

        result = subprocess.run(
            ["python", "scripts/validate_gh_pages_links.py", "--timeout", "5", str(markdown)],
            capture_output=True,
            text=True,
        )

        # Should accept timeout configuration
        assert "--timeout" not in result.stderr  # No error about unknown flag


class TestValidationResult:
    """Test LinkValidationResult data structure."""

    def test_result_distinguishes_errors_and_warnings(self):
        """Should distinguish between errors (fail) and warnings (pass with info)."""
        result = LinkValidationResult(
            success=True,
            links_validated=5,
            errors=[],
            warnings=["External link timeout: https://slow.example.com/"],
        )

        assert result.success is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 1

    def test_result_includes_mode_information(self):
        """Should include validation mode in results."""
        result = LinkValidationResult(
            success=True, links_validated=10, mode=ValidationMode.STRICT, errors=[], warnings=[]
        )

        assert result.mode == ValidationMode.STRICT

    def test_result_json_serializable(self):
        """Should be JSON serializable for CI/CD integration."""
        import json

        result = LinkValidationResult(
            success=False,
            links_validated=5,
            mode=ValidationMode.STRICT,
            errors=["Missing file: ./nonexistent.md"],
            warnings=[],
        )

        json_str = json.dumps(result.to_dict())
        assert isinstance(json_str, str)

        data = json.loads(json_str)
        assert data["success"] is False
        assert data["mode"] == "strict"


# Import subprocess for CLI tests
import subprocess
