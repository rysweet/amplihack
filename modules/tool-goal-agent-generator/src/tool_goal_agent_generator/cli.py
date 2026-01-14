"""
CLI for Goal Agent Generator.

Provides `amplihack new --file <prompt.md>` command to generate goal agents.
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
def new_goal_agent(
    file: Path,
    output: Path | None,
    name: str | None,
    skills_dir: Path | None,
    verbose: bool,
) -> int:
    """
    Generate a new goal-seeking agent from a prompt file.

    Example:
        amplihack new --file my_goal.md
        amplihack new --file my_goal.md --name my-agent --output ./agents
    """
    # Configure logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(levelname)s - %(message)s", stream=sys.stdout
    )

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

        # Stage 2b: Synthesize skills
        click.echo("\n[3/4] Matching skills...")
        synthesizer = SkillSynthesizer(skills_directory=skills_dir)
        skills = synthesizer.synthesize_skills(execution_plan)

        click.echo(f"  Skills matched: {len(skills)}")
        for skill in skills:
            match_pct = int(skill.match_score * 100)
            click.echo(f"    - {skill.name} ({match_pct}% match)")

        # Stage 3: Assemble bundle
        click.echo("\n[4/4] Assembling agent bundle...")
        assembler = AgentAssembler()
        bundle = assembler.assemble(goal_definition, execution_plan, skills, bundle_name=name)

        click.echo(f"  Bundle name: {bundle.name}")
        click.echo(f"  Bundle ID: {bundle.id}")

        # Stage 4: Package agent
        click.echo("\nPackaging agent...")
        packager = GoalAgentPackager(output_dir=output)
        agent_dir = packager.package(bundle)

        elapsed = time.time() - start_time

        # Success message
        click.echo(f"\n✓ Goal agent created successfully in {elapsed:.1f}s")
        click.echo(f"\nAgent directory: {agent_dir}")
        click.echo("\nTo run the agent:")
        click.echo(f"  cd {agent_dir}")
        click.echo("  python main.py")

        return 0

    except FileNotFoundError as e:
        click.echo(f"\n✗ Error: {e}", err=True)
        return 1
    except ValueError as e:
        click.echo(f"\n✗ Validation error: {e}", err=True)
        return 1
    except Exception as e:
        click.echo(f"\n✗ Unexpected error: {e}", err=True)
        if verbose:
            import traceback

            traceback.print_exc()
        return 1


# For testing and direct invocation
if __name__ == "__main__":
    sys.exit(new_goal_agent())  # type: ignore[call-arg]  # Click handles args
