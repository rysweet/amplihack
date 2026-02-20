"""Skill injection registry for domain agents."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any


class SkillInjector:
    """Registry that maps amplihack skills to domain agent tools."""

    def __init__(self):
        self._skills: dict[str, dict[str, Callable]] = {}

    def register(self, domain: str, skill_name: str, tool_fn: Callable) -> None:
        if not domain or not domain.strip():
            raise ValueError("domain cannot be empty")
        if not skill_name or not skill_name.strip():
            raise ValueError("skill_name cannot be empty")
        if not callable(tool_fn):
            raise ValueError(f"tool_fn for '{skill_name}' must be callable")

        domain = domain.strip()
        skill_name = skill_name.strip()
        if domain not in self._skills:
            self._skills[domain] = {}
        self._skills[domain][skill_name] = tool_fn

    def get_skills_for_domain(self, domain: str) -> dict[str, Callable]:
        if not domain or not domain.strip():
            return {}
        return dict(self._skills.get(domain.strip(), {}))

    def get_all_domains(self) -> list[str]:
        return list(self._skills.keys())

    def has_skill(self, domain: str, skill_name: str) -> bool:
        return skill_name in self._skills.get(domain, {})


# Default skill tool implementations


def code_smell_detector_tool(code: str, language: str = "python") -> dict[str, Any]:
    """Detect code smells in source code."""
    smells = []
    lines = code.strip().split("\n")
    if len(lines) > 50:
        smells.append(
            {
                "type": "long_function",
                "severity": "warning",
                "message": f"Function is {len(lines)} lines long (threshold: 50)",
            }
        )
    max_indent = 0
    for line in lines:
        stripped = line.lstrip()
        if stripped:
            max_indent = max(max_indent, len(line) - len(stripped))
    if max_indent > 16:
        smells.append(
            {
                "type": "deep_nesting",
                "severity": "warning",
                "message": f"Maximum nesting depth is {max_indent // 4} levels",
            }
        )
    magic_numbers = re.findall(r"(?<![.\w])\d{2,}(?!\w)", code)
    if magic_numbers:
        smells.append(
            {
                "type": "magic_numbers",
                "severity": "info",
                "message": f"Found {len(magic_numbers)} magic numbers: {magic_numbers[:5]}",
            }
        )
    return {"smells": smells, "smell_count": len(smells), "language": language}


def pr_review_tool(code_diff: str) -> dict[str, Any]:
    """Review a code diff for issues."""
    findings = []
    lines = code_diff.split("\n")
    added = [ln for ln in lines if ln.startswith("+") and not ln.startswith("+++")]
    removed = [ln for ln in lines if ln.startswith("-") and not ln.startswith("---")]
    if len(added) > 200:
        findings.append(
            {
                "type": "large_change",
                "severity": "info",
                "message": f"Large change: {len(added)} lines added",
            }
        )
    for line in added:
        if "print(" in line or "console.log" in line or "debugger" in line:
            findings.append(
                {
                    "type": "debug_statement",
                    "severity": "warning",
                    "message": f"Debug statement found: {line.strip()[:80]}",
                }
            )
    return {"findings": findings, "lines_added": len(added), "lines_removed": len(removed)}


def meeting_notes_tool(transcript: str) -> dict[str, Any]:
    """Extract structured notes from a meeting transcript."""
    lines = transcript.strip().split("\n")
    speakers = set()
    for line in lines:
        if ":" in line:
            speaker = line.split(":")[0].strip()
            if speaker and len(speaker) < 30:
                speakers.add(speaker)
    return {
        "speaker_count": len(speakers),
        "speakers": list(speakers),
        "line_count": len(lines),
        "word_count": len(transcript.split()),
    }


def email_draft_tool(context: str, recipients: str, tone: str = "professional") -> dict[str, Any]:
    """Draft an email from context."""
    return {
        "to": recipients,
        "subject": f"Re: {context[:50]}",
        "body_template": f"Dear {recipients},\n\nRegarding {context[:100]}...\n\nBest regards",
        "tone": tone,
    }
