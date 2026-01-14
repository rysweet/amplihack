"""Tests for GitHub Copilot integration components."""

import os
from unittest.mock import Mock, patch

import pytest

from amplihack.proxy.config import ProxyConfig
from amplihack.proxy.github_auth import GitHubAuthManager
from amplihack.proxy.github_detector import GitHubEndpointDetector
from amplihack.proxy.github_models import GitHubModelMapper


class TestGitHubEndpointDetector:
    """Test GitHub endpoint detection."""

    def test_github_api_endpoint_detection(self):
        """Test detection of GitHub API endpoints."""
        detector = GitHubEndpointDetector()

        # Valid GitHub endpoints
        assert detector.is_github_endpoint("https://api.github.com/copilot", {})
        assert detector.is_github_endpoint("https://copilot-proxy.githubusercontent.com", {})

        # Invalid endpoints
        assert not detector.is_github_endpoint("https://api.openai.com", {})
        assert not detector.is_github_endpoint("https://example.com", {})

    def test_github_config_indicators(self):
        """Test detection via configuration indicators."""
        detector = GitHubEndpointDetector()

        # Config with GitHub indicators
        config_with_github = {"GITHUB_TOKEN": "gho_test"}
        assert detector.is_github_endpoint(None, config_with_github)

        config_with_proxy_type = {"PROXY_TYPE": "github_copilot"}
        assert detector.is_github_endpoint(None, config_with_proxy_type)

        # Config without GitHub indicators
        config_without_github = {"OPENAI_API_KEY": "sk-test"}  # pragma: allowlist secret
        assert not detector.is_github_endpoint(None, config_without_github)

    def test_endpoint_type_detection(self):
        """Test endpoint type detection."""
        detector = GitHubEndpointDetector()

        github_config = {"GITHUB_TOKEN": "gho_test"}
        assert detector.get_endpoint_type(None, github_config) == "github_copilot"

        openai_config = {"OPENAI_API_KEY": "sk-test"}  # pragma: allowlist secret
        assert detector.get_endpoint_type(None, openai_config) == "openai"

    def test_canonical_endpoint(self):
        """Test canonical endpoint resolution."""
        detector = GitHubEndpointDetector()

        # Valid endpoint should return as-is
        valid_endpoint = "https://api.github.com/copilot"
        assert detector.get_canonical_endpoint(valid_endpoint) == valid_endpoint

        # Invalid endpoint should return default
        assert (
            detector.get_canonical_endpoint("https://invalid.com")
            == "https://api.github.com/copilot"
        )
        assert detector.get_canonical_endpoint(None) == "https://api.github.com/copilot"


class TestGitHubModelMapper:
    """Test GitHub model mapping."""

    def test_default_model_mapping(self):
        """Test default OpenAI to GitHub model mappings."""
        mapper = GitHubModelMapper({})

        assert mapper.get_github_model("gpt-4") == "copilot-gpt-4"
        assert mapper.get_github_model("gpt-3.5-turbo") == "copilot-gpt-3.5-turbo"
        assert mapper.get_github_model("gpt-4o") == "copilot-gpt-4"

    def test_custom_model_mapping(self):
        """Test custom model mappings from config."""
        config = {"GITHUB_COPILOT_MODEL": "custom-model"}
        mapper = GitHubModelMapper(config)

        # For models with default mappings, should use default, not custom
        assert mapper.get_github_model("gpt-4") == "copilot-gpt-4"

        # For models without default mappings, should use custom
        assert mapper.get_github_model("unknown-model") == "custom-model"

    def test_model_capabilities(self):
        """Test model capability detection."""
        mapper = GitHubModelMapper({})

        # GPT-4 capabilities
        caps = mapper.get_model_capabilities("copilot-gpt-4")
        assert caps["function_calling"] is True
        assert caps["context_window"] == 128000
        assert caps["code_generation"] is True

        # GPT-3.5 capabilities
        caps = mapper.get_model_capabilities("copilot-gpt-3.5-turbo")
        assert caps["function_calling"] is True
        assert caps["context_window"] == 16384

    def test_supported_languages(self):
        """Test programming language support."""
        mapper = GitHubModelMapper({})

        languages = mapper.get_supported_languages("copilot-gpt-4")
        assert "python" in languages
        assert "javascript" in languages
        assert "rust" in languages

    def test_streaming_support(self):
        """Test streaming support detection."""
        mapper = GitHubModelMapper({})

        assert mapper.supports_streaming("copilot-gpt-4") is True
        assert mapper.supports_streaming("copilot-gpt-3.5-turbo") is True


class TestGitHubAuthManager:
    """Test GitHub authentication manager."""

    @patch("subprocess.run")
    def test_existing_token_detection(self, mock_run):
        """Test detection of existing GitHub CLI tokens."""
        auth_manager = GitHubAuthManager()

        # Mock successful gh auth status
        mock_run.side_effect = [
            Mock(returncode=0),  # gh auth status
            Mock(returncode=0, stdout="gho_test_token\n"),  # gh auth token
        ]

        with patch.object(auth_manager, "_verify_copilot_access", return_value=True):
            token = auth_manager.get_existing_token()
            assert token == "gho_test_token"

    @patch("subprocess.run")
    def test_no_existing_token(self, mock_run):
        """Test when no existing token is available."""
        auth_manager = GitHubAuthManager()

        # Mock failed gh auth status
        mock_run.return_value = Mock(returncode=1)

        token = auth_manager.get_existing_token()
        assert token is None

    def test_token_validation(self):
        """Test GitHub token format validation via ProxyConfig."""
        config = ProxyConfig()

        # Valid tokens
        assert config._validate_github_token_format("gho_" + "x" * 20) is True
        assert config._validate_github_token_format("ghp_" + "x" * 20) is True
        assert config._validate_github_token_format("test-token-123") is True

        # Invalid tokens
        assert config._validate_github_token_format("") is False
        assert config._validate_github_token_format("short") is False
        assert config._validate_github_token_format("invalid_prefix_token") is False


class TestProxyConfigGitHubIntegration:
    """Test ProxyConfig GitHub integration."""

    def test_github_endpoint_detection(self):
        """Test GitHub endpoint detection in ProxyConfig."""
        config = ProxyConfig()
        config.config = {"GITHUB_TOKEN": "gho_test"}

        assert config.is_github_endpoint() is True
        assert config.get_endpoint_type() == "github_copilot"

    def test_github_config_validation(self):
        """Test GitHub configuration validation."""
        config = ProxyConfig()
        config.config = {"GITHUB_TOKEN": "gho_" + "x" * 20}

        assert config.validate_github_config() is True

    def test_github_config_validation_failure(self):
        """Test GitHub configuration validation failure."""
        config = ProxyConfig()
        config.config = {}  # Missing token

        assert config.validate_github_config() is False
        assert len(config.get_validation_errors()) > 0

    def test_github_model_mapping(self):
        """Test GitHub model mapping through ProxyConfig."""
        config = ProxyConfig()
        # Use a model that doesn't have a default mapping
        config.config = {"GITHUB_COPILOT_MODEL": "custom-model"}
        # Reinitialize the mapper with new config
        config._github_mapper = GitHubModelMapper(config.config)

        # Test with a model that has default mapping - should use default
        assert config.get_github_model("gpt-4") == "copilot-gpt-4"

        # Test with a model that has no default mapping - should use custom
        assert config.get_github_model("unknown-model") == "custom-model"

    def test_github_token_retrieval(self):
        """Test GitHub token retrieval."""
        config = ProxyConfig()
        config.config = {"GITHUB_TOKEN": "gho_test_token"}

        assert config.get_github_token() == "gho_test_token"

    def test_github_copilot_enabled_detection(self):
        """Test GitHub Copilot enabled detection."""
        config = ProxyConfig()

        # Test enabled values
        for enabled_value in ["true", "1", "yes", "on"]:
            config.config = {"GITHUB_COPILOT_ENABLED": enabled_value}
            assert config.is_github_copilot_enabled() is True

        # Test disabled values
        for disabled_value in ["false", "0", "no", "off", ""]:
            config.config = {"GITHUB_COPILOT_ENABLED": disabled_value}
            assert config.is_github_copilot_enabled() is False

    def test_full_validation_with_github(self):
        """Test full configuration validation with GitHub setup."""
        config = ProxyConfig()
        config.config = {
            "GITHUB_TOKEN": "gho_" + "x" * 20,
            "GITHUB_COPILOT_ENABLED": "true",
            "PROXY_TYPE": "github_copilot",
        }

        assert config.validate() is True


# ============================================================================
# NEW TESTS FOR ISSUE #1922 - Model Validation & Security
# ============================================================================


class TestModelValidation:
    """Test unified model validation (Issue #1922)."""

    def test_model_validator_sonnet_routing(self):
        """Test that ModelValidator correctly routes Sonnet models."""
        from amplihack.proxy.server import ModelValidator

        validator = ModelValidator()

        # Test Sonnet 4 routing (the conflict case from #1920)
        assert validator.validate_and_route("claude-sonnet-4.5-20250514") == "anthropic/claude-sonnet-4.5-20250514"
        assert validator.validate_and_route("claude-sonnet-4-20250514") == "anthropic/claude-sonnet-4-20250514"

        # Test other Claude models
        assert validator.validate_and_route("claude-opus-4-20240229") == "anthropic/claude-opus-4-20240229"
        assert validator.validate_and_route("claude-3-5-sonnet-20241022") == "anthropic/claude-3-5-sonnet-20241022"

    def test_sonnet_4_routing_fix_issue_1920(self):
        """Test explicit Sonnet 4 routing fix from Issue #1920.

        Verifies that "claude-sonnet-4" routes to Anthropic, not GitHub/OpenAI.
        This was the root cause of Issue #1920.
        """
        from amplihack.proxy.server import ModelValidator

        validator = ModelValidator()

        # The core fix: "claude-sonnet-4" must route to Anthropic
        result = validator.validate_and_route("claude-sonnet-4")
        assert result == "anthropic/claude-sonnet-4", f"Expected Anthropic routing, got {result}"

        # Verify provider determination
        provider = validator.get_provider("claude-sonnet-4")
        assert provider == "anthropic", f"Expected 'anthropic' provider, got '{provider}'"

    def test_model_validator_openai_routing(self):
        """Test that ModelValidator correctly routes OpenAI models."""
        from amplihack.proxy.server import ModelValidator

        validator = ModelValidator()

        # OpenAI models
        assert validator.validate_and_route("gpt-4") == "openai/gpt-4"
        assert validator.validate_and_route("gpt-4-turbo") == "openai/gpt-4-turbo"
        assert validator.validate_and_route("gpt-3.5-turbo") == "openai/gpt-3.5-turbo"

    def test_model_validator_github_routing(self):
        """Test that ModelValidator correctly routes GitHub models."""
        from amplihack.proxy.server import ModelValidator

        validator = ModelValidator()

        # GitHub Copilot models
        assert validator.validate_and_route("copilot-gpt-4") == "github/copilot-gpt-4"
        assert validator.validate_and_route("copilot-gpt-3.5-turbo") == "github/copilot-gpt-3.5-turbo"

    def test_model_validator_provider_prefix_determination(self):
        """Test that ModelValidator determines provider prefixes correctly."""
        from amplihack.proxy.server import ModelValidator

        validator = ModelValidator()

        # Claude models should get 'anthropic' prefix
        assert validator.get_provider("claude-sonnet-4.5-20250514") == "anthropic"
        assert validator.get_provider("claude-opus-4-20240229") == "anthropic"

        # GPT models should get 'openai' prefix
        assert validator.get_provider("gpt-4") == "openai"
        assert validator.get_provider("gpt-3.5-turbo") == "openai"

        # Copilot models should get 'github' prefix
        assert validator.get_provider("copilot-gpt-4") == "github"

    def test_model_validator_invalid_model(self):
        """Test that ModelValidator rejects invalid model names."""
        from amplihack.proxy.server import ModelValidator

        validator = ModelValidator()

        # Invalid model names should raise ValueError
        with pytest.raises(ValueError, match="Invalid model name"):
            validator.validate_and_route("invalid-model-123")

        with pytest.raises(ValueError, match="Invalid model name"):
            validator.validate_and_route("")

        with pytest.raises(ValueError, match="Invalid model name"):
            validator.validate_and_route("hack'; DROP TABLE models;--")

    def test_model_validator_constants_used(self):
        """Test that ModelValidator uses constants, not hardcoded strings."""
        from amplihack.proxy.server import ModelValidator, CLAUDE_MODELS

        validator = ModelValidator()

        # Verify CLAUDE_MODELS constant is defined
        assert isinstance(CLAUDE_MODELS, (list, tuple, set))
        assert len(CLAUDE_MODELS) > 0

        # Verify Sonnet 4 models are in constants
        claude_models_str = str(CLAUDE_MODELS).lower()
        assert "sonnet-4" in claude_models_str or "sonnet-4.5" in claude_models_str

    def test_model_list_completeness(self):
        """Test that model constants include all expected Claude models."""
        from amplihack.proxy.server import CLAUDE_MODELS

        # Expected model patterns
        expected_patterns = [
            "claude-3",
            "claude-sonnet",
            "claude-opus",
        ]

        claude_models_str = str(CLAUDE_MODELS).lower()

        for pattern in expected_patterns:
            assert pattern in claude_models_str, f"Missing pattern: {pattern}"


class TestInputValidation:
    """Test input validation for security (Issue #1922)."""

    def test_validate_model_name_format(self):
        """Test that model names are validated for format."""
        from amplihack.proxy.github_models import GitHubModelMapper

        mapper = GitHubModelMapper({})

        # Valid model names
        valid_models = [
            "gpt-4",
            "gpt-3.5-turbo",
            "claude-sonnet-4.5-20250514",
            "copilot-gpt-4"
        ]

        for model in valid_models:
            # Should not raise exception
            result = mapper.validate_model_name(model)
            assert result is True

    def test_reject_injection_attempts(self):
        """Test that injection attempts in model names are rejected."""
        from amplihack.proxy.github_models import GitHubModelMapper

        mapper = GitHubModelMapper({})

        # Injection attempts
        injection_attempts = [
            "gpt-4; DROP TABLE models;--",
            "gpt-4' OR '1'='1",
            "gpt-4<script>alert('xss')</script>",
            "../../../etc/passwd",
            "gpt-4\n\nmalicious-header: value"
        ]

        for attempt in injection_attempts:
            with pytest.raises(ValueError, match="Invalid model name"):
                mapper.validate_model_name(attempt)

    def test_validate_edge_cases(self):
        """Test validation of edge cases."""
        from amplihack.proxy.github_models import GitHubModelMapper

        mapper = GitHubModelMapper({})

        # Edge cases that should fail
        edge_cases = [
            "",  # Empty
            None,  # None
            "a" * 1000,  # Too long
            "gpt 4",  # Space instead of dash
            "GPT-4",  # Wrong case (if case-sensitive)
        ]

        for case in edge_cases:
            with pytest.raises((ValueError, TypeError)):
                mapper.validate_model_name(case)

    def test_validate_unicode_handling(self):
        """Test that unicode in model names is handled correctly."""
        from amplihack.proxy.github_models import GitHubModelMapper

        mapper = GitHubModelMapper({})

        # Unicode characters should be rejected
        unicode_attempts = [
            "gpt-4-你好",
            "gpt-4-🎉",
            "gpt\u0000-4",  # Null byte
        ]

        for attempt in unicode_attempts:
            with pytest.raises(ValueError, match="Invalid model name"):
                mapper.validate_model_name(attempt)


class TestFilePermissions:
    """Test file permissions for security (Issue #1922)."""

    def test_token_file_permissions(self, tmp_path):
        """Test that token files have 0600 permissions."""
        from amplihack.proxy.github_auth import GitHubAuthManager
        import os
        import stat

        auth_manager = GitHubAuthManager()
        token_file = tmp_path / ".github_token"

        # Save a token
        auth_manager.save_token("gho_test123", str(token_file))

        # Check permissions are 0600 (read/write for owner only)
        file_stat = os.stat(token_file)
        permissions = stat.filemode(file_stat.st_mode)

        # Should be -rw------- (0600)
        assert permissions == "-rw-------", f"Expected -rw-------, got {permissions}"

        # Verify using octal
        mode = file_stat.st_mode
        assert stat.S_IMODE(mode) == 0o600, f"Expected 0600, got {oct(stat.S_IMODE(mode))}"

    def test_token_directory_permissions(self, tmp_path):
        """Test that token directory has 0700 permissions."""
        from amplihack.proxy.github_auth import GitHubAuthManager
        import os
        import stat

        auth_manager = GitHubAuthManager()
        token_dir = tmp_path / ".amplihack"
        token_file = token_dir / ".github_token"

        # Create directory and save token
        auth_manager.save_token("gho_test123", str(token_file))

        # Check directory permissions are 0700 (rwx for owner only)
        dir_stat = os.stat(token_dir)
        permissions = stat.filemode(dir_stat.st_mode)

        # Should be drwx------ (0700)
        assert permissions == "drwx------", f"Expected drwx------, got {permissions}"

        # Verify using octal
        mode = dir_stat.st_mode
        assert stat.S_IMODE(mode) == 0o700, f"Expected 0700, got {oct(stat.S_IMODE(mode))}"

    def test_permission_error_handling(self, tmp_path):
        """Test that permission errors are handled gracefully."""
        from amplihack.proxy.github_auth import GitHubAuthManager
        import os

        auth_manager = GitHubAuthManager()

        # Create read-only directory
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        os.chmod(readonly_dir, 0o444)  # Read-only

        token_file = readonly_dir / ".github_token"

        # Attempting to save should raise PermissionError
        with pytest.raises(PermissionError):
            auth_manager.save_token("gho_test123", str(token_file))

        # Cleanup
        os.chmod(readonly_dir, 0o755)

    def test_existing_file_permission_update(self, tmp_path):
        """Test that existing files get permissions updated to 0600."""
        from amplihack.proxy.github_auth import GitHubAuthManager
        import os
        import stat

        auth_manager = GitHubAuthManager()
        token_file = tmp_path / ".github_token"

        # Create file with wrong permissions (0644)
        token_file.write_text("gho_oldtoken")
        os.chmod(token_file, 0o644)

        # Save new token (should update permissions)
        auth_manager.save_token("gho_newtoken", str(token_file))

        # Verify permissions are now 0600
        file_stat = os.stat(token_file)
        mode = file_stat.st_mode
        assert stat.S_IMODE(mode) == 0o600, f"Expected 0600, got {oct(stat.S_IMODE(mode))}"

    @pytest.mark.skipif(
        os.name == "nt",
        reason="Unix permissions not applicable on Windows"
    )
    def test_umask_does_not_affect_permissions(self, tmp_path):
        """Test that umask does not affect token file permissions."""
        from amplihack.proxy.github_auth import GitHubAuthManager
        import os
        import stat

        auth_manager = GitHubAuthManager()
        token_file = tmp_path / ".github_token"

        # Set restrictive umask
        old_umask = os.umask(0o077)

        try:
            # Save token
            auth_manager.save_token("gho_test123", str(token_file))

            # Verify permissions are still 0600
            file_stat = os.stat(token_file)
            mode = file_stat.st_mode
            assert stat.S_IMODE(mode) == 0o600

        finally:
            # Restore umask
            os.umask(old_umask)

    def test_set_secure_permissions_file(self, tmp_path):
        """Test _set_secure_permissions helper method for files."""
        from amplihack.proxy.github_auth import GitHubAuthManager
        import os
        import stat

        auth_manager = GitHubAuthManager()
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("test content")

        # Set secure permissions for file
        auth_manager._set_secure_permissions(test_file, is_dir=False)

        # Verify permissions are 0600
        file_stat = os.stat(test_file)
        mode = file_stat.st_mode
        assert stat.S_IMODE(mode) == 0o600, f"Expected 0600, got {oct(stat.S_IMODE(mode))}"

    def test_set_secure_permissions_directory(self, tmp_path):
        """Test _set_secure_permissions helper method for directories."""
        from amplihack.proxy.github_auth import GitHubAuthManager
        import os
        import stat

        auth_manager = GitHubAuthManager()
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        # Set secure permissions for directory
        auth_manager._set_secure_permissions(test_dir, is_dir=True)

        # Verify permissions are 0700
        dir_stat = os.stat(test_dir)
        mode = dir_stat.st_mode
        assert stat.S_IMODE(mode) == 0o700, f"Expected 0700, got {oct(stat.S_IMODE(mode))}"

    def test_set_secure_permissions_error_handling(self, tmp_path):
        """Test _set_secure_permissions error handling."""
        from amplihack.proxy.github_auth import GitHubAuthManager
        import os

        auth_manager = GitHubAuthManager()

        # Create read-only directory
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        test_file = readonly_dir / "test_file.txt"
        test_file.write_text("test")

        # Make directory read-only
        os.chmod(readonly_dir, 0o444)

        try:
            # Attempting to change permissions should raise PermissionError
            with pytest.raises(PermissionError, match="Unable to set secure permissions"):
                auth_manager._set_secure_permissions(test_file, is_dir=False)
        finally:
            # Cleanup - restore permissions
            os.chmod(readonly_dir, 0o755)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
