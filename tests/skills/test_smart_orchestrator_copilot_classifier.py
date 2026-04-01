"""Regression tests for smart-orchestrator Copilot classifier compatibility."""

from __future__ import annotations

import json
import os
import subprocess
import textwrap
from pathlib import Path

import yaml

from amplihack.recipes.rust_runner_copilot import _normalize_copilot_cli_args

REPO_ROOT = Path(__file__).resolve().parents[2]
RECIPE_PATH = REPO_ROOT / "amplifier-bundle" / "recipes" / "smart-orchestrator.yaml"


def _steps_by_id() -> dict[str, dict]:
    data = yaml.safe_load(RECIPE_PATH.read_text(encoding="utf-8"))
    return {step["id"]: step for step in data["steps"]}


def _render_classify_command(
    *,
    task_description: str = "Smart-orchestrator Copilot classifier regression",
    force_single_workstream: str = "false",
) -> str:
    command = _steps_by_id()["classify-and-decompose"]["command"]
    return command.replace("{{task_description}}", task_description).replace(
        "{{force_single_workstream}}", force_single_workstream
    )


def _write_fake_copilot(path: Path, capture_file: Path) -> None:
    path.write_text(
        textwrap.dedent(
            f"""\
            #!/usr/bin/env python3
            import json
            import sys
            from pathlib import Path

            Path({str(capture_file)!r}).write_text(json.dumps(sys.argv[1:]), encoding="utf-8")
            sys.stdout.write(json.dumps({{
                "task_type": "Development",
                "goal": "ok",
                "success_criteria": ["ok"],
                "workstreams": [
                    {{"name": "slug", "description": "full task", "recipe": "default-workflow"}}
                ],
            }}))
            """
        ),
        encoding="utf-8",
    )
    path.chmod(0o755)


def test_classify_and_decompose_uses_copilot_safe_prompt_mode(tmp_path: Path) -> None:
    capture_file = tmp_path / "copilot-argv.json"
    fake_copilot = tmp_path / "copilot"
    _write_fake_copilot(fake_copilot, capture_file)

    env = os.environ.copy()
    env["AMPLIHACK_AGENT_BINARY"] = "copilot"
    env["PATH"] = f"{tmp_path}{os.pathsep}{env['PATH']}"

    task_description = "Step 9b classify request"
    command = _render_classify_command(task_description=task_description)
    result = subprocess.run(
        ["bash", "-lc", command],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    args = json.loads(capture_file.read_text(encoding="utf-8"))

    assert "--dangerously-skip-permissions" not in args
    assert "--disallowed-tools" not in args
    assert "--append-system-prompt" not in args

    assert "--no-custom-instructions" in args
    assert "--allow-all-paths" in args
    available_tools_index = args.index("--available-tools")
    assert args[available_tools_index + 1] == ""

    normalized_args = _normalize_copilot_cli_args(args)
    assert "--allow-all-tools" not in normalized_args
    normalized_available_tools_index = normalized_args.index("--available-tools")
    assert normalized_args[normalized_available_tools_index + 1] == ""

    prompt_index = args.index("-p")
    merged_prompt = args[prompt_index + 1]
    assert "You are a task classifier. Output ONLY JSON." in merged_prompt
    assert "You are classifying a task for the smart-orchestrator recipe." in merged_prompt
    assert f"REQUEST: {task_description}" in merged_prompt


def test_classify_and_decompose_keeps_claude_flag_path() -> None:
    command = _steps_by_id()["classify-and-decompose"]["command"]

    assert 'if [ "$AGENT_BIN" = "copilot" ]' in command
    assert "--dangerously-skip-permissions" in command
    assert '--append-system-prompt "$CLASSIFIER_SYSTEM_PROMPT"' in command
