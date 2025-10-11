#!/usr/bin/env python3
"""
Claude Transcript Builder - Microsoft Amplifier Style
Builds comprehensive session documentation and transcripts for knowledge extraction.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from ..paths import get_project_root
except ImportError:
    # Fallback for testing or standalone usage
    from pathlib import Path

    def get_project_root():
        return Path(__file__).resolve().parents[4]


class ClaudeTranscriptBuilder:
    """Builds and manages Claude session transcripts for documentation and knowledge extraction."""

    def __init__(self, session_id: Optional[str] = None):
        """Initialize transcript builder.

        Args:
            session_id: Optional session ID. If not provided, generates one from timestamp.
        """
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.project_root = get_project_root()
        self.session_dir = self.project_root / ".claude" / "runtime" / "logs" / self.session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)

    def build_session_transcript(
        self, messages: List[Dict[str, Any]], metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build a comprehensive session transcript.

        Args:
            messages: List of conversation messages with role, content, timestamp
            metadata: Optional session metadata

        Returns:
            Path to the created transcript file
        """
        transcript_content = self._generate_transcript_content(messages, metadata)
        transcript_file = self.session_dir / "CONVERSATION_TRANSCRIPT.md"
        transcript_file.write_text(transcript_content)

        # Also create a JSON version for programmatic access
        self._create_json_transcript(messages, metadata)

        return str(transcript_file)

    def build_session_summary(
        self, messages: List[Dict[str, Any]], metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build a session summary with key statistics and insights.

        Args:
            messages: List of conversation messages
            metadata: Optional session metadata

        Returns:
            Session summary dictionary
        """
        summary = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "message_count": len(messages),
            "total_characters": sum(len(msg.get("content", "")) for msg in messages),
            "total_words": sum(len(str(msg.get("content", "")).split()) for msg in messages),
            "duration_estimate": self._estimate_session_duration(messages),
            "tools_used": self._extract_tools_used(messages),
            "key_topics": self._extract_key_topics(messages),
            "outcomes": self._extract_outcomes(messages),
            "metadata": metadata or {},
        }

        # Save summary
        summary_file = self.session_dir / "session_summary.json"
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)

        return summary

    def export_for_codex(
        self, messages: List[Dict[str, Any]], metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Export session data in a format optimized for codex/knowledge extraction.

        Args:
            messages: List of conversation messages
            metadata: Optional session metadata

        Returns:
            Path to the codex export file
        """
        codex_data = {
            "session_metadata": {
                "id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "source": "claude_transcript_builder",
                "version": "1.0",
            },
            "conversation_flow": self._extract_conversation_flow(messages),
            "knowledge_artifacts": self._extract_knowledge_artifacts(messages),
            "patterns_detected": self._detect_patterns(messages),
            "decisions_made": self._extract_decisions(messages),
            "tools_usage": self._analyze_tools_usage(messages),
            "outcomes_achieved": self._extract_detailed_outcomes(messages),
            "raw_messages": self._sanitize_messages_for_export(messages),
        }

        codex_file = self.session_dir / "codex_export.json"
        with open(codex_file, "w") as f:
            json.dump(codex_data, f, indent=2)

        return str(codex_file)

    def _generate_transcript_content(
        self, messages: List[Dict[str, Any]], metadata: Optional[Dict[str, Any]]
    ) -> str:
        """Generate markdown transcript content."""
        content = f"""# Conversation Transcript - {self.session_id}

**Session ID**: {self.session_id}
**Timestamp**: {datetime.now().isoformat()}
**Messages**: {len(messages)}
**Total Words**: {sum(len(str(msg.get("content", "")).split()) for msg in messages)}

## Session Overview

{self._generate_session_overview(messages, metadata)}

## Conversation Flow

"""

        for i, msg in enumerate(messages, 1):
            role = msg.get("role", "unknown")
            msg_content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")

            content += f"\n### Message {i} - {role.title()}\n"
            if timestamp:
                content += f"**Time**: {timestamp}\n"
            content += f"\n{msg_content}\n\n"

        content += f"""
## Session Statistics

- **Duration**: {self._estimate_session_duration(messages)}
- **Tools Used**: {", ".join(self._extract_tools_used(messages))}
- **Key Topics**: {", ".join(self._extract_key_topics(messages)[:5])}

---
Generated by Claude Transcript Builder at {datetime.now().isoformat()}
"""

        return content

    def _create_json_transcript(
        self, messages: List[Dict[str, Any]], metadata: Optional[Dict[str, Any]]
    ) -> None:
        """Create JSON version of transcript for programmatic access."""
        json_data = {
            "session_id": self.session_id,
            "created_at": datetime.now().isoformat(),
            "metadata": metadata or {},
            "statistics": {
                "message_count": len(messages),
                "total_words": sum(len(str(msg.get("content", "")).split()) for msg in messages),
                "tools_used": self._extract_tools_used(messages),
            },
            "messages": messages,
        }

        json_file = self.session_dir / "conversation_transcript.json"
        with open(json_file, "w") as f:
            json.dump(json_data, f, indent=2)

    def _generate_session_overview(
        self, messages: List[Dict[str, Any]], metadata: Optional[Dict[str, Any]]
    ) -> str:
        """Generate an overview of the session."""
        if not messages:
            return "No messages in this session."

        first_msg = messages[0].get("content", "")
        tools_used = self._extract_tools_used(messages)
        key_topics = self._extract_key_topics(messages)

        overview = f"This session involved {len(messages)} message exchanges"
        if tools_used:
            overview += f" using tools: {', '.join(tools_used[:3])}"
        if key_topics:
            overview += f". Key topics discussed: {', '.join(key_topics[:3])}"

        if len(first_msg) > 100:
            overview += f"\n\nInitial request: {first_msg[:100]}..."

        return overview

    def _estimate_session_duration(self, messages: List[Dict[str, Any]]) -> str:
        """Estimate session duration based on message count and complexity."""
        if not messages:
            return "0 minutes"

        # Simple heuristic: ~2-3 minutes per message exchange
        estimated_minutes = len(messages) * 2.5

        if estimated_minutes < 60:
            return f"{int(estimated_minutes)} minutes"
        hours = int(estimated_minutes // 60)
        minutes = int(estimated_minutes % 60)
        return f"{hours}h {minutes}m"

    def _extract_tools_used(self, messages: List[Dict[str, Any]]) -> List[str]:
        """Extract unique tools mentioned or used in the conversation."""
        tools = set()

        for msg in messages:
            content = str(msg.get("content", ""))

            # Look for tool mentions
            tool_patterns = [
                r"<function_calls>.*?<invoke name=\"([^\"]+)\"",
                r"`([A-Z][a-zA-Z]+)`",  # Capitalized tool names in backticks
                r"(\w+) tool",
                r"using (\w+)",
            ]

            for pattern in tool_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    if len(match) > 2 and len(match) < 20:
                        tools.add(match)

        return sorted(list(tools))

    def _extract_key_topics(self, messages: List[Dict[str, Any]]) -> List[str]:
        """Extract key topics discussed in the conversation."""
        topics = set()

        for msg in messages:
            content = str(msg.get("content", ""))

            # Extract nouns and technical terms
            words = re.findall(r"\b[A-Z][a-z]{3,}|[a-z]{4,}(?:_[a-z]+)*\b", content)

            # Filter for likely topic words
            technical_words = [
                w
                for w in words
                if len(w) > 4
                and w.lower()
                not in {
                    "this",
                    "that",
                    "with",
                    "from",
                    "have",
                    "will",
                    "been",
                    "would",
                    "could",
                    "should",
                    "there",
                    "where",
                    "their",
                }
            ]

            for word in technical_words[:10]:  # Limit per message
                topics.add(word.lower())

        return sorted(list(topics))[:10]  # Return top 10

    def _extract_outcomes(self, messages: List[Dict[str, Any]]) -> List[str]:
        """Extract achieved outcomes from the conversation."""
        outcomes = []

        for msg in messages:
            content = str(msg.get("content", ""))

            # Look for completion indicators
            outcome_patterns = [
                r"✅.*",
                r"Successfully (.*?)\.?$",
                r"Completed (.*?)\.?$",
                r"Fixed (.*?)\.?$",
                r"Implemented (.*?)\.?$",
                r"Created (.*?)\.?$",
            ]

            for pattern in outcome_patterns:
                matches = re.findall(pattern, content, re.MULTILINE | re.IGNORECASE)
                for match in matches:
                    if len(match) > 5:  # Filter out very short matches
                        outcomes.append(match.strip())

        return outcomes[:5]  # Return top 5 outcomes

    def _extract_conversation_flow(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract conversation flow for codex analysis."""
        flow = []

        for i, msg in enumerate(messages):
            flow_item = {
                "sequence": i + 1,
                "role": msg.get("role", "unknown"),
                "timestamp": msg.get("timestamp", ""),
                "message_type": self._classify_message_type(msg),
                "word_count": len(str(msg.get("content", "")).split()),
                "tools_mentioned": self._extract_tools_from_message(msg),
                "key_phrases": self._extract_key_phrases(msg),
            }
            flow.append(flow_item)

        return flow

    def _extract_knowledge_artifacts(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract knowledge artifacts like code snippets, configurations, etc."""
        artifacts = []

        for i, msg in enumerate(messages):
            content = str(msg.get("content", ""))

            # Extract code blocks
            code_blocks = re.findall(r"```(\w+)?\n(.*?)\n```", content, re.DOTALL)
            for lang, code in code_blocks:
                artifacts.append(
                    {
                        "type": "code_block",
                        "language": lang or "unknown",
                        "content": code.strip(),
                        "message_index": i,
                        "size": len(code),
                    }
                )

            # Extract file paths
            file_paths = re.findall(r"([/\w.-]+\.\w+)", content)
            for path in file_paths:
                if len(path) > 5:  # Filter out short false positives
                    artifacts.append({"type": "file_path", "content": path, "message_index": i})

        return artifacts

    def _detect_patterns(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect patterns in the conversation."""
        patterns = []

        # Detect tool usage patterns
        tool_sequence = []
        for msg in messages:
            tools = self._extract_tools_from_message(msg)
            if tools:
                tool_sequence.extend(tools)

        if tool_sequence:
            patterns.append(
                {
                    "type": "tool_usage_pattern",
                    "sequence": tool_sequence,
                    "frequency": len(tool_sequence),
                }
            )

        # Detect error-fix cycles
        error_keywords = ["error", "failed", "exception", "issue", "problem"]
        fix_keywords = ["fixed", "resolved", "solved", "corrected", "updated"]

        error_fix_cycles = 0
        for i in range(len(messages) - 1):
            msg_content = str(messages[i].get("content", "")).lower()
            next_msg_content = str(messages[i + 1].get("content", "")).lower()

            has_error = any(keyword in msg_content for keyword in error_keywords)
            has_fix = any(keyword in next_msg_content for keyword in fix_keywords)

            if has_error and has_fix:
                error_fix_cycles += 1

        if error_fix_cycles > 0:
            patterns.append(
                {
                    "type": "error_fix_cycle",
                    "count": error_fix_cycles,
                    "frequency": error_fix_cycles / len(messages),
                }
            )

        return patterns

    def _extract_decisions(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract decisions made during the conversation."""
        decisions = []

        decision_patterns = [
            r"I'll (.*?)\.?$",
            r"Let's (.*?)\.?$",
            r"We should (.*?)\.?$",
            r"The approach is to (.*?)\.?$",
            r"Decision: (.*?)\.?$",
        ]

        for i, msg in enumerate(messages):
            content = str(msg.get("content", ""))

            for pattern in decision_patterns:
                matches = re.findall(pattern, content, re.MULTILINE | re.IGNORECASE)
                for match in matches:
                    if len(match) > 10:  # Filter out very short decisions
                        decisions.append(
                            {
                                "decision": match.strip(),
                                "message_index": i,
                                "role": msg.get("role", "unknown"),
                            }
                        )

        return decisions[:10]  # Return top 10 decisions

    def _analyze_tools_usage(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze tools usage patterns."""
        tools_analysis = {
            "total_tool_calls": 0,
            "unique_tools": set(),
            "tool_frequency": {},
            "tool_sequence": [],
        }

        for msg in messages:
            tools = self._extract_tools_from_message(msg)
            for tool in tools:
                tools_analysis["total_tool_calls"] += 1
                tools_analysis["unique_tools"].add(tool)
                tools_analysis["tool_frequency"][tool] = (
                    tools_analysis["tool_frequency"].get(tool, 0) + 1
                )
                tools_analysis["tool_sequence"].append(tool)

        # Convert set to list for JSON serialization
        tools_analysis["unique_tools"] = list(tools_analysis["unique_tools"])

        return tools_analysis

    def _extract_detailed_outcomes(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract detailed outcomes with context."""
        outcomes = []

        success_patterns = [
            (r"✅ (.*)", "success"),
            (r"Successfully (.*)", "success"),
            (r"Completed (.*)", "completion"),
            (r"Fixed (.*)", "fix"),
            (r"❌ (.*)", "failure"),
            (r"Error: (.*)", "error"),
        ]

        for i, msg in enumerate(messages):
            content = str(msg.get("content", ""))

            for pattern, outcome_type in success_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    outcomes.append(
                        {
                            "type": outcome_type,
                            "description": match.strip(),
                            "message_index": i,
                            "timestamp": msg.get("timestamp", ""),
                        }
                    )

        return outcomes

    def _sanitize_messages_for_export(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sanitize messages for safe export."""
        sanitized = []

        for msg in messages:
            sanitized_msg = {
                "role": msg.get("role", "unknown"),
                "content": str(msg.get("content", ""))[:5000],  # Limit content length
                "timestamp": msg.get("timestamp", ""),
                "word_count": len(str(msg.get("content", "")).split()),
            }
            sanitized.append(sanitized_msg)

        return sanitized

    def _classify_message_type(self, msg: Dict[str, Any]) -> str:
        """Classify the type of message."""
        content = str(msg.get("content", "")).lower()
        role = msg.get("role", "")

        if role == "user":
            if "?" in content:
                return "question"
            if any(word in content for word in ["please", "can you", "could you"]):
                return "request"
            return "statement"
        if role == "assistant":
            if "```" in content:
                return "code_response"
            if "<function_calls>" in content:
                return "tool_usage"
            if "✅" in content or "❌" in content:
                return "status_update"
            return "explanation"
        return "unknown"

    def _extract_tools_from_message(self, msg: Dict[str, Any]) -> List[str]:
        """Extract tools mentioned in a specific message."""
        content = str(msg.get("content", ""))
        tools = []

        # Extract function calls
        function_calls = re.findall(r'<invoke name="([^"]+)"', content)
        tools.extend(function_calls)

        return tools

    def _extract_key_phrases(self, msg: Dict[str, Any]) -> List[str]:
        """Extract key phrases from a message."""
        content = str(msg.get("content", ""))

        # Extract phrases in quotes
        quoted_phrases = re.findall(r'"([^"]{10,50})"', content)

        # Extract technical terms (camelCase, snake_case, etc.)
        technical_terms = re.findall(r"\b[a-z]+(?:[A-Z][a-z]*|_[a-z]+)+\b", content)

        key_phrases = quoted_phrases + technical_terms
        return key_phrases[:5]  # Return top 5 key phrases
