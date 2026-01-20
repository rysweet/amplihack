"""Override management for workflow enforcement."""

import json
from datetime import datetime
from pathlib import Path


class OverrideManager:
    """Manages workflow enforcement overrides."""

    OVERRIDE_FILE = Path.home() / ".amplifier" / "state" / "workflow_override.json"
    AUDIT_FILE = Path.home() / ".amplifier" / "state" / "override_audit.jsonl"

    @staticmethod
    def is_override_active() -> tuple[bool, str]:
        """
        Check if user override is active.

        Returns:
            (active: bool, reason: str)
        """
        if not OverrideManager.OVERRIDE_FILE.exists():
            return False, "no override file"

        try:
            with open(OverrideManager.OVERRIDE_FILE) as f:
                data = json.load(f)

            # Verify it's a user-created override
            if data.get("created_by") != "user":
                return False, "invalid override source"

            # Check expiry
            expiry = datetime.fromisoformat(data["expires_at"])
            if datetime.now() > expiry:
                # Clean up expired override
                OverrideManager.OVERRIDE_FILE.unlink()
                return False, "override expired"

            reason = data.get("reason", "unknown")
            return True, reason

        except (json.JSONDecodeError, KeyError, ValueError, OSError) as e:
            # Invalid override file - ignore
            return False, f"invalid override: {e}"

    @staticmethod
    def record_override_usage(tool_name: str, context: dict):
        """Record that override was used (for auditing)."""
        OverrideManager.AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)

        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "tool_name": tool_name,
            "session_id": context.get("session_id"),
            "override_reason": context.get("override_reason", "unknown"),
        }

        try:
            with open(OverrideManager.AUDIT_FILE, "a") as f:
                f.write(json.dumps(audit_entry) + "\n")
        except OSError:
            pass  # Fail gracefully if we can't audit
