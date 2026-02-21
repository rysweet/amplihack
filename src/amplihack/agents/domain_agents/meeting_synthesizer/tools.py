"""Meeting synthesizer domain tools. Pure functions for extracting information from transcripts."""

from __future__ import annotations

import re
from typing import Any


def extract_action_items(transcript: str) -> list[dict[str, Any]]:
    """Extract action items from a meeting transcript.

    Looks for assignment patterns like:
    - "X, can you/please do Y by Z"
    - "I will/I'll do Y"
    - "X will do Y"

    Returns list of dicts with keys: owner, action, deadline, source_line
    """
    if not transcript or not transcript.strip():
        return []

    items: list[dict[str, Any]] = []
    lines = transcript.strip().split("\n")

    # Patterns for action item detection
    assignment_patterns = [
        # "Bob, can you draft the API spec by Friday?"
        r"(\w+),?\s+(?:can you|please|could you)\s+(.+?)(?:\s+by\s+(.+?))?[.?]?\s*$",
        # "Bob, please complete the migration by next Wednesday"
        r"(\w+),?\s+please\s+(.+?)(?:\s+by\s+(.+?))?[.?]?\s*$",
    ]

    # "I will have the draft ready by Friday"
    self_assignment_pattern = r"I\s+(?:will|'ll)\s+(.+?)(?:\s+by\s+(.+?))?[.?]?\s*$"

    # "X will do Y"
    third_person_pattern = r"(\w+)\s+will\s+(.+?)(?:\s+by\s+(.+?))?[.?]?\s*$"

    for line in lines:
        # Get speaker
        speaker = ""
        content = line
        if ":" in line:
            parts = line.split(":", 1)
            speaker = parts[0].strip()
            content = parts[1].strip()

        # Check assignment patterns (someone assigning to another person)
        for pattern in assignment_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                owner = match.group(1)
                action = match.group(2).strip()
                deadline = match.group(3).strip() if match.group(3) else ""
                items.append(
                    {
                        "owner": owner,
                        "action": action,
                        "deadline": deadline,
                        "source_line": line.strip(),
                    }
                )
                break

        # Check self-assignment ("I will...")
        match = re.search(self_assignment_pattern, content, re.IGNORECASE)
        if match and speaker:
            action = match.group(1).strip()
            deadline = match.group(2).strip() if match.group(2) else ""
            items.append(
                {
                    "owner": speaker,
                    "action": action,
                    "deadline": deadline,
                    "source_line": line.strip(),
                }
            )
            continue

        # Check third-person assignment ("Bob will...")
        match = re.search(third_person_pattern, content, re.IGNORECASE)
        if match:
            owner = match.group(1)
            action = match.group(2).strip()
            deadline = match.group(3).strip() if match.group(3) else ""
            # Skip common false positives
            if owner.lower() not in ("it", "this", "that", "which", "we", "they", "the"):
                items.append(
                    {
                        "owner": owner,
                        "action": action,
                        "deadline": deadline,
                        "source_line": line.strip(),
                    }
                )

    return items


def generate_summary(transcript: str) -> dict[str, Any]:
    """Generate a summary of a meeting transcript.

    Returns dict with: summary_text, participants, word_count,
    line_count, duration_estimate, key_points
    """
    if not transcript or not transcript.strip():
        return {
            "summary_text": "",
            "participants": [],
            "word_count": 0,
            "line_count": 0,
            "duration_estimate": "",
            "key_points": [],
        }

    lines = transcript.strip().split("\n")
    words = transcript.split()

    # Extract participants
    participants = _extract_speakers(lines)

    # Estimate duration (roughly 150 words per minute of meeting)
    word_count = len(words)
    estimated_minutes = max(1, word_count // 150)
    if estimated_minutes < 5:
        duration_estimate = f"~{estimated_minutes} minute(s)"
    else:
        duration_estimate = f"~{estimated_minutes} minutes"

    # Extract key points from content lines
    key_points = []
    for line in lines:
        content = line.split(":", 1)[1].strip() if ":" in line else line.strip()
        if not content:
            continue
        # Look for substantive statements
        if any(
            indicator in content.lower()
            for indicator in [
                "think",
                "should",
                "need",
                "prioritize",
                "agree",
                "decided",
                "proposal",
                "important",
                "plan",
                "finish",
                "complete",
            ]
        ):
            key_points.append(content[:200])

    # Build summary text
    summary_parts = []
    if participants:
        summary_parts.append(
            f"Meeting with {len(participants)} participants: {', '.join(participants)}."
        )
    summary_parts.append(f"Estimated duration: {duration_estimate}.")
    if key_points:
        summary_parts.append(f"Key points discussed: {len(key_points)}.")

    return {
        "summary_text": " ".join(summary_parts),
        "participants": participants,
        "word_count": word_count,
        "line_count": len(lines),
        "duration_estimate": duration_estimate,
        "key_points": key_points[:10],
    }


def identify_decisions(transcript: str) -> list[dict[str, Any]]:
    """Identify decisions made during a meeting.

    Looks for decision indicators: "decided", "agreed", "approved",
    "will go with", "consensus", "chosen", "selected".

    Returns list of dicts with: decision, speaker, context
    """
    if not transcript or not transcript.strip():
        return []

    decisions: list[dict[str, Any]] = []
    lines = transcript.strip().split("\n")

    decision_indicators = [
        r"\b(?:decided|agreed|approved|resolved)\b",
        r"\bwill\s+go\s+with\b",
        r"\b(?:consensus|chosen|selected|concluded)\b",
        r"\b(?:let'?s\s+go\s+with|we'?ll\s+use|moving\s+forward\s+with)\b",
    ]

    for line in lines:
        speaker = ""
        content = line.strip()
        if ":" in line:
            parts = line.split(":", 1)
            speaker = parts[0].strip()
            content = parts[1].strip()

        for pattern in decision_indicators:
            if re.search(pattern, content, re.IGNORECASE):
                decisions.append(
                    {
                        "decision": content[:300],
                        "speaker": speaker,
                        "context": line.strip(),
                    }
                )
                break

    return decisions


def identify_topics(transcript: str) -> list[dict[str, Any]]:
    """Identify topics discussed in a meeting.

    Groups discussion by thematic shifts and speaker participation.

    Returns list of dicts with: topic, speakers, line_range
    """
    if not transcript or not transcript.strip():
        return []

    lines = transcript.strip().split("\n")
    topics: list[dict[str, Any]] = []

    # Simple topic extraction: look for topic indicators
    topic_indicators = [
        r"\blet'?s\s+(?:discuss|talk\s+about|move\s+to|look\s+at)\b",
        r"\b(?:next|moving\s+on|regarding|about|re:)\b",
        r"\b(?:agenda\s+item|topic|subject)\b",
    ]

    current_topic_lines: list[str] = []
    current_speakers: set[str] = set()
    start_line = 0

    for i, line in enumerate(lines):
        speaker = ""
        content = line.strip()
        if ":" in line:
            parts = line.split(":", 1)
            speaker = parts[0].strip()
            content = parts[1].strip()
            if speaker and len(speaker) < 30:
                current_speakers.add(speaker)

        # Check if this line starts a new topic
        is_new_topic = any(re.search(p, content, re.IGNORECASE) for p in topic_indicators)

        if is_new_topic and current_topic_lines:
            # Save previous topic
            topic_text = _infer_topic(current_topic_lines)
            if topic_text:
                topics.append(
                    {
                        "topic": topic_text,
                        "speakers": list(current_speakers),
                        "line_range": [start_line + 1, i],
                    }
                )
            current_topic_lines = []
            current_speakers = set()
            if speaker:
                current_speakers.add(speaker)
            start_line = i

        current_topic_lines.append(content)

    # Save last topic
    if current_topic_lines:
        topic_text = _infer_topic(current_topic_lines)
        if topic_text:
            topics.append(
                {
                    "topic": topic_text,
                    "speakers": list(current_speakers),
                    "line_range": [start_line + 1, len(lines)],
                }
            )

    # If no topics detected via indicators, create a single topic from all content
    if not topics:
        all_speakers = list(_extract_speakers(lines))
        topic_text = _infer_topic(
            [ln.split(":", 1)[1].strip() if ":" in ln else ln.strip() for ln in lines]
        )
        if topic_text:
            topics.append(
                {
                    "topic": topic_text,
                    "speakers": all_speakers,
                    "line_range": [1, len(lines)],
                }
            )

    return topics


def _extract_speakers(lines: list[str]) -> list[str]:
    """Extract unique speaker names from transcript lines."""
    speakers: list[str] = []
    seen: set[str] = set()
    for line in lines:
        if ":" in line:
            speaker = line.split(":")[0].strip()
            if speaker and len(speaker) < 30 and speaker.lower() not in seen:
                speakers.append(speaker)
                seen.add(speaker.lower())
    return speakers


def _infer_topic(lines: list[str]) -> str:
    """Infer a topic label from a set of content lines."""
    # Use the first substantive line as the topic
    for line in lines:
        clean = line.strip()
        if len(clean) > 10:
            # Truncate and clean up
            topic = clean[:100]
            # Remove common prefixes
            for prefix in ["let's discuss ", "let's talk about ", "moving on to ", "regarding "]:
                if topic.lower().startswith(prefix):
                    topic = topic[len(prefix) :]
                    break
            return topic.strip().rstrip(".")
    return ""
