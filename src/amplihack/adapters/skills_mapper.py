"""Skills Mapper - Analyze and map amplihack skills for Copilot CLI usage.

This module scans all amplihack skills and determines the optimal mapping strategy:
- custom_agent: Convert to GitHub Copilot custom agent
- mcp_tool: Expose via MCP server tool
- hybrid: Both agent and MCP tool
- documentation: Reference only (no conversion needed)

Philosophy: Ruthless simplicity - automatic categorization based on skill characteristics.
"""

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any


@dataclass
class SkillMetadata:
    """Metadata extracted from skill file frontmatter."""

    name: str
    category: str
    mapping_strategy: str
    description: str
    auto_activate: bool
    tools_required: List[str]
    skill_file: Path
    activation_keywords: List[str]
    version: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with string paths."""
        data = asdict(self)
        data['skill_file'] = str(self.skill_file)
        return data


class SkillsMapper:
    """Scan and analyze all amplihack skills for Copilot CLI integration."""

    # Skill categories
    CATEGORIES = {
        'analyst': 'Perspective analysts (anthropologist, economist, etc.)',
        'workflow': 'Multi-step workflow orchestration',
        'tool_handler': 'File format and tool handlers (PDF, DOCX, etc.)',
        'integration': 'External service integrations (Azure, DevOps)',
        'code_quality': 'Code review and quality assurance',
        'documentation': 'Documentation and visualization',
        'productivity': 'Productivity and synthesis',
        'framework': 'Framework and SDK knowledge',
        'orchestration': 'Meta-orchestration and delegation',
        'management': 'Context and resource management',
        'evaluation': 'Model and system evaluation',
        'domain_specialized': 'Specialized domain expertise',
        'library': 'Common libraries and utilities',
        'misc': 'Miscellaneous'
    }

    # Mapping strategies
    STRATEGIES = {
        'custom_agent': 'Convert to GitHub Copilot custom agent',
        'mcp_tool': 'Expose via MCP server tool',
        'hybrid': 'Both custom agent and MCP tool',
        'documentation': 'Reference documentation only'
    }

    def __init__(self, skills_dir: Optional[Path] = None):
        """Initialize mapper with skills directory."""
        if skills_dir is None:
            # Default to amplihack skills directory
            # Navigate from src/amplihack/adapters to project root
            project_root = Path(__file__).parent.parent.parent.parent
            skills_dir = project_root / '.claude' / 'skills'

        self.skills_dir = Path(skills_dir)
        self.skills: List[SkillMetadata] = []

    def extract_frontmatter(self, skill_file: Path) -> Dict[str, Any]:
        """Extract YAML frontmatter from skill file.

        Args:
            skill_file: Path to SKILL.md file

        Returns:
            Dictionary of frontmatter fields
        """
        try:
            content = skill_file.read_text()

            if not content.startswith('---'):
                return {}

            # Find second ---
            end = content.find('---', 3)
            if end == -1:
                return {}

            frontmatter_text = content[3:end].strip()

            # Parse YAML frontmatter (simplified parser)
            result = {}
            current_key = None
            list_items = []

            for line in frontmatter_text.split('\n'):
                line = line.rstrip()

                # List item
                if line.strip().startswith('- '):
                    if current_key:
                        list_items.append(line.strip()[2:])
                    continue

                # Key-value pair
                if ':' in line and not line.startswith(' '):
                    # Save previous list if any
                    if current_key and list_items:
                        result[current_key] = list_items
                        list_items = []

                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()

                    if value:
                        result[key] = value
                        current_key = None
                    else:
                        current_key = key
                        list_items = []
                elif current_key and line.strip() and line.startswith(' '):
                    # Multi-line value
                    if not list_items:
                        result[current_key] = line.strip()

            # Save final list if any
            if current_key and list_items:
                result[current_key] = list_items

            return result

        except Exception as e:
            return {"error": str(e)}

    def categorize_skill(self, name: str, frontmatter: Dict[str, Any]) -> str:
        """Determine skill category based on name and characteristics.

        Args:
            name: Skill directory name
            frontmatter: Extracted frontmatter metadata

        Returns:
            Category name from CATEGORIES
        """
        name_lower = name.lower()

        # Analyst skills
        if 'analyst' in name_lower:
            return 'analyst'

        # Workflow skills
        workflow_skills = [
            'cascade-workflow', 'debate-workflow', 'n-version-workflow',
            'default-workflow', 'investigation-workflow', 'consensus-voting',
            'philosophy-compliance-workflow', 'quality-audit-workflow'
        ]
        if 'workflow' in name_lower or name in workflow_skills:
            return 'workflow'

        # Tool/Format handlers
        tool_handlers = ['pdf', 'docx', 'xlsx', 'pptx', 'dynamic-debugger']
        if name in tool_handlers:
            return 'tool_handler'

        # Azure/DevOps integrations
        if 'azure' in name_lower or 'devops' in name_lower:
            return 'integration'

        # Code quality/development
        code_quality = [
            'code-smell-detector', 'outside-in-testing', 'test-gap-analyzer',
            'design-patterns-expert', 'module-spec-generator', 'pr-review-assistant'
        ]
        if name in code_quality:
            return 'code_quality'

        # Documentation/visualization
        docs = [
            'documentation-writing', 'mermaid-diagram-generator',
            'storytelling-synthesizer'
        ]
        if name in docs:
            return 'documentation'

        # Productivity/synthesis
        productivity = [
            'email-drafter', 'meeting-synthesizer', 'knowledge-extractor',
            'learning-path-builder', 'backlog-curator'
        ]
        if name in productivity:
            return 'productivity'

        # Framework/SDK skills
        frameworks = [
            'agent-sdk', 'microsoft-agent-framework', 'github-copilot-cli-expert'
        ]
        if name in frameworks:
            return 'framework'

        # Meta/orchestration
        orchestration = [
            'ultrathink-orchestrator', 'work-delegator', 'workstream-coordinator',
            'skill-builder', 'goal-seeking-agent-pattern'
        ]
        if name in orchestration:
            return 'orchestration'

        # Context/management
        management = ['context_management', 'mcp-manager', 'remote-work']
        if name in management:
            return 'management'

        # Model evaluation
        evaluation = ['model-evaluation-benchmark', 'eval-recipes-runner']
        if name in evaluation:
            return 'evaluation'

        # Specialized domain
        domain = ['pm-architect', 'roadmap-strategist']
        if name in domain:
            return 'domain_specialized'

        # Common/library
        library = [
            'common', 'development', 'collaboration', 'meta-cognitive',
            'quality', 'research'
        ]
        if name in library:
            return 'library'

        return 'misc'

    def determine_mapping_strategy(
        self, category: str, name: str, frontmatter: Dict[str, Any]
    ) -> str:
        """Determine optimal mapping strategy for skill.

        Args:
            category: Skill category
            name: Skill name
            frontmatter: Extracted metadata

        Returns:
            Mapping strategy from STRATEGIES
        """
        # Programmatic tools → MCP server
        if category == 'tool_handler':
            return 'mcp_tool'

        # Workflows → Custom agents (state management)
        if category == 'workflow':
            return 'custom_agent'

        # Analysts → Custom agents (conversational)
        if category == 'analyst':
            return 'custom_agent'

        # Integrations → Hybrid (agent + MCP)
        if category == 'integration':
            return 'hybrid'

        # Code quality → Custom agents
        if category == 'code_quality':
            return 'custom_agent'

        # Documentation/visualization → Custom agents
        if category in ['documentation', 'productivity']:
            return 'custom_agent'

        # Frameworks → Documentation only (no conversion)
        if category == 'framework':
            return 'documentation'

        # Orchestration → Custom agents
        if category == 'orchestration':
            return 'custom_agent'

        # Management → Hybrid
        if category == 'management':
            return 'hybrid'

        # Evaluation → MCP tools
        if category == 'evaluation':
            return 'mcp_tool'

        # Domain specialized → Custom agents
        if category == 'domain_specialized':
            return 'custom_agent'

        # Library → Documentation only
        if category == 'library':
            return 'documentation'

        # Default: custom agent
        return 'custom_agent'

    def scan_all_skills(self) -> List[SkillMetadata]:
        """Scan all skills and extract metadata.

        Returns:
            List of skill metadata objects
        """
        skills = []

        for skill_dir in sorted(self.skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue

            name = skill_dir.name

            # Find SKILL.md or skill.md
            skill_file = skill_dir / 'SKILL.md'
            if not skill_file.exists():
                skill_file = skill_dir / 'skill.md'

            if not skill_file.exists():
                # No skill file - skip
                continue

            # Extract frontmatter
            frontmatter = self.extract_frontmatter(skill_file)

            # Categorize and determine strategy
            category = self.categorize_skill(name, frontmatter)
            strategy = self.determine_mapping_strategy(category, name, frontmatter)

            # Extract activation keywords
            keywords = []
            if 'activation_keywords' in frontmatter:
                kw = frontmatter['activation_keywords']
                if isinstance(kw, list):
                    keywords = kw
                elif isinstance(kw, str):
                    keywords = [kw]
            elif 'auto_activate_keywords' in frontmatter:
                kw = frontmatter['auto_activate_keywords']
                if isinstance(kw, list):
                    keywords = kw
                elif isinstance(kw, str):
                    keywords = [kw]

            # Extract tools
            tools = []
            if 'tools_required' in frontmatter:
                tools_val = frontmatter['tools_required']
                if isinstance(tools_val, list):
                    tools = tools_val

            # Create metadata object
            metadata = SkillMetadata(
                name=name,
                category=category,
                mapping_strategy=strategy,
                description=frontmatter.get('description', ''),
                auto_activate='auto_activate' in frontmatter and \
                    frontmatter.get('auto_activate', '').lower() == 'true',
                tools_required=tools,
                skill_file=skill_file,
                activation_keywords=keywords,
                version=frontmatter.get('version', '1.0.0')
            )

            skills.append(metadata)

        self.skills = skills
        return skills

    def generate_registry(self, output_path: Optional[Path] = None) -> Dict[str, Any]:
        """Generate complete skills registry.

        Args:
            output_path: Optional path to save registry JSON

        Returns:
            Registry dictionary
        """
        if not self.skills:
            self.scan_all_skills()

        # Group by category
        by_category = {}
        for skill in self.skills:
            cat = skill.category
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(skill.name)

        # Group by strategy
        by_strategy = {}
        for skill in self.skills:
            strat = skill.mapping_strategy
            if strat not in by_strategy:
                by_strategy[strat] = []
            by_strategy[strat].append(skill.name)

        # Build registry
        registry = {
            'total_skills': len(self.skills),
            'categories': self.CATEGORIES,
            'strategies': self.STRATEGIES,
            'skills': [skill.to_dict() for skill in self.skills],
            'by_category': by_category,
            'by_strategy': by_strategy,
            'statistics': {
                'custom_agents': len(by_strategy.get('custom_agent', [])),
                'mcp_tools': len(by_strategy.get('mcp_tool', [])),
                'hybrid': len(by_strategy.get('hybrid', [])),
                'documentation_only': len(by_strategy.get('documentation', []))
            }
        }

        # Save if output path provided
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(registry, indent=2))

        return registry

    def print_summary(self):
        """Print human-readable summary of skills mapping."""
        if not self.skills:
            self.scan_all_skills()

        print(f"Total Skills: {len(self.skills)}\n")
        print("=" * 70)

        # Group by category
        by_category = {}
        for skill in self.skills:
            cat = skill.category
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(skill)

        print("\nSKILLS BY CATEGORY:")
        print("-" * 70)
        for category, skills_list in sorted(by_category.items()):
            desc = self.CATEGORIES.get(category, 'Unknown')
            print(f"\n{category.upper()} ({len(skills_list)} skills)")
            print(f"  {desc}")
            for skill in sorted(skills_list, key=lambda s: s.name):
                print(f"  • {skill.name} → {skill.mapping_strategy}")

        # Group by strategy
        by_strategy = {}
        for skill in self.skills:
            strat = skill.mapping_strategy
            if strat not in by_strategy:
                by_strategy[strat] = []
            by_strategy[strat].append(skill)

        print("\n\nMAPPING STRATEGIES:")
        print("=" * 70)
        for strategy, skills_list in sorted(by_strategy.items()):
            desc = self.STRATEGIES.get(strategy, 'Unknown')
            print(f"\n{strategy.upper()} ({len(skills_list)} skills)")
            print(f"  {desc}")
            for skill in sorted(skills_list, key=lambda s: s.name):
                print(f"  • {skill.name}")

        print("\n" + "=" * 70)
        print(f"Summary: {len(self.skills)} skills mapped for Copilot CLI")
        print(f"  - {len(by_strategy.get('custom_agent', []))} custom agents")
        print(f"  - {len(by_strategy.get('mcp_tool', []))} MCP tools")
        print(f"  - {len(by_strategy.get('hybrid', []))} hybrid (agent + MCP)")
        print(f"  - {len(by_strategy.get('documentation', []))} documentation only")
        print("=" * 70)


def main():
    """CLI entry point for skills mapper."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Map amplihack skills for GitHub Copilot CLI'
    )
    parser.add_argument(
        '--skills-dir',
        type=Path,
        help='Path to skills directory (default: .claude/skills)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Output path for registry JSON'
    )
    parser.add_argument(
        '--format',
        choices=['summary', 'json', 'both'],
        default='summary',
        help='Output format'
    )

    args = parser.parse_args()

    mapper = SkillsMapper(args.skills_dir)

    if args.format in ['summary', 'both']:
        mapper.print_summary()

    if args.format in ['json', 'both']:
        registry = mapper.generate_registry(args.output)
        if not args.output:
            print(json.dumps(registry, indent=2))


if __name__ == '__main__':
    main()
