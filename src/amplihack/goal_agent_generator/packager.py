"""
Goal Agent Packager - Package goal agents as standalone directories.

Creates self-contained agent directories with all necessary files.
Supports multi-agent packaging with sub-agent configurations.
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import GoalAgentBundle
from .templates.memory_template import (
    get_memory_config_yaml,
    get_memory_initialization_code,
    get_memory_readme_section,
)
from .templates.multi_agent_template import (
    get_coordinator_yaml,
    get_memory_agent_yaml,
    get_multi_agent_init_code,
    get_multi_agent_readme_section,
    get_spawner_yaml,
)


class GoalAgentPackager:
    """Package goal agent bundles as standalone directories."""

    def __init__(self, output_dir: Path | None = None):
        """
        Initialize packager.

        Args:
            output_dir: Directory for packaged agents (defaults to ./goal_agents)
        """
        self.output_dir = output_dir or Path.cwd() / "goal_agents"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def package(self, bundle: GoalAgentBundle) -> Path:
        """
        Package a goal agent bundle into a standalone directory.

        Args:
            bundle: Bundle to package

        Returns:
            Path to packaged agent directory

        Raises:
            ValueError: If bundle is incomplete
        """
        if not bundle.is_complete:
            raise ValueError(f"Bundle {bundle.name} is incomplete - missing required components")

        # Create agent directory
        agent_dir = self.output_dir / bundle.name
        agent_dir.mkdir(parents=True, exist_ok=True)

        # Create directory structure
        self._create_directory_structure(agent_dir, bundle)

        # Write goal definition
        self._write_goal_definition(agent_dir, bundle)

        # Write execution plan
        self._write_execution_plan(agent_dir, bundle)

        # Write skills
        self._write_skills(agent_dir, bundle)

        # Write main entry point
        self._write_main_script(agent_dir, bundle)

        # Write README
        self._write_readme(agent_dir, bundle)

        # Write configuration
        self._write_config(agent_dir, bundle)

        # Write memory configuration if enabled
        if bundle.metadata.get("memory_enabled"):
            self._write_memory_config(agent_dir, bundle)

        # Write multi-agent configs if enabled
        if bundle.metadata.get("multi_agent"):
            self._write_multi_agent_configs(agent_dir, bundle)

        # Write SDK tools config if present
        if bundle.sdk_tools:
            self._write_sdk_tools_config(agent_dir, bundle)

        # Write requirements.txt
        self._write_requirements(agent_dir, bundle)

        return agent_dir

    def _create_directory_structure(self, agent_dir: Path, bundle: GoalAgentBundle) -> None:
        """Create standard directory structure."""
        (agent_dir / ".claude").mkdir(exist_ok=True)
        (agent_dir / ".claude" / "agents").mkdir(exist_ok=True)
        (agent_dir / ".claude" / "context").mkdir(exist_ok=True)
        (agent_dir / "logs").mkdir(exist_ok=True)

        # Create sub_agents directory for multi-agent bundles
        if bundle.metadata.get("multi_agent"):
            (agent_dir / "sub_agents").mkdir(exist_ok=True)

    def _write_goal_definition(self, agent_dir: Path, bundle: GoalAgentBundle) -> None:
        """Write goal definition file."""
        if not bundle.goal_definition:
            return

        goal_path = agent_dir / "prompt.md"
        goal_path.write_text(bundle.goal_definition.raw_prompt)

        # Also write structured goal
        goal_json_path = agent_dir / ".claude" / "context" / "goal.json"
        goal_data = {
            "goal": bundle.goal_definition.goal,
            "domain": bundle.goal_definition.domain,
            "complexity": bundle.goal_definition.complexity,
            "constraints": bundle.goal_definition.constraints,
            "success_criteria": bundle.goal_definition.success_criteria,
            "context": bundle.goal_definition.context,
        }
        goal_json_path.write_text(json.dumps(goal_data, indent=2))

    def _write_execution_plan(self, agent_dir: Path, bundle: GoalAgentBundle) -> None:
        """Write execution plan file."""
        if not bundle.execution_plan:
            return

        plan_path = agent_dir / ".claude" / "context" / "execution_plan.json"
        plan_data = {
            "total_duration": bundle.execution_plan.total_estimated_duration,
            "required_skills": bundle.execution_plan.required_skills,
            "parallel_opportunities": bundle.execution_plan.parallel_opportunities,
            "risk_factors": bundle.execution_plan.risk_factors,
            "phases": [
                {
                    "name": phase.name,
                    "description": phase.description,
                    "required_capabilities": phase.required_capabilities,
                    "estimated_duration": phase.estimated_duration,
                    "dependencies": phase.dependencies,
                    "parallel_safe": phase.parallel_safe,
                    "success_indicators": phase.success_indicators,
                }
                for phase in bundle.execution_plan.phases
            ],
        }

        plan_path.write_text(json.dumps(plan_data, indent=2))

    def _write_skills(self, agent_dir: Path, bundle: GoalAgentBundle) -> None:
        """Write skill files."""
        skills_dir = agent_dir / ".claude" / "agents"

        for skill in bundle.skills:
            skill_path = skills_dir / f"{skill.name}.md"
            skill_path.write_text(skill.content)

    def _write_main_script(self, agent_dir: Path, bundle: GoalAgentBundle) -> None:
        """Write main entry point script."""
        # Check if memory is enabled
        memory_enabled = bundle.metadata.get("memory_enabled", False)

        # Generate memory initialization code if enabled
        memory_init_code = ""
        memory_import = ""
        memory_cleanup = ""

        if memory_enabled:
            memory_import = """
try:
    from amplihack_memory import MemoryConnector, ExperienceStore, Experience, ExperienceType
except ImportError:
    print("Warning: amplihack-memory-lib not found. Memory features disabled.")
    print("Install with: pip install amplihack-memory-lib")
    MemoryConnector = None
"""
            memory_init_code = get_memory_initialization_code(bundle.name, "./memory")
            memory_cleanup = """
    # Cleanup memory connections
    if 'cleanup_memory' in globals():
        cleanup_memory()
"""

        main_content = f'''#!/usr/bin/env python3
"""
{bundle.name} - Autonomous Goal-Seeking Agent

Generated by Amplihack Goal Agent Generator
"""

import sys
from pathlib import Path
from typing import Any

# Add parent directory to path for amplihack imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from amplihack.launcher.auto_mode import AutoMode
except ImportError:
    print("Error: amplihack package not found")
    print("Install with: pip install amplihack")
    sys.exit(1)
{memory_import}
{memory_init_code if memory_enabled else ""}


def main() -> int:
    """Execute the goal-seeking agent."""
    # Load configuration
    config: dict[str, Any] = {bundle.auto_mode_config}

    # Read initial prompt
    prompt_path = Path(__file__).parent / "prompt.md"
    if not prompt_path.exists():
        print("Error: prompt.md not found")
        sys.exit(1)

    initial_prompt = prompt_path.read_text()

    # Extract configuration with explicit type conversions
    sdk_value = str(config.get("sdk", "claude"))
    max_turns_value = int(config.get("max_turns", 10))
    ui_mode_value = bool(config.get("ui_mode", False))

    # Create auto-mode instance
    auto_mode = AutoMode(
        sdk=sdk_value,
        prompt=initial_prompt,
        max_turns=max_turns_value,
        working_dir=Path(__file__).parent,
        ui_mode=ui_mode_value,
    )

    # Run agent
    print(f"Starting {bundle.name}...")
    print(f"Goal: {bundle.goal_definition.goal if bundle.goal_definition else "Unknown"}")
    print(f"Estimated duration: {bundle.execution_plan.total_estimated_duration if bundle.execution_plan else "Unknown"}")
    print()

    exit_code = auto_mode.run()

    if exit_code == 0:
        print("\\nGoal achieved successfully!")
    else:
        print(f"\\nGoal execution failed with code {{exit_code}}")
{memory_cleanup}
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
'''

        main_path = agent_dir / "main.py"
        main_path.write_text(main_content)
        main_path.chmod(0o755)  # Make executable

    def _write_readme(self, agent_dir: Path, bundle: GoalAgentBundle) -> None:
        """Write README file."""
        readme_content = f"""# {bundle.name}

Autonomous goal-seeking agent generated by Amplihack.

## Goal

{bundle.goal_definition.goal if bundle.goal_definition else "No goal defined"}

## Domain

{bundle.goal_definition.domain if bundle.goal_definition else "general"}

## Complexity

{bundle.goal_definition.complexity if bundle.goal_definition else "moderate"}

## Execution Plan

{bundle.execution_plan.phase_count if bundle.execution_plan else 0} phases, estimated duration: {bundle.execution_plan.total_estimated_duration if bundle.execution_plan else "unknown"}

### Phases

"""

        if bundle.execution_plan:
            for i, phase in enumerate(bundle.execution_plan.phases, 1):
                readme_content += f"\n{i}. **{phase.name}** ({phase.estimated_duration})\n"
                readme_content += f"   {phase.description}\n"
                readme_content += f"   - Capabilities: {', '.join(phase.required_capabilities)}\n"

        readme_content += f"""

## Skills

{bundle.skill_count} skills included:

"""

        for skill in bundle.skills:
            readme_content += f"- **{skill.name}** (match: {skill.match_score:.0%})\n"
            readme_content += f"  {skill.description[:100]}...\n"

        # Add SDK tools section if present
        if bundle.sdk_tools:
            readme_content += "\n## SDK Tools\n\n"
            readme_content += f"Target SDK: {bundle.auto_mode_config.get('sdk', 'copilot')}\n\n"
            for tool in bundle.sdk_tools:
                readme_content += f"- **{tool.name}** ({tool.category}): {tool.description}\n"

        readme_content += """

## Usage

### Run the agent

```bash
python main.py
```

### Requirements

- Python >= 3.11
- amplihack package installed
- Claude API access (or other configured SDK)

### Configuration

Auto-mode configuration is in `main.py`. Adjust `max_turns`, `sdk`, or `ui_mode` as needed.

## Success Criteria

"""

        if bundle.goal_definition and bundle.goal_definition.success_criteria:
            for criterion in bundle.goal_definition.success_criteria:
                readme_content += f"- {criterion}\n"

        if bundle.goal_definition and bundle.goal_definition.constraints:
            readme_content += "\n## Constraints\n\n"
            for constraint in bundle.goal_definition.constraints:
                readme_content += f"- {constraint}\n"

        # Add memory section if enabled
        if bundle.metadata.get("memory_enabled"):
            readme_content += get_memory_readme_section()

        # Add multi-agent section if enabled
        if bundle.metadata.get("multi_agent"):
            readme_content += get_multi_agent_readme_section(bundle.name)

        readme_content += f"""

## Generated Metadata

- Bundle ID: {bundle.id}
- Version: {bundle.version}
- Created: {bundle.created_at.isoformat()}

---

Generated by Amplihack Goal Agent Generator v1.0.0
"""

        readme_path = agent_dir / "README.md"
        readme_path.write_text(readme_content)

    def _write_config(self, agent_dir: Path, bundle: GoalAgentBundle) -> None:
        """Write configuration file."""
        config_data: dict = {
            "bundle_id": str(bundle.id),
            "name": bundle.name,
            "version": bundle.version,
            "metadata": bundle.metadata,
            "auto_mode_config": bundle.auto_mode_config,
        }

        # Include SDK tools in config
        if bundle.sdk_tools:
            config_data["sdk_tools"] = [t.to_dict() for t in bundle.sdk_tools]

        # Include sub-agent config summaries
        if bundle.sub_agent_configs:
            config_data["sub_agents"] = [
                {"role": sa.role, "filename": sa.filename}
                for sa in bundle.sub_agent_configs
            ]

        config_path = agent_dir / "agent_config.json"
        config_path.write_text(json.dumps(config_data, indent=2))

    def _write_memory_config(self, agent_dir: Path, bundle: GoalAgentBundle) -> None:
        """Write memory configuration file."""
        config_content = get_memory_config_yaml(bundle.name)
        config_path = agent_dir / "memory_config.yaml"
        config_path.write_text(config_content)

        # Create memory directory
        memory_dir = agent_dir / "memory"
        memory_dir.mkdir(exist_ok=True)

        # Add .gitignore to memory directory
        gitignore_path = memory_dir / ".gitignore"
        gitignore_path.write_text("*.sqlite\n*.db\n*.log\n")

    def _write_multi_agent_configs(self, agent_dir: Path, bundle: GoalAgentBundle) -> None:
        """Write multi-agent sub-agent configuration files."""
        sub_agents_dir = agent_dir / "sub_agents"
        sub_agents_dir.mkdir(exist_ok=True)

        enable_spawning = bundle.metadata.get("enable_spawning", False)

        # Write coordinator config
        coordinator_yaml = get_coordinator_yaml(bundle.name)
        (sub_agents_dir / "coordinator.yaml").write_text(coordinator_yaml)

        # Write memory agent config
        memory_agent_yaml = get_memory_agent_yaml(bundle.name)
        (sub_agents_dir / "memory_agent.yaml").write_text(memory_agent_yaml)

        # Write spawner config (always write it, enabled flag controls behavior)
        spawner_yaml = get_spawner_yaml(
            bundle.name,
            enable_spawning=enable_spawning,
        )
        (sub_agents_dir / "spawner.yaml").write_text(spawner_yaml)

        # Write multi-agent init helper
        init_code = get_multi_agent_init_code(bundle.name)
        (sub_agents_dir / "__init__.py").write_text(init_code)

    def _write_sdk_tools_config(self, agent_dir: Path, bundle: GoalAgentBundle) -> None:
        """Write SDK tools configuration file."""
        tools_data = {
            "sdk": bundle.auto_mode_config.get("sdk", "copilot"),
            "tools": [tool.to_dict() for tool in bundle.sdk_tools],
        }

        tools_path = agent_dir / ".claude" / "context" / "sdk_tools.json"
        tools_path.write_text(json.dumps(tools_data, indent=2))

    def _write_requirements(self, agent_dir: Path, bundle: GoalAgentBundle) -> None:
        """Write requirements.txt file."""
        requirements = ["amplihack>=0.9.0"]

        # Add memory library if enabled
        if bundle.metadata.get("memory_enabled"):
            requirements.append("amplihack-memory-lib>=0.1.0")

        # Add PyYAML for multi-agent config loading
        if bundle.metadata.get("multi_agent"):
            requirements.append("pyyaml>=6.0")

        requirements_path = agent_dir / "requirements.txt"
        requirements_path.write_text("\n".join(requirements) + "\n")
