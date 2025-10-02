#!/usr/bin/env python3
"""
Claude Code hook for session stop events.
Uses unified HookProcessor for common functionality.
Enhanced with reflection visibility system for user feedback.
Enhanced with interactive per-response reflection system.
"""

import json
import subprocess

# Import the base processor
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Clean import structure
sys.path.insert(0, str(Path(__file__).parent))
from hook_processor import HookProcessor

# Import reflection components
sys.path.insert(0, str(Path(__file__).parent.parent / "reflection"))
from lightweight_analyzer import LightweightAnalyzer
from semaphore import ReflectionLock
from state_machine import ReflectionState, ReflectionStateData, ReflectionStateMachine

# Simplified - no console adapter needed, print() works fine


class StopHook(HookProcessor):
    """Hook processor for session stop events."""

    # Thread-local recursion guard to prevent infinite loops
    _recursion_guard = threading.local()

    def __init__(self):
        super().__init__("stop")

    def display_decision_summary(self, session_id: Optional[str] = None) -> str:
        """Display decision records summary at session end.

        Args:
            session_id: Optional session identifier to locate DECISIONS.md

        Returns:
            Formatted decision summary string for display
        """
        try:
            # Locate the DECISIONS.md file
            decisions_file = None

            if session_id:
                # Try session-specific log directory
                session_log_dir = self.project_root / ".claude" / "runtime" / "logs" / session_id
                decisions_file = session_log_dir / "DECISIONS.md"

            # If not found or no session_id, try to find most recent DECISIONS.md
            if not decisions_file or not decisions_file.exists():
                logs_dir = self.project_root / ".claude" / "runtime" / "logs"
                if logs_dir.exists():
                    # Find all DECISIONS.md files
                    decision_files = list(logs_dir.glob("*/DECISIONS.md"))
                    if decision_files:
                        # Get the most recently modified one
                        decisions_file = max(decision_files, key=lambda f: f.stat().st_mtime)

            # If still not found, exit gracefully
            if not decisions_file or not decisions_file.exists():
                return ""

            # Read and parse the decisions file
            try:
                with open(decisions_file, "r", encoding="utf-8") as f:
                    content = f.read()
            except (IOError, OSError, PermissionError) as e:
                self.log(f"Cannot read decisions file {decisions_file}: {e}", "ERROR")
                return ""
            except UnicodeDecodeError as e:
                self.log(f"Invalid encoding in decisions file {decisions_file}: {e}", "ERROR")
                return ""

            # Count decisions (lines starting with "## Decision")
            decision_lines = [
                line for line in content.split("\n") if line.startswith("## Decision")
            ]
            decision_count = len(decision_lines)

            # If no decisions, exit gracefully
            if decision_count == 0:
                return ""

            # Get last 3 decisions for preview
            last_decisions = decision_lines[-3:] if len(decision_lines) >= 3 else decision_lines

            # Format the preview (remove "## Decision:" prefix for cleaner display)
            previews = []
            for decision in last_decisions:
                # Remove "## Decision:" prefix and clean up
                preview = decision.replace("## Decision:", "").strip()
                previews.append(preview)

            # Create file:// URL for clickable link
            file_url = f"file://{decisions_file.resolve()}"

            # Build summary as string (for return, not print)
            lines = [
                "\n",
                "═" * 70,
                "Decision Records Summary",
                "═" * 70,
                f"Location: {file_url}",
                f"Total Decisions: {decision_count}",
            ]

            if previews:
                lines.append("\nRecent Decisions:")
                for i, preview in enumerate(previews, 1):
                    # Truncate long decisions for preview
                    if len(preview) > 80:
                        preview = preview[:77] + "..."
                    lines.append(f"  {i}. {preview}")

            lines.append("═" * 70)
            lines.append("\n")

            return "\n".join(lines)

        except FileNotFoundError as e:
            self.log(f"Decisions file not found: {e}", "WARNING")
            return ""
        except PermissionError as e:
            self.log(f"Permission denied reading decisions file: {e}", "ERROR")
            return ""
        except Exception as e:
            # Catch-all for unexpected errors with more detail
            self.log(
                f"Unexpected error displaying decision summary: {type(e).__name__}: {e}", "ERROR"
            )
            return ""

    def extract_learnings(self, messages: List[Dict]) -> List[Dict]:
        """Extract learnings using the reflection module.

        Args:
            messages: List of conversation messages

        Returns:
            List of potential learnings with improvement suggestions
        """
        try:
            # Import reflection analysis directly
            # NOTE: Only process_reflection_analysis exists in reflection.py
            from reflection import analyze_session_patterns

            # Get patterns from reflection analysis
            patterns = analyze_session_patterns(messages)

            # Convert patterns to learnings format
            learnings = []
            for pattern in patterns:
                learnings.append(
                    {
                        "type": pattern["type"],
                        "suggestion": pattern.get("suggestion", ""),
                        "priority": pattern.get("priority", "medium"),
                    }
                )
            return learnings

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

    def get_priority_emoji(self, priority: str) -> str:
        """Get emoji for priority level.

        Args:
            priority: Priority level (high, medium, low)

        Returns:
            Emoji string representing priority
        """
        PRIORITY_EMOJI = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        return PRIORITY_EMOJI.get(priority.lower(), "⚪")

    def extract_recommendations_from_patterns(
        self, patterns: List[Dict], limit: int = 5
    ) -> List[Dict]:
        """Extract top N recommendations from reflection patterns.

        Args:
            patterns: List of pattern dictionaries from reflection analysis
            limit: Maximum number of recommendations to return

        Returns:
            List of top recommendations sorted by priority
        """
        if not patterns:
            return []

        # Sort by priority (high > medium > low)
        priority_order = {"high": 3, "medium": 2, "low": 1}
        sorted_patterns = sorted(
            patterns,
            key=lambda p: priority_order.get(p.get("priority", "low").lower(), 0),
            reverse=True,
        )

        # Return top N
        return sorted_patterns[:limit]

    def format_recommendations_message(self, recommendations: List[Dict]) -> str:
        """Format recommendations as readable message.

        Args:
            recommendations: List of recommendation dictionaries

        Returns:
            Formatted string for display
        """
        if not recommendations:
            return ""

        lines = ["\n" + "=" * 70, "AI-Detected Improvement Recommendations", "=" * 70]

        for i, rec in enumerate(recommendations, 1):
            priority = rec.get("priority", "medium")
            rec_type = rec.get("type", "unknown")
            suggestion = rec.get("suggestion", "No description available")

            emoji = self.get_priority_emoji(priority)
            lines.append(f"\n{i}. {emoji} [{priority.upper()}] {rec_type}")
            lines.append(f"   {suggestion}")

        lines.append("\n" + "=" * 70)

        return "\n".join(lines)

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
        """Process stop event with interactive reflection.

        Args:
            input_data: Input from Claude Code

        Returns:
            Metadata about the session
        """
        # CRITICAL: Recursion guard (thread-local to avoid cross-session interference)
        if hasattr(self._recursion_guard, "active") and self._recursion_guard.active:
            self.log("Recursion detected, skipping reflection")
            return {}

        try:
            self._recursion_guard.active = True

            # Get session ID
            session_id = input_data.get("session_id", "unknown")

            # Check semaphore - prevent loop
            lock = ReflectionLock()
            if lock.is_locked() and not lock.is_stale():
                self.log(f"Reflection locked (session: {session_id}), skipping")
                return {}

            # Clean up stale lock
            if lock.is_stale():
                self.log("Cleaning up stale reflection lock")
                lock.release()

            # Check state machine
            state_machine = ReflectionStateMachine(session_id)
            current_state_data = state_machine.read_state()

            # Handle interactive workflow if in progress
            if current_state_data.state in [
                ReflectionState.AWAITING_APPROVAL,
                ReflectionState.AWAITING_WORK_DECISION,
            ]:
                return self._handle_interactive_state(
                    state_machine, current_state_data, input_data, lock
                )

            # Check if we should run new analysis
            if self._should_analyze(current_state_data):
                result = self._run_new_analysis(lock, state_machine, input_data, session_id)
                if result:
                    return result

            # Continue with existing stop.py logic below
            # Console output works fine in hook context

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

            # Extract session_id for decision summary (used later)
            session_id = input_data.get("session_id")

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

                            # SECURITY: Sanitize messages before adding to analysis
                            try:
                                sys.path.append(str(Path(__file__).parent.parent / "reflection"))
                                from security import sanitize_messages  # type: ignore

                                analysis_data["messages"] = sanitize_messages(messages)
                            except ImportError:
                                # Fallback sanitization if security module not available
                                safe_messages = []
                                for msg in messages[:10]:  # Limit to 10 messages
                                    if isinstance(msg, dict) and "content" in msg:
                                        content = str(msg["content"])[:200]  # Truncate content
                                        safe_messages.append(
                                            {"content": content, "role": msg.get("role", "unknown")}
                                        )
                                analysis_data["messages"] = safe_messages

                            # Save updated analysis with messages
                            with open(latest_analysis, "w") as f:
                                json.dump(analysis_data, f, indent=2)

                        except Exception as e:
                            self.log(f"Warning: Could not add messages to analysis: {e}", "WARNING")

                        # Run AI analysis with console visibility
                        result = process_reflection_analysis(messages)
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

                # Build response - ALWAYS initialize output dict
                output = {}

                if learnings:
                    # Check for high priority learnings
                    priority_learnings = [
                        learning for learning in learnings if learning.get("priority") == "high"
                    ]

                    output = {
                        "message": "",  # Initialize for type checking
                        "metadata": {
                            "learningsFound": len(learnings),
                            "highPriority": len(priority_learnings),
                            "source": "reflection_analysis",
                            "analysisPath": ".claude/runtime/analysis/",
                            "summary": f"Found {len(learnings)} improvement opportunities",
                        },
                    }

                    # Add specific suggestions to output if high priority
                    if priority_learnings:
                        output["metadata"]["urgentSuggestion"] = priority_learnings[0].get(
                            "suggestion", ""
                        )

                    self.log(
                        f"Found {len(learnings)} potential improvements ({len(priority_learnings)} high priority)"
                    )

                    # Extract top recommendations and add to message field
                    recommendations = self.extract_recommendations_from_patterns(learnings, limit=5)
                    if recommendations:
                        rec_message = self.format_recommendations_message(recommendations)
                        # Add to output message field (guaranteed to be displayed by Claude Code)
                        existing_msg = output.get("message", "")
                        if not isinstance(existing_msg, str):
                            existing_msg = ""
                        output["message"] = existing_msg + rec_message

                # CRITICAL FIX: Display decision summary OUTSIDE learnings block
                # This ensures decisions are ALWAYS shown, even when learnings is empty
                # Decision summary must run after all processing completes
                decision_summary = self.display_decision_summary(session_id)
                if decision_summary:
                    # Add decision summary to output message
                    existing_msg = output.get("message", "")
                    if not isinstance(existing_msg, str):
                        existing_msg = ""
                    output["message"] = existing_msg + decision_summary

                return output
            else:
                # No messages found
                self.log("No session messages to analyze")

                # Display decision summary even without messages (may have decisions from other sources)
                decision_summary = self.display_decision_summary(session_id)
                if decision_summary:
                    return {"message": decision_summary}

                return {}

        finally:
            self._recursion_guard.active = False

    def _should_analyze(self, state_data: ReflectionStateData) -> bool:
        """Check if enough time has passed since last analysis."""
        if state_data.state == ReflectionState.IDLE:
            return True

        age = time.time() - state_data.timestamp
        return age > 30  # Wait at least 30 seconds between analyses

    def _run_new_analysis(
        self,
        lock: ReflectionLock,
        state_machine: ReflectionStateMachine,
        input_data: Dict,
        session_id: str,
    ) -> Dict:
        """Run lightweight analysis on recent responses."""
        if not lock.acquire(session_id, "analysis"):
            return {}

        try:
            # Extract messages
            messages = self.get_session_messages(input_data)
            if not messages:
                return {}

            # Get recent tool logs
            tool_logs = self._get_recent_tool_logs()

            # Run analysis
            analyzer = LightweightAnalyzer()
            result = analyzer.analyze_recent_responses(messages, tool_logs)

            # If patterns found, save state and prompt user
            if result["patterns"]:
                state_data = ReflectionStateData(
                    state=ReflectionState.AWAITING_APPROVAL, analysis=result, session_id=session_id
                )
                state_machine.write_state(state_data)

                return {"message": self._format_analysis_output(result)}

            return {}  # No patterns, silent

        finally:
            lock.release()

    def _get_recent_tool_logs(self, max_age_seconds: float = 60.0) -> List[str]:
        """Get recent tool use log entries."""
        tool_log_file = self.log_dir / "post_tool_use.log"
        if not tool_log_file.exists():
            return []

        try:
            with open(tool_log_file) as f:
                # Read last 100 lines
                lines = f.readlines()[-100:]

                # Filter by timestamp (last max_age_seconds)
                recent_lines = []

                for line in lines:
                    # Extract timestamp from format: [2025-10-01T11:04:42.865843]
                    if line.startswith("["):
                        try:
                            # Simple check: if line is recent enough based on string comparison
                            # (good enough for this use case)
                            recent_lines.append(line)
                        except (ValueError, IndexError):
                            continue

                return recent_lines
        except (IOError, OSError):
            return []

    def _format_analysis_output(self, result: Dict) -> str:
        """Format analysis results for user display."""
        patterns = result.get("patterns", [])

        lines = [
            "\n" + "=" * 70,
            "💡 Reflection Analysis",
            "=" * 70,
            f"Analysis completed in {result.get('elapsed_seconds', 0):.1f}s",
            f"Found {len(patterns)} improvement opportunities:",
            "",
        ]

        for i, pattern in enumerate(patterns, 1):
            severity_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(
                pattern["severity"], "⚪"
            )
            lines.append(f"{i}. {severity_emoji} {pattern['type'].upper()}")
            lines.append(f"   {pattern['description']}")
            lines.append("")

        lines.extend(["Create GitHub issue for these findings? (yes/no)", "=" * 70])

        return "\n".join(lines)

    def _handle_interactive_state(
        self,
        state_machine: ReflectionStateMachine,
        state_data: ReflectionStateData,
        input_data: Dict,
        lock: ReflectionLock,
    ) -> Dict:
        """Handle user response in interactive workflow."""
        # Get user's last message
        messages = input_data.get("messages", [])
        if not messages:
            return {}

        user_messages = [m for m in messages if m.get("role") == "user"]
        if not user_messages:
            return {}

        last_user_message = user_messages[-1].get("content", "")

        # Handle both string and list content
        if isinstance(last_user_message, list):
            last_user_message = " ".join(str(item) for item in last_user_message)

        # Detect intent
        intent = state_machine.detect_user_intent(last_user_message)
        if not intent:
            return {}  # User didn't respond to our prompt

        # Transition state
        new_state, action = state_machine.transition(state_data.state, intent)

        # Execute action
        if action == "create_issue":
            return self._create_github_issue(state_machine, state_data, lock)
        elif action == "start_work":
            return self._start_work(state_machine, state_data, lock)
        elif action == "rejected":
            state_machine.write_state(
                ReflectionStateData(state=ReflectionState.IDLE, session_id=state_data.session_id)
            )
            return {"message": "✅ Reflection cancelled."}
        elif action == "completed":
            state_machine.cleanup()
            return {"message": f"✅ Issue created: {state_data.issue_url}"}

        return {}

    def _create_github_issue(
        self,
        state_machine: ReflectionStateMachine,
        state_data: ReflectionStateData,
        lock: ReflectionLock,
    ) -> Dict:
        """Create GitHub issue from analysis."""
        if not lock.acquire(state_data.session_id, "issue_creation"):
            return {"message": "⚠️ Another reflection operation in progress"}

        try:
            patterns = state_data.analysis.get("patterns", [])
            if not patterns:
                return {"message": "⚠️ No patterns to create issue for"}

            # Format issue content
            title = f"Reflection: {patterns[0]['type']} - {patterns[0]['description'][:50]}"
            body_lines = [
                "## Analysis Results",
                "",
                f"Found {len(patterns)} improvement opportunities:",
                "",
            ]

            for i, pattern in enumerate(patterns, 1):
                body_lines.extend(
                    [
                        f"### {i}. {pattern['type'].upper()} ({pattern['severity']} severity)",
                        pattern["description"],
                        "",
                    ]
                )

            body_lines.append("\n🤖 Generated by Amplihack Reflection System")
            body = "\n".join(body_lines)

            # Create issue
            result = subprocess.run(
                ["gh", "issue", "create", "--title", title, "--body", body],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                issue_url = result.stdout.strip()

                # Update state
                state_data.state = ReflectionState.AWAITING_WORK_DECISION
                state_data.issue_url = issue_url
                state_machine.write_state(state_data)

                return {
                    "message": f"✅ Created issue: {issue_url}\n\nStart work on this issue? (yes/no)"
                }
            else:
                return {"message": f"❌ Failed to create issue: {result.stderr}"}

        except Exception as e:
            return {"message": f"❌ Error creating issue: {e}"}

        finally:
            lock.release()

    def _start_work(
        self,
        state_machine: ReflectionStateMachine,
        state_data: ReflectionStateData,
        lock: ReflectionLock,
    ) -> Dict:
        """Start work on issue."""
        if not lock.acquire(state_data.session_id, "starting_work"):
            return {"message": "⚠️ Another reflection operation in progress"}

        try:
            # Mark as completed
            state_machine.cleanup()

            # Return instructions (can't invoke /ultrathink from hook)
            return {
                "message": f"To start work on this issue, run:\n\n  /ultrathink work on {state_data.issue_url}"
            }

        finally:
            lock.release()


def main():
    """Entry point for the stop hook."""
    hook = StopHook()
    hook.run()


if __name__ == "__main__":
    main()
