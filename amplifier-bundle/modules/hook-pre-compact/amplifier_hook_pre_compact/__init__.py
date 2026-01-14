"""Pre-Compact Hook - Amplifier wrapper for transcript export.

Exports conversation transcript before context compaction to preserve
the full session history.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from amplifier_core.protocols import Hook, HookResult


class PreCompactHook(Hook):
    """Exports transcript before context compaction."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.output_dir = Path(self.config.get("output_dir", ".amplifier/transcripts"))

    async def __call__(self, event: str, data: dict[str, Any]) -> HookResult | None:
        """Handle context:compact events to export transcript."""
        if not self.enabled:
            return None

        if event != "context:compact":
            return None

        try:
            # Get messages before compaction
            messages = data.get("messages", [])
            session_id = data.get("session_id", "unknown")
            
            if not messages:
                return None

            # Create output directory
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate transcript filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            transcript_file = self.output_dir / f"transcript_{session_id}_{timestamp}.json"
            
            # Export transcript
            transcript = {
                "session_id": session_id,
                "exported_at": datetime.now().isoformat(),
                "message_count": len(messages),
                "messages": messages,
                "compaction_reason": data.get("reason", "unknown")
            }
            
            transcript_file.write_text(json.dumps(transcript, indent=2, default=str))
            
            return HookResult(
                modified_data=data,
                metadata={
                    "transcript_exported": True,
                    "transcript_file": str(transcript_file),
                    "message_count": len(messages)
                }
            )

        except Exception:
            # Fail open
            pass

        return None


def mount(coordinator, config: dict[str, Any] | None = None) -> None:
    """Mount the pre-compact hook."""
    hook = PreCompactHook(config)
    coordinator.mount("hooks", hook)


__all__ = ["PreCompactHook", "mount"]
