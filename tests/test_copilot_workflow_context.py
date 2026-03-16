from src.amplihack.launcher.copilot import (
    build_copilot_agents_context,
    generate_copilot_instructions,
)


def test_build_copilot_agents_context_includes_dev_orchestrator_rules(tmp_path):
    claude_dir = tmp_path / ".claude"
    routing_prompt = (
        claude_dir / "tools" / "amplihack" / "hooks" / "templates" / "routing_prompt.txt"
    )
    routing_prompt.parent.mkdir(parents=True, exist_ok=True)
    routing_prompt.write_text('Say "DEV → launching dev-orchestrator" and invoke the skill.')

    skill_md = claude_dir / "skills" / "dev-orchestrator" / "SKILL.md"
    skill_md.parent.mkdir(parents=True, exist_ok=True)
    skill_md.write_text(
        "# Dev Orchestrator Skill\n\n"
        "## Execution Instructions\n\n"
        'Run `run_recipe_by_name("smart-orchestrator")` immediately.\n\n'
        "## Task Type Classification\n"
    )

    context = build_copilot_agents_context(claude_dir, "Preference: autonomous")

    assert 'Skill(skill="dev-orchestrator")' in context
    assert 'run_recipe_by_name("smart-orchestrator")' in context
    assert "Preference: autonomous" in context
    assert "Do not follow the workflow manually" in context


def test_generate_copilot_instructions_prefers_dev_command(tmp_path):
    copilot_home = tmp_path / ".copilot"
    workflow_dir = copilot_home / "workflow" / "amplihack"
    workflow_dir.mkdir(parents=True, exist_ok=True)
    (workflow_dir / "DEFAULT_WORKFLOW.md").write_text("### Step 0:\n### Step 1:\n")

    generate_copilot_instructions(copilot_home)

    instructions = (copilot_home / "copilot-instructions.md").read_text()
    assert "/dev" in instructions
    assert "dev-orchestrator" in instructions
    assert "Deprecated alias to `/dev`" in instructions
