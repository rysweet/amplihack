"""PR triage validator - main orchestration."""

import os
import time
from pathlib import Path
from typing import Any

from . import github_client, security
from .report_generator import generate_triage_report

# Use MVP analyzers (heuristic-based) by default
# Can switch to Claude-based analyzers by setting USE_CLAUDE_ANALYZERS=1
USE_CLAUDE = os.environ.get("USE_CLAUDE_ANALYZERS", "0") == "1"

if USE_CLAUDE:
    from . import analyzers
else:
    from . import analyzers_mvp as analyzers

REPO_ROOT = Path(__file__).parent.parent.parent.parent


class PRTriageValidator:
    """Validates PR compliance using heuristic analysis or Claude CLI."""

    def __init__(self, pr_number: int):
        """Initialize validator.

        Args:
            pr_number: GitHub PR number

        Raises:
            ValueError: If PR number is invalid
        """
        # Security validation
        security.validate_pr_number(pr_number)

        self.pr_number = pr_number
        self.log_dir = REPO_ROOT / ".claude" / "runtime" / "logs" / f"pr-triage-{pr_number}"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Audit log file
        self.audit_log = self.log_dir / "audit.log"

    def log(self, msg: str, level: str = "INFO") -> None:
        """Log message to console and file.

        Args:
            msg: Message to log
            level: Log level
        """
        # Sanitize log message
        msg = security.sanitize_markdown(msg)

        log_msg = f"[{time.strftime('%H:%M:%S')}] [{level}] [PR-{self.pr_number}] {msg}"
        print(log_msg)

        log_file = self.log_dir / "triage.log"
        with open(log_file, "a") as f:
            f.write(log_msg + "\n")

    def audit(self, operation: str, result: str, details: dict[str, Any] = None) -> None:
        """Write audit log entry.

        Args:
            operation: Operation name
            result: Result status
            details: Additional details
        """
        entry = security.create_audit_log(self.pr_number, operation, result, details)
        with open(self.audit_log, "a") as f:
            f.write(entry + "\n")

    def get_pr_data(self) -> dict[str, Any]:
        """Fetch PR data using gh CLI.

        Returns:
            PR data dictionary

        Raises:
            ValueError: If PR data is invalid
        """
        self.audit("get_pr_data", "started")

        try:
            pr_data = github_client.get_pr_data(self.pr_number)

            # Security validation
            security.validate_pr_data(pr_data)
            security.validate_file_paths(pr_data.get("files", []))

            # Sanitize text fields
            pr_data["title"] = security.sanitize_markdown(pr_data.get("title", ""))
            pr_data["body"] = security.sanitize_markdown(pr_data.get("body", ""))

            self.audit("get_pr_data", "success", {"num_files": len(pr_data.get("files", []))})
            return pr_data

        except Exception as e:
            self.audit("get_pr_data", "failed", {"error": str(e)})
            raise

    def validate_workflow_compliance(self, pr_data: dict[str, Any]) -> dict[str, Any]:
        """Check if PR completed Steps 11-12 of workflow."""
        return analyzers.validate_workflow_compliance(pr_data)

    def detect_priority_complexity(self, pr_data: dict[str, Any]) -> dict[str, str]:
        """Detect appropriate priority and complexity labels."""
        return analyzers.detect_priority_complexity(pr_data)

    def detect_unrelated_changes(self, pr_data: dict[str, Any]) -> dict[str, Any]:
        """Detect if PR contains unrelated changes."""
        return analyzers.detect_unrelated_changes(pr_data)

    def generate_triage_report(
        self,
        pr_data: dict[str, Any],
        compliance: dict[str, Any],
        labels: dict[str, str],
        unrelated: dict[str, Any],
    ) -> str:
        """Generate comprehensive triage report."""
        return generate_triage_report(self.pr_number, pr_data, compliance, labels, unrelated)

    def apply_labels(self, labels: dict[str, str]) -> None:
        """Apply priority and complexity labels to PR.

        Args:
            labels: Dictionary with priority and complexity labels

        Raises:
            ValueError: If labels are invalid
        """
        priority = labels.get("priority", "MEDIUM")
        complexity = labels.get("complexity", "MODERATE")

        label_names = [
            f"priority:{priority.lower()}",
            f"complexity:{complexity.lower()}",
        ]

        # Security validation
        security.validate_allowed_labels(label_names)

        self.audit("apply_labels", "started", {"labels": label_names})

        try:
            github_client.apply_labels(self.pr_number, label_names)
            self.audit("apply_labels", "success", {"labels": label_names})
        except Exception as e:
            self.audit("apply_labels", "failed", {"error": str(e)})
            self.log(f"Warning: Failed to apply labels: {e}", level="WARNING")

    def return_to_draft(self) -> None:
        """Convert PR back to draft status."""
        self.audit("return_to_draft", "started")

        try:
            github_client.return_to_draft(self.pr_number)
            self.log(f"Returned PR #{self.pr_number} to draft status")
            self.audit("return_to_draft", "success")
        except Exception as e:
            self.audit("return_to_draft", "failed", {"error": str(e)})
            self.log(f"Warning: Failed to return to draft: {e}", level="WARNING")

    def post_report(self, report: str) -> None:
        """Post triage report as PR comment.

        Args:
            report: Markdown report to post
        """
        # Sanitize report content
        report = security.sanitize_markdown(report)

        report_file = self.log_dir / "triage_report.md"
        report_file.write_text(report)

        self.audit("post_report", "started", {"report_length": len(report)})

        try:
            github_client.post_comment(self.pr_number, str(report_file))
            self.log(f"Posted triage report to PR #{self.pr_number}")
            self.audit("post_report", "success")
        except Exception as e:
            self.audit("post_report", "failed", {"error": str(e)})
            self.log(f"Error posting report: {e}", level="ERROR")
