#!/usr/bin/env python3
"""
Claude Code hook for session stop events.
Uses unified HookProcessor for common functionality.
"""

import json

# Import the base processor
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent))
from hook_processor import HookProcessor


class StopHook(HookProcessor):
    """Hook processor for session stop events."""

    def __init__(self):
        super().__init__("stop")

    def extract_learnings(self, messages: List[Dict]) -> List[Dict]:
        """Extract learnings using the reflection module.

        Args:
            messages: List of conversation messages

        Returns:
            List of potential learnings with improvement suggestions
        """
        try:
            # Import reflection module
            from reflection import SessionReflector, save_reflection_summary

            # Create reflector and analyze session
            reflector = SessionReflector()
            analysis = reflector.analyze_session(messages)

            # Save detailed analysis if not skipped
            if not analysis.get("skipped"):
                summary_file = save_reflection_summary(analysis, self.analysis_dir)
                if summary_file:
                    self.log(f"Reflection analysis saved to {summary_file}")

                # Return patterns found as learnings
                learnings = []
                for pattern in analysis.get("patterns", []):
                    learnings.append(
                        {
                            "type": pattern["type"],
                            "suggestion": pattern.get("suggestion", ""),
                            "priority": "high"
                            if pattern["type"] == "user_frustration"
                            else "normal",
                        }
                    )
                return learnings
            else:
                self.log("Reflection skipped (loop prevention active)")
                return []

        except ImportError as e:
            self.log(f"Could not import reflection module: {e}", "WARNING")
            # Fall back to simple keyword extraction
            return self.extract_learnings_simple(messages)
        except Exception as e:
            self.log(f"Error in reflection analysis: {e}", "ERROR")
            return []

    def extract_learnings_simple(self, messages: List[Dict]) -> List[Dict]:
        """Simple fallback learning extraction.

        Args:
            messages: List of conversation messages

        Returns:
            List of simple keyword-based learnings
        """
        learnings = []
        keywords = ["discovered", "learned", "found that", "issue was", "solution was"]

        for message in messages:
            content = message.get("content", "")
            if isinstance(content, str):
                for keyword in keywords:
                    if keyword.lower() in content.lower():
                        learnings.append({"keyword": keyword, "preview": content[:200]})
                        break
        return learnings

    def save_session_analysis(self, messages: List[Dict]):
        """Save session analysis for later review.

        Args:
            messages: List of conversation messages
        """
        # Generate analysis filename
        analysis_file = (
            self.analysis_dir / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        # Extract stats
        stats = {
            "timestamp": datetime.now().isoformat(),
            "message_count": len(messages),
            "tool_uses": 0,
            "errors": 0,
        }

        # Count tool uses and errors
        for msg in messages:
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                if "tool_use" in str(content):
                    stats["tool_uses"] += 1
                if "error" in str(content).lower():
                    stats["errors"] += 1

        # Extract learnings
        learnings = self.extract_learnings(messages)
        if learnings:
            stats["potential_learnings"] = len(learnings)

        # Save analysis
        analysis = {"stats": stats, "learnings": learnings}

        with open(analysis_file, "w") as f:
            json.dump(analysis, f, indent=2)

        self.log(f"Saved session analysis to {analysis_file.name}")

        # Also save metrics
        self.save_metric("message_count", stats["message_count"])
        self.save_metric("tool_uses", stats["tool_uses"])
        self.save_metric("errors", stats["errors"])
        if learnings:
            self.save_metric("potential_learnings", len(learnings))

    def read_transcript(self, transcript_path: str) -> List[Dict]:
        """Read and parse transcript file.

        Args:
            transcript_path: Path to transcript file

        Returns:
            List of messages from transcript
        """
        try:
            if not transcript_path:
                self.log("No transcript path provided", "WARNING")
                return []

            transcript_file = Path(transcript_path)
            if not transcript_file.exists():
                self.log(f"Transcript file not found: {transcript_path}", "WARNING")
                return []

            # Allow reading from Claude Code directories and temp directories
            # These are trusted locations where Claude Code stores transcripts
            allowed_external_paths = [
                Path.home() / ".claude",  # Claude Code's data directory
                Path("/tmp"),  # Temporary files
                Path("/var/folders"),  # macOS temp directory
                Path("/private/var/folders"),  # macOS temp directory (resolved)
            ]

            # Check if the transcript is in an allowed external location
            is_allowed_external = False
            for allowed_path in allowed_external_paths:
                try:
                    transcript_file.resolve().relative_to(allowed_path.resolve())
                    is_allowed_external = True
                    break
                except (ValueError, RuntimeError):
                    continue

            # If not in allowed external location, validate it's within project
            if not is_allowed_external:
                try:
                    self.validate_path_containment(transcript_file)
                except ValueError as e:
                    self.log(f"Transcript path not in allowed locations: {e}", "WARNING")
                    # Don't completely fail - just log the issue
                    pass

            self.log(f"Reading transcript from: {transcript_path}")

            with open(transcript_file, "r", encoding="utf-8") as f:
                content = f.read().strip()

            if not content:
                self.log("Transcript file is empty", "WARNING")
                return []

            # Try parsing as JSON first
            try:
                data = json.loads(content)

                # Handle different transcript formats
                if isinstance(data, list):
                    # Direct list of messages
                    self.log(f"Parsed JSON array with {len(data)} items")
                    return data
                elif isinstance(data, dict):
                    # Wrapped format
                    if "messages" in data:
                        messages = data["messages"]
                        self.log(f"Found 'messages' key with {len(messages)} messages")
                        return messages
                    elif "conversation" in data:
                        conversation = data["conversation"]
                        self.log(f"Found 'conversation' key with {len(conversation)} messages")
                        return conversation
                    else:
                        self.log(f"Unexpected transcript format: {list(data.keys())}", "WARNING")
                        return []
                else:
                    self.log(f"Unexpected transcript data type: {type(data)}", "WARNING")
                    return []

            except json.JSONDecodeError:
                # Try parsing as JSONL (one JSON object per line) - Claude Code's format
                self.log("Parsing as JSONL format (Claude Code transcript)")
                messages = []
                for line_num, line in enumerate(content.split("\n"), 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)

                        # Claude Code JSONL format has nested message structure
                        if isinstance(entry, dict):
                            # Extract the actual message from Claude Code format
                            if "message" in entry and isinstance(entry["message"], dict):
                                # This is Claude Code format - extract the nested message
                                message = entry["message"]
                                if "role" in message:
                                    messages.append(message)
                            elif "role" in entry:
                                # Direct message format
                                messages.append(entry)
                            elif "type" in entry:
                                # Some entries are metadata - skip them
                                if entry["type"] in ["user", "assistant"]:
                                    # Try to extract message if it exists
                                    if "message" in entry:
                                        messages.append(entry["message"])
                                else:
                                    self.log(
                                        f"Skipping metadata entry with type: {entry.get('type')}",
                                        "DEBUG",
                                    )
                    except json.JSONDecodeError as e:
                        # Log but continue - some lines might be metadata
                        self.log(f"Skipping non-JSON line {line_num}: {str(e)[:100]}", "DEBUG")
                        continue

                self.log(f"Parsed JSONL with {len(messages)} messages")
                return messages

        except Exception as e:
            self.log(f"Error reading transcript: {e}", "ERROR")
            return []

    def find_session_transcript(self, session_id: str) -> Optional[Path]:
        """Find transcript file for a given session ID.

        Args:
            session_id: Session identifier

        Returns:
            Path to transcript file if found
        """
        if not session_id:
            return None

        # Possible transcript locations and naming patterns
        possible_locations = [
            # Current runtime structure
            self.project_root / ".claude" / "runtime" / "transcripts",
            self.project_root / ".claude" / "runtime" / "sessions",
            self.project_root / ".claude" / "runtime" / "logs" / session_id,
            # Alternative naming patterns
            self.project_root / "transcripts",
            self.project_root / "sessions",
            # Temporary locations
            Path("/tmp") / "claude" / "transcripts",
        ]

        # Possible file patterns
        patterns = [
            f"{session_id}.json",
            f"{session_id}_transcript.json",
            f"transcript_{session_id}.json",
            f"session_{session_id}.json",
            "transcript.json",
            "messages.json",
            "conversation.json",
        ]

        for location in possible_locations:
            if not location.exists():
                continue

            for pattern in patterns:
                transcript_file = location / pattern
                if transcript_file.exists():
                    self.log(f"Found transcript file: {transcript_file}")
                    return transcript_file

        return None

    def get_session_messages(self, input_data: Dict[str, Any]) -> List[Dict]:
        """Get session messages using multiple strategies.

        Args:
            input_data: Input from Claude Code

        Returns:
            List of session messages
        """
        # Strategy 1: Direct messages (highest priority - most reliable)
        if "messages" in input_data:
            messages = input_data["messages"]
            if messages:
                self.log(f"Using direct messages: {len(messages)} messages")
                return messages

        # Strategy 2: Provided transcript path
        transcript_path = input_data.get("transcript_path")

        # Handle different types of transcript_path values
        if transcript_path:
            # Convert to string if it's not already
            if not isinstance(transcript_path, str):
                self.log(f"transcript_path is type {type(transcript_path)}, converting to string")
                # Handle None or other non-string types
                if transcript_path is None or str(transcript_path) in ["None", "null", ""]:
                    transcript_path = None
                else:
                    transcript_path = str(transcript_path)

            if transcript_path and transcript_path.strip() and transcript_path != "None":
                messages = self.read_transcript(transcript_path)
                if messages:
                    self.log(
                        f"Read {len(messages)} messages from provided transcript: {transcript_path}"
                    )
                    return messages
                else:
                    self.log(f"No messages found at provided transcript path: {transcript_path}")

        # Strategy 3: Find transcript using session_id
        session_id = input_data.get("session_id")
        if session_id:
            transcript_file = self.find_session_transcript(session_id)
            if transcript_file:
                messages = self.read_transcript(str(transcript_file))
                if messages:
                    self.log(
                        f"Read {len(messages)} messages from discovered transcript: {transcript_file}"
                    )
                    return messages

        # Strategy 4: Search for recent transcript files in common locations
        self.log("Searching for recent transcript files...")
        transcript_locations = [
            self.project_root / ".claude" / "runtime" / "transcripts",
            self.project_root / ".claude" / "runtime" / "sessions",
            self.project_root / "transcripts",
        ]

        for location in transcript_locations:
            if not location.exists():
                continue

            # Find most recent transcript file
            try:
                transcript_files = list(location.glob("*.json"))
                if transcript_files:
                    # Sort by modification time, most recent first
                    transcript_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                    recent_file = transcript_files[0]

                    # Only use if it's very recent (within last hour)
                    import time

                    if time.time() - recent_file.stat().st_mtime < 3600:
                        messages = self.read_transcript(str(recent_file))
                        if messages:
                            self.log(
                                f"Using recent transcript: {recent_file} ({len(messages)} messages)"
                            )
                            return messages
            except Exception as e:
                self.log(f"Error searching in {location}: {e}", "WARNING")

        # No messages found
        self.log("No session messages found using any strategy", "WARNING")
        return []

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process stop event.

        Args:
            input_data: Input from Claude Code

        Returns:
            Metadata about the session
        """
        # Debug log the input data to understand what we're receiving
        self.log(f"Input data keys: {list(input_data.keys())}")

        # Log specific fields that might contain transcript info
        for key in ["transcript_path", "session_id", "messages"]:
            if key in input_data:
                value = input_data[key]
                if key == "messages" and isinstance(value, list):
                    self.log(f"  {key}: list with {len(value)} items")
                elif value is None:
                    self.log(f"  {key}: None")
                else:
                    self.log(f"  {key}: {type(value).__name__} = {str(value)[:100]}")

        # Extract messages - try transcript_path first, fallback to direct messages
        messages = []

        # Try multiple strategies to get session messages
        messages = self.get_session_messages(input_data)

        self.log(f"Processing {len(messages)} messages")

        # Save session analysis
        if messages:
            self.save_session_analysis(messages)

            # Try AI-powered automation (respects REFLECTION_ENABLED environment variable)
            try:
                sys.path.append(str(Path(__file__).parent.parent / "reflection"))
                from reflection import process_reflection_analysis  # type: ignore

                self.log("Starting AI-powered reflection analysis...")

                # Find the most recent analysis file
                analysis_files = list(self.analysis_dir.glob("session_*.json"))
                if analysis_files:
                    latest_analysis = max(analysis_files, key=lambda f: f.stat().st_mtime)
                    self.log(f"Processing analysis file: {latest_analysis}")

                    # Add messages to the analysis data for AI processing
                    try:
                        with open(latest_analysis, "r") as f:
                            analysis_data = json.load(f)

                        # Add the actual session messages for AI analysis
                        analysis_data["messages"] = messages

                        # Save updated analysis with messages
                        with open(latest_analysis, "w") as f:
                            json.dump(analysis_data, f, indent=2)

                    except Exception as e:
                        self.log(f"Warning: Could not add messages to analysis: {e}", "WARNING")

                    # Run AI analysis
                    result = process_reflection_analysis(latest_analysis)
                    if result:
                        self.log(f"✅ AI automation completed: Issue #{result}")
                    else:
                        self.log("AI analysis complete - no automation triggered")
                else:
                    self.log("No analysis files found for AI processing", "WARNING")

            except Exception as auto_error:
                self.log(f"AI automation error: {auto_error}", "ERROR")
                import traceback

                self.log(f"Stack trace: {traceback.format_exc()}", "DEBUG")

        # Check for learnings
        learnings = self.extract_learnings(messages)

        # Build response
        output = {}
        if learnings:
            # Check for high priority learnings
            priority_learnings = [
                learning for learning in learnings if learning.get("priority") == "high"
            ]

            output = {
                "metadata": {
                    "learningsFound": len(learnings),
                    "highPriority": len(priority_learnings),
                    "source": "reflection_analysis",
                    "analysisPath": ".claude/runtime/analysis/",
                    "summary": f"Found {len(learnings)} improvement opportunities",
                }
            }

            # Add specific suggestions to output if high priority
            if priority_learnings:
                output["metadata"]["urgentSuggestion"] = priority_learnings[0].get("suggestion", "")

            self.log(
                f"Found {len(learnings)} potential improvements ({len(priority_learnings)} high priority)"
            )

        return output


def main():
    """Entry point for the stop hook."""
    hook = StopHook()
    hook.run()


if __name__ == "__main__":
    main()
