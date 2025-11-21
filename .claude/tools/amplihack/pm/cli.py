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
from .workstream import WorkstreamManager, WorkstreamMonitor, CoordinationAnalysis
from .intelligence import RecommendationEngine, Recommendation, RichDelegationPackage


__all__ = [
    "cmd_init",
    "cmd_add",
    "cmd_start",
    "cmd_status",
    "cmd_suggest",
    "cmd_prepare",
    "cmd_coordinate",
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

        # Phase 3: Check capacity instead of single workstream limit
        can_start, reason = state_manager.can_start_workstream()
        if not can_start:
            print(f"❌ Error: {reason}")
            return 1

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
    multi_project: bool = False,
) -> int:
    """Implement /pm:status command.

    Three modes:
    - No args: Project overview (config, active workstreams, backlog)
    - With ws_id: Detailed workstream status
    - With multi_project: Aggregate status across multiple projects

    Args:
        ws_id: Optional workstream ID
        project_root: Project directory
        multi_project: Show multi-project dashboard

    Returns:
        Exit code
    """
    if project_root is None:
        project_root = Path.cwd()

    state_manager = PMStateManager(project_root)

    try:
        # Validate PM initialized (skip for multi-project mode)
        if not multi_project:
            validate_initialized(state_manager)

        if multi_project:
            # Multi-project dashboard mode (Phase 3)
            print(format_multi_project_dashboard(project_root))
        elif ws_id:
            # Workstream details mode
            ws_manager = WorkstreamManager(
                state_manager=state_manager,
                project_root=project_root,
            )
            status = ws_manager.get_workstream_status(ws_id)
            print(format_workstream_details(status["workstream"], status))
        else:
            # Project overview mode (Phase 3: multiple workstreams)
            config = state_manager.get_config()
            active_workstreams = state_manager.get_active_workstreams()
            backlog = state_manager.get_backlog_items(status="READY")
            counts = state_manager.get_workstream_count()
            print(format_project_overview_phase3(config, active_workstreams, backlog, counts))

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


def cmd_coordinate(
    project_root: Optional[Path] = None,
) -> int:
    """Implement /pm:coordinate command (Phase 3).

    Analyze all active workstreams for:
    - Cross-workstream dependencies
    - Conflicts (overlapping areas)
    - Stalled workstreams
    - Blockers
    - Optimal execution order

    Process:
    1. Validate PM initialized
    2. Run coordination analysis
    3. Display analysis results
    4. Show recommendations

    Args:
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

        # Run coordination analysis
        monitor = WorkstreamMonitor(state_manager)
        analysis = monitor.analyze_coordination()

        # Display analysis
        print("=" * 60)
        print("🎯 WORKSTREAM COORDINATION ANALYSIS")
        print("=" * 60)
        print()
        print(format_coordination_analysis(analysis))
        print()
        print("=" * 60)

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
    """Format project overview for terminal output (Phase 1/2 - backward compatibility).

    Deprecated: Use format_project_overview_phase3 for Phase 3+.
    """
    # Convert single workstream to list for Phase 3 formatter
    active_workstreams = [active_ws] if active_ws else []
    counts = {"RUNNING": len(active_workstreams), "PAUSED": 0, "COMPLETED": 0, "FAILED": 0}
    return format_project_overview_phase3(config, active_workstreams, backlog, counts)


def format_project_overview_phase3(
    config: PMConfig,
    active_workstreams: List[WorkstreamState],
    backlog: List[BacklogItem],
    counts: dict,
) -> str:
    """Format project overview for terminal output (Phase 3).

    Returns formatted string with:
    - Project header
    - Active workstreams (up to 5)
    - Backlog summary
    - Health indicator
    - Capacity status
    """
    output = []
    output.append("=" * 60)
    output.append(f"PROJECT: {config.project_name} [{config.project_type}]")
    output.append("=" * 60)
    output.append("")

    # Active workstreams (Phase 3: multiple)
    running_count = len(active_workstreams)
    output.append(f"⚡ ACTIVE WORKSTREAMS ({running_count}/5):")
    if active_workstreams:
        for ws in active_workstreams[:5]:  # Show up to 5
            output.append(f"  • {ws.id}: {ws.title} [{ws.agent}]")
            output.append(f"    Status: {ws.status} ({ws.elapsed_minutes} min elapsed)")
        if len(active_workstreams) > 5:
            output.append(f"  ... and {len(active_workstreams) - 5} more")
    else:
        output.append("  (none)")
    output.append("")

    # Backlog
    output.append(f"📋 BACKLOG ({len(backlog)} items ready):")
    for item in backlog[:5]:  # Show first 5
        output.append(f"  • {item.id}: {item.title} [{item.priority}]")
    if len(backlog) > 5:
        output.append(f"  ... and {len(backlog) - 5} more")
    if not backlog:
        output.append("  (empty)")
    output.append("")

    # Workstream statistics
    output.append(f"📊 WORKSTREAM STATS:")
    output.append(f"   Running: {counts.get('RUNNING', 0)}")
    output.append(f"   Paused: {counts.get('PAUSED', 0)}")
    output.append(f"   Completed: {counts.get('COMPLETED', 0)}")
    output.append(f"   Failed: {counts.get('FAILED', 0)}")
    output.append("")

    # Project health
    health = "🟢 HEALTHY"
    if any(ws.status == "FAILED" for ws in active_workstreams):
        health = "🔴 ATTENTION NEEDED"
    elif running_count >= 5:
        health = "🟡 AT CAPACITY"
    elif len(backlog) == 0 and running_count == 0:
        health = "🟡 IDLE"

    output.append(f"💚 PROJECT HEALTH: {health}")
    output.append(f"   Quality Bar: {config.quality_bar}")
    output.append(f"   Capacity: {running_count}/5 workstreams")
    output.append("")
    output.append("💡 TIP: Use /pm:coordinate to analyze workstream coordination")

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
    """Raise error if active workstream exists (Phase 1 limit).

    Deprecated in Phase 3 - use can_start_workstream() instead.
    """
    active = state_manager.get_active_workstream()
    if active:
        raise ValueError(
            f"Active workstream exists: {active.id} - {active.title}\n"
            f"Phase 1 allows only one workstream at a time.\n"
            f"Complete or stop it with: /pm:status {active.id}"
        )


def format_coordination_analysis(analysis: CoordinationAnalysis) -> str:
    """Format coordination analysis for display (Phase 3)."""
    output = []

    # Capacity status
    output.append(f"📊 Capacity: {analysis.capacity_status}")
    output.append("")

    # Active workstreams
    output.append(f"⚡ Active Workstreams ({len(analysis.active_workstreams)}):")
    if analysis.active_workstreams:
        for ws in analysis.active_workstreams:
            output.append(f"  • {ws.id}: {ws.title} [{ws.agent}] - {ws.elapsed_minutes} min")
    else:
        output.append("  (none)")
    output.append("")

    # Dependencies
    if analysis.dependencies:
        output.append(f"🔗 Dependencies ({len(analysis.dependencies)}):")
        for dep in analysis.dependencies:
            output.append(
                f"  • {dep['workstream']} depends on {dep['depends_on']} "
                f"[{dep['type']}]"
            )
        output.append("")

    # Conflicts
    if analysis.conflicts:
        output.append(f"⚠️  Conflicts ({len(analysis.conflicts)}):")
        for conflict in analysis.conflicts:
            ws_list = ", ".join(conflict["workstreams"])
            output.append(f"  • {ws_list}")
            output.append(f"    Reason: {conflict['reason']}")
            output.append(f"    Severity: {conflict['severity']}")
        output.append("")

    # Stalled workstreams
    if analysis.stalled:
        output.append(f"⏸️  Stalled Workstreams ({len(analysis.stalled)}):")
        for ws in analysis.stalled:
            output.append(f"  • {ws.id}: {ws.title} (no progress > 30 min)")
        output.append("")

    # Blockers
    if analysis.blockers:
        output.append(f"🚫 Blockers ({len(analysis.blockers)}):")
        for blocker in analysis.blockers:
            output.append(f"  • {blocker['workstream']}: {blocker['title']}")
            for issue in blocker["issues"]:
                output.append(f"    - {issue}")
        output.append("")

    # Recommended execution order
    if analysis.execution_order:
        output.append("📋 Suggested Execution Order:")
        for i, ws_id in enumerate(analysis.execution_order, 1):
            output.append(f"  {i}. {ws_id}")
        output.append("")

    # Recommendations
    output.append("💡 Recommendations:")
    for rec in analysis.recommendations:
        output.append(f"  {rec}")

    return "\n".join(output)


def format_multi_project_dashboard(search_root: Path) -> str:
    """Format multi-project dashboard (Phase 3).

    Searches for all .pm/ directories under search_root and aggregates status.
    """
    output = []
    output.append("=" * 60)
    output.append("🏢 MULTI-PROJECT DASHBOARD")
    output.append("=" * 60)
    output.append("")

    # Find all .pm directories
    pm_dirs = list(search_root.rglob(".pm"))

    if not pm_dirs:
        output.append("No PM-managed projects found.")
        return "\n".join(output)

    # Aggregate stats
    total_running = 0
    total_paused = 0
    total_completed = 0
    total_failed = 0
    total_backlog = 0

    projects = []

    for pm_dir in pm_dirs:
        project_root = pm_dir.parent
        try:
            state_manager = PMStateManager(project_root)
            if not state_manager.is_initialized():
                continue

            config = state_manager.get_config()
            counts = state_manager.get_workstream_count()
            backlog = state_manager.get_backlog_items(status="READY")

            total_running += counts.get("RUNNING", 0)
            total_paused += counts.get("PAUSED", 0)
            total_completed += counts.get("COMPLETED", 0)
            total_failed += counts.get("FAILED", 0)
            total_backlog += len(backlog)

            projects.append({
                "name": config.project_name,
                "path": project_root,
                "running": counts.get("RUNNING", 0),
                "backlog": len(backlog),
                "health": "🟢" if counts.get("RUNNING", 0) > 0 else "🟡",
            })
        except Exception:
            # Skip projects with errors
            continue

    # Display projects
    output.append(f"📁 Projects ({len(projects)}):")
    for proj in projects:
        output.append(
            f"  {proj['health']} {proj['name']}: {proj['running']} running, "
            f"{proj['backlog']} backlog"
        )
        output.append(f"     Path: {proj['path']}")
    output.append("")

    # Aggregate stats
    output.append("📊 Aggregate Statistics:")
    output.append(f"   Total Running: {total_running}")
    output.append(f"   Total Backlog: {total_backlog}")
    output.append(f"   Total Completed: {total_completed}")
    output.append(f"   Total Failed: {total_failed}")

    return "\n".join(output)
