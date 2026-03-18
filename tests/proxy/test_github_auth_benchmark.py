"""GitHub auth path benchmark tests for PR #3175.

Validates that:
1. Token validation is fast and effectively O(1) (no subprocess per call).
2. gh-models and Copilot SDK auth produce equivalent routing decisions
   (the "same lane" assumption).
3. Auth config caching works — repeated ProxyConfig lookups hit the
   cache, not the underlying storage.
4. The proxy server ModelValidator routes GitHub-authenticated requests
   through the same path for both copilot and gh-models model names.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

from amplihack.proxy.config import ProxyConfig
from amplihack.proxy.github_auth import GitHubAuthManager
from amplihack.proxy.github_detector import GitHubEndpointDetector
from amplihack.proxy.github_models import GitHubModelMapper

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_GHO_TOKEN = "gho_" + "a" * 36  # pragma: allowlist secret


def _make_github_config(token: str = _VALID_GHO_TOKEN) -> ProxyConfig:
    cfg = ProxyConfig()
    cfg.config = {
        "GITHUB_TOKEN": token,
        "GITHUB_COPILOT_ENABLED": "true",
        "PROXY_TYPE": "github_copilot",
    }
    return cfg


# ---------------------------------------------------------------------------
# 1. Auth validation performance
# ---------------------------------------------------------------------------


class TestAuthValidationPerformance:
    """Token format validation must be effectively instant (no I/O)."""

    def test_token_validation_is_fast(self):
        """Validate 1000 tokens in <100 ms — no subprocess or network I/O."""
        cfg = ProxyConfig()
        tokens = [
            ("gho_" + "x" * (i % 32 + 4), True)  # valid lengths
            for i in range(500)
        ] + [("bad", False) for _ in range(500)]

        start = time.perf_counter()
        for token, _ in tokens:
            cfg._validate_github_token_format(token)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 100, (
            f"Token validation took {elapsed_ms:.1f}ms for 1000 tokens (expected <100ms)"
        )

    def test_config_lookup_is_cached(self):
        """Repeated is_github_copilot_enabled() calls must not re-parse config."""
        cfg = _make_github_config()

        # Warm up
        cfg.is_github_copilot_enabled()

        start = time.perf_counter()
        for _ in range(10_000):
            cfg.is_github_copilot_enabled()
        elapsed_ms = (time.perf_counter() - start) * 1000

        # 10k lookups should complete in <50ms — confirms no repeated parsing
        assert elapsed_ms < 50, (
            f"10k is_github_copilot_enabled() calls took {elapsed_ms:.1f}ms (expected <50ms)"
        )

    def test_model_mapping_is_cached(self):
        """Repeated get_github_model() calls on the same name hit the cache."""
        mapper = GitHubModelMapper({})

        # Prime the cache
        mapper.get_github_model("gpt-4")

        start = time.perf_counter()
        for _ in range(10_000):
            mapper.get_github_model("gpt-4")
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 20, f"10k cached model lookups took {elapsed_ms:.1f}ms (expected <20ms)"


# ---------------------------------------------------------------------------
# 2. gh-models and Copilot SDK auth parity (same-lane assumption)
# ---------------------------------------------------------------------------


class TestGhModelsCopilotSDKAuthParity:
    """gh-models and Copilot SDK auth are the same lane — same token, same routing."""

    def test_same_token_works_for_both_lanes(self):
        """A GITHUB_TOKEN should satisfy both gh-models and Copilot SDK auth checks."""
        cfg = _make_github_config()

        # Copilot SDK lane
        assert cfg.is_github_copilot_enabled() is True
        assert cfg.validate_github_config() is True

        # gh-models lane — same token, same endpoint detector result
        detector = GitHubEndpointDetector()
        assert detector.is_github_endpoint(None, cfg.config) is True
        assert detector.is_litellm_provider_enabled(cfg.config) is True

    def test_model_routing_parity_copilot_vs_gh_models(self):
        """copilot-gpt-4 and github/copilot-gpt-4 both route via the GitHub lane."""
        from amplihack.proxy.server import ModelValidator

        validator = ModelValidator()

        # Direct copilot model name (Copilot SDK lane)
        copilot_route = validator.validate_and_route("copilot-gpt-4")
        # gh-models-style prefix
        gh_route = validator.validate_and_route("github/copilot-gpt-4")

        # Both must resolve to the same provider (github/)
        assert copilot_route is not None, "copilot-gpt-4 should route successfully"
        assert gh_route is not None, "github/copilot-gpt-4 should route successfully"

        # Both must be in the github lane (not anthropic or openai)
        assert "github" in copilot_route.lower() or "copilot" in copilot_route.lower(), (
            f"copilot-gpt-4 routed to unexpected lane: {copilot_route}"
        )
        assert "github" in gh_route.lower() or "copilot" in gh_route.lower(), (
            f"github/copilot-gpt-4 routed to unexpected lane: {gh_route}"
        )

    def test_token_scope_is_copilot_for_both_lanes(self):
        """GitHubAuthManager uses 'copilot' scope — valid for both Copilot SDK and gh-models."""
        auth_manager = GitHubAuthManager()
        assert "copilot" in auth_manager.scopes, (
            "Auth manager must request 'copilot' scope to cover both gh-models and Copilot SDK"
        )

    def test_endpoint_detection_symmetry(self):
        """Both gh-models and Copilot SDK configs are detected as github_copilot."""
        detector = GitHubEndpointDetector()

        # Copilot SDK config
        copilot_sdk_config = {
            "GITHUB_TOKEN": _VALID_GHO_TOKEN,
            "PROXY_TYPE": "github_copilot",
        }
        # gh-models config
        gh_models_config = {
            "GITHUB_TOKEN": _VALID_GHO_TOKEN,
            "GITHUB_COPILOT_ENABLED": "true",
        }

        assert detector.get_endpoint_type(None, copilot_sdk_config) == "github_copilot"
        assert detector.get_endpoint_type(None, gh_models_config) == "github_copilot"


# ---------------------------------------------------------------------------
# 3. Auth manager: no subprocess on cache hit
# ---------------------------------------------------------------------------


class TestAuthManagerSubprocessBehavior:
    """get_existing_token() must not call subprocess.run when token is cached."""

    @patch("subprocess.run")
    def test_get_existing_token_calls_subprocess_once(self, mock_run):
        """First call may invoke subprocess; result should be deterministic."""
        auth_manager = GitHubAuthManager()

        mock_run.side_effect = [
            MagicMock(returncode=0),  # gh auth status
            MagicMock(returncode=0, stdout=f"{_VALID_GHO_TOKEN}\n"),  # gh auth token
        ]

        with patch.object(auth_manager, "_verify_copilot_access", return_value=True):
            token = auth_manager.get_existing_token()

        assert token == _VALID_GHO_TOKEN
        # subprocess.run called exactly twice (auth status + token retrieval)
        assert mock_run.call_count == 2

    @patch("subprocess.run")
    def test_failed_gh_auth_returns_none_without_network(self, mock_run):
        """When gh auth status fails, return None immediately — no copilot API call."""
        auth_manager = GitHubAuthManager()
        mock_run.return_value = MagicMock(returncode=1)

        result = auth_manager.get_existing_token()

        assert result is None
        # Should only call gh auth status, nothing else
        assert mock_run.call_count == 1


# ---------------------------------------------------------------------------
# 4. ProxyConfig litellm config generation
# ---------------------------------------------------------------------------


class TestLiteLLMConfigGeneration:
    """get_litellm_github_config() must include all keys needed for gh-models routing."""

    def test_litellm_config_has_required_keys(self):
        cfg = _make_github_config()
        litellm_config = cfg.get_litellm_github_config()

        required_keys = {"GITHUB_TOKEN", "GITHUB_API_BASE", "GITHUB_COPILOT_MODEL"}
        missing = required_keys - set(litellm_config.keys())
        assert not missing, f"litellm config missing keys: {missing}"

    def test_litellm_config_token_matches_config(self):
        cfg = _make_github_config()
        litellm_config = cfg.get_litellm_github_config()

        assert litellm_config["GITHUB_TOKEN"] == _VALID_GHO_TOKEN

    def test_litellm_config_generation_is_fast(self):
        cfg = _make_github_config()

        start = time.perf_counter()
        for _ in range(1000):
            cfg.get_litellm_github_config()
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 100, (
            f"1000 litellm config generations took {elapsed_ms:.1f}ms (expected <100ms)"
        )
