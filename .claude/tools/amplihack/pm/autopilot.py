"""PM autonomous decision-making and action execution.

This module implements Phase 4 (Autonomy) capabilities for the PM Architect,
enabling autonomous work selection, execution, and learning from outcomes.

Public API:
    - AutopilotDecision: Record of autonomous decision
    - AutopilotEngine: Autonomous work selection and execution
    - AutonomousSchedule: Schedule for autopilot runs

Philosophy:
    - Transparency: All decisions logged with full rationale
    - User control: Dry-run mode and override capability
    - Learning: Track outcomes to improve over time
    - Ruthless simplicity: Rule-based, not ML
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import uuid

from .state import PMStateManager, BacklogItem, WorkstreamState
from .intelligence import RecommendationEngine, Recommendation
from .workstream import WorkstreamManager

__all__ = [
    "AutopilotDecision",
    "AutopilotEngine",
    "AutonomousSchedule",
]


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class AutopilotDecision:
    """Record of an autonomous decision made by autopilot.

    Attributes:
        decision_id: Unique identifier for this decision
        timestamp: When decision was made
        decision_type: start_work, pause_work, escalate_blocker, etc.
        action_taken: What action was taken
        rationale: Why this decision was made
        alternatives_considered: Other options that were evaluated
        confidence: Confidence in decision (0.0-1.0)
        outcome: Result after execution (success/failure/pending)
        can_override: Whether user can reverse this decision
        override_command: Command to reverse decision
        context: Additional context data
    """
    decision_id: str
    timestamp: str  # ISO timestamp
    decision_type: str
    action_taken: str
    rationale: str
    alternatives_considered: List[str]
    confidence: float
    outcome: str = "pending"  # pending, success, failure
    can_override: bool = True
    override_command: str = ""
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AutopilotDecision":
        """Create from dictionary loaded from YAML."""
        if data.get("alternatives_considered") is None:
            data["alternatives_considered"] = []
        if data.get("context") is None:
            data["context"] = {}
        return cls(**data)


@dataclass
class AutonomousSchedule:
    """Schedule configuration for autopilot.

    Attributes:
        mode: on-demand, hourly, daily
        last_run: ISO timestamp of last run
        next_run: ISO timestamp of next scheduled run
        enabled: Whether autopilot is enabled
        max_concurrent: Maximum concurrent workstreams to start
        min_confidence: Minimum confidence threshold for decisions
    """
    mode: str = "on-demand"  # on-demand, hourly, daily
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    enabled: bool = True
    max_concurrent: int = 3
    min_confidence: float = 0.7

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AutonomousSchedule":
        """Create from dictionary loaded from YAML."""
        return cls(**data)


# =============================================================================
# Autopilot Engine
# =============================================================================


class AutopilotEngine:
    """Autonomous decision-making and execution engine.

    Capabilities:
    - Analyze current state and decide what to work on
    - Start new workstreams autonomously
    - Monitor and adjust running work
    - Escalate blockers and conflicts
    - Learn from outcomes over time

    Decision transparency:
    - All decisions logged with rationale
    - Alternatives considered documented
    - Override commands provided
    - Confidence scores included

    Usage:
        engine = AutopilotEngine(project_root)

        # Dry-run mode (show decisions, don't execute)
        decisions = engine.run(dry_run=True)

        # Execute mode (actually take actions)
        decisions = engine.run(dry_run=False)

        # Explain a decision
        explanation = engine.explain_decision(decision_id)
    """

    def __init__(self, project_root: Path):
        """Initialize autopilot engine.

        Args:
            project_root: Root directory of project (contains .pm/)
        """
        self.project_root = project_root
        self.state_mgr = PMStateManager(project_root)
        self.ws_mgr = WorkstreamManager(
            state_manager=self.state_mgr,
            project_root=project_root
        )
        self.rec_engine = RecommendationEngine(
            state_manager=self.state_mgr,
            project_root=project_root
        )
        self.decisions_file = project_root / ".pm" / "logs" / "autopilot_decisions.yaml"

    def run(self, dry_run: bool = True, max_actions: int = 3) -> List[AutopilotDecision]:
        """Run autopilot cycle: analyze, decide, execute.

        Args:
            dry_run: If True, show decisions but don't execute
            max_actions: Maximum number of actions to take in one run

        Returns:
            List of decisions made
        """
        decisions = []

        # Load schedule and check if we should run
        schedule = self._load_schedule()
        if not schedule.enabled:
            return decisions

        # Analyze current state
        active_ws = self.state_mgr.get_active_workstreams()
        can_start, reason = self.state_mgr.can_start_workstream(
            max_concurrent=schedule.max_concurrent
        )

        # Decision 1: Check for stalled workstreams
        stalled_decisions = self._check_stalled_workstreams(active_ws, dry_run)
        decisions.extend(stalled_decisions)

        # Decision 2: Start new work if capacity available
        if can_start and len(decisions) < max_actions:
            start_decisions = self._decide_new_work(schedule, dry_run)
            decisions.extend(start_decisions[:max_actions - len(decisions)])

        # Decision 3: Monitor for conflicts
        if active_ws and len(decisions) < max_actions:
            conflict_decisions = self._check_conflicts(active_ws, dry_run)
            decisions.extend(conflict_decisions[:max_actions - len(decisions)])

        # Log all decisions
        self._log_decisions(decisions)

        # Update schedule
        schedule.last_run = datetime.utcnow().isoformat() + "Z"
        if schedule.mode == "hourly":
            next_time = datetime.utcnow() + timedelta(hours=1)
            schedule.next_run = next_time.isoformat() + "Z"
        elif schedule.mode == "daily":
            next_time = datetime.utcnow() + timedelta(days=1)
            schedule.next_run = next_time.isoformat() + "Z"
        self._save_schedule(schedule)

        return decisions

    def _check_stalled_workstreams(
        self,
        active_ws: List[WorkstreamState],
        dry_run: bool
    ) -> List[AutopilotDecision]:
        """Check for stalled workstreams and decide what to do.

        A workstream is considered stalled if:
        - No progress update in > 30 minutes
        - No process_id (not actually running)
        """
        decisions = []

        for ws in active_ws:
            # Check if stalled
            is_stalled = False
            stall_reason = ""

            if not ws.last_activity:
                is_stalled = True
                stall_reason = "No activity recorded"
            else:
                try:
                    last_time = datetime.fromisoformat(ws.last_activity.replace("Z", "+00:00"))
                    elapsed = datetime.now(last_time.tzinfo) - last_time
                    if elapsed.total_seconds() > 1800:  # 30 minutes
                        is_stalled = True
                        stall_reason = f"No activity for {int(elapsed.total_seconds() / 60)} minutes"
                except (ValueError, AttributeError):
                    pass

            if not ws.process_id:
                is_stalled = True
                stall_reason = "No active process"

            if is_stalled:
                # Decide to escalate
                decision = AutopilotDecision(
                    decision_id=f"autopilot-{uuid.uuid4().hex[:8]}",
                    timestamp=datetime.utcnow().isoformat() + "Z",
                    decision_type="escalate_stalled",
                    action_taken=f"Escalate {ws.id}: {stall_reason}",
                    rationale=f"Workstream {ws.id} appears stalled. {stall_reason}. Requires human attention.",
                    alternatives_considered=[
                        "Wait longer (risk continued stall)",
                        "Auto-restart (risky without understanding cause)",
                        "Escalate to human (conservative, ensures proper handling)"
                    ],
                    confidence=0.8,
                    can_override=False,
                    override_command="",
                    context={"workstream_id": ws.id, "reason": stall_reason}
                )

                if not dry_run:
                    # In execute mode, mark as escalated
                    decision.outcome = "success"
                    # Note: In a real system, this would send notifications

                decisions.append(decision)

        return decisions

    def _decide_new_work(
        self,
        schedule: AutonomousSchedule,
        dry_run: bool
    ) -> List[AutopilotDecision]:
        """Decide what new work to start.

        Uses recommendation engine to select best item.
        Only starts if confidence >= min_confidence.
        """
        decisions = []

        # Get recommendations
        try:
            recommendations = self.rec_engine.generate_recommendations(max_recommendations=3)
        except Exception:
            # No recommendations available
            return decisions

        if not recommendations:
            return decisions

        # Take top recommendation if confidence is high enough
        top_rec = recommendations[0]

        if top_rec.confidence >= schedule.min_confidence:
            # Decide to start this work
            decision = AutopilotDecision(
                decision_id=f"autopilot-{uuid.uuid4().hex[:8]}",
                timestamp=datetime.utcnow().isoformat() + "Z",
                decision_type="start_work",
                action_taken=f"Start work on {top_rec.backlog_item.id}: {top_rec.backlog_item.title}",
                rationale=top_rec.rationale,
                alternatives_considered=[
                    f"#{i+1}: {r.backlog_item.title} (score: {r.score:.1f}, confidence: {r.confidence:.2f})"
                    for i, r in enumerate(recommendations[1:3])
                ] if len(recommendations) > 1 else ["No other options available"],
                confidence=top_rec.confidence,
                can_override=True,
                override_command=f"/pm:pause {top_rec.backlog_item.id}",
                context={
                    "backlog_id": top_rec.backlog_item.id,
                    "score": top_rec.score,
                    "complexity": top_rec.complexity,
                    "blocking_count": top_rec.blocking_count
                }
            )

            if not dry_run:
                # Execute: Start the workstream
                try:
                    ws = self.ws_mgr.start_workstream(
                        backlog_id=top_rec.backlog_item.id,
                        agent="builder"  # Default agent
                    )
                    decision.outcome = "success"
                    decision.context["workstream_id"] = ws.id
                except Exception as e:
                    decision.outcome = "failure"
                    decision.context["error"] = str(e)

            decisions.append(decision)

        return decisions

    def _check_conflicts(
        self,
        active_ws: List[WorkstreamState],
        dry_run: bool
    ) -> List[AutopilotDecision]:
        """Check for conflicts between workstreams.

        Uses coordination analysis to detect overlaps.
        """
        decisions = []

        if len(active_ws) < 2:
            return decisions

        # Use workstream manager to detect conflicts
        from .workstream import WorkstreamMonitor
        monitor = WorkstreamMonitor(self.project_root)

        try:
            analysis = monitor.coordinate_workstreams(active_ws)

            if analysis.conflicts:
                # Decide to escalate conflicts
                decision = AutopilotDecision(
                    decision_id=f"autopilot-{uuid.uuid4().hex[:8]}",
                    timestamp=datetime.utcnow().isoformat() + "Z",
                    decision_type="escalate_conflict",
                    action_taken=f"Escalate {len(analysis.conflicts)} conflicts to human",
                    rationale=f"Detected {len(analysis.conflicts)} potential conflicts between active workstreams. Requires human judgment.",
                    alternatives_considered=[
                        "Auto-pause lower priority work (risky, may pause wrong item)",
                        "Continue and hope for best (risky, could cause problems)",
                        "Escalate to human (conservative, ensures proper resolution)"
                    ],
                    confidence=0.9,
                    can_override=False,
                    override_command="",
                    context={"conflicts": analysis.conflicts[:3]}  # Top 3 conflicts
                )

                if not dry_run:
                    decision.outcome = "success"

                decisions.append(decision)
        except Exception:
            # Coordination analysis failed, skip
            pass

        return decisions

    def explain_decision(self, decision_id: str) -> Optional[AutopilotDecision]:
        """Get detailed explanation of a decision.

        Args:
            decision_id: ID of decision to explain

        Returns:
            AutopilotDecision object or None if not found
        """
        decisions = self._load_decisions()
        return next(
            (d for d in decisions if d.decision_id == decision_id),
            None
        )

    def get_recent_decisions(self, hours: int = 24) -> List[AutopilotDecision]:
        """Get recent decisions within time window.

        Args:
            hours: How many hours back to look

        Returns:
            List of decisions sorted by timestamp (newest first)
        """
        decisions = self._load_decisions()
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        recent = []
        for d in decisions:
            try:
                ts = datetime.fromisoformat(d.timestamp.replace("Z", "+00:00"))
                if ts.replace(tzinfo=None) >= cutoff:
                    recent.append(d)
            except (ValueError, AttributeError):
                continue

        # Sort by timestamp, newest first
        recent.sort(
            key=lambda d: d.timestamp,
            reverse=True
        )

        return recent

    # =========================================================================
    # Private Helpers - State Management
    # =========================================================================

    def _load_schedule(self) -> AutonomousSchedule:
        """Load autopilot schedule from file."""
        schedule_file = self.project_root / ".pm" / "logs" / "autopilot_schedule.yaml"

        if not schedule_file.exists():
            # Create default schedule
            schedule = AutonomousSchedule()
            self._save_schedule(schedule)
            return schedule

        import yaml
        with open(schedule_file) as f:
            data = yaml.safe_load(f) or {}

        return AutonomousSchedule.from_dict(data)

    def _save_schedule(self, schedule: AutonomousSchedule) -> None:
        """Save autopilot schedule to file."""
        schedule_file = self.project_root / ".pm" / "logs" / "autopilot_schedule.yaml"
        schedule_file.parent.mkdir(parents=True, exist_ok=True)

        import yaml
        with open(schedule_file, "w") as f:
            yaml.dump(schedule.to_dict(), f, default_flow_style=False)

    def _load_decisions(self) -> List[AutopilotDecision]:
        """Load decision log from file."""
        if not self.decisions_file.exists():
            return []

        import yaml
        with open(self.decisions_file) as f:
            data = yaml.safe_load(f) or {}

        decision_list = data.get("decisions", [])
        return [AutopilotDecision.from_dict(d) for d in decision_list]

    def _log_decisions(self, decisions: List[AutopilotDecision]) -> None:
        """Append decisions to log file."""
        if not decisions:
            return

        # Load existing decisions
        existing = self._load_decisions()

        # Append new decisions
        all_decisions = existing + decisions

        # Keep only last 1000 decisions
        if len(all_decisions) > 1000:
            all_decisions = all_decisions[-1000:]

        # Save
        self.decisions_file.parent.mkdir(parents=True, exist_ok=True)

        import yaml
        with open(self.decisions_file, "w") as f:
            yaml.dump(
                {"decisions": [d.to_dict() for d in all_decisions]},
                f,
                default_flow_style=False
            )
