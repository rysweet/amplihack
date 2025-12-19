"""TDD tests for Issue #1870: Neo4j dialog bug fix.

Tests for _check_neo4j_credentials() early return when AMPLIHACK_ENABLE_NEO4J_MEMORY not set.

Bug: Method shows Neo4j Container Setup dialog even when env var not set.
Fix: Early return when AMPLIHACK_ENABLE_NEO4J_MEMORY != "1"

Testing pyramid:
- 60% Unit tests (mocked Neo4jManager)
- 30% Integration tests (real method calls)
- 10% E2E tests (complete workflow)
"""

import os
from unittest.mock import Mock, patch

import pytest

from amplihack.launcher.core import ClaudeLauncher


class TestNeo4jCheckEarlyReturn:
    """Unit tests for _check_neo4j_credentials early return behavior."""

    def test_returns_early_when_env_var_not_set(self):
        """Test that method returns early when AMPLIHACK_ENABLE_NEO4J_MEMORY not set.

        FAILING TEST - Will pass once fix is implemented.
        Bug: Currently shows dialog even when disabled.
        Expected: Should return immediately without calling Neo4jManager.
        """
        launcher = ClaudeLauncher()

        # Ensure env var is not set
        with patch.dict(os.environ, {}, clear=False):
            # Remove the key if it exists
            os.environ.pop("AMPLIHACK_ENABLE_NEO4J_MEMORY", None)

            # Mock Neo4jManager to verify it's NOT called
            with patch("amplihack.launcher.core.Neo4jManager") as mock_manager_class:
                launcher._check_neo4j_credentials()

                # Should NOT instantiate Neo4jManager when disabled
                mock_manager_class.assert_not_called()

    def test_returns_early_when_env_var_is_zero(self):
        """Test that method returns early when AMPLIHACK_ENABLE_NEO4J_MEMORY is "0".

        FAILING TEST - Will pass once fix is implemented.
        Bug: Currently processes "0" as enabled.
        Expected: Should return immediately, only "1" enables feature.
        """
        launcher = ClaudeLauncher()

        with patch.dict(os.environ, {"AMPLIHACK_ENABLE_NEO4J_MEMORY": "0"}):
            with patch("amplihack.launcher.core.Neo4jManager") as mock_manager_class:
                launcher._check_neo4j_credentials()

                # Should NOT instantiate Neo4jManager when explicitly disabled
                mock_manager_class.assert_not_called()

    def test_returns_early_when_env_var_is_empty_string(self):
        """Test that method returns early when AMPLIHACK_ENABLE_NEO4J_MEMORY is empty.

        FAILING TEST - Will pass once fix is implemented.
        Bug: Currently processes empty string as enabled.
        Expected: Should return immediately.
        """
        launcher = ClaudeLauncher()

        with patch.dict(os.environ, {"AMPLIHACK_ENABLE_NEO4J_MEMORY": ""}):
            with patch("amplihack.launcher.core.Neo4jManager") as mock_manager_class:
                launcher._check_neo4j_credentials()

                # Should NOT instantiate Neo4jManager with empty value
                mock_manager_class.assert_not_called()

    def test_proceeds_when_env_var_is_one(self):
        """Test that method proceeds normally when AMPLIHACK_ENABLE_NEO4J_MEMORY = "1".

        PASSING TEST - Current behavior works correctly when enabled.
        Expected: Should call Neo4jManager.check_and_sync() when enabled.
        """
        launcher = ClaudeLauncher()

        with patch.dict(os.environ, {"AMPLIHACK_ENABLE_NEO4J_MEMORY": "1"}):
            with patch("amplihack.launcher.core.Neo4jManager") as mock_manager_class:
                mock_manager = Mock()
                mock_manager_class.return_value = mock_manager

                launcher._check_neo4j_credentials()

                # SHOULD instantiate Neo4jManager when enabled
                mock_manager_class.assert_called_once()
                # SHOULD call check_and_sync
                mock_manager.check_and_sync.assert_called_once()

    def test_neo4j_manager_not_called_when_disabled(self):
        """Test that Neo4jManager.check_and_sync() is NOT called when disabled.

        FAILING TEST - Will pass once fix is implemented.
        Bug: Dialog appears even when feature disabled.
        Expected: No Neo4j operations when disabled.
        """
        launcher = ClaudeLauncher()

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AMPLIHACK_ENABLE_NEO4J_MEMORY", None)

            with patch("amplihack.launcher.core.Neo4jManager") as mock_manager_class:
                mock_manager = Mock()
                mock_manager_class.return_value = mock_manager

                launcher._check_neo4j_credentials()

                # Should NOT call check_and_sync when disabled
                mock_manager.check_and_sync.assert_not_called()


class TestNeo4jCheckIntegration:
    """Integration tests for _check_neo4j_credentials with real paths."""

    def test_graceful_degradation_when_disabled(self):
        """Test that method completes without errors when disabled.

        FAILING TEST - Will pass once fix is implemented.
        Bug: May show dialog or perform operations when disabled.
        Expected: Silent no-op, no errors, no side effects.
        """
        launcher = ClaudeLauncher()

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AMPLIHACK_ENABLE_NEO4J_MEMORY", None)

            # Should complete without error
            launcher._check_neo4j_credentials()

            # No assertions needed - test passes if no exception raised

    def test_handles_neo4j_manager_errors_gracefully_when_enabled(self):
        """Test that errors from Neo4jManager are caught when enabled.

        PASSING TEST - Current error handling works correctly.
        Expected: Errors caught and suppressed, launcher continues.
        """
        launcher = ClaudeLauncher()

        with patch.dict(os.environ, {"AMPLIHACK_ENABLE_NEO4J_MEMORY": "1"}):
            with patch("amplihack.launcher.core.Neo4jManager") as mock_manager_class:
                mock_manager = Mock()
                mock_manager.check_and_sync.side_effect = Exception("Test error")
                mock_manager_class.return_value = mock_manager

                # Should not raise exception
                launcher._check_neo4j_credentials()

    def test_different_env_var_values(self):
        """Test behavior with various environment variable values.

        FAILING TEST - Will pass once fix is implemented.
        Bug: Only "1" should enable, all others should disable.
        Expected: Strict "1" check, case-sensitive.
        """
        launcher = ClaudeLauncher()

        disabled_values = [
            None,
            "",
            "0",
            "false",
            "False",
            "no",
            "disabled",
            "true",
            "True",
            "yes",
            "enabled",
        ]

        for value in disabled_values:
            with patch.dict(os.environ, {}, clear=False):
                if value is None:
                    os.environ.pop("AMPLIHACK_ENABLE_NEO4J_MEMORY", None)
                else:
                    os.environ["AMPLIHACK_ENABLE_NEO4J_MEMORY"] = value

                with patch("amplihack.launcher.core.Neo4jManager") as mock_manager_class:
                    launcher._check_neo4j_credentials()

                    # All non-"1" values should skip Neo4j operations
                    if value != "1":
                        (
                            mock_manager_class.assert_not_called(),
                            f"Neo4jManager should not be called for value: {value!r}",
                        )


class TestNeo4jCheckEdgeCases:
    """Edge case tests for _check_neo4j_credentials."""

    def test_env_var_with_whitespace(self):
        """Test that env var with whitespace is treated as disabled.

        FAILING TEST - Will pass once fix is implemented.
        Bug: May trim whitespace and treat " 1 " as enabled.
        Expected: Exact "1" match only, no trimming.
        """
        launcher = ClaudeLauncher()

        whitespace_values = [" 1", "1 ", " 1 ", "\t1", "1\n"]

        for value in whitespace_values:
            with patch.dict(os.environ, {"AMPLIHACK_ENABLE_NEO4J_MEMORY": value}):
                with patch("amplihack.launcher.core.Neo4jManager") as mock_manager_class:
                    launcher._check_neo4j_credentials()

                    # Should NOT match with whitespace
                    (
                        mock_manager_class.assert_not_called(),
                        f"Neo4jManager should not be called for value with whitespace: {value!r}",
                    )

    def test_case_sensitivity(self):
        """Test that env var check is case-sensitive.

        FAILING TEST - Will pass once fix is implemented.
        Bug: May accept "1" in any case.
        Expected: Only exact "1" string, not "ONE" or other variants.
        """
        launcher = ClaudeLauncher()

        case_variants = ["ONE", "one", "True", "TRUE"]

        for value in case_variants:
            with patch.dict(os.environ, {"AMPLIHACK_ENABLE_NEO4J_MEMORY": value}):
                with patch("amplihack.launcher.core.Neo4jManager") as mock_manager_class:
                    launcher._check_neo4j_credentials()

                    # Should be case-sensitive
                    (
                        mock_manager_class.assert_not_called(),
                        f"Neo4jManager should not be called for case variant: {value!r}",
                    )


class TestNeo4jCheckE2E:
    """End-to-end tests for complete _check_neo4j_credentials workflow."""

    def test_complete_disabled_workflow(self):
        """Test complete workflow when Neo4j memory disabled.

        FAILING TEST - Will pass once fix is implemented.
        Bug: May show dialog or perform checks.
        Expected: Complete immediately with no Neo4j operations.
        """
        launcher = ClaudeLauncher()

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AMPLIHACK_ENABLE_NEO4J_MEMORY", None)

            # Mock all Neo4j components
            with patch("amplihack.launcher.core.Neo4jManager") as mock_manager_class:
                with patch("amplihack.neo4j.detector.Neo4jContainerDetector") as mock_detector:
                    with patch("amplihack.neo4j.credential_sync.CredentialSync") as mock_sync:
                        launcher._check_neo4j_credentials()

                        # None of the Neo4j components should be instantiated
                        mock_manager_class.assert_not_called()
                        mock_detector.assert_not_called()
                        mock_sync.assert_not_called()

    def test_complete_enabled_workflow(self):
        """Test complete workflow when Neo4j memory enabled.

        PASSING TEST - Current enabled behavior works correctly.
        Expected: Normal Neo4j detection and sync flow.
        """
        launcher = ClaudeLauncher()

        with patch.dict(os.environ, {"AMPLIHACK_ENABLE_NEO4J_MEMORY": "1"}):
            with patch("amplihack.launcher.core.Neo4jManager") as mock_manager_class:
                mock_manager = Mock()
                mock_manager_class.return_value = mock_manager

                launcher._check_neo4j_credentials()

                # Neo4j components should be used
                mock_manager_class.assert_called_once()
                mock_manager.check_and_sync.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
