#!/usr/bin/env python3
"""
dev_intent_router.py — Injects intent-routing guidance into every prompt.

Instead of regex-based classification (which required 366 lines and still
found 5+ bugs per audit round), this module injects a short classification
prompt that lets the LLM itself classify intent with full natural language
understanding.

The LLM already processes every message — making it classify intent is
essentially free (happens during existing thinking) and infinitely more
accurate than any regex pattern.

Disable: export AMPLIHACK_AUTO_DEV=false (also: 0, no, off)
"""

import os

# The classification prompt injected as additionalContext.
# Claude reads this BEFORE processing the user's message.
_ROUTING_PROMPT = """\
<system-reminder source="auto-intent-router">
Before responding, classify this prompt into one of these categories and act accordingly:

  DEV (build, fix, write, test, verify, deploy, document, refactor, configure, add feature)
    → Invoke Skill(skill="dev-orchestrator"). Do not answer inline.

  INVESTIGATE (analyze, understand, explore, research, audit, trace, map out)
    → Invoke Skill(skill="dev-orchestrator"). It will use INVESTIGATION_WORKFLOW.

  HYBRID (investigate/understand THEN implement/fix/build — both in one prompt)
    → Invoke Skill(skill="dev-orchestrator"). It will create parallel workstreams.

  Q&A (what is, how does, explain, describe, compare, define — knowledge questions)
    → Answer directly and concisely. No workflow invocation needed.

  OPS (run git, show disk, delete temp files, restart service — admin/shell tasks)
    → Execute directly. No workflow invocation needed.

  SKIP (prompt starts with / — existing slash command; or bypass phrases like
        "just answer", "skip workflow", "skip orchestration", "without workflow")
    → Respect the existing command or bypass. Do not override.

Key: "make sure it works" = DEV (verification). "write docs" = DEV (documentation).
     "tests are failing" without a clear action request = ask if they want you to investigate/fix.
     "investigate X then fix Y" = HYBRID. "what is OAuth?" = Q&A.
</system-reminder>"""


def should_auto_route(prompt: str) -> tuple[bool, str]:
    """
    Returns (should_inject, injection_text).

    Returns (False, "") when:
    1. Disabled via AMPLIHACK_AUTO_DEV=false/0/no/off
    2. Prompt is not a string
    3. Prompt is empty or whitespace-only
    4. Prompt starts with / (existing slash command)
    """
    # Check disable flag
    auto_dev = os.environ.get("AMPLIHACK_AUTO_DEV", "true").lower().strip()
    if auto_dev in ("false", "0", "no", "off"):
        return False, ""

    # Type guard — prompt must be a string
    if not isinstance(prompt, str):
        return False, ""

    # Don't inject for empty prompts or existing slash commands
    if not prompt or not prompt.strip():
        return False, ""
    if prompt.strip().startswith("/"):
        return False, ""

    return True, _ROUTING_PROMPT
