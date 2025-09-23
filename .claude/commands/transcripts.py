#!/usr/bin/env python3
"""
/transcripts command - Restore conversation context from transcripts
Implements Microsoft Amplifier-style context restoration capabilities.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Clean import setup
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root / ".claude" / "tools" / "amplihack"))


def list_available_sessions() -> List[str]:
    """List available session transcripts."""
    logs_dir = project_root / ".claude" / "runtime" / "logs"
    if not logs_dir.exists():
        return []

    sessions = []
    for session_dir in logs_dir.iterdir():
        if session_dir.is_dir() and (session_dir / "CONVERSATION_TRANSCRIPT.md").exists():
            sessions.append(session_dir.name)

    return sorted(sessions, reverse=True)  # Most recent first


def get_session_summary(session_id: str) -> Dict[str, str]:
    """Get summary information for a session."""
    session_dir = project_root / ".claude" / "runtime" / "logs" / session_id

    summary = {
        "session_id": session_id,
        "transcript_exists": False,
        "original_request_exists": False,
        "target": "Unknown",
        "message_count": 0,
        "timestamp": "Unknown",
    }

    # Check for transcript
    transcript_file = session_dir / "CONVERSATION_TRANSCRIPT.md"
    if transcript_file.exists():
        summary["transcript_exists"] = True
        try:
            content = transcript_file.read_text()
            # Extract message count
            if "**Messages**:" in content:
                line = [
                    msg_line for msg_line in content.split("\n") if "**Messages**:" in msg_line
                ][0]
                summary["message_count"] = int(line.split(":")[-1].strip())
        except (ValueError, IndexError, OSError):
            pass

    # Check for original request
    original_request_file = session_dir / "original_request.json"
    if original_request_file.exists():
        summary["original_request_exists"] = True
        try:
            with open(original_request_file, "r") as f:
                data = json.load(f)
                summary["target"] = data.get("target", "Unknown")
                summary["timestamp"] = data.get("timestamp", "Unknown")
        except (json.JSONDecodeError, OSError, KeyError):
            pass

    return summary


def display_session_list(sessions: List[str]) -> None:
    """Display formatted list of available sessions."""
    if not sessions:
        print("🔍 No conversation transcripts found")
        print("   Transcripts are automatically created when PreCompact hook triggers")
        return

    print(f"📋 Available Conversation Transcripts ({len(sessions)} sessions)")
    print("━" * 80)

    for i, session_id in enumerate(sessions[:10], 1):  # Show latest 10
        summary = get_session_summary(session_id)

        # Format timestamp
        try:
            if summary["timestamp"] != "Unknown":
                ts = datetime.fromisoformat(summary["timestamp"].replace("Z", "+00:00"))
                time_str = ts.strftime("%Y-%m-%d %H:%M")
            else:
                time_str = "Unknown time"
        except (ValueError, KeyError, AttributeError):
            time_str = "Unknown time"

        # Status indicators
        status = []
        if summary["transcript_exists"]:
            status.append(f"📄 {summary['message_count']} msgs")
        if summary["original_request_exists"]:
            status.append("🎯 original req")

        status_str = " | ".join(status) if status else "❌ incomplete"

        print(f"{i:2d}. {session_id}")
        print(f"    🕒 {time_str}")
        print(f"    🎯 {summary['target'][:60]}{'...' if len(summary['target']) > 60 else ''}")
        print(f"    📊 {status_str}")
        print()


def restore_session_context(session_id: str) -> None:
    """Restore and display context from a specific session."""
    session_dir = project_root / ".claude" / "runtime" / "logs" / session_id

    if not session_dir.exists():
        print(f"❌ Session not found: {session_id}")
        return

    print(f"🔄 Restoring Context from Session: {session_id}")
    print("━" * 80)

    # Display original request if available
    original_request_file = session_dir / "ORIGINAL_REQUEST.md"
    if original_request_file.exists():
        print("🎯 ORIGINAL USER REQUEST")
        print("━" * 40)
        content = original_request_file.read_text()
        # Skip the header and show the content
        lines = content.split("\n")
        in_request = False
        for line in lines:
            if line.startswith("## Raw Request"):
                in_request = True
                continue
            elif line.startswith("## ") and in_request:
                break
            elif in_request and not line.startswith("```"):
                print(line)
        print()

    # Display conversation summary
    transcript_file = session_dir / "CONVERSATION_TRANSCRIPT.md"
    if transcript_file.exists():
        print("💬 CONVERSATION SUMMARY")
        print("━" * 40)
        content = transcript_file.read_text()

        # Extract key information
        lines = content.split("\n")
        for line in lines[:10]:  # Show header info
            if line.startswith("**"):
                print(line)

        print()
        print("📄 Full transcript available at:")
        print(f"   {transcript_file}")
        print()

    # Display compaction events if any
    compaction_file = session_dir / "compaction_events.json"
    if compaction_file.exists():
        try:
            with open(compaction_file, "r") as f:
                events = json.load(f)
            print(f"🔄 COMPACTION EVENTS ({len(events)})")
            print("━" * 40)
            for event in events[-3:]:  # Show last 3 events
                trigger = event.get("compaction_trigger", "unknown")
                timestamp = event.get("timestamp", "")
                msg_count = event.get("messages_exported", 0)
                print(f"   📅 {timestamp[:19]}")
                print(f"   🔄 Trigger: {trigger}")
                print(f"   💬 Exported: {msg_count} messages")
                print()
        except (KeyError, IndexError, TypeError):
            pass

    print("✅ Context restoration complete!")
    print("   Original requirements have been preserved and can be referenced by agents.")


def main():
    """Main entry point for /transcripts command."""
    args = sys.argv[1:] if len(sys.argv) > 1 else []

    if not args:
        # List available sessions
        sessions = list_available_sessions()
        display_session_list(sessions)

        if sessions:
            print("💡 Usage:")
            print("   /transcripts <session_id>  - Restore context from specific session")
            print("   /transcripts latest        - Restore context from most recent session")
            print("   /transcripts list          - Show this list again")

    elif args[0] == "list":
        # Explicit list command
        sessions = list_available_sessions()
        display_session_list(sessions)

    elif args[0] == "latest":
        # Restore latest session
        sessions = list_available_sessions()
        if sessions:
            restore_session_context(sessions[0])
        else:
            print("❌ No sessions found")

    else:
        # Restore specific session
        session_id = args[0]
        restore_session_context(session_id)


if __name__ == "__main__":
    main()
