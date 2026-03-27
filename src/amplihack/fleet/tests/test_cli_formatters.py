"""Tests for fleet _cli_formatters -- format_scout_report and format_advance_report.

Tests cover:
- New-style (ScoutResult/AdvanceResult dataclass) calling convention
- Legacy calling convention
- All three output formats: table, json, yaml
- Truncation behavior (MAX_OUTPUT_LENGTH=300, MAX_FINDING_LENGTH=150)
- Error handling for invalid formats

Testing pyramid:
- 100% unit tests (no external dependencies)
"""

from __future__ import annotations

import json

import pytest
import yaml

from amplihack.fleet._cli_formatters import (
    MAX_FINDING_LENGTH,
    MAX_OUTPUT_LENGTH,
    AdvanceResult,
    ScoutResult,
    format_advance_report,
    format_scout_report,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def scout_result_success():
    """A successful ScoutResult with findings and recommendations."""
    return ScoutResult(
        session_id="sess-abc123",
        task="Analyze codebase for auth issues",
        success=True,
        agents_used=2,
        findings=["Found JWT validation in auth.py", "Token expiry not checked"],
        recommendations=["Add expiry validation", "Use RS256 algorithm"],
    )


@pytest.fixture
def scout_result_failure():
    """A failed ScoutResult with error."""
    return ScoutResult(
        session_id="sess-xyz789",
        task="Scout production logs",
        success=False,
        agents_used=1,
        findings=[],
        recommendations=[],
        error="SSH connection refused",
    )


@pytest.fixture
def scout_result_empty():
    """A ScoutResult with no findings or recommendations."""
    return ScoutResult(
        session_id="sess-empty",
        task="Quick scan",
        success=True,
        agents_used=1,
    )


@pytest.fixture
def advance_result_success():
    """A successful AdvanceResult with changes."""
    return AdvanceResult(
        session_id="sess-abc123",
        task="Fix JWT validation",
        success=True,
        agents_used=1,
        steps_completed=3,
        steps_total=3,
        changes_made=["Updated auth.py", "Added test_auth.py"],
        output="All tests pass",
    )


@pytest.fixture
def advance_result_partial():
    """A partial AdvanceResult (some steps done)."""
    return AdvanceResult(
        session_id="sess-partial",
        task="Multi-step refactor",
        success=False,
        agents_used=2,
        steps_completed=1,
        steps_total=5,
        changes_made=[],
        output="",
        error="Network timeout",
    )


@pytest.fixture
def advance_result_empty():
    """An AdvanceResult with no changes."""
    return AdvanceResult(
        session_id="sess-nochange",
        task="Dry run check",
        success=True,
        agents_used=1,
        steps_completed=0,
        steps_total=0,
    )


# ---------------------------------------------------------------------------
# format_scout_report -- table format (new style)
# ---------------------------------------------------------------------------


class TestFormatScoutReportTable:
    """Tests for format_scout_report() with format='table'."""

    def test_table_default_format(self, scout_result_success):
        """Default format is table."""
        report = format_scout_report(scout_result_success)
        assert "Scout Report" in report
        assert "sess-abc123" in report

    def test_table_explicit_format(self, scout_result_success):
        """Explicit format='table' produces table output."""
        report = format_scout_report(scout_result_success, "table")
        assert "Scout Report [+]" in report
        assert "Analyze codebase for auth issues" in report

    def test_table_shows_session_id(self, scout_result_success):
        """Table includes session_id."""
        report = format_scout_report(scout_result_success, "table")
        assert "sess-abc123" in report

    def test_table_shows_task(self, scout_result_success):
        """Table shows task description."""
        report = format_scout_report(scout_result_success, "table")
        assert "Analyze codebase for auth issues" in report

    def test_table_shows_agents(self, scout_result_success):
        """Table shows agent count."""
        report = format_scout_report(scout_result_success, "table")
        assert "2" in report

    def test_table_shows_findings(self, scout_result_success):
        """Table includes findings list."""
        report = format_scout_report(scout_result_success, "table")
        assert "Found JWT validation in auth.py" in report
        assert "Token expiry not checked" in report

    def test_table_shows_recommendations(self, scout_result_success):
        """Table includes recommendations."""
        report = format_scout_report(scout_result_success, "table")
        assert "Add expiry validation" in report
        assert "Use RS256 algorithm" in report

    def test_table_success_icon_plus(self, scout_result_success):
        """Successful result shows [+] icon."""
        report = format_scout_report(scout_result_success, "table")
        assert "[+]" in report

    def test_table_failure_icon_x(self, scout_result_failure):
        """Failed result shows [X] icon."""
        report = format_scout_report(scout_result_failure, "table")
        assert "[X]" in report

    def test_table_shows_error_on_failure(self, scout_result_failure):
        """Failed result includes error message."""
        report = format_scout_report(scout_result_failure, "table")
        assert "SSH connection refused" in report

    def test_table_no_error_on_success(self, scout_result_success):
        """Successful result does not show error field."""
        report = format_scout_report(scout_result_success, "table")
        assert "Error:" not in report

    def test_table_empty_findings_placeholder(self, scout_result_empty):
        """Empty findings shows placeholder."""
        report = format_scout_report(scout_result_empty, "table")
        assert "(none)" in report

    def test_table_shows_completed_status(self, scout_result_success):
        """Successful result shows 'completed' status."""
        report = format_scout_report(scout_result_success, "table")
        assert "completed" in report

    def test_table_shows_failed_status(self, scout_result_failure):
        """Failed result shows 'failed' status."""
        report = format_scout_report(scout_result_failure, "table")
        assert "failed" in report


# ---------------------------------------------------------------------------
# format_scout_report -- json format (new style)
# ---------------------------------------------------------------------------


class TestFormatScoutReportJson:
    """Tests for format_scout_report() with format='json'."""

    def test_json_is_valid(self, scout_result_success):
        """JSON output is valid JSON."""
        report = format_scout_report(scout_result_success, "json")
        data = json.loads(report)
        assert isinstance(data, dict)

    def test_json_contains_session_id(self, scout_result_success):
        """JSON contains session_id."""
        data = json.loads(format_scout_report(scout_result_success, "json"))
        assert data["session_id"] == "sess-abc123"

    def test_json_contains_task(self, scout_result_success):
        """JSON contains task field."""
        data = json.loads(format_scout_report(scout_result_success, "json"))
        assert data["task"] == "Analyze codebase for auth issues"

    def test_json_contains_success(self, scout_result_success):
        """JSON contains success flag."""
        data = json.loads(format_scout_report(scout_result_success, "json"))
        assert data["success"] is True

    def test_json_contains_findings(self, scout_result_success):
        """JSON contains findings list."""
        data = json.loads(format_scout_report(scout_result_success, "json"))
        assert data["findings"] == ["Found JWT validation in auth.py", "Token expiry not checked"]

    def test_json_contains_recommendations(self, scout_result_success):
        """JSON contains recommendations list."""
        data = json.loads(format_scout_report(scout_result_success, "json"))
        assert data["recommendations"] == ["Add expiry validation", "Use RS256 algorithm"]

    def test_json_contains_agents_used(self, scout_result_success):
        """JSON contains agents_used count."""
        data = json.loads(format_scout_report(scout_result_success, "json"))
        assert data["agents_used"] == 2

    def test_json_failure_has_error(self, scout_result_failure):
        """JSON for failure contains error field."""
        data = json.loads(format_scout_report(scout_result_failure, "json"))
        assert data["error"] == "SSH connection refused"
        assert data["success"] is False

    def test_json_success_error_is_none(self, scout_result_success):
        """JSON for success has null error."""
        data = json.loads(format_scout_report(scout_result_success, "json"))
        assert data["error"] is None

    def test_json_contains_metadata(self, scout_result_success):
        """JSON contains metadata field."""
        data = json.loads(format_scout_report(scout_result_success, "json"))
        assert "metadata" in data


# ---------------------------------------------------------------------------
# format_scout_report -- yaml format (new style)
# ---------------------------------------------------------------------------


class TestFormatScoutReportYaml:
    """Tests for format_scout_report() with format='yaml'."""

    def test_yaml_is_valid(self, scout_result_success):
        """YAML output is valid YAML."""
        report = format_scout_report(scout_result_success, "yaml")
        data = yaml.safe_load(report)
        assert isinstance(data, dict)

    def test_yaml_contains_session_id(self, scout_result_success):
        """YAML contains session_id."""
        data = yaml.safe_load(format_scout_report(scout_result_success, "yaml"))
        assert data["session_id"] == "sess-abc123"

    def test_yaml_contains_task(self, scout_result_success):
        """YAML contains task field."""
        data = yaml.safe_load(format_scout_report(scout_result_success, "yaml"))
        assert data["task"] == "Analyze codebase for auth issues"

    def test_yaml_contains_success(self, scout_result_success):
        """YAML contains success flag."""
        data = yaml.safe_load(format_scout_report(scout_result_success, "yaml"))
        assert data["success"] is True

    def test_yaml_contains_findings(self, scout_result_success):
        """YAML contains findings list."""
        data = yaml.safe_load(format_scout_report(scout_result_success, "yaml"))
        assert "Found JWT validation in auth.py" in data["findings"]

    def test_yaml_failure_has_error(self, scout_result_failure):
        """YAML for failure contains error field."""
        data = yaml.safe_load(format_scout_report(scout_result_failure, "yaml"))
        assert data["error"] == "SSH connection refused"


# ---------------------------------------------------------------------------
# format_scout_report -- invalid format
# ---------------------------------------------------------------------------


class TestFormatScoutReportInvalidFormat:
    """Tests for format_scout_report() with invalid format."""

    def test_invalid_format_raises_value_error(self, scout_result_success):
        """Invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid format"):
            format_scout_report(scout_result_success, "xml")

    def test_invalid_format_shows_valid_options(self, scout_result_success):
        """Error message includes valid format options."""
        with pytest.raises(ValueError, match="table"):
            format_scout_report(scout_result_success, "markdown")


# ---------------------------------------------------------------------------
# format_scout_report -- truncation behavior
# ---------------------------------------------------------------------------


class TestFormatScoutReportTruncation:
    """Tests for truncation in format_scout_report()."""

    def test_long_finding_truncated_in_table(self):
        """Findings longer than MAX_FINDING_LENGTH are truncated in table."""
        long_finding = "x" * (MAX_FINDING_LENGTH + 50)
        result = ScoutResult(
            session_id="s1",
            task="task",
            success=True,
            findings=[long_finding],
        )
        report = format_scout_report(result, "table")
        assert "..." in report
        # The full string should NOT appear (it's truncated)
        assert long_finding not in report

    def test_short_finding_not_truncated(self):
        """Findings within MAX_FINDING_LENGTH are not truncated."""
        short_finding = "x" * (MAX_FINDING_LENGTH - 10)
        result = ScoutResult(
            session_id="s1",
            task="task",
            success=True,
            findings=[short_finding],
        )
        report = format_scout_report(result, "table")
        assert short_finding in report

    def test_exact_length_finding_not_truncated(self):
        """Finding at exactly MAX_FINDING_LENGTH is not truncated."""
        exact_finding = "y" * MAX_FINDING_LENGTH
        result = ScoutResult(
            session_id="s1",
            task="task",
            success=True,
            findings=[exact_finding],
        )
        report = format_scout_report(result, "table")
        assert exact_finding in report

    def test_verbose_mode_no_truncation(self):
        """verbose=True skips truncation of findings."""
        long_finding = "z" * (MAX_FINDING_LENGTH + 50)
        result = ScoutResult(
            session_id="s1",
            task="task",
            success=True,
            findings=[long_finding],
        )
        # Third positional arg is verbose_or_adopted_count
        report = format_scout_report(result, "table", True)
        assert long_finding in report

    def test_json_format_no_truncation(self):
        """JSON format includes full finding text (not truncated)."""
        long_finding = "a" * (MAX_FINDING_LENGTH + 100)
        result = ScoutResult(
            session_id="s1",
            task="task",
            success=True,
            findings=[long_finding],
        )
        data = json.loads(format_scout_report(result, "json"))
        assert data["findings"][0] == long_finding


# ---------------------------------------------------------------------------
# format_scout_report -- legacy calling convention
# ---------------------------------------------------------------------------


class TestFormatScoutReportLegacy:
    """Tests for legacy format_scout_report(all_vms, decisions, adopted_count, skip_adopt)."""

    def _make_vm(self, name, sessions=None):
        """Create a minimal VM-like object for legacy tests."""
        from unittest.mock import MagicMock
        vm = MagicMock()
        vm.name = name
        vm.is_running = True
        vm.sessions = sessions or []
        return vm

    def _make_session(self, name, status="idle", branch="main"):
        """Create a minimal session-like object for legacy tests."""
        from unittest.mock import MagicMock
        sess = MagicMock()
        sess.session_name = name
        sess.status = status
        sess.branch = branch
        sess.agent_alive = False
        return sess

    def test_legacy_produces_header(self):
        """Legacy format includes the FLEET SCOUT REPORT header."""
        report = format_scout_report([], [], 0, False)
        assert "FLEET SCOUT REPORT" in report

    def test_legacy_empty_vms(self):
        """Legacy format with no VMs shows zero counts."""
        report = format_scout_report([], [], 0, False)
        assert "Running VMs: 0" in report

    def test_legacy_shows_vm_count(self):
        """Legacy format counts running VMs."""
        vm1 = self._make_vm("vm-1")
        report = format_scout_report([vm1], [], 0, False)
        assert "Running VMs: 1" in report

    def test_legacy_shows_adopted_count(self):
        """Legacy format shows adoption count when not skipped."""
        report = format_scout_report([], [], 5, False)
        assert "Adopted: 5" in report

    def test_legacy_skip_adopt_hides_count(self):
        """Legacy format hides adoption count when skip_adopt=True."""
        report = format_scout_report([], [], 5, True)
        assert "Adopted" not in report

    def test_legacy_shows_next_steps(self):
        """Legacy format includes Next Steps section."""
        report = format_scout_report([], [], 0, False)
        assert "Next Steps" in report

    def test_legacy_shows_session_in_table(self):
        """Legacy format includes sessions in the table."""
        sess = self._make_session("task-1", "idle")
        vm1 = self._make_vm("dev-vm", sessions=[sess])
        report = format_scout_report([vm1], [], 0, False)
        assert "task-1" in report

    def test_legacy_decisions_shown(self):
        """Legacy format shows decision counts."""
        sess = self._make_session("task-1", "idle")
        vm1 = self._make_vm("dev-vm", sessions=[sess])
        decisions = [{"vm": "dev-vm", "session": "task-1", "action": "wait", "confidence": 0.8}]
        report = format_scout_report([vm1], decisions, 0, False)
        assert "wait" in report


# ---------------------------------------------------------------------------
# format_advance_report -- table format (new style)
# ---------------------------------------------------------------------------


class TestFormatAdvanceReportTable:
    """Tests for format_advance_report() with format='table'."""

    def test_table_default_format(self, advance_result_success):
        """Default format is table."""
        report = format_advance_report(advance_result_success)
        assert "Advance Report" in report

    def test_table_shows_session_id(self, advance_result_success):
        """Table includes session_id."""
        report = format_advance_report(advance_result_success, "table")
        assert "sess-abc123" in report

    def test_table_shows_task(self, advance_result_success):
        """Table shows task description."""
        report = format_advance_report(advance_result_success, "table")
        assert "Fix JWT validation" in report

    def test_table_shows_steps(self, advance_result_success):
        """Table shows steps completed/total."""
        report = format_advance_report(advance_result_success, "table")
        assert "3/3" in report

    def test_table_shows_changes(self, advance_result_success):
        """Table includes changes made."""
        report = format_advance_report(advance_result_success, "table")
        assert "Updated auth.py" in report
        assert "Added test_auth.py" in report

    def test_table_shows_output(self, advance_result_success):
        """Table shows output text."""
        report = format_advance_report(advance_result_success, "table")
        assert "All tests pass" in report

    def test_table_success_icon_plus(self, advance_result_success):
        """Successful result shows [+] icon."""
        report = format_advance_report(advance_result_success, "table")
        assert "[+]" in report

    def test_table_failure_icon_x(self, advance_result_partial):
        """Failed result shows [X] icon."""
        report = format_advance_report(advance_result_partial, "table")
        assert "[X]" in report

    def test_table_shows_error_on_failure(self, advance_result_partial):
        """Failed result includes error message."""
        report = format_advance_report(advance_result_partial, "table")
        assert "Network timeout" in report

    def test_table_empty_changes_placeholder(self, advance_result_empty):
        """No changes shows placeholder."""
        report = format_advance_report(advance_result_empty, "table")
        assert "(none)" in report

    def test_table_partial_steps(self, advance_result_partial):
        """Partial completion shows 1/5 steps."""
        report = format_advance_report(advance_result_partial, "table")
        assert "1/5" in report

    def test_table_shows_completed_status(self, advance_result_success):
        """Successful result shows 'completed' status."""
        report = format_advance_report(advance_result_success, "table")
        assert "completed" in report


# ---------------------------------------------------------------------------
# format_advance_report -- json format (new style)
# ---------------------------------------------------------------------------


class TestFormatAdvanceReportJson:
    """Tests for format_advance_report() with format='json'."""

    def test_json_is_valid(self, advance_result_success):
        """JSON output is valid JSON."""
        report = format_advance_report(advance_result_success, "json")
        data = json.loads(report)
        assert isinstance(data, dict)

    def test_json_contains_session_id(self, advance_result_success):
        """JSON contains session_id."""
        data = json.loads(format_advance_report(advance_result_success, "json"))
        assert data["session_id"] == "sess-abc123"

    def test_json_contains_steps(self, advance_result_success):
        """JSON contains steps_completed and steps_total."""
        data = json.loads(format_advance_report(advance_result_success, "json"))
        assert data["steps_completed"] == 3
        assert data["steps_total"] == 3

    def test_json_contains_changes(self, advance_result_success):
        """JSON contains changes_made list."""
        data = json.loads(format_advance_report(advance_result_success, "json"))
        assert "Updated auth.py" in data["changes_made"]

    def test_json_contains_output(self, advance_result_success):
        """JSON contains output field."""
        data = json.loads(format_advance_report(advance_result_success, "json"))
        assert data["output"] == "All tests pass"

    def test_json_failure_has_error(self, advance_result_partial):
        """JSON for failure contains error field."""
        data = json.loads(format_advance_report(advance_result_partial, "json"))
        assert data["error"] == "Network timeout"
        assert data["success"] is False

    def test_json_contains_metadata(self, advance_result_success):
        """JSON contains metadata field."""
        data = json.loads(format_advance_report(advance_result_success, "json"))
        assert "metadata" in data


# ---------------------------------------------------------------------------
# format_advance_report -- yaml format (new style)
# ---------------------------------------------------------------------------


class TestFormatAdvanceReportYaml:
    """Tests for format_advance_report() with format='yaml'."""

    def test_yaml_is_valid(self, advance_result_success):
        """YAML output is valid YAML."""
        report = format_advance_report(advance_result_success, "yaml")
        data = yaml.safe_load(report)
        assert isinstance(data, dict)

    def test_yaml_contains_session_id(self, advance_result_success):
        """YAML contains session_id."""
        data = yaml.safe_load(format_advance_report(advance_result_success, "yaml"))
        assert data["session_id"] == "sess-abc123"

    def test_yaml_contains_changes(self, advance_result_success):
        """YAML contains changes_made list."""
        data = yaml.safe_load(format_advance_report(advance_result_success, "yaml"))
        assert "Updated auth.py" in data["changes_made"]

    def test_yaml_contains_success(self, advance_result_success):
        """YAML contains success flag."""
        data = yaml.safe_load(format_advance_report(advance_result_success, "yaml"))
        assert data["success"] is True

    def test_yaml_failure_has_error(self, advance_result_partial):
        """YAML for failure has error field."""
        data = yaml.safe_load(format_advance_report(advance_result_partial, "yaml"))
        assert data["error"] == "Network timeout"


# ---------------------------------------------------------------------------
# format_advance_report -- invalid format
# ---------------------------------------------------------------------------


class TestFormatAdvanceReportInvalidFormat:
    """Tests for format_advance_report() with invalid format."""

    def test_invalid_format_raises_value_error(self, advance_result_success):
        """Invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid format"):
            format_advance_report(advance_result_success, "xml")


# ---------------------------------------------------------------------------
# format_advance_report -- output truncation
# ---------------------------------------------------------------------------


class TestFormatAdvanceReportTruncation:
    """Tests for truncation in format_advance_report()."""

    def test_long_output_truncated_in_table(self):
        """Output longer than MAX_OUTPUT_LENGTH is truncated in table."""
        long_output = "y" * (MAX_OUTPUT_LENGTH + 100)
        result = AdvanceResult(
            session_id="s1",
            task="task",
            success=True,
            output=long_output,
        )
        report = format_advance_report(result, "table")
        assert "..." in report
        assert long_output not in report

    def test_short_output_not_truncated(self):
        """Output within MAX_OUTPUT_LENGTH is not truncated."""
        short_output = "z" * (MAX_OUTPUT_LENGTH - 10)
        result = AdvanceResult(
            session_id="s1",
            task="task",
            success=True,
            output=short_output,
        )
        report = format_advance_report(result, "table")
        assert short_output in report

    def test_verbose_mode_no_truncation(self):
        """verbose=True skips output truncation."""
        long_output = "w" * (MAX_OUTPUT_LENGTH + 100)
        result = AdvanceResult(
            session_id="s1",
            task="task",
            success=True,
            output=long_output,
        )
        # Third positional arg is verbose
        report = format_advance_report(result, "table", True)
        assert long_output in report

    def test_json_format_no_truncation(self):
        """JSON format includes full output text (not truncated)."""
        long_output = "b" * (MAX_OUTPUT_LENGTH + 200)
        result = AdvanceResult(
            session_id="s1",
            task="task",
            success=True,
            output=long_output,
        )
        data = json.loads(format_advance_report(result, "json"))
        assert data["output"] == long_output


# ---------------------------------------------------------------------------
# format_advance_report -- legacy calling convention
# ---------------------------------------------------------------------------


class TestFormatAdvanceReportLegacy:
    """Tests for legacy format_advance_report(decisions, executed)."""

    def test_legacy_produces_header(self):
        """Legacy format includes the FLEET ADVANCE REPORT header."""
        report = format_advance_report([], [])
        assert "FLEET ADVANCE REPORT" in report

    def test_legacy_empty_inputs(self):
        """Legacy format with empty inputs shows zero sessions."""
        report = format_advance_report([], [])
        assert "Sessions analyzed: 0" in report

    def test_legacy_shows_decision_count(self):
        """Legacy format counts sessions analyzed."""
        decisions = [
            {"action": "wait", "vm": "vm1", "session": "s1"},
            {"action": "send_input", "vm": "vm1", "session": "s2"},
        ]
        report = format_advance_report(decisions, [])
        assert "Sessions analyzed: 2" in report

    def test_legacy_shows_action_counts(self):
        """Legacy format breaks down actions by type."""
        decisions = [
            {"action": "wait"},
            {"action": "wait"},
            {"action": "send_input"},
        ]
        report = format_advance_report(decisions, [])
        assert "wait: 2" in report
        assert "send_input: 1" in report

    def test_legacy_shows_executed_actions(self):
        """Legacy format shows executed actions section."""
        executed = [
            {"vm": "vm1", "session": "s1", "action": "send_input", "executed": True, "error": None}
        ]
        report = format_advance_report([], executed)
        assert "Actions Executed" in report
        assert "vm1/s1" in report

    def test_legacy_executed_ok_status(self):
        """Legacy format shows OK for successful execution."""
        executed = [
            {"vm": "vm1", "session": "s1", "action": "send_input",
             "executed": True, "error": None}
        ]
        report = format_advance_report([], executed)
        assert "[OK]" in report

    def test_legacy_executed_error_status(self):
        """Legacy format shows ERROR for failed execution."""
        executed = [
            {"vm": "vm1", "session": "s1", "action": "restart",
             "executed": False, "error": "VM unreachable"}
        ]
        report = format_advance_report([], executed)
        assert "[ERROR]" in report
        assert "VM unreachable" in report

    def test_legacy_no_executed_no_section(self):
        """Legacy format omits 'Actions Executed' when empty."""
        report = format_advance_report([{"action": "wait"}], [])
        assert "Actions Executed" not in report

    def test_legacy_none_defaults(self):
        """Legacy format handles None defaults gracefully."""
        # format_advance_report(decisions) with no executed arg
        report = format_advance_report([{"action": "wait"}])
        assert "FLEET ADVANCE REPORT" in report
        assert "Sessions analyzed: 1" in report
