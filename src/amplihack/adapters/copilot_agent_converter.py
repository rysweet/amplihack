"""Convert amplihack agents from Claude Code to Copilot CLI format.

Philosophy:
- Ruthless simplicity - single-pass conversion
- Zero-BS - every function works or doesn't exist
- Fail-fast - validate before converting
- Regeneratable - can rebuild .github/agents/ at any time

Public API (the "studs"):
    ConversionReport: Results of conversion operation
    AgentConversion: Single agent conversion result
    convert_agents: Convert all agents
    convert_single_agent: Convert one agent
    validate_agent: Validate agent structure
    is_agents_synced: Check if agents are in sync
"""

import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import List, Literal, Optional

from .agent_parser import parse_agent, AgentDocument
from .agent_adapter import adapt_agent_for_copilot
from .agent_registry import (
    AgentRegistryEntry,
    categorize_agent,
    create_registry,
    write_registry,
)


@dataclass
class AgentConversion:
    """Single agent conversion result.

    Attributes:
        source_path: Original agent path
        target_path: Converted agent path
        agent_name: Name of the agent
        status: Conversion status
        reason: Optional reason for status
    """
    source_path: Path
    target_path: Path
    agent_name: str
    status: Literal["success", "skipped", "failed"]
    reason: Optional[str] = None


@dataclass
class ConversionReport:
    """Results of agent conversion operation.

    Attributes:
        total: Total agents processed
        succeeded: Number of successful conversions
        failed: Number of failed conversions
        skipped: Number of skipped agents
        conversions: List of all conversions
        errors: List of error messages
    """
    total: int
    succeeded: int
    failed: int
    skipped: int
    conversions: List[AgentConversion]
    errors: List[str]


def validate_agent(agent_path: Path) -> Optional[str]:
    """Validate agent structure before conversion.

    Args:
        agent_path: Path to agent file

    Returns:
        None if valid, error message if invalid

    Example:
        >>> error = validate_agent(Path(".claude/agents/core/architect.md"))
        >>> error is None
        True
    """
    try:
        agent = parse_agent(agent_path)

        # Validate required fields exist
        if not agent.frontmatter.get("name"):
            return f"Missing 'name' field in frontmatter"

        if not agent.frontmatter.get("description"):
            return f"Missing 'description' field in frontmatter"

        # Validate agent name format (alphanumeric + hyphen only)
        name = agent.frontmatter["name"]
        if not all(c.isalnum() or c in ['-', '_'] for c in name):
            return f"Invalid agent name '{name}': use only alphanumeric and hyphens"

        return None

    except Exception as e:
        return f"Validation error: {str(e)}"


def convert_single_agent(
    agent_path: Path,
    target_dir: Path,
    force: bool = False
) -> AgentConversion:
    """Convert single agent file.

    Args:
        agent_path: Path to agent file
        target_dir: Target directory for converted agent
        force: Overwrite existing files

    Returns:
        AgentConversion result

    Example:
        >>> result = convert_single_agent(
        ...     Path(".claude/agents/core/architect.md"),
        ...     Path(".github/agents")
        ... )
        >>> result.status
        'success'
    """
    agent_name = agent_path.stem

    try:
        # Parse agent
        agent = parse_agent(agent_path)

        # Adapt for Copilot
        adapted = adapt_agent_for_copilot(agent)

        # Determine target path (preserve directory structure)
        # Extract relative path from .claude/agents/
        try:
            relative_path = agent_path.relative_to(".claude/agents")
        except ValueError:
            # If not under .claude/agents/, use filename only
            relative_path = Path(agent_path.name)

        target_path = target_dir / relative_path

        # Check if target exists
        if target_path.exists() and not force:
            return AgentConversion(
                source_path=agent_path,
                target_path=target_path,
                agent_name=agent_name,
                status="skipped",
                reason="Target exists (use --force to overwrite)"
            )

        # Create target directory
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Write converted agent
        _write_agent(adapted, target_path)

        return AgentConversion(
            source_path=agent_path,
            target_path=target_path,
            agent_name=agent_name,
            status="success"
        )

    except Exception as e:
        return AgentConversion(
            source_path=agent_path,
            target_path=Path(),  # Empty path on failure
            agent_name=agent_name,
            status="failed",
            reason=str(e)
        )


def _write_agent(agent: AgentDocument, target_path: Path) -> None:
    """Write adapted agent to file.

    Args:
        agent: Adapted agent document
        target_path: Target file path
    """
    # Reconstruct markdown with frontmatter
    frontmatter_yaml = yaml.dump(
        agent.frontmatter,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False
    )

    content = f"---\n{frontmatter_yaml}---\n\n{agent.body}"

    target_path.write_text(content, encoding='utf-8')


def convert_agents(
    source_dir: Path = Path(".claude/agents"),
    target_dir: Path = Path(".github/agents"),
    force: bool = False
) -> ConversionReport:
    """Convert all agents from source to target directory.

    Process:
    1. Prerequisite validation
    2. Agent discovery
    3. Agent validation (fail-fast)
    4. Agent conversion
    5. Registry generation
    6. Report generation

    Args:
        source_dir: Source directory with Claude agents
        target_dir: Target directory for Copilot agents
        force: Overwrite existing files

    Returns:
        ConversionReport with results

    Raises:
        FileNotFoundError: If source directory doesn't exist
        PermissionError: If cannot write to target directory

    Example:
        >>> report = convert_agents()
        >>> report.succeeded
        37
    """
    errors = []
    conversions = []

    # Step 1: Prerequisite Validation
    if not source_dir.exists():
        raise FileNotFoundError(
            f"Source directory not found: {source_dir}\n"
            f"Fix: Ensure you're in an amplihack project directory\n"
            f"     Run 'amplihack init' to create project structure"
        )

    # Check write permissions
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        raise PermissionError(
            f"Cannot write to target directory: {target_dir}\n"
            f"Fix: Check directory permissions\n"
            f"     chmod +w {target_dir.parent}"
        )

    # Step 2: Agent Discovery
    agent_files = list(source_dir.rglob("*.md"))
    # Filter out README files
    agent_files = [f for f in agent_files if f.name.upper() != "README.MD"]

    if not agent_files:
        return ConversionReport(
            total=0,
            succeeded=0,
            failed=0,
            skipped=0,
            conversions=[],
            errors=["No agent files found in source directory"]
        )

    # Step 3: Agent Validation (fail-fast)
    validation_errors = []
    for agent_path in agent_files:
        error = validate_agent(agent_path)
        if error:
            validation_errors.append(f"{agent_path}: {error}")

    if validation_errors:
        # Report all validation errors at once
        error_msg = "Agent validation failed:\n" + "\n".join(validation_errors)
        errors.append(error_msg)
        return ConversionReport(
            total=len(agent_files),
            succeeded=0,
            failed=len(agent_files),
            skipped=0,
            conversions=[],
            errors=errors
        )

    # Step 4: Agent Conversion
    for agent_path in agent_files:
        conversion = convert_single_agent(agent_path, target_dir, force)
        conversions.append(conversion)

        if conversion.status == "failed":
            errors.append(f"{agent_path}: {conversion.reason}")

    # Step 5: Registry Generation
    registry_entries = []
    for conversion in conversions:
        if conversion.status == "success":
            # Read converted agent to get metadata
            try:
                agent = parse_agent(conversion.source_path)
                category = categorize_agent(conversion.source_path)

                entry = AgentRegistryEntry(
                    name=agent.frontmatter["name"],
                    description=agent.frontmatter.get("description", ""),
                    category=category,
                    source_path=str(conversion.source_path),
                    target_path=str(conversion.target_path),
                    triggers=agent.frontmatter.get("triggers", [agent.frontmatter["name"]]),
                    version=agent.frontmatter.get("version", "1.0.0")
                )
                registry_entries.append(entry)
            except Exception as e:
                errors.append(f"Failed to create registry entry for {conversion.source_path}: {str(e)}")

    # Write registry
    if registry_entries:
        try:
            registry = create_registry(
                registry_entries,
                source_dir=str(source_dir),
                target_dir=str(target_dir)
            )
            write_registry(registry, target_dir / "REGISTRY.json")
        except Exception as e:
            errors.append(f"Failed to write registry: {str(e)}")

    # Step 6: Report Generation
    succeeded = sum(1 for c in conversions if c.status == "success")
    failed = sum(1 for c in conversions if c.status == "failed")
    skipped = sum(1 for c in conversions if c.status == "skipped")

    return ConversionReport(
        total=len(conversions),
        succeeded=succeeded,
        failed=failed,
        skipped=skipped,
        conversions=conversions,
        errors=errors
    )


def is_agents_synced(
    source_dir: Path = Path(".claude/agents"),
    target_dir: Path = Path(".github/agents")
) -> bool:
    """Check if .github/agents/ is in sync with .claude/agents/.

    Args:
        source_dir: Source directory
        target_dir: Target directory

    Returns:
        True if in sync, False if outdated or never synced

    Example:
        >>> is_agents_synced()
        True
    """
    registry_path = target_dir / "REGISTRY.json"

    if not registry_path.exists():
        return False  # Never synced

    registry_mtime = registry_path.stat().st_mtime

    # Check if any source agent is newer than registry
    for agent_path in source_dir.rglob("*.md"):
        if agent_path.name.upper() == "README.MD":
            continue
        if agent_path.stat().st_mtime > registry_mtime:
            return False  # Source newer than target

    return True  # In sync


__all__ = [
    "ConversionReport",
    "AgentConversion",
    "convert_agents",
    "convert_single_agent",
    "validate_agent",
    "is_agents_synced",
]
