#!/usr/bin/env python3
"""
Session reflection module for detecting improvement opportunities.
Prevents infinite loops via CLAUDE_REFLECTION_MODE environment variable.
"""

import json
import os
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def find_claude_trace_logs(session_dir: Path, project_root: Path) -> List[Path]:
    """Find claude-trace logs for a session.

    Args:
        session_dir: Session log directory
        project_root: Project root directory

    Returns:
        List of paths to claude-trace .jsonl files
    """
    trace_logs = []

    # Check session directory for trace logs
    if session_dir.exists():
        trace_logs.extend(session_dir.glob("*.jsonl"))

    # Check global .claude-trace directory
    global_trace_dir = project_root / ".claude-trace"
    if global_trace_dir.exists():
        # Look for recent trace logs (within last hour of session)
        trace_logs.extend(global_trace_dir.glob("*.jsonl"))

    return trace_logs


class SessionReflector:
    """Simple pattern detector for session improvement opportunities"""

    PATTERNS = {
        "repeated_commands": {
            "threshold": 3,
            "action": "Consider creating a tool or script for this repeated action",
        },
        "error_retry": {
            "keywords": ["error", "failed", "retry", "again", "exception", "traceback"],
            "threshold": 3,
            "action": "Investigate root cause and add better error handling",
        },
        "long_duration": {
            "threshold_messages": 100,  # ~50 back-and-forth exchanges
            "action": "Consider breaking into smaller, focused tasks",
        },
        "frustration": {
            "keywords": [
                "doesn't work",
                "still failing",
                "not working",
                "broken",
                "stuck",
                "confused",
                "why isn't",
                "should be",
            ],
            "action": "Review approach and consider alternative solution",
        },
        "repeated_reads": {
            "threshold": 5,
            "action": "Consider caching or extracting relevant parts once",
        },
    }

    def __init__(self):
        # Prevent loops via environment variable
        self.enabled = os.environ.get("CLAUDE_REFLECTION_MODE") != "1"

    def _analyze_trace_logs(self, trace_logs: List[Path]) -> Optional[Dict]:
        """Analyze claude-trace logs for additional patterns.

        Args:
            trace_logs: List of paths to claude-trace .jsonl files

        Returns:
            Dict with trace analysis findings, or None if no patterns found
        """
        if not trace_logs:
            return None

        findings = {
            "api_errors": [],
            "rate_limits": [],
            "slow_requests": [],
            "token_usage": {"total_input": 0, "total_output": 0},
        }

        for log_path in trace_logs:
            try:
                with open(log_path) as f:
                    for line in f:
                        try:
                            entry = json.loads(line)

                            # Check for API errors
                            if entry.get("error"):
                                findings["api_errors"].append(
                                    {
                                        "error": entry["error"],
                                        "timestamp": entry.get("timestamp"),
                                    }
                                )

                            # Check for rate limiting
                            if "rate_limit" in str(entry).lower() or entry.get("status") == 429:
                                findings["rate_limits"].append(
                                    {"timestamp": entry.get("timestamp")}
                                )

                            # Check for slow requests (> 30 seconds)
                            duration = entry.get("duration_ms", 0)
                            if duration > 30000:
                                findings["slow_requests"].append(
                                    {
                                        "duration_ms": duration,
                                        "timestamp": entry.get("timestamp"),
                                    }
                                )

                            # Accumulate token usage
                            if "usage" in entry:
                                usage = entry["usage"]
                                findings["token_usage"]["total_input"] += usage.get(
                                    "input_tokens", 0
                                )
                                findings["token_usage"]["total_output"] += usage.get(
                                    "output_tokens", 0
                                )

                        except json.JSONDecodeError:
                            continue  # Skip invalid JSON lines

            except (OSError, PermissionError):
                continue  # Skip inaccessible files

        # Return None if no significant findings
        has_findings = (
            findings["api_errors"]
            or findings["rate_limits"]
            or findings["slow_requests"]
            or findings["token_usage"]["total_input"] > 0
        )

        return findings if has_findings else None

    def analyze_session(
        self, messages: List[Dict], trace_logs: Optional[List[Path]] = None
    ) -> Dict[str, Any]:
        """Extract patterns from session messages"""
        if not self.enabled:
            return {"skipped": True, "reason": "reflection_loop_prevention"}

        findings = {
            "timestamp": datetime.now().isoformat(),
            "patterns": [],
            "metrics": self._extract_metrics(messages),
            "suggestions": [],
        }

        # Detect repeated tool uses
        tool_uses = self._extract_tool_uses(messages)
        repeated = self._find_repetitions(tool_uses)
        if repeated:
            for tool, count in repeated.items():
                findings["patterns"].append(
                    {
                        "type": "repeated_tool_use",
                        "tool": tool,
                        "count": count,
                        "suggestion": f"Used {tool} {count} times. {self.PATTERNS['repeated_commands']['action']}",
                    }
                )

        # Detect error patterns
        errors = self._find_error_patterns(messages)
        if errors:
            findings["patterns"].append(
                {
                    "type": "error_patterns",
                    "count": errors["count"],
                    "samples": errors.get("samples", [])[:3],  # First 3 examples
                    "suggestion": self.PATTERNS["error_retry"]["action"],
                }
            )

        # Check for long session
        if len(messages) > self.PATTERNS["long_duration"]["threshold_messages"]:
            findings["patterns"].append(
                {
                    "type": "long_session",
                    "message_count": len(messages),
                    "suggestion": self.PATTERNS["long_duration"]["action"],
                }
            )

        # Detect frustration indicators
        frustration = self._find_frustration_patterns(messages)
        if frustration:
            findings["patterns"].append(
                {
                    "type": "user_frustration",
                    "indicators": frustration["count"],
                    "suggestion": self.PATTERNS["frustration"]["action"],
                }
            )

        # Analyze claude-trace logs if provided
        if trace_logs:
            trace_analysis = self._analyze_trace_logs(trace_logs)
            if trace_analysis:
                findings["trace_analysis"] = trace_analysis

                # Add trace-based patterns
                if trace_analysis.get("api_errors"):
                    findings["patterns"].append(
                        {
                            "type": "api_errors",
                            "count": len(trace_analysis["api_errors"]),
                            "samples": trace_analysis["api_errors"][:3],
                            "suggestion": "Review API error patterns and add retry logic or error handling",
                        }
                    )

                if trace_analysis.get("rate_limits"):
                    findings["patterns"].append(
                        {
                            "type": "rate_limiting",
                            "count": len(trace_analysis["rate_limits"]),
                            "suggestion": "Consider adding rate limit backoff or reducing request frequency",
                        }
                    )

                if trace_analysis.get("slow_requests"):
                    findings["patterns"].append(
                        {
                            "type": "slow_requests",
                            "count": len(trace_analysis["slow_requests"]),
                            "suggestion": "Optimize prompts or break down complex requests",
                        }
                    )

        # Add summary suggestions
        if findings["patterns"]:
            findings["suggestions"] = self._generate_suggestions(findings["patterns"])

        return findings

    def _extract_tool_uses(self, messages: List[Dict]) -> List[str]:
        """Extract tool use patterns from messages"""
        tools = []
        for msg in messages:
            if msg.get("role") == "assistant":
                content = str(msg.get("content", ""))

                # Look for tool use patterns
                if "<function_calls>" in content:
                    if "Bash" in content:
                        tools.append("bash")
                    if "Read" in content:
                        tools.append("read")
                    if "Write" in content:
                        tools.append("write")
                    if "Edit" in content:
                        tools.append("edit")
                    if "Task" in content:
                        tools.append("task")
                    if "TodoWrite" in content:
                        tools.append("todo")
                    if "Glob" in content:
                        tools.append("glob")
                    if "Grep" in content:
                        tools.append("grep")

        return tools

    def _find_repetitions(self, items: List[str]) -> Dict[str, int]:
        """Find items repeated more than threshold times"""
        if not items:
            return {}

        counts = Counter(items)
        threshold = self.PATTERNS["repeated_commands"]["threshold"]
        repeated = {k: v for k, v in counts.items() if v >= threshold}
        return repeated

    def _find_error_patterns(self, messages: List[Dict]) -> Optional[Dict]:
        """Detect error-related patterns"""
        error_count = 0
        error_samples = []
        keywords = self.PATTERNS["error_retry"]["keywords"]

        for msg in messages:
            content = str(msg.get("content", "")).lower()
            if any(kw in content for kw in keywords):
                error_count += 1
                # Capture a sample of the error
                if len(error_samples) < 3:  # Keep first 3 examples
                    sample = content[:200]  # First 200 chars
                    if sample not in error_samples:
                        error_samples.append(sample)

        if error_count >= self.PATTERNS["error_retry"]["threshold"]:
            return {"count": error_count, "samples": error_samples}
        return None

    def _find_frustration_patterns(self, messages: List[Dict]) -> Optional[Dict]:
        """Detect user frustration indicators"""
        frustration_count = 0
        keywords = self.PATTERNS["frustration"]["keywords"]

        for msg in messages:
            if msg.get("role") == "user":
                content = str(msg.get("content", "")).lower()
                if any(kw in content for kw in keywords):
                    frustration_count += 1

        if frustration_count >= 2:  # Lower threshold for frustration
            return {"count": frustration_count}
        return None

    def _extract_metrics(self, messages: List[Dict]) -> Dict:
        """Basic session metrics"""
        tool_count = 0
        for msg in messages:
            if msg.get("role") == "assistant":
                content = str(msg.get("content", ""))
                if "<function_calls>" in content:
                    tool_count += 1

        return {
            "total_messages": len(messages),
            "user_messages": sum(1 for m in messages if m.get("role") == "user"),
            "assistant_messages": sum(1 for m in messages if m.get("role") == "assistant"),
            "tool_uses": tool_count,
        }

    def _generate_suggestions(self, patterns: List[Dict]) -> List[str]:
        """Generate actionable suggestions from patterns"""
        suggestions = []

        # Priority suggestions based on patterns found
        pattern_types = [p["type"] for p in patterns]

        if "user_frustration" in pattern_types:
            suggestions.insert(
                0,
                "HIGH PRIORITY: User frustration detected. Consider reviewing the approach with the architect agent.",
            )

        if "error_patterns" in pattern_types:
            suggestions.append(
                "Multiple errors encountered. Consider adding error handling or using the pre-commit-diagnostic agent."
            )

        if "repeated_tool_use" in pattern_types:
            repeated_tools = [p for p in patterns if p["type"] == "repeated_tool_use"]
            for tool_pattern in repeated_tools:
                if tool_pattern["tool"] == "bash" and tool_pattern["count"] >= 5:
                    suggestions.append(
                        "Consider creating a script to automate these bash commands."
                    )
                elif tool_pattern["tool"] == "read" and tool_pattern["count"] >= 5:
                    suggestions.append(
                        "Consider caching file contents or using a more targeted search."
                    )

        if "long_session" in pattern_types:
            suggestions.append(
                "Long session detected. Future tasks could benefit from better decomposition using TodoWrite."
            )

        return suggestions


def save_reflection_summary(analysis: Dict, output_dir: Path) -> Optional[Path]:
    """Save reflection analysis to a summary file"""
    if analysis.get("skipped"):
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_file = output_dir / f"reflection_{timestamp}.json"

    # Create a human-readable summary
    summary = {
        "session_time": analysis["timestamp"],
        "metrics": analysis["metrics"],
        "patterns_found": len(analysis.get("patterns", [])),
        "patterns": analysis.get("patterns", []),
        "suggestions": analysis.get("suggestions", []),
        "action_items": [],
    }

    # Generate action items from patterns
    for pattern in analysis.get("patterns", []):
        if pattern.get("suggestion"):
            summary["action_items"].append(
                {
                    "issue": pattern["type"],
                    "action": pattern["suggestion"],
                    "priority": "high" if pattern["type"] == "user_frustration" else "normal",
                }
            )

    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)

    return summary_file
