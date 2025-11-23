#!/usr/bin/env python3
"""Main entry point for PR triage.

This script orchestrates the PR triage process by:
- Fetching PR data
- Running compliance validations
- Generating triage reports
- Applying labels and taking actions
"""

import os
import sys
from pathlib import Path

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from pr_triage import PRTriageValidator


def main():
    """Main entry point for PR triage."""
    # Get PR number from environment
    pr_number = int(os.environ.get("PR_NUMBER", "0"))
    if not pr_number:
        print("Error: PR_NUMBER environment variable not set", file=sys.stderr)
        sys.exit(1)

    # Create validator
    validator = PRTriageValidator(pr_number)

    try:
        # Fetch PR data
        validator.log("Fetching PR data...")
        pr_data = validator.get_pr_data()

        # Run validations
        validator.log("Validating workflow compliance...")
        compliance = validator.validate_workflow_compliance(pr_data)

        validator.log("Detecting priority and complexity...")
        labels = validator.detect_priority_complexity(pr_data)

        validator.log("Checking for unrelated changes...")
        unrelated = validator.detect_unrelated_changes(pr_data)

        # Generate report
        validator.log("Generating triage report...")
        report = validator.generate_triage_report(pr_data, compliance, labels, unrelated)

        # Apply labels
        validator.log("Applying labels...")
        validator.apply_labels(labels)

        # Post report
        validator.log("Posting triage report...")
        validator.post_report(report)

        # Handle non-compliance
        if not compliance.get("overall_compliant"):
            validator.log(
                "PR is non-compliant, returning to draft status...",
                level="WARNING",
            )
            validator.return_to_draft()
            validator.log(
                "NOTE: Auto-fix requires Claude CLI. Set USE_CLAUDE_ANALYZERS=1 to enable.",
                level="INFO",
            )

        validator.log("PR triage completed successfully")

    except Exception as e:
        validator.log(f"Fatal error: {e}", level="ERROR")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
