"""
Gadugi YAML scenario validation and behavioral assertions for PR #3268.

Validates that the gadugi outside-in test scenario for issue #3233 (cli crash
handler propagation) is structurally valid, and executes grep-based behavioral
assertions against the actual source code (src/amplihack/cli.py) to verify:

- No nested try/except in the crash handler section
- crash_session is called without being wrapped in its own try/except
- os.chdir is called without being wrapped in its own try/except
- logging.debug (module-level) is replaced with logger.debug (instance)
"""

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

GADUGI_DIR = Path(__file__).parent.parent / "gadugi"
CLI_PATH = Path(__file__).parent.parent.parent / "src" / "amplihack" / "cli.py"


def load_yaml(path: Path) -> dict[str, Any]:
    with open(path) as f:
        return yaml.safe_load(f)


@pytest.fixture
def crash_handler_scenario():
    return load_yaml(GADUGI_DIR / "cli-crash-handler-propagation.yaml")


@pytest.fixture
def cli_source():
    return CLI_PATH.read_text()


@pytest.fixture
def launch_command_source(cli_source):
    """Extract just the launch_command function body (up to the next top-level def)."""
    lines = cli_source.splitlines()
    start = None
    end = None
    for i, line in enumerate(lines):
        if line.startswith("def launch_command("):
            start = i
        elif start is not None and i > start and re.match(r"^def \w+", line):
            end = i
            break
    if start is None:
        pytest.fail("Could not find launch_command in cli.py")
    if end is None:
        end = len(lines)
    return "\n".join(lines[start:end])


class TestGadugiYAMLStructure:
    """Validate the crash-handler-propagation YAML scenario has correct structure."""

    REQUIRED_FIELDS = ["name", "description", "type", "steps"]

    def test_valid_yaml_syntax(self, crash_handler_scenario):
        assert crash_handler_scenario is not None, "YAML file is empty"

    def test_has_required_fields(self, crash_handler_scenario):
        scenario = crash_handler_scenario.get("scenario", {})
        for field in self.REQUIRED_FIELDS:
            assert field in scenario, f"Missing required field: {field}"

    def test_has_valid_type(self, crash_handler_scenario):
        scenario_type = crash_handler_scenario.get("scenario", {}).get("type")
        assert scenario_type == "cli", f"type should be 'cli', got '{scenario_type}'"

    def test_has_tags(self, crash_handler_scenario):
        tags = crash_handler_scenario.get("scenario", {}).get("tags", [])
        assert len(tags) > 0, "Must have tags"

    def test_has_issue_tags(self, crash_handler_scenario):
        tags = crash_handler_scenario.get("scenario", {}).get("tags", [])
        assert "issue-3233" in tags, "Must be tagged with issue-3233"
        assert "issue-3268" in tags, "Must be tagged with issue-3268"

    def test_has_prerequisites(self, crash_handler_scenario):
        prereqs = crash_handler_scenario.get("scenario", {}).get("prerequisites", [])
        assert len(prereqs) > 0, "Must have prerequisites"

    def test_steps_have_action_and_description(self, crash_handler_scenario):
        steps = crash_handler_scenario.get("scenario", {}).get("steps", [])
        assert len(steps) > 0, "Must have at least one step"
        for i, step in enumerate(steps):
            assert "action" in step, f"Step {i} missing 'action'"
            assert "description" in step, f"Step {i} missing 'description'"


class TestCrashHandlerScenarioContent:
    """Validate scenario content covers the required verification points."""

    def test_covers_crash_session_check(self, crash_handler_scenario):
        steps = crash_handler_scenario["scenario"]["steps"]
        found = any(
            "crash_session" in str(s.get("pattern", ""))
            or "crash_session" in str(s.get("contains", ""))
            or "crash_session" in s.get("description", "")
            for s in steps
        )
        assert found, "Must verify crash_session behavior"

    def test_covers_os_chdir_check(self, crash_handler_scenario):
        steps = crash_handler_scenario["scenario"]["steps"]
        found = any(
            "os.chdir" in str(s.get("pattern", ""))
            or "os.chdir" in str(s.get("contains", ""))
            or "os.chdir" in s.get("description", "")
            for s in steps
        )
        assert found, "Must verify os.chdir behavior"

    def test_covers_logger_debug_check(self, crash_handler_scenario):
        steps = crash_handler_scenario["scenario"]["steps"]
        found = any(
            "logger.debug" in str(s.get("contains", ""))
            or "logger.debug" in s.get("description", "")
            for s in steps
        )
        assert found, "Must verify logger.debug usage"

    def test_covers_re_raise_check(self, crash_handler_scenario):
        steps = crash_handler_scenario["scenario"]["steps"]
        found = any(
            "raise" in str(s.get("pattern", "")) or "re-raise" in s.get("description", "").lower()
            for s in steps
        )
        assert found, "Must verify exception re-raise"


class TestBehavioralAssertions:
    """Grep-based assertions against cli.py source to verify crash handler fix."""

    def test_no_nested_try_in_crash_handler(self, launch_command_source):
        """The crash handler must not contain nested try blocks.

        After the top-level 'try:', there should be no additional 'try:' lines
        within launch_command.
        """
        lines = launch_command_source.splitlines()
        try_count = sum(1 for line in lines if re.match(r"\s+try:\s*$", line))
        assert try_count == 1, (
            f"Expected exactly 1 try block in launch_command, found {try_count}. "
            "Nested try/except blocks silently swallow errors."
        )

    def test_crash_session_not_wrapped_in_try(self, launch_command_source):
        """crash_session() must be called directly, not inside a nested try/except."""
        lines = launch_command_source.splitlines()
        for i, line in enumerate(lines):
            if "crash_session" in line:
                # Check the 1-3 lines before crash_session for a nested try
                context = "\n".join(lines[max(0, i - 3) : i])
                assert "try:" not in context, (
                    "crash_session() is wrapped in a nested try block — "
                    "failures would be silently swallowed"
                )
                break
        else:
            pytest.fail("crash_session() not found in launch_command")

    def test_os_chdir_not_wrapped_in_try(self, launch_command_source):
        """os.chdir() must be in finally block, not inside a nested try/except."""
        lines = launch_command_source.splitlines()
        for i, line in enumerate(lines):
            if "os.chdir(" in line and "original_cwd" in line:
                # Check the 1-3 lines before os.chdir for a nested try
                context = "\n".join(lines[max(0, i - 3) : i])
                assert "try:" not in context or "finally:" in context, (
                    "os.chdir() is wrapped in a nested try block — "
                    "failures would be silently swallowed"
                )
                break
        else:
            pytest.fail("os.chdir(original_cwd) not found in launch_command")

    def test_uses_logger_debug_not_logging_debug(self, launch_command_source):
        """Must use logger.debug (instance) not logging.debug (module-level)."""
        assert "logging.debug" not in launch_command_source, (
            "Found 'logging.debug' in launch_command — should use 'logger.debug' "
            "(the module-level logger instance)"
        )
        assert "logger.debug" in launch_command_source, (
            "Expected 'logger.debug' in launch_command crash handler"
        )

    def test_except_block_reraises(self, launch_command_source):
        """The except block must re-raise the exception."""
        lines = launch_command_source.splitlines()
        in_except = False
        found_raise = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("except "):
                in_except = True
            elif in_except and stripped == "raise":
                found_raise = True
                break
            elif in_except and re.match(r"^(def |class |finally:)", stripped):
                break
        assert found_raise, (
            "except block in launch_command does not re-raise — "
            "exceptions would be silently swallowed"
        )

    def test_finally_block_restores_cwd(self, launch_command_source):
        """The finally block must restore the original working directory."""
        lines = launch_command_source.splitlines()
        in_finally = False
        found_chdir = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("finally:"):
                in_finally = True
            elif in_finally and "os.chdir(" in stripped:
                found_chdir = True
                break
        assert found_chdir, "finally block must call os.chdir() to restore CWD"
