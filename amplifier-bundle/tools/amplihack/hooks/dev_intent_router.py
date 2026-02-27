#!/usr/bin/env python3
"""
dev_intent_router.py — Classifies user prompts and injects workflow routing signals.

Three routing outcomes:
  DEV  → Invoke dev-orchestrator (DEFAULT_WORKFLOW for builds, fixes, docs, verification)
  Q&A  → Answer directly (knowledge questions, explanations)
  OPS  → Execute directly (shell commands, admin tasks, maintenance)
  SKIP → No injection (existing slash commands, greetings, explicit bypasses)

Why three routes matter:
  - DEV tasks: "fix the bug", "write the docs", "make sure it works", "add rate limiting"
  - Q&A tasks: "what is OAuth?", "how does JWT work?" — deserve direct concise answers
  - OPS tasks: "run git status", "delete old logs" — execute, don't orchestrate

Performance: <1ms per call (pure keyword matching, no LLM).
Disable:     export AMPLIHACK_AUTO_DEV=false (also: 0, no, off)
"""

import os
import re
from dataclasses import dataclass


@dataclass
class IntentResult:
    route_type: str    # "dev" | "qa" | "ops" | "skip"
    confidence: float  # 0.0–1.0
    tier: str          # "required" | "recommended" | "suggested" | "skip"
    reason: str

    @property
    def should_route(self) -> bool:
        """True for any route that produces an injection (dev, qa, ops)."""
        return self.route_type != "skip"

# Backwards-compatible alias
DevIntentResult = IntentResult


# ── Hard bypasses: always skip ────────────────────────────────────────────────

_SKIP_PREFIXES = ('/', 'task(', 'skill(')

_BYPASS_RE = re.compile(
    r'\b(?:just\s+(?:answer|explain|tell)|only\s+(?:explain|tell|describe)|'
    r'briefly\s+(?:answer\b)?|without\s+(?:orchestration|workflow|/dev|dev\b)|'
    r'quick(?:ly)?\s+(?:answer|tell|explain|show)|'
    r'skip\s+(?:orchestration|workflow)|'
    r'directly\s+answer|no\s+workflow|'
    r'don\'t\s+use\s+/dev)\b',
    re.I,
)


# ── Greetings and acknowledgements ───────────────────────────────────────────

_GREETING_RE = re.compile(
    r'^(?:hi\b|hello\b|hey\b|thanks\b|thank\s+you|ok\b|okay\b|'
    r'yes\b|no\b|sure\b|sounds\s+good|great\b|perfect\b|'
    r'awesome\b|cool\b|nice\b|got\s+it|understood)\b',
    re.I,
)


# ── Operations: shell/admin — route_type="ops" ───────────────────────────────
# Note: (?<![/A-Z])\bcd\b avoids matching "CI/CD"

_OPS_RE = re.compile(
    r'(?:'
    r'git\s+\w+'
    r'|(?<![/A-Z])\bcd\b'
    r'|\bls\b|\bpwd\b|\brm\b|\bcp\b|\bmv\b|\bcat\b|\bgrep\b'
    r'|disk\s+usage|\bdf\b|\bdu\b|\bps\b|\bkill\b'
    r'|restart\s+\w+'
    r'|clean\s+up\s+(?:old|temp|log)'
    r'|delete\s+(?:old|temp|log)\s+files?'
    r'|show\s+me\s+(?:the\s+)?(?:files?|directory|output|log\s+files?)'
    r')',
    re.I,
)


# ── Q&A / knowledge patterns — route_type="qa" ───────────────────────────────

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


# ── Development action verbs — route_type="dev" ───────────────────────────────
# Includes documentation and verification work (they belong in DEFAULT_WORKFLOW)

_ACTION_RE = re.compile(
    r'\b(?:implement|build|create|fix|add|develop|make|generate|configure|'
    r'optimize|improve|patch|repair|resolve|handle|update|upgrade|refactor|'
    r'migrate|deploy|integrate|scaffold|debug|verify|review|analyze|'
    r'investigate|explore|research|audit|'
    r'structure|architect|design|organize|arrange|'
    r'set\s+up|clean\s+up|wire\s+up|hook\s+up|spin\s+up|'
    r'port\s+(?:to|from)|extract|split|merge|combine|'
    r'profile|monitor|benchmark|secure|harden|automate|'
    r'document|write)\b',     # 'write' and 'document' belong in dev actions
    re.I,
)


# ── Test-verb detection (distinguishes "test the flow" from "a test result") ──

_TEST_NOUN_FOLLOW = frozenset({
    'suite', 'suites', 'case', 'cases', 'coverage', 'result', 'results',
    'run', 'runner', 'runners', 'data', 'bed', 'driven', 'environment',
    'setup', 'teardown', 'fixture', 'fixtures', 'harness', 'plan', 'plans',
    'report', 'reports', 'output', 'outputs', 'execution',
})

_TEST_NONVERB_BEFORE = re.compile(
    r'\b(?:a|an|the|this|that|these|those|my|your|our|their|its|'
    r'to|should|can|will|would|must|might|could|may|need\s+to|'
    r'quick|simple|basic|initial|final|unit|integration|end[\s-]to[\s-]end|'
    r'want\s+to|like\s+to|going\s+to|trying\s+to|'
    r'just|only|simple|another|one|some|any)'
    r'(?:\s+(?:i|you|we|he|she|they|me|us|him|her|them|it))?\s+$',
    re.I,
)


def _is_test_imperative(text_lower: str) -> bool:
    """True when 'test' is used as an imperative verb (not a noun or modal context)."""
    for m in re.finditer(r'\btest[s]?\b', text_lower):
        pos = m.start()
        before = text_lower[:pos]
        after = text_lower[pos + len(m.group()):].lstrip()
        next_word_m = re.match(r'(\w+)', after)
        if not next_word_m:
            continue
        if next_word_m.group(1) in _TEST_NOUN_FOLLOW:
            continue
        if _TEST_NONVERB_BEFORE.search(before):
            continue
        return True
    return False


# ── Technology context words (two+ → implicit dev context) ───────────────────

_TECH_WORDS = frozenset({
    'api', 'endpoint', 'service', 'database', 'schema', 'oauth', 'jwt',
    'auth', 'authentication', 'middleware', 'component', 'module', 'function',
    'class', 'pipeline', 'dockerfile', 'migration', 'query', 'cache', 'caching',
    'feature', 'bug', 'issue', 'pr', 'test', 'spec', 'webhook', 'ui',
    'microservice', 'microservices', 'ci', 'cicd', 'workflow', 'hook',
    'plugin', 'backend', 'frontend', 'fullstack', 'cli', 'sdk', 'library',
    'package', 'lambda', 'serverless', 'container', 'kubernetes', 'docker',
    'terraform', 'redis', 'postgres', 'mysql', 'mongodb', 'elasticsearch',
    'graphql', 'grpc', 'websocket', 'cron', 'queue', 'worker',
    'security', 'vulnerability', 'vulnerabilities', 'injection', 'xss', 'csrf',
})


# ── Main classifier ───────────────────────────────────────────────────────────

def classify(prompt: str) -> IntentResult:
    """
    Classify a user prompt into one of four routing outcomes.

    DEV:  Development/investigation task → dev-orchestrator (DEFAULT_WORKFLOW)
          Includes: coding, fixing, testing, documenting, verifying, deploying
    Q&A:  Knowledge/explanation question → direct concise answer (Q&A_WORKFLOW)
    OPS:  Shell/admin task → direct execution (OPS_WORKFLOW)
    SKIP: Existing slash command, greeting, or explicit bypass → no injection
    """
    if not prompt or not prompt.strip():
        return IntentResult("skip", 0.0, "skip", "empty prompt")

    p = prompt.strip()
    p_lower = p.lower()

    # 1. Hard bypasses — always skip, respect explicit user intent
    for prefix in _SKIP_PREFIXES:
        if p_lower.startswith(prefix):
            return IntentResult("skip", 0.0, "skip", "existing command/invocation")

    if _BYPASS_RE.search(p):
        return IntentResult("skip", 0.0, "skip", "explicit bypass")

    # 2. Short greetings and acknowledgements
    if _GREETING_RE.match(p) and len(p.split()) <= 5:
        return IntentResult("skip", 0.0, "skip", "greeting/acknowledgement")

    # 3. Operations tasks → OPS routing (execute directly, no workflow overhead)
    if _OPS_RE.search(p):
        return IntentResult("ops", 0.85, "required", "operations/admin task")

    # 4. Feature extraction
    has_action = bool(_ACTION_RE.search(p)) or _is_test_imperative(p_lower)
    has_knowledge = bool(_KNOWLEDGE_RE.search(p))
    words = frozenset(re.findall(r'\b\w+\b', p_lower))
    tech_hits = _TECH_WORDS & words

    # 5. Clear development action → DEV (includes "make sure", "write docs",
    #    "verify deployment" — verification and documentation ARE dev work)
    if has_action and not has_knowledge:
        return IntentResult("dev", 0.95, "required", "clear action request")

    # 6. Action + explanation context ("explain how to implement X") → DEV
    if has_action and has_knowledge:
        return IntentResult("dev", 0.80, "recommended",
                            "action + knowledge: dev task with explanation")

    # 7. Pure knowledge / Q&A → Q&A routing (direct answer, no workflow)
    if has_knowledge and not has_action:
        return IntentResult("qa", 0.85, "required", "knowledge/Q&A question")

    # 8. Implicit dev context via tech word co-occurrence
    if not has_action and not has_knowledge:
        if len(tech_hits) >= 2:
            return IntentResult("dev", 0.55, "suggested",
                                f"implicit dev context: {tech_hits}")
        if tech_hits:
            # Single tech word — ambiguous, skip rather than misroute
            return IntentResult("skip", 0.30, "skip", "single tech word, ambiguous")

    return IntentResult("skip", 0.10, "skip", "no clear intent")


# ── Injection builders ────────────────────────────────────────────────────────

def build_context_injection(result: IntentResult, prompt: str) -> str:
    """Build the additionalContext system reminder for the given route type."""

    if result.route_type == "dev":
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

    if result.route_type == "qa":
        return (
            f'<system-reminder source="auto-qa-router">\n'
            f'KNOWLEDGE/Q&A REQUEST DETECTED (confidence: {result.confidence:.0%}).\n'
            f'Answer this question directly and concisely. '
            f'No workflow invocation is needed.\n'
            f'Question: "{prompt[:300]}"\n'
            f'</system-reminder>'
        )

    if result.route_type == "ops":
        return (
            f'<system-reminder source="auto-ops-router">\n'
            f'OPERATIONS TASK DETECTED (confidence: {result.confidence:.0%}).\n'
            f'Execute this admin/maintenance task directly. '
            f'No workflow invocation is needed.\n'
            f'Task: "{prompt[:300]}"\n'
            f'</system-reminder>'
        )

    return ""


def should_auto_route(prompt: str) -> tuple[bool, str]:
    """
    Main entry point for user_prompt_submit.py.

    Returns (should_inject, injection_text) for dev, qa, and ops routes.
    Returns (False, "") when routing is disabled or prompt should be skipped.

    Disable entirely: export AMPLIHACK_AUTO_DEV=false (also: 0, no, off)
    """
    auto_dev = os.environ.get("AMPLIHACK_AUTO_DEV", "true").lower().strip()
    if auto_dev in ("false", "0", "no", "off"):
        return False, ""

    result = classify(prompt)
    if result.route_type == "skip":
        return False, ""

    return True, build_context_injection(result, prompt)
