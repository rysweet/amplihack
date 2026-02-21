"""
CLI for Goal Agent Generator.

Provides `amplihack new --file <prompt.md>` command to generate goal agents.
Supports SDK-specific tool injection and multi-agent packaging.
"""
# pyright: reportOptionalMemberAccess=false, reportMissingImports=false

import logging
import sys
import time
from pathlib import Path

try:
    import click
except ImportError:
    click = None  # type: ignore[assignment]

from .agent_assembler import AgentAssembler
from .objective_planner import ObjectivePlanner
from .packager import GoalAgentPackager
from .prompt_analyzer import PromptAnalyzer
from .skill_synthesizer import SkillSynthesizer

logger = logging.getLogger(__name__)


@click.command(name="new")
@click.option(
    "--file",
    "-f",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to prompt.md file containing goal description",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Output directory for goal agent (default: ./goal_agents)",
)
@click.option(
    "--name",
    "-n",
    type=str,
    default=None,
    help="Custom name for goal agent (auto-generated if not provided)",
)
@click.option(
    "--skills-dir",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Custom skills directory (default: .claude/agents/amplihack)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output",
)
@click.option(
    "--enable-memory",
    is_flag=True,
    help="Enable memory/learning capabilities",
)
@click.option(
    "--sdk",
    type=click.Choice(["copilot", "claude", "microsoft", "mini"], case_sensitive=False),
    default="copilot",
    help="SDK to use for agent execution (default: copilot)",
)
@click.option(
    "--multi-agent",
    is_flag=True,
    help="Enable multi-agent architecture with coordinator, memory agent, and sub-agents",
)
@click.option(
    "--enable-spawning",
    is_flag=True,
    help="Enable dynamic sub-agent spawning (requires --multi-agent)",
)
def new_goal_agent(
    file: Path,
    output: Path | None,
    name: str | None,
    skills_dir: Path | None,
    verbose: bool,
    enable_memory: bool,
    sdk: str,
    multi_agent: bool,
    enable_spawning: bool,
) -> int:
    """
    Generate a new goal-seeking agent from a prompt file.

    Example:
        amplihack new --file my_goal.md
        amplihack new --file my_goal.md --name my-agent --output ./agents
        amplihack new --file my_goal.md --enable-memory
        amplihack new --file my_goal.md --multi-agent --enable-spawning
        amplihack new --file my_goal.md --sdk claude --multi-agent
    """
    # Configure logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(levelname)s - %(message)s", stream=sys.stdout
    )

    # Validate flag combinations
    if enable_spawning and not multi_agent:
        click.echo(
            "Warning: --enable-spawning has no effect without --multi-agent. "
            "Adding --multi-agent automatically.",
            err=True,
        )
        multi_agent = True

    try:
        click.echo(f"\nGenerating goal agent from: {file}")
        start_time = time.time()

        # Stage 1: Analyze prompt
        click.echo("\n[1/4] Analyzing goal prompt...")
        analyzer = PromptAnalyzer()
        goal_definition = analyzer.analyze(file)

        click.echo(f"  Goal: {goal_definition.goal}")
        click.echo(f"  Domain: {goal_definition.domain}")
        click.echo(f"  Complexity: {goal_definition.complexity}")

        if verbose:
            logger.debug(f"Constraints: {goal_definition.constraints}")
            logger.debug(f"Success criteria: {goal_definition.success_criteria}")

        # Stage 2: Generate execution plan
        click.echo("\n[2/4] Creating execution plan...")
        planner = ObjectivePlanner()
        execution_plan = planner.generate_plan(goal_definition)

        click.echo(f"  Phases: {execution_plan.phase_count}")
        click.echo(f"  Estimated duration: {execution_plan.total_estimated_duration}")
        click.echo(f"  Required skills: {', '.join(execution_plan.required_skills)}")

        if verbose:
            for phase in execution_plan.phases:
                logger.debug(f"  - {phase.name}: {phase.description}")

        # Stage 2b: Synthesize skills with SDK tool awareness
        click.echo("\n[3/4] Matching skills and SDK tools...")
        synthesizer = SkillSynthesizer(skills_directory=skills_dir)
        synthesis_result = synthesizer.synthesize_with_sdk_tools(execution_plan, sdk=sdk)
        skills = synthesis_result["skills"]
        sdk_tools = synthesis_result["sdk_tools"]

        click.echo(f"  Skills matched: {len(skills)}")
        for skill in skills:
            match_pct = int(skill.match_score * 100)
            click.echo(f"    - {skill.name} ({match_pct}% match)")

        if sdk_tools:
            click.echo(f"  SDK tools ({sdk}): {len(sdk_tools)}")
            for tool in sdk_tools:
                click.echo(f"    - {tool.name} ({tool.category})")

        # Stage 3: Assemble bundle
        click.echo("\n[4/4] Assembling agent bundle...")
        assembler = AgentAssembler()
        bundle = assembler.assemble(
            goal_definition,
            execution_plan,
            skills,
            bundle_name=name,
            enable_memory=enable_memory,
            sdk=sdk,
            multi_agent=multi_agent,
            enable_spawning=enable_spawning,
            sdk_tools=sdk_tools,
        )

        click.echo(f"  Bundle name: {bundle.name}")
        click.echo(f"  Bundle ID: {bundle.id}")
        click.echo(f"  SDK: {sdk}")
        if enable_memory:
            click.echo("  Memory: Enabled")
        if multi_agent:
            click.echo("  Multi-Agent: Enabled")
            click.echo(f"  Sub-agents: {len(bundle.sub_agent_configs)}")
            if enable_spawning:
                click.echo("  Spawning: Enabled")

        # Stage 4: Package agent
        click.echo("\nPackaging agent...")
        packager = GoalAgentPackager(output_dir=output)
        agent_dir = packager.package(bundle)

        elapsed = time.time() - start_time

        # Success message
        click.echo(f"\n+ Goal agent created successfully in {elapsed:.1f}s")
        click.echo(f"\nAgent directory: {agent_dir}")
        click.echo("\nTo run the agent:")
        click.echo(f"  cd {agent_dir}")
        click.echo("  python main.py")

        return 0

    except FileNotFoundError as e:
        click.echo(f"\n- Error: {e}", err=True)
        return 1
    except ValueError as e:
        click.echo(f"\n- Validation error: {e}", err=True)
        return 1
    except Exception as e:
        click.echo(f"\n- Unexpected error: {e}", err=True)
        if verbose:
            import traceback

            traceback.print_exc()
        return 1


# For testing and direct invocation
if __name__ == "__main__":
    sys.exit(new_goal_agent())  # type: ignore[call-arg]  # Click handles args
