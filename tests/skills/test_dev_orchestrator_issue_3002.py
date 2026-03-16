"""Regression tests for issue #3002 documentation drift.

These tests lock in the repaired launch path for the dev-orchestrator skill
and related docs:
- use ``PYTHONPATH=src python3`` so shell launches import the checked-out repo
- do not rely on a hardcoded ``.venv/bin/python``
- do not reference the removed Python adapter import path
- do not tell callers to pass ``adapter=...`` to ``run_recipe_by_name()``
"""

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEV_ORCHESTRATOR_SKILL = REPO_ROOT / ".claude" / "skills" / "dev-orchestrator" / "SKILL.md"
OXIDIZER_DOC = REPO_ROOT / "docs" / "OXIDIZER.md"


def test_dev_orchestrator_skill_uses_python3_and_no_stale_adapter_import():
    content = DEV_ORCHESTRATOR_SKILL.read_text()

    assert "env -u CLAUDECODE PYTHONPATH=src python3 -c" in content
    assert "env -u CLAUDECODE .venv/bin/python -c" not in content
    assert "amplihack.recipes.adapters.cli_subprocess" not in content
    assert "CLISubprocessAdapter" not in content


def test_dev_orchestrator_shell_launch_works_from_repo_root():
    command = """env -u CLAUDECODE PYTHONPATH=src python3 - <<'PY'
from amplihack.recipes import run_recipe_by_name
result = run_recipe_by_name(
    'smart-orchestrator',
    user_context={
        'task_description': 'Issue 3002 shell launch regression test',
        'repo_path': '.',
        'force_single_workstream': 'true',
    },
    dry_run=True,
)
print('SUCCESS', result.success)
print('LAST', result.step_results[-1].step_id)
PY"""

    result = subprocess.run(
        ["bash", "-lc", command],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert "SUCCESS True" in result.stdout
    assert "LAST complete-session" in result.stdout


def test_oxidizer_doc_uses_rust_only_run_recipe_api():
    content = OXIDIZER_DOC.read_text()

    assert "from amplihack.recipes import run_recipe_by_name" in content
    assert "adapter=CLISubprocessAdapter()" not in content
    assert "amplihack.recipes.adapters.cli_subprocess" not in content
