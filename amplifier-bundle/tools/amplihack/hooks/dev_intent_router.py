#!/usr/bin/env python3
"""
dev_intent_router.py — Smart prompt routing for amplihack development workflows.

Six routing outcomes, matching amplihack's workflow types:

  DEV         → dev-orchestrator + DEFAULT_WORKFLOW (build, fix, write, verify, deploy)
  INVESTIGATE → dev-orchestrator + INVESTIGATION_WORKFLOW (analyze, explore, understand)
  HYBRID      → dev-orchestrator (investigate first, then implement)
  Q&A         → direct concise answer (knowledge questions)
  OPS         → direct execution (shell commands, admin)
  SKIP        → no injection (existing slash commands, greetings, bypasses)

Design principles:
  - Fast: <1ms (pure regex + keyword matching, no LLM)
  - Conservative on SKIP: anything that might be work gets routed somewhere
  - Human injection text: brief, helpful, not robotic
  - Disable: export AMPLIHACK_AUTO_DEV=false (also: 0, no, off)
"""

import os
import re
from dataclasses import dataclass


@dataclass
class IntentResult:
    route_type: str    # "dev" | "investigate" | "hybrid" | "qa" | "ops" | "skip"
    confidence: float  # 0.0–1.0
    tier: str          # "required" | "recommended" | "suggested" | "skip"
    reason: str

    @property
    def should_route(self) -> bool:
        """True for any route that produces an injection."""
        return self.route_type != "skip"

# Backwards-compatible alias
DevIntentResult = IntentResult


# ── Hard bypasses ─────────────────────────────────────────────────────────────

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


# ── Greetings ─────────────────────────────────────────────────────────────────

_GREETING_RE = re.compile(
    r'^(?:hi\b|hello\b|hey\b|thanks\b|thank\s+you|ok\b|okay\b|'
    r'yes\b|no\b|sure\b|sounds\s+good|great\b|perfect\b|'
    r'awesome\b|cool\b|nice\b|got\s+it|understood)\b',
    re.I,
)


# ── Operations (shell/admin) ─────────────────────────────────────────────────

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


# ── Q&A / knowledge patterns ─────────────────────────────────────────────────

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


# ── Development action verbs ─────────────────────────────────────────────────
# Build, fix, write, verify, deploy — things that CHANGE the codebase

_DEV_RE = re.compile(
    r'\b(?:implement|build|create|fix|add|develop|make|generate|configure|'
    r'optimize|improve|patch|repair|resolve|handle|update|upgrade|refactor|'
    r'migrate|deploy|integrate|scaffold|debug|verify|'
    r'structure|architect|design|organize|arrange|'
    r'set\s+up|clean\s+up|wire\s+up|hook\s+up|spin\s+up|'
    r'port\s+(?:to|from)|extract|split|merge|combine|'
    r'profile|monitor|benchmark|secure|harden|automate|'
    r'document|write)\b',
    re.I,
)


# ── Investigation verbs ──────────────────────────────────────────────────────
# Understand, explore, analyze — things that READ and LEARN about the codebase

_INVESTIGATE_RE = re.compile(
    r'\b(?:investigate|analyze|explore|research|understand|'
    r'audit|study|examine|'
    r'map\s+(?:out|the)|trace|'
    r'look\s+(?:at|into)|dig\s+into|'
    r'figure\s+out|find\s+out)\b',
    re.I,
)


# ── Test-verb detection ──────────────────────────────────────────────────────

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
    """True when 'test' is an imperative verb (not a noun or modal context)."""
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


# ── Technology context ────────────────────────────────────────────────────────

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


# ── Review verb (can be either investigate or dev depending on context) ──────

_REVIEW_RE = re.compile(r'\breview\b', re.I)


# ── Main classifier ──────────────────────────────────────────────────────────

def classify(prompt: str) -> IntentResult:
    """
    Classify a user prompt into one of six routing outcomes.

    DEV:         Build, fix, write, verify, deploy → DEFAULT_WORKFLOW
    INVESTIGATE: Analyze, explore, understand → INVESTIGATION_WORKFLOW
    HYBRID:      Both investigate AND dev verbs → investigate then implement
    Q&A:         Knowledge/explanation question → direct answer
    OPS:         Shell/admin → execute directly
    SKIP:        Existing commands, greetings, bypasses → no injection
    """
    if not prompt or not prompt.strip():
        return IntentResult("skip", 0.0, "skip", "empty prompt")

    p = prompt.strip()
    p_lower = p.lower()

    # 1. Hard bypasses
    for prefix in _SKIP_PREFIXES:
        if p_lower.startswith(prefix):
            return IntentResult("skip", 0.0, "skip", "existing command")

    if _BYPASS_RE.search(p):
        return IntentResult("skip", 0.0, "skip", "explicit bypass")

    # 2. Greetings
    if _GREETING_RE.match(p) and len(p.split()) <= 5:
        return IntentResult("skip", 0.0, "skip", "greeting")

    # 3. Operations
    if _OPS_RE.search(p):
        return IntentResult("ops", 0.85, "required", "operations task")

    # 4. Feature extraction
    has_dev = bool(_DEV_RE.search(p)) or _is_test_imperative(p_lower)
    has_investigate = bool(_INVESTIGATE_RE.search(p))
    has_review = bool(_REVIEW_RE.search(p))
    has_knowledge = bool(_KNOWLEDGE_RE.search(p))
    words = frozenset(re.findall(r'\b\w+\b', p_lower))
    tech_hits = _TECH_WORDS & words

    # 'review' context: "review PR #42" = dev; "review the architecture" = investigate
    if has_review and not has_dev and not has_investigate:
        if tech_hits & {'pr', 'code', 'implementation', 'fix', 'patch'}:
            has_dev = True
        else:
            has_investigate = True

    # For hybrid detection: filter out dev-verb matches that are actually nouns.
    # "the build is failing" → "build" is a noun; "investigate then build it" → verb.
    # Check ALL dev matches — if any real verb exists (not preceded by article), keep has_dev.
    if has_investigate and has_dev:
        _article_re = re.compile(r'\b(?:the|a|an|this|that|my|our|your|its)\s+$', re.I)
        has_real_dev_verb = False
        for dev_m in _DEV_RE.finditer(p):
            before = p[:dev_m.start()]
            if not _article_re.search(before):
                has_real_dev_verb = True
                break
        if not has_real_dev_verb:
            has_dev = False

    # 5. HYBRID: both investigate AND dev verbs present
    #    "investigate X then implement Y", "analyze and fix", "understand then add"
    if has_investigate and has_dev:
        return IntentResult("hybrid", 0.90, "required",
                            "investigate then implement")

    # 6. Pure development action (no investigation verb, no knowledge question)
    if has_dev and not has_knowledge:
        return IntentResult("dev", 0.95, "required", "development task")

    # 7. Development + knowledge ("explain how to implement X")
    if has_dev and has_knowledge:
        return IntentResult("dev", 0.80, "recommended",
                            "development task with explanation")

    # 8. Pure investigation (no dev verb)
    if has_investigate and not has_knowledge:
        return IntentResult("investigate", 0.90, "required", "investigation task")

    # 9. Investigation + knowledge ("how does the caching layer work")
    if has_investigate and has_knowledge:
        return IntentResult("investigate", 0.80, "recommended",
                            "investigation with explanation")

    # 10. Pure Q&A (knowledge question, no action verbs)
    if has_knowledge and not has_dev and not has_investigate:
        return IntentResult("qa", 0.85, "required", "knowledge question")

    # 11. Implicit dev context via tech words
    if len(tech_hits) >= 2:
        return IntentResult("dev", 0.55, "suggested",
                            f"implicit dev context: {tech_hits}")

    if tech_hits:
        return IntentResult("skip", 0.30, "skip", "single tech word, ambiguous")

    return IntentResult("skip", 0.10, "skip", "no clear intent")


# ── Injection builders ────────────────────────────────────────────────────────

def build_context_injection(result: IntentResult, prompt: str) -> str:
    """Build human-readable routing signal for Claude."""

    task_preview = prompt[:200]

    if result.route_type == "dev":
        directives = {
            "required":    'Invoke Skill(skill="dev-orchestrator") — this is a development task.',
            "recommended": 'This looks like a dev task. Invoke Skill(skill="dev-orchestrator") '
                           'unless you have a reason to answer directly.',
            "suggested":   'This might be a dev task. Consider invoking '
                           'Skill(skill="dev-orchestrator").',
        }
        return (
            f'<system-reminder source="auto-dev-router">\n'
            f'{directives.get(result.tier, "")}\n'
            f'Task: "{task_preview}"\n'
            f'</system-reminder>'
        )

    if result.route_type == "investigate":
        return (
            f'<system-reminder source="auto-dev-router">\n'
            f'This is an investigation/research task. '
            f'Invoke Skill(skill="dev-orchestrator") — it will use the '
            f'INVESTIGATION_WORKFLOW to analyze the system.\n'
            f'Task: "{task_preview}"\n'
            f'</system-reminder>'
        )

    if result.route_type == "hybrid":
        return (
            f'<system-reminder source="auto-dev-router">\n'
            f'This is a hybrid task — investigate first, then implement. '
            f'Invoke Skill(skill="dev-orchestrator") — it will create '
            f'investigation and development workstreams.\n'
            f'Task: "{task_preview}"\n'
            f'</system-reminder>'
        )

    if result.route_type == "qa":
        return (
            f'<system-reminder source="auto-qa-router">\n'
            f'Knowledge/Q&A question — answer directly and concisely. '
            f'No workflow invocation needed.\n'
            f'Question: "{task_preview}"\n'
            f'</system-reminder>'
        )

    if result.route_type == "ops":
        return (
            f'<system-reminder source="auto-ops-router">\n'
            f'Operations/admin task — execute directly. '
            f'No workflow invocation needed.\n'
            f'Task: "{task_preview}"\n'
            f'</system-reminder>'
        )

    return ""


def should_auto_route(prompt: str) -> tuple[bool, str]:
    """
    Main entry point for user_prompt_submit.py.

    Returns (should_inject, injection_text).
    Disable: export AMPLIHACK_AUTO_DEV=false (also: 0, no, off)
    """
    auto_dev = os.environ.get("AMPLIHACK_AUTO_DEV", "true").lower().strip()
    if auto_dev in ("false", "0", "no", "off"):
        return False, ""

    result = classify(prompt)
    if result.route_type == "skip":
        return False, ""

    return True, build_context_injection(result, prompt)
