#!/usr/bin/env python3
"""
Security test cases for context preservation system.
Tests all security protections against regex DoS and input validation attacks.
"""

import sys
import time
from pathlib import Path

import pytest

# Add the tools directory to the path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / ".claude" / "tools" / "amplihack"))

from context_preservation_secure import (
    ContextPreserver,
    InputValidationError,
    RegexTimeoutError,
    SecurityConfig,
    SecurityValidator,
)


class TestSecurityValidator:
    """Test cases for SecurityValidator class."""

    def test_input_size_validation_success(self):
        """Test that valid input passes size validation."""
        text = "This is a normal sized input"
        result = SecurityValidator.validate_input_size(text)
        assert result == text

    def test_input_size_validation_too_large(self):
        """Test that oversized input is rejected."""
        # Create input larger than MAX_INPUT_SIZE
        large_text = "x" * (SecurityConfig.MAX_INPUT_SIZE + 1)

        with pytest.raises(InputValidationError) as exc_info:
            SecurityValidator.validate_input_size(large_text)

        assert "exceeds maximum allowed" in str(exc_info.value)

    def test_input_size_validation_long_lines(self):
        """Test that excessively long lines are rejected."""
        # Create a line longer than MAX_LINE_LENGTH
        long_line = "x" * (SecurityConfig.MAX_LINE_LENGTH + 1)

        with pytest.raises(InputValidationError) as exc_info:
            SecurityValidator.validate_input_size(long_line)

        assert "Line 1 length" in str(exc_info.value)

    def test_input_sanitization_whitelist(self):
        """Test that input sanitization removes disallowed characters."""
        malicious_input = "Normal text with <script>alert('xss')</script> tags"
        sanitized = SecurityValidator.sanitize_input(malicious_input)

        # Should remove script tags but keep normal text
        assert "<script>" not in sanitized
        assert "Normal text" in sanitized

    def test_input_sanitization_unicode_normalization(self):
        """Test that unicode normalization prevents encoding attacks."""
        # Unicode that could be used for bypassing filters
        unicode_input = "caf\u00e9"  # café with combining character
        sanitized = SecurityValidator.sanitize_input(unicode_input)

        # Should normalize unicode
        assert len(sanitized) > 0
        assert isinstance(sanitized, str)

    def test_safe_regex_finditer_timeout_protection(self):
        """Test that regex operations timeout on malicious patterns."""
        # This would be a potentially dangerous regex pattern
        malicious_pattern = r"(a+)+b"
        malicious_input = "a" * 1000  # Would cause exponential backtracking

        # Should complete without hanging (may timeout on some systems)
        start_time = time.time()
        try:
            _ = SecurityValidator.safe_regex_finditer(malicious_pattern, malicious_input)
            elapsed = time.time() - start_time
            # Should either timeout quickly or complete quickly, not hang
            assert elapsed < 5.0  # 5 second max for safety
        except RegexTimeoutError:
            # Timeout is expected and acceptable
            elapsed = time.time() - start_time
            assert elapsed < 3.0  # Should timeout within reasonable time

    def test_safe_regex_finditer_max_matches(self):
        """Test that regex finditer respects max_matches limit."""
        pattern = r"a"
        text = "a" * 200  # 200 'a' characters

        result = SecurityValidator.safe_regex_finditer(pattern, text, max_matches=50)
        assert len(result) <= 50

    def test_safe_regex_search_basic_functionality(self):
        """Test that safe regex search works for normal patterns."""
        pattern = r"hello"
        text = "hello world"

        result = SecurityValidator.safe_regex_search(pattern, text)
        assert result is not None
        assert result.group() == "hello"

    def test_safe_regex_findall_limits(self):
        """Test that findall respects limits."""
        pattern = r"\w+"
        text = "word " * 200  # 200 words

        result = SecurityValidator.safe_regex_findall(pattern, text, max_matches=50)
        assert len(result) <= 50

    def test_safe_split_with_limits(self):
        """Test that split operations respect limits."""
        text = "a.b.c." * 1000  # Many split points
        pattern = r"\."

        result = SecurityValidator.safe_split(text, pattern, max_splits=100)
        assert len(result) <= 100

    def test_safe_split_fallback_for_simple_patterns(self):
        """Test that simple patterns fall back to string split."""
        text = "line1\nline2\nline3"

        result = SecurityValidator.safe_split(text, "\n")
        assert len(result) == 3
        assert result[0] == "line1"


class TestContextPreserverSecurity:
    """Test cases for ContextPreserver security features."""

    def test_extract_original_request_oversized_input(self):
        """Test that oversized input is handled securely."""
        preserver = ContextPreserver("test_session")

        # Create oversized input
        oversized_prompt = "x" * (SecurityConfig.MAX_INPUT_SIZE + 1)

        result = preserver.extract_original_request(oversized_prompt)

        # Should return secure error response
        assert result["raw_prompt"] == "[INVALID INPUT - SANITIZED]"
        assert result["target"] == "Security validation failed"
        assert "security_error" in result

    def test_extract_original_request_malicious_input(self):
        """Test that malicious input is sanitized."""
        preserver = ContextPreserver("test_session")

        malicious_prompt = """
        **Target**: Legitimate request with <script>alert('xss')</script>
        **Problem**: This contains malicious content
        """

        result = preserver.extract_original_request(malicious_prompt)

        # Should sanitize the input
        assert "<script>" not in result["raw_prompt"]
        assert "alert" not in result["raw_prompt"]

    def test_parse_requirements_with_limits(self):
        """Test that requirement parsing respects limits."""
        preserver = ContextPreserver("test_session")

        # Create input with many requirements
        many_requirements = "\n".join([f"- Requirement {i}" for i in range(50)])

        result = preserver._parse_requirements(many_requirements)

        # Should be limited to MAX_REQUIREMENTS
        assert len(result) <= SecurityConfig.MAX_REQUIREMENTS

    def test_parse_constraints_with_limits(self):
        """Test that constraint parsing respects limits."""
        preserver = ContextPreserver("test_session")

        # Create input with many constraints
        many_constraints = "\n".join([f"Must not do {i}" for i in range(20)])

        result = preserver._parse_constraints(many_constraints)

        # Should be limited to MAX_CONSTRAINTS
        assert len(result) <= SecurityConfig.MAX_CONSTRAINTS

    def test_parse_success_criteria_with_limits(self):
        """Test that success criteria parsing respects limits."""
        preserver = ContextPreserver("test_session")

        # Create input with many criteria
        many_criteria = "\n".join([f"Success criteria {i}: Complete task {i}" for i in range(20)])

        result = preserver._parse_success_criteria(many_criteria)

        # Should be limited to MAX_CRITERIA
        assert len(result) <= SecurityConfig.MAX_CRITERIA

    def test_parse_target_length_limits(self):
        """Test that target parsing respects length limits."""
        preserver = ContextPreserver("test_session")

        # Create a very long target
        long_target = "**Target**: " + "x" * 1000

        result = preserver._parse_target(long_target)

        # Should either be limited or fall back to default
        assert len(result) <= 200 or result == "General development task"

    def test_save_original_request_html_escaping(self):
        """Test that saved content is HTML escaped."""
        preserver = ContextPreserver("test_session")

        malicious_request = {
            "timestamp": "2023-01-01T00:00:00",
            "session_id": "test",
            "raw_prompt": "<script>alert('xss')</script>",
            "target": "<img src=x onerror=alert(1)>",
            "requirements": ["<iframe src=javascript:alert(1)>"],
            "constraints": ["<svg onload=alert(1)>"],
            "success_criteria": ["<object data=javascript:alert(1)>"],
            "word_count": 5,
            "char_count": 50,
            "extracted_at": "2023-01-01T00:00:00",
        }

        preserver._save_original_request(malicious_request)

        # Read the saved file and verify HTML escaping
        request_file = preserver.session_dir / "ORIGINAL_REQUEST.md"
        content = request_file.read_text()

        # Should not contain raw HTML tags
        assert "<script>" not in content
        assert "<img" not in content
        assert "<iframe" not in content
        assert "<svg" not in content
        assert "<object" not in content

        # Should contain escaped versions
        assert "&lt;script&gt;" in content

    def test_format_agent_context_escaping(self):
        """Test that agent context escapes HTML."""
        preserver = ContextPreserver("test_session")

        malicious_request = {
            "target": "<script>alert('xss')</script>",
            "requirements": ["<img src=x onerror=alert(1)>"],
            "constraints": ["<iframe src=javascript:alert(1)>"],
            "success_criteria": ["<svg onload=alert(1)>"],
        }

        context = preserver.format_agent_context(malicious_request)

        # Should not contain raw HTML tags
        assert "<script>" not in context
        assert "<img" not in context
        assert "<iframe" not in context
        assert "<svg" not in context

        # Should contain escaped versions
        assert "&lt;script&gt;" in context

    def test_get_latest_session_id_directory_limit(self):
        """Test that directory scanning is limited to prevent DoS."""
        preserver = ContextPreserver("test_session")

        # This test would need a mock filesystem with many directories
        # For now, just test that the method doesn't hang
        start_time = time.time()
        _ = preserver.get_latest_session_id()
        elapsed = time.time() - start_time

        # Should complete quickly regardless of result
        assert elapsed < 1.0


class TestSecurityEdgeCases:
    """Test edge cases and corner cases for security."""

    def test_empty_input_handling(self):
        """Test handling of empty input."""
        preserver = ContextPreserver("test_session")

        result = preserver.extract_original_request("")

        # Should handle empty input gracefully
        assert result["raw_prompt"] == "[INVALID INPUT - SANITIZED]"

    def test_whitespace_only_input(self):
        """Test handling of whitespace-only input."""
        preserver = ContextPreserver("test_session")

        result = preserver.extract_original_request("   \n\t   ")

        # Should handle whitespace-only input gracefully
        assert result["raw_prompt"] == "[INVALID INPUT - SANITIZED]"

    def test_non_string_input_validation(self):
        """Test that non-string input is rejected."""
        with pytest.raises(InputValidationError):
            SecurityValidator.validate_input_size(123)

    def test_unicode_edge_cases(self):
        """Test handling of various unicode edge cases."""
        test_cases = [
            "\u0000",  # Null character
            "\ufeff",  # BOM
            "\u200b",  # Zero-width space
            "\U0001f600",  # Emoji
        ]

        for test_input in test_cases:
            # Should not crash
            try:
                result = SecurityValidator.sanitize_input(test_input)
                assert isinstance(result, str)
            except Exception as e:
                pytest.fail(f"Unicode input '{test_input!r}' caused exception: {e}")


class TestPerformanceAndDoSProtection:
    """Test performance characteristics and DoS protection."""

    def test_large_valid_input_performance(self):
        """Test that large but valid input is processed efficiently."""
        # Create large but valid input (under size limit and with proper line breaks)
        large_input = "Normal text.\n" * 1000  # Under 50KB limit, valid line lengths

        start_time = time.time()
        preserver = ContextPreserver("test_session")
        result = preserver.extract_original_request(large_input)
        elapsed = time.time() - start_time

        # Should complete in reasonable time
        assert elapsed < 5.0  # 5 seconds max
        assert result["char_count"] > 0

    def test_many_bullet_points_handling(self):
        """Test handling of many bullet points."""
        # Create input with many bullet points
        many_bullets = "\n".join([f"- Item {i}" for i in range(100)])

        preserver = ContextPreserver("test_session")
        result = preserver._parse_requirements(many_bullets)

        # Should be limited and not cause performance issues
        assert len(result) <= SecurityConfig.MAX_BULLETS

    def test_deep_nesting_protection(self):
        """Test protection against deeply nested patterns."""
        # Create deeply nested parentheses that could cause regex issues
        nested_input = "(" * 1000 + "test" + ")" * 1000

        start_time = time.time()
        try:
            SecurityValidator.sanitize_input(nested_input)
            elapsed = time.time() - start_time
            assert elapsed < 2.0  # Should complete quickly
        except Exception:
            # Any exception is acceptable as long as it doesn't hang
            elapsed = time.time() - start_time
            assert elapsed < 2.0


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
