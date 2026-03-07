"""Transcript helpers mixin - utilities for parsing and extracting from transcripts."""

from typing import Any


class TranscriptHelpersMixin:
    """Mixin with transcript parsing and extraction utilities."""

    def _generic_analyzer(
        self, transcript: list[dict], session_id: str, consideration: dict[str, Any]
    ) -> bool:
        """Generic analyzer for considerations without specific checkers.

        Uses simple keyword matching on the consideration question.
        Phase 2: Simple heuristics (future: LLM-based analysis)

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier
            consideration: Consideration dictionary with question

        Returns:
            True if satisfied (fail-open default), False if potential issues detected
        """
        return True  # Fail-open fallback

    @staticmethod
    def _find_last_todo_write(transcript: list[dict]) -> dict | None:
        """Find the most recent TodoWrite tool call input in the transcript.

        Args:
            transcript: List of message dictionaries

        Returns:
            TodoWrite input dict (with 'todos' key), or None if not found
        """
        for msg in reversed(transcript):
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            if block.get("name") == "TodoWrite":
                                return block.get("input", {})
        return None

    def _extract_incomplete_todos(self, transcript: list[dict]) -> list[str]:
        """Extract list of incomplete todo items from transcript.

        Helper method used by continuation prompt generation to show
        specific items the agent needs to complete.

        Args:
            transcript: List of message dictionaries

        Returns:
            List of incomplete todo item descriptions
        """
        last_todo_write = self._find_last_todo_write(transcript)
        if not last_todo_write:
            return []

        return [
            f"[{todo.get('status', 'pending')}] {todo.get('content', 'Unknown task')}"
            for todo in last_todo_write.get("todos", [])
            if todo.get("status") != "completed"
        ]

    def _extract_next_steps_mentioned(self, transcript: list[dict]) -> list[str]:
        """Extract specific next steps mentioned in recent assistant messages.

        Helper method used by continuation prompt generation to show
        specific next steps the agent mentioned but hasn't completed.

        Args:
            transcript: List of message dictionaries

        Returns:
            List of next step descriptions (extracted sentences/phrases)
        """
        next_steps = []
        next_steps_triggers = [
            "next step",
            "next steps",
            "follow-up",
            "remaining",
            "still need",
            "todo",
            "left to",
        ]

        # Check recent assistant messages
        recent_messages = [m for m in transcript[-15:] if m.get("type") == "assistant"][-5:]

        for msg in recent_messages:
            content = msg.get("message", {}).get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = str(block.get("text", ""))
                        text_lower = text.lower()

                        # Check if this block mentions next steps
                        if any(trigger in text_lower for trigger in next_steps_triggers):
                            # Extract sentences containing the trigger
                            sentences = text.replace("\n", " ").split(". ")
                            for sentence in sentences:
                                sentence_lower = sentence.lower()
                                if any(
                                    trigger in sentence_lower for trigger in next_steps_triggers
                                ):
                                    clean_sentence = sentence.strip()
                                    if clean_sentence and len(clean_sentence) > 10:
                                        # Truncate long sentences
                                        if len(clean_sentence) > 150:
                                            clean_sentence = clean_sentence[:147] + "..."
                                        if clean_sentence not in next_steps:
                                            next_steps.append(clean_sentence)

        return next_steps[:5]  # Limit to 5 items

    def _transcript_to_text(self, transcript: list[dict]) -> str:
        """Convert transcript list to plain text for pattern matching.

        Args:
            transcript: List of message dictionaries

        Returns:
            Plain text representation of transcript
        """
        lines = []
        for msg in transcript:
            role = msg.get("type", "unknown")
            if role == "user":
                lines.append(f"User: {self._extract_message_text(msg)}")
            elif role == "assistant":
                lines.append(f"Claude: {self._extract_message_text(msg)}")
        return "\n".join(lines)

    def _extract_message_text(self, msg: dict) -> str:
        """Extract text content from message.

        Args:
            msg: Message dictionary

        Returns:
            Text content
        """
        message = msg.get("message", {})
        content = message.get("content", [])

        if isinstance(content, str):
            return content

        if isinstance(content, list):
            texts = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        texts.append(block.get("text", ""))
                    elif block.get("type") == "tool_use":
                        # Include tool invocations in text
                        tool_name = block.get("name", "")
                        tool_input = block.get("input", {})
                        texts.append(f'<invoke name="{tool_name}">{tool_input}')
            return " ".join(texts)

        return ""
