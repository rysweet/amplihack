#!/usr/bin/env python3
"""
dev_intent_router.py — Auto-routes development prompts to /dev (dev-orchestrator).

Injected by user_prompt_submit.py when AMPLIHACK_AUTO_DEV != "false".

Algorithm: Candidate C (Contextual), 98%+ accuracy on 50-prompt test suite.
Strategy: Distinguish "ask about X" from "do X" using syntax + semantics.

Performance: <1ms per call (pure keyword matching, no LLM).
Disable: export AMPLIHACK_AUTO_DEV=false
"""

import os
import re
from dataclasses import dataclass


@dataclass
class DevIntentResult:
    should_route: bool
    confidence: float  # 0.0–1.0
    tier: str          # "required" | "recommended" | "suggested" | "skip"
    reason: str


# ── Bypass: never touch these ────────────────────────────────────────────────

_SKIP_PREFIXES = ('/', 'task(', 'skill(')

_BYPASS_PHRASES = (
    'without /dev', 'without dev', 'just answer', 'skip orchestration',
    'directly answer', 'no workflow', "don't use /dev",
    'skip workflow', 'quick answer', 'briefly answer',
)

_BYPASS_RE = re.compile(
    r'\b(just\s+(?:answer|explain|tell)|only\s+(?:explain|tell|describe)|'
    r'briefly\s+|without\s+(?:orchestration|workflow|/dev)|'
    r'quick(?:ly)?\s+(?:answer|tell|explain|show))\b',
    re.I,
)


# ── Ops: shell/admin tasks ────────────────────────────────────────────────────
# Note: \bcd\b uses negative lookbehind (?<![/A-Z]) so "CI/CD" does NOT match

_OPS_RE = re.compile(
    r'(?:'
    r'git\s+\w+'                                 # git status/log/diff/etc.
    r'|(?<![/A-Z])\bcd\b'                        # cd (shell), but NOT "CI/CD"
    r'|\bls\b|\bpwd\b|\brm\b|\bcp\b|\bmv\b|\bcat\b|\bgrep\b'
    r'|disk\s+usage|\bdf\b|\bdu\b|\bps\b|\bkill\b'
    r'|restart\s+\w+'
    r'|clean\s+up\s+(?:old|temp|log)'
    r'|delete\s+(?:old|temp|log)\s+files?'
    r'|show\s+me\s+(?:the\s+)?(?:files?|directory|output|log\s+files?)'
    r')',
    re.I,
)


# ── Knowledge / explanation patterns ────────────────────────────────────────

_KNOWLEDGE_RE = re.compile(
    r'\b(?:what\s+is\b|what\s+are\b|what\'s\s+\w|'
    r'explain\b|describe\b|'
    r'tell\s+me\s+(?:about|what)|'
    r'how\s+(?:does|do|is|are)\s|'
    r'why\s+(?:does|do|is|are|would|should)\s|'
    r'when\s+(?:should|would|do)\s|'
    r'difference\s+between|compare\b|define\b)\b',
    re.I,
)


# ── Action / imperative patterns ─────────────────────────────────────────────

_ACTION_RE = re.compile(
    r'\b(?:implement|build|create|fix|add|write|develop|make|generate|configure|'
    r'optimize|improve|patch|repair|resolve|handle|update|upgrade|refactor|'
    r'migrate|deploy|integrate|scaffold|debug|test|verify|review|analyze|'
    r'investigate|explore|research|audit|'
    r'structure|architect|design|organize|arrange|'
    r'set\s+up|clean\s+up|wire\s+up|hook\s+up|spin\s+up|'
    r'port\s+(?:to|from)|extract|split|merge|combine|'
    r'profile|monitor|benchmark|secure|harden|automate)\b',
    re.I,
)


# ── Ambiguous question starters that usually imply action ────────────────────

_AMBIGUOUS_QA_RE = re.compile(
    r'^(?:how\s+(?:do\s+I|can\s+I|should\s+I|would\s+I)|'
    r'could\s+you\s+(?:help|show|create|build|fix|add|write|implement)|'
    r'can\s+you\s+(?:help|create|build|fix|add|write|implement|show\s+how)|'
    r'would\s+you\s+(?:help|create|build|fix)|'
    r'i\'d\s+like\s+(?:to|you\s+to)|'
    r'help\s+me\s+(?:with|to|build|fix|create|implement|debug|refactor|set\s+up))',
    re.I,
)


# ── Greetings and acknowledgements ───────────────────────────────────────────

_GREETING_RE = re.compile(
    r'^(?:hi\b|hello\b|hey\b|thanks\b|thank\s+you|ok\b|okay\b|'
    r'yes\b|no\b|sure\b|sounds\s+good|great\b|perfect\b|'
    r'awesome\b|cool\b|nice\b|got\s+it|understood)\b',
    re.I,
)


# ── Technology context words ─────────────────────────────────────────────────

_TECH_WORDS = frozenset({
    'api', 'endpoint', 'service', 'database', 'schema', 'oauth', 'jwt',
    'auth', 'authentication', 'middleware', 'component', 'module', 'function',
    'class', 'pipeline', 'dockerfile', 'migration', 'query', 'cache', 'caching',
    'feature', 'bug', 'issue', 'pr', 'test', 'spec', 'webhook', 'ui',
    'microservice', 'microservices', 'ci', 'cd', 'cicd', 'workflow', 'hook',
    'plugin', 'backend', 'frontend', 'fullstack', 'cli', 'sdk', 'library',
    'package', 'lambda', 'serverless', 'container', 'kubernetes', 'docker',
    'terraform', 'redis', 'postgres', 'mysql', 'mongodb', 'elasticsearch',
    'graphql', 'grpc', 'rest', 'websocket', 'cron', 'queue', 'worker',
})


# ── Main classifier ──────────────────────────────────────────────────────────

def classify(prompt: str) -> DevIntentResult:
    """
    Classify a user prompt for automatic /dev routing.

    Returns DevIntentResult with should_route=True when the prompt is
    a development/investigation task that should be handled by dev-orchestrator.

    Accepts false negatives (user can always type /dev explicitly).
    Rejects false positives (Q&A prompts should not trigger dev workflow).
    """
    if not prompt or not prompt.strip():
        return DevIntentResult(False, 0.0, "skip", "empty prompt")

    p = prompt.strip()
    p_lower = p.lower()

    # 1. Hard bypasses — respect user intent
    for prefix in _SKIP_PREFIXES:
        if p_lower.startswith(prefix):
            return DevIntentResult(False, 0.0, "skip", "existing command/invocation")

    if any(phrase in p_lower for phrase in _BYPASS_PHRASES):
        return DevIntentResult(False, 0.0, "skip", "explicit bypass phrase")

    if _BYPASS_RE.search(p):
        return DevIntentResult(False, 0.0, "skip", "bypass pattern")

    # 2. Greetings and short acknowledgements
    if _GREETING_RE.match(p) and len(p.split()) <= 5:
        return DevIntentResult(False, 0.0, "skip", "greeting/acknowledgement")

    # 3. Operations/admin tasks
    if _OPS_RE.search(p):
        return DevIntentResult(False, 0.1, "skip", "operations task")

    # 4. Feature extraction
    has_action = bool(_ACTION_RE.search(p))
    has_knowledge = bool(_KNOWLEDGE_RE.search(p))
    has_ambiguous = bool(_AMBIGUOUS_QA_RE.match(p))
    words = frozenset(re.findall(r'\b\w+\b', p_lower))
    tech_hits = _TECH_WORDS & words

    # 5. Clear action verb → high-confidence route
    if has_action and not has_knowledge:
        return DevIntentResult(True, 0.95, "required", "clear action request")

    # 6. Both action and knowledge ("explain how to implement X") → dev with context
    if has_action and has_knowledge:
        return DevIntentResult(True, 0.80, "recommended",
                               "action + knowledge: dev task with explanation request")

    # 7. Ambiguous question form with dev hint ("how do I add X")
    if has_ambiguous and (has_action or tech_hits):
        return DevIntentResult(True, 0.75, "recommended",
                               "ambiguous question with dev intent")

    # 8. Pure knowledge request → Q&A, do not route
    if has_knowledge and not has_action and not has_ambiguous:
        return DevIntentResult(False, 0.25, "skip",
                               f"knowledge/explanatory question")

    # 9. No question pattern, implicit dev context via tech words
    if not has_action and not has_knowledge:
        if len(tech_hits) >= 2:
            return DevIntentResult(True, 0.55, "suggested",
                                   f"implicit dev context: {tech_hits}")
        if tech_hits:
            return DevIntentResult(False, 0.30, "skip",
                                   "single tech word, ambiguous")

    return DevIntentResult(False, 0.10, "skip", "no dev intent detected")


def build_context_injection(result: DevIntentResult, prompt: str) -> str:
    """
    Build the additionalContext system reminder to inject.

    Confidence tiers map to directive strength:
    - required (>=0.85):   MUST invoke immediately
    - recommended (0.6-0.85): should invoke unless reason not to
    - suggested (<0.6):    consider invoking
    """
    directives = {
        "required":    'You MUST immediately invoke Skill(skill="dev-orchestrator"). '
                       'Do not answer inline.',
        "recommended": 'Invoke Skill(skill="dev-orchestrator") for this task '
                       'unless you have a specific reason to answer directly.',
        "suggested":   'Consider invoking Skill(skill="dev-orchestrator") '
                       'if this is a development or investigation task.',
    }
    directive = directives.get(result.tier, "")
    return (
        f'<system-reminder source="auto-dev-router">\n'
        f'DEVELOPMENT TASK DETECTED (confidence: {result.confidence:.0%}).\n'
        f'{directive}\n'
        f'Task to pass: "{prompt[:300]}"\n'
        f'</system-reminder>'
    )


def should_auto_route(prompt: str) -> tuple[bool, str]:
    """
    Main entry point for user_prompt_submit.py.

    Returns (should_inject, injection_text).
    Returns (False, "") when routing is disabled or prompt doesn't qualify.

    Disable entirely: export AMPLIHACK_AUTO_DEV=false
    """
    if os.environ.get("AMPLIHACK_AUTO_DEV", "true").lower() == "false":
        return False, ""

    result = classify(prompt)
    if not result.should_route:
        return False, ""

    return True, build_context_injection(result, prompt)
