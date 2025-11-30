"""Tests for security features including SSRF protection."""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from rest_api_client.security import SSRFProtector


class TestSSRFProtector(unittest.TestCase):
    """Test SSRF protection features."""

    def setUp(self):
        """Set up test fixtures."""
        self.protector = SSRFProtector()

    def test_blocks_localhost(self):
        """Test that localhost URLs are blocked."""
        unsafe_urls = [
            "http://localhost/api",
            "http://127.0.0.1/api",
            "http://[::1]/api",
            "https://localhost:8080/api",
            "http://LOCALHOST/api",  # Case insensitive
        ]

        for url in unsafe_urls:
            with self.subTest(url=url):
                self.assertFalse(self.protector.is_safe_url(url), f"Should block {url}")

    def test_blocks_private_ips(self):
        """Test that private IP ranges are blocked."""
        unsafe_urls = [
            "http://10.0.0.1/api",
            "http://192.168.1.1/api",
            "http://172.16.0.1/api",
            "http://172.31.255.255/api",
            "http://169.254.1.1/api",  # Link-local
            "http://[fc00::1]/api",  # IPv6 private
        ]

        for url in unsafe_urls:
            with self.subTest(url=url):
                self.assertFalse(self.protector.is_safe_url(url), f"Should block {url}")

    def test_allows_public_urls(self):
        """Test that public URLs are allowed."""
        safe_urls = [
            "https://api.github.com/users",
            "https://www.google.com/search",
            "http://example.com/api",
            "https://8.8.8.8/dns",  # Public DNS
        ]

        # Mock socket.gethostbyname to return public IPs
        with patch("socket.gethostbyname") as mock_resolve:
            mock_resolve.side_effect = [
                "140.82.112.5",  # github.com
                "142.250.80.46",  # google.com
                "93.184.216.34",  # example.com
                "8.8.8.8",  # Already an IP
            ]

            for url in safe_urls:
                with self.subTest(url=url):
                    self.assertTrue(self.protector.is_safe_url(url), f"Should allow {url}")

    def test_blocks_dns_rebinding(self):
        """Test protection against DNS rebinding attacks."""
        # URL that looks safe but resolves to internal IP
        url = "http://evil.example.com/api"

        with patch("socket.gethostbyname") as mock_resolve:
            # Resolves to internal IP
            mock_resolve.return_value = "192.168.1.1"

            self.assertFalse(
                self.protector.is_safe_url(url), "Should block URLs resolving to internal IPs"
            )

    def test_blocks_unresolvable_hosts(self):
        """Test that unresolvable hosts are blocked."""
        import socket

        url = "http://nonexistent.invalid/api"

        with patch("socket.gethostbyname") as mock_resolve:
            mock_resolve.side_effect = socket.gaierror("Name resolution failed")

            self.assertFalse(self.protector.is_safe_url(url), "Should block unresolvable hosts")

    def test_custom_blocklist(self):
        """Test custom blocklist functionality."""
        protector = SSRFProtector(additional_blocked_hosts=["api.internal.com", "secret.service"])

        self.assertFalse(
            protector.is_safe_url("http://api.internal.com/data"),
            "Should block custom blocked hosts",
        )

    def test_custom_allowlist_overrides(self):
        """Test that allowlist overrides blocklist."""
        protector = SSRFProtector(allowed_hosts=["trusted.local", "10.0.0.5"])

        # These would normally be blocked but are explicitly allowed
        self.assertTrue(
            protector.is_safe_url("http://trusted.local/api"),
            "Should allow explicitly allowed hosts",
        )

        self.assertTrue(
            protector.is_safe_url("http://10.0.0.5/api"), "Should allow explicitly allowed IPs"
        )


class TestResponseSizeLimits(unittest.TestCase):
    """Test response size limiting features."""

    def test_content_length_check(self):
        """Test that Content-Length is checked before downloading."""
        from rest_api_client.transport import HTTPTransport

        transport = HTTPTransport(max_response_size=1024)  # 1KB limit

        mock_response = MagicMock()
        mock_response.headers = {"Content-Length": "2048"}  # 2KB

        with patch("urllib.request.urlopen", return_value=mock_response):
            with self.assertRaises(ValueError) as ctx:
                transport.request("GET", "http://example.com/large")

            self.assertIn("too large", str(ctx.exception).lower())

    def test_streaming_size_limit(self):
        """Test size limit during streaming."""
        from rest_api_client.transport import HTTPTransport

        transport = HTTPTransport(max_response_size=100)  # 100 bytes

        mock_response = MagicMock()
        mock_response.headers = {}  # No Content-Length
        mock_response.getcode.return_value = 200

        # Simulate large response in chunks
        chunks = [b"X" * 50, b"Y" * 50, b"Z" * 50]  # 150 bytes total
        mock_response.read.side_effect = chunks + [b""]

        with patch("urllib.request.urlopen", return_value=mock_response):
            with self.assertRaises(ValueError) as ctx:
                transport.request("GET", "http://example.com/stream")

            self.assertIn("exceeded", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
