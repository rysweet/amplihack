#!/usr/bin/env python3
"""
Context Preservation System - amplihack Style
Preserves original user requests and conversation context to prevent loss during compaction.
"""

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

# Use clean import through dedicated paths module
from paths import get_project_root

try:
    from amplihack.utils.paths import FrameworkPathResolver
except ImportError:
    FrameworkPathResolver = None


class ContextPreserver:
    """Handles preservation and retrieval of conversation context and original requests."""

    def __init__(self, session_id: Optional[str] = None):
        """Initialize context preserver.

        Args:
            session_id: Optional session ID. If not provided, generates one from timestamp.
        """
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.project_root = get_project_root()
        self.session_dir = self.project_root / ".claude" / "runtime" / "logs" / self.session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)

    def extract_original_request(self, prompt: str) -> Dict[str, Any]:
        """Extract and structure original user requirements from initial prompt.

        Args:
            prompt: The initial user prompt/request

        Returns:
            Structured original request data
        """
        # Clean the prompt
        prompt = prompt.strip()

        # Extract explicit requirements using patterns
        requirements = self._parse_requirements(prompt)

        # Extract constraints
        constraints = self._parse_constraints(prompt)

        # Extract success criteria
        success_criteria = self._parse_success_criteria(prompt)

        # Extract target/goal
        target = self._parse_target(prompt)

        original_request = {
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "raw_prompt": prompt,
            "target": target,
            "requirements": requirements,
            "constraints": constraints,
            "success_criteria": success_criteria,
            "word_count": len(prompt.split()),
            "char_count": len(prompt),
            "extracted_at": datetime.now().isoformat(),
        }

        # Save to session logs
        self._save_original_request(original_request)

        return original_request

    def _parse_requirements(self, prompt: str) -> List[str]:
        """Parse explicit requirements from prompt."""
        requirements = []

        # Extract marked sections first
        for pattern in [r"\*\*(Target|Problem)\*\*:\s*(.+?)(?:\n|$)"]:
            for match in re.finditer(pattern, prompt, re.IGNORECASE):
                requirements.append(f"{match.group(1).upper()}: {match.group(2).strip()}")

        # Extract quantified statements (ALL, EVERY, etc.)
        quantifier_words = ["ALL", "EVERY", "EACH", "COMPLETE", "COMPREHENSIVE"]
        sentences = re.split(r"[.!?\n]+", prompt)
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10 and any(word in sentence.upper() for word in quantifier_words):
                if sentence not in requirements:
                    requirements.append(sentence)

        # Extract bullet points
        bullets = re.findall(r"[-•*]\s*([^\n]+)", prompt)
        for bullet in bullets:
            bullet = bullet.strip()
            if len(bullet) > 5 and bullet not in requirements:
                requirements.append(bullet)

        return requirements[:10]

    def _parse_constraints(self, prompt: str) -> List[str]:
        """Parse constraints from prompt."""
        constraints = []

        # Extract marked constraints
        constraint_match = re.search(
            r"\*\*Constraints?\*\*:\s*(.+?)(?:\n|$)", prompt, re.IGNORECASE
        )
        if constraint_match:
            constraints.append(constraint_match.group(1).strip())

        # Extract negative statements
        negative_patterns = ["must not", "cannot", "avoid", "limitation", "restriction"]
        sentences = re.split(r"[.!?\n]+", prompt)
        for sentence in sentences:
            sentence = sentence.strip()
            if any(pattern in sentence.lower() for pattern in negative_patterns):
                if len(sentence) > 5 and sentence not in constraints:
                    constraints.append(sentence)

        return constraints[:5]

    def _parse_success_criteria(self, prompt: str) -> List[str]:
        """Parse success criteria from prompt."""
        criteria = []

        # Simple pattern matching for common success indicators
        success_patterns = ["success criteria", "acceptance criteria", "goal", "outcome"]
        lines = prompt.split("\n")
        for line in lines:
            line = line.strip()
            if any(pattern in line.lower() for pattern in success_patterns) and ":" in line:
                parts = line.split(":", 1)
                if len(parts) > 1 and len(parts[1].strip()) > 5:
                    criteria.append(parts[1].strip())

        return criteria[:5]

    def _parse_target(self, prompt: str) -> str:
        """Parse the main target/goal from prompt."""
        # Check for explicit target
        target_match = re.search(r"\*\*Target\*\*:\s*(.+?)(?:\n|$)", prompt, re.IGNORECASE)
        if target_match:
            return target_match.group(1).strip()

        # Use first substantial sentence with action words
        action_words = ["implement", "create", "build", "add", "fix", "update", "improve"]
        sentences = re.split(r"[.!?]+", prompt)[:3]
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 15 and any(word in sentence.lower() for word in action_words):
                return sentence

        # Fallback to first non-empty sentence
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10:
                return sentence

        return "General development task"

    def _save_original_request(self, original_request: Dict[str, Any]):
        """Save original request to session logs."""
        request_file = self.session_dir / "ORIGINAL_REQUEST.md"

        content = f"""# Original User Request

**Session**: {self.session_id}
**Timestamp**: {original_request["timestamp"]}
**Target**: {original_request["target"]}

## Raw Request
```
{original_request["raw_prompt"]}
```

## Extracted Requirements
"""

        for i, req in enumerate(original_request["requirements"], 1):
            content += f"{i}. {req}\n"

        if original_request["constraints"]:
            content += "\n## Constraints\n"
            for i, constraint in enumerate(original_request["constraints"], 1):
                content += f"{i}. {constraint}\n"

        if original_request["success_criteria"]:
            content += "\n## Success Criteria\n"
            for i, criterion in enumerate(original_request["success_criteria"], 1):
                content += f"{i}. {criterion}\n"

        content += f"""
## Metadata
- Word count: {original_request["word_count"]}
- Character count: {original_request["char_count"]}
- Extracted at: {original_request["extracted_at"]}

## Usage Notes
This file preserves the original user requirements to prevent loss during context compaction.
All agents should receive this context to ensure user requirements are preserved throughout the workflow.
"""

        with open(request_file, "w") as f:
            f.write(content)

        # Also save as JSON for programmatic access
        json_file = self.session_dir / "original_request.json"
        with open(json_file, "w") as f:
            json.dump(original_request, f, indent=2)

    def get_original_request(self, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieve original request for a session.

        Args:
            session_id: Session ID to retrieve. Uses current session if not provided.

        Returns:
            Original request data or None if not found
        """
        target_session_id = session_id or self.session_id
        json_file = (
            self.project_root
            / ".claude"
            / "runtime"
            / "logs"
            / target_session_id
            / "original_request.json"
        )

        if not json_file.exists():
            return None

        try:
            with open(json_file) as f:
                return json.load(f)
        except Exception:
            return None

    def format_agent_context(self, original_request: Optional[Dict[str, Any]] = None) -> str:
        """Format original request as context for agent injection.

        Args:
            original_request: Original request data. Retrieves current session if not provided.

        Returns:
            Formatted context string for agent injection
        """
        if not original_request:
            original_request = self.get_original_request()

        if not original_request:
            return ""

        context_parts = [
            "## 🎯 ORIGINAL USER REQUEST - PRESERVE THESE REQUIREMENTS",
            "",
            f"**Target**: {original_request['target']}",
            "",
        ]

        if original_request["requirements"]:
            context_parts.append("**Requirements**:")
            for req in original_request["requirements"]:
                context_parts.append(f"• {req}")
            context_parts.append("")

        if original_request["constraints"]:
            context_parts.append("**Constraints**:")
            for constraint in original_request["constraints"]:
                context_parts.append(f"• {constraint}")
            context_parts.append("")

        if original_request["success_criteria"]:
            context_parts.append("**Success Criteria**:")
            for criterion in original_request["success_criteria"]:
                context_parts.append(f"• {criterion}")
            context_parts.append("")

        context_parts.extend(
            [
                "**CRITICAL**: These are the user's explicit requirements. Do NOT optimize them away.",
                "Your solution must address ALL requirements while following the constraints.",
                "━" * 60,
            ]
        )

        return "\n".join(context_parts)

    def export_conversation_transcript(self, conversation_data: List[Dict[str, Any]]) -> str:
        """Export complete conversation transcript (Amplifier-style).

        Args:
            conversation_data: List of conversation messages/interactions

        Returns:
            Path to exported transcript file
        """
        transcript_file = self.session_dir / "CONVERSATION_TRANSCRIPT.md"

        content = [
            f"# Conversation Transcript - Session {self.session_id}",
            "",
            f"**Exported**: {datetime.now().isoformat()}",
            f"**Messages**: {len(conversation_data)}",
            "",
            "━" * 80,
            "",
        ]

        for i, message in enumerate(conversation_data, 1):
            timestamp = message.get("timestamp", "Unknown")
            role = message.get("role", "Unknown")
            text = message.get("text", message.get("content", ""))

            content.append(f"## Message {i} - {role.upper()}")
            content.append(f"**Timestamp**: {timestamp}")
            content.append("")
            content.append(text)
            content.append("")
            content.append("─" * 40)
            content.append("")

        transcript_content = "\n".join(content)

        with open(transcript_file, "w") as f:
            f.write(transcript_content)

        return str(transcript_file)

    def get_latest_session_id(self) -> Optional[str]:
        """Get the most recent session ID."""
        logs_dir = self.project_root / ".claude" / "runtime" / "logs"
        if not logs_dir.exists():
            return None

        session_dirs = [
            d for d in logs_dir.iterdir() if d.is_dir() and re.match(r"\d{8}_\d{6}", d.name)
        ]
        if not session_dirs:
            return None

        return sorted(session_dirs)[-1].name


def create_context_preserver(session_id: Optional[str] = None) -> ContextPreserver:
    """Factory function to create a ContextPreserver instance."""
    return ContextPreserver(session_id)


# Example usage for testing
if __name__ == "__main__":
    # Test with sample prompt
    sample_prompt = """
Implement conversation transcript and original request preservation for amplihack.

**Target**: Context preservation system for original user requirements
**Problem**: Original user requests get lost during context compaction and aren't consistently passed to subagents
**Constraints**: Simple implementation based on Amplifier's proven approach

## Required Implementation

### 1. **Original Request Extraction & Preservation**
- Extract explicit user requirements from initial request
- Store in structured format accessible to all agents
- Include in `.claude/runtime/logs/<session_id>/ORIGINAL_REQUEST.md`
"""

    preserver = ContextPreserver()
    original_request = preserver.extract_original_request(sample_prompt)
    print("Original request extracted and saved!")
    print(f"Session ID: {preserver.session_id}")
    print(f"Target: {original_request['target']}")
    print(f"Requirements: {len(original_request['requirements'])}")

    # Test agent context formatting
    agent_context = preserver.format_agent_context(original_request)
    print("\nAgent context preview:")
    print(agent_context[:200] + "...")
