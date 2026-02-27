#!/usr/bin/env python3
"""
dev_intent_router.py — Auto-routes development prompts to /dev (dev-orchestrator).

Injected by user_prompt_submit.py when AMPLIHACK_AUTO_DEV is not disabled.

Algorithm: Candidate C (Contextual), minimal false positives, precision-first design.
Strategy: Distinguish "ask about X" from "do X" using syntax + semantics.

Performance: <1ms per call (pure keyword matching, no LLM).
Disable: export AMPLIHACK_AUTO_DEV=false (also: 0, no, off)
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

_BYPASS_RE = re.compile(
    r'\b(just\s+(?:answer|explain|tell)|only\s+(?:explain|tell|describe)|'
    r'briefly\s+(?:answer\b)?|without\s+(?:orchestration|workflow|/dev|dev\b)|'
    r'quick(?:ly)?\s+(?:answer|tell|explain|show)|'
    r'skip\s+(?:orchestration|workflow)|'
    r'directly\s+answer|no\s+workflow|'
    r'don\'t\s+use\s+/dev)\b',
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
    r'\b(?:implement|build|create|fix|add|develop|make|generate|configure|'
    r'optimize|improve|patch|repair|resolve|handle|update|upgrade|refactor|'
    r'migrate|deploy|integrate|scaffold|debug|verify|review|analyze|'
    r'investigate|explore|research|audit|'
    r'structure|architect|design|organize|arrange|'
    r'set\s+up|clean\s+up|wire\s+up|hook\s+up|spin\s+up|'
    r'port\s+(?:to|from)|extract|split|merge|combine|'
    r'profile|monitor|benchmark|secure|harden|automate)\b',
    re.I,
)

# Exclude "make sure" and "make it" from matching as dev action
_MAKE_NONDEV_RE = re.compile(r'\bmake\s+(?:sure\b|it\b)', re.I)

# Words that follow 'test' indicating it's used as a noun (compound nouns)
_TEST_NOUN_FOLLOW = frozenset({
    'suite', 'suites', 'case', 'cases', 'coverage', 'result', 'results',
    'run', 'runner', 'runners', 'data', 'bed', 'driven', 'environment',
    'setup', 'teardown', 'fixture', 'fixtures', 'harness', 'plan', 'plans',
    'report', 'reports', 'output', 'outputs', 'execution',
})

# Context words before 'test' indicating it's NOT an imperative verb.
# Handles both "should test" and "should I test", "can you test", etc.
_TEST_NONVERB_BEFORE = re.compile(
    r'\b(?:a|an|the|this|that|these|those|my|your|our|their|its|'
    r'to|should|can|will|would|must|might|could|may|need\s+to|'
    r'quick|simple|basic|initial|final|unit|integration|end[\s-]to[\s-]end|'
    r'want\s+to|like\s+to|going\s+to|trying\s+to|'
    r'just|only|simple|another|one|some|any)'
    r'(?:\s+(?:i|you|we|he|she|they|me|us|him|her|them|it))?\s+$',
    re.I,
)

# Code artifacts that make 'write X' a development task
_WRITE_CODE_WORDS = frozenset({
    'test', 'tests', 'spec', 'specs', 'migration', 'migrations', 'query', 'queries',
    'function', 'functions', 'method', 'methods', 'class', 'classes', 'module',
    'modules', 'script', 'scripts', 'endpoint', 'endpoints', 'handler', 'handlers',
    'middleware', 'hook', 'hooks', 'component', 'components', 'service', 'services',
    'fixture', 'fixtures', 'mock', 'mocks', 'stub', 'stubs', 'code', 'implementation',
    'algorithm', 'algorithms', 'parser', 'parsers', 'validator', 'validators',
    'schema', 'model', 'models', 'route', 'routes', 'controller', 'controllers',
})


def _is_test_imperative(text_lower: str) -> bool:
    """Return True only when 'test' is used as an imperative verb with a direct object.

    Filters out:
    - 'test' as a noun (test suite, test case, a test, the test)
    - 'test' in modal/question contexts (should I test, can you test)
    - 'test' in infinitive context (want to test, going to test)
    """
    for m in re.finditer(r'\btest[s]?\b', text_lower):
        pos = m.start()
        before = text_lower[:pos]
        after = text_lower[pos + len(m.group()):].lstrip()

        # Must be followed by at least one word
        next_word_m = re.match(r'(\w+)', after)
        if not next_word_m:
            continue
        next_word = next_word_m.group(1)

        # Exclude noun compounds (test suite, test case, etc.)
        if next_word in _TEST_NOUN_FOLLOW:
            continue

        # Exclude non-imperative contexts before 'test'
        if _TEST_NONVERB_BEFORE.search(before):
            continue

        # 'test' with a direct object in non-excluded context = imperative
        return True

    return False


def _write_is_dev(text_lower: str) -> bool:
    """Return True when 'write' is followed (near) by a code artifact word."""
    if 'write' not in text_lower:
        return False
    words = frozenset(re.findall(r'\b\w+\b', text_lower))
    return bool(words & _WRITE_CODE_WORDS)


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
    'microservice', 'microservices', 'ci', 'cicd', 'workflow', 'hook',
    'plugin', 'backend', 'frontend', 'fullstack', 'cli', 'sdk', 'library',
    'package', 'lambda', 'serverless', 'container', 'kubernetes', 'docker',
    'terraform', 'redis', 'postgres', 'mysql', 'mongodb', 'elasticsearch',
    'graphql', 'grpc', 'websocket', 'cron', 'queue', 'worker',
    'security', 'vulnerability', 'vulnerabilities', 'injection', 'xss', 'csrf', 'exploit',
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

    if _BYPASS_RE.search(p):
        return DevIntentResult(False, 0.0, "skip", "bypass pattern")

    # 2. Greetings and short acknowledgements
    if _GREETING_RE.match(p) and len(p.split()) <= 5:
        return DevIntentResult(False, 0.0, "skip", "greeting/acknowledgement")

    # 3. Operations/admin tasks
    if _OPS_RE.search(p):
        return DevIntentResult(False, 0.1, "skip", "operations task")

    # 4. Feature extraction
    has_action = (bool(_ACTION_RE.search(p)) and not bool(_MAKE_NONDEV_RE.search(p))) \
                 or _write_is_dev(p_lower) \
                 or _is_test_imperative(p_lower)
    has_knowledge = bool(_KNOWLEDGE_RE.search(p))
    words = frozenset(re.findall(r'\b\w+\b', p_lower))
    tech_hits = _TECH_WORDS & words

    # 5. Clear action verb → high-confidence route
    if has_action and not has_knowledge:
        return DevIntentResult(True, 0.95, "required", "clear action request")

    # 6. Both action and knowledge ("explain how to implement X") → dev with context
    if has_action and has_knowledge:
        return DevIntentResult(True, 0.80, "recommended",
                               "action + knowledge: dev task with explanation request")

    # 7. Pure knowledge request → Q&A, do not route
    if has_knowledge and not has_action:
        return DevIntentResult(False, 0.25, "skip",
                               "knowledge/explanatory question")

    # 8. No question pattern, implicit dev context via tech words
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

    Injection strength is determined by the `tier` field of the result:
    - 'required':    MUST invoke immediately (action verbs, high confidence)
    - 'recommended': Should invoke (action + explanation requests)
    - 'suggested':   Consider invoking (implicit tech context, low confidence)
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

    Disable entirely: export AMPLIHACK_AUTO_DEV=false (also: 0, no, off)
    """
    auto_dev = os.environ.get("AMPLIHACK_AUTO_DEV", "true").lower().strip()
    if auto_dev in ("false", "0", "no", "off"):
        return False, ""

    result = classify(prompt)
    if not result.should_route:
        return False, ""

    return True, build_context_injection(result, prompt)
