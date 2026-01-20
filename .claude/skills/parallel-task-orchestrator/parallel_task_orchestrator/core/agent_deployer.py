"""Agent deployment and worktree management.

Deploys agents to isolated git worktrees with proper initialization.

Philosophy:
- File-based agent isolation via git worktrees
- Simple prompt templates
- Status file protocol
- Safe subprocess handling

Public API:
    AgentDeployer: Main deployment class
"""

import json
import logging
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class AgentDeployer:
    """Deploys agents to git worktrees for parallel task execution.

    Each agent gets:
    - Isolated git worktree
    - Initial .agent_status.json file
    - Agent prompt with contract
    """

    def __init__(
        self,
        worktree_base: Optional[Path] = None,
        max_parallel: int = 5
    ):
        """Initialize agent deployer.

        Args:
            worktree_base: Base directory for worktrees
            max_parallel: Maximum parallel agents
        """
        self.worktree_base = Path(worktree_base) if worktree_base else Path("./worktrees")
        self.max_parallel = max_parallel

    def generate_prompt(
        self,
        issue_number: int,
        issue_title: str,
        parent_issue: int,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate agent prompt for sub-issue.

        Args:
            issue_number: Sub-issue number
            issue_title: Sub-issue title
            parent_issue: Parent orchestration issue
            context: Additional context (dependencies, etc.)

        Returns:
            Agent prompt string
        """
        prompt = f"""# Agent Task: Issue #{issue_number}

## Task
{issue_title}

## Parent Issue
This task is part of the larger orchestration in issue #{parent_issue}.

## Your Responsibilities
1. Implement the feature/fix described in issue #{issue_number}
2. Create comprehensive tests
3. Update documentation
4. Ensure code quality and philosophy compliance
5. Update .agent_status.json regularly with progress

## Status Updates
Update .agent_status.json in your worktree directory with:
- status: "pending", "in_progress", "completed", or "failed"
- completion_percentage: 0-100
- last_update: ISO timestamp
- errors: List of any errors encountered

## Expected Outputs
- Working implementation
- Tests passing
- Documentation updated
- PR ready for review
"""

        if context:
            prompt += "\n## Additional Context\n"
            if "dependencies" in context:
                prompt += f"- Dependencies: Issues {', '.join(map(str, context['dependencies']))}\n"
            if "priority" in context:
                prompt += f"- Priority: {context['priority']}\n"
            if "estimated_hours" in context:
                prompt += f"- Estimated effort: {context['estimated_hours']} hours\n"

        return prompt

    def generate_contract(
        self,
        issue_number: int,
        issue_title: str
    ) -> str:
        """Generate agent contract specification.

        Args:
            issue_number: Issue number
            issue_title: Issue title

        Returns:
            Contract specification string
        """
        contract = f"""# Agent Contract: Issue #{issue_number}

## deliverables
- Functional implementation of: {issue_title}
- Test coverage (unit + integration)
- Updated documentation
- Clean git history with conventional commits

## status_updates Required
Regular updates to .agent_status.json:
- Every major milestone
- When blocked or encountering errors
- At least every 30 minutes during active work

## outputs
- Code changes committed to feature branch
- Tests passing locally
- PR description with testing evidence
"""
        return contract

    def generate_agent_id(self, issue_number: int) -> str:
        """Generate unique agent ID for issue.

        Args:
            issue_number: Issue number

        Returns:
            Agent ID string
        """
        return f"agent-{issue_number}"

    def get_worktree_path(self, issue_number: int) -> Path:
        """Get worktree path for issue.

        Args:
            issue_number: Issue number

        Returns:
            Path to worktree directory
        """
        return self.worktree_base / f"feat-issue-{issue_number}"

    def get_status_file_path(self, agent_id: str) -> Path:
        """Get status file path for agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Path to .agent_status.json
        """
        # Extract issue number from agent_id
        issue_num = agent_id.replace("agent-", "")
        worktree = self.worktree_base / f"feat-issue-{issue_num}"
        return worktree / ".agent_status.json"

    def initialize_status_file(
        self,
        status_file: Path,
        agent_id: str,
        issue_number: int
    ) -> None:
        """Initialize agent status file.

        Args:
            status_file: Path to status file
            agent_id: Agent identifier
            issue_number: Issue number
        """
        initial_status = {
            "agent_id": agent_id,
            "issue_number": issue_number,
            "status": "pending",
            "completion_percentage": 0,
            "last_update": datetime.now().isoformat(),
            "errors": []
        }

        status_file.parent.mkdir(parents=True, exist_ok=True)
        status_file.write_text(json.dumps(initial_status, indent=2))

    def validate_prerequisites(self) -> Dict[str, bool]:
        """Validate deployment prerequisites.

        Returns:
            Dict with validation results for each tool
        """
        tools = ["git", "gh"]
        results = {}

        for tool in tools:
            try:
                result = subprocess.run(
                    [tool, "--version"],
                    capture_output=True,
                    timeout=5
                )
                results[tool] = result.returncode == 0
            except (FileNotFoundError, subprocess.TimeoutExpired):
                results[tool] = False

        return results

    def create_worktree(
        self,
        issue_number: int,
        branch_name: str
    ) -> Path:
        """Create git worktree for agent.

        Args:
            issue_number: Issue number
            branch_name: Branch name for worktree

        Returns:
            Path to created worktree

        Raises:
            RuntimeError: If worktree creation fails
        """
        worktree_path = self.get_worktree_path(issue_number)

        try:
            result = subprocess.run(
                ["git", "worktree", "add", "-b", branch_name, str(worktree_path)],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                if "already exists" in result.stderr:
                    raise RuntimeError(f"Worktree already exists: {worktree_path}")
                raise RuntimeError(f"Worktree creation failed: {result.stderr}")

            return worktree_path

        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Worktree creation timed out for issue {issue_number}")
        except Exception as e:
            raise RuntimeError(f"Worktree creation failed: {e}")

    def cleanup_worktree(self, worktree_path: Path) -> None:
        """Cleanup git worktree.

        Args:
            worktree_path: Path to worktree to remove
        """
        try:
            subprocess.run(
                ["git", "worktree", "remove", str(worktree_path), "--force"],
                capture_output=True,
                timeout=30
            )
        except Exception as e:
            # Best effort cleanup
            logger.debug(f"Worktree cleanup failed for {worktree_path}: {e}", exc_info=True)

    def launch_agent(
        self,
        worktree_path: Path,
        prompt: str
    ) -> None:
        """Launch agent with Claude CLI in worktree.

        Args:
            worktree_path: Path to agent worktree
            prompt: Agent prompt
        """
        # Write prompt to file
        prompt_file = worktree_path / ".agent_prompt.txt"
        prompt_file.write_text(prompt)

        # Launch claude CLI
        try:
            subprocess.run(
                ["claude", "--prompt-file", str(prompt_file)],
                cwd=str(worktree_path),
                capture_output=True,
                timeout=1  # Quick launch, don't wait for completion
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # Expected - claude runs in background or not installed
            pass
        except Exception as e:
            # Non-fatal - agent may be launched manually
            logger.debug(f"Agent launch failed for {worktree_path}: {e}", exc_info=True)

    def deploy_agent(
        self,
        issue_number: int,
        issue_title: str,
        parent_issue: int,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Deploy single agent for issue.

        Args:
            issue_number: Sub-issue number
            issue_title: Sub-issue title
            parent_issue: Parent orchestration issue
            context: Additional context

        Returns:
            Deployment details dict

        Raises:
            RuntimeError: If deployment fails
        """
        try:
            # Generate agent ID
            agent_id = self.generate_agent_id(issue_number)

            # Create worktree
            branch_name = f"feat/issue-{issue_number}"
            worktree_path = self.create_worktree(issue_number, branch_name)

            # Initialize status file
            status_file = worktree_path / ".agent_status.json"
            self.initialize_status_file(status_file, agent_id, issue_number)

            # Generate prompt
            prompt = self.generate_prompt(
                issue_number, issue_title, parent_issue, context
            )

            # Agent launch is intentionally commented out - orchestrator creates worktrees
            # and status files, but agents are expected to be launched manually by users
            # who want control over when/how agents execute
            # Uncomment self.launch_agent(worktree_path, prompt) for automatic launch
            # self.launch_agent(worktree_path, prompt)

            return {
                "agent_id": agent_id,
                "issue_number": issue_number,
                "worktree_path": str(worktree_path),
                "status_file": str(status_file),
                "branch_name": branch_name
            }

        except Exception as e:
            raise RuntimeError(f"Agent deployment failed for issue {issue_number}: {e}")

    def deploy_batch(
        self,
        issues: List[Dict[str, Any]],
        parent_issue: int
    ) -> List[Dict[str, Any]]:
        """Deploy batch of agents.

        Args:
            issues: List of issue dicts with 'number' and 'title'
            parent_issue: Parent orchestration issue

        Returns:
            List of deployment result dicts
        """
        results = []

        for issue in issues:
            try:
                result = self.deploy_agent(
                    issue_number=issue["number"],
                    issue_title=issue["title"],
                    parent_issue=parent_issue
                )
                results.append(result)
            except Exception as e:
                # Continue with other deployments
                results.append({
                    "issue_number": issue["number"],
                    "error": str(e)
                })

        return results


__all__ = ["AgentDeployer"]
