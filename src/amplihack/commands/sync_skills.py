"""Sync Skills Command - Generate and sync amplihack skills for Copilot CLI.

This command:
1. Scans all amplihack skills
2. Generates skills registry
3. Converts skills to custom agents
4. Updates MCP server with tool mappings

Philosophy: Single command for complete skills integration.
"""

from pathlib import Path
from typing import Optional

from ..adapters.skills_mapper import SkillsMapper
from ..adapters.skills_to_agents import SkillsToAgentsConverter


def sync_skills_command(
    output_dir: Optional[Path] = None,
    registry_path: Optional[Path] = None,
    strategies: Optional[list[str]] = None,
    verbose: bool = False
) -> int:
    """Sync amplihack skills for Copilot CLI usage.

    Args:
        output_dir: Output directory for agent files
        registry_path: Path for skills registry JSON
        strategies: Mapping strategies to include
        verbose: Enable verbose output

    Returns:
        Exit code (0 = success)
    """
    try:
        # Default paths
        if output_dir is None:
            # Navigate from src/amplihack/commands to project root
            project_root = Path(__file__).parent.parent.parent.parent
            output_dir = project_root / '.github' / 'agents' / 'skills'

        if registry_path is None:
            # Navigate from src/amplihack/commands to project root
            project_root = Path(__file__).parent.parent.parent.parent
            registry_path = project_root / '.github' / 'skills' / 'SKILLS_REGISTRY.json'

        if strategies is None:
            strategies = ['custom_agent', 'hybrid']

        print("=" * 70)
        print("Syncing amplihack skills for GitHub Copilot CLI")
        print("=" * 70)
        print()

        # Step 1: Scan and map skills
        print("Step 1/4: Scanning skills...")
        mapper = SkillsMapper()
        skills = mapper.scan_all_skills()
        print(f"  ✓ Found {len(skills)} skills")
        print()

        # Step 2: Generate registry
        print("Step 2/4: Generating skills registry...")
        registry = mapper.generate_registry(registry_path)
        print(f"  ✓ Registry saved: {registry_path}")
        print(f"    - Total skills: {registry['total_skills']}")
        print(f"    - Custom agents: {registry['statistics']['custom_agents']}")
        print(f"    - MCP tools: {registry['statistics']['mcp_tools']}")
        print(f"    - Hybrid: {registry['statistics']['hybrid']}")
        print(f"    - Documentation only: {registry['statistics']['documentation_only']}")
        print()

        # Step 3: Convert skills to agents
        print("Step 3/4: Converting skills to custom agents...")
        converter = SkillsToAgentsConverter(mapper)
        agents = converter.convert_all_skills(
            output_dir=output_dir,
            include_strategies=strategies
        )
        print(f"  ✓ Generated {len(agents)} agent files: {output_dir}")
        print()

        # Step 4: Generate index
        print("Step 4/4: Generating agents index...")
        index_content = converter.generate_agents_index(agents)
        index_file = output_dir / 'README.md'
        index_file.write_text(index_content)
        print(f"  ✓ Index created: {index_file}")
        print()

        # Show summary if verbose
        if verbose:
            print("Agents by category:")
            by_category = {}
            for name, agent in agents.items():
                skill = next(
                    (s for s in mapper.skills if s.name == name),
                    None
                )
                if skill:
                    cat = skill.category
                    if cat not in by_category:
                        by_category[cat] = []
                    by_category[cat].append(name)

            for category in sorted(by_category.keys()):
                skill_names = by_category[category]
                print(f"  {category}: {len(skill_names)} agents")
                for name in sorted(skill_names):
                    print(f"    - {name}")
            print()

        print("=" * 70)
        print("Skills sync complete!")
        print()
        print("Next steps:")
        print("  1. Review generated agents in: .github/agents/skills/")
        print("  2. Test with: gh copilot agent <agent-name> \"<request>\"")
        print("  3. Customize agents as needed for your workflows")
        print("=" * 70)

        return 0

    except Exception as e:
        print(f"\n✗ Error: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return 1


def main():
    """CLI entry point for sync-skills command."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Sync amplihack skills for GitHub Copilot CLI'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        help='Output directory for agent files (default: .github/agents/skills)'
    )
    parser.add_argument(
        '--registry-path',
        type=Path,
        help='Path for skills registry JSON (default: .github/skills/SKILLS_REGISTRY.json)'
    )
    parser.add_argument(
        '--strategies',
        nargs='+',
        choices=['custom_agent', 'hybrid', 'mcp_tool', 'documentation'],
        help='Mapping strategies to include (default: custom_agent hybrid)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )

    args = parser.parse_args()

    exit(sync_skills_command(
        output_dir=args.output_dir,
        registry_path=args.registry_path,
        strategies=args.strategies,
        verbose=args.verbose
    ))


if __name__ == '__main__':
    main()
