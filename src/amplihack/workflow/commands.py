"""Workflow enforcement override commands."""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path


class WorkflowCommands:
    """CLI commands for workflow enforcement management."""

    OVERRIDE_FILE = Path.home() / ".amplifier" / "state" / "workflow_override.json"

    @staticmethod
    def override(reason: str, duration: int = 30) -> int:
        """
        Enable workflow enforcement override.

        This allows direct implementation without workflow execution.
        Use only for:
        - Emergency hotfixes
        - Trivial typo corrections
        - Documentation-only changes

        Args:
            reason: Justification for override (minimum 10 characters)
            duration: Duration in minutes (default: 30)

        Returns:
            Exit code (0 = success, 1 = error)
        """
        # Prevent AI from calling this programmatically
        if not sys.stdin.isatty():
            print("❌ This command requires interactive terminal")
            print("   (Cannot be executed by AI)")
            return 1

        if not reason or len(reason) < 10:
            print("❌ Reason must be at least 10 characters")
            return 1

        expiry = datetime.now() + timedelta(minutes=duration)

        override_data = {
            "enabled": True,
            "reason": reason,
            "created_at": datetime.now().isoformat(),
            "expires_at": expiry.isoformat(),
            "created_by": "user",  # Identifies as user action
        }

        WorkflowCommands.OVERRIDE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(WorkflowCommands.OVERRIDE_FILE, "w") as f:
            json.dump(override_data, f, indent=2)

        print(f"✅ Workflow override enabled for {duration} minutes")
        print(f"   Reason: {reason}")
        print(f"   Expires: {expiry.strftime('%H:%M:%S')}")
        print("\n⚠️  Use responsibly - skipping workflow bypasses quality gates")

        return 0

    @staticmethod
    def check() -> int:
        """
        Check if workflow override is active.

        Returns:
            Exit code (0 = success, 1 = error)
        """
        if not WorkflowCommands.OVERRIDE_FILE.exists():
            print("❌ No active override")
            return 1

        try:
            with open(WorkflowCommands.OVERRIDE_FILE) as f:
                data = json.load(f)

            expiry = datetime.fromisoformat(data["expires_at"])

            if datetime.now() > expiry:
                print("❌ Override expired")
                WorkflowCommands.OVERRIDE_FILE.unlink()
                return 1

            remaining = (expiry - datetime.now()).total_seconds() / 60

            print("✅ Override active")
            print(f"   Reason: {data['reason']}")
            print(f"   Remaining: {remaining:.1f} minutes")

            return 0

        except (json.JSONDecodeError, KeyError, ValueError, OSError):
            print("❌ Invalid override file")
            return 1

    @staticmethod
    def clear() -> int:
        """
        Clear active workflow override.

        Returns:
            Exit code (0 = success)
        """
        if WorkflowCommands.OVERRIDE_FILE.exists():
            WorkflowCommands.OVERRIDE_FILE.unlink()
            print("✅ Override cleared")
        else:
            print("ℹ️  No active override")

        return 0
