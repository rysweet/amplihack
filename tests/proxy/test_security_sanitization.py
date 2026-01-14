"""Tests for token sanitization security module.

Testing pyramid:
- 60% Unit tests (fast, heavily mocked)
- 30% Integration tests (multiple components)
- 10% E2E tests (complete workflows)

These tests define the expected behavior for the security.py module
that will be implemented in src/amplihack/proxy/security.py
"""

import time
from typing import Any, Dict, List

import pytest

from amplihack.proxy.security import TokenSanitizer

# ============================================================================
# UNIT TESTS (60%) - Pattern Detection & Basic Sanitization
# ============================================================================


class TestTokenPatternDetection:
    """Test token pattern detection for various token types."""

    def test_github_token_detection(self):
        """Test detection of GitHub tokens (gho_, ghp_, ghs_, etc.)."""
        sanitizer = TokenSanitizer()

        # GitHub OAuth tokens
        assert sanitizer.contains_token("gho_1234567890abcdefghij")
        assert sanitizer.contains_token("Bearer gho_1234567890abcdefghij")

        # GitHub PAT tokens
        assert sanitizer.contains_token("ghp_1234567890abcdefghij")
        assert sanitizer.contains_token("Authorization: ghp_test123")

        # GitHub App tokens
        assert sanitizer.contains_token("ghs_1234567890abcdefghij")

        # Non-tokens should not match
        assert not sanitizer.contains_token("github oauth token")
        assert not sanitizer.contains_token("no tokens here")

    def test_openai_token_detection(self):
        """Test detection of OpenAI API keys."""
        sanitizer = TokenSanitizer()

        # Valid OpenAI keys
        assert sanitizer.contains_token("sk-1234567890abcdefghij")
        assert sanitizer.contains_token("sk-proj-1234567890abcdefghij")

        # With prefixes
        assert sanitizer.contains_token("OPENAI_API_KEY=sk-test123")
        assert sanitizer.contains_token("Bearer sk-1234567890")

        # Non-tokens
        assert not sanitizer.contains_token("openai key")
        assert not sanitizer.contains_token("sk-short")

    def test_anthropic_token_detection(self):
        """Test detection of Anthropic API keys."""
        sanitizer = TokenSanitizer()

        # Valid Anthropic keys
        assert sanitizer.contains_token("sk-ant-1234567890abcdefghij")
        assert sanitizer.contains_token("x-api-key: sk-ant-test123")

        # Non-tokens
        assert not sanitizer.contains_token("anthropic key")
        assert not sanitizer.contains_token("sk-ant-short")

    def test_bearer_token_detection(self):
        """Test detection of generic Bearer tokens."""
        sanitizer = TokenSanitizer()

        # Valid Bearer tokens
        assert sanitizer.contains_token("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")
        assert sanitizer.contains_token("Authorization: Bearer abc123xyz")

        # Non-tokens
        assert not sanitizer.contains_token("Bearer")
        assert not sanitizer.contains_token("Bearer short")

    def test_jwt_token_detection(self):
        """Test detection of JWT tokens."""
        sanitizer = TokenSanitizer()

        # Valid JWT structure (header.payload.signature)
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        assert sanitizer.contains_token(jwt)

        # With Bearer prefix
        assert sanitizer.contains_token(f"Bearer {jwt}")

        # Non-JWT
        assert not sanitizer.contains_token("not.a.jwt")

    def test_azure_token_detection(self):
        """Test detection of Azure tokens."""
        sanitizer = TokenSanitizer()

        # Azure subscription keys
        assert sanitizer.contains_token("azure-key-1234567890abcdefghij")

        # Azure connection strings
        assert sanitizer.contains_token("DefaultEndpointsProtocol=https;AccountName=test;AccountKey=abc123==;EndpointSuffix=core.windows.net")


class TestStringSanitization:
    """Test sanitization of string data."""

    def test_sanitize_simple_string(self):
        """Test sanitizing strings containing tokens."""
        sanitizer = TokenSanitizer()

        # GitHub token
        result = sanitizer.sanitize("My token is gho_1234567890abcdefghij")
        assert "gho_1234567890abcdefghij" not in result
        assert "[REDACTED-GITHUB-TOKEN]" in result

        # OpenAI token
        result = sanitizer.sanitize("API key: sk-1234567890abcdefghij")
        assert "sk-1234567890abcdefghij" not in result
        assert "[REDACTED-OPENAI-KEY]" in result

    def test_sanitize_multiple_tokens(self):
        """Test sanitizing strings with multiple different tokens."""
        sanitizer = TokenSanitizer()

        text = "GitHub: gho_abc123 OpenAI: sk-xyz789"
        result = sanitizer.sanitize(text)

        assert "gho_abc123" not in result
        assert "sk-xyz789" not in result
        assert "[REDACTED-GITHUB-TOKEN]" in result
        assert "[REDACTED-OPENAI-KEY]" in result

    def test_sanitize_preserves_non_tokens(self):
        """Test that non-sensitive text is preserved."""
        sanitizer = TokenSanitizer()

        text = "This is safe text with no tokens"
        result = sanitizer.sanitize(text)
        assert result == text

    def test_sanitize_empty_string(self):
        """Test sanitizing empty strings."""
        sanitizer = TokenSanitizer()
        assert sanitizer.sanitize("") == ""

    def test_sanitize_none(self):
        """Test sanitizing None values."""
        sanitizer = TokenSanitizer()
        assert sanitizer.sanitize(None) is None


class TestDictSanitization:
    """Test sanitization of dictionary data structures."""

    def test_sanitize_flat_dict(self):
        """Test sanitizing flat dictionaries."""
        sanitizer = TokenSanitizer()

        data = {
            "api_key": "sk-1234567890abcdefghij",
            "github_token": "gho_abc123xyz",
            "safe_field": "no tokens here"
        }

        result = sanitizer.sanitize(data)

        assert "sk-1234567890abcdefghij" not in str(result)
        assert "gho_abc123xyz" not in str(result)
        assert result["safe_field"] == "no tokens here"

    def test_sanitize_nested_dict(self):
        """Test sanitizing nested dictionaries."""
        sanitizer = TokenSanitizer()

        data = {
            "config": {
                "auth": {
                    "token": "gho_nested123"
                },
                "api_key": "sk-nested456"
            },
            "name": "test"
        }

        result = sanitizer.sanitize(data)

        assert "gho_nested123" not in str(result)
        assert "sk-nested456" not in str(result)
        assert result["name"] == "test"

    def test_sanitize_dict_with_list_values(self):
        """Test sanitizing dictionaries with list values."""
        sanitizer = TokenSanitizer()

        data = {
            "tokens": ["gho_abc123", "sk-xyz789"],
            "safe_list": ["item1", "item2"]
        }

        result = sanitizer.sanitize(data)

        assert "gho_abc123" not in str(result)
        assert "sk-xyz789" not in str(result)
        assert result["safe_list"] == ["item1", "item2"]

    def test_sanitize_empty_dict(self):
        """Test sanitizing empty dictionaries."""
        sanitizer = TokenSanitizer()
        result = sanitizer.sanitize({})
        assert result == {}


class TestListSanitization:
    """Test sanitization of list data structures."""

    def test_sanitize_flat_list(self):
        """Test sanitizing flat lists."""
        sanitizer = TokenSanitizer()

        data = ["gho_abc123", "safe text", "sk-xyz789"]
        result = sanitizer.sanitize(data)

        assert "gho_abc123" not in str(result)
        assert "sk-xyz789" not in str(result)
        assert "safe text" in result

    def test_sanitize_nested_list(self):
        """Test sanitizing nested lists."""
        sanitizer = TokenSanitizer()

        data = [["gho_abc123", "safe"], ["sk-xyz789"]]
        result = sanitizer.sanitize(data)

        assert "gho_abc123" not in str(result)
        assert "sk-xyz789" not in str(result)
        assert "safe" in str(result)

    def test_sanitize_list_of_dicts(self):
        """Test sanitizing lists containing dictionaries."""
        sanitizer = TokenSanitizer()

        data = [
            {"token": "gho_abc123", "name": "test1"},
            {"token": "sk-xyz789", "name": "test2"}
        ]

        result = sanitizer.sanitize(data)

        assert "gho_abc123" not in str(result)
        assert "sk-xyz789" not in str(result)
        assert any("test1" in str(item) for item in result)

    def test_sanitize_empty_list(self):
        """Test sanitizing empty lists."""
        sanitizer = TokenSanitizer()
        result = sanitizer.sanitize([])
        assert result == []


# ============================================================================
# INTEGRATION TESTS (30%) - Real Error Scenarios & Edge Cases
# ============================================================================


class TestRealErrorScenarios:
    """Test sanitization in real error scenarios from Issue #1920."""

    def test_sanitize_github_api_error(self):
        """Test sanitizing GitHub API error messages."""
        sanitizer = TokenSanitizer()

        error_msg = """
        HTTP 401 Unauthorized
        Request headers:
            Authorization: Bearer gho_1234567890abcdefghij
            X-GitHub-Api-Version: 2023-11-15
        Response: {"message": "Bad credentials"}
        """

        result = sanitizer.sanitize(error_msg)

        assert "gho_1234567890abcdefghij" not in result
        assert "[REDACTED-GITHUB-TOKEN]" in result
        assert "Bad credentials" in result

    def test_sanitize_openai_api_error(self):
        """Test sanitizing OpenAI API error messages."""
        sanitizer = TokenSanitizer()

        error_msg = """
        OpenAI API Error 401
        Headers: {'Authorization': 'Bearer sk-1234567890abcdefghij'}
        Body: {"error": {"message": "Incorrect API key provided"}}
        """

        result = sanitizer.sanitize(error_msg)

        assert "sk-1234567890abcdefghij" not in result
        assert "[REDACTED-OPENAI-KEY]" in result
        assert "Incorrect API key" in result

    def test_sanitize_anthropic_api_error(self):
        """Test sanitizing Anthropic API error messages."""
        sanitizer = TokenSanitizer()

        error_msg = """
        Anthropic API Error 401
        Headers: {'x-api-key': 'sk-ant-1234567890abcdefghij'}
        Response: {"error": {"type": "authentication_error"}}
        """

        result = sanitizer.sanitize(error_msg)

        assert "sk-ant-1234567890abcdefghij" not in result
        assert "[REDACTED-ANTHROPIC-KEY]" in result
        assert "authentication_error" in result

    def test_sanitize_mixed_error_trace(self):
        """Test sanitizing error traces with multiple token types."""
        sanitizer = TokenSanitizer()

        trace = """
        Traceback (most recent call last):
          File "proxy/server.py", line 123
            github_auth = "gho_abc123"
            openai_key = "sk-xyz789"
            anthropic_key = "sk-ant-test456"
        ConnectionError: Multiple API authentication failures
        """

        result = sanitizer.sanitize(trace)

        assert "gho_abc123" not in result
        assert "sk-xyz789" not in result
        assert "sk-ant-test456" not in result
        assert "ConnectionError" in result

    def test_sanitize_json_response(self):
        """Test sanitizing JSON responses containing tokens."""
        sanitizer = TokenSanitizer()

        json_data = {
            "error": "Authentication failed",
            "request": {
                "headers": {
                    "Authorization": "Bearer gho_1234567890",
                    "X-API-Key": "sk-test123"
                }
            },
            "timestamp": "2024-01-14T12:00:00Z"
        }

        result = sanitizer.sanitize(json_data)

        assert "gho_1234567890" not in str(result)
        assert "sk-test123" not in str(result)
        assert result["error"] == "Authentication failed"
        assert result["timestamp"] == "2024-01-14T12:00:00Z"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_sanitize_very_long_string(self):
        """Test sanitizing very long strings."""
        sanitizer = TokenSanitizer()

        # 10KB string with token embedded
        long_text = "x" * 5000 + "gho_abc123" + "y" * 5000
        result = sanitizer.sanitize(long_text)

        assert "gho_abc123" not in result
        assert len(result) > 9900  # Token pattern caps at 100 chars + marker

    def test_sanitize_deeply_nested_structure(self):
        """Test sanitizing deeply nested data structures."""
        sanitizer = TokenSanitizer()

        # 10 levels deep
        data: Dict[str, Any] = {"level0": {}}
        current = data["level0"]
        for i in range(1, 10):
            current[f"level{i}"] = {}
            current = current[f"level{i}"]
        current["token"] = "gho_deepnested123"

        result = sanitizer.sanitize(data)
        assert "gho_deepnested123" not in str(result)

    def test_sanitize_token_at_boundary(self):
        """Test sanitizing tokens at string boundaries."""
        sanitizer = TokenSanitizer()

        # Token at start
        assert "gho_abc123" not in sanitizer.sanitize("gho_abc123 text")

        # Token at end
        assert "gho_abc123" not in sanitizer.sanitize("text gho_abc123")

        # Token is entire string
        assert "gho_abc123" not in sanitizer.sanitize("gho_abc123")

    def test_sanitize_partial_token_patterns(self):
        """Test that partial token patterns are not falsely detected."""
        sanitizer = TokenSanitizer()

        # These should NOT be detected as tokens (too short, wrong format)
        safe_texts = [
            "gho_",  # Prefix only
            "sk-",   # Prefix only
            "github oauth",  # Contains keywords but no token
            "bearer token",  # Generic reference
            "sk-short",  # Too short to be real
        ]

        for text in safe_texts:
            result = sanitizer.sanitize(text)
            assert result == text, f"False positive for: {text}"

    def test_sanitize_unicode_with_tokens(self):
        """Test sanitizing unicode strings containing tokens."""
        sanitizer = TokenSanitizer()

        text = "Token: gho_abc123 ✓ Unicode: 你好 🎉"
        result = sanitizer.sanitize(text)

        assert "gho_abc123" not in result
        assert "✓" in result
        assert "你好" in result
        assert "🎉" in result

    def test_sanitize_repeated_tokens(self):
        """Test sanitizing when same token appears multiple times."""
        sanitizer = TokenSanitizer()

        text = "Token1: gho_abc123, Token2: gho_abc123, Token3: gho_abc123"
        result = sanitizer.sanitize(text)

        # Token should be redacted everywhere
        assert "gho_abc123" not in result
        assert result.count("[REDACTED-GITHUB-TOKEN]") == 3

    def test_sanitize_mixed_types_in_list(self):
        """Test sanitizing lists with mixed data types."""
        sanitizer = TokenSanitizer()

        data = [
            "gho_abc123",
            123,
            None,
            {"key": "sk-xyz789"},
            ["nested", "ghs_test456"]
        ]

        result = sanitizer.sanitize(data)

        assert "gho_abc123" not in str(result)
        assert "sk-xyz789" not in str(result)
        assert "ghs_test456" not in str(result)
        assert 123 in result
        assert None in result


# ============================================================================
# PERFORMANCE TESTS (Part of Unit Tests)
# ============================================================================


class TestPerformance:
    """Test sanitization performance requirements."""

    def test_sanitize_performance_simple_string(self):
        """Test that simple string sanitization is < 1ms."""
        sanitizer = TokenSanitizer()
        text = "Token: gho_1234567890abcdefghij"

        start = time.perf_counter()
        for _ in range(100):
            sanitizer.sanitize(text)
        elapsed = time.perf_counter() - start

        avg_time_ms = (elapsed / 100) * 1000
        assert avg_time_ms < 1.0, f"Average time {avg_time_ms:.3f}ms exceeds 1ms"

    def test_sanitize_performance_dict(self):
        """Test that dict sanitization is < 1ms for small dicts."""
        sanitizer = TokenSanitizer()
        data = {
            "token1": "gho_abc123",
            "token2": "sk-xyz789",
            "safe": "text"
        }

        start = time.perf_counter()
        for _ in range(100):
            sanitizer.sanitize(data)
        elapsed = time.perf_counter() - start

        avg_time_ms = (elapsed / 100) * 1000
        assert avg_time_ms < 1.0, f"Average time {avg_time_ms:.3f}ms exceeds 1ms"

    def test_sanitize_performance_large_batch(self):
        """Test sanitizing 1000 strings completes in reasonable time."""
        sanitizer = TokenSanitizer()
        texts = [f"Token {i}: gho_test{i}" for i in range(1000)]

        start = time.perf_counter()
        for text in texts:
            sanitizer.sanitize(text)
        elapsed = time.perf_counter() - start

        assert elapsed < 1.0, f"Batch took {elapsed:.3f}s, should be < 1s"


class TestNoFalsePositives:
    """Test that sanitizer does not produce false positives."""

    def test_safe_github_references(self):
        """Test that GitHub references without tokens are preserved."""
        sanitizer = TokenSanitizer()

        safe_texts = [
            "Connect to GitHub API",
            "Use github.com for authentication",
            "GitHub token format: gho_...",
            "OAuth with GitHub",
        ]

        for text in safe_texts:
            result = sanitizer.sanitize(text)
            assert result == text, f"False positive for: {text}"

    def test_safe_api_key_references(self):
        """Test that API key references without actual keys are preserved."""
        sanitizer = TokenSanitizer()

        safe_texts = [
            "Set your OpenAI API key",
            "API key format: sk-...",
            "Configure Anthropic API",
            "Bearer token authentication",
        ]

        for text in safe_texts:
            result = sanitizer.sanitize(text)
            assert result == text, f"False positive for: {text}"

    def test_safe_code_examples(self):
        """Test that code examples without real tokens are preserved."""
        sanitizer = TokenSanitizer()

        code = """
        # Example configuration
        GITHUB_TOKEN = "your-token-here"
        OPENAI_API_KEY = "your-key-here"

        # Don't use real tokens like: gho_1234...
        """

        result = sanitizer.sanitize(code)
        assert "your-token-here" in result
        assert "your-key-here" in result


# ============================================================================
# E2E TESTS (10%) - Complete Sanitization Workflows
# ============================================================================


class TestEndToEndSanitization:
    """Test complete sanitization workflows."""

    def test_complete_error_sanitization_workflow(self):
        """Test sanitizing a complete error report."""
        sanitizer = TokenSanitizer()

        error_report = {
            "error": "API authentication failed",
            "request": {
                "url": "https://api.github.com/copilot/chat/completions",
                "headers": {
                    "Authorization": "Bearer gho_1234567890abcdefghij",
                    "Content-Type": "application/json"
                },
                "body": {
                    "messages": [
                        {"role": "user", "content": "Hello"}
                    ]
                }
            },
            "response": {
                "status": 401,
                "body": {"message": "Bad credentials"}
            },
            "traceback": [
                "File 'proxy/server.py', line 123",
                "  auth_header = f'Bearer {gho_1234567890abcdefghij}'",
                "ConnectionError: Authentication failed"
            ]
        }

        result = sanitizer.sanitize(error_report)

        # Verify tokens are redacted
        assert "gho_1234567890abcdefghij" not in str(result)

        # Verify structure is preserved
        assert result["error"] == "API authentication failed"
        assert result["response"]["status"] == 401
        assert "Bad credentials" in result["response"]["body"]["message"]

    def test_sanitize_logging_output(self):
        """Test sanitizing typical logging output."""
        sanitizer = TokenSanitizer()

        log_lines = [
            "2024-01-14 12:00:00 INFO Starting proxy server",
            "2024-01-14 12:00:01 DEBUG GitHub token: gho_abc123",
            "2024-01-14 12:00:02 DEBUG OpenAI key: sk-xyz789",
            "2024-01-14 12:00:03 ERROR Authentication failed",
            "2024-01-14 12:00:04 INFO Retrying with token: gho_abc123",
        ]

        sanitized_logs = [sanitizer.sanitize(line) for line in log_lines]

        # Verify tokens are redacted
        for log in sanitized_logs:
            assert "gho_abc123" not in log
            assert "sk-xyz789" not in log

        # Verify timestamps and messages are preserved
        assert "2024-01-14 12:00:00" in sanitized_logs[0]
        assert "INFO Starting proxy server" in sanitized_logs[0]
        assert "ERROR Authentication failed" in sanitized_logs[3]

    def test_sanitize_configuration_dump(self):
        """Test sanitizing configuration dumps."""
        sanitizer = TokenSanitizer()

        config = {
            "proxy": {
                "host": "0.0.0.0",
                "port": 8000
            },
            "github": {
                "enabled": True,
                "token": "gho_1234567890abcdefghij",
                "endpoint": "https://api.github.com"
            },
            "openai": {
                "enabled": True,
                "api_key": "sk-1234567890abcdefghij",
                "model": "gpt-4"
            },
            "anthropic": {
                "enabled": True,
                "api_key": "sk-ant-1234567890abcdefghij",
                "model": "claude-3-sonnet"
            }
        }

        result = sanitizer.sanitize(config)

        # Verify all tokens are redacted
        assert "gho_1234567890abcdefghij" not in str(result)
        assert "sk-1234567890abcdefghij" not in str(result)
        assert "sk-ant-1234567890abcdefghij" not in str(result)

        # Verify configuration structure is preserved
        assert result["proxy"]["host"] == "0.0.0.0"
        assert result["proxy"]["port"] == 8000
        assert result["github"]["enabled"] is True
        assert result["openai"]["model"] == "gpt-4"
        assert result["anthropic"]["model"] == "claude-3-sonnet"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
