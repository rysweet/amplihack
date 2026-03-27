"""Regression test for issue #3069: force_single_workstream Bool/String coercion.

When force_single_workstream is passed as user_context={'force_single_workstream': 'true'},
the Python wrapper sends --set force_single_workstream=true to the Rust binary.
The Rust CLI's parse_context_value converts "true" to Value::Bool(true).

The recipe condition `force_single_workstream == 'true'` then compares
Bool(true) against String("true"). Without cross-type coercion in the
condition evaluator's values_equal function, this comparison returns false,
causing execute-single-round-1 to be skipped and the parallel path to fail
with "workstreams config has 0 entries".

Fix: recipe-runner-rs condition.rs values_equal now handles Bool/String
cross-type coercion (Bool(true) == String("true"), Bool(false) == String("false")).
"""

import json
import subprocess
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _find_recipe_runner_binary() -> str | None:
    """Find the recipe-runner-rs binary."""
    import shutil

    for candidate in [
        "recipe-runner-rs",
        str(Path.home() / ".cargo" / "bin" / "recipe-runner-rs"),
    ]:
        if shutil.which(candidate):
            return shutil.which(candidate)
    return None


def test_bool_string_coercion_in_condition():
    """Verify that Bool(true) == String('true') in conditions (issue #3069).

    Creates a minimal recipe where a context variable defaults to "false"
    (YAML string), then overrides it to true via --set (which becomes Bool).
    A conditional step checks `flag == 'true'` and should NOT be skipped.
    """
    binary = _find_recipe_runner_binary()
    if binary is None:
        import pytest
        pytest.skip("recipe-runner-rs binary not found")

    recipe_yaml = """\
name: "test-bool-string-coercion"
context:
  flag: "false"
steps:
  - id: "check-flag-true"
    command: "echo FLAG_IS_TRUE"
    condition: "flag == 'true'"
    output: "result_true"
  - id: "check-flag-not-true"
    command: "echo FLAG_IS_NOT_TRUE"
    condition: "flag != 'true'"
    output: "result_not_true"
"""

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", prefix="test-3069-", delete=False
    ) as f:
        f.write(recipe_yaml)
        recipe_path = f.name

    try:
        # Test 1: flag=true via --set (Bool coercion)
        result = subprocess.run(
            [binary, recipe_path, "--output-format", "json", "--set", "flag=true"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0, f"Runner failed: {result.stderr}"
        data = json.loads(result.stdout)
        assert data["success"], f"Recipe failed: {data}"

        steps = {s["step_id"]: s["status"] for s in data["step_results"]}
        assert steps["check-flag-true"] == "completed", (
            f"check-flag-true should run when flag=true (Bool), got: {steps['check-flag-true']}"
        )
        assert steps["check-flag-not-true"] == "skipped", (
            f"check-flag-not-true should be skipped when flag=true (Bool), got: {steps['check-flag-not-true']}"
        )

        # Test 2: flag=false via --set (Bool coercion, opposite)
        result2 = subprocess.run(
            [binary, recipe_path, "--output-format", "json", "--set", "flag=false"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        assert result2.returncode == 0, f"Runner failed: {result2.stderr}"
        data2 = json.loads(result2.stdout)
        assert data2["success"], f"Recipe failed: {data2}"

        steps2 = {s["step_id"]: s["status"] for s in data2["step_results"]}
        assert steps2["check-flag-true"] == "skipped", (
            f"check-flag-true should be skipped when flag=false (Bool), got: {steps2['check-flag-true']}"
        )
        assert steps2["check-flag-not-true"] == "completed", (
            f"check-flag-not-true should run when flag=false (Bool), got: {steps2['check-flag-not-true']}"
        )
    finally:
        Path(recipe_path).unlink(missing_ok=True)


def test_bool_string_inequality_coercion():
    """Verify that Bool(true) != String('false') and Bool(false) != String('true').

    Complements test_bool_string_coercion_in_condition by testing the != operator
    which is used in the create-workstreams-config condition:
    `force_single_workstream != 'true'`
    """
    binary = _find_recipe_runner_binary()
    if binary is None:
        import pytest
        pytest.skip("recipe-runner-rs binary not found")

    recipe_yaml = """\
name: "test-bool-string-inequality"
context:
  flag: "false"
steps:
  - id: "flag-is-not-false"
    command: "echo NOT_FALSE"
    condition: "flag != 'false'"
    output: "result1"
  - id: "flag-is-not-true"
    command: "echo NOT_TRUE"
    condition: "flag != 'true'"
    output: "result2"
"""

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", prefix="test-3069-neq-", delete=False
    ) as f:
        f.write(recipe_yaml)
        recipe_path = f.name

    try:
        # flag=true (Bool) -> "flag != 'false'" should be completed, "flag != 'true'" should be skipped
        result = subprocess.run(
            [binary, recipe_path, "--output-format", "json", "--set", "flag=true"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0, f"Runner failed: {result.stderr}"
        data = json.loads(result.stdout)
        steps = {s["step_id"]: s["status"] for s in data["step_results"]}

        assert steps["flag-is-not-false"] == "completed", (
            f"Bool(true) != String('false') should be true, got: {steps['flag-is-not-false']}"
        )
        assert steps["flag-is-not-true"] == "skipped", (
            f"Bool(true) != String('true') should be false, got: {steps['flag-is-not-true']}"
        )
    finally:
        Path(recipe_path).unlink(missing_ok=True)
