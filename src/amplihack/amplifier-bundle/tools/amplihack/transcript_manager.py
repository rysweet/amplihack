#!/usr/bin/env python3
"""Transcript Manager - Conversation transcript preservation and restoration.

This tool provides conversation history management for context preservation and
restoration. It handles listing transcripts, generating summaries, restoring
context, and managing session checkpoints.

Philosophy:
- Single responsibility: Save and restore conversation transcripts
- Standard library only (no external dependencies)
- Self-contained and regeneratable
- Zero-BS implementation (all functions work completely)

Public API:
    TranscriptManager: Main transcript management class
    list_transcripts: List available transcripts
    get_transcript_summary: Get summary of specific transcript
    restore_transcript: Restore and display transcript context
    save_checkpoint: Create session checkpoint marker
    get_current_session_id: Get or generate current session ID
    TranscriptSummary: Summary dataclass
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

__all__ = [
    "TranscriptManager",
    "list_transcripts",
    "get_transcript_summary",
    "restore_transcript",
    "save_checkpoint",
    "get_current_session_id",
    "TranscriptSummary",
]

# ============================================================================
# Data Models
# ============================================================================


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

    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "target": self.target,
            "message_count": self.message_count,
            "transcript_exists": self.transcript_exists,
            "original_request_exists": self.original_request_exists,
            "file_path": str(self.file_path),
        }


# ============================================================================
# Configuration and Constants
# ============================================================================

DEFAULT_LOGS_DIR = ".claude/runtime/logs"


# ============================================================================
# Main Transcript Manager
# ============================================================================


class TranscriptManager:
    """Main transcript management coordinator.

    Responsibilities:
    - List available transcript sessions
    - Generate session summaries
    - Restore transcript context
    - Create checkpoint markers
    - Session ID management
    """

    def __init__(self, logs_dir: Path | None = None):
        """Initialize transcript manager.

        Args:
            logs_dir: Directory containing transcript logs
        """
        self.logs_dir = self._resolve_path(logs_dir, DEFAULT_LOGS_DIR)

    def _resolve_path(self, provided_path: Path | None, default_path: str) -> Path:
        """Resolve path relative to project root."""
        if provided_path:
            return provided_path if isinstance(provided_path, Path) else Path(provided_path)

        # Try to find project root
        cwd = Path.cwd()
        if (cwd / ".claude").exists():
            return cwd / default_path
        return Path(default_path)

    # ========================================================================
    # Session Listing
    # ========================================================================

    def list_sessions(self) -> list[str]:
        """List available session transcripts.

        Returns:
            List of session IDs (most recent first)
        """
        if not self.logs_dir.exists():
            return []

        sessions = []
        for session_dir in self.logs_dir.iterdir():
            if session_dir.is_dir() and (session_dir / "CONVERSATION_TRANSCRIPT.md").exists():
                sessions.append(session_dir.name)

        return sorted(sessions, reverse=True)

    # ========================================================================
    # Session Summary
    # ========================================================================

    def get_summary(self, session_id: str) -> TranscriptSummary:
        """Get summary information for a session.

        Args:
            session_id: Session ID to summarize

        Returns:
            TranscriptSummary object
        """
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
                    line = [
                        msg_line for msg_line in content.split("\n") if "**Messages**:" in msg_line
                    ][0]
                    summary.message_count = int(line.split(":")[-1].strip())
            except (ValueError, IndexError, OSError):
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
            except (json.JSONDecodeError, OSError, KeyError):
                pass

        return summary

    # ========================================================================
    # Context Restoration
    # ========================================================================

    def restore_context(self, session_id: str) -> dict[str, Any]:
        """Restore and return context from a transcript.

        Args:
            session_id: Session ID to restore

        Returns:
            Dict with restored context information:
            - original_request: User's original request text
            - conversation_summary: Summary info
            - transcript_path: Path to full transcript
            - compaction_events: List of compaction events (if any)
        """
        session_dir = self.logs_dir / session_id

        if not session_dir.exists():
            raise FileNotFoundError(f"Session not found: {session_id}")

        context = {
            "session_id": session_id,
            "original_request": None,
            "conversation_summary": None,
            "transcript_path": None,
            "compaction_events": [],
        }

        # Extract original request
        original_request_file = session_dir / "ORIGINAL_REQUEST.md"
        if original_request_file.exists():
            content = original_request_file.read_text()
            lines = content.split("\n")
            in_request = False
            request_lines = []
            for line in lines:
                if line.startswith("## Raw Request"):
                    in_request = True
                    continue
                if line.startswith("## ") and in_request:
                    break
                if in_request and not line.startswith("```"):
                    request_lines.append(line)
            context["original_request"] = "\n".join(request_lines).strip()

        # Extract conversation summary
        transcript_file = session_dir / "CONVERSATION_TRANSCRIPT.md"
        if transcript_file.exists():
            context["transcript_path"] = str(transcript_file)
            content = transcript_file.read_text()
            lines = content.split("\n")
            summary_lines = []
            for line in lines[:10]:
                if line.startswith("**"):
                    summary_lines.append(line)
            context["conversation_summary"] = "\n".join(summary_lines)

        # Extract compaction events
        compaction_file = session_dir / "compaction_events.json"
        if compaction_file.exists():
            try:
                with open(compaction_file) as f:
                    events = json.load(f)
                context["compaction_events"] = events[-3:]  # Last 3 events
            except (json.JSONDecodeError, KeyError, IndexError, TypeError):
                pass

        return context

    # ========================================================================
    # Checkpoint Management
    # ========================================================================

    def save_checkpoint(self, session_id: str | None = None) -> str:
        """Create a session checkpoint marker.

        Args:
            session_id: Optional session ID (generates if not provided)

        Returns:
            Session ID of created checkpoint
        """
        if session_id is None:
            session_id = self.get_current_session_id()

        session_dir = self.logs_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        # Create checkpoint marker file
        checkpoint_file = session_dir / "CHECKPOINTS.jsonl"
        checkpoint_data = {
            "timestamp": datetime.now().isoformat(),
            "type": "manual_checkpoint",
            "session_id": session_id,
            "created_via": "transcript_manager tool",
        }

        # Append to checkpoints file (JSONL format)
        with open(checkpoint_file, "a") as f:
            f.write(json.dumps(checkpoint_data) + "\n")

        return session_id

    def get_checkpoint_count(self, session_id: str) -> int:
        """Get the number of checkpoints for a session.

        Args:
            session_id: Session ID

        Returns:
            Number of checkpoints
        """
        session_dir = self.logs_dir / session_id
        checkpoint_file = session_dir / "CHECKPOINTS.jsonl"

        if not checkpoint_file.exists():
            return 0

        with open(checkpoint_file) as f:
            return sum(1 for _ in f)

    # ========================================================================
    # Session ID Management
    # ========================================================================

    def get_current_session_id(self) -> str:
        """Get or generate the current session ID.

        Attempts to find the current session ID from:
        1. Runtime environment variables
        2. Latest session directory
        3. Generate new session ID from timestamp

        Returns:
            Current session ID string in format YYYYMMDD_HHMMSS
        """
        import os

        # Try environment variable first (if set by Claude Code)
        env_session = os.environ.get("AMPLIHACK_SESSION_ID")
        if env_session:
            return env_session

        # Try to find most recent session directory
        if self.logs_dir.exists():
            session_dirs = [
                d
                for d in self.logs_dir.iterdir()
                if d.is_dir() and len(d.name) == 15 and "_" in d.name
            ]
            if session_dirs:
                latest = sorted(session_dirs, reverse=True)[0]
                return latest.name

        # Generate new session ID from current timestamp
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    # ========================================================================
    # Formatting Utilities
    # ========================================================================

    def format_summary_display(self, summary: TranscriptSummary, index: int) -> str:
        """Format a transcript summary for display.

        Args:
            summary: TranscriptSummary object
            index: Display index number

        Returns:
            Formatted string for display
        """
        # Format timestamp
        try:
            if summary.timestamp != "Unknown":
                ts = datetime.fromisoformat(summary.timestamp.replace("Z", "+00:00"))
                time_str = ts.strftime("%Y-%m-%d %H:%M")
            else:
                time_str = "Unknown time"
        except (ValueError, KeyError, AttributeError):
            time_str = "Unknown time"

        # Status indicators
        status = []
        if summary.transcript_exists:
            status.append(f"📄 {summary.message_count} msgs")
        if summary.original_request_exists:
            status.append("🎯 original req")

        status_str = " | ".join(status) if status else "❌ incomplete"

        # Truncate target if too long
        target = summary.target[:60]
        if len(summary.target) > 60:
            target += "..."

        return f"""{index:2d}. {summary.session_id}
    🕒 {time_str}
    🎯 {target}
    📊 {status_str}
"""

    def format_context_display(self, context: dict[str, Any]) -> str:
        """Format restored context for display.

        Args:
            context: Context dict from restore_context

        Returns:
            Formatted string for display
        """
        lines = [
            f"🔄 Restoring Context from Session: {context['session_id']}",
            "━" * 80,
            "",
        ]

        # Original request
        if context["original_request"]:
            lines.extend(
                [
                    "🎯 ORIGINAL USER REQUEST",
                    "━" * 40,
                    context["original_request"],
                    "",
                ]
            )

        # Conversation summary
        if context["conversation_summary"]:
            lines.extend(
                [
                    "💬 CONVERSATION SUMMARY",
                    "━" * 40,
                    context["conversation_summary"],
                    "",
                ]
            )

        # Transcript location
        if context["transcript_path"]:
            lines.extend(
                [
                    "📄 Full transcript available at:",
                    f"   {context['transcript_path']}",
                    "",
                ]
            )

        # Compaction events
        if context["compaction_events"]:
            lines.extend([f"🔄 COMPACTION EVENTS ({len(context['compaction_events'])})", "━" * 40])
            for event in context["compaction_events"]:
                trigger = event.get("compaction_trigger", "unknown")
                timestamp = event.get("timestamp", "")
                msg_count = event.get("messages_exported", 0)
                lines.extend(
                    [
                        f"   📅 {timestamp[:19]}",
                        f"   🔄 Trigger: {trigger}",
                        f"   💬 Exported: {msg_count} messages",
                        "",
                    ]
                )

        lines.extend(
            [
                "✅ Context restoration complete!",
                "   Original requirements have been preserved and can be referenced by agents.",
            ]
        )

        return "\n".join(lines)


# ============================================================================
# Convenience Functions (Simplified API)
# ============================================================================


def list_transcripts(**kwargs) -> list[str]:
    """List available transcript sessions.

    Returns:
        List of session IDs (most recent first)
    """
    manager = TranscriptManager(**kwargs)
    return manager.list_sessions()


def get_transcript_summary(session_id: str, **kwargs) -> TranscriptSummary:
    """Get summary of specific transcript.

    Args:
        session_id: Session ID

    Returns:
        TranscriptSummary object
    """
    manager = TranscriptManager(**kwargs)
    return manager.get_summary(session_id)


def restore_transcript(session_id: str, **kwargs) -> dict[str, Any]:
    """Restore transcript context.

    Args:
        session_id: Session ID to restore

    Returns:
        Dict with restored context
    """
    manager = TranscriptManager(**kwargs)
    return manager.restore_context(session_id)


def save_checkpoint(session_id: str | None = None, **kwargs) -> str:
    """Save session checkpoint marker.

    Args:
        session_id: Optional session ID

    Returns:
        Session ID
    """
    manager = TranscriptManager(**kwargs)
    return manager.save_checkpoint(session_id)


def get_current_session_id(**kwargs) -> str:
    """Get current session ID.

    Returns:
        Session ID string
    """
    manager = TranscriptManager(**kwargs)
    return manager.get_current_session_id()


# ============================================================================
# CLI Interface (for testing)
# ============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python transcript_manager.py <action> [args...]")
        print("Actions: list, restore, save, current")
        sys.exit(1)

    action = sys.argv[1]
    manager = TranscriptManager()

    if action == "list":
        sessions = manager.list_sessions()
        if not sessions:
            print("No transcripts found")
        else:
            print(f"📋 Available Conversation Transcripts ({len(sessions)} sessions)")
            print("━" * 80)
            for i, session_id in enumerate(sessions[:10], 1):
                summary = manager.get_summary(session_id)
                print(manager.format_summary_display(summary, i))

    elif action == "restore":
        if len(sys.argv) < 3:
            print("Usage: python transcript_manager.py restore <session_id>")
            sys.exit(1)
        session_id = sys.argv[2]
        try:
            context = manager.restore_context(session_id)
            print(manager.format_context_display(context))
        except FileNotFoundError as e:
            print(f"❌ {e}")

    elif action == "save":
        session_id = manager.save_checkpoint()
        checkpoint_count = manager.get_checkpoint_count(session_id)
        print("✅ Session checkpoint created!")
        print("━" * 80)
        print(f"📄 Session ID: {session_id}")
        print(f"🔖 Checkpoint #{checkpoint_count}")
        print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    elif action == "current":
        session_id = manager.get_current_session_id()
        print(f"Current session ID: {session_id}")

    else:
        print(f"Unknown action: {action}")
        sys.exit(1)
