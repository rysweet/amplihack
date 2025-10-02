"""Lightweight per-response analysis using Claude Code SDK."""

import json
import time
from typing import Dict, List, Optional


class LightweightAnalyzer:
    """Fast analysis of recent responses for improvement opportunities."""

    def __init__(self):
        """Initialize analyzer."""
        self.max_duration = 5.0  # seconds

    def analyze_recent_responses(
        self, messages: List[Dict], tool_logs: Optional[List[str]] = None
    ) -> Dict:
        """Analyze last 2 responses for patterns.

        Args:
            messages: Full transcript messages
            tool_logs: Recent tool use log lines

        Returns:
            {
                "patterns": [{type, description, severity}],
                "summary": str,
                "elapsed_seconds": float
            }
        """
        start_time = time.time()

        # Extract last 2 assistant messages
        assistant_messages = [m for m in messages if m.get("role") == "assistant"]
        recent_messages = (
            assistant_messages[-2:] if len(assistant_messages) >= 2 else assistant_messages
        )

        if len(recent_messages) < 1:
            return {
                "patterns": [],
                "summary": "Not enough messages to analyze",
                "elapsed_seconds": time.time() - start_time,
            }

        # Build analysis prompt
        prompt = self._build_analysis_prompt(recent_messages, tool_logs or [])

        # Call Claude SDK (placeholder - user will specify actual SDK method)
        try:
            patterns = self._call_claude_sdk(prompt)
            elapsed = time.time() - start_time

            return {
                "patterns": patterns,
                "summary": f"Found {len(patterns)} patterns in {elapsed:.1f}s",
                "elapsed_seconds": elapsed,
            }
        except TimeoutError:
            return {
                "patterns": [],
                "summary": "Analysis timed out",
                "elapsed_seconds": time.time() - start_time,
            }
        except Exception as e:
            return {
                "patterns": [],
                "summary": f"Analysis failed: {e}",
                "elapsed_seconds": time.time() - start_time,
            }

    def _build_analysis_prompt(self, messages: List[Dict], tool_logs: List[str]) -> str:
        """Build concise analysis prompt."""
        # Extract message contents
        message_contents = []
        for msg in messages:
            content = msg.get("content", "")
            # Handle both string and list content formats
            if isinstance(content, list):
                content = "\n".join(str(item) for item in content)
            message_contents.append(content[:500])  # Truncate long messages

        # Extract recent tool logs (last 10 lines)
        recent_tool_logs = tool_logs[-10:] if tool_logs else []

        return f"""Analyze these recent Claude Code interactions for improvement opportunities.

Recent Messages:
{json.dumps(message_contents, indent=2)}

Recent Tool Usage:
{chr(10).join(recent_tool_logs)}

Identify ONLY:
1. Errors or failures that occurred
2. Obvious inefficiencies in workflow
3. Repeated patterns that could be automated

Be concise and specific. Return JSON format:
{{
  "patterns": [
    {{
      "type": "error|inefficiency|automation_opportunity",
      "description": "Brief description of the pattern",
      "severity": "low|medium|high"
    }}
  ]
}}

If no issues found, return: {{"patterns": []}}
"""

    def _call_claude_sdk(self, prompt: str) -> List[Dict]:
        """Call Claude Code SDK for analysis.

        TODO: User needs to specify which Claude Code SDK method to use.
        This is a placeholder that does simple pattern matching for now.
        """
        # PLACEHOLDER: Replace with actual Claude Code SDK call
        # For now, return empty to avoid blocking

        # Simple fallback pattern detection
        patterns = []
        prompt_lower = prompt.lower()

        if "error" in prompt_lower or "failed" in prompt_lower:
            patterns.append(
                {
                    "type": "error",
                    "description": "Error detected in recent interaction",
                    "severity": "high",
                }
            )

        if "timeout" in prompt_lower:
            patterns.append(
                {
                    "type": "inefficiency",
                    "description": "Timeout detected, may indicate performance issue",
                    "severity": "medium",
                }
            )

        return patterns
