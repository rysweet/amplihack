"""TDD tests for step-transition JSONL markers (#3625).

These tests define the expected behavior for step-transition JSONL emission
in _drain_stderr(). They will FAIL until the implementation is added to:
  - src/amplihack/recipes/rust_runner_execution.py
  - src/amplihack/recipes/rust_runner.py

Expected behavior: when _drain_stderr() encounters a progress marker
(\u25b6, \u2713, \u2717, \u2298), it should emit a machine-readable JSONL line to stderr
with the schema: {"type":"step_transition","step":"<name>","status":"<status>","ts":<epoch>}
"""

from __future__ import annotations

import io
import json
import sys
from unittest.mock import patch

import pytest

from amplihack.recipes.rust_runner import run_recipe_via_rust
from amplihack.recipes.rust_runner_execution import (
    _meaningful_stderr_tail,
)


@pytest.fixture(autouse=True)
def _mock_runner_version_check():
    """Bypass version gating so tests focus on JSONL behavior."""
    with patch(
        "amplihack.recipes.rust_runner.runner_binary.raise_for_runner_version",
        return_value=None,
    ):
        yield


def _make_rust_output(success: bool = True) -> str:
    return json.dumps(
        {
            "recipe_name": "test-recipe",
            "success": success,
            "step_results": [
                {"step_id": "s1", "status": "Completed", "output": "ok", "error": ""},
            ],
            "context": {},
        }
    )


class FakePopen:
    """Minimal Popen stand-in with controllable stdout/stderr."""

    def __init__(self, stdout: str, stderr: str, returncode: int = 0):
        self.stdout = io.StringIO(stdout)
        self.stderr = io.StringIO(stderr)
        self._returncode = returncode
        self.pid = 12345

    def wait(self, timeout=None):
        return self._returncode


class TestStepTransitionStart:
    """_drain_stderr must emit a step_transition JSON line when \u25b6 is detected."""

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary",
        return_value="/usr/bin/recipe-runner-rs",
    )
    @patch("subprocess.Popen")
    def test_start_marker_emits_jsonl(self, mock_popen, mock_find):
        mock_popen.return_value = FakePopen(
            stdout=_make_rust_output(),
            stderr="\u25b6 classify-and-decompose (agent)\n",
        )
        captured = io.StringIO()
        with patch.object(sys, "stderr", captured):
            run_recipe_via_rust("test-recipe", progress=True)
        lines = captured.getvalue().strip().splitlines()
        json_lines = [ln for ln in lines if ln.startswith("{")]
        assert len(json_lines) >= 1, (
            f"Expected at least one JSONL step_transition line on stderr; got lines: {lines}"
        )
        obj = json.loads(json_lines[0])
        assert obj["type"] == "step_transition"
        assert obj["step"] == "classify-and-decompose"
        assert obj["status"] == "start"
        assert "ts" in obj

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary",
        return_value="/usr/bin/recipe-runner-rs",
    )
    @patch("subprocess.Popen")
    def test_start_marker_strips_parenthetical(self, mock_popen, mock_find):
        mock_popen.return_value = FakePopen(
            stdout=_make_rust_output(),
            stderr="\u25b6 activate-workflow (bash)\n",
        )
        captured = io.StringIO()
        with patch.object(sys, "stderr", captured):
            run_recipe_via_rust("test-recipe", progress=True)
        json_lines = [ln for ln in captured.getvalue().strip().splitlines() if ln.startswith("{")]
        assert len(json_lines) >= 1
        obj = json.loads(json_lines[0])
        assert obj["step"] == "activate-workflow"
        assert "(bash)" not in obj["step"]


class TestStepTransitionDone:
    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary",
        return_value="/usr/bin/recipe-runner-rs",
    )
    @patch("subprocess.Popen")
    def test_done_marker_emits_jsonl(self, mock_popen, mock_find):
        mock_popen.return_value = FakePopen(
            stdout=_make_rust_output(),
            stderr="\u25b6 classify-and-decompose (agent)\n\u2713 classify-and-decompose\n",
        )
        captured = io.StringIO()
        with patch.object(sys, "stderr", captured):
            run_recipe_via_rust("test-recipe", progress=True)
        json_lines = [ln for ln in captured.getvalue().strip().splitlines() if ln.startswith("{")]
        done_lines = [ln for ln in json_lines if json.loads(ln)["status"] == "done"]
        assert len(done_lines) >= 1, f"Expected a 'done' transition; got: {json_lines}"
        obj = json.loads(done_lines[0])
        assert obj["type"] == "step_transition"
        assert obj["step"] == "classify-and-decompose"


class TestStepTransitionFail:
    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary",
        return_value="/usr/bin/recipe-runner-rs",
    )
    @patch("subprocess.Popen")
    def test_fail_marker_emits_jsonl(self, mock_popen, mock_find):
        mock_popen.return_value = FakePopen(
            stdout=_make_rust_output(success=False),
            stderr="\u25b6 run-tests (bash)\n\u2717 run-tests\n",
        )
        captured = io.StringIO()
        with patch.object(sys, "stderr", captured):
            run_recipe_via_rust("test-recipe", progress=True)
        json_lines = [ln for ln in captured.getvalue().strip().splitlines() if ln.startswith("{")]
        fail_lines = [ln for ln in json_lines if json.loads(ln)["status"] == "fail"]
        assert len(fail_lines) >= 1, f"Expected a 'fail' transition; got: {json_lines}"
        obj = json.loads(fail_lines[0])
        assert obj["type"] == "step_transition"
        assert obj["step"] == "run-tests"


class TestStepTransitionSkip:
    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary",
        return_value="/usr/bin/recipe-runner-rs",
    )
    @patch("subprocess.Popen")
    def test_skip_marker_emits_jsonl(self, mock_popen, mock_find):
        mock_popen.return_value = FakePopen(
            stdout=_make_rust_output(),
            stderr="\u25b6 optional-step (bash)\n\u2298 optional-step\n",
        )
        captured = io.StringIO()
        with patch.object(sys, "stderr", captured):
            run_recipe_via_rust("test-recipe", progress=True)
        json_lines = [ln for ln in captured.getvalue().strip().splitlines() if ln.startswith("{")]
        skip_lines = [ln for ln in json_lines if json.loads(ln)["status"] == "skip"]
        assert len(skip_lines) >= 1, f"Expected a 'skip' transition; got: {json_lines}"


class TestStepTransitionMultiStep:
    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary",
        return_value="/usr/bin/recipe-runner-rs",
    )
    @patch("subprocess.Popen")
    def test_multiple_steps_produce_ordered_transitions(self, mock_popen, mock_find):
        mock_popen.return_value = FakePopen(
            stdout=_make_rust_output(),
            stderr=(
                "\u25b6 step-01 (agent)\n\u2713 step-01\n"
                "\u25b6 step-02 (bash)\n\u2717 step-02\n"
                "\u25b6 step-03 (agent)\n\u2298 step-03\n"
            ),
        )
        captured = io.StringIO()
        with patch.object(sys, "stderr", captured):
            run_recipe_via_rust("test-recipe", progress=True)
        json_lines = [
            json.loads(ln) for ln in captured.getvalue().strip().splitlines() if ln.startswith("{")
        ]
        transitions = [obj for obj in json_lines if obj.get("type") == "step_transition"]
        assert len(transitions) == 6, (
            f"Expected 6 transitions (3 starts + 3 ends); got {len(transitions)}: {transitions}"
        )
        statuses = [t["status"] for t in transitions]
        assert statuses == ["start", "done", "start", "fail", "start", "skip"]

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary",
        return_value="/usr/bin/recipe-runner-rs",
    )
    @patch("subprocess.Popen")
    def test_timestamps_are_monotonically_increasing(self, mock_popen, mock_find):
        mock_popen.return_value = FakePopen(
            stdout=_make_rust_output(),
            stderr="\u25b6 step-A (agent)\n\u2713 step-A\n\u25b6 step-B (agent)\n\u2713 step-B\n",
        )
        captured = io.StringIO()
        with patch.object(sys, "stderr", captured):
            run_recipe_via_rust("test-recipe", progress=True)
        json_lines = [
            json.loads(ln) for ln in captured.getvalue().strip().splitlines() if ln.startswith("{")
        ]
        timestamps = [obj["ts"] for obj in json_lines if obj.get("type") == "step_transition"]
        assert len(timestamps) >= 2
        for i in range(1, len(timestamps)):
            assert timestamps[i] >= timestamps[i - 1], f"Timestamps not monotonic: {timestamps}"


class TestStepTransitionSchema:
    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary",
        return_value="/usr/bin/recipe-runner-rs",
    )
    @patch("subprocess.Popen")
    def test_jsonl_contains_required_fields(self, mock_popen, mock_find):
        mock_popen.return_value = FakePopen(
            stdout=_make_rust_output(),
            stderr="\u25b6 my-step (agent)\n\u2713 my-step\n",
        )
        captured = io.StringIO()
        with patch.object(sys, "stderr", captured):
            run_recipe_via_rust("test-recipe", progress=True)
        json_lines = [
            json.loads(ln) for ln in captured.getvalue().strip().splitlines() if ln.startswith("{")
        ]
        for obj in json_lines:
            if obj.get("type") != "step_transition":
                continue
            assert "type" in obj
            assert "step" in obj
            assert "status" in obj
            assert "ts" in obj
            assert isinstance(obj["ts"], (int, float))
            assert obj["status"] in ("start", "done", "fail", "skip")

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary",
        return_value="/usr/bin/recipe-runner-rs",
    )
    @patch("subprocess.Popen")
    def test_jsonl_lines_are_valid_json(self, mock_popen, mock_find):
        mock_popen.return_value = FakePopen(
            stdout=_make_rust_output(),
            stderr="\u25b6 s1 (agent)\n\u2713 s1\n\u25b6 s2 (bash)\n\u2298 s2\n",
        )
        captured = io.StringIO()
        with patch.object(sys, "stderr", captured):
            run_recipe_via_rust("test-recipe", progress=True)
        for line in captured.getvalue().strip().splitlines():
            if line.startswith("{"):
                try:
                    json.loads(line)
                except json.JSONDecodeError:
                    pytest.fail(f"Invalid JSON on stderr: {line!r}")


class TestMeaningfulStderrSkipsJson:
    def test_json_lines_are_filtered_from_meaningful_tail(self):
        stderr = (
            '{"type":"step_transition","step":"s1","status":"start","ts":1234}\n'
            "\u25b6 step-one (agent)\n"
            '{"type":"step_transition","step":"s1","status":"done","ts":1235}\n'
            "\u2713 step-one\n"
            "ERROR: something bad happened\n"
            "Traceback (most recent call last):\n"
            '  File "runner.py", line 42\n'
        )
        result = _meaningful_stderr_tail(stderr)
        assert '{"type"' not in result
        assert "ERROR: something bad happened" in result

    def test_only_json_lines_falls_back_to_raw(self):
        stderr = (
            '{"type":"step_transition","step":"s1","status":"start","ts":1}\n'
            "\u25b6 s1 (agent)\n"
            '{"type":"step_transition","step":"s1","status":"done","ts":2}\n'
            "\u2713 s1\n"
        )
        result = _meaningful_stderr_tail(stderr)
        assert len(result.strip()) > 0

    def test_mixed_content_preserves_real_errors(self):
        stderr = (
            '{"type":"step_transition","step":"x","status":"start","ts":1}\n'
            "\u25b6 x (agent)\n"
            "[agent] heartbeat: still running\n"
            "Permission denied: /etc/shadow\n"
            '{"type":"step_transition","step":"x","status":"fail","ts":2}\n'
            "\u2717 x\n"
        )
        result = _meaningful_stderr_tail(stderr)
        assert "Permission denied" in result


class TestRustRunnerDuplicateConsistency:
    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary",
        return_value="/usr/bin/recipe-runner-rs",
    )
    @patch("subprocess.Popen")
    def test_rust_runner_also_emits_jsonl_on_start(self, mock_popen, mock_find):
        mock_popen.return_value = FakePopen(
            stdout=_make_rust_output(),
            stderr="\u25b6 test-step (agent)\n",
        )
        captured = io.StringIO()
        with patch.object(sys, "stderr", captured):
            run_recipe_via_rust("test-recipe", progress=True)
        json_lines = [ln for ln in captured.getvalue().strip().splitlines() if ln.startswith("{")]
        assert any(json.loads(ln).get("type") == "step_transition" for ln in json_lines), (
            f"No step_transition JSONL found: {json_lines}"
        )

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary",
        return_value="/usr/bin/recipe-runner-rs",
    )
    @patch("subprocess.Popen")
    def test_rust_runner_meaningful_stderr_skips_json(self, mock_popen, mock_find):
        mock_popen.return_value = FakePopen(
            stdout="invalid json",
            stderr=(
                '{"type":"step_transition","step":"s1","status":"start","ts":1}\n'
                "\u25b6 s1 (agent)\n"
                "Real error: import failed\n"
                '{"type":"step_transition","step":"s1","status":"fail","ts":2}\n'
                "\u2717 s1\n"
            ),
            returncode=1,
        )
        with pytest.raises(RuntimeError, match="Real error"):
            run_recipe_via_rust("test-recipe", progress=True)


class TestStepTransitionEdgeCases:
    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary",
        return_value="/usr/bin/recipe-runner-rs",
    )
    @patch("subprocess.Popen")
    def test_no_markers_produces_no_jsonl(self, mock_popen, mock_find):
        mock_popen.return_value = FakePopen(
            stdout=_make_rust_output(),
            stderr="some regular output\nanother line\n",
        )
        captured = io.StringIO()
        with patch.object(sys, "stderr", captured):
            run_recipe_via_rust("test-recipe", progress=True)
        json_lines = [ln for ln in captured.getvalue().strip().splitlines() if ln.startswith("{")]
        assert len(json_lines) == 0, f"Unexpected JSONL output: {json_lines}"

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary",
        return_value="/usr/bin/recipe-runner-rs",
    )
    @patch("subprocess.Popen")
    def test_empty_stderr_produces_no_jsonl(self, mock_popen, mock_find):
        mock_popen.return_value = FakePopen(stdout=_make_rust_output(), stderr="")
        captured = io.StringIO()
        with patch.object(sys, "stderr", captured):
            run_recipe_via_rust("test-recipe", progress=True)
        json_lines = [ln for ln in captured.getvalue().strip().splitlines() if ln.startswith("{")]
        assert len(json_lines) == 0

    @patch(
        "amplihack.recipes.rust_runner.find_rust_binary",
        return_value="/usr/bin/recipe-runner-rs",
    )
    @patch("subprocess.Popen")
    def test_marker_without_step_name_still_emits(self, mock_popen, mock_find):
        mock_popen.return_value = FakePopen(stdout=_make_rust_output(), stderr="\u25b6\n")
        captured = io.StringIO()
        with patch.object(sys, "stderr", captured):
            run_recipe_via_rust("test-recipe", progress=True)
        json_lines = [ln for ln in captured.getvalue().strip().splitlines() if ln.startswith("{")]
        assert len(json_lines) >= 1
        obj = json.loads(json_lines[0])
        assert obj["type"] == "step_transition"
        assert obj["status"] == "start"
