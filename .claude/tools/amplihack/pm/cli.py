"""PM CLI commands with user interaction and formatting.

This module implements user-facing CLI commands for PM Architect,
handling interactive prompts, input validation, and terminal output formatting.

Public API:
    - cmd_init: Initialize PM in current project
    - cmd_add: Add item to backlog
    - cmd_start: Start workstream for backlog item
    - cmd_status: Show project or workstream status

Philosophy:
    - Simple, direct commands
    - Clear error messages
    - Beautiful terminal output
    - Ruthless simplicity
"""

from pathlib import Path
from typing import Optional, List

from .state import PMStateManager, PMConfig, BacklogItem, WorkstreamState
from .workstream import WorkstreamManager
from .intelligence import RecommendationEngine, Recommendation, RichDelegationPackage


__all__ = [
    "cmd_init",
    "cmd_add",
    "cmd_start",
    "cmd_status",
    "cmd_suggest",
    "cmd_prepare",
]


# =============================================================================
# CLI Commands
# =============================================================================


def cmd_init(project_root: Optional[Path] = None) -> int:
    """Implement /pm:init command.

    Interactive initialization:
    1. Check if already initialized
    2. Ask user questions (via simple prompts)
    3. Initialize PM state
    4. Print success message

    Args:
        project_root: Project directory (default: cwd)

    Returns:
        Exit code (0=success, 1=error)
    """
    if project_root is None:
        project_root = Path.cwd()

    manager = PMStateManager(project_root)

    try:
        # Check if already initialized
        if manager.is_initialized():
            print(f"❌ PM already initialized at {manager.pm_dir}")
            print("   Use /pm:status to view current state")
            return 1

        print("🚀 PM Architect Initialization\n")

        # Get project name (default to directory name)
        default_name = project_root.name
        project_name = input(f"Project name [{default_name}]: ").strip() or default_name

        # Get project type
        print("\nProject type:")
        print("  1. cli-tool (Command-line application)")
        print("  2. web-service (API or web app)")
        print("  3. library (Reusable package)")
        print("  4. other (Custom project type)")
        type_choice = input("Select [1]: ").strip() or "1"
        type_map = {
            "1": "cli-tool",
            "2": "web-service",
            "3": "library",
            "4": "other",
        }
        project_type = type_map.get(type_choice, "cli-tool")

        # Get primary goals
        print("\nPrimary goals (one per line, empty line to finish):")
        goals = []
        while True:
            goal = input(f"  Goal {len(goals) + 1}: ").strip()
            if not goal:
                break
            goals.append(goal)

        if not goals:
            goals = ["Complete project successfully"]

        # Get quality bar
        print("\nQuality bar:")
        print("  1. strict (High standards, thorough review)")
        print("  2. balanced (Good quality, reasonable speed)")
        print("  3. relaxed (Move fast, iterate quickly)")
        quality_choice = input("Select [2]: ").strip() or "2"
        quality_map = {"1": "strict", "2": "balanced", "3": "relaxed"}
        quality_bar = quality_map.get(quality_choice, "balanced")

        # Initialize
        manager.initialize(
            project_name=project_name,
            project_type=project_type,
            primary_goals=goals,
            quality_bar=quality_bar,
        )

        # Print success
        print("\n" + "=" * 60)
        print(f"✅ PM INITIALIZED: {project_name}")
        print("=" * 60)
        print()
        print(f"Configuration: {manager.pm_dir / 'config.yaml'}")
        print(f"Roadmap: {manager.pm_dir / 'roadmap.md'}")
        print()
        print('Next: /pm:add "First item" to add work')

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


def cmd_add(
    title: str,
    priority: str = "MEDIUM",
    description: str = "",
    estimated_hours: int = 4,
    tags: Optional[List[str]] = None,
    project_root: Optional[Path] = None,
) -> int:
    """Implement /pm:add command.

    Process:
    1. Validate PM initialized
    2. Validate inputs
    3. Add backlog item
    4. Print success with ID

    Args:
        title: Item title (required)
        priority: HIGH, MEDIUM, LOW
        description: Detailed description
        estimated_hours: Estimated hours
        tags: Optional tags
        project_root: Project directory

    Returns:
        Exit code
    """
    if project_root is None:
        project_root = Path.cwd()

    manager = PMStateManager(project_root)

    try:
        # Validate PM initialized
        validate_initialized(manager)

        # Validate inputs
        if not title.strip():
            print("❌ Error: Title cannot be empty")
            return 1

        if priority not in ["HIGH", "MEDIUM", "LOW"]:
            print(f"❌ Error: Priority must be HIGH, MEDIUM, or LOW (got: {priority})")
            return 1

        # Add backlog item
        item = manager.add_backlog_item(
            title=title,
            priority=priority,
            description=description,
            estimated_hours=estimated_hours,
            tags=tags,
        )

        # Print success
        print(f"✅ Added {item.id}: {item.title} [{item.priority}]")
        print(f"   Edit details: {manager.pm_dir / 'backlog' / 'items.yaml'}")

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


def cmd_start(
    backlog_id: str,
    agent: str = "builder",
    timeout: Optional[int] = None,
    project_root: Optional[Path] = None,
) -> int:
    """Implement /pm:start command.

    Process:
    1. Validate PM initialized
    2. Validate no active workstream
    3. Validate backlog item exists
    4. Confirm with user
    5. Start workstream
    6. Print status

    Args:
        backlog_id: Backlog item ID (BL-001)
        agent: Agent role
        timeout: Process timeout
        project_root: Project directory

    Returns:
        Exit code
    """
    if project_root is None:
        project_root = Path.cwd()

    state_manager = PMStateManager(project_root)
    ws_manager = WorkstreamManager(
        state_manager=state_manager,
        project_root=project_root,
    )

    try:
        # Validate PM initialized
        validate_initialized(state_manager)

        # Validate no active workstream
        validate_no_active_workstream(state_manager)

        # Validate backlog item exists
        item = state_manager.get_backlog_item(backlog_id)
        if not item:
            print(f"❌ Error: Backlog item {backlog_id} not found")
            print("   Use /pm:status to see available items")
            return 1

        # Confirm with user
        print("\nPM: Preparing delegation package...")
        print(f"    Title: {item.title}")
        print(f"    Priority: {item.priority}")
        print(f"    Agent: {agent}")
        print(f"    Estimated: {item.estimated_hours} hours")
        print()
        confirm = input("Start workstream? [y/N]: ").strip().lower()
        if confirm != "y":
            print("Cancelled.")
            return 0

        # Start workstream
        workstream = ws_manager.start_workstream(
            backlog_id=backlog_id,
            agent=agent,
            timeout=timeout,
        )

        # Print success
        print(f"\n✅ Workstream {workstream.id} started")
        print(f"   Title: {workstream.title}")
        print(f"   Agent: {workstream.agent}")
        print(f"   Estimated: {item.estimated_hours} hours")
        print()
        print(f"Monitor: /pm:status {workstream.id}")

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


def cmd_status(
    ws_id: Optional[str] = None,
    project_root: Optional[Path] = None,
) -> int:
    """Implement /pm:status command.

    Two modes:
    - No args: Project overview (config, active workstream, backlog)
    - With ws_id: Detailed workstream status

    Args:
        ws_id: Optional workstream ID
        project_root: Project directory

    Returns:
        Exit code
    """
    if project_root is None:
        project_root = Path.cwd()

    state_manager = PMStateManager(project_root)

    try:
        # Validate PM initialized
        validate_initialized(state_manager)

        if ws_id:
            # Workstream details mode
            ws_manager = WorkstreamManager(
                state_manager=state_manager,
                project_root=project_root,
            )
            status = ws_manager.get_workstream_status(ws_id)
            print(format_workstream_details(status["workstream"], status))
        else:
            # Project overview mode
            config = state_manager.get_config()
            active_ws = state_manager.get_active_workstream()
            backlog = state_manager.get_backlog_items(status="READY")
            print(format_project_overview(config, active_ws, backlog))

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


def cmd_suggest(
    project_root: Optional[Path] = None,
    max_recommendations: int = 3,
) -> int:
    """Implement /pm:suggest command (Phase 2).

    Analyze all backlog items and provide smart recommendations for
    what to work on next, with rationale and confidence scores.

    Process:
    1. Validate PM initialized
    2. Run recommendation engine
    3. Display top N recommendations with details
    4. Show scoring breakdown

    Args:
        project_root: Project directory
        max_recommendations: Number of recommendations (default: 3)

    Returns:
        Exit code
    """
    if project_root is None:
        project_root = Path.cwd()

    state_manager = PMStateManager(project_root)

    try:
        # Validate PM initialized
        validate_initialized(state_manager)

        # Get recommendations
        engine = RecommendationEngine(state_manager, project_root)
        recommendations = engine.generate_recommendations(max_recommendations=max_recommendations)

        if not recommendations:
            print("📋 No backlog items ready for work")
            print("   Add items with /pm:add or check dependencies")
            return 0

        # Display recommendations
        print("=" * 60)
        print("🤖 PM ARCHITECT RECOMMENDATIONS")
        print("=" * 60)
        print()

        for rec in recommendations:
            print(format_recommendation(rec))
            print()

        print("=" * 60)
        print("💡 TIP: Use /pm:prepare <id> to create rich delegation package")
        print()

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


def cmd_prepare(
    backlog_id: str,
    agent: str = "builder",
    project_root: Optional[Path] = None,
) -> int:
    """Implement /pm:prepare command (Phase 2).

    Create rich delegation package with AI-generated context including:
    - Relevant files to examine
    - Similar patterns in codebase
    - Comprehensive test requirements
    - Architectural notes

    Process:
    1. Validate PM initialized
    2. Validate backlog item exists
    3. Run AI analysis
    4. Generate rich delegation package
    5. Display package details

    Args:
        backlog_id: Backlog item ID (BL-001)
        agent: Agent role (builder, reviewer, tester)
        project_root: Project directory

    Returns:
        Exit code
    """
    if project_root is None:
        project_root = Path.cwd()

    state_manager = PMStateManager(project_root)

    try:
        # Validate PM initialized
        validate_initialized(state_manager)

        # Validate backlog item exists
        item = state_manager.get_backlog_item(backlog_id)
        if not item:
            print(f"❌ Error: Backlog item {backlog_id} not found")
            print("   Use /pm:status to see available items")
            return 1

        print("\n🤖 Analyzing backlog item and codebase...")
        print("   This may take a moment...\n")

        # Generate rich delegation package
        engine = RecommendationEngine(state_manager, project_root)
        package = engine.create_rich_delegation_package(backlog_id, agent)

        # Display package
        print("=" * 60)
        print(f"📦 RICH DELEGATION PACKAGE: {backlog_id}")
        print("=" * 60)
        print()
        print(format_rich_delegation_package(package))
        print()
        print("=" * 60)
        print(f"💡 TIP: Use /pm:start {backlog_id} to begin work with this package")
        print()

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


# =============================================================================
# Formatting Helpers
# =============================================================================


def format_project_overview(
    config: PMConfig,
    active_ws: Optional[WorkstreamState],
    backlog: List[BacklogItem],
) -> str:
    """Format project overview for terminal output.

    Returns formatted string with:
    - Project header
    - Active workstream (if any)
    - Backlog summary
    - Health indicator
    """
    output = []
    output.append("=" * 60)
    output.append(f"PROJECT: {config.project_name} [{config.project_type}]")
    output.append("=" * 60)
    output.append("")

    # Active workstreams
    if active_ws:
        output.append("⚡ ACTIVE WORKSTREAMS (1):")
        output.append(f"  • {active_ws.id}: {active_ws.title} [{active_ws.agent}]")
        output.append(f"    Status: {active_ws.status} ({active_ws.elapsed_minutes} min elapsed)")
        output.append("")
    else:
        output.append("⚡ ACTIVE WORKSTREAMS: None")
        output.append("")

    # Backlog
    output.append(f"📋 BACKLOG ({len(backlog)} items ready):")
    for item in backlog[:5]:  # Show first 5
        output.append(f"  • {item.id}: {item.title} [{item.priority}] - {item.status}")
    if len(backlog) > 5:
        output.append(f"  ... and {len(backlog) - 5} more")
    if not backlog:
        output.append("  (empty)")
    output.append("")

    # Project health
    health = "🟢 HEALTHY"
    if active_ws and active_ws.status == "FAILED":
        health = "🔴 ATTENTION NEEDED"
    elif len(backlog) == 0 and not active_ws:
        health = "🟡 IDLE"

    output.append(f"📊 PROJECT HEALTH: {health}")
    output.append(f"   Quality Bar: {config.quality_bar}")
    output.append(f"   Active: {1 if active_ws else 0} workstream")

    return "\n".join(output)


def format_workstream_details(
    workstream: WorkstreamState,
    status: dict,
) -> str:
    """Format workstream details for terminal output."""
    output = []
    output.append("=" * 60)
    output.append(f"WORKSTREAM: {workstream.id}")
    output.append("=" * 60)
    output.append("")
    output.append(f"Title: {workstream.title}")
    output.append(f"Backlog: {workstream.backlog_id}")
    output.append(f"Status: {workstream.status}")
    output.append(f"Agent: {workstream.agent}")
    output.append(f"Started: {workstream.started_at}")
    output.append(f"Elapsed: {status['elapsed_time']}")
    output.append(f"Progress: {status['progress']}")

    if workstream.completed_at:
        output.append(f"Completed: {workstream.completed_at}")

    if workstream.progress_notes:
        output.append("")
        output.append("Progress Notes:")
        for note in workstream.progress_notes:
            output.append(f"  • {note}")

    if workstream.process_id:
        output.append("")
        output.append(f"Process ID: {workstream.process_id}")
        output.append(f"Log: .pm/logs/{workstream.process_id}.log")

    return "\n".join(output)


def format_backlog_item(item: BacklogItem, verbose: bool = False) -> str:
    """Format single backlog item for display."""
    output = f"{item.id}: {item.title} [{item.priority}] - {item.status}"
    if verbose:
        output += f"\n  Description: {item.description or '(none)'}"
        output += f"\n  Estimated: {item.estimated_hours}h"
        output += f"\n  Tags: {', '.join(item.tags) if item.tags else 'none'}"
        output += f"\n  Created: {item.created_at}"
    return output


def format_recommendation(rec: Recommendation) -> str:
    """Format recommendation for display (Phase 2)."""
    output = []

    # Header
    output.append(f"#{rec.rank} | {rec.backlog_item.id}: {rec.backlog_item.title}")
    output.append(f"    Priority: {rec.backlog_item.priority} | Score: {rec.score:.1f}/100")
    output.append(f"    Complexity: {rec.complexity} | Confidence: {rec.confidence:.0%}")

    # Rationale
    output.append(f"\n    {rec.rationale}")

    # Additional details
    details = []
    if rec.blocking_count > 0:
        details.append(f"Unblocks {rec.blocking_count} item(s)")
    if rec.dependencies:
        details.append(f"Depends on: {', '.join(rec.dependencies)}")
    if details:
        output.append(f"    Details: {' | '.join(details)}")

    return "\n".join(output)


def format_rich_delegation_package(package: RichDelegationPackage) -> str:
    """Format rich delegation package for display (Phase 2)."""
    output = []

    # Item info
    output.append(f"Item: {package.backlog_item.id} - {package.backlog_item.title}")
    output.append(f"Agent: {package.agent_role}")
    output.append(f"Priority: {package.backlog_item.priority}")
    output.append(f"Complexity: {package.complexity} ({package.estimated_hours}h estimated)")
    output.append("")

    # Description
    if package.backlog_item.description:
        output.append("Description:")
        output.append(f"  {package.backlog_item.description}")
        output.append("")

    # Relevant files
    if package.relevant_files:
        output.append("📂 Relevant Files to Examine:")
        for f in package.relevant_files[:10]:  # Limit to 10
            output.append(f"  • {f}")
        if len(package.relevant_files) > 10:
            output.append(f"  ... and {len(package.relevant_files) - 10} more")
        output.append("")

    # Similar patterns
    if package.similar_patterns:
        output.append("🔍 Similar Patterns in Codebase:")
        for pattern in package.similar_patterns:
            output.append(f"  • {pattern}")
        output.append("")

    # Test requirements
    if package.test_requirements:
        output.append("✅ Test Requirements:")
        for req in package.test_requirements:
            output.append(f"  • {req}")
        output.append("")

    # Architectural notes
    if package.architectural_notes:
        output.append("🏗️  Architectural Notes:")
        for line in package.architectural_notes.split("\n"):
            output.append(f"  {line}")
        output.append("")

    # Dependencies
    if package.dependencies:
        output.append("⚠️  Dependencies:")
        output.append(f"  This item depends on: {', '.join(package.dependencies)}")
        output.append("")

    return "\n".join(output)


# =============================================================================
# Validation Helpers
# =============================================================================


def validate_initialized(state_manager: PMStateManager) -> None:
    """Raise error if PM not initialized."""
    if not state_manager.is_initialized():
        raise ValueError("PM not initialized. Run /pm:init first to set up project management.")


def validate_no_active_workstream(state_manager: PMStateManager) -> None:
    """Raise error if active workstream exists (Phase 1 limit)."""
    active = state_manager.get_active_workstream()
    if active:
        raise ValueError(
            f"Active workstream exists: {active.id} - {active.title}\n"
            f"Phase 1 allows only one workstream at a time.\n"
            f"Complete or stop it with: /pm:status {active.id}"
        )
