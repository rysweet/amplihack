#!/usr/bin/env python3
"""
Pre-push git hook for quality gate enforcement.
Prevents commits made with --no-verify from reaching remote by detecting quality violations.
"""

import os
import subprocess
import sys
from pathlib import Path

# Add .claude directory to path for imports
# pre_push.py is at: .claude/tools/amplihack/hooks/pre_push.py
_hook_dir = Path(__file__).parent  # .claude/tools/amplihack/hooks
_tools_dir = _hook_dir.parent  # .claude/tools/amplihack
_claude_tools_dir = _tools_dir.parent  # .claude/tools
_claude_dir = _claude_tools_dir.parent  # .claude
sys.path.insert(0, str(_claude_dir))

from tools.amplihack.hooks.hook_processor import HookProcessor  # noqa: E402
from tools.amplihack.hooks.quality_checker import QualityChecker  # noqa: E402


class PrePushHook(HookProcessor):
    """Pre-push hook that enforces quality checks on pushed commits."""

    def __init__(self):
        """Initialize the pre-push hook processor."""
        super().__init__("pre_push")
        self.quality_checker = QualityChecker(self.project_root)

    def read_push_refs(self) -> list[tuple[str, str, str, str]]:
        """Read push references from stdin.

        Git pre-push hook receives lines in format:
        <local ref> <local sha> <remote ref> <remote sha>

        Returns:
            List of tuples (local_ref, local_sha, remote_ref, remote_sha)
        """
        refs = []
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            parts = line.split()
            if len(parts) >= 4:
                refs.append((parts[0], parts[1], parts[2], parts[3]))

        return refs

    def check_emergency_override(self) -> bool:
        """Check if emergency override is enabled.

        Returns:
            True if FORCE_PUSH_UNVERIFIED=1 is set
        """
        return os.getenv("FORCE_PUSH_UNVERIFIED", "0") == "1"

    def process(self, input_data: dict) -> dict:
        """Process pre-push hook.

        This is NOT a Claude Code hook - it's a Git hook.
        Git hooks don't use JSON stdin/stdout, they use plain text.

        Args:
            input_data: Ignored for Git hooks (they don't use JSON)

        Returns:
            Empty dict (Git hooks communicate via exit code)
        """
        try:
            self.log("Pre-push hook starting")

            # Check for emergency override
            if self.check_emergency_override():
                self.log("FORCE_PUSH_UNVERIFIED=1 detected - bypassing quality checks", "WARNING")
                print("\n⚠️  WARNING: Quality checks bypassed by FORCE_PUSH_UNVERIFIED", file=sys.stderr)
                print("This should only be used in emergencies!\n", file=sys.stderr)
                return {}

            # Read push refs from stdin (Git pre-push format)
            push_refs = self.read_push_refs()

            if not push_refs:
                self.log("No refs to push - allowing push")
                return {}

            self.log(f"Checking {len(push_refs)} ref(s)")

            # Check each ref being pushed
            all_violations = []
            for local_ref, local_sha, remote_ref, remote_sha in push_refs:
                self.log(f"Checking {local_ref}: {remote_sha[:8]}..{local_sha[:8]}")

                # Run quality checks
                results = self.quality_checker.check_commits(local_sha, remote_sha)

                # Log results
                for result in results:
                    self.log(
                        f"  {result.checker_name}: {len(result.violations)} violations "
                        f"({result.execution_time:.2f}s)"
                    )

                # Collect violations
                violations = self.quality_checker.aggregate_violations(results)
                all_violations.extend(violations)

                # Log violations to metrics
                if violations:
                    self.save_metric(
                        "pre_push_violations",
                        len(violations),
                        metadata={
                            "local_ref": local_ref,
                            "local_sha": local_sha,
                            "remote_ref": remote_ref,
                            "remote_sha": remote_sha,
                            "violations": [v.to_dict() for v in violations],
                        },
                    )

            # If we found violations, block the push
            if all_violations:
                self.log(f"BLOCKING PUSH: {len(all_violations)} quality violations found", "ERROR")

                # Format and display violations
                report = self.quality_checker.format_violations_report(results)
                print("\n" + report, file=sys.stderr)

                # Exit with error code to block push
                sys.exit(1)

            # All checks passed
            self.log("All quality checks passed - allowing push")
            print("\n✅ Quality checks passed", file=sys.stderr)
            return {}

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            # Non-blocking errors - allow push with warning
            self.log(f"Checker error (non-blocking): {e}", "WARNING")
            print(f"\n⚠️  Pre-push hook warning: {e}", file=sys.stderr)
            print("Allowing push to proceed (non-critical checker error)\n", file=sys.stderr)
            return {}
        except Exception as e:
            # Unexpected errors - block push for safety (fail-closed)
            self.log(f"CRITICAL: Pre-push hook failed: {e}", "ERROR")
            print(f"\n❌ Pre-push hook failed: {e}", file=sys.stderr)
            print("Blocking push for safety - fix the issue or use FORCE_PUSH_UNVERIFIED=1", file=sys.stderr)
            sys.exit(1)


def main():
    """Entry point for pre-push hook."""
    hook = PrePushHook()
    hook.run()


if __name__ == "__main__":
    main()
