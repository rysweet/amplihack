"""Skills to Agents Converter - Convert amplihack skills to Copilot CLI custom agents.

This module converts interactive amplihack skills into GitHub Copilot CLI custom agents,
preserving skill logic and adapting for Copilot invocation patterns.

Philosophy: Zero-BS - every generated agent works, no stubs or placeholders.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from .skills_mapper import SkillsMapper, SkillMetadata


@dataclass
class AgentDefinition:
    """Definition for a GitHub Copilot CLI custom agent."""

    name: str
    description: str
    instructions: str
    model: str
    tools: List[str]
    activation_keywords: List[str]
    source_skill: str

    def to_agent_file(self) -> str:
        """Generate GitHub Copilot CLI agent YAML file content."""
        tools_str = '\n'.join(f'  - {tool}' for tool in self.tools)

        activation_str = '\n'.join(
            f'  - {kw}' for kw in self.activation_keywords
        )

        return f"""# GitHub Copilot CLI Custom Agent
# Generated from amplihack skill: {self.source_skill}

name: {self.name}
description: |
  {self.description}

model: {self.model}

tools:
{tools_str if self.tools else '  []'}

activation_keywords:
{activation_str if self.activation_keywords else '  []'}

instructions: |
{self._indent_instructions(self.instructions, 2)}

# Source: {self.source_skill}
"""

    def _indent_instructions(self, text: str, spaces: int) -> str:
        """Indent multi-line text by specified spaces."""
        indent = ' ' * spaces
        lines = text.strip().split('\n')
        return '\n'.join(f'{indent}{line}' for line in lines)


class SkillsToAgentsConverter:
    """Convert amplihack skills to GitHub Copilot CLI custom agents."""

    # Default model for agents
    DEFAULT_MODEL = 'claude-sonnet-4.5'

    # Copilot CLI tool mapping
    COPILOT_TOOLS = {
        'bash': 'terminal',
        'read_file': 'file-read',
        'write_file': 'file-write',
        'edit_file': 'file-edit',
        'glob': 'file-search',
        'grep': 'content-search'
    }

    def __init__(self, mapper: Optional[SkillsMapper] = None):
        """Initialize converter with skills mapper."""
        self.mapper = mapper or SkillsMapper()
        if not self.mapper.skills:
            self.mapper.scan_all_skills()

    def extract_skill_instructions(self, skill: SkillMetadata) -> str:
        """Extract main instructions from skill file.

        Args:
            skill: Skill metadata

        Returns:
            Instructions text for agent
        """
        try:
            content = skill.skill_file.read_text()

            # Skip frontmatter
            if content.startswith('---'):
                second_delimiter = content.find('---', 3)
                if second_delimiter != -1:
                    content = content[second_delimiter + 3:].strip()

            # Extract main content (first few sections)
            # Remove first heading if present
            lines = content.split('\n')
            filtered_lines = []
            in_code_block = False

            for line in lines:
                # Track code blocks
                if line.strip().startswith('```'):
                    in_code_block = not in_code_block

                # Skip certain sections for brevity
                if not in_code_block:
                    if line.startswith('## Next Steps') or \
                       line.startswith('## Resources') or \
                       line.startswith('## Navigation Guide'):
                        break

                filtered_lines.append(line)

            # Limit to reasonable size (first ~100 lines)
            instructions = '\n'.join(filtered_lines[:100])

            return instructions.strip()

        except Exception as e:
            return f"Error extracting instructions: {e}"

    def map_tools_to_copilot(self, tools_required: List[str]) -> List[str]:
        """Map amplihack tools to Copilot CLI tool names.

        Args:
            tools_required: List of tool paths or names

        Returns:
            List of Copilot CLI tool names
        """
        copilot_tools = []

        for tool in tools_required:
            tool_lower = tool.lower()

            # Check for known tool patterns
            if 'bash' in tool_lower or 'sh' in tool_lower:
                copilot_tools.append('terminal')
            elif 'read' in tool_lower:
                copilot_tools.append('file-read')
            elif 'write' in tool_lower:
                copilot_tools.append('file-write')
            elif 'edit' in tool_lower:
                copilot_tools.append('file-edit')
            elif 'glob' in tool_lower or 'find' in tool_lower:
                copilot_tools.append('file-search')
            elif 'grep' in tool_lower or 'search' in tool_lower:
                copilot_tools.append('content-search')

        # Remove duplicates while preserving order
        seen = set()
        unique_tools = []
        for tool in copilot_tools:
            if tool not in seen:
                seen.add(tool)
                unique_tools.append(tool)

        return unique_tools

    def convert_skill_to_agent(self, skill: SkillMetadata) -> Optional[AgentDefinition]:
        """Convert single skill to agent definition.

        Args:
            skill: Skill metadata

        Returns:
            AgentDefinition or None if skill should not be converted
        """
        # Skip documentation-only skills
        if skill.mapping_strategy == 'documentation':
            return None

        # Extract instructions
        instructions = self.extract_skill_instructions(skill)

        # Map tools
        copilot_tools = self.map_tools_to_copilot(skill.tools_required)

        # Create agent definition
        agent = AgentDefinition(
            name=skill.name,
            description=skill.description or f'Agent for {skill.name}',
            instructions=instructions,
            model=self.DEFAULT_MODEL,
            tools=copilot_tools,
            activation_keywords=skill.activation_keywords,
            source_skill=str(skill.skill_file)
        )

        return agent

    def convert_all_skills(
        self,
        output_dir: Optional[Path] = None,
        include_strategies: Optional[List[str]] = None
    ) -> Dict[str, AgentDefinition]:
        """Convert all eligible skills to agents.

        Args:
            output_dir: Optional directory to save agent files
            include_strategies: Optional list of strategies to include
                               (default: custom_agent, hybrid)

        Returns:
            Dictionary mapping skill name to agent definition
        """
        if include_strategies is None:
            include_strategies = ['custom_agent', 'hybrid']

        agents = {}

        for skill in self.mapper.skills:
            # Filter by strategy
            if skill.mapping_strategy not in include_strategies:
                continue

            # Convert skill
            agent = self.convert_skill_to_agent(skill)
            if agent is None:
                continue

            agents[skill.name] = agent

            # Save to file if output directory provided
            if output_dir:
                output_dir.mkdir(parents=True, exist_ok=True)
                agent_file = output_dir / f'{skill.name}.yaml'
                agent_file.write_text(agent.to_agent_file())

        return agents

    def generate_agents_index(self, agents: Dict[str, AgentDefinition]) -> str:
        """Generate index/README for agents directory.

        Args:
            agents: Dictionary of agent definitions

        Returns:
            Markdown content for README
        """
        # Group by category
        by_category = {}
        for name, agent in agents.items():
            # Find original skill
            skill = next(
                (s for s in self.mapper.skills if s.name == name),
                None
            )
            if skill:
                cat = skill.category
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append((name, agent))

        # Build README
        lines = [
            '# GitHub Copilot CLI Custom Agents',
            '',
            'Custom agents generated from amplihack skills for use with GitHub Copilot CLI.',
            '',
            f'**Total agents:** {len(agents)}',
            '',
            '## Usage',
            '',
            'Invoke agents in Copilot CLI:',
            '',
            '```bash',
            'gh copilot agent <agent-name> "<your request>"',
            '```',
            '',
            '## Available Agents',
            ''
        ]

        for category in sorted(by_category.keys()):
            agents_list = by_category[category]
            cat_desc = self.mapper.CATEGORIES.get(category, 'Unknown')

            lines.append(f'### {category.replace("_", " ").title()}')
            lines.append(f'*{cat_desc}*')
            lines.append('')

            for name, agent in sorted(agents_list, key=lambda x: x[0]):
                desc = agent.description.split('\n')[0]  # First line only
                lines.append(f'- **{name}**: {desc}')

            lines.append('')

        lines.extend([
            '## Integration',
            '',
            'These agents integrate with:',
            '- GitHub Copilot CLI tool invocation',
            '- amplihack MCP server for enhanced capabilities',
            '- Local file system access',
            '- Terminal command execution',
            '',
            '## Generated',
            '',
            f'Generated from {len(agents)} amplihack skills using `amplihack sync-skills`.',
            ''
        ])

        return '\n'.join(lines)


def main():
    """CLI entry point for skills to agents converter."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Convert amplihack skills to Copilot CLI agents'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        required=True,
        help='Output directory for agent files'
    )
    parser.add_argument(
        '--strategies',
        nargs='+',
        choices=['custom_agent', 'hybrid', 'mcp_tool', 'documentation'],
        default=['custom_agent', 'hybrid'],
        help='Mapping strategies to include'
    )
    parser.add_argument(
        '--generate-index',
        action='store_true',
        help='Generate README.md index file'
    )

    args = parser.parse_args()

    # Initialize converter
    converter = SkillsToAgentsConverter()

    # Convert skills
    print(f"Converting skills to agents...")
    print(f"Output directory: {args.output_dir}")
    print(f"Strategies: {', '.join(args.strategies)}")
    print()

    agents = converter.convert_all_skills(
        output_dir=args.output_dir,
        include_strategies=args.strategies
    )

    print(f"✓ Converted {len(agents)} skills to agents")

    # Generate index if requested
    if args.generate_index:
        index_content = converter.generate_agents_index(agents)
        index_file = args.output_dir / 'README.md'
        index_file.write_text(index_content)
        print(f"✓ Generated index: {index_file}")

    # Summary by category
    by_category = {}
    for name, agent in agents.items():
        skill = next(
            (s for s in converter.mapper.skills if s.name == name),
            None
        )
        if skill:
            cat = skill.category
            if cat not in by_category:
                by_category[cat] = 0
            by_category[cat] += 1

    print("\nAgents by category:")
    for category in sorted(by_category.keys()):
        count = by_category[category]
        print(f"  - {category}: {count}")


if __name__ == '__main__':
    main()
