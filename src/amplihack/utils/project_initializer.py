"""Smart PROJECT.md initialization for user projects.

Automatically detects when PROJECT.md needs initialization or regeneration
and creates appropriate project-specific content.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ProjectState(Enum):
    """State of PROJECT.md file."""

    MISSING = "missing"
    DESCRIBES_AMPLIHACK = "describes_amplihack"
    VALID_USER_CONTENT = "valid_user_content"


class InitMode(Enum):
    """Initialization mode."""

    AUTO = "auto"  # Initialize if missing, offer regeneration if anti-pattern
    FORCE = "force"  # Always regenerate
    CHECK = "check"  # Only report state, don't modify


class GenerationMethod(Enum):
    """Method used to generate PROJECT.md."""

    SDK = "sdk"
    TEMPLATE = "template"
    NONE = "none"


class ActionTaken(Enum):
    """Action taken during initialization."""

    INITIALIZED = "initialized"
    REGENERATED = "regenerated"
    SKIPPED = "skipped"
    OFFERED = "offered"


@dataclass
class InitializationResult:
    """Result of PROJECT.md initialization.

    Attributes:
        action_taken: What action was performed
        state: Current state of PROJECT.md
        method: Generation method used (if any)
        message: Human-readable description
        success: True if operation succeeded
    """

    action_taken: ActionTaken
    state: ProjectState
    method: GenerationMethod
    message: str
    success: bool = True


# Indicators that PROJECT.md describes amplihack instead of user's project
AMPLIHACK_INDICATORS = [
    "Microsoft Hackathon 2025",
    "Agentic Coding Framework",
    "Building the tools that build the future",
    "AI agents to accelerate software development",
]


# Template for PROJECT.md (from PR #1278)
PROJECT_MD_TEMPLATE = """# Project Context

**This file provides project-specific context to Claude Code agents.**

When amplihack is installed in your project, customize this file to describe YOUR project. This helps agents understand what you're building and provide better assistance.

## Quick Start

Replace the sections below with information about your project.

---

## Project: {project_name}

## Overview

{project_description}

## Architecture

### Key Components

- **Component 1**: [Purpose and responsibilities]
- **Component 2**: [Purpose and responsibilities]
- **Component 3**: [Purpose and responsibilities]

### Technology Stack

{tech_stack}

## Development Guidelines

### Code Organization

[How is your code organized? What are the main directories?]

### Key Patterns

[What architectural patterns or conventions does your project follow?]

### Testing Strategy

[How do you test? Unit tests, integration tests, E2E?]

## Domain Knowledge

### Business Context

[What problem does this project solve? Who are the users?]

### Key Terminology

[Important domain-specific terms that agents should understand]

## Common Tasks

### Development Workflow

[How do developers typically work on this project?]

### Deployment Process

[How is the project deployed?]

## Important Notes

[Any special considerations, gotchas, or critical information]

---

## About This File

This file is installed by amplihack to provide project-specific context to AI agents.

**For more about amplihack itself**, see PROJECT_AMPLIHACK.md in this directory.

**Tip**: Keep this file updated as your project evolves. Accurate context leads to better AI assistance.
"""


def detect_project_md_state(project_root: Path) -> tuple[ProjectState, str]:
    """Detect current state of PROJECT.md.

    Args:
        project_root: Root directory of user's project

    Returns:
        Tuple of (state, reason)
    """
    project_md = project_root / ".claude" / "context" / "PROJECT.md"

    # Check if exists
    if not project_md.exists():
        return ProjectState.MISSING, "PROJECT.md not found"

    # Read content
    try:
        content = project_md.read_text()
    except Exception as e:
        logger.warning(f"Could not read PROJECT.md: {e}")
        return ProjectState.VALID_USER_CONTENT, f"Unreadable (assuming valid): {e}"

    # Check for amplihack indicators
    indicator_count = sum(
        1 for indicator in AMPLIHACK_INDICATORS if indicator.lower() in content.lower()
    )

    # Threshold: 2+ indicators = describes amplihack
    if indicator_count >= 2:
        return ProjectState.DESCRIBES_AMPLIHACK, f"Contains {indicator_count} amplihack indicators"

    return ProjectState.VALID_USER_CONTENT, "User content detected"


def analyze_project_structure(project_root: Path) -> Dict[str, Any]:
    """Analyze project structure to gather context.

    Args:
        project_root: Root directory of project

    Returns:
        Dictionary with project information
    """
    info = {
        "name": project_root.name,
        "has_readme": (project_root / "README.md").exists(),
        "languages": [],
        "package_files": {},
    }

    # Detect languages
    if list(project_root.rglob("*.py"))[:1]:
        info["languages"].append("Python")
    if list(project_root.rglob("*.js"))[:1] or list(project_root.rglob("*.ts"))[:1]:
        info["languages"].append("JavaScript/TypeScript")
    if list(project_root.rglob("*.rs"))[:1]:
        info["languages"].append("Rust")
    if list(project_root.rglob("*.go"))[:1]:
        info["languages"].append("Go")

    # Read package metadata
    pyproject = project_root / "pyproject.toml"
    if pyproject.exists():
        try:
            info["package_files"]["pyproject.toml"] = pyproject.read_text()[:500]
        except Exception:
            pass

    package_json = project_root / "package.json"
    if package_json.exists():
        try:
            info["package_files"]["package.json"] = package_json.read_text()[:500]
        except Exception:
            pass

    readme = project_root / "README.md"
    if readme.exists():
        try:
            info["readme_preview"] = readme.read_text()[:500]
        except Exception:
            pass

    return info


def generate_from_template(project_info: Dict[str, Any]) -> str:
    """Generate PROJECT.md from template.

    Args:
        project_info: Project information from analyze_project_structure

    Returns:
        Generated PROJECT.md content
    """
    # Extract project name
    project_name = project_info.get("name", "[Your Project Name]")

    # Generate description
    if "readme_preview" in project_info:
        # Try to extract first paragraph from README
        lines = project_info["readme_preview"].split("\n")
        desc_lines = []
        for line in lines[1:]:  # Skip title
            line = line.strip()
            if line and not line.startswith("#"):
                desc_lines.append(line)
                if len(desc_lines) >= 2:
                    break
        project_description = (
            " ".join(desc_lines) if desc_lines else "[Brief description of what your project does]"
        )
    else:
        project_description = "[Brief description of what your project does]"

    # Generate tech stack
    languages = project_info.get("languages", [])
    if languages:
        tech_stack = "\n".join(f"- **Language**: {lang}" for lang in languages)
        tech_stack += "\n- **Framework**: [Main framework if applicable]"
        tech_stack += "\n- **Database**: [Database system if applicable]"
    else:
        tech_stack = """- **Language**: [Primary language(s)]
- **Framework**: [Main framework if applicable]
- **Database**: [Database system if applicable]"""

    # Fill template
    content = PROJECT_MD_TEMPLATE.format(
        project_name=project_name, project_description=project_description, tech_stack=tech_stack
    )

    return content


def initialize_project_md(
    project_root: Path, mode: InitMode = InitMode.AUTO
) -> InitializationResult:
    """Initialize or regenerate PROJECT.md for user's project.

    Args:
        project_root: Root directory of project
        mode: Initialization mode

    Returns:
        Result of initialization attempt
    """
    # Detect current state
    state, reason = detect_project_md_state(project_root)

    logger.debug(f"PROJECT.md state: {state.value}, reason: {reason}")

    # Check mode
    if mode == InitMode.CHECK:
        return InitializationResult(
            action_taken=ActionTaken.SKIPPED,
            state=state,
            method=GenerationMethod.NONE,
            message=f"Check mode: {state.value} - {reason}",
        )

    # Handle based on state
    project_md_path = project_root / ".claude" / "context" / "PROJECT.md"

    if state == ProjectState.VALID_USER_CONTENT and mode != InitMode.FORCE:
        return InitializationResult(
            action_taken=ActionTaken.SKIPPED,
            state=state,
            method=GenerationMethod.NONE,
            message="Valid user content detected, skipping initialization",
        )

    if state == ProjectState.DESCRIBES_AMPLIHACK and mode == InitMode.AUTO:
        return InitializationResult(
            action_taken=ActionTaken.OFFERED,
            state=state,
            method=GenerationMethod.NONE,
            message="PROJECT.md describes amplihack. Run 'amplihack init-project-md --force' to regenerate",
        )

    # Need to initialize or regenerate
    try:
        # Analyze project
        project_info = analyze_project_structure(project_root)

        # Try SDK generation first (future phase)
        # For Phase 1 MVP, go straight to template
        content = generate_from_template(project_info)
        method = GenerationMethod.TEMPLATE

        # Create backup if exists
        if project_md_path.exists():
            backup_path = project_md_path.with_suffix(".md.bak")
            project_md_path.rename(backup_path)
            logger.info(f"Created backup: {backup_path}")

        # Ensure directory exists
        project_md_path.parent.mkdir(parents=True, exist_ok=True)

        # Write new content
        project_md_path.write_text(content)

        action = (
            ActionTaken.REGENERATED
            if state == ProjectState.DESCRIBES_AMPLIHACK
            else ActionTaken.INITIALIZED
        )

        return InitializationResult(
            action_taken=action,
            state=state,
            method=method,
            message=f"PROJECT.md {action.value} using {method.value}",
            success=True,
        )

    except Exception as e:
        logger.error(f"Failed to initialize PROJECT.md: {e}")
        return InitializationResult(
            action_taken=ActionTaken.SKIPPED,
            state=state,
            method=GenerationMethod.NONE,
            message=f"Initialization failed: {e}",
            success=False,
        )
