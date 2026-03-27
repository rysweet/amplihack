"""Outside-in tests for fleet CLI session operations.

Tests the fleet module from a user's perspective:
- Create and manage fleet sessions
- Run scout and advance agents
- Format reports in multiple output formats
- List and query sessions

These tests exercise the public API in _cli_session_ops.py and _cli_formatters.py.
"""

from __future__ import annotations

import json

import pytest

from amplihack.fleet import (
    AdvanceResult,
    FleetConfig,
    FleetSession,
    ScoutResult,
    format_advance_report,
    format_scout_report,
    get_fleet_session_status,
    list_fleet_sessions,
    run_advance,
    run_scout,
    start_fleet_session,
    stop_fleet_session,
)
from amplihack.fleet._cli_session_ops import _active_sessions


@pytest.fixture(autouse=True)
def clear_sessions():
    """Clear in-memory session registry between tests."""
    _active_sessions.clear()
    yield
    _active_sessions.clear()


# ---- Session lifecycle ----


class TestFleetSessionLifecycle:
    def test_start_creates_active_session(self):
        session = start_fleet_session("test-session", FleetConfig(persist=False))
        assert isinstance(session, FleetSession)
        assert session.name == "test-session"
        assert session.is_active()
        assert session.session_id in _active_sessions

    def test_stop_removes_session_from_active(self):
        session = start_fleet_session("stop-test", FleetConfig(persist=False))
        sid = session.session_id
        result = stop_fleet_session(sid)
        assert result is True
        assert sid not in _active_sessions

    def test_stop_unknown_session_returns_false(self):
        assert stop_fleet_session("nonexistent-id") is False

    def test_session_status_returns_expected_keys(self):
        session = start_fleet_session("status-test", FleetConfig(persist=False))
        status = get_fleet_session_status(session.session_id)
        assert status["name"] == "status-test"
        assert status["status"] == "active"
        assert "config" in status
        assert "scout_count" in status
        assert "advance_count" in status

    def test_session_status_unknown_returns_empty(self):
        assert get_fleet_session_status("no-such-session") == {}

    def test_list_sessions_includes_active(self):
        s1 = start_fleet_session("alpha", FleetConfig(persist=False))
        s2 = start_fleet_session("beta", FleetConfig(persist=False))
        sessions = list_fleet_sessions(active_only=True)
        ids = {s["session_id"] for s in sessions}
        assert s1.session_id in ids
        assert s2.session_id in ids

    def test_list_sessions_newest_first(self):
        s1 = start_fleet_session("first", FleetConfig(persist=False))
        s2 = start_fleet_session("second", FleetConfig(persist=False))
        sessions = list_fleet_sessions(active_only=True)
        # second session created after first so should appear first
        assert sessions[0]["session_id"] == s2.session_id or sessions[0]["created_at"] >= sessions[-1]["created_at"]

    def test_custom_config_respected(self):
        cfg = FleetConfig(max_scout_agents=5, max_advance_agents=4, timeout_seconds=600, persist=False)
        session = start_fleet_session("configured", cfg)
        status = get_fleet_session_status(session.session_id)
        assert status["config"]["max_scout_agents"] == 5
        assert status["config"]["max_advance_agents"] == 4
        assert status["config"]["timeout_seconds"] == 600


# ---- Scout operations ----


class TestRunScout:
    def test_run_scout_returns_scout_result(self):
        session = start_fleet_session("scout-test", FleetConfig(persist=False))
        result = run_scout(session, "analyze codebase")
        assert isinstance(result, ScoutResult)
        assert result.session_id == session.session_id
        assert result.task == "analyze codebase"
        assert result.success is True

    def test_scout_appended_to_session(self):
        session = start_fleet_session("scout-append", FleetConfig(persist=False))
        run_scout(session, "task 1")
        run_scout(session, "task 2")
        assert len(session.scout_results) == 2

    def test_scout_agents_capped_by_config(self):
        cfg = FleetConfig(max_scout_agents=2, persist=False)
        session = start_fleet_session("cap-test", cfg)
        result = run_scout(session, "analyze", agents=10)
        assert result.agents_used == 2

    def test_scout_with_findings(self):
        session = start_fleet_session("findings-test", FleetConfig(persist=False))
        findings = ["Found module A", "Found module B"]
        result = run_scout(session, "explore", findings=findings)
        assert result.findings == findings

    def test_scout_count_reflected_in_status(self):
        session = start_fleet_session("count-scout", FleetConfig(persist=False))
        run_scout(session, "scan")
        status = get_fleet_session_status(session.session_id)
        assert status["scout_count"] == 1


# ---- Advance operations ----


class TestRunAdvance:
    def test_run_advance_returns_advance_result(self):
        session = start_fleet_session("advance-test", FleetConfig(persist=False))
        result = run_advance(session, "implement feature")
        assert isinstance(result, AdvanceResult)
        assert result.session_id == session.session_id
        assert result.task == "implement feature"
        assert result.success is True

    def test_advance_steps_match_plan(self):
        session = start_fleet_session("steps-test", FleetConfig(persist=False))
        plan = ["step 1", "step 2", "step 3"]
        result = run_advance(session, "execute", plan=plan)
        assert result.steps_completed == 3
        assert result.steps_total == 3

    def test_advance_agents_capped_by_config(self):
        cfg = FleetConfig(max_advance_agents=1, persist=False)
        session = start_fleet_session("advance-cap", cfg)
        result = run_advance(session, "task", agents=5)
        assert result.agents_used == 1

    def test_advance_changes_recorded(self):
        session = start_fleet_session("changes-test", FleetConfig(persist=False))
        changes = ["src/foo.py", "tests/test_foo.py"]
        result = run_advance(session, "add feature", changes_made=changes)
        assert result.changes_made == changes

    def test_advance_count_reflected_in_status(self):
        session = start_fleet_session("count-advance", FleetConfig(persist=False))
        run_advance(session, "execute")
        status = get_fleet_session_status(session.session_id)
        assert status["advance_count"] == 1


# ---- Formatting: scout reports ----


class TestFormatScoutReport:
    def _make_scout(self, **kwargs) -> ScoutResult:
        defaults = dict(
            session_id="sess-123",
            task="analyze code",
            success=True,
            agents_used=2,
            findings=["Finding A", "Finding B"],
            recommendations=["Use module X"],
        )
        defaults.update(kwargs)
        return ScoutResult(**defaults)

    def test_table_format_contains_key_info(self):
        result = self._make_scout()
        output = format_scout_report(result, format="table")
        assert "sess-123" in output
        assert "analyze code" in output
        assert "Finding A" in output
        assert "completed" in output

    def test_json_format_is_valid_json(self):
        result = self._make_scout()
        output = format_scout_report(result, format="json")
        data = json.loads(output)
        assert data["session_id"] == "sess-123"
        assert data["task"] == "analyze code"
        assert data["findings"] == ["Finding A", "Finding B"]

    def test_yaml_format_contains_task(self):
        result = self._make_scout()
        output = format_scout_report(result, format="yaml")
        assert "analyze code" in output
        assert "session_id" in output

    def test_failed_scout_shows_error(self):
        result = self._make_scout(success=False, error="Agent timeout", findings=[])
        output = format_scout_report(result, format="table")
        assert "Agent timeout" in output

    def test_invalid_format_raises_value_error(self):
        result = self._make_scout()
        with pytest.raises(ValueError, match="Invalid format"):
            format_scout_report(result, format="xml")

    def test_empty_findings_shows_none_label(self):
        result = self._make_scout(findings=[], recommendations=[])
        output = format_scout_report(result, format="table")
        assert "(none)" in output

    def test_verbose_preserves_long_text(self):
        long_finding = "A" * 500
        result = self._make_scout(findings=[long_finding])
        verbose_output = format_scout_report(result, format="table", verbose=True)
        assert long_finding in verbose_output

    def test_non_verbose_truncates_long_text(self):
        long_finding = "A" * 500
        result = self._make_scout(findings=[long_finding])
        output = format_scout_report(result, format="table", verbose=False)
        assert "..." in output


# ---- Formatting: advance reports ----


class TestFormatAdvanceReport:
    def _make_advance(self, **kwargs) -> AdvanceResult:
        defaults = dict(
            session_id="sess-456",
            task="implement auth",
            success=True,
            agents_used=1,
            steps_completed=3,
            steps_total=3,
            changes_made=["auth.py", "tests/test_auth.py"],
            output="Authentication implemented",
        )
        defaults.update(kwargs)
        return AdvanceResult(**defaults)

    def test_table_format_contains_key_info(self):
        result = self._make_advance()
        output = format_advance_report(result, format="table")
        assert "sess-456" in output
        assert "implement auth" in output
        assert "auth.py" in output
        assert "3/3" in output

    def test_json_format_is_valid_json(self):
        result = self._make_advance()
        output = format_advance_report(result, format="json")
        data = json.loads(output)
        assert data["session_id"] == "sess-456"
        assert data["steps_completed"] == 3
        assert data["changes_made"] == ["auth.py", "tests/test_auth.py"]

    def test_yaml_format_contains_task(self):
        result = self._make_advance()
        output = format_advance_report(result, format="yaml")
        assert "implement auth" in output

    def test_failed_advance_shows_error(self):
        result = self._make_advance(success=False, error="Build failed", changes_made=[])
        output = format_advance_report(result, format="table")
        assert "Build failed" in output

    def test_invalid_format_raises_value_error(self):
        result = self._make_advance()
        with pytest.raises(ValueError, match="Invalid format"):
            format_advance_report(result, format="csv")

    def test_no_changes_shows_none_label(self):
        result = self._make_advance(changes_made=[], output="")
        output = format_advance_report(result, format="table")
        assert "(none)" in output

    def test_verbose_preserves_long_output(self):
        long_output = "X" * 600
        result = self._make_advance(output=long_output)
        verbose_output = format_advance_report(result, format="table", verbose=True)
        assert long_output in verbose_output

    def test_non_verbose_truncates_long_output(self):
        long_output = "X" * 600
        result = self._make_advance(output=long_output)
        output = format_advance_report(result, format="table", verbose=False)
        assert "..." in output


# ---- Module separation verification ----


class TestModuleSeparation:
    """Verify that formatting and session ops are properly separated."""

    def test_formatters_importable_independently(self):
        from amplihack.fleet._cli_formatters import format_advance_report, format_scout_report

        assert callable(format_scout_report)
        assert callable(format_advance_report)

    def test_session_ops_importable_independently(self):
        from amplihack.fleet._cli_session_ops import (
            list_fleet_sessions,
            run_advance,
            run_scout,
            start_fleet_session,
            stop_fleet_session,
        )

        assert callable(start_fleet_session)
        assert callable(stop_fleet_session)
        assert callable(run_scout)
        assert callable(run_advance)
        assert callable(list_fleet_sessions)

    def test_result_types_defined_in_formatters(self):
        from amplihack.fleet._cli_formatters import AdvanceResult, ScoutResult

        assert ScoutResult.__module__ == "amplihack.fleet._cli_formatters"
        assert AdvanceResult.__module__ == "amplihack.fleet._cli_formatters"

    def test_session_ops_reexports_formatters_from_formatters_module(self):
        from amplihack.fleet._cli_session_ops import format_advance_report, format_scout_report
        from amplihack.fleet._cli_formatters import (
            format_advance_report as fmt_adv,
            format_scout_report as fmt_sco,
        )

        # Re-exported functions are the same objects as those defined in _cli_formatters
        assert format_scout_report is fmt_sco
        assert format_advance_report is fmt_adv
