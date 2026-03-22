"""
Gadugi YAML scenario execution for PR #3390 (issues #3022 and #3023).

Actually executes all 15 bash-based gadugi scenarios from
tests/gadugi/bl-001-bl-002-default-workflow-idempotency.yaml
and verifies output assertions. This goes beyond YAML structure
validation — each launch action runs in a real subprocess and
verify_output assertions are checked against captured stdout.
"""

import re
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

GADUGI_DIR = Path(__file__).parent.parent / "gadugi"
SCENARIO_FILE = GADUGI_DIR / "bl-001-bl-002-default-workflow-idempotency.yaml"
REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
RECIPE_PATH = REPO_ROOT / "amplifier-bundle" / "recipes" / "default-workflow.yaml"


def load_yaml(path: Path) -> dict[str, Any]:
    with open(path) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def scenario():
    return load_yaml(SCENARIO_FILE)


@pytest.fixture(scope="module")
def recipe_content():
    return RECIPE_PATH.read_text()


@pytest.fixture(scope="module")
def steps(scenario):
    return scenario["scenario"]["steps"]


# ---------------------------------------------------------------------------
# YAML Structure Tests
# ---------------------------------------------------------------------------


class TestYAMLStructure:
    """Validate gadugi YAML scenarios have correct structure."""

    def test_valid_yaml_syntax(self):
        data = load_yaml(SCENARIO_FILE)
        assert data is not None

    def test_has_required_fields(self, scenario):
        s = scenario["scenario"]
        for field in ["name", "description", "type", "steps", "tags"]:
            assert field in s, f"Missing required field: {field}"

    def test_type_is_cli(self, scenario):
        assert scenario["scenario"]["type"] == "cli"

    def test_has_issue_tags(self, scenario):
        tags = scenario["scenario"]["tags"]
        assert "issue-3022" in tags
        assert "issue-3023" in tags

    def test_minimum_step_count(self, scenario):
        steps = scenario["scenario"]["steps"]
        assert len(steps) >= 30, f"Expected >= 30 steps (launch + verify), got {len(steps)}"

    def test_has_prerequisites(self, scenario):
        prereqs = scenario["scenario"].get("prerequisites", [])
        assert len(prereqs) >= 2


# ---------------------------------------------------------------------------
# Actual Execution: run each launch step and verify assertions
# ---------------------------------------------------------------------------


def _parse_execution_pairs(steps: list[dict]) -> list[dict]:
    """Parse steps into (launch, [verify_output...]) groups."""
    pairs = []
    i = 0
    while i < len(steps):
        step = steps[i]
        if step.get("action") == "launch":
            group = {
                "launch": step,
                "verifications": [],
                "description": step.get("description", f"step-{i}"),
            }
            i += 1
            while i < len(steps) and steps[i].get("action") == "verify_output":
                group["verifications"].append(steps[i])
                i += 1
            pairs.append(group)
        else:
            i += 1
    return pairs


def _run_bash(args: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
    """Execute a bash launch step from the repo root."""
    return subprocess.run(
        ["bash"] + args,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(REPO_ROOT),
    )


@pytest.fixture(scope="module")
def execution_pairs(steps):
    return _parse_execution_pairs(steps)


class TestScenarioExecution:
    """Execute all 15 gadugi scenarios and verify output assertions."""

    @pytest.fixture(scope="class")
    def all_results(self, execution_pairs):
        """Run all scenarios once and cache results."""
        results = []
        for pair in execution_pairs:
            launch = pair["launch"]
            args = launch.get("args", [])
            timeout_str = launch.get("timeout", "30s")
            timeout = int(re.sub(r"[^0-9]", "", timeout_str)) if timeout_str else 30
            timeout = max(timeout, 10)

            result = _run_bash(args, timeout=timeout)
            combined = result.stdout + result.stderr
            results.append(
                {
                    "description": pair["description"],
                    "output": combined,
                    "returncode": result.returncode,
                    "verifications": pair["verifications"],
                }
            )
        return results

    def test_scenario_count(self, execution_pairs):
        """Must have 15 launch scenarios."""
        assert len(execution_pairs) == 15, f"Expected 15 scenarios, got {len(execution_pairs)}"

    def test_all_scenarios_exit_zero(self, all_results):
        """Every scenario must exit 0."""
        failures = []
        for r in all_results:
            if r["returncode"] != 0:
                failures.append(
                    f"  {r['description']}: exit {r['returncode']}\n    output: {r['output'][:200]}"
                )
        assert not failures, "Scenarios with non-zero exit:\n" + "\n".join(failures)

    def test_all_verify_output_assertions(self, all_results):
        """Every verify_output 'contains' assertion must match."""
        failures = []
        for r in all_results:
            for v in r["verifications"]:
                expected = v.get("contains", "")
                if expected and expected not in r["output"]:
                    failures.append(
                        f"  {r['description']}: missing '{expected}'\n"
                        f"    verify: {v.get('description', '')}\n"
                        f"    output snippet: {r['output'][:300]}"
                    )
                pattern = v.get("matches", "")
                if pattern and not re.search(pattern, r["output"]):
                    failures.append(
                        f"  {r['description']}: regex '{pattern}' not found\n"
                        f"    verify: {v.get('description', '')}\n"
                        f"    output snippet: {r['output'][:300]}"
                    )
        assert not failures, "Failed verify_output assertions:\n" + "\n".join(failures)


# ---------------------------------------------------------------------------
# Individual scenario tests (one test per scenario for granular reporting)
# ---------------------------------------------------------------------------


def _make_individual_test(idx: int, pair: dict):
    """Generate a test function for a single scenario."""

    def test_func(self):
        launch = pair["launch"]
        args = launch.get("args", [])
        timeout_str = launch.get("timeout", "30s")
        timeout = int(re.sub(r"[^0-9]", "", timeout_str)) if timeout_str else 30
        timeout = max(timeout, 10)

        result = _run_bash(args, timeout=timeout)
        combined = result.stdout + result.stderr

        assert result.returncode == 0, (
            f"Scenario '{pair['description']}' exited {result.returncode}:\n{combined[:500]}"
        )

        for v in pair["verifications"]:
            expected = v.get("contains", "")
            if expected:
                assert expected in combined, (
                    f"Missing '{expected}' in output of '{pair['description']}':\n{combined[:500]}"
                )
            pattern = v.get("matches", "")
            if pattern:
                assert re.search(pattern, combined), (
                    f"Regex '{pattern}' not found in output of '{pair['description']}':\n{combined[:500]}"
                )

    test_func.__doc__ = f"Scenario {idx + 1}: {pair['description']}"
    return test_func


# Dynamically generate individual test methods
_pairs = _parse_execution_pairs(load_yaml(SCENARIO_FILE)["scenario"]["steps"])


class TestIndividualScenarios:
    """One test per gadugi scenario for granular pass/fail reporting."""


for _idx, _pair in enumerate(_pairs):
    setattr(
        TestIndividualScenarios,
        f"test_scenario_{_idx + 1:02d}_{re.sub(r'[^a-z0-9]+', '_', _pair['description'].lower()).strip('_')[:60]}",
        _make_individual_test(_idx, _pair),
    )
