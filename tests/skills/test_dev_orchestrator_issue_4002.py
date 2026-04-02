"""Regression tests for issue #4002 nested Copilot classify compatibility."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_nested_copilot_classify_path_completes_without_recursive_dev_workflow(tmp_path):
    sandbox = tmp_path
    fake_bin = sandbox / "bin"
    fake_home = sandbox / "home"
    fake_repo = sandbox / "repo"
    fake_bin.mkdir()
    fake_home.mkdir()
    fake_repo.mkdir()

    fake_copilot = fake_bin / "copilot"
    fake_copilot.write_text(
        """#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

home = Path(os.environ["HOME"])
records_path = home / "copilot-records.jsonl"
prompt = ""
if "-p" in sys.argv:
    idx = sys.argv.index("-p")
    if idx + 1 < len(sys.argv):
        prompt = sys.argv[idx + 1]

record = {
    "argv": sys.argv[1:],
    "prompt": prompt,
}
with records_path.open("a", encoding="utf-8") as fh:
    fh.write(json.dumps(record) + "\\n")

if "--help" in sys.argv or "--version" in sys.argv:
    print("GitHub Copilot CLI 1.0.15-0.")
    raise SystemExit(0)

if "You are an intelligent task orchestrator" in prompt:
    print(json.dumps({
        "task_type": "Q&A",
        "goal": "Reproduce nested classify",
        "success_criteria": ["classify works"],
        "workstreams": [{
            "name": "single",
            "description": "Answer the question directly",
            "recipe": "default-workflow",
        }],
    }))
    raise SystemExit(0)

if "Review for any remaining ambiguity in the requirements." in prompt:
    print("Requirements are clear. Proceeding.")
    raise SystemExit(0)

print("Nested agent step completed.")
""",
        encoding="utf-8",
    )
    fake_copilot.chmod(0o755)

    command = """PYTHONPATH=src python3 - <<'PY'
from amplihack.recipes import run_recipe_by_name

result = run_recipe_by_name(
    'smart-orchestrator',
    user_context={
        'task_description': 'Issue 4002 nested classify regression probe',
        'repo_path': '.',
        'force_single_workstream': 'true',
    },
    progress=True,
)
print('SUCCESS', result.success)
print('LAST', result.step_results[-1].step_id)
PY"""

    env = os.environ.copy()
    env["HOME"] = str(fake_home)
    env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"
    env["AMPLIHACK_AGENT_BINARY"] = "copilot"

    result = subprocess.run(
        ["bash", "-lc", command],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert "SUCCESS True" in result.stdout
    assert "classify-and-decompose" in result.stderr
    assert "handle-qa" in result.stderr

    records_path = fake_home / "copilot-records.jsonl"
    assert records_path.exists(), "fake Copilot binary was never invoked"
    records = [
        json.loads(line)
        for line in records_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert records, "expected at least one nested Copilot invocation"

    nested_records = [r for r in records if "--no-custom-instructions" in r["argv"]]
    assert nested_records, f"expected nested launches to disable custom instructions: {records!r}"

    classify_records = [
        r for r in nested_records if "You are an intelligent task orchestrator" in r["prompt"]
    ]
    assert classify_records, f"expected classify prompt to reach fake Copilot: {records!r}"
    assert any("Answer this question directly." in r["prompt"] for r in nested_records), records

    for record in nested_records:
        argv = record["argv"]
        prompt = record["prompt"]
        assert "--dangerously-skip-permissions" not in argv
        assert "--append-system-prompt" not in argv
        assert 'Skill(skill="dev-orchestrator")' not in prompt
        assert 'run_recipe_by_name("smart-orchestrator")' not in prompt
        assert "/dev" not in prompt
