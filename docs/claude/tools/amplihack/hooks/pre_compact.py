#!/usr/bin/env python3
"""
PreCompact Hook - amplihack Style
Automatically exports conversation transcript before context compaction.
Ensures no conversation history is lost when Claude Code compacts context.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Clean import setup
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import dependencies with clean structure
from context_preservation import ContextPreserver
from hook_processor import HookProcessor


class PreCompactHook(HookProcessor):
    """Hook processor for pre-compact events."""

    def __init__(self):
        super().__init__("pre_compact")
        # Initialize session attributes
        self.session_id = self.get_session_id()
        self.session_dir = self.log_dir / self.session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process pre-compact event and export conversation transcript.

        Args:
            input_data: Input from Claude Code containing conversation data

        Returns:
            Confirmation of export completion
        """
        try:
            # Get conversation data
            conversation = input_data.get("conversation", [])
            messages = input_data.get("messages", [])

            # Use either conversation or messages data
            conversation_data = conversation if conversation else messages

            self.log(
                f"Exporting conversation with {len(conversation_data)} entries before compaction"
            )

            # Create context preserver
            preserver = ContextPreserver(self.session_id)
            # Override the session_dir to use the hook's session directory
            # This ensures all files are saved in the correct location
            preserver.session_dir = self.session_dir

            # Extract original request if it exists in the conversation
            original_request = None
            for entry in conversation_data:
                if entry.get("role") == "user" and len(entry.get("content", "")) > 50:
                    # Found substantial user input - try to extract as original request
                    try:
                        original_request = preserver.extract_original_request(entry["content"])
                        self.log(
                            f"Original request extracted from conversation: {original_request.get('target', 'Unknown')}"
                        )
                        break
                    except Exception as e:
                        self.log(f"Failed to extract original request: {e}")

            # Export the full conversation transcript
            transcript_path = preserver.export_conversation_transcript(conversation_data)
            self.log(f"Conversation transcript exported to: {transcript_path}")

            # Also create a copy in the transcripts subdirectory for easy access
            transcripts_dir = self.session_dir / "transcripts"
            transcripts_dir.mkdir(exist_ok=True)
            transcript_copy = (
                transcripts_dir / f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            )

            try:
                with open(transcript_path) as src, open(transcript_copy, "w") as dst:
                    dst.write(src.read())
                self.log(f"Transcript copy created in: {transcript_copy}")
            except Exception as e:
                self.log(f"Failed to create transcript copy: {e}", "WARNING")

            # Save compaction event metadata
            compaction_info = {
                "timestamp": datetime.now().isoformat(),
                "session_id": self.session_id,
                "messages_exported": len(conversation_data),
                "transcript_path": transcript_path,
                "original_request_preserved": original_request is not None,
                "compaction_trigger": input_data.get("trigger", "unknown"),
            }

            # Save metadata
            metadata_file = self.session_dir / "compaction_events.json"
            events = []
            if metadata_file.exists():
                try:
                    with open(metadata_file) as f:
                        events = json.load(f)
                except Exception:
                    events = []

            events.append(compaction_info)

            with open(metadata_file, "w") as f:
                json.dump(events, f, indent=2)

            # Save metrics
            self.save_metric("messages_exported", len(conversation_data))
            self.save_metric("compaction_events", len(events))
            self.save_metric("transcript_exported", True)

            return {
                "status": "success",
                "message": f"Conversation exported successfully - {len(conversation_data)} messages preserved",
                "transcript_path": transcript_path,
                "metadata": compaction_info,
            }

        except Exception as e:
            error_msg = f"Failed to export conversation before compaction: {e}"
            self.log(error_msg)
            self.save_metric("transcript_exported", False)

            return {"status": "error", "message": error_msg, "error": str(e)}

    def restore_conversation_from_latest(self) -> List[Dict[str, Any]]:
        """Restore conversation from the latest transcript.

        Returns:
            List of conversation messages or empty list if not found
        """
        try:
            # Find latest session using the log directory
            logs_dir = (
                self.log_dir
                if hasattr(self, "log_dir")
                else (self.project_root / ".claude" / "runtime" / "logs")
            )

            if not logs_dir.exists():
                self.log("No logs directory found")
                return []

            # Find session directories (format: YYYYMMDD_HHMMSS)
            import re

            session_dirs = [
                d for d in logs_dir.iterdir() if d.is_dir() and re.match(r"\d{8}_\d{6}", d.name)
            ]

            if not session_dirs:
                self.log("No session logs found")
                return []

            # Get the latest session
            latest_session = sorted(session_dirs)[-1].name

            transcript_file = logs_dir / latest_session / "CONVERSATION_TRANSCRIPT.md"

            if not transcript_file.exists():
                self.log(f"No transcript found for session: {latest_session}")
                return []

            self.log(f"Restored conversation from session: {latest_session}")
            return [
                {"source": "transcript", "path": str(transcript_file), "session": latest_session}
            ]

        except Exception as e:
            self.log(f"Failed to restore conversation: {e}")
            return []


def main():
    """Entry point for the pre-compact hook."""
    hook = PreCompactHook()
    hook.run()


if __name__ == "__main__":
    main()
