"""Context extraction brick for intelligent snapshot creation.

This module extracts essential context from conversation history,
focusing on requirements, decisions, state, and open items rather than
full conversation dumps.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import ContextSnapshot

# Default snapshot storage location
DEFAULT_SNAPSHOT_DIR = ".claude/runtime/context-snapshots"


class ContextExtractor:
    """Extracts essential context for snapshot preservation.

    This brick intelligently extracts key information from conversations:
    - Original user requirements
    - Key decisions and trade-offs
    - Current implementation state
    - Open questions and blockers
    - Tools used during the session

    Attributes:
        snapshot_dir: Directory where snapshots are stored
    """

    def __init__(self, snapshot_dir: Optional[Path] = None):
        """Initialize context extractor.

        Args:
            snapshot_dir: Directory for snapshots (default: .claude/runtime/context-snapshots)
        """
        if snapshot_dir is None:
            # Try to find project root
            cwd = Path.cwd()
            if (cwd / ".claude").exists():
                self.snapshot_dir = cwd / DEFAULT_SNAPSHOT_DIR
            else:
                # Fallback to current directory
                self.snapshot_dir = Path(DEFAULT_SNAPSHOT_DIR)
        else:
            self.snapshot_dir = snapshot_dir

        # Ensure directory exists
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

    def extract_from_conversation(self, conversation_data: List[Dict]) -> Dict[str, Any]:
        """Extract essential context from conversation history.

        Args:
            conversation_data: List of conversation messages with 'role' and 'content'

        Returns:
            Dict with structured context components:
            - original_requirements: User's initial request
            - key_decisions: List of decisions with rationale
            - implementation_state: Current progress summary
            - open_items: Pending questions/blockers
            - tools_used: List of tools invoked

        Example:
            >>> messages = [
            ...     {'role': 'user', 'content': 'Build an API'},
            ...     {'role': 'assistant', 'content': 'I decided to use FastAPI...'},
            ...     {'role': 'tool_use', 'tool_name': 'Write', ...}
            ... ]
            >>> context = extractor.extract_from_conversation(messages)
            >>> context['original_requirements']
            'Build an API'
        """
        # Extract original requirements (first user message)
        original_requirements = self._extract_original_requirements(conversation_data)

        # Extract key decisions (look for decision keywords)
        key_decisions = self._extract_key_decisions(conversation_data)

        # Extract implementation state (summarize what's been done)
        implementation_state = self._extract_implementation_state(conversation_data)

        # Extract open items (questions, TODOs, blockers)
        open_items = self._extract_open_items(conversation_data)

        # Extract tools used
        tools_used = self._extract_tools_used(conversation_data)

        return {
            "original_requirements": original_requirements,
            "key_decisions": key_decisions,
            "implementation_state": implementation_state,
            "open_items": open_items,
            "tools_used": tools_used,
        }

    def _extract_original_requirements(self, conversation_data: List[Dict]) -> str:
        """Extract first user message as original requirements."""
        for message in conversation_data:
            if message.get("role") == "user":
                content = message.get("content", "")
                # Take first 500 chars if very long
                return content[:500] + ("..." if len(content) > 500 else "")
        return "No user requirements found"

    def _extract_key_decisions(self, conversation_data: List[Dict]) -> List[Dict[str, str]]:
        """Extract key decisions from assistant messages."""
        decisions = []
        decision_keywords = ["decided", "chosen", "selected", "opted", "approach"]

        for message in conversation_data:
            if message.get("role") == "assistant":
                content = message.get("content", "").lower()
                # Look for decision indicators
                for keyword in decision_keywords:
                    if keyword in content:
                        # Extract sentence containing decision
                        sentences = message.get("content", "").split(".")
                        for sentence in sentences:
                            if keyword in sentence.lower() and len(sentence.strip()) > 10:
                                decisions.append(
                                    {
                                        "decision": sentence.strip(),
                                        "rationale": "Extracted from conversation",
                                        "alternatives": "Not captured",
                                    }
                                )
                                break
                        break

        # Limit to top 5 decisions
        return decisions[:5]

    def _extract_implementation_state(self, conversation_data: List[Dict]) -> str:
        """Summarize current implementation state from tool usage."""
        tool_usage_count = sum(
            1 for msg in conversation_data if msg.get("role") == "tool_use" or "tool_name" in msg
        )

        files_modified = []
        for message in conversation_data:
            if message.get("tool_name") in ["Write", "Edit"]:
                file_path = message.get("file_path", message.get("parameters", {}).get("file_path"))
                if file_path:
                    files_modified.append(Path(file_path).name)

        state = f"Tools invoked: {tool_usage_count}\n"
        if files_modified:
            state += f"Files modified: {', '.join(set(files_modified[:10]))}"
            if len(files_modified) > 10:
                state += f" and {len(files_modified) - 10} more"

        return state

    def _extract_open_items(self, conversation_data: List[Dict]) -> List[str]:
        """Extract open questions and blockers."""
        open_items = []
        question_indicators = ["?", "todo", "need to", "should we", "blocker", "pending"]

        for message in conversation_data:
            content = message.get("content", "")
            content_lower = content.lower()

            # Look for questions
            if "?" in content:
                sentences = content.split("?")
                for sentence in sentences[:-1]:  # Exclude last split (after final ?)
                    question = sentence.strip().split(".")[-1] + "?"
                    if len(question) > 10:
                        open_items.append(question.strip())

            # Look for TODOs and blockers
            for indicator in question_indicators[1:]:
                if indicator in content_lower:
                    # Extract relevant sentence
                    sentences = content.split(".")
                    for sentence in sentences:
                        if indicator in sentence.lower() and len(sentence.strip()) > 10:
                            open_items.append(sentence.strip())
                            break

        # Limit to top 10 unique items
        return list(set(open_items))[:10]

    def _extract_tools_used(self, conversation_data: List[Dict]) -> List[str]:
        """Extract list of unique tools used."""
        tools = set()
        for message in conversation_data:
            tool_name = message.get("tool_name")
            if tool_name:
                tools.add(tool_name)
            # Also check for tool results
            if message.get("role") == "tool_result":
                # Tool name might be in parent context
                pass

        return sorted(list(tools))

    def create_snapshot(self, context: Dict[str, Any], name: Optional[str] = None) -> Path:
        """Create a named context snapshot.

        Args:
            context: Extracted context dictionary from extract_from_conversation
            name: Optional human-readable snapshot name

        Returns:
            Path to created snapshot file

        Example:
            >>> context = extractor.extract_from_conversation(messages)
            >>> path = extractor.create_snapshot(context, name='auth-feature')
            >>> path.exists()
            True
        """
        # Generate snapshot ID
        snapshot_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create ContextSnapshot object
        snapshot = ContextSnapshot(
            snapshot_id=snapshot_id,
            name=name,
            timestamp=datetime.now(),
            original_requirements=context.get("original_requirements", ""),
            key_decisions=context.get("key_decisions", []),
            implementation_state=context.get("implementation_state", ""),
            open_items=context.get("open_items", []),
            tools_used=context.get("tools_used", []),
            token_count=self._estimate_tokens(context),
            file_path=None,  # Will be set below
        )

        # Save to file
        file_path = self.snapshot_dir / f"{snapshot_id}.json"
        snapshot.file_path = file_path

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(snapshot.to_dict(), f, indent=2, ensure_ascii=False)

        return file_path

    def _estimate_tokens(self, context: Dict[str, Any]) -> int:
        """Rough token estimation (1 token ≈ 4 characters)."""
        total_chars = 0
        total_chars += len(context.get("original_requirements", ""))
        total_chars += len(context.get("implementation_state", ""))

        for decision in context.get("key_decisions", []):
            total_chars += len(str(decision))

        for item in context.get("open_items", []):
            total_chars += len(item)

        return total_chars // 4
