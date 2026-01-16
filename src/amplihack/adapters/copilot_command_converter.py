"""Convert amplihack commands from Claude Code to Copilot CLI format.

Philosophy:
- Ruthless simplicity - single-pass conversion
- Zero-BS - every function works or doesn't exist
- Fail-fast - validate before converting
- Regeneratable - can rebuild .github/commands/ at any time

Public API (the "studs"):
    ConversionReport: Results of conversion operation
    CommandConversion: Single command conversion result
    convert_commands: Convert all commands
    convert_single_command: Convert one command
    validate_command: Validate command structure
    is_commands_synced: Check if commands are in sync
"""

import json
import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional


@dataclass
class CommandConversion:
    """Single command conversion result.

    Attributes:
        source_path: Original command path
        target_path: Converted command path
        command_name: Name of the command
        status: Conversion status
        reason: Optional reason for status
    """
    source_path: Path
    target_path: Path
    command_name: str
    status: Literal["success", "skipped", "failed"]
    reason: Optional[str] = None


@dataclass
class ConversionReport:
    """Results of command conversion operation.

    Attributes:
        total: Total commands processed
        succeeded: Number of successful conversions
        failed: Number of failed conversions
        skipped: Number of skipped commands
        conversions: List of all conversions
        errors: List of error messages
    """
    total: int
    succeeded: int
    failed: int
    skipped: int
    conversions: List[CommandConversion]
    errors: List[str]


def parse_command(command_path: Path) -> Dict[str, Any]:
    """Parse command markdown file with frontmatter.

    Args:
        command_path: Path to command file

    Returns:
        Dict with 'frontmatter' and 'body' keys

    Raises:
        ValueError: If command format is invalid

    Example:
        >>> cmd = parse_command(Path(".claude/commands/amplihack/ultrathink.md"))
        >>> cmd['frontmatter']['name']
        'amplihack:ultrathink'
    """
    content = command_path.read_text(encoding='utf-8')

    # Split frontmatter and body
    if not content.startswith('---'):
        raise ValueError(f"Command missing frontmatter: {command_path}")

    parts = content.split('---', 2)
    if len(parts) < 3:
        raise ValueError(f"Invalid frontmatter format: {command_path}")

    frontmatter_text = parts[1].strip()
    body = parts[2].strip()

    # Parse YAML frontmatter
    try:
        frontmatter = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in frontmatter: {e}")

    return {
        'frontmatter': frontmatter or {},
        'body': body
    }


def validate_command(command_path: Path) -> Optional[str]:
    """Validate command structure before conversion.

    Args:
        command_path: Path to command file

    Returns:
        None if valid, error message if invalid

    Example:
        >>> error = validate_command(Path(".claude/commands/amplihack/ultrathink.md"))
        >>> error is None
        True
    """
    try:
        cmd = parse_command(command_path)
        frontmatter = cmd['frontmatter']

        # Validate required fields exist
        if not frontmatter.get("name"):
            return f"Missing 'name' field in frontmatter"

        if not frontmatter.get("description"):
            return f"Missing 'description' field in frontmatter"

        # Validate command name format
        name = frontmatter["name"]
        if not all(c.isalnum() or c in [':', '-', '_'] for c in name):
            return f"Invalid command name '{name}': use only alphanumeric, colon, and hyphens"

        return None

    except Exception as e:
        return f"Validation error: {str(e)}"


def adapt_command_for_copilot(command: Dict[str, Any]) -> Dict[str, Any]:
    """Adapt command from Claude Code to Copilot CLI format.

    Conversions:
    - Replace @.claude/ references with @.github/
    - Replace @docs/ references with @ (Copilot root reference)
    - Preserve command structure and logic
    - Update invocation patterns for Copilot

    Args:
        command: Parsed command dict

    Returns:
        Adapted command dict

    Example:
        >>> cmd = parse_command(Path("ultrathink.md"))
        >>> adapted = adapt_command_for_copilot(cmd)
        >>> '@.github/' in adapted['body']
        True
    """
    frontmatter = command['frontmatter'].copy()
    body = command['body']

    # Replace path references
    body = body.replace('@.claude/', '@.github/')
    body = body.replace('@docs/', '@')

    # Update invocation patterns if present
    # Replace Skill(skill="...") with Copilot pattern
    body = body.replace(
        'Skill(skill="',
        'copilot --allow-all-tools -p "@.github/skills/'
    )
    body = body.replace(
        '")',
        '.md"'
    )

    # Replace Task(subagent_type="...") with Copilot agent pattern
    body = body.replace(
        'Task(subagent_type="',
        'copilot --allow-all-tools -p "@.github/agents/'
    )

    return {
        'frontmatter': frontmatter,
        'body': body
    }


def categorize_command(command_path: Path) -> str:
    """Determine command category from path.

    Args:
        command_path: Path to command file

    Returns:
        Category name

    Example:
        >>> categorize_command(Path(".claude/commands/amplihack/ultrathink.md"))
        'core'
        >>> categorize_command(Path(".claude/commands/ddd/1-plan.md"))
        'ddd'
    """
    # Extract directory name from path
    try:
        relative_path = command_path.relative_to(".claude/commands")
        parent = relative_path.parent.name

        if parent == "amplihack":
            return "core"
        elif parent == "ddd":
            return "ddd"
        else:
            return "custom"
    except ValueError:
        return "unknown"


def convert_single_command(
    command_path: Path,
    target_dir: Path,
    force: bool = False
) -> CommandConversion:
    """Convert single command file.

    Args:
        command_path: Path to command file
        target_dir: Target directory for converted command
        force: Overwrite existing files

    Returns:
        CommandConversion result

    Example:
        >>> result = convert_single_command(
        ...     Path(".claude/commands/amplihack/ultrathink.md"),
        ...     Path(".github/commands")
        ... )
        >>> result.status
        'success'
    """
    command_name = command_path.stem

    try:
        # Parse command
        cmd = parse_command(command_path)

        # Adapt for Copilot
        adapted = adapt_command_for_copilot(cmd)

        # Determine target path (preserve directory structure)
        try:
            relative_path = command_path.relative_to(".claude/commands")
        except ValueError:
            # If not under .claude/commands/, use filename only
            relative_path = Path(command_path.name)

        target_path = target_dir / relative_path

        # Check if target exists
        if target_path.exists() and not force:
            return CommandConversion(
                source_path=command_path,
                target_path=target_path,
                command_name=command_name,
                status="skipped",
                reason="Target exists (use --force to overwrite)"
            )

        # Create target directory
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Write converted command
        _write_command(adapted, target_path)

        return CommandConversion(
            source_path=command_path,
            target_path=target_path,
            command_name=command_name,
            status="success"
        )

    except Exception as e:
        return CommandConversion(
            source_path=command_path,
            target_path=Path(),  # Empty path on failure
            command_name=command_name,
            status="failed",
            reason=str(e)
        )


def _write_command(command: Dict[str, Any], target_path: Path) -> None:
    """Write adapted command to file.

    Args:
        command: Adapted command dict
        target_path: Target file path
    """
    # Reconstruct markdown with frontmatter
    frontmatter_yaml = yaml.dump(
        command['frontmatter'],
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False
    )

    content = f"---\n{frontmatter_yaml}---\n\n{command['body']}"

    target_path.write_text(content, encoding='utf-8')


def convert_commands(
    source_dir: Path = Path(".claude/commands"),
    target_dir: Path = Path(".github/commands"),
    force: bool = False
) -> ConversionReport:
    """Convert all commands from source to target directory.

    Process:
    1. Prerequisite validation
    2. Command discovery
    3. Command validation (fail-fast)
    4. Command conversion
    5. Registry generation
    6. Report generation

    Args:
        source_dir: Source directory with Claude commands
        target_dir: Target directory for Copilot commands
        force: Overwrite existing files

    Returns:
        ConversionReport with results

    Raises:
        FileNotFoundError: If source directory doesn't exist
        PermissionError: If cannot write to target directory

    Example:
        >>> report = convert_commands()
        >>> report.succeeded
        32
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

    # Step 2: Command Discovery
    command_files = list(source_dir.rglob("*.md"))

    if not command_files:
        return ConversionReport(
            total=0,
            succeeded=0,
            failed=0,
            skipped=0,
            conversions=[],
            errors=["No command files found in source directory"]
        )

    # Step 3: Command Validation (fail-fast)
    validation_errors = []
    for command_path in command_files:
        error = validate_command(command_path)
        if error:
            validation_errors.append(f"{command_path}: {error}")

    if validation_errors:
        # Report all validation errors at once
        error_msg = "Command validation failed:\n" + "\n".join(validation_errors)
        errors.append(error_msg)
        return ConversionReport(
            total=len(command_files),
            succeeded=0,
            failed=len(command_files),
            skipped=0,
            conversions=[],
            errors=errors
        )

    # Step 4: Command Conversion
    for command_path in command_files:
        conversion = convert_single_command(command_path, target_dir, force)
        conversions.append(conversion)

        if conversion.status == "failed":
            errors.append(f"{command_path}: {conversion.reason}")

    # Step 5: Registry Generation
    registry_entries = []
    for conversion in conversions:
        if conversion.status == "success":
            try:
                cmd = parse_command(conversion.source_path)
                category = categorize_command(conversion.source_path)

                entry = {
                    "name": cmd['frontmatter']['name'],
                    "description": cmd['frontmatter'].get('description', ''),
                    "category": category,
                    "source_path": str(conversion.source_path),
                    "target_path": str(conversion.target_path),
                    "triggers": cmd['frontmatter'].get('triggers', []),
                    "version": cmd['frontmatter'].get('version', '1.0.0')
                }
                registry_entries.append(entry)
            except Exception as e:
                errors.append(f"Failed to create registry entry for {conversion.source_path}: {str(e)}")

    # Write registry
    if registry_entries:
        try:
            registry = {
                "version": "1.0.0",
                "commands": registry_entries,
                "metadata": {
                    "source_dir": str(source_dir),
                    "target_dir": str(target_dir),
                    "total_commands": len(registry_entries)
                }
            }
            registry_path = target_dir / "COMMANDS_REGISTRY.json"
            registry_path.write_text(
                json.dumps(registry, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
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


def is_commands_synced(
    source_dir: Path = Path(".claude/commands"),
    target_dir: Path = Path(".github/commands")
) -> bool:
    """Check if .github/commands/ is in sync with .claude/commands/.

    Args:
        source_dir: Source directory
        target_dir: Target directory

    Returns:
        True if in sync, False if outdated or never synced

    Example:
        >>> is_commands_synced()
        True
    """
    registry_path = target_dir / "COMMANDS_REGISTRY.json"

    if not registry_path.exists():
        return False  # Never synced

    registry_mtime = registry_path.stat().st_mtime

    # Check if any source command is newer than registry
    for command_path in source_dir.rglob("*.md"):
        if command_path.stat().st_mtime > registry_mtime:
            return False  # Source newer than target

    return True  # In sync


__all__ = [
    "ConversionReport",
    "CommandConversion",
    "convert_commands",
    "convert_single_command",
    "validate_command",
    "is_commands_synced",
]
