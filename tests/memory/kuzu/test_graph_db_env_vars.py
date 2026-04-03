"""Tests for backend-neutral env-var DB path resolution (AC-01).

Verifies that:
- AMPLIHACK_GRAPH_DB_PATH overrides the default Kùzu database path
- AMPLIHACK_KUZU_DB_PATH triggers a DeprecationWarning and falls back correctly
- Invalid paths (non-absolute, path-traversal, blocked prefixes) are rejected

These tests mirror the contract enforced by amplihack-rs
``resolve_memory_graph_db_path()`` in graph_db.rs.
"""

from __future__ import annotations

import warnings
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _import_connector():
    """Import KuzuConnector; skip if kuzu not installed."""
    pytest.importorskip("kuzu")
    from amplihack.memory.kuzu.connector import KuzuConnector

    return KuzuConnector


# ---------------------------------------------------------------------------
# AC-01 Part A: AMPLIHACK_GRAPH_DB_PATH (primary env var)
# ---------------------------------------------------------------------------


class TestGraphDbEnvVarPrimary:
    """AMPLIHACK_GRAPH_DB_PATH is the primary, backend-neutral override."""

    def test_env_var_overrides_default(self, tmp_path):
        """When AMPLIHACK_GRAPH_DB_PATH is set the connector uses it."""
        KuzuConnector = _import_connector()
        db_path = tmp_path / "custom_graph_db"
        db_path.mkdir()

        env = {"AMPLIHACK_GRAPH_DB_PATH": str(db_path), "AMPLIHACK_KUZU_DB_PATH": ""}
        with patch.dict("os.environ", env, clear=False):
            connector = KuzuConnector()

        assert connector.db_path == db_path

    def test_env_var_no_deprecation_warning(self, tmp_path):
        """Primary env var must NOT produce a DeprecationWarning."""
        KuzuConnector = _import_connector()
        db_path = tmp_path / "custom_graph_db"
        db_path.mkdir()

        env = {"AMPLIHACK_GRAPH_DB_PATH": str(db_path), "AMPLIHACK_KUZU_DB_PATH": ""}
        with patch.dict("os.environ", env, clear=False):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                KuzuConnector()

        deprecation_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        assert deprecation_warnings == [], (
            "AMPLIHACK_GRAPH_DB_PATH must not emit DeprecationWarning"
        )

    def test_env_var_takes_precedence_over_legacy(self, tmp_path):
        """AMPLIHACK_GRAPH_DB_PATH wins over AMPLIHACK_KUZU_DB_PATH."""
        KuzuConnector = _import_connector()
        primary = tmp_path / "primary_db"
        primary.mkdir()
        legacy = tmp_path / "legacy_db"
        legacy.mkdir()

        env = {
            "AMPLIHACK_GRAPH_DB_PATH": str(primary),
            "AMPLIHACK_KUZU_DB_PATH": str(legacy),
        }
        with patch.dict("os.environ", env, clear=False):
            connector = KuzuConnector()

        assert connector.db_path == primary


# ---------------------------------------------------------------------------
# AC-01 Part B: AMPLIHACK_KUZU_DB_PATH (deprecated fallback)
# ---------------------------------------------------------------------------


class TestGraphDbEnvVarLegacy:
    """AMPLIHACK_KUZU_DB_PATH is the deprecated fallback."""

    def test_legacy_env_var_is_used(self, tmp_path):
        """AMPLIHACK_KUZU_DB_PATH is used when primary is absent."""
        KuzuConnector = _import_connector()
        db_path = tmp_path / "legacy_db"
        db_path.mkdir()

        env = {"AMPLIHACK_KUZU_DB_PATH": str(db_path), "AMPLIHACK_GRAPH_DB_PATH": ""}
        with patch.dict("os.environ", env, clear=False):
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                connector = KuzuConnector()

        assert connector.db_path == db_path

    def test_legacy_env_var_emits_deprecation_warning(self, tmp_path):
        """AMPLIHACK_KUZU_DB_PATH must emit a DeprecationWarning."""
        KuzuConnector = _import_connector()
        db_path = tmp_path / "legacy_db"
        db_path.mkdir()

        env = {"AMPLIHACK_KUZU_DB_PATH": str(db_path), "AMPLIHACK_GRAPH_DB_PATH": ""}
        with patch.dict("os.environ", env, clear=False):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                KuzuConnector()

        deprecation_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        assert deprecation_warnings, "AMPLIHACK_KUZU_DB_PATH must emit DeprecationWarning"
        assert "AMPLIHACK_GRAPH_DB_PATH" in str(deprecation_warnings[0].message)

    def test_no_env_var_falls_back_to_default(self, tmp_path):
        """Without any env var, the default path resolution kicks in."""
        KuzuConnector = _import_connector()

        env = {"AMPLIHACK_GRAPH_DB_PATH": "", "AMPLIHACK_KUZU_DB_PATH": ""}
        # Point home to tmp_path so we can verify the default
        with (
            patch.dict("os.environ", env, clear=False),
            patch("pathlib.Path.home", return_value=tmp_path),
        ):
            connector = KuzuConnector()

        expected_suffix = Path(".amplihack") / "kuzu_db"
        assert connector.db_path.parts[-2:] == expected_suffix.parts


# ---------------------------------------------------------------------------
# AC-01 Part C: Path validation (mirrors amplihack-rs security checks)
# ---------------------------------------------------------------------------


class TestGraphDbEnvVarValidation:
    """Env-var paths are validated with the same rules as amplihack-rs."""

    def test_rejects_relative_path(self):
        """Non-absolute paths are rejected."""
        KuzuConnector = _import_connector()

        env = {"AMPLIHACK_GRAPH_DB_PATH": "relative/path/db", "AMPLIHACK_KUZU_DB_PATH": ""}
        with patch.dict("os.environ", env, clear=False):
            with pytest.raises(ValueError, match="must be absolute"):
                KuzuConnector()

    def test_rejects_path_traversal(self, tmp_path):
        """Paths containing ``..`` are rejected."""
        KuzuConnector = _import_connector()
        traversal = str(tmp_path) + "/../evil"

        env = {"AMPLIHACK_GRAPH_DB_PATH": traversal, "AMPLIHACK_KUZU_DB_PATH": ""}
        with patch.dict("os.environ", env, clear=False):
            with pytest.raises(ValueError, match=r"\.\.|blocked|absolute"):
                KuzuConnector()

    @pytest.mark.parametrize("blocked", ["/proc/1", "/sys/kernel", "/dev/null"])
    def test_rejects_blocked_prefixes(self, blocked):
        """Paths starting with /proc, /sys, /dev are rejected."""
        KuzuConnector = _import_connector()

        env = {"AMPLIHACK_GRAPH_DB_PATH": blocked, "AMPLIHACK_KUZU_DB_PATH": ""}
        with patch.dict("os.environ", env, clear=False):
            with pytest.raises(ValueError, match="blocked"):
                KuzuConnector()
