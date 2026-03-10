"""Regression tests for issue #3024 progress-enabled recipe launches."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEV_ORCHESTRATOR_SKILL = REPO_ROOT / ".claude" / "skills" / "dev-orchestrator" / "SKILL.md"


def test_dev_orchestrator_skill_uses_progress_enabled_recipe_launch():
    content = DEV_ORCHESTRATOR_SKILL.read_text()

    assert "progress=True" in content
    assert "mktemp /tmp/recipe-runner-output." in content
    assert 'chmod 600 "$LOG_FILE"' in content
    assert "/tmp/recipe-runner-output.log" not in content
