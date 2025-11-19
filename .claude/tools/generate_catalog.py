#!/usr/bin/env python3
"""
Generate component catalog from frontmatter metadata.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import yaml


def extract_frontmatter(file_path: Path) -> Dict[str, Any]:
    """Extract YAML frontmatter from markdown file."""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # Match frontmatter between --- markers
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        if match:
            frontmatter_text = match.group(1)
            metadata = yaml.safe_load(frontmatter_text)
            return metadata if metadata else {}
        return {}
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return {}


def find_components(base_path: Path, subdir: str, extension: str = "*.md") -> List[Path]:
    """Find all component files in a subdirectory."""
    search_path = base_path / subdir
    if not search_path.exists():
        return []
    return sorted(search_path.rglob(extension))


def format_workflow(path: Path, metadata: Dict) -> str:
    """Format workflow entry."""
    name = metadata.get("name", path.stem)
    version = metadata.get("version", "N/A")
    desc = metadata.get("description", "No description")
    steps = metadata.get("steps", "N/A")
    phases = metadata.get("phases", [])

    entry = f"### {name} (v{version})\n\n"
    entry += f"**Description**: {desc}\n\n"
    entry += f"**Steps/Phases**: {steps}\n\n"
    if phases:
        entry += f"**Phases**: {', '.join(phases)}\n\n"
    entry += f"**Location**: `{path.relative_to(Path.cwd())}`\n\n"

    return entry


def format_command(path: Path, metadata: Dict) -> str:
    """Format command entry."""
    name = metadata.get("name", path.stem)
    version = metadata.get("version", "N/A")
    desc = metadata.get("description", "No description")
    triggers = metadata.get("triggers", [])
    invokes = metadata.get("invokes", [])

    # Determine command path based on directory structure
    rel_path = path.relative_to(Path.cwd())
    parts = rel_path.parts
    if "amplihack" in parts:
        cmd_name = f"/amplihack:{name}"
    elif "ddd" in parts:
        cmd_name = f"/ddd:{name}"
    else:
        cmd_name = f"/{name}"

    entry = f"### {cmd_name} (v{version})\n\n"
    entry += f"**Description**: {desc}\n\n"

    if triggers:
        entry += f"**Triggers**: {', '.join(triggers)}\n\n"

    if invokes:
        entry += "**Invokes**:\n"
        for invoke in invokes:
            if isinstance(invoke, dict):
                inv_type = invoke.get("type", "unknown")
                inv_path = invoke.get("path", "N/A")
                entry += f"  - {inv_type}: `{inv_path}`\n"
        entry += "\n"

    entry += f"**Location**: `{rel_path}`\n\n"

    return entry


def format_skill(path: Path, metadata: Dict) -> str:
    """Format skill entry."""
    name = metadata.get("name", path.stem)
    version = metadata.get("version", "N/A")
    desc = metadata.get("description", "No description")
    keywords = metadata.get("activation_keywords", [])
    auto_activate = metadata.get("auto_activate", False)

    entry = f"### {name} (v{version})\n\n"
    entry += f"**Description**: {desc}\n\n"

    if keywords:
        entry += f"**Activation Keywords**: {', '.join(keywords)}\n\n"

    entry += f"**Auto-activate**: {'Yes' if auto_activate else 'No'}\n\n"
    entry += f"**Location**: `{path.relative_to(Path.cwd())}`\n\n"

    return entry


def format_agent(path: Path, metadata: Dict) -> str:
    """Format agent entry."""
    name = metadata.get("name", path.stem)
    version = metadata.get("version", "N/A")
    desc = metadata.get("description", "No description")
    role = metadata.get("role", "N/A")

    entry = f"### {name} (v{version})\n\n"
    entry += f"**Description**: {desc}\n\n"

    if role and role != "N/A":
        entry += f"**Role**: {role}\n\n"

    entry += f"**Location**: `{path.relative_to(Path.cwd())}`\n\n"

    return entry


def generate_catalog():
    """Generate complete component catalog."""
    base_path = Path.cwd()
    catalog_path = base_path / ".claude" / "context" / "COMPONENT_CATALOG.md"

    # Initialize catalog
    catalog = f"""# Amplihack Component Catalog

Auto-generated from frontmatter metadata.

**Last Updated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

This catalog provides a comprehensive reference to all workflows, commands, skills, and agents in the amplihack framework.

---

"""

    # Workflows
    catalog += "## Workflows\n\n"
    workflows = find_components(base_path, ".claude/workflow")
    workflow_entries = []
    for wf in workflows:
        if wf.name in ["README.md", "CONSENSUS_WORKFLOWS_OVERVIEW.md"]:
            continue
        metadata = extract_frontmatter(wf)
        if metadata:
            workflow_entries.append(format_workflow(wf, metadata))

    catalog += f"**Total**: {len(workflow_entries)} workflows\n\n"
    catalog += "".join(workflow_entries)
    catalog += "---\n\n"

    # Commands
    catalog += "## Commands\n\n"
    commands = find_components(base_path, ".claude/commands")
    command_entries = []
    for cmd in commands:
        if cmd.name in ["README.md", "SKILL_BUILDER_EXAMPLES.md"]:
            continue
        metadata = extract_frontmatter(cmd)
        if metadata and metadata.get("name"):
            command_entries.append(format_command(cmd, metadata))

    catalog += f"**Total**: {len(command_entries)} commands\n\n"
    catalog += "".join(command_entries)
    catalog += "---\n\n"

    # Skills
    catalog += "## Skills\n\n"
    skills = find_components(base_path, ".claude/skills")
    skill_entries = []
    # Only include SKILL.md files or specific skill markdown files
    for skill in skills:
        if skill.name == "SKILL.md" or (skill.parent.name == "skills" and skill.suffix == ".md"):
            if skill.name in [
                "README.md",
                "SKILLS_QUICK_REFERENCE.md",
                "INTEGRATION_STATUS.md",
                "ANALYST_SEARCH_CAPABILITY.md",
                "ANALYST_VALIDATION_PLAN.md",
            ]:
                continue
            metadata = extract_frontmatter(skill)
            if metadata and metadata.get("name"):
                skill_entries.append(format_skill(skill, metadata))

    catalog += f"**Total**: {len(skill_entries)} skills\n\n"
    catalog += "".join(skill_entries)
    catalog += "---\n\n"

    # Agents
    catalog += "## Agents\n\n"
    agents = find_components(base_path, ".claude/agents")
    agent_entries = []
    for agent in agents:
        if agent.name == "README.md":
            continue
        metadata = extract_frontmatter(agent)
        if metadata and metadata.get("name"):
            agent_entries.append(format_agent(agent, metadata))

    catalog += f"**Total**: {len(agent_entries)} agents\n\n"

    # Group agents by category
    core_agents = []
    specialized_agents = []
    workflow_agents = []
    other_agents = []

    for agent in agents:
        if agent.name == "README.md":
            continue
        metadata = extract_frontmatter(agent)
        if metadata and metadata.get("name"):
            rel_path = agent.relative_to(base_path)
            if "core" in rel_path.parts:
                core_agents.append(format_agent(agent, metadata))
            elif "specialized" in rel_path.parts:
                specialized_agents.append(format_agent(agent, metadata))
            elif "workflows" in rel_path.parts:
                workflow_agents.append(format_agent(agent, metadata))
            else:
                other_agents.append(format_agent(agent, metadata))

    if core_agents:
        catalog += "### Core Agents\n\n"
        catalog += "".join(core_agents)

    if specialized_agents:
        catalog += "### Specialized Agents\n\n"
        catalog += "".join(specialized_agents)

    if workflow_agents:
        catalog += "### Workflow Agents\n\n"
        catalog += "".join(workflow_agents)

    if other_agents:
        catalog += "### Other Agents\n\n"
        catalog += "".join(other_agents)

    catalog += "---\n\n"

    # Summary
    catalog += "## Summary\n\n"
    catalog += f"- **Workflows**: {len(workflow_entries)}\n"
    catalog += f"- **Commands**: {len(command_entries)}\n"
    catalog += f"- **Skills**: {len(skill_entries)}\n"
    catalog += f"- **Agents**: {len(agent_entries)}\n"
    catalog += f"  - Core: {len(core_agents)}\n"
    catalog += f"  - Specialized: {len(specialized_agents)}\n"
    catalog += f"  - Workflow: {len(workflow_agents)}\n"
    catalog += f"  - Other: {len(other_agents)}\n"
    catalog += f"\n**Total Components**: {len(workflow_entries) + len(command_entries) + len(skill_entries) + len(agent_entries)}\n\n"

    # Write catalog
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    with open(catalog_path, "w", encoding="utf-8") as f:
        f.write(catalog)

    print(f"✅ Catalog generated: {catalog_path}")
    print("\nSummary:")
    print(f"  - Workflows: {len(workflow_entries)}")
    print(f"  - Commands: {len(command_entries)}")
    print(f"  - Skills: {len(skill_entries)}")
    print(f"  - Agents: {len(agent_entries)}")
    print(
        f"  - Total: {len(workflow_entries) + len(command_entries) + len(skill_entries) + len(agent_entries)}"
    )


if __name__ == "__main__":
    generate_catalog()
