"""General-purpose agent capability evaluations beyond memory.

Measures five dimensions of agent competence:
1. Tool Use Efficiency: Correct tool selection, chaining, and call economy
2. Planning: Multi-step task decomposition and execution
3. Reasoning Under Uncertainty: Handling incomplete/conflicting evidence
4. Cross-Domain Transfer: Applying learned patterns to new domains
5. Collaborative Task: Multi-agent delegation and synthesis (if spawning enabled)

Each eval type defines scenarios with gold-standard expectations, runs the
agent through them, and grades using rubric-based LLM evaluation.

Usage:
    python -m amplihack.eval.general_capability_eval --eval tool_use,planning,reasoning
    python -m amplihack.eval.general_capability_eval --eval all --sdk mini
    python -m amplihack.eval.general_capability_eval --eval planning --output-dir /tmp/cap-eval

Philosophy: Data-driven scenario evaluation, separates scenario definition
from runner logic. Each eval is self-contained and independently runnable.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import statistics
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import anthropic  # type: ignore[import-untyped]  # pyright: ignore[reportMissingImports]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ToolCall:
    """A single tool call recorded during agent execution."""

    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    result: str = ""
    timestamp_ms: int = 0


@dataclass
class ToolTrajectory:
    """Complete record of tool calls made by an agent for a task."""

    task_description: str
    calls: list[ToolCall] = field(default_factory=list)
    total_time_ms: int = 0

    @property
    def call_names(self) -> list[str]:
        """Return ordered list of tool names called."""
        return [c.tool_name for c in self.calls]

    @property
    def unique_tools(self) -> set[str]:
        """Return set of distinct tools used."""
        return {c.tool_name for c in self.calls}

    @property
    def call_count(self) -> int:
        return len(self.calls)


@dataclass
class ScenarioResult:
    """Result of running one scenario within an eval."""

    scenario_id: str
    scenario_name: str
    agent_response: str
    trajectory: ToolTrajectory | None = None
    scores: dict[str, float] = field(default_factory=dict)
    reasoning: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalTypeResult:
    """Aggregate result for one eval type (e.g. tool_use)."""

    eval_type: str
    scenarios: list[ScenarioResult] = field(default_factory=list)
    metric_averages: dict[str, float] = field(default_factory=dict)
    overall_score: float = 0.0
    duration_s: float = 0.0

    def compute_averages(self) -> None:
        """Compute metric averages across all scenarios."""
        if not self.scenarios:
            return
        all_metrics: dict[str, list[float]] = {}
        for s in self.scenarios:
            for k, v in s.scores.items():
                all_metrics.setdefault(k, []).append(v)
        self.metric_averages = {k: statistics.mean(v) for k, v in all_metrics.items()}
        if self.metric_averages:
            self.overall_score = statistics.mean(self.metric_averages.values())


@dataclass
class CapabilityReport:
    """Complete report across all eval types."""

    eval_results: list[EvalTypeResult] = field(default_factory=list)
    agent_name: str = ""
    agent_sdk: str = ""
    agent_model: str = ""
    grader_model: str = ""
    timestamp: str = ""
    total_time_s: float = 0.0

    @property
    def overall_score(self) -> float:
        if not self.eval_results:
            return 0.0
        return statistics.mean(r.overall_score for r in self.eval_results)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "agent_sdk": self.agent_sdk,
            "agent_model": self.agent_model,
            "grader_model": self.grader_model,
            "timestamp": self.timestamp,
            "total_time_s": self.total_time_s,
            "overall_score": self.overall_score,
            "eval_results": [
                {
                    "eval_type": r.eval_type,
                    "overall_score": r.overall_score,
                    "metric_averages": r.metric_averages,
                    "duration_s": r.duration_s,
                    "scenarios": [
                        {
                            "scenario_id": s.scenario_id,
                            "scenario_name": s.scenario_name,
                            "scores": s.scores,
                            "reasoning": s.reasoning,
                        }
                        for s in r.scenarios
                    ],
                }
                for r in self.eval_results
            ],
        }


# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------


@dataclass
class ToolUseScenario:
    """Defines a task with a gold-standard tool sequence."""

    scenario_id: str
    name: str
    task: str
    context_content: str  # Content to pre-load into agent memory
    expected_tool_order: list[str]  # Gold tool sequence
    unnecessary_tools: list[str]  # Tools that should NOT be called
    max_calls: int  # Efficient upper bound on total calls


TOOL_USE_SCENARIOS = [
    ToolUseScenario(
        scenario_id="TU-1",
        name="Learn then recall",
        task="What is the maximum safe dosage of ibuprofen per day?",
        context_content=(
            "The maximum safe dosage of ibuprofen for adults is 1200mg per day "
            "for over-the-counter use, or up to 3200mg per day under medical "
            "supervision. Doses should be taken every 4-6 hours."
        ),
        expected_tool_order=["search_memory", "synthesize_answer"],
        unnecessary_tools=["calculate", "read_content"],
        max_calls=4,
    ),
    ToolUseScenario(
        scenario_id="TU-2",
        name="Calculate from memory",
        task=(
            "If Norway has 26 total medals and Italy has 22, what is the "
            "percentage difference between their medal counts?"
        ),
        context_content=(
            "As of February 15, 2026, the Milan-Cortina Winter Olympics medal standings: "
            "Norway leads with 26 total medals. Italy is in second place with 22 total medals."
        ),
        expected_tool_order=["search_memory", "calculate", "synthesize_answer"],
        unnecessary_tools=["read_content", "explain_knowledge"],
        max_calls=5,
    ),
    ToolUseScenario(
        scenario_id="TU-3",
        name="No-knowledge question",
        task="What color is the sky on Mars during sunset?",
        context_content=(
            "Earth's sky appears blue during the day due to Rayleigh scattering. "
            "Sunsets on Earth appear red/orange as light travels through more atmosphere."
        ),
        expected_tool_order=["search_memory", "synthesize_answer"],
        unnecessary_tools=["calculate", "read_content"],
        max_calls=4,
    ),
    ToolUseScenario(
        scenario_id="TU-4",
        name="Multi-fact synthesis",
        task=(
            "Compare the security postures of CompanyA and CompanyB based on "
            "their recent audit results."
        ),
        context_content=(
            "CompanyA Security Audit (2026-01): Passed 94% of controls. "
            "Key findings: unpatched CVE-2025-1234 on 3 servers, MFA not enforced "
            "for VPN access. Remediation deadline: 30 days.\n\n"
            "CompanyB Security Audit (2026-01): Passed 87% of controls. "
            "Key findings: open S3 buckets with PII data, default credentials on "
            "2 network devices, no SIEM logging for cloud workloads. "
            "Remediation deadline: 14 days due to severity."
        ),
        expected_tool_order=["search_memory", "search_memory", "synthesize_answer"],
        unnecessary_tools=["calculate"],
        max_calls=6,
    ),
]


@dataclass
class PlanningScenario:
    """Defines a task requiring multi-step planning."""

    scenario_id: str
    name: str
    task: str
    context_content: str
    expected_subtasks: list[str]  # Key subtasks that should appear in plan
    expected_ordering_constraints: list[tuple[str, str]]  # (before, after) pairs
    success_criteria: str  # What makes a complete answer


PLANNING_SCENARIOS = [
    PlanningScenario(
        scenario_id="PL-1",
        name="Security incident investigation",
        task=(
            "Investigate the security incident, identify all affected systems, "
            "determine the attack vector, and recommend remediation steps."
        ),
        context_content=(
            "INCIDENT REPORT IR-2026-042:\n"
            "At 03:14 UTC on 2026-02-20, the SOC detected unusual outbound traffic "
            "from server web-prod-03 (10.1.2.33). Initial analysis shows:\n"
            "- 2.3GB data transferred to external IP 198.51.100.47\n"
            "- SSH brute force attempts from 198.51.100.47 starting at 01:22 UTC\n"
            "- Successful SSH login to web-prod-03 at 02:58 UTC using service account 'deploy-svc'\n"
            "- Lateral movement detected: web-prod-03 -> db-prod-01 (10.1.2.50) at 03:02 UTC\n"
            "- db-prod-01 hosts customer PII database (PostgreSQL)\n"
            "- No evidence of data modification, only SELECT queries observed\n"
            "- Firewall logs show port 22 open to 0.0.0.0/0 on web-prod-03"
        ),
        expected_subtasks=[
            "identify affected systems",
            "determine attack vector",
            "assess data exposure",
            "recommend remediation",
        ],
        expected_ordering_constraints=[
            ("identify affected systems", "assess data exposure"),
            ("determine attack vector", "recommend remediation"),
        ],
        success_criteria=(
            "Answer must: (1) list affected systems (web-prod-03, db-prod-01), "
            "(2) identify SSH brute force as attack vector, (3) note PII database "
            "access, (4) recommend specific remediation (close port 22, rotate "
            "credentials, review deploy-svc permissions)"
        ),
    ),
    PlanningScenario(
        scenario_id="PL-2",
        name="System migration planning",
        task=(
            "Plan the migration of our monolithic application to microservices. "
            "Identify the services to extract, their dependencies, the migration "
            "order, and rollback strategy."
        ),
        context_content=(
            "SYSTEM OVERVIEW - OrderManager Monolith:\n"
            "- Single Django application handling: user auth, product catalog, "
            "order processing, payment, shipping, notifications\n"
            "- Shared PostgreSQL database with 47 tables\n"
            "- 250K lines of Python code, 15 developers\n"
            "- Current issues: 45-minute deploy cycles, one module's bugs crash everything\n"
            "- Dependencies: Auth -> all modules, Product -> Orders, Orders -> Payment -> Shipping, "
            "Notifications depends on Orders and Shipping\n"
            "- SLA: 99.9% uptime, max 5s response time"
        ),
        expected_subtasks=[
            "identify service boundaries",
            "map dependencies",
            "determine migration order",
            "plan rollback strategy",
        ],
        expected_ordering_constraints=[
            ("identify service boundaries", "determine migration order"),
            ("map dependencies", "determine migration order"),
        ],
        success_criteria=(
            "Answer must: (1) identify at least 4 services to extract, "
            "(2) recognize Auth as foundational dependency, (3) propose a "
            "migration order that respects dependencies, (4) include rollback plan"
        ),
    ),
    PlanningScenario(
        scenario_id="PL-3",
        name="Root cause analysis workflow",
        task=(
            "Our production database is experiencing intermittent query timeouts. "
            "Design a systematic investigation plan, execute it, and report findings."
        ),
        context_content=(
            "DATABASE PERFORMANCE ALERT:\n"
            "- PostgreSQL 15 cluster, primary + 2 read replicas\n"
            "- Timeouts started 2026-02-18 around 14:00 UTC\n"
            "- Affected queries: JOIN-heavy reports on orders + inventory tables\n"
            "- orders table: 12M rows, inventory: 800K rows\n"
            "- Last schema change: 2026-02-17 added column 'priority' to orders (no index)\n"
            "- Last deploy: 2026-02-18 08:00 UTC added new reporting endpoint\n"
            "- Replica lag increased from 50ms to 2.3s during incidents\n"
            "- Connection pool: 50 max connections, hitting 48 during peak\n"
            "- autovacuum last ran on orders table: 2026-02-15"
        ),
        expected_subtasks=[
            "gather symptoms",
            "form hypotheses",
            "test hypotheses",
            "identify root cause",
            "recommend fix",
        ],
        expected_ordering_constraints=[
            ("gather symptoms", "form hypotheses"),
            ("form hypotheses", "test hypotheses"),
            ("test hypotheses", "identify root cause"),
        ],
        success_criteria=(
            "Answer must: (1) identify the missing index on 'priority' column as "
            "likely cause, (2) note the correlation with schema change timing, "
            "(3) mention connection pool saturation as contributing factor, "
            "(4) recommend adding index and adjusting connection pool"
        ),
    ),
]


@dataclass
class UncertaintyScenario:
    """Defines a scenario with conflicting or incomplete information."""

    scenario_id: str
    name: str
    question: str
    evidence_pieces: list[dict[str, Any]]  # Each has 'content', 'confidence', 'source'
    expected_behavior: str  # What the agent should do
    key_criteria: list[str]  # Rubric items to grade


UNCERTAINTY_SCENARIOS = [
    UncertaintyScenario(
        scenario_id="RU-1",
        name="Conflicting expert reports",
        question=(
            "Based on available reports, what caused the outage on 2026-02-10 "
            "and how long did it last?"
        ),
        evidence_pieces=[
            {
                "content": (
                    "Post-incident report from SRE team (2026-02-11): The outage "
                    "on 2026-02-10 was caused by a misconfigured load balancer "
                    "rule deployed at 14:32 UTC. Duration: 47 minutes."
                ),
                "confidence": 0.9,
                "source": "SRE post-incident report",
            },
            {
                "content": (
                    "Network team analysis (2026-02-12): Root cause was a BGP "
                    "route leak from upstream provider AS64512. The load balancer "
                    "misconfiguration was a symptom, not the cause. Duration: "
                    "approximately 2 hours including partial degradation."
                ),
                "confidence": 0.85,
                "source": "Network team analysis",
            },
            {
                "content": (
                    "Customer impact dashboard: 73% of API requests failed between "
                    "14:35 and 15:22 UTC. Partial recovery at 15:22, full recovery "
                    "at 16:30 UTC."
                ),
                "confidence": 0.95,
                "source": "Monitoring dashboard",
            },
        ],
        expected_behavior=(
            "Acknowledge the disagreement between SRE and Network teams on root "
            "cause. Use dashboard data to corroborate the Network team's longer "
            "duration estimate. Present both theories with appropriate hedging."
        ),
        key_criteria=[
            "acknowledges_conflict",
            "cites_both_sources",
            "uses_dashboard_as_evidence",
            "appropriate_hedging",
            "synthesizes_rather_than_picks_one",
        ],
    ),
    UncertaintyScenario(
        scenario_id="RU-2",
        name="Incomplete information with gap acknowledgment",
        question="What is the current risk level for CVE-2026-0042?",
        evidence_pieces=[
            {
                "content": (
                    "NVD entry (2026-02-01): CVE-2026-0042 affects OpenSSL 3.1.x. "
                    "CVSS base score: 7.5 (High). Attack vector: Network. "
                    "No exploit code observed in the wild as of publication."
                ),
                "confidence": 0.95,
                "source": "NVD database",
            },
            {
                "content": (
                    "Threat intelligence feed (2026-02-15): Proof-of-concept "
                    "exploit for CVE-2026-0042 published on GitHub. Reliability: "
                    "unverified. Our environment runs OpenSSL 3.1.4."
                ),
                "confidence": 0.6,
                "source": "Threat intel feed (unverified)",
            },
        ],
        expected_behavior=(
            "Report the CVSS score from NVD as reliable baseline. Note the PoC "
            "exploit report but flag it as unverified. Acknowledge missing info: "
            "whether our specific version is patched, whether exploit works in "
            "practice. Recommend investigation without false certainty."
        ),
        key_criteria=[
            "reports_cvss_accurately",
            "flags_unverified_source",
            "acknowledges_missing_info",
            "does_not_overstate_certainty",
            "recommends_further_investigation",
        ],
    ),
    UncertaintyScenario(
        scenario_id="RU-3",
        name="Probabilistic evidence weighing",
        question=(
            "Should we proceed with the vendor contract renewal given the "
            "available security assessment data?"
        ),
        evidence_pieces=[
            {
                "content": (
                    "Annual security assessment (2025-12): Vendor passed 91% of "
                    "SOC2 controls. Two critical findings: no encryption at rest "
                    "for backups, shared admin credentials. Remediation committed "
                    "by Q1 2026."
                ),
                "confidence": 0.9,
                "source": "2025 annual assessment",
            },
            {
                "content": (
                    "Vendor self-attestation (2026-02): 'All critical findings "
                    "from 2025 assessment have been remediated.' No independent "
                    "verification provided."
                ),
                "confidence": 0.4,
                "source": "Vendor self-attestation",
            },
            {
                "content": (
                    "Peer company report (informal, 2026-01): 'We dropped this "
                    "vendor after finding they hadn't actually implemented "
                    "encryption at rest despite claiming they did.'"
                ),
                "confidence": 0.5,
                "source": "Informal peer report",
            },
        ],
        expected_behavior=(
            "Weight evidence by reliability. The formal assessment is strongest. "
            "The self-attestation is weak (no verification). The peer report is "
            "concerning but informal. Recommend: do not renew without independent "
            "verification of remediation."
        ),
        key_criteria=[
            "weights_evidence_by_reliability",
            "distinguishes_verified_vs_self_reported",
            "notes_peer_report_concern",
            "recommends_verification_before_renewal",
            "avoids_binary_yes_no_without_nuance",
        ],
    ),
]


@dataclass
class TransferScenario:
    """Defines a scenario testing cross-domain knowledge transfer."""

    scenario_id: str
    name: str
    source_domain_content: str  # Knowledge in domain A
    target_domain_question: str  # Question in domain B that benefits from domain A
    expected_analogy: str  # How A should inform B
    key_criteria: list[str]


TRANSFER_SCENARIOS = [
    TransferScenario(
        scenario_id="CT-1",
        name="Security patterns to new system",
        source_domain_content=(
            "SECURITY PATTERN KNOWLEDGE BASE:\n"
            "Pattern: Defense in Depth\n"
            "- Multiple layers of security controls\n"
            "- If one layer fails, others still protect\n"
            "- Applied in: network segmentation, WAF + IDS + firewall, "
            "auth (MFA + session tokens + IP allowlisting)\n\n"
            "Pattern: Least Privilege\n"
            "- Grant minimum permissions needed for function\n"
            "- Reduces blast radius of compromise\n"
            "- Applied in: IAM roles, database user permissions, API scopes\n\n"
            "Pattern: Zero Trust\n"
            "- Never trust, always verify\n"
            "- Every request authenticated regardless of network location\n"
            "- Applied in: service mesh mTLS, API gateway auth, microsegmentation"
        ),
        target_domain_question=(
            "We are deploying a new IoT sensor network for a smart building. "
            "The sensors collect temperature, occupancy, and energy data. "
            "They communicate via MQTT to a central broker. "
            "What security architecture would you recommend?"
        ),
        expected_analogy=(
            "Apply Defense in Depth (MQTT TLS + broker auth + network segmentation), "
            "Least Privilege (per-sensor topic ACLs, read-only for most sensors), "
            "and Zero Trust (per-device certificates, no implicit trust from being "
            "on the same network)."
        ),
        key_criteria=[
            "applies_defense_in_depth",
            "applies_least_privilege",
            "applies_zero_trust",
            "adapts_to_iot_context",
            "mentions_specific_iot_concerns",
        ],
    ),
    TransferScenario(
        scenario_id="CT-2",
        name="Incident response to new domain",
        source_domain_content=(
            "INCIDENT RESPONSE FRAMEWORK:\n"
            "Phase 1: Detection & Triage - Identify scope, severity, affected assets\n"
            "Phase 2: Containment - Isolate affected systems, preserve evidence\n"
            "Phase 3: Eradication - Remove threat, patch vulnerabilities\n"
            "Phase 4: Recovery - Restore services, verify integrity\n"
            "Phase 5: Lessons Learned - Document findings, update playbooks\n\n"
            "Key principle: Speed of containment is the #1 factor in reducing damage. "
            "Always preserve forensic evidence before eradication."
        ),
        target_domain_question=(
            "A data quality issue has been discovered: customer addresses in our "
            "CRM have been corrupted by a buggy import script that ran 3 days ago. "
            "About 15,000 records are affected. How should we handle this?"
        ),
        expected_analogy=(
            "Apply incident response phases: (1) Triage - scope the 15K records, "
            "determine which imports were affected; (2) Contain - stop the import "
            "script, prevent further corruption; (3) Eradicate - fix the script bug; "
            "(4) Recover - restore records from backup before the bad import; "
            "(5) Lessons learned - add validation checks to prevent recurrence."
        ),
        key_criteria=[
            "follows_phased_approach",
            "prioritizes_containment",
            "preserves_data_evidence",
            "includes_recovery_from_backup",
            "includes_prevention_measures",
        ],
    ),
]


@dataclass
class CollaborativeScenario:
    """Defines a task requiring multi-agent collaboration."""

    scenario_id: str
    name: str
    task: str
    context_content: str
    expected_delegations: list[str]  # Specialist types that should be spawned
    synthesis_criteria: list[str]  # What the final synthesis should contain


COLLABORATIVE_SCENARIOS = [
    CollaborativeScenario(
        scenario_id="CO-1",
        name="Architecture review with specialists",
        task=(
            "Review this system design for the new payment processing service "
            "from security, performance, and reliability perspectives."
        ),
        context_content=(
            "DESIGN DOC: Payment Processing Service v2\n"
            "- Receives payment intents via REST API (HTTPS)\n"
            "- Validates card details against Stripe API\n"
            "- Stores transaction records in PostgreSQL (encrypted at rest)\n"
            "- Publishes events to Kafka for downstream consumers\n"
            "- Rate limit: 500 TPS\n"
            "- Runs on 3 Kubernetes pods with HPA\n"
            "- PCI DSS compliance required\n"
            "- Card numbers stored in Stripe vault, only tokenized references locally"
        ),
        expected_delegations=["security", "performance", "reliability"],
        synthesis_criteria=[
            "security_findings_present",
            "performance_findings_present",
            "reliability_findings_present",
            "findings_are_specific_to_design",
            "cross_cutting_issues_identified",
        ],
    ),
    CollaborativeScenario(
        scenario_id="CO-2",
        name="Cross-functional incident response",
        task=(
            "Coordinate the response to a production outage affecting the "
            "checkout flow. We need engineering, customer support, and "
            "executive communication handled simultaneously."
        ),
        context_content=(
            "OUTAGE ALERT: Checkout service returning 503 errors\n"
            "- Started: 2026-02-20 09:15 UTC\n"
            "- Impact: 100% of checkout attempts failing\n"
            "- Preliminary cause: database connection pool exhausted\n"
            "- Revenue impact: ~$45K/hour\n"
            "- Customer complaints flooding support channels\n"
            "- CEO asking for status update"
        ),
        expected_delegations=["engineering", "communication", "analysis"],
        synthesis_criteria=[
            "engineering_actions_defined",
            "customer_communication_drafted",
            "executive_summary_included",
            "parallel_execution_demonstrated",
            "timeline_and_priority_clear",
        ],
    ),
]


# ---------------------------------------------------------------------------
# LLM-based grading
# ---------------------------------------------------------------------------


def _get_anthropic_client() -> anthropic.Anthropic:
    """Create Anthropic client from environment."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise OSError("ANTHROPIC_API_KEY environment variable required for grading")
    return anthropic.Anthropic(api_key=api_key)


def _extract_json(text: str) -> dict:
    """Extract JSON object from LLM response text."""
    import re

    stripped = text.strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass
    fenced = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", stripped, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1).strip())
        except json.JSONDecodeError:
            pass
    brace_match = re.search(r"\{.*\}", stripped, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass
    raise json.JSONDecodeError(f"No valid JSON in: {stripped[:200]}", stripped, 0)


def _llm_grade(prompt: str, grader_model: str | None = None) -> dict[str, Any]:
    """Run a grading prompt through the LLM and return parsed JSON.

    Args:
        prompt: Grading prompt expecting JSON response
        grader_model: Model to use (defaults to env GRADER_MODEL or claude-opus-4-6)

    Returns:
        Parsed JSON dict from grader response
    """
    client = _get_anthropic_client()
    model = grader_model or os.environ.get("GRADER_MODEL", "claude-opus-4-6")
    message = client.messages.create(
        model=model,
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )
    return _extract_json(message.content[0].text)


# ---------------------------------------------------------------------------
# Tool Use Efficiency Eval
# ---------------------------------------------------------------------------


def _grade_tool_use(
    scenario: ToolUseScenario,
    trajectory: ToolTrajectory,
    agent_response: str,
) -> ScenarioResult:
    """Grade tool use efficiency for a single scenario.

    Metrics:
    - tool_selection_accuracy: Did the agent call the right tools?
    - tool_chain_correctness: Were tools called in the right order?
    - call_efficiency: Was the total call count within budget?
    """
    actual_names = trajectory.call_names
    expected = scenario.expected_tool_order

    # Tool selection accuracy: fraction of expected tools that were called
    expected_set = set(expected)
    called_set = trajectory.unique_tools
    if expected_set:
        selection_recall = len(expected_set & called_set) / len(expected_set)
    else:
        selection_recall = 1.0

    # Penalize for unnecessary tools
    unnecessary_called = called_set & set(scenario.unnecessary_tools)
    unnecessary_penalty = len(unnecessary_called) * 0.15
    selection_accuracy = max(0.0, selection_recall - unnecessary_penalty)

    # Tool chain correctness: check ordering constraints
    # For each pair (expected[i], expected[i+1]), check that actual
    # first occurrence of expected[i] < first occurrence of expected[i+1]
    chain_score = 1.0
    if len(expected) > 1:
        correct_orderings = 0
        total_orderings = 0
        for i in range(len(expected) - 1):
            a, b = expected[i], expected[i + 1]
            total_orderings += 1
            try:
                first_a = actual_names.index(a)
                first_b = actual_names.index(b)
                if first_a < first_b:
                    correct_orderings += 1
            except ValueError:
                pass  # Missing tool, already penalized in selection
        if total_orderings > 0:
            chain_score = correct_orderings / total_orderings

    # Call efficiency: 1.0 if at or below max_calls, linearly decreasing
    if trajectory.call_count <= scenario.max_calls:
        efficiency = 1.0
    else:
        excess = trajectory.call_count - scenario.max_calls
        efficiency = max(0.0, 1.0 - (excess * 0.2))

    scores = {
        "tool_selection_accuracy": round(selection_accuracy, 3),
        "tool_chain_correctness": round(chain_score, 3),
        "call_efficiency": round(efficiency, 3),
    }

    reasoning = (
        f"Expected tools: {expected}, Actual: {actual_names}. "
        f"Selection: {selection_accuracy:.2f}, Chain: {chain_score:.2f}, "
        f"Efficiency: {efficiency:.2f} ({trajectory.call_count}/{scenario.max_calls} calls)"
    )

    return ScenarioResult(
        scenario_id=scenario.scenario_id,
        scenario_name=scenario.name,
        agent_response=agent_response,
        trajectory=trajectory,
        scores=scores,
        reasoning=reasoning,
    )


# ---------------------------------------------------------------------------
# Planning Eval
# ---------------------------------------------------------------------------


def _grade_planning(
    scenario: PlanningScenario,
    agent_response: str,
    grader_model: str | None = None,
) -> ScenarioResult:
    """Grade planning quality using LLM rubric evaluation.

    Metrics:
    - plan_completeness: Were all expected subtasks addressed?
    - plan_ordering: Were ordering constraints respected?
    - plan_execution_success: Does the response meet success criteria?
    """
    subtasks_str = "\n".join(f"  - {s}" for s in scenario.expected_subtasks)
    ordering_str = "\n".join(
        f"  - '{a}' must come before '{b}'" for a, b in scenario.expected_ordering_constraints
    )

    prompt = f"""You are evaluating an AI agent's planning and problem-solving ability.

TASK: {scenario.task}

CONTEXT PROVIDED TO AGENT:
{scenario.context_content}

AGENT'S RESPONSE:
{agent_response}

EVALUATION CRITERIA:

1. plan_completeness (0.0-1.0): Did the agent address all required subtasks?
Required subtasks:
{subtasks_str}
Score 1.0 if all subtasks are addressed. Deduct proportionally for missing subtasks.

2. plan_ordering (0.0-1.0): Did the agent respect logical ordering?
Ordering constraints:
{ordering_str}
Score 1.0 if all ordering constraints are respected in the response structure.

3. plan_execution_success (0.0-1.0): Does the response meet the success criteria?
Success criteria: {scenario.success_criteria}
Score based on how many criteria elements are present and correct.

Return ONLY a JSON object:
{{"plan_completeness": 0.85, "plan_ordering": 0.9, "plan_execution_success": 0.8, "reasoning": "Brief explanation"}}"""

    result = _llm_grade(prompt, grader_model)

    scores = {
        "plan_completeness": float(result.get("plan_completeness", 0.0)),
        "plan_ordering": float(result.get("plan_ordering", 0.0)),
        "plan_execution_success": float(result.get("plan_execution_success", 0.0)),
    }

    return ScenarioResult(
        scenario_id=scenario.scenario_id,
        scenario_name=scenario.name,
        agent_response=agent_response,
        scores=scores,
        reasoning=result.get("reasoning", ""),
    )


# ---------------------------------------------------------------------------
# Reasoning Under Uncertainty Eval
# ---------------------------------------------------------------------------


def _grade_uncertainty(
    scenario: UncertaintyScenario,
    agent_response: str,
    grader_model: str | None = None,
) -> ScenarioResult:
    """Grade reasoning under uncertainty using LLM rubric.

    Metrics:
    - uncertainty_calibration: Does the agent express appropriate confidence levels?
    - evidence_weighing: Does the agent weight sources by reliability?
    - hedging_appropriateness: Does the agent hedge correctly (not over or under)?
    """
    evidence_str = "\n".join(
        f"  Source: {e['source']} (confidence: {e['confidence']})\n  Content: {e['content']}"
        for e in scenario.evidence_pieces
    )
    criteria_str = "\n".join(f"  - {c}" for c in scenario.key_criteria)

    prompt = f"""You are evaluating an AI agent's ability to reason under uncertainty.

QUESTION: {scenario.question}

EVIDENCE PROVIDED (with confidence levels):
{evidence_str}

EXPECTED BEHAVIOR: {scenario.expected_behavior}

AGENT'S RESPONSE:
{agent_response}

EVALUATION CRITERIA (check each):
{criteria_str}

Score on three dimensions:

1. uncertainty_calibration (0.0-1.0): Does the agent express appropriate confidence?
   - 1.0: Confidence matches evidence quality perfectly
   - 0.5: Over-confident or under-confident in places
   - 0.0: Completely miscalibrated (certain about uncertain things or vice versa)

2. evidence_weighing (0.0-1.0): Does the agent properly weight sources?
   - 1.0: High-confidence sources weighted more, low-confidence flagged
   - 0.5: Some sources weighted, but not consistently
   - 0.0: All sources treated equally regardless of reliability

3. hedging_appropriateness (0.0-1.0): Is the hedging language appropriate?
   - 1.0: Appropriate hedging where needed, confident where evidence is strong
   - 0.5: Some hedging but inconsistent
   - 0.0: No hedging despite uncertainty, or excessive hedging about clear facts

Also score each criterion as met (1) or not met (0):
{criteria_str}

Return ONLY a JSON object:
{{"uncertainty_calibration": 0.8, "evidence_weighing": 0.9, "hedging_appropriateness": 0.7, "criteria_met": {{"acknowledges_conflict": 1, ...}}, "reasoning": "Brief explanation"}}"""

    result = _llm_grade(prompt, grader_model)

    scores = {
        "uncertainty_calibration": float(result.get("uncertainty_calibration", 0.0)),
        "evidence_weighing": float(result.get("evidence_weighing", 0.0)),
        "hedging_appropriateness": float(result.get("hedging_appropriateness", 0.0)),
    }
    # Add per-criterion scores
    criteria_met = result.get("criteria_met", {})
    if criteria_met:
        criteria_score = sum(float(v) for v in criteria_met.values()) / len(criteria_met)
        scores["criteria_fulfillment"] = round(criteria_score, 3)

    return ScenarioResult(
        scenario_id=scenario.scenario_id,
        scenario_name=scenario.name,
        agent_response=agent_response,
        scores=scores,
        reasoning=result.get("reasoning", ""),
        metadata={"criteria_met": criteria_met},
    )


# ---------------------------------------------------------------------------
# Cross-Domain Transfer Eval
# ---------------------------------------------------------------------------


def _grade_transfer(
    scenario: TransferScenario,
    agent_response: str,
    grader_model: str | None = None,
) -> ScenarioResult:
    """Grade cross-domain knowledge transfer.

    Metrics:
    - transfer_accuracy: Are the transferred patterns correctly applied?
    - analogy_quality: How well does the agent draw parallels?
    """
    criteria_str = "\n".join(f"  - {c}" for c in scenario.key_criteria)

    prompt = f"""You are evaluating an AI agent's ability to transfer knowledge across domains.

SOURCE DOMAIN KNOWLEDGE (previously learned):
{scenario.source_domain_content}

TARGET DOMAIN QUESTION:
{scenario.target_domain_question}

EXPECTED ANALOGY/TRANSFER:
{scenario.expected_analogy}

AGENT'S RESPONSE:
{agent_response}

EVALUATION CRITERIA:
{criteria_str}

Score on two dimensions:

1. transfer_accuracy (0.0-1.0): Are patterns from the source domain correctly applied?
   - 1.0: All relevant patterns identified and correctly applied to new domain
   - 0.5: Some patterns applied but with errors or missing key ones
   - 0.0: No transfer from source domain apparent

2. analogy_quality (0.0-1.0): How well does the agent draw parallels?
   - 1.0: Clear, specific analogies between source and target domains
   - 0.5: Some analogies present but vague or partially incorrect
   - 0.0: No analogical reasoning visible

Also score each criterion as met (1) or not met (0).

Return ONLY a JSON object:
{{"transfer_accuracy": 0.8, "analogy_quality": 0.7, "criteria_met": {{"applies_defense_in_depth": 1, ...}}, "reasoning": "Brief explanation"}}"""

    result = _llm_grade(prompt, grader_model)

    scores = {
        "transfer_accuracy": float(result.get("transfer_accuracy", 0.0)),
        "analogy_quality": float(result.get("analogy_quality", 0.0)),
    }
    criteria_met = result.get("criteria_met", {})
    if criteria_met:
        criteria_score = sum(float(v) for v in criteria_met.values()) / len(criteria_met)
        scores["criteria_fulfillment"] = round(criteria_score, 3)

    return ScenarioResult(
        scenario_id=scenario.scenario_id,
        scenario_name=scenario.name,
        agent_response=agent_response,
        scores=scores,
        reasoning=result.get("reasoning", ""),
        metadata={"criteria_met": criteria_met},
    )


# ---------------------------------------------------------------------------
# Collaborative Task Eval
# ---------------------------------------------------------------------------


def _grade_collaborative(
    scenario: CollaborativeScenario,
    agent_response: str,
    grader_model: str | None = None,
) -> ScenarioResult:
    """Grade multi-agent collaboration quality.

    Metrics:
    - delegation_quality: Did the agent delegate to the right specialists?
    - synthesis_of_results: Were specialist outputs well-synthesized?
    - coordination_efficiency: Was the coordination well-organized?
    """
    delegations_str = ", ".join(scenario.expected_delegations)
    criteria_str = "\n".join(f"  - {c}" for c in scenario.synthesis_criteria)

    prompt = f"""You are evaluating an AI agent's collaborative task execution.

TASK: {scenario.task}

CONTEXT PROVIDED:
{scenario.context_content}

EXPECTED SPECIALIST DELEGATIONS: {delegations_str}

AGENT'S RESPONSE:
{agent_response}

SYNTHESIS CRITERIA:
{criteria_str}

Score on three dimensions:

1. delegation_quality (0.0-1.0): Did the agent identify the right specialist perspectives?
   - 1.0: All expected specialists addressed, clear separation of concerns
   - 0.5: Some specialists covered, missing key perspectives
   - 0.0: No multi-perspective analysis attempted

2. synthesis_of_results (0.0-1.0): Were findings well-integrated?
   - 1.0: Findings from all perspectives coherently synthesized, conflicts noted
   - 0.5: Findings listed but not integrated
   - 0.0: No synthesis, just raw perspectives

3. coordination_efficiency (0.0-1.0): Was the approach well-organized?
   - 1.0: Clear structure, parallel work where possible, no redundancy
   - 0.5: Some structure but with redundancy or unclear organization
   - 0.0: Chaotic, no organizational structure

Also score each synthesis criterion as met (1) or not met (0).

Return ONLY a JSON object:
{{"delegation_quality": 0.8, "synthesis_of_results": 0.7, "coordination_efficiency": 0.9, "criteria_met": {{"security_findings_present": 1, ...}}, "reasoning": "Brief explanation"}}"""

    result = _llm_grade(prompt, grader_model)

    scores = {
        "delegation_quality": float(result.get("delegation_quality", 0.0)),
        "synthesis_of_results": float(result.get("synthesis_of_results", 0.0)),
        "coordination_efficiency": float(result.get("coordination_efficiency", 0.0)),
    }
    criteria_met = result.get("criteria_met", {})
    if criteria_met:
        criteria_score = sum(float(v) for v in criteria_met.values()) / len(criteria_met)
        scores["criteria_fulfillment"] = round(criteria_score, 3)

    return ScenarioResult(
        scenario_id=scenario.scenario_id,
        scenario_name=scenario.name,
        agent_response=agent_response,
        scores=scores,
        reasoning=result.get("reasoning", ""),
        metadata={"criteria_met": criteria_met},
    )


# ---------------------------------------------------------------------------
# Main evaluation orchestrator
# ---------------------------------------------------------------------------


class GeneralCapabilityEval:
    """Orchestrates general-purpose capability evaluations.

    Creates a LearningAgent, feeds context, runs scenarios, and grades results.

    Args:
        agent_name: Identifier for the agent instance
        sdk: SDK type (mini, claude, copilot, microsoft)
        model: LLM model for the agent
        storage_path: Path for agent memory storage
        grader_model: LLM model for grading (default from env or claude-opus-4-6)
        enable_spawning: Whether to enable multi-agent spawning for collaborative eval
    """

    def __init__(
        self,
        agent_name: str = "capability-eval-agent",
        sdk: str = "mini",
        model: str = "",
        storage_path: Path | None = None,
        grader_model: str | None = None,
        enable_spawning: bool = False,
    ):
        self.agent_name = agent_name
        self.sdk = sdk
        self.model = model
        self.storage_path = storage_path or Path(f"/tmp/cap-eval-{agent_name}")
        self.grader_model = grader_model
        self.enable_spawning = enable_spawning
        self._agent = None

    def _create_agent(self) -> Any:
        """Create a fresh agent instance."""
        if self.sdk == "mini":
            from amplihack.agents.goal_seeking.learning_agent import LearningAgent

            kwargs: dict[str, Any] = {
                "agent_name": self.agent_name,
                "use_hierarchical": True,
                "storage_path": self.storage_path,
            }
            if self.model:
                kwargs["model"] = self.model
            return LearningAgent(**kwargs)
        from amplihack.agents.goal_seeking.sdk_adapters.factory import create_agent

        kwargs = {
            "name": self.agent_name,
            "sdk": self.sdk,
            "storage_path": self.storage_path,
        }
        if self.model:
            kwargs["model"] = self.model
        return create_agent(**kwargs)

    def _learn_content(self, agent: Any, content: str) -> None:
        """Feed content to the agent."""
        if hasattr(agent, "learn_from_content"):
            agent.learn_from_content(content)
        elif hasattr(agent, "run"):
            import asyncio

            asyncio.run(agent.run(f"Learn and remember:\n\n{content}"))

    def _ask_agent(self, agent: Any, question: str) -> tuple[str, ToolTrajectory]:
        """Ask the agent a question and capture the tool trajectory.

        Returns:
            Tuple of (answer_text, tool_trajectory)
        """
        trajectory = ToolTrajectory(task_description=question)

        if hasattr(agent, "answer_question"):
            result = agent.answer_question(question)
            if isinstance(result, tuple):
                answer_text, trace = result
                # Extract tool calls from reasoning trace if available
                if trace and hasattr(trace, "steps"):
                    for step in trace.steps:
                        if step.step_type == "search":
                            for q in step.queries:
                                trajectory.calls.append(
                                    ToolCall(tool_name="search_memory", arguments={"query": q})
                                )
                        elif step.step_type == "calculate":
                            trajectory.calls.append(ToolCall(tool_name="calculate"))
                # Also check trace metadata for explicit tool use
                if trace and hasattr(trace, "metadata"):
                    for tc in trace.metadata.get("tool_calls", []):
                        trajectory.calls.append(
                            ToolCall(
                                tool_name=tc.get("name", "unknown"),
                                arguments=tc.get("arguments", {}),
                            )
                        )
            else:
                answer_text = str(result)
        elif hasattr(agent, "run"):
            import asyncio

            result = asyncio.run(agent.run(question))
            answer_text = str(result.response) if result else ""
        else:
            answer_text = ""

        # If we still have no tool calls, add a synthesize_answer at minimum
        # since the agent must have synthesized to produce an answer
        if answer_text and not trajectory.calls:
            trajectory.calls.append(ToolCall(tool_name="synthesize_answer"))

        return answer_text, trajectory

    def _reset_agent(self, agent: Any) -> None:
        """Close and release agent resources."""
        if hasattr(agent, "close"):
            agent.close()

    # ----- Eval runners per type -----

    def eval_tool_use(self) -> EvalTypeResult:
        """Run tool use efficiency evaluation.

        Tests whether the agent selects the right tools and uses them efficiently.
        """
        start = time.time()
        result = EvalTypeResult(eval_type="tool_use")

        for scenario in TOOL_USE_SCENARIOS:
            logger.info("Running tool use scenario: %s", scenario.name)
            agent = self._create_agent()
            try:
                self._learn_content(agent, scenario.context_content)
                answer, trajectory = self._ask_agent(agent, scenario.task)
                sr = _grade_tool_use(scenario, trajectory, answer)
                result.scenarios.append(sr)
            except Exception as e:
                logger.error("Tool use scenario %s failed: %s", scenario.scenario_id, e)
                result.scenarios.append(
                    ScenarioResult(
                        scenario_id=scenario.scenario_id,
                        scenario_name=scenario.name,
                        agent_response="",
                        scores={
                            "tool_selection_accuracy": 0,
                            "tool_chain_correctness": 0,
                            "call_efficiency": 0,
                        },
                        reasoning=f"Error: {e}",
                    )
                )
            finally:
                self._reset_agent(agent)

        result.duration_s = time.time() - start
        result.compute_averages()
        return result

    def eval_planning(self) -> EvalTypeResult:
        """Run planning evaluation.

        Tests multi-step task decomposition and execution quality.
        """
        start = time.time()
        result = EvalTypeResult(eval_type="planning")

        for scenario in PLANNING_SCENARIOS:
            logger.info("Running planning scenario: %s", scenario.name)
            agent = self._create_agent()
            try:
                self._learn_content(agent, scenario.context_content)
                answer, _ = self._ask_agent(agent, scenario.task)
                sr = _grade_planning(scenario, answer, self.grader_model)
                result.scenarios.append(sr)
            except Exception as e:
                logger.error("Planning scenario %s failed: %s", scenario.scenario_id, e)
                result.scenarios.append(
                    ScenarioResult(
                        scenario_id=scenario.scenario_id,
                        scenario_name=scenario.name,
                        agent_response="",
                        scores={
                            "plan_completeness": 0,
                            "plan_ordering": 0,
                            "plan_execution_success": 0,
                        },
                        reasoning=f"Error: {e}",
                    )
                )
            finally:
                self._reset_agent(agent)

        result.duration_s = time.time() - start
        result.compute_averages()
        return result

    def eval_reasoning_under_uncertainty(self) -> EvalTypeResult:
        """Run reasoning under uncertainty evaluation.

        Tests handling of conflicting/incomplete information.
        """
        start = time.time()
        result = EvalTypeResult(eval_type="reasoning_under_uncertainty")

        for scenario in UNCERTAINTY_SCENARIOS:
            logger.info("Running uncertainty scenario: %s", scenario.name)
            agent = self._create_agent()
            try:
                # Feed each evidence piece separately with its source label
                for ev in scenario.evidence_pieces:
                    content = (
                        f"[Source: {ev['source']}, Confidence: {ev['confidence']}]\n{ev['content']}"
                    )
                    self._learn_content(agent, content)
                answer, _ = self._ask_agent(agent, scenario.question)
                sr = _grade_uncertainty(scenario, answer, self.grader_model)
                result.scenarios.append(sr)
            except Exception as e:
                logger.error("Uncertainty scenario %s failed: %s", scenario.scenario_id, e)
                result.scenarios.append(
                    ScenarioResult(
                        scenario_id=scenario.scenario_id,
                        scenario_name=scenario.name,
                        agent_response="",
                        scores={
                            "uncertainty_calibration": 0,
                            "evidence_weighing": 0,
                            "hedging_appropriateness": 0,
                        },
                        reasoning=f"Error: {e}",
                    )
                )
            finally:
                self._reset_agent(agent)

        result.duration_s = time.time() - start
        result.compute_averages()
        return result

    def eval_cross_domain_transfer(self) -> EvalTypeResult:
        """Run cross-domain transfer evaluation.

        Tests whether knowledge in one domain helps with a different domain.
        """
        start = time.time()
        result = EvalTypeResult(eval_type="cross_domain_transfer")

        for scenario in TRANSFER_SCENARIOS:
            logger.info("Running transfer scenario: %s", scenario.name)
            agent = self._create_agent()
            try:
                # Teach the source domain first
                self._learn_content(agent, scenario.source_domain_content)
                # Ask the target domain question
                answer, _ = self._ask_agent(agent, scenario.target_domain_question)
                sr = _grade_transfer(scenario, answer, self.grader_model)
                result.scenarios.append(sr)
            except Exception as e:
                logger.error("Transfer scenario %s failed: %s", scenario.scenario_id, e)
                result.scenarios.append(
                    ScenarioResult(
                        scenario_id=scenario.scenario_id,
                        scenario_name=scenario.name,
                        agent_response="",
                        scores={"transfer_accuracy": 0, "analogy_quality": 0},
                        reasoning=f"Error: {e}",
                    )
                )
            finally:
                self._reset_agent(agent)

        result.duration_s = time.time() - start
        result.compute_averages()
        return result

    def eval_collaborative(self) -> EvalTypeResult:
        """Run collaborative task evaluation.

        Tests multi-agent delegation and synthesis. Uses the agent's native
        capabilities; multi-agent spawning is tested if the agent supports it.
        """
        start = time.time()
        result = EvalTypeResult(eval_type="collaborative_task")

        for scenario in COLLABORATIVE_SCENARIOS:
            logger.info("Running collaborative scenario: %s", scenario.name)
            agent = self._create_agent()
            try:
                self._learn_content(agent, scenario.context_content)
                # Frame the task to encourage multi-perspective analysis
                prompt = (
                    f"{scenario.task}\n\n"
                    f"Please address this from multiple specialist perspectives "
                    f"({', '.join(scenario.expected_delegations)}) and synthesize "
                    f"the findings into a coherent response."
                )
                answer, _ = self._ask_agent(agent, prompt)
                sr = _grade_collaborative(scenario, answer, self.grader_model)
                result.scenarios.append(sr)
            except Exception as e:
                logger.error("Collaborative scenario %s failed: %s", scenario.scenario_id, e)
                result.scenarios.append(
                    ScenarioResult(
                        scenario_id=scenario.scenario_id,
                        scenario_name=scenario.name,
                        agent_response="",
                        scores={
                            "delegation_quality": 0,
                            "synthesis_of_results": 0,
                            "coordination_efficiency": 0,
                        },
                        reasoning=f"Error: {e}",
                    )
                )
            finally:
                self._reset_agent(agent)

        result.duration_s = time.time() - start
        result.compute_averages()
        return result

    # ----- Main run method -----

    def run(
        self,
        eval_types: list[str] | None = None,
    ) -> CapabilityReport:
        """Run the specified eval types and return a comprehensive report.

        Args:
            eval_types: List of eval types to run. Options:
                'tool_use', 'planning', 'reasoning', 'transfer', 'collaborative', 'all'
                Defaults to ['all'] if None.

        Returns:
            CapabilityReport with results for each eval type
        """
        if eval_types is None:
            eval_types = ["all"]

        all_types = {"tool_use", "planning", "reasoning", "transfer", "collaborative"}
        if "all" in eval_types:
            types_to_run = all_types
        else:
            types_to_run = set(eval_types) & all_types

        if not types_to_run:
            raise ValueError(
                f"No valid eval types in {eval_types}. Choose from: {sorted(all_types)}"
            )

        report = CapabilityReport(
            agent_name=self.agent_name,
            agent_sdk=self.sdk,
            agent_model=self.model or "(default)",
            grader_model=self.grader_model or os.environ.get("GRADER_MODEL", "claude-opus-4-6"),
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

        start = time.time()

        dispatch = {
            "tool_use": self.eval_tool_use,
            "planning": self.eval_planning,
            "reasoning": self.eval_reasoning_under_uncertainty,
            "transfer": self.eval_cross_domain_transfer,
            "collaborative": self.eval_collaborative,
        }

        for eval_type in sorted(types_to_run):
            logger.info("Starting eval: %s", eval_type)
            try:
                result = dispatch[eval_type]()
                report.eval_results.append(result)
                logger.info(
                    "Completed %s: overall=%.2f in %.1fs",
                    eval_type,
                    result.overall_score,
                    result.duration_s,
                )
            except Exception as e:
                logger.error("Eval %s failed entirely: %s", eval_type, e)
                report.eval_results.append(EvalTypeResult(eval_type=eval_type, overall_score=0.0))

        report.total_time_s = time.time() - start
        return report


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def print_report(report: CapabilityReport) -> None:
    """Print a human-readable report to stdout."""
    print("=" * 72)
    print("GENERAL CAPABILITY EVALUATION REPORT")
    print("=" * 72)
    print(f"Agent: {report.agent_name} (SDK: {report.agent_sdk})")
    print(f"Model: {report.agent_model}")
    print(f"Grader: {report.grader_model}")
    print(f"Time: {report.timestamp}")
    print(f"Duration: {report.total_time_s:.1f}s")
    print(f"Overall Score: {report.overall_score:.1%}")
    print("-" * 72)

    for er in report.eval_results:
        print(
            f"\n  [{er.eval_type.upper()}] Overall: {er.overall_score:.1%} ({er.duration_s:.1f}s)"
        )
        if er.metric_averages:
            for metric, val in sorted(er.metric_averages.items()):
                print(f"    {metric}: {val:.1%}")
        for sc in er.scenarios:
            score_str = ", ".join(f"{k}={v:.2f}" for k, v in sc.scores.items())
            print(f"    {sc.scenario_id} ({sc.scenario_name}): {score_str}")
            if sc.reasoning:
                print(f"      Reasoning: {sc.reasoning[:120]}...")

    print("\n" + "=" * 72)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point for general capability evaluation."""
    parser = argparse.ArgumentParser(
        description="General-Purpose Agent Capability Evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m amplihack.eval.general_capability_eval --eval tool_use,planning\n"
            "  python -m amplihack.eval.general_capability_eval --eval all --sdk mini\n"
            "  python -m amplihack.eval.general_capability_eval --eval reasoning --output-dir /tmp/eval\n"
        ),
    )
    parser.add_argument(
        "--eval",
        type=str,
        default="all",
        help="Comma-separated eval types: tool_use, planning, reasoning, transfer, collaborative, all",
    )
    parser.add_argument("--sdk", default="mini", help="Agent SDK: mini, claude, copilot, microsoft")
    parser.add_argument("--model", default="", help="Agent LLM model override")
    parser.add_argument("--grader-model", default="", help="Grader LLM model override")
    parser.add_argument("--agent-name", default="capability-eval", help="Agent name for isolation")
    parser.add_argument(
        "--output-dir", default="./capability_eval_results", help="Output directory"
    )
    parser.add_argument(
        "--enable-spawning", action="store_true", help="Enable multi-agent spawning"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    eval_types = [t.strip() for t in args.eval.split(",")]

    storage_path = Path(args.output_dir) / "agent_storage"
    evaluator = GeneralCapabilityEval(
        agent_name=args.agent_name,
        sdk=args.sdk,
        model=args.model,
        storage_path=storage_path,
        grader_model=args.grader_model or None,
        enable_spawning=args.enable_spawning,
    )

    report = evaluator.run(eval_types=eval_types)

    # Print report
    print_report(report)

    # Save JSON results
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results_file = output_dir / "capability_eval_results.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, indent=2)

    print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    main()
