"""Main parallel orchestrator coordinating all components.

Orchestrates parallel agent execution from issue parsing through PR creation.

Philosophy:
- Coordinate existing components, don't reinvent
- File-based communication via status files
- Graceful degradation on partial failures
- Clear progress tracking and reporting

Public API:
    ParallelOrchestrator: Main orchestration class
"""

import json
import logging
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

from ..models.orchestration import OrchestrationConfig
from ..models.agent_status import AgentState
from ..models.completion import OrchestrationReport
from .issue_parser import GitHubIssueParser
from .agent_deployer import AgentDeployer
from .status_monitor import StatusMonitor
from .pr_creator import PRCreator

logger = logging.getLogger(__name__)


class ParallelOrchestrator:
    """Main orchestrator coordinating parallel agent execution.

    Coordinates:
    1. Issue parsing and config creation
    2. Agent deployment to worktrees
    3. Status monitoring and progress tracking
    4. PR creation for completed work
    5. Final report generation
    """

    def __init__(
        self,
        worktree_base: Optional[Path] = None,
        timeout_minutes: int = 120,
        status_poll_interval: int = 30,
        cleanup_on_completion: bool = False,
        post_summary: bool = False,
        log_file: Optional[Path] = None
    ):
        """Initialize parallel orchestrator.

        Args:
            worktree_base: Base directory for worktrees
            timeout_minutes: Timeout per agent in minutes
            status_poll_interval: Status polling interval in seconds
            cleanup_on_completion: Clean up worktrees when done
            post_summary: Post summary comment to parent issue
            log_file: Optional log file path
        """
        self.worktree_base = Path(worktree_base) if worktree_base else Path("./worktrees")
        self.timeout_minutes = timeout_minutes
        self.status_poll_interval = status_poll_interval
        self.cleanup_on_completion = cleanup_on_completion
        self.post_summary = post_summary
        self.log_file = log_file

        # Initialize components
        self.issue_parser = GitHubIssueParser()
        self.agent_deployer = AgentDeployer(worktree_base=self.worktree_base)
        self.status_monitor = StatusMonitor(
            worktree_base=self.worktree_base,
            timeout_minutes=timeout_minutes,
            status_poll_interval=status_poll_interval
        )
        self.pr_creator = PRCreator()

        # Track current orchestration state
        self.current_config: Optional[OrchestrationConfig] = None
        self.current_deployments: List[Dict[str, Any]] = []
        self.start_time: Optional[float] = None

    @classmethod
    def from_config_file(cls, config_file: Path) -> "ParallelOrchestrator":
        """Create orchestrator from configuration file.

        Args:
            config_file: Path to JSON config file

        Returns:
            ParallelOrchestrator instance configured from file
        """
        config_data = json.loads(config_file.read_text())
        config = OrchestrationConfig.from_dict(config_data)

        return cls(
            worktree_base=Path(config.worktree_base),
            timeout_minutes=config.timeout_minutes,
            status_poll_interval=config.status_poll_interval
        )

    def orchestrate(
        self,
        parent_issue: int,
        parallel_degree: int = 3,
        timeout_minutes: Optional[int] = None,
        recovery_strategy: str = "continue_on_failure"
    ) -> Dict[str, Any]:
        """Execute complete orchestration workflow.

        Args:
            parent_issue: Parent issue number
            parallel_degree: Maximum parallel agents
            timeout_minutes: Override default timeout
            recovery_strategy: Recovery strategy on failures

        Returns:
            Orchestration result dict with success status and report

        Raises:
            RuntimeError: If orchestration fails critically
        """
        self.start_time = time.time()

        try:
            # Step 1: Fetch issue body and parse sub-issues
            logger.info(f"Fetching parent issue #{parent_issue}")
            issue_body = self.issue_parser.fetch_issue_body(parent_issue)
            sub_issues = self.issue_parser.parse_sub_issues(issue_body)

            if not sub_issues:
                raise ValueError(f"No sub-issues found in issue #{parent_issue}")

            # Step 2: Create orchestration config
            self.current_config = OrchestrationConfig(
                parent_issue=parent_issue,
                sub_issues=sub_issues,
                parallel_degree=parallel_degree,
                timeout_minutes=timeout_minutes or self.timeout_minutes,
                recovery_strategy=recovery_strategy,
                worktree_base=str(self.worktree_base),
                status_poll_interval=self.status_poll_interval
            )

            logger.info(f"Orchestrating {len(sub_issues)} sub-issues with parallel_degree={parallel_degree}")

            # Step 3: Deploy agents to worktrees
            deployments = self._deploy_agents()
            self.current_deployments = deployments

            logger.info(f"Deployed {len(deployments)} agents")

            # Step 4: Monitor agent progress
            final_statuses = self._monitor_agents()

            # Step 5: Create PRs for completed agents
            pr_results = self._create_prs(final_statuses)

            # Step 6: Generate final report
            report = self._generate_report(final_statuses, pr_results)

            # Optional: Cleanup worktrees
            if self.cleanup_on_completion:
                self._cleanup_worktrees()

            # Optional: Post summary to parent issue
            if self.post_summary:
                self._post_summary_comment(report)

            return {
                "success": report.failed == 0,
                "total_sub_issues": report.total_sub_issues,
                "completed": report.completed,
                "failed": report.failed,
                "success_rate": report.calculate_success_rate(),
                "report": report.to_dict(),
                "pr_links": report.pr_links,
                "cleanup_complete": self.cleanup_on_completion,
                "summary_posted": self.post_summary,
                "log_path": str(self.log_file) if self.log_file else None
            }

        except KeyboardInterrupt:
            logger.warning("Orchestration interrupted by user")
            # Preserve partial progress
            raise
        except Exception as e:
            logger.error(f"Orchestration failed: {e}", exc_info=True)
            raise RuntimeError(f"Orchestration failed: {e}")

    def orchestrate_from_config(self) -> Dict[str, Any]:
        """Execute orchestration using current config.

        Returns:
            Orchestration result dict

        Raises:
            RuntimeError: If no config loaded
        """
        if not self.current_config:
            raise RuntimeError("No configuration loaded. Use from_config_file() first.")

        return self.orchestrate(
            parent_issue=self.current_config.parent_issue,
            parallel_degree=self.current_config.parallel_degree,
            timeout_minutes=self.current_config.timeout_minutes,
            recovery_strategy=self.current_config.recovery_strategy
        )

    def get_current_status(self) -> Dict[str, Any]:
        """Get current orchestration status.

        Returns:
            Status dict with current progress
        """
        if not self.current_config:
            return {"status": "not_started"}

        statuses = self.status_monitor.poll_all_agents()

        return {
            "total": len(self.current_config.sub_issues),
            "agents": len(statuses),
            "completed": len(self.status_monitor.filter_by_status(statuses, AgentState.COMPLETED.value)),
            "failed": len(self.status_monitor.filter_by_status(statuses, AgentState.FAILED.value)),
            "in_progress": len(self.status_monitor.filter_by_status(statuses, AgentState.IN_PROGRESS.value)),
            "overall_progress": self.status_monitor.calculate_overall_progress(statuses),
            "elapsed_seconds": time.time() - self.start_time if self.start_time else 0
        }

    def _deploy_agents(self) -> List[Dict[str, Any]]:
        """Deploy agents for all sub-issues.

        Returns:
            List of deployment result dicts
        """
        if not self.current_config:
            raise RuntimeError("No configuration set")

        issues = [
            {"number": issue_num, "title": f"Issue {issue_num}"}
            for issue_num in self.current_config.sub_issues
        ]

        return self.agent_deployer.deploy_batch(
            issues=issues,
            parent_issue=self.current_config.parent_issue
        )

    def _monitor_agents(self) -> List[Dict[str, Any]]:
        """Monitor agents until completion or timeout.

        Returns:
            List of final agent status dicts
        """
        if not self.current_config:
            raise RuntimeError("No configuration set")

        logger.info("Monitoring agent progress...")

        # Extract agent IDs from deployments
        agent_ids = [d.get("agent_id") for d in self.current_deployments if "agent_id" in d]

        try:
            # Wait for completion with configured timeout
            result = self.status_monitor.wait_for_completion(
                agent_ids=agent_ids if agent_ids else None,
                timeout_seconds=self.current_config.timeout_minutes * 60,
                poll_interval=self.current_config.status_poll_interval
            )

            logger.info(f"Monitoring complete after {result['duration']:.1f}s")
            return result["statuses"]

        except TimeoutError as e:
            logger.warning(f"Monitoring timeout: {e}")
            # Return whatever statuses we have
            return self.status_monitor.poll_all_agents()

    def monitor_agents(self) -> List[Dict[str, Any]]:
        """Public alias for _monitor_agents for testing."""
        return self._monitor_agents()

    def _create_prs(self, statuses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create PRs for completed agents.

        Args:
            statuses: List of agent status dicts

        Returns:
            List of PR creation results
        """
        if not self.current_config:
            raise RuntimeError("No configuration set")

        # Filter to completed agents only
        completed = self.status_monitor.filter_by_status(statuses, AgentState.COMPLETED.value)

        if not completed:
            logger.info("No completed agents - skipping PR creation")
            return []

        logger.info(f"Creating PRs for {len(completed)} completed agents")

        # Build agent info for PR creation
        agents = []
        for status in completed:
            issue_num = status.get("issue_number")
            branch_name = status.get("branch_name") or f"feat/issue-{issue_num}"

            agents.append({
                "issue_number": issue_num,
                "issue_title": f"Issue {issue_num}",
                "branch_name": branch_name,
                "summary": "Implementation completed by automated agent"
            })

        return self.pr_creator.create_batch(
            agents=agents,
            parent_issue=self.current_config.parent_issue
        )

    def _generate_report(
        self,
        statuses: List[Dict[str, Any]],
        pr_results: List[Dict[str, Any]]
    ) -> OrchestrationReport:
        """Generate final orchestration report.

        Args:
            statuses: Final agent status dicts
            pr_results: PR creation results

        Returns:
            OrchestrationReport instance
        """
        if not self.current_config:
            raise RuntimeError("No configuration set")

        # Count outcomes
        completed = self.status_monitor.filter_by_status(statuses, AgentState.COMPLETED.value)
        failed = self.status_monitor.filter_by_status(statuses, AgentState.FAILED.value)

        # Extract PR links
        pr_links = [
            pr.get("pr_url", "")
            for pr in pr_results
            if pr.get("success")
        ]

        # Extract failure details
        failures = []
        for status in failed:
            failures.append({
                "issue_number": status.get("issue_number"),
                "error": self.status_monitor.extract_error_details(status) or "Unknown error",
                "status": status.get("status")
            })

        # Calculate duration
        duration = time.time() - self.start_time if self.start_time else 0

        return OrchestrationReport(
            parent_issue=self.current_config.parent_issue,
            total_sub_issues=len(self.current_config.sub_issues),
            completed=len(completed),
            failed=len(failed),
            duration_seconds=duration,
            pr_links=pr_links,
            failures=failures
        )

    def _cleanup_worktrees(self) -> None:
        """Clean up worktrees after orchestration."""
        logger.info("Cleaning up worktrees...")

        for deployment in self.current_deployments:
            worktree_path = deployment.get("worktree_path")
            if worktree_path:
                self.agent_deployer.cleanup_worktree(Path(worktree_path))

    def _post_summary_comment(self, report: OrchestrationReport) -> None:
        """Post summary comment to parent issue.

        Args:
            report: Orchestration report to post
        """
        if not self.current_config:
            return

        logger.info(f"Posting summary to issue #{self.current_config.parent_issue}")

        summary = report.generate_summary()

        # Post summary as issue comment via gh CLI
        try:
            result = subprocess.run(
                [
                    "gh",
                    "issue",
                    "comment",
                    str(self.current_config.parent_issue),
                    "--body",
                    summary,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                logger.info(f"Successfully posted summary to issue #{self.current_config.parent_issue}")
            else:
                logger.warning(f"Failed to post issue comment: {result.stderr}")
                logger.info(f"Summary:\n{summary}")  # Fallback to logging
        except subprocess.TimeoutExpired:
            logger.warning("Timeout posting issue comment - falling back to logging")
            logger.info(f"Summary:\n{summary}")
        except Exception as e:
            logger.warning(f"Error posting issue comment: {e} - falling back to logging")
            logger.info(f"Summary:\n{summary}")


__all__ = ["ParallelOrchestrator"]
