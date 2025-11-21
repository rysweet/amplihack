"""PM workstream management with ClaudeProcess integration.

This module manages workstream lifecycle and delegates work to AI agents
through ClaudeProcess. It creates delegation packages that contain all
context needed for an agent to complete work autonomously.

Public API:
    - DelegationPackage: Structured context for agent work
    - WorkstreamManager: Manages workstream lifecycle and agent delegation

Philosophy:
    - Template-based delegation (predictable, testable)
    - ClaudeProcess integration for agent execution
    - Simple synchronous execution (no async complexity)
    - Ruthless simplicity
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Any

from .state import PMStateManager, BacklogItem, WorkstreamState

try:
    # Try importing from installed package or sys.path first
    from amplihack.orchestration.claude_process import ClaudeProcess, ProcessResult
except ImportError:
    # Fallback for direct execution in .claude/tools/
    import sys
    from pathlib import Path as _Path

    _tools_dir = _Path(__file__).parent.parent
    if str(_tools_dir) not in sys.path:
        sys.path.insert(0, str(_tools_dir))
    from orchestration.claude_process import ClaudeProcess, ProcessResult

# Import Phase 2 intelligence module (optional - degrades gracefully)
try:
    from .intelligence import (
        RecommendationEngine,
        RichDelegationPackage,
    )
    INTELLIGENCE_AVAILABLE = True
except ImportError:
    INTELLIGENCE_AVAILABLE = False


__all__ = [
    "DelegationPackage",
    "WorkstreamManager",
    "WorkstreamMonitor",
    "CoordinationAnalysis",
]


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class DelegationPackage:
    """Structured delegation package for agent.

    Contains everything agent needs to complete work.
    """

    backlog_item: BacklogItem
    agent_role: str  # builder, reviewer, etc.
    project_context: str  # From .pm/config.yaml + roadmap.md
    instructions: str  # Generated instructions
    success_criteria: List[str]  # What defines done
    estimated_hours: int
    rich_context: Optional[Dict[str, Any]] = None  # Phase 2: AI-enhanced context

    def to_prompt(self) -> str:
        """Convert package to Claude prompt string.

        Phase 2: Includes rich context if available.
        """
        prompt = f"""# Work Assignment: {self.backlog_item.title}

## Context

{self.project_context}

## Your Task

{self.backlog_item.description}

**Priority**: {self.backlog_item.priority}
**Estimated**: {self.estimated_hours} hours
**Tags**: {", ".join(self.backlog_item.tags) if self.backlog_item.tags else "None"}
"""

        # Phase 2: Add rich context if available
        if self.rich_context:
            prompt += "\n## AI-Enhanced Context\n\n"

            if self.rich_context.get("complexity"):
                prompt += f"**Complexity**: {self.rich_context['complexity']}\n\n"

            if self.rich_context.get("relevant_files"):
                prompt += "**Relevant Files to Examine**:\n"
                for f in self.rich_context["relevant_files"][:10]:
                    prompt += f"- {f}\n"
                prompt += "\n"

            if self.rich_context.get("similar_patterns"):
                prompt += "**Similar Patterns in Codebase**:\n"
                for pattern in self.rich_context["similar_patterns"]:
                    prompt += f"- {pattern}\n"
                prompt += "\n"

            if self.rich_context.get("test_requirements"):
                prompt += "**Test Requirements**:\n"
                for req in self.rich_context["test_requirements"]:
                    prompt += f"- {req}\n"
                prompt += "\n"

            if self.rich_context.get("architectural_notes"):
                prompt += f"**Architectural Notes**:\n{self.rich_context['architectural_notes']}\n\n"

        # Success criteria
        prompt += "## Success Criteria\n\n"
        prompt += "\n".join(f"- {criterion}" for criterion in self.success_criteria)

        # Instructions
        prompt += f"""

## Instructions

{self.instructions}

## Philosophy Reminder

- Ruthless simplicity
- Zero-BS implementation (no stubs, no placeholders)
- Every function works or doesn't exist
- Question every abstraction
- Test behavior, not implementation

---

Begin implementation now. Report when complete.
"""
        return prompt


# =============================================================================
# Workstream Manager
# =============================================================================


class WorkstreamManager:
    """Manages workstream execution and ClaudeProcess integration.

    Responsibilities:
    - Create delegation packages
    - Spawn ClaudeProcess for agent work
    - Monitor workstream progress
    - Update workstream state

    Usage:
        manager = WorkstreamManager(
            state_manager=state_mgr,
            project_root=Path.cwd(),
            log_dir=Path(".pm/logs")
        )

        # Start workstream
        result = manager.start_workstream(
            backlog_id="BL-001",
            agent="builder"
        )

        # Check status
        status = manager.get_workstream_status("ws-001")
    """

    def __init__(
        self,
        state_manager: PMStateManager,
        project_root: Path,
        log_dir: Optional[Path] = None,
    ):
        """Initialize workstream manager.

        Args:
            state_manager: PM state manager
            project_root: Project root directory
            log_dir: Directory for process logs (default: .pm/logs)
        """
        self.state_manager = state_manager
        self.project_root = project_root
        self.log_dir = log_dir or (project_root / ".pm" / "logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def start_workstream(
        self,
        backlog_id: str,
        agent: str = "builder",
        timeout: Optional[int] = None,
    ) -> WorkstreamState:
        """Start new workstream for backlog item.

        Process:
        1. Check capacity (Phase 3: max 5 concurrent)
        2. Load backlog item
        3. Create delegation package
        4. Create workstream state
        5. Spawn ClaudeProcess
        6. Return workstream state

        Args:
            backlog_id: Backlog item ID (BL-001)
            agent: Agent role (builder, reviewer, etc.)
            timeout: Process timeout in seconds

        Returns:
            WorkstreamState object

        Raises:
            ValueError: If at capacity or item not found
        """
        # Phase 3: Check capacity (max 5 concurrent workstreams)
        can_start, reason = self.state_manager.can_start_workstream()
        if not can_start:
            raise ValueError(f"Cannot start workstream: {reason}")

        # Load backlog item
        backlog_item = self.state_manager.get_backlog_item(backlog_id)
        if not backlog_item:
            raise ValueError(f"Backlog item {backlog_id} not found")

        # Create workstream
        workstream = self.state_manager.create_workstream(
            backlog_id=backlog_id,
            agent=agent,
        )

        # Create delegation package
        delegation_package = self.create_delegation_package(
            backlog_item=backlog_item,
            agent=agent,
        )

        # Spawn agent process
        result = self.spawn_agent_process(
            delegation_package=delegation_package,
            workstream=workstream,
            timeout=timeout,
        )

        # Update workstream with process info and duration
        self.state_manager.update_workstream(
            workstream.id,
            process_id=result.process_id,
            elapsed_minutes=int(result.duration / 60),
        )

        return self.state_manager.get_workstream(workstream.id)

    def get_workstream_status(self, ws_id: str) -> Dict[str, Any]:
        """Get detailed workstream status.

        Returns:
            {
                "workstream": WorkstreamState,
                "elapsed_time": "30 min",
                "progress": "60%",
                "status": "RUNNING",
            }
        """
        workstream = self.state_manager.get_workstream(ws_id)
        if not workstream:
            raise ValueError(f"Workstream {ws_id} not found")

        # Calculate elapsed time
        elapsed_str = f"{workstream.elapsed_minutes} min"
        if workstream.elapsed_minutes >= 60:
            hours = workstream.elapsed_minutes // 60
            mins = workstream.elapsed_minutes % 60
            elapsed_str = f"{hours}h {mins}m"

        # Estimate progress (simple heuristic based on status)
        progress = "0%"
        if workstream.status == "RUNNING":
            # Rough estimate based on elapsed time vs estimated
            backlog_item = self.state_manager.get_backlog_item(workstream.backlog_id)
            if backlog_item:
                estimated_mins = backlog_item.estimated_hours * 60
                progress_pct = min(int((workstream.elapsed_minutes / estimated_mins) * 100), 99)
                progress = f"{progress_pct}%"
        elif workstream.status == "COMPLETED":
            progress = "100%"
        elif workstream.status == "FAILED":
            progress = "N/A"

        return {
            "workstream": workstream,
            "elapsed_time": elapsed_str,
            "progress": progress,
            "status": workstream.status,
        }

    def stop_workstream(self, ws_id: str, reason: str = "") -> WorkstreamState:
        """Stop active workstream.

        Updates state to PAUSED, adds note about reason.
        """
        workstream = self.state_manager.get_workstream(ws_id)
        if not workstream:
            raise ValueError(f"Workstream {ws_id} not found")

        # Add stop reason to notes
        notes = workstream.progress_notes.copy()
        if reason:
            notes.append(f"Stopped: {reason}")
        else:
            notes.append("Stopped by user")

        # Update status
        return self.state_manager.update_workstream(
            ws_id,
            status="PAUSED",
            progress_notes=notes,
        )

    def complete_workstream(
        self,
        ws_id: str,
        success: bool = True,
        notes: Optional[List[str]] = None,
    ) -> WorkstreamState:
        """Mark workstream as completed.

        Delegates to state_manager.complete_workstream()
        """
        workstream = self.state_manager.get_workstream(ws_id)
        if not workstream:
            raise ValueError(f"Workstream {ws_id} not found")

        # Add completion notes if provided
        if notes:
            all_notes = workstream.progress_notes + notes
            self.state_manager.update_workstream(
                ws_id,
                progress_notes=all_notes,
            )

        # Complete workstream
        return self.state_manager.complete_workstream(ws_id, success=success)

    # =========================================================================
    # Delegation Package Creation
    # =========================================================================

    def create_delegation_package(
        self,
        backlog_item: BacklogItem,
        agent: str,
    ) -> DelegationPackage:
        """Create delegation package for agent.

        Builds package from:
        - Backlog item details
        - Project config
        - Roadmap context
        - Agent-specific instructions (template)

        Phase 2: If intelligence module available, includes AI-enhanced context:
        - Complexity estimation
        - Relevant files
        - Similar patterns
        - Test requirements
        - Architectural notes
        """
        # Load project context
        project_context = self._load_project_context()

        # Generate agent-specific instructions
        instructions = self._generate_agent_instructions(agent, backlog_item)

        # Define success criteria
        success_criteria = [
            "All requirements implemented and working",
            "Tests pass (if applicable)",
            "Code follows project philosophy (ruthless simplicity)",
            "No stubs or placeholders",
            "Documentation updated",
        ]

        # Phase 2: Try to generate rich context
        rich_context = None
        if INTELLIGENCE_AVAILABLE:
            try:
                engine = RecommendationEngine(self.state_manager, self.project_root)
                rich_package = engine.create_rich_delegation_package(
                    backlog_item.id,
                    agent,
                )
                # Extract relevant fields for DelegationPackage
                rich_context = {
                    "complexity": rich_package.complexity,
                    "relevant_files": rich_package.relevant_files,
                    "similar_patterns": rich_package.similar_patterns,
                    "test_requirements": rich_package.test_requirements,
                    "architectural_notes": rich_package.architectural_notes,
                }
            except Exception:
                # Degrade gracefully - intelligence is optional
                pass

        return DelegationPackage(
            backlog_item=backlog_item,
            agent_role=agent,
            project_context=project_context,
            instructions=instructions,
            success_criteria=success_criteria,
            estimated_hours=backlog_item.estimated_hours,
            rich_context=rich_context,
        )

    # =========================================================================
    # ClaudeProcess Integration
    # =========================================================================

    def spawn_agent_process(
        self,
        delegation_package: DelegationPackage,
        workstream: WorkstreamState,
        timeout: Optional[int] = None,
    ) -> ProcessResult:
        """Spawn ClaudeProcess for agent work.

        Creates ClaudeProcess with:
        - Prompt from delegation package
        - Working directory = project_root
        - Log directory = .pm/logs
        - Process ID = pm-{agent}-{ws_id}

        Returns:
            ProcessResult from ClaudeProcess.run()
        """
        # Build prompt from delegation package
        prompt = delegation_package.to_prompt()

        # Create process
        process = ClaudeProcess(
            prompt=prompt,
            process_id=f"pm-{workstream.agent}-{workstream.id}",
            working_dir=self.project_root,
            log_dir=self.log_dir,
            model=None,  # Use default
            stream_output=True,
            timeout=timeout,
        )

        # Log start
        print(f"\n{'=' * 60}")
        print(f"PM: Starting {workstream.agent} agent for workstream {workstream.id}")
        print(f"PM: Title: {workstream.title}")
        print(f"PM: Log: {self.log_dir / f'{process.process_id}.log'}")
        print(f"{'=' * 60}\n")

        # Run and capture result
        result = process.run()

        # Log completion
        print(f"\n{'=' * 60}")
        print(f"PM: Agent completed (exit code: {result.exit_code})")
        print(f"PM: Duration: {result.duration:.1f}s")
        print(f"{'=' * 60}\n")

        return result

    # =========================================================================
    # Template Generation
    # =========================================================================

    def _generate_agent_instructions(
        self,
        agent: str,
        backlog_item: BacklogItem,
    ) -> str:
        """Generate agent-specific instructions.

        Templates by agent role:
        - builder: Implementation focus
        - reviewer: Quality checks
        - tester: Test coverage
        """
        templates = {
            "builder": """1. Analyze the requirements carefully
2. Design solution following project patterns
3. Implement working code (no stubs or placeholders)
4. Add tests to verify behavior
5. Check philosophy compliance
6. Update documentation as needed

Focus on ruthless simplicity. Start with the simplest solution that works.""",
            "reviewer": """1. Review code for philosophy compliance
2. Check for stubs, placeholders, or dead code
3. Verify tests cover behavior (not implementation)
4. Look for unnecessary abstractions
5. Suggest simplifications
6. Verify documentation accuracy

Focus on ruthless simplicity and zero-BS implementation.""",
            "tester": """1. Analyze code behavior and contracts
2. Design tests for edge cases
3. Implement comprehensive test coverage
4. Verify tests pass
5. Document test scenarios

Focus on testing behavior, not implementation details.""",
        }

        return templates.get(
            agent,
            """1. Complete the assigned task following project philosophy
2. Focus on ruthless simplicity
3. Verify all requirements are met
4. Test your work
5. Document any important decisions""",
        )

    def _load_project_context(self) -> str:
        """Load project context from config + roadmap."""
        # Load config
        config = self.state_manager.get_config()

        # Load roadmap if exists
        roadmap_path = self.state_manager.pm_dir / "roadmap.md"
        roadmap_content = ""
        if roadmap_path.exists():
            roadmap_content = roadmap_path.read_text()

        # Build context string
        context = f"""**Project**: {config.project_name}
**Type**: {config.project_type}
**Quality Bar**: {config.quality_bar}

**Primary Goals**:
"""
        for goal in config.primary_goals:
            context += f"- {goal}\n"

        if roadmap_content:
            context += f"\n**Roadmap**:\n{roadmap_content[:1000]}"  # First 1000 chars

        return context


# =============================================================================
# Phase 3: Coordination & Monitoring
# =============================================================================


@dataclass
class CoordinationAnalysis:
    """Result of workstream coordination analysis (Phase 3)."""

    active_workstreams: List[WorkstreamState]
    conflicts: List[Dict[str, Any]]  # Detected conflicts between workstreams
    dependencies: List[Dict[str, Any]]  # Cross-workstream dependencies
    stalled: List[WorkstreamState]  # Workstreams with no progress > 30 min
    blockers: List[Dict[str, Any]]  # Identified blockers
    recommendations: List[str]  # Coordination recommendations
    execution_order: List[str]  # Suggested execution order (workstream IDs)
    capacity_status: str  # e.g., "3/5 concurrent workstreams"


class WorkstreamMonitor:
    """Monitor workstream health and detect issues (Phase 3).

    Responsibilities:
    - Detect stalled workstreams (no progress > 30 min)
    - Identify off-track workstreams
    - Auto-escalate blockers
    - Health status tracking
    - Cross-workstream dependency analysis
    - Conflict detection

    Usage:
        monitor = WorkstreamMonitor(state_manager)

        # Check for stalls
        stalled = monitor.detect_stalls()

        # Get health status
        health = monitor.get_workstream_health("ws-001")

        # Analyze coordination
        analysis = monitor.analyze_coordination()
    """

    STALL_THRESHOLD_MINUTES = 30

    def __init__(self, state_manager: PMStateManager):
        """Initialize workstream monitor.

        Args:
            state_manager: PM state manager
        """
        self.state_manager = state_manager

    def detect_stalls(self) -> List[WorkstreamState]:
        """Detect stalled workstreams (no progress > 30 min).

        Returns:
            List of stalled workstreams
        """
        from datetime import datetime, timedelta

        active = self.state_manager.get_active_workstreams()
        stalled = []

        for ws in active:
            # Check last_activity or fall back to started_at
            last_activity_str = ws.last_activity or ws.started_at

            try:
                last_activity = datetime.fromisoformat(last_activity_str.replace("Z", "+00:00"))
                now = datetime.now(last_activity.tzinfo)
                elapsed = (now - last_activity).total_seconds() / 60

                if elapsed > self.STALL_THRESHOLD_MINUTES:
                    stalled.append(ws)
            except Exception:
                # If timestamp parsing fails, assume not stalled
                pass

        return stalled

    def get_workstream_health(self, ws_id: str) -> Dict[str, Any]:
        """Get health status for workstream.

        Returns:
            {
                "status": "HEALTHY" | "STALLED" | "OFF_TRACK" | "BLOCKED",
                "issues": ["issue1", "issue2"],
                "recommendations": ["rec1", "rec2"],
            }
        """
        ws = self.state_manager.get_workstream(ws_id)
        if not ws:
            return {"status": "NOT_FOUND", "issues": [], "recommendations": []}

        issues = []
        recommendations = []
        status = "HEALTHY"

        # Check if stalled
        stalled_workstreams = self.detect_stalls()
        if any(w.id == ws_id for w in stalled_workstreams):
            status = "STALLED"
            issues.append(f"No progress for > {self.STALL_THRESHOLD_MINUTES} minutes")
            recommendations.append("Check agent status and consider restarting")

        # Check dependencies
        if ws.dependencies:
            unmet_deps = self._check_dependencies(ws)
            if unmet_deps:
                status = "BLOCKED"
                issues.append(f"Blocked by: {', '.join(unmet_deps)}")
                recommendations.append(f"Complete dependencies: {', '.join(unmet_deps)}")

        # Check for excessive duration
        backlog_item = self.state_manager.get_backlog_item(ws.backlog_id)
        if backlog_item and ws.elapsed_minutes > (backlog_item.estimated_hours * 60 * 1.5):
            status = "OFF_TRACK"
            issues.append(f"Exceeded estimated time by 50%")
            recommendations.append("Review scope or re-estimate effort")

        return {
            "status": status,
            "issues": issues,
            "recommendations": recommendations,
        }

    def analyze_coordination(self) -> CoordinationAnalysis:
        """Analyze all active workstreams for coordination needs.

        Detects:
        - Cross-workstream dependencies
        - Conflicts (same files/areas)
        - Optimal execution order
        - Blockers and stalls

        Returns:
            CoordinationAnalysis object
        """
        active = self.state_manager.get_active_workstreams()
        counts = self.state_manager.get_workstream_count()

        # Detect stalls
        stalled = self.detect_stalls()

        # Analyze dependencies
        dependencies = self._analyze_dependencies(active)

        # Detect conflicts (simplified - check for overlapping tags/areas)
        conflicts = self._detect_conflicts(active)

        # Identify blockers
        blockers = self._identify_blockers(active)

        # Generate recommendations
        recommendations = self._generate_recommendations(active, stalled, conflicts, blockers)

        # Suggest execution order
        execution_order = self._suggest_execution_order(active, dependencies)

        # Capacity status
        running = counts.get("RUNNING", 0)
        capacity_status = f"{running}/5 concurrent workstreams"

        return CoordinationAnalysis(
            active_workstreams=active,
            conflicts=conflicts,
            dependencies=dependencies,
            stalled=stalled,
            blockers=blockers,
            recommendations=recommendations,
            execution_order=execution_order,
            capacity_status=capacity_status,
        )

    # =========================================================================
    # Private Helpers
    # =========================================================================

    def _check_dependencies(self, ws: WorkstreamState) -> List[str]:
        """Check unmet dependencies for workstream.

        Returns:
            List of backlog IDs that are not yet DONE
        """
        if not ws.dependencies:
            return []

        unmet = []
        for dep_id in ws.dependencies:
            dep_item = self.state_manager.get_backlog_item(dep_id)
            if dep_item and dep_item.status != "DONE":
                unmet.append(dep_id)

        return unmet

    def _analyze_dependencies(self, workstreams: List[WorkstreamState]) -> List[Dict[str, Any]]:
        """Analyze cross-workstream dependencies.

        Returns:
            List of dependency relationships
        """
        dependencies = []

        for ws in workstreams:
            if ws.dependencies:
                for dep_id in ws.dependencies:
                    # Check if dependency is another active workstream
                    dep_ws = next((w for w in workstreams if w.backlog_id == dep_id), None)
                    if dep_ws:
                        dependencies.append({
                            "workstream": ws.id,
                            "depends_on": dep_ws.id,
                            "type": "workstream",
                            "blocking": True,
                        })
                    else:
                        # Dependency on backlog item
                        dep_item = self.state_manager.get_backlog_item(dep_id)
                        if dep_item and dep_item.status != "DONE":
                            dependencies.append({
                                "workstream": ws.id,
                                "depends_on": dep_id,
                                "type": "backlog",
                                "blocking": True,
                            })

        return dependencies

    def _detect_conflicts(self, workstreams: List[WorkstreamState]) -> List[Dict[str, Any]]:
        """Detect potential conflicts between workstreams.

        Simplified approach: Check for overlapping tags in backlog items.
        """
        conflicts = []

        for i, ws1 in enumerate(workstreams):
            item1 = self.state_manager.get_backlog_item(ws1.backlog_id)
            if not item1:
                continue

            for ws2 in workstreams[i + 1:]:
                item2 = self.state_manager.get_backlog_item(ws2.backlog_id)
                if not item2:
                    continue

                # Check for overlapping tags
                overlap = set(item1.tags) & set(item2.tags)
                if overlap:
                    conflicts.append({
                        "workstreams": [ws1.id, ws2.id],
                        "reason": f"Overlapping areas: {', '.join(overlap)}",
                        "severity": "MEDIUM",
                    })

        return conflicts

    def _identify_blockers(self, workstreams: List[WorkstreamState]) -> List[Dict[str, Any]]:
        """Identify blockers across workstreams."""
        blockers = []

        for ws in workstreams:
            health = self.get_workstream_health(ws.id)
            if health["status"] == "BLOCKED":
                blockers.append({
                    "workstream": ws.id,
                    "title": ws.title,
                    "issues": health["issues"],
                    "recommendations": health["recommendations"],
                })

        return blockers

    def _generate_recommendations(
        self,
        active: List[WorkstreamState],
        stalled: List[WorkstreamState],
        conflicts: List[Dict[str, Any]],
        blockers: List[Dict[str, Any]],
    ) -> List[str]:
        """Generate coordination recommendations."""
        recommendations = []

        # Stalled workstreams
        if stalled:
            stalled_ids = [ws.id for ws in stalled]
            recommendations.append(
                f"⚠️  {len(stalled)} stalled workstream(s): {', '.join(stalled_ids)}. "
                "Check agent status or restart."
            )

        # Conflicts
        if conflicts:
            recommendations.append(
                f"⚠️  {len(conflicts)} potential conflict(s) detected. "
                "Consider sequential execution or coordination."
            )

        # Blockers
        if blockers:
            recommendations.append(
                f"🚫 {len(blockers)} blocked workstream(s). "
                "Resolve dependencies first."
            )

        # Capacity
        if len(active) >= 5:
            recommendations.append(
                "⚠️  At maximum capacity (5 workstreams). "
                "Complete some before starting new ones."
            )

        # All clear
        if not recommendations:
            recommendations.append("✅ All workstreams healthy. No coordination issues detected.")

        return recommendations

    def _suggest_execution_order(
        self,
        workstreams: List[WorkstreamState],
        dependencies: List[Dict[str, Any]],
    ) -> List[str]:
        """Suggest optimal execution order based on dependencies.

        Simple topological sort approach.
        """
        # Build dependency graph
        graph = {ws.id: [] for ws in workstreams}
        for dep in dependencies:
            if dep["type"] == "workstream":
                graph[dep["workstream"]].append(dep["depends_on"])

        # Simple ordering: dependencies first, then independent
        ordered = []
        remaining = set(ws.id for ws in workstreams)

        # First pass: items with no dependencies
        for ws_id in list(remaining):
            if not graph[ws_id]:
                ordered.append(ws_id)
                remaining.remove(ws_id)

        # Second pass: items with dependencies (may not be optimal)
        ordered.extend(list(remaining))

        return ordered
