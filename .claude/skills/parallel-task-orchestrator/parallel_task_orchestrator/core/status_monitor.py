"""Agent status monitoring and polling.

Monitors agent status files and detects completion/failures/timeouts.

Philosophy:
- File-based status protocol (.agent_status.json)
- Simple polling mechanism
- Timeout detection based on last_update
- No complex messaging - trust files

Public API:
    StatusMonitor: Main monitoring class
"""

import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional


class StatusMonitor:
    """Monitors agent status files and tracks orchestration progress.

    Uses file-based protocol where each agent writes .agent_status.json
    to its worktree directory.
    """

    def __init__(
        self,
        worktree_base: Optional[Path] = None,
        timeout_minutes: int = 120,
        status_poll_interval: int = 30
    ):
        """Initialize status monitor.

        Args:
            worktree_base: Base directory for worktrees (optional)
            timeout_minutes: Default timeout threshold
            status_poll_interval: Default poll interval in seconds
        """
        self.worktree_base = Path(worktree_base) if worktree_base else Path("./worktrees")
        self.timeout_minutes = timeout_minutes
        self.status_poll_interval = status_poll_interval

    def read_status_file(self, status_file: Path) -> Optional[Dict[str, Any]]:
        """Read agent status from file.

        Args:
            status_file: Path to .agent_status.json

        Returns:
            Status dict or None if file not found

        Raises:
            ValueError: If JSON is invalid
        """
        if not status_file.exists():
            return None

        try:
            content = status_file.read_text()
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {status_file}: {e}")

    def poll_all_agents(self) -> List[Dict[str, Any]]:
        """Poll all agent status files in worktree base.

        Returns:
            List of agent status dicts
        """
        statuses = []

        if not self.worktree_base.exists():
            return statuses

        # Find all .agent_status.json files
        for status_file in self.worktree_base.rglob(".agent_status.json"):
            status = self.read_status_file(status_file)
            if status:
                statuses.append(status)

        return statuses

    def filter_by_status(self, statuses: List[Dict[str, Any]], status: str) -> List[Dict[str, Any]]:
        """Filter agents by status.

        Args:
            statuses: List of agent status dicts
            status: Status to filter by (e.g., "completed", "failed")

        Returns:
            Filtered list of statuses
        """
        return [s for s in statuses if s.get("status") == status]

    def detect_timeout(self, status: Dict[str, Any], timeout_minutes: int = 120) -> bool:
        """Detect if agent has timed out based on last_update.

        Args:
            status: Agent status dict
            timeout_minutes: Timeout threshold in minutes

        Returns:
            True if agent has timed out
        """
        last_update_str = status.get("last_update")
        if not last_update_str:
            return False

        try:
            last_update = datetime.fromisoformat(last_update_str)
            age = datetime.now() - last_update
            return age > timedelta(minutes=timeout_minutes)
        except (ValueError, TypeError):
            return False

    def is_timed_out(self, status: Dict[str, Any]) -> bool:
        """Check if agent status indicates timeout.

        Uses the timeout_minutes configured at initialization.

        Args:
            status: Agent status dict

        Returns:
            True if agent has timed out
        """
        return self.detect_timeout(status, self.timeout_minutes)

    def calculate_overall_progress(self, statuses: List[Dict[str, Any]]) -> float:
        """Calculate overall progress across all agents.

        Args:
            statuses: List of agent status dicts

        Returns:
            Overall progress percentage (0-100)
        """
        if not statuses:
            return 0.0

        total_progress = sum(
            s.get("completion_percentage", 0)
            for s in statuses
        )
        return total_progress / len(statuses)

    def all_agents_completed(self, statuses: List[Dict[str, Any]]) -> bool:
        """Check if all agents have completed.

        Args:
            statuses: List of agent status dicts

        Returns:
            True if all agents are completed or failed
        """
        if not statuses:
            return False

        terminal_states = {"completed", "failed", "timeout"}
        return all(s.get("status") in terminal_states for s in statuses)

    def wait_for_completion(
        self,
        agent_ids: Optional[List[str]] = None,
        timeout_seconds: int = 7200,
        poll_interval: Optional[int] = None
    ) -> Dict[str, Any]:
        """Wait for all agents to complete or timeout.

        Args:
            agent_ids: List of agent IDs to wait for (None = all agents)
            timeout_seconds: Maximum wait time
            poll_interval: Polling interval in seconds (None = use default)

        Returns:
            Dict with completion status and final statuses

        Raises:
            TimeoutError: If overall timeout exceeded
        """
        # Use configured poll interval if not provided
        if poll_interval is None:
            poll_interval = self.status_poll_interval

        start_time = time.time()

        while True:
            # Poll current statuses
            all_statuses = self.poll_all_agents()

            # Filter by agent_ids if specified
            if agent_ids:
                relevant_statuses = [
                    s for s in all_statuses
                    if s.get("agent_id") in agent_ids
                ]
            else:
                relevant_statuses = all_statuses

            # Check if all completed
            if (not agent_ids or len(relevant_statuses) == len(agent_ids)) and self.all_completed(relevant_statuses):
                return {
                    "completed": True,
                    "statuses": relevant_statuses,
                    "duration": time.time() - start_time
                }

            # Check timeout
            if time.time() - start_time > timeout_seconds:
                target_count = len(agent_ids) if agent_ids else len(relevant_statuses)
                raise TimeoutError(
                    f"Orchestration timeout after {timeout_seconds}s. "
                    f"Completed: {len(self.filter_by_status(relevant_statuses, 'completed'))}/{target_count}"
                )

            # Sleep before next poll
            time.sleep(poll_interval)

    def get_agent_log_path(self, agent_id: str) -> Path:
        """Get path to agent's log file.

        Args:
            agent_id: Agent identifier

        Returns:
            Path to agent log file
        """
        return self.worktree_base / agent_id / "agent.log"

    def extract_error_details(self, status: Dict[str, Any]) -> Optional[str]:
        """Extract error details from agent status.

        Args:
            status: Agent status dict

        Returns:
            Error message or None
        """
        errors = status.get("errors", [])
        if errors:
            return "; ".join(errors)
        return None

    def health_check(self, statuses: List[Dict[str, Any]], stall_minutes: int = 30) -> Dict[str, Any]:
        """Perform health check on all agents.

        Detects:
        - Stalled agents (no update in stall_minutes)
        - Failed agents
        - Completed agents

        Args:
            statuses: List of agent status dicts
            stall_minutes: Minutes without update = stalled

        Returns:
            Health check report dict with 'overall' and 'issues' keys
        """
        now = datetime.now()
        stalled = []
        healthy = []
        issues = []
        failed = self.filter_by_status(statuses, "failed")
        completed = self.filter_by_status(statuses, "completed")

        for status in statuses:
            if status.get("status") in {"completed", "failed"}:
                continue

            last_update_str = status.get("last_update")
            if last_update_str:
                try:
                    last_update = datetime.fromisoformat(last_update_str)
                    age = now - last_update
                    if age > timedelta(minutes=stall_minutes):
                        stalled.append(status)
                        agent_id = status.get("agent_id", "unknown")
                        issues.append(f"Agent {agent_id} stalled (no update for {age.total_seconds() / 60:.0f} minutes)")
                    else:
                        healthy.append(status)
                except (ValueError, TypeError):
                    stalled.append(status)
                    issues.append(f"Agent {status.get('agent_id', 'unknown')} has invalid timestamp")

        # Add failed agents to issues
        for fail_status in failed:
            agent_id = fail_status.get("agent_id", "unknown")
            errors = fail_status.get("errors", [])
            error_msg = errors[0] if errors else "Unknown error"
            issues.append(f"Agent {agent_id} failed: {error_msg}")

        # Determine overall health status
        if stalled or failed:
            overall = "degraded"
        else:
            overall = "healthy"

        return {
            "healthy": healthy,
            "stalled": stalled,
            "failed": failed,
            "completed": completed,
            "total": len(statuses),
            "overall": overall,
            "issues": issues,
        }

    def all_completed(self, statuses: List[Dict[str, Any]]) -> bool:
        """Alias for all_agents_completed for backwards compatibility."""
        return self.all_agents_completed(statuses)

    def extract_errors(self, status: Dict[str, Any]) -> List[str]:
        """Extract errors list from agent status.

        Args:
            status: Agent status dict

        Returns:
            List of error messages
        """
        return status.get("errors", [])

    def detect_changes(self, old_statuses: List[Dict[str, Any]], new_statuses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect changes between old and new status lists.

        Args:
            old_statuses: Previous status list
            new_statuses: Current status list

        Returns:
            List of dicts with change information for each changed agent
        """
        changes = []

        # Create lookup by agent_id
        old_by_id = {s.get("agent_id"): s for s in old_statuses}
        new_by_id = {s.get("agent_id"): s for s in new_statuses}

        # Check for status changes
        for agent_id, new_status in new_by_id.items():
            old_status = old_by_id.get(agent_id)
            if not old_status:
                continue

            # Status change detected
            if old_status.get("status") != new_status.get("status"):
                changes.append({
                    "agent_id": agent_id,
                    "old_status": old_status.get("status"),
                    "new_status": new_status.get("status"),
                    "progress": new_status.get("completion_percentage", 0)
                })

        return changes


__all__ = ["StatusMonitor"]
