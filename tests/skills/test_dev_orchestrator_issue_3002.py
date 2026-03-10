"""Regression tests for issue #3002 documentation drift.

These tests lock in the repaired launch path for the dev-orchestrator skill
and related docs:
- use ``python3`` from PATH, not a hardcoded ``.venv/bin/python``
- do not reference the removed Python adapter import path
- do not tell callers to pass ``adapter=...`` to ``run_recipe_by_name()``
"""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEV_ORCHESTRATOR_SKILL = REPO_ROOT / ".claude" / "skills" / "dev-orchestrator" / "SKILL.md"
OXIDIZER_DOC = REPO_ROOT / "docs" / "OXIDIZER.md"


def test_dev_orchestrator_skill_uses_python3_and_no_stale_adapter_import():
    content = DEV_ORCHESTRATOR_SKILL.read_text()

    assert "env -u CLAUDECODE python3 -c" in content
    assert "env -u CLAUDECODE .venv/bin/python -c" not in content
    assert "amplihack.recipes.adapters.cli_subprocess" not in content
    assert "CLISubprocessAdapter" not in content


def test_oxidizer_doc_uses_rust_only_run_recipe_api():
    content = OXIDIZER_DOC.read_text()

    assert "from amplihack.recipes import run_recipe_by_name" in content
    assert "adapter=CLISubprocessAdapter()" not in content
    assert "amplihack.recipes.adapters.cli_subprocess" not in content
