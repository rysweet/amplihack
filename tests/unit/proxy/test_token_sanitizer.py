"""
Unit Tests for TokenSanitizer

Tests for credential sanitization to prevent credential exposure in logs.

Created for Issue #1997: API Keys Logged in Plain Text

Note: This file contains fake credentials for testing purposes only.
All test credentials are marked with pragma: allowlist secret.
"""

from amplihack.proxy.token_sanitizer import TokenSanitizer, sanitize


class TestTokenSanitizer:
    """Test suite for TokenSanitizer"""

    # OpenAI API Key Tests
    def test_sanitize_openai_key(self):
        """Test sanitization of OpenAI API keys"""
        text = "Using API key sk-1234567890abcdefghijklmnopqrstuvwxyz"
        result = TokenSanitizer.sanitize(text)
        assert "sk-" not in result or result.count("sk-") == result.count("sk-***")
        assert "***" in result
        assert "1234567890" not in result

    def test_sanitize_openai_project_key(self):
        """Test sanitization of OpenAI project keys"""
        text = "Project key: sk-proj-abcd1234efgh5678ijkl"
        result = TokenSanitizer.sanitize(text)
        assert "sk-proj-***" in result
        assert "abcd1234" not in result

    # Bearer Token Tests
    def test_sanitize_bearer_token(self):
        """Test sanitization of Bearer tokens"""
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        result = TokenSanitizer.sanitize(text)
        # Should sanitize the entire Authorization header value
        assert "Authorization: Bearer ***" in result or "Bearer ***" in result
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result

    # GitHub Token Tests
    def test_sanitize_github_pat(self):
        """Test sanitization of GitHub Personal Access Tokens"""
        text = "Token: ghp_1234567890123456789012345678901234"
        result = TokenSanitizer.sanitize(text)
        assert "ghp_***" in result
        assert "123456789012345678901234567890" not in result

    def test_sanitize_github_oauth(self):
        """Test sanitization of GitHub OAuth tokens"""
        text = "OAuth: gho_1234567890123456789012345678901234"
        result = TokenSanitizer.sanitize(text)
        assert "gho_***" in result

    def test_sanitize_github_server_token(self):
        """Test sanitization of GitHub server-to-server tokens"""
        text = "Server token: ghs_1234567890123456789012345678901234"
        result = TokenSanitizer.sanitize(text)
        assert "ghs_***" in result

    def test_sanitize_github_fine_grained_pat(self):
        """Test sanitization of GitHub fine-grained PATs"""
        text = "Fine-grained: github_pat_11AAAAAA0XXxxXXxXxXXxX_xxxxxXXXxxXxxXXxxxXXXXxXxXXXxXxX"
        result = TokenSanitizer.sanitize(text)
        assert "github_pat_***" in result

    # Azure/JWT Token Tests
    def test_sanitize_jwt_token(self):
        """Test sanitization of JWT tokens (Azure AD, etc.)"""
        text = "JWT: eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"  # pragma: allowlist secret
        result = TokenSanitizer.sanitize(text)
        assert "eyJ***.eyJ***.***" in result
        assert (
            "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c" not in result  # pragma: allowlist secret
        )  # pragma: allowlist secret

    # AWS Credentials Tests
    def test_sanitize_aws_access_key(self):
        """Test sanitization of AWS access key IDs"""
        text = "AWS Access Key: AKIAIOSFODNN7EXAMPLE"  # pragma: allowlist secret
        result = TokenSanitizer.sanitize(text)
        assert "AKIA***" in result
        assert "IOSFODNN7EXAMPLE" not in result

    def test_sanitize_aws_secret_key(self):
        """Test sanitization of AWS secret access keys"""
        text = 'aws_secret_access_key: "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"'  # pragma: allowlist secret
        result = TokenSanitizer.sanitize(text)
        assert "***" in result
        assert "wJalrXUtnFEMI" not in result

    # JSON API Key Tests
    def test_sanitize_json_api_key(self):
        """Test sanitization of API keys in JSON"""
        text = '{"api_key": "secret-key-12345", "user": "john"}'  # pragma: allowlist secret
        result = TokenSanitizer.sanitize(text)
        assert '"api_key": "***"' in result
        assert "secret-key-12345" not in result
        assert '"user": "john"' in result  # Non-sensitive data preserved

    def test_sanitize_json_access_token(self):
        """Test sanitization of access_token in JSON"""
        text = '{"access_token": "abc123def456"}'  # pragma: allowlist secret
        result = TokenSanitizer.sanitize(text)
        assert '"access_token": "***"' in result
        assert "abc123def456" not in result  # pragma: allowlist secret

    def test_sanitize_json_password(self):
        """Test sanitization of passwords in JSON"""
        text = '{"password": "mySecretPassword123"}'  # pragma: allowlist secret
        result = TokenSanitizer.sanitize(text)
        assert '"password": "***"' in result
        assert "mySecretPassword123" not in result

    # Header Tests
    def test_sanitize_authorization_header(self):
        """Test sanitization of Authorization headers"""
        text = "Authorization: sk-1234567890abcdef"
        result = TokenSanitizer.sanitize(text)
        assert "Authorization: ***" in result

    def test_sanitize_xapi_key_header(self):
        """Test sanitization of X-API-Key headers"""
        text = "X-API-Key: my-secret-api-key-12345"
        result = TokenSanitizer.sanitize(text)
        assert "X-API-Key: ***" in result
        assert "my-secret-api-key-12345" not in result

    # Edge Cases
    def test_sanitize_none(self):
        """Test sanitization of None value"""
        result = TokenSanitizer.sanitize(None)
        assert result == ""

    def test_sanitize_empty_string(self):
        """Test sanitization of empty string"""
        result = TokenSanitizer.sanitize("")
        assert result == ""

    def test_sanitize_no_secrets(self):
        """Test that clean text passes through unchanged"""
        text = "This is a clean log message with no secrets"
        result = TokenSanitizer.sanitize(text)
        assert result == text

    def test_sanitize_multiple_secrets(self):
        """Test sanitization of multiple secrets in one string"""
        text = "OpenAI: sk-abc123456789, GitHub: ghp_12345678901234567890123456789012, AWS: AKIAIOSFODNN7EXAMPLE"  # pragma: allowlist secret
        result = TokenSanitizer.sanitize(text)
        assert "sk-***" in result  # pragma: allowlist secret
        assert "ghp_***" in result
        assert "AKIA***" in result
        assert "abc123456789" not in result  # pragma: allowlist secret
        assert "123456789012345678" not in result

    # Dictionary Sanitization Tests
    def test_sanitize_dict_simple(self):  # pragma: allowlist secret
        """Test dictionary sanitization"""
        data = {  # pragma: allowlist secret
            "api_key": "sk-1234567890abcdef",  # pragma: allowlist secret
            "user": "john",
            "token": "ghp_123456789012345678901234567890123456",  # pragma: allowlist secret
        }
        result = TokenSanitizer.sanitize_dict(data)
        assert "sk-***" in result["api_key"]
        assert result["user"] == "john"  # Non-sensitive preserved
        assert "ghp_***" in result["token"]

    def test_sanitize_dict_nested(self):
        """Test nested dictionary sanitization"""
        data = {  # pragma: allowlist secret
            "config": {
                "api_key": "sk-secret123",  # pragma: allowlist secret
                "region": "us-west-2",
            },  # pragma: allowlist secret
            "user": "alice",
        }
        result = TokenSanitizer.sanitize_dict(data)
        assert "sk-***" in result["config"]["api_key"]
        assert result["config"]["region"] == "us-west-2"
        assert result["user"] == "alice"

    def test_sanitize_dict_with_list(self):
        """Test dictionary with list sanitization"""
        data = {"tokens": ["sk-token1", "sk-token2"], "name": "test"}
        result = TokenSanitizer.sanitize_dict(data)
        assert all("sk-***" in token for token in result["tokens"])
        assert result["name"] == "test"

    def test_sanitize_dict_none(self):
        """Test dictionary sanitization with None"""
        result = TokenSanitizer.sanitize_dict(None)
        assert result == {}

    # Convenience Function Test
    def test_sanitize_convenience_function(self):
        """Test the convenience sanitize() function"""
        text = "API key: sk-1234567890abcdef"
        result = sanitize(text)
        assert "sk-***" in result
        assert "1234567890" not in result

    # Real-world Scenarios
    def test_sanitize_curl_command(self):
        """Test sanitization of curl command with Authorization header"""
        text = 'curl -H "Authorization: Bearer sk-proj-abc123xyz" https://api.openai.com/v1/chat/completions'
        result = TokenSanitizer.sanitize(text)
        assert "Authorization: ***" in result or "Bearer ***" in result
        assert "abc123xyz" not in result

    def test_sanitize_http_request_log(self):
        """Test sanitization of HTTP request log"""
        text = """POST /v1/chat/completions
Headers: {
  "Authorization": "Bearer sk-proj-1234567890",
  "Content-Type": "application/json"
}
Body: {"model": "gpt-4", "messages": [...]}"""
        result = TokenSanitizer.sanitize(text)
        assert "Authorization: ***" in result or "***" in result
        assert "1234567890" not in result
        assert "Content-Type" in result  # Non-sensitive preserved

    def test_sanitize_azure_error_message(self):
        """Test sanitization of Azure error with token"""
        text = "Azure auth failed with token: eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature"  # pragma: allowlist secret
        result = TokenSanitizer.sanitize(text)
        assert "eyJ***.eyJ***.***" in result
        assert "signature" not in result

    # Performance Test (informal)
    def test_sanitize_large_string(self):
        """Test sanitization of large string (performance check)"""
        # Simulate large log with mix of clean and sensitive data
        text = ("Clean log line " * 100) + " sk-secret123 " + ("More clean data " * 100)
        result = TokenSanitizer.sanitize(text)
        assert "sk-***" in result
        assert "secret123" not in result
        # Should complete quickly (no assertion, just checking it doesn't hang)
