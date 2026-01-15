"""Skills Invocation Wrapper - Invoke amplihack skills from Copilot CLI.

This module provides a unified interface for invoking amplihack skills,
routing to custom agents or MCP server tools based on the mapping strategy.

Philosophy: Ruthless simplicity - single entry point, automatic routing.
"""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any


@dataclass
class SkillInvocationResult:
    """Result from skill invocation."""

    success: bool
    output: str
    error: Optional[str] = None
    strategy: Optional[str] = None
    skill_name: str = ''


class SkillsWrapper:
    """Unified wrapper for invoking amplihack skills in Copilot CLI context."""

    def __init__(self, registry_path: Optional[Path] = None):
        """Initialize wrapper with skills registry.

        Args:
            registry_path: Path to SKILLS_REGISTRY.json
        """
        if registry_path is None:
            # Default path
            project_root = Path(__file__).parent.parent.parent.parent.parent
            registry_path = project_root / '.github' / 'skills' / 'SKILLS_REGISTRY.json'

        self.registry_path = Path(registry_path)
        self.registry: Dict[str, Any] = {}
        self._load_registry()

    def _load_registry(self):
        """Load skills registry from JSON file."""
        if not self.registry_path.exists():
            raise FileNotFoundError(
                f"Skills registry not found: {self.registry_path}\n"
                f"Run 'amplihack sync-skills' to generate it."
            )

        try:
            self.registry = json.loads(self.registry_path.read_text())
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid registry JSON: {e}")

    def get_skill_info(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """Get skill information from registry.

        Args:
            skill_name: Name of skill

        Returns:
            Skill metadata dict or None if not found
        """
        skills = self.registry.get('skills', [])
        for skill in skills:
            if skill['name'] == skill_name:
                return skill
        return None

    def invoke_as_agent(
        self,
        skill_name: str,
        context: str,
        agent_dir: Optional[Path] = None
    ) -> SkillInvocationResult:
        """Invoke skill as GitHub Copilot CLI custom agent.

        Args:
            skill_name: Name of skill/agent
            context: User request context
            agent_dir: Directory containing agent definitions

        Returns:
            SkillInvocationResult
        """
        if agent_dir is None:
            project_root = Path(__file__).parent.parent.parent.parent.parent
            agent_dir = project_root / '.github' / 'agents' / 'skills'

        agent_file = agent_dir / f'{skill_name}.yaml'

        if not agent_file.exists():
            return SkillInvocationResult(
                success=False,
                output='',
                error=f'Agent file not found: {agent_file}',
                strategy='custom_agent',
                skill_name=skill_name
            )

        try:
            # Invoke Copilot CLI with custom agent
            result = subprocess.run(
                ['gh', 'copilot', 'agent', skill_name, context],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            return SkillInvocationResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None,
                strategy='custom_agent',
                skill_name=skill_name
            )

        except subprocess.TimeoutExpired:
            return SkillInvocationResult(
                success=False,
                output='',
                error='Agent invocation timed out after 5 minutes',
                strategy='custom_agent',
                skill_name=skill_name
            )
        except FileNotFoundError:
            return SkillInvocationResult(
                success=False,
                output='',
                error='GitHub CLI not found. Install: https://cli.github.com/',
                strategy='custom_agent',
                skill_name=skill_name
            )
        except Exception as e:
            return SkillInvocationResult(
                success=False,
                output='',
                error=f'Error invoking agent: {e}',
                strategy='custom_agent',
                skill_name=skill_name
            )

    def invoke_as_mcp_tool(
        self,
        skill_name: str,
        context: str
    ) -> SkillInvocationResult:
        """Invoke skill via MCP server tool.

        Args:
            skill_name: Name of skill
            context: Tool invocation context

        Returns:
            SkillInvocationResult
        """
        # Get skill info
        skill_info = self.get_skill_info(skill_name)
        if not skill_info:
            return SkillInvocationResult(
                success=False,
                output='',
                error=f'Skill not found in registry: {skill_name}',
                strategy='mcp_tool',
                skill_name=skill_name
            )

        # Map skill to MCP tool
        tool_mapping = {
            'pdf': 'pdf_process',
            'docx': 'docx_process',
            'xlsx': 'xlsx_process',
            'pptx': 'pptx_process',
            'dynamic-debugger': 'debug_code',
            'eval-recipes-runner': 'run_eval',
            'model-evaluation-benchmark': 'benchmark_model'
        }

        tool_name = tool_mapping.get(skill_name)
        if not tool_name:
            return SkillInvocationResult(
                success=False,
                output='',
                error=f'No MCP tool mapping for skill: {skill_name}',
                strategy='mcp_tool',
                skill_name=skill_name
            )

        # Note: Actual MCP invocation would go here
        # For now, return informational result
        return SkillInvocationResult(
            success=True,
            output=f'MCP tool invocation: {tool_name}\nContext: {context}',
            error=None,
            strategy='mcp_tool',
            skill_name=skill_name
        )

    def invoke_skill(
        self,
        skill_name: str,
        context: str,
        force_strategy: Optional[str] = None
    ) -> SkillInvocationResult:
        """Invoke skill using appropriate strategy.

        Args:
            skill_name: Name of skill
            context: Invocation context
            force_strategy: Force specific strategy (custom_agent, mcp_tool)

        Returns:
            SkillInvocationResult
        """
        # Get skill info
        skill_info = self.get_skill_info(skill_name)
        if not skill_info:
            return SkillInvocationResult(
                success=False,
                output='',
                error=f'Skill not found: {skill_name}',
                skill_name=skill_name
            )

        # Determine strategy
        strategy = force_strategy or skill_info['mapping_strategy']

        # Route to appropriate handler
        if strategy == 'custom_agent':
            return self.invoke_as_agent(skill_name, context)
        elif strategy == 'mcp_tool':
            return self.invoke_as_mcp_tool(skill_name, context)
        elif strategy == 'hybrid':
            # Try agent first, fall back to MCP
            result = self.invoke_as_agent(skill_name, context)
            if not result.success:
                result = self.invoke_as_mcp_tool(skill_name, context)
            return result
        elif strategy == 'documentation':
            return SkillInvocationResult(
                success=True,
                output=f'Skill {skill_name} is documentation-only.\n'
                       f'See: {skill_info["skill_file"]}',
                strategy='documentation',
                skill_name=skill_name
            )
        else:
            return SkillInvocationResult(
                success=False,
                output='',
                error=f'Unknown strategy: {strategy}',
                skill_name=skill_name
            )

    def list_skills(
        self,
        category: Optional[str] = None,
        strategy: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List all skills, optionally filtered.

        Args:
            category: Filter by category
            strategy: Filter by mapping strategy

        Returns:
            List of skill metadata dicts
        """
        skills = self.registry.get('skills', [])

        # Apply filters
        if category:
            skills = [s for s in skills if s['category'] == category]

        if strategy:
            skills = [s for s in skills if s['mapping_strategy'] == strategy]

        return skills

    def get_statistics(self) -> Dict[str, Any]:
        """Get skills statistics from registry.

        Returns:
            Statistics dictionary
        """
        return self.registry.get('statistics', {})


def main():
    """CLI entry point for skills wrapper."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Invoke amplihack skills for Copilot CLI'
    )

    subparsers = parser.add_subparsers(dest='command', help='Command')

    # Invoke command
    invoke_parser = subparsers.add_parser('invoke', help='Invoke a skill')
    invoke_parser.add_argument('skill', help='Skill name')
    invoke_parser.add_argument('context', help='Invocation context')
    invoke_parser.add_argument(
        '--strategy',
        choices=['custom_agent', 'mcp_tool'],
        help='Force specific invocation strategy'
    )

    # List command
    list_parser = subparsers.add_parser('list', help='List skills')
    list_parser.add_argument('--category', help='Filter by category')
    list_parser.add_argument('--strategy', help='Filter by mapping strategy')
    list_parser.add_argument(
        '--format',
        choices=['summary', 'json'],
        default='summary',
        help='Output format'
    )

    # Stats command
    subparsers.add_parser('stats', help='Show skills statistics')

    args = parser.parse_args()

    # Initialize wrapper
    wrapper = SkillsWrapper()

    if args.command == 'invoke':
        # Invoke skill
        print(f"Invoking skill: {args.skill}")
        if args.strategy:
            print(f"Strategy: {args.strategy}")
        print()

        result = wrapper.invoke_skill(
            args.skill,
            args.context,
            force_strategy=args.strategy
        )

        if result.success:
            print("✓ Success")
            print(f"\nOutput:\n{result.output}")
        else:
            print("✗ Failed")
            print(f"\nError: {result.error}")

        exit(0 if result.success else 1)

    elif args.command == 'list':
        # List skills
        skills = wrapper.list_skills(
            category=args.category,
            strategy=args.strategy
        )

        if args.format == 'json':
            print(json.dumps(skills, indent=2))
        else:
            print(f"Skills ({len(skills)}):")
            for skill in skills:
                name = skill['name']
                desc = skill['description'].split('\n')[0]  # First line
                strategy = skill['mapping_strategy']
                print(f"  - {name} ({strategy})")
                print(f"    {desc}")

    elif args.command == 'stats':
        # Show statistics
        stats = wrapper.get_statistics()
        print("Skills Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
