"""PR triage validator - main orchestration."""

import time
from pathlib import Path
from typing import Any, Dict

from . import analyzers, github_client
from .claude_runner import run_claude
from .report_generator import generate_triage_report

REPO_ROOT = Path(__file__).parent.parent.parent.parent


class PRTriageValidator:
    """Validates PR compliance using Claude CLI."""

    def __init__(self, pr_number: int):
        """Initialize validator.

        Args:
            pr_number: GitHub PR number
        """
        self.pr_number = pr_number
        self.log_dir = REPO_ROOT / ".claude" / "runtime" / "logs" / f"pr-triage-{pr_number}"
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def log(self, msg: str, level: str = "INFO") -> None:
        """Log message to console and file.

        Args:
            msg: Message to log
            level: Log level
        """
        log_msg = f"[{time.strftime('%H:%M:%S')}] [{level}] [PR-{self.pr_number}] {msg}"
        print(log_msg)

        log_file = self.log_dir / "triage.log"
        with open(log_file, "a") as f:
            f.write(log_msg + "\n")

    def get_pr_data(self) -> Dict[str, Any]:
        """Fetch PR data using gh CLI."""
        return github_client.get_pr_data(self.pr_number)

    def validate_workflow_compliance(self, pr_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check if PR completed Steps 11-12 of workflow."""
        return analyzers.validate_workflow_compliance(pr_data)

    def detect_priority_complexity(self, pr_data: Dict[str, Any]) -> Dict[str, str]:
        """Detect appropriate priority and complexity labels."""
        return analyzers.detect_priority_complexity(pr_data)

    def detect_unrelated_changes(self, pr_data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect if PR contains unrelated changes."""
        return analyzers.detect_unrelated_changes(pr_data)

    def generate_triage_report(
        self,
        pr_data: Dict[str, Any],
        compliance: Dict[str, Any],
        labels: Dict[str, str],
        unrelated: Dict[str, Any],
    ) -> str:
        """Generate comprehensive triage report."""
        return generate_triage_report(self.pr_number, pr_data, compliance, labels, unrelated)

    def apply_labels(self, labels: Dict[str, str]) -> None:
        """Apply priority and complexity labels to PR."""
        priority = labels.get("priority", "MEDIUM")
        complexity = labels.get("complexity", "MODERATE")

        label_names = [
            f"priority:{priority.lower()}",
            f"complexity:{complexity.lower()}",
        ]

        try:
            github_client.apply_labels(self.pr_number, label_names)
        except Exception as e:
            self.log(f"Warning: Failed to apply labels: {e}", level="WARNING")

    def return_to_draft(self) -> None:
        """Convert PR back to draft status."""
        try:
            github_client.return_to_draft(self.pr_number)
            self.log(f"Returned PR #{self.pr_number} to draft status")
        except Exception as e:
            self.log(f"Warning: Failed to return to draft: {e}", level="WARNING")

    def spawn_auto_fix(self, compliance: Dict[str, Any]) -> None:
        """Spawn auto mode to fix workflow compliance issues."""
        issues = compliance.get("blocking_issues", [])
        if not issues:
            return

        fix_prompt = f"""Fix workflow compliance issues in PR #{self.pr_number}.

**Blocking Issues:**
{chr(10).join(f"- {issue}" for issue in issues)}

**Required Actions:**
1. Complete Step 11 (Review the PR):
   - Post comprehensive code review
   - Perform security review
   - Verify code quality and standards
   - Check philosophy compliance
   - Verify test coverage

2. Complete Step 12 (Implement Review Feedback):
   - Address all review comments
   - Push updates to PR
   - Respond to comments
   - Ensure tests still pass

Follow the DEFAULT_WORKFLOW.md process exactly.
"""

        self.log("Spawning auto mode to fix compliance issues...")

        result = run_claude(fix_prompt, timeout=1800)

        if result["exit_code"] == 0:
            self.log("Auto-fix completed successfully")
        else:
            self.log(f"Auto-fix failed: {result['stderr']}", level="ERROR")

    def post_report(self, report: str) -> None:
        """Post triage report as PR comment."""
        report_file = self.log_dir / "triage_report.md"
        report_file.write_text(report)

        try:
            github_client.post_comment(self.pr_number, str(report_file))
            self.log(f"Posted triage report to PR #{self.pr_number}")
        except Exception as e:
            self.log(f"Error posting report: {e}", level="ERROR")
