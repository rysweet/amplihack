"""
Transcript Manager - Conversation transcript preservation and restoration.

Handles listing transcripts, generating summaries, restoring context,
and managing session checkpoints.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class TranscriptSummary:
    """Summary of a transcript session."""

    session_id: str
    timestamp: str
    target: str
    message_count: int
    transcript_exists: bool
    original_request_exists: bool
    file_path: Path

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "target": self.target,
            "message_count": self.message_count,
            "transcript_exists": self.transcript_exists,
            "original_request_exists": self.original_request_exists,
            "file_path": str(self.file_path),
        }


# Default configuration
DEFAULT_LOGS_DIR = Path.home() / ".amplifier" / "runtime" / "logs"


class TranscriptManager:
    """Main transcript management coordinator."""

    def __init__(self, logs_dir: Path | None = None) -> None:
        """Initialize transcript manager.

        Args:
            logs_dir: Directory containing transcript logs
        """
        self.logs_dir = logs_dir or DEFAULT_LOGS_DIR

    def list_sessions(self) -> list[str]:
        """List available session transcripts.

        Returns:
            List of session IDs (most recent first)
        """
        if not self.logs_dir.exists():
            return []

        sessions = []
        for session_dir in self.logs_dir.iterdir():
            if session_dir.is_dir():
                # Check for transcript or events file
                if (session_dir / "CONVERSATION_TRANSCRIPT.md").exists() or (
                    session_dir / "events.jsonl"
                ).exists():
                    sessions.append(session_dir.name)

        return sorted(sessions, reverse=True)

    def get_summary(self, session_id: str) -> TranscriptSummary:
        """Get summary information for a session."""
        session_dir = self.logs_dir / session_id

        summary = TranscriptSummary(
            session_id=session_id,
            transcript_exists=False,
            original_request_exists=False,
            target="Unknown",
            message_count=0,
            timestamp="Unknown",
            file_path=session_dir,
        )

        # Check for transcript
        transcript_file = session_dir / "CONVERSATION_TRANSCRIPT.md"
        if transcript_file.exists():
            summary.transcript_exists = True
            try:
                content = transcript_file.read_text()
                if "**Messages**:" in content:
                    for line in content.split("\n"):
                        if "**Messages**:" in line:
                            summary.message_count = int(line.split(":")[-1].strip())
                            break
            except (ValueError, OSError):
                pass

        # Check for original request
        original_request_file = session_dir / "original_request.json"
        if original_request_file.exists():
            summary.original_request_exists = True
            try:
                with open(original_request_file) as f:
                    data = json.load(f)
                    summary.target = data.get("target", "Unknown")
                    summary.timestamp = data.get("timestamp", "Unknown")
            except (json.JSONDecodeError, OSError):
                pass

        # Try to get timestamp from session ID if not found
        if summary.timestamp == "Unknown" and "_" in session_id:
            try:
                parts = session_id.split("_")
                if len(parts) >= 2:
                    date_part = parts[0] if len(parts[0]) == 8 else parts[1]
                    time_part = (
                        parts[1] if len(parts[0]) == 8 else parts[2] if len(parts) > 2 else ""
                    )
                    if date_part.isdigit() and len(date_part) == 8:
                        summary.timestamp = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:]}"
                        if time_part.isdigit() and len(time_part) >= 4:
                            summary.timestamp += f" {time_part[:2]}:{time_part[2:4]}"
            except (ValueError, IndexError):
                pass

        return summary

    def restore_context(self, session_id: str) -> dict[str, Any]:
        """Restore and return context from a transcript."""
        session_dir = self.logs_dir / session_id

        result: dict[str, Any] = {
            "session_id": session_id,
            "exists": session_dir.exists(),
            "original_request": None,
            "transcript_path": None,
            "events_path": None,
        }

        if not session_dir.exists():
            return result

        # Load original request
        original_file = session_dir / "original_request.json"
        if original_file.exists():
            try:
                with open(original_file) as f:
                    result["original_request"] = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass

        # Check for transcript
        transcript_file = session_dir / "CONVERSATION_TRANSCRIPT.md"
        if transcript_file.exists():
            result["transcript_path"] = str(transcript_file)

        # Check for events
        events_file = session_dir / "events.jsonl"
        if events_file.exists():
            result["events_path"] = str(events_file)

        return result

    def save_checkpoint(
        self,
        session_id: str,
        checkpoint_name: str,
        data: dict | None = None,
    ) -> dict[str, Any]:
        """Create a checkpoint marker for a session."""
        session_dir = self.logs_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        checkpoint_dir = session_dir / "checkpoints"
        checkpoint_dir.mkdir(exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        checkpoint_file = checkpoint_dir / f"{timestamp}_{checkpoint_name}.json"

        checkpoint_data = {
            "checkpoint_name": checkpoint_name,
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_id,
            "data": data or {},
        }

        with open(checkpoint_file, "w") as f:
            json.dump(checkpoint_data, f, indent=2)

        return {
            "success": True,
            "checkpoint_file": str(checkpoint_file),
            "checkpoint_name": checkpoint_name,
            "timestamp": checkpoint_data["timestamp"],
        }

    def list_checkpoints(self, session_id: str) -> list[dict[str, Any]]:
        """List checkpoints for a session."""
        checkpoint_dir = self.logs_dir / session_id / "checkpoints"
        if not checkpoint_dir.exists():
            return []

        checkpoints = []
        for checkpoint_file in sorted(checkpoint_dir.glob("*.json"), reverse=True):
            try:
                with open(checkpoint_file) as f:
                    data = json.load(f)
                    checkpoints.append(
                        {
                            "file": checkpoint_file.name,
                            "name": data.get("checkpoint_name", "Unknown"),
                            "timestamp": data.get("timestamp", "Unknown"),
                        }
                    )
            except (json.JSONDecodeError, OSError):
                pass

        return checkpoints


# Module-level convenience functions
_default_manager: TranscriptManager | None = None


def _get_manager() -> TranscriptManager:
    global _default_manager
    if _default_manager is None:
        _default_manager = TranscriptManager()
    return _default_manager


def list_transcripts() -> list[str]:
    """List available transcripts."""
    return _get_manager().list_sessions()


def get_transcript_summary(session_id: str) -> TranscriptSummary:
    """Get summary for a transcript."""
    return _get_manager().get_summary(session_id)


def restore_transcript(session_id: str) -> dict[str, Any]:
    """Restore context from a transcript."""
    return _get_manager().restore_context(session_id)


def save_checkpoint(
    session_id: str,
    checkpoint_name: str,
    data: dict | None = None,
) -> dict[str, Any]:
    """Save a checkpoint for a session."""
    return _get_manager().save_checkpoint(session_id, checkpoint_name, data)
