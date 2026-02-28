#!/usr/bin/env python3
"""Integration evaluation: HiveAwareLearningAgent swarm with cross-domain knowledge.

Creates 3 agents (biology, chemistry, physics) sharing a UnifiedHiveMind.
Each agent learns domain-specific facts (stored directly, no LLM).
Asks cross-domain questions and measures improvement over isolated agents.
Prints a comparison table.

Usage:
    python -m experiments.hive_mind.run_integration_eval
    # or
    python experiments/hive_mind/run_integration_eval.py
"""

from __future__ import annotations

import os
import sys
import time

# Allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from amplihack.agents.goal_seeking.hive_mind.learning_agent_bridge import (
    HiveAwareMemoryAdapter,
    HiveBridgeConfig,
)
from amplihack.agents.goal_seeking.hive_mind.unified import (
    HiveMindConfig,
    UnifiedHiveMind,
)

# ---------------------------------------------------------------------------
# Domain knowledge: 10 facts per agent (no LLM needed)
# ---------------------------------------------------------------------------

BIOLOGY_FACTS = [
    (
        "Biology",
        "DNA is a double helix molecule that stores genetic information",
        0.95,
        ["genetics"],
    ),
    (
        "Biology",
        "Mitochondria are the powerhouses of the cell producing ATP",
        0.93,
        ["cell_biology"],
    ),
    (
        "Biology",
        "Photosynthesis converts carbon dioxide and water into glucose using sunlight",
        0.94,
        ["botany"],
    ),
    (
        "Biology",
        "Enzymes are biological catalysts that speed up chemical reactions",
        0.92,
        ["biochemistry"],
    ),
    ("Biology", "The human genome contains approximately 3 billion base pairs", 0.91, ["genetics"]),
    (
        "Biology",
        "Ribosomes translate mRNA into protein chains via amino acid assembly",
        0.90,
        ["molecular"],
    ),
    (
        "Biology",
        "Natural selection drives evolution by favoring traits that improve survival",
        0.96,
        ["evolution"],
    ),
    (
        "Biology",
        "Neurons transmit electrical signals across synapses using neurotransmitters",
        0.89,
        ["neuroscience"],
    ),
    (
        "Biology",
        "ATP synthase is a molecular motor that generates ATP in mitochondria",
        0.88,
        ["biochemistry"],
    ),
    (
        "Biology",
        "CRISPR-Cas9 allows precise editing of DNA sequences in living organisms",
        0.94,
        ["genetics"],
    ),
]

CHEMISTRY_FACTS = [
    (
        "Chemistry",
        "Water has the molecular formula H2O with a bent molecular geometry",
        0.95,
        ["inorganic"],
    ),
    (
        "Chemistry",
        "The periodic table organizes elements by atomic number and electron configuration",
        0.94,
        ["fundamentals"],
    ),
    ("Chemistry", "Covalent bonds form when atoms share electron pairs", 0.93, ["bonding"]),
    (
        "Chemistry",
        "Catalysts lower the activation energy of chemical reactions without being consumed",
        0.92,
        ["kinetics"],
    ),
    (
        "Chemistry",
        "pH measures the hydrogen ion concentration on a logarithmic scale from 0 to 14",
        0.91,
        ["acids_bases"],
    ),
    (
        "Chemistry",
        "Oxidation-reduction reactions involve the transfer of electrons between species",
        0.90,
        ["redox"],
    ),
    (
        "Chemistry",
        "Le Chatelier's principle predicts how equilibria shift when conditions change",
        0.89,
        ["equilibrium"],
    ),
    (
        "Chemistry",
        "Carbon can form four covalent bonds enabling the diversity of organic molecules",
        0.94,
        ["organic"],
    ),
    (
        "Chemistry",
        "Electronegativity measures an atom's ability to attract shared electrons in a bond",
        0.88,
        ["bonding"],
    ),
    (
        "Chemistry",
        "The Haber process synthesizes ammonia from nitrogen and hydrogen at high pressure",
        0.87,
        ["industrial"],
    ),
]

PHYSICS_FACTS = [
    (
        "Physics",
        "The speed of light in vacuum is approximately 299792458 meters per second",
        0.96,
        ["optics"],
    ),
    (
        "Physics",
        "Newton's second law states F equals ma relating force mass and acceleration",
        0.95,
        ["mechanics"],
    ),
    (
        "Physics",
        "Entropy always increases in an isolated system according to the second law of thermodynamics",
        0.94,
        ["thermodynamics"],
    ),
    (
        "Physics",
        "Quantum entanglement links particles so measuring one instantly affects the other",
        0.92,
        ["quantum"],
    ),
    (
        "Physics",
        "E equals mc squared relates energy to mass times the speed of light squared",
        0.96,
        ["relativity"],
    ),
    (
        "Physics",
        "The Heisenberg uncertainty principle limits simultaneous knowledge of position and momentum",
        0.91,
        ["quantum"],
    ),
    (
        "Physics",
        "Electromagnetic waves include radio microwaves infrared visible UV X-rays and gamma rays",
        0.90,
        ["electromagnetism"],
    ),
    (
        "Physics",
        "Superconductors have zero electrical resistance below a critical temperature",
        0.89,
        ["condensed_matter"],
    ),
    (
        "Physics",
        "The Higgs boson gives particles mass through interaction with the Higgs field",
        0.93,
        ["particle_physics"],
    ),
    (
        "Physics",
        "Gravitational waves are ripples in spacetime caused by accelerating massive objects",
        0.92,
        ["relativity"],
    ),
]

# ---------------------------------------------------------------------------
# Cross-domain questions: answers require knowledge from 2+ agents
# ---------------------------------------------------------------------------

CROSS_DOMAIN_QUESTIONS = [
    {
        "question": "How do biological enzymes relate to chemical catalysts?",
        "expected_keywords": ["enzyme", "catalyst", "activation energy", "reaction"],
        "domains_needed": ["biology", "chemistry"],
    },
    {
        "question": "What role does ATP synthase play and what is its energy source?",
        "expected_keywords": ["ATP", "synthase", "mitochondria"],
        "domains_needed": ["biology"],
    },
    {
        "question": "How does the speed of light relate to E=mc2?",
        "expected_keywords": ["speed", "light", "energy", "mass", "mc2", "299792458"],
        "domains_needed": ["physics"],
    },
    {
        "question": "How does CRISPR editing relate to the structure of DNA?",
        "expected_keywords": ["CRISPR", "DNA", "helix", "edit", "genetic"],
        "domains_needed": ["biology"],
    },
    {
        "question": "What are catalysts in chemistry and biology?",
        "expected_keywords": ["catalyst", "enzyme", "activation", "reaction"],
        "domains_needed": ["biology", "chemistry"],
    },
    {
        "question": "How do covalent bonds relate to carbon's role in organic molecules?",
        "expected_keywords": ["covalent", "carbon", "bond", "organic", "electron"],
        "domains_needed": ["chemistry"],
    },
    {
        "question": "What is the connection between entropy and energy in living systems?",
        "expected_keywords": ["entropy", "energy", "ATP", "thermodynamics"],
        "domains_needed": ["physics", "biology"],
    },
    {
        "question": "How do electromagnetic waves interact with molecular bonds?",
        "expected_keywords": ["electromagnetic", "bond", "electron", "wave"],
        "domains_needed": ["physics", "chemistry"],
    },
]


# ---------------------------------------------------------------------------
# Evaluation helpers (no LLM -- pure keyword matching)
# ---------------------------------------------------------------------------


class FakeMemoryAdapter:
    """Minimal in-memory adapter for evaluation without database dependencies."""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self._facts: list[dict] = []
        self._id_counter = 0

    def store_fact(
        self,
        context: str,
        fact: str,
        confidence: float = 0.9,
        tags: list[str] | None = None,
        **kwargs,
    ) -> str:
        self._id_counter += 1
        fact_id = f"eval_{self.agent_name}_{self._id_counter}"
        self._facts.append(
            {
                "experience_id": fact_id,
                "context": context,
                "outcome": fact,
                "confidence": confidence,
                "tags": tags or [],
                "timestamp": "",
                "metadata": {},
            }
        )
        return fact_id

    def search(self, query: str, limit: int = 10, **kwargs) -> list[dict]:
        q_lower = query.lower()
        q_words = set(q_lower.split())
        scored = []
        for f in self._facts:
            text = f"{f['context']} {f['outcome']}".lower()
            # Score by word overlap
            score = sum(1 for w in q_words if w in text)
            if score > 0:
                scored.append((score, f))
        scored.sort(key=lambda x: -x[0])
        return [f for _, f in scored[:limit]]

    def get_all_facts(self, limit: int = 50) -> list[dict]:
        return self._facts[:limit]


def keyword_score(results: list[dict], expected_keywords: list[str]) -> float:
    """Score results by how many expected keywords appear in the combined text.

    Returns:
        Fraction of expected keywords found (0.0 to 1.0).
    """
    if not expected_keywords:
        return 1.0

    all_text = " ".join(
        f"{r.get('context', '')} {r.get('outcome', r.get('content', ''))}" for r in results
    ).lower()

    found = sum(1 for kw in expected_keywords if kw.lower() in all_text)
    return found / len(expected_keywords)


# ---------------------------------------------------------------------------
# Main evaluation
# ---------------------------------------------------------------------------


def run_evaluation() -> None:
    """Run the full integration evaluation."""

    print("=" * 70)
    print("  Hive Mind Integration Evaluation: LearningAgent Bridge")
    print("=" * 70)
    print()

    # --- Phase 1: Create isolated agents (baseline) ---
    print("Phase 1: Creating isolated agents (no hive) ...")
    isolated_agents: dict[str, FakeMemoryAdapter] = {}
    for name in ["biology", "chemistry", "physics"]:
        isolated_agents[name] = FakeMemoryAdapter(name)

    for context, fact, conf, tags in BIOLOGY_FACTS:
        isolated_agents["biology"].store_fact(context, fact, conf, tags)
    for context, fact, conf, tags in CHEMISTRY_FACTS:
        isolated_agents["chemistry"].store_fact(context, fact, conf, tags)
    for context, fact, conf, tags in PHYSICS_FACTS:
        isolated_agents["physics"].store_fact(context, fact, conf, tags)

    print(f"  Biology:   {len(isolated_agents['biology']._facts)} facts")
    print(f"  Chemistry: {len(isolated_agents['chemistry']._facts)} facts")
    print(f"  Physics:   {len(isolated_agents['physics']._facts)} facts")
    print()

    # --- Phase 2: Create hive-connected agents ---
    print("Phase 2: Creating hive-connected agents ...")
    hive = UnifiedHiveMind(
        config=HiveMindConfig(
            promotion_consensus_required=1,
            promotion_confidence_threshold=0.3,
            gossip_interval_rounds=3,
            enable_gossip=True,
            enable_events=True,
        )
    )

    bridge_config = HiveBridgeConfig(
        auto_promote=True,
        promote_confidence_threshold=0.5,
        hive_query_limit=30,
    )

    hive_agents: dict[str, HiveAwareMemoryAdapter] = {}
    hive_memories: dict[str, FakeMemoryAdapter] = {}
    for name in ["biology", "chemistry", "physics"]:
        hive.register_agent(name)
        mem = FakeMemoryAdapter(name)
        hive_memories[name] = mem
        hive_agents[name] = HiveAwareMemoryAdapter(
            wrapped=mem,
            hive=hive,
            agent_id=name,
            bridge_config=bridge_config,
        )

    # Store facts through hive-aware adapters
    t_start = time.time()
    for context, fact, conf, tags in BIOLOGY_FACTS:
        hive_agents["biology"].store_fact(context, fact, conf, tags)
    for context, fact, conf, tags in CHEMISTRY_FACTS:
        hive_agents["chemistry"].store_fact(context, fact, conf, tags)
    for context, fact, conf, tags in PHYSICS_FACTS:
        hive_agents["physics"].store_fact(context, fact, conf, tags)
    t_store = time.time() - t_start

    print(f"  Stored 30 facts in {t_store:.3f}s")

    # Run gossip + event processing
    hive.run_gossip_round()
    events = hive.process_events()
    total_events = sum(events.values())
    print(f"  Gossip round complete, {total_events} events processed")

    stats = hive.get_stats()
    print(f"  Hive stats: {stats['graph']['hive_facts']} hive facts, {stats['agent_count']} agents")
    print()

    # --- Phase 3: Evaluate cross-domain questions ---
    print("Phase 3: Cross-domain question evaluation")
    print("-" * 70)

    isolated_scores: list[float] = []
    hive_scores: list[float] = []
    results_table: list[dict] = []

    for q_info in CROSS_DOMAIN_QUESTIONS:
        question = q_info["question"]
        expected = q_info["expected_keywords"]
        domains = q_info["domains_needed"]

        # Isolated: Each agent searches independently, combine best results
        # This simulates an agent that only has its own domain knowledge
        best_isolated_score = 0.0
        for domain, adapter in isolated_agents.items():
            results = adapter.search(question, limit=20)
            score = keyword_score(results, expected)
            best_isolated_score = max(best_isolated_score, score)
        isolated_scores.append(best_isolated_score)

        # Hive: Each agent searches with hive augmentation
        best_hive_score = 0.0
        for domain, adapter in hive_agents.items():
            results = adapter.search(question, limit=20)
            score = keyword_score(results, expected)
            best_hive_score = max(best_hive_score, score)
        hive_scores.append(best_hive_score)

        improvement = best_hive_score - best_isolated_score
        results_table.append(
            {
                "question": question[:55],
                "domains": ", ".join(domains),
                "isolated": best_isolated_score,
                "hive": best_hive_score,
                "improvement": improvement,
            }
        )

    # --- Phase 4: Print results ---
    print()
    print(f"{'Question':<57} {'Domains':<15} {'Isolated':>8} {'Hive':>8} {'Delta':>8}")
    print("-" * 98)

    for row in results_table:
        delta_str = (
            f"+{row['improvement']:.0%}" if row["improvement"] > 0 else f"{row['improvement']:.0%}"
        )
        print(
            f"{row['question']:<57} "
            f"{row['domains']:<15} "
            f"{row['isolated']:>7.0%} "
            f"{row['hive']:>7.0%} "
            f"{delta_str:>8}"
        )

    print("-" * 98)

    avg_isolated = sum(isolated_scores) / len(isolated_scores) if isolated_scores else 0
    avg_hive = sum(hive_scores) / len(hive_scores) if hive_scores else 0
    avg_improvement = avg_hive - avg_isolated

    delta_str = f"+{avg_improvement:.0%}" if avg_improvement > 0 else f"{avg_improvement:.0%}"
    print(f"{'AVERAGE':<57} {'':<15} {avg_isolated:>7.0%} {avg_hive:>7.0%} {delta_str:>8}")

    print()
    print("=" * 70)
    print(f"  Isolated average: {avg_isolated:.1%}")
    print(f"  Hive average:     {avg_hive:.1%}")
    print(f"  Improvement:      {avg_improvement:+.1%}")
    print(
        f"  Questions with improvement: "
        f"{sum(1 for r in results_table if r['improvement'] > 0)}/{len(results_table)}"
    )
    print("=" * 70)

    # --- Phase 5: Agent knowledge summary ---
    print()
    print("Agent Knowledge Summary:")
    print("-" * 50)
    for name in ["biology", "chemistry", "physics"]:
        summary = hive.get_agent_knowledge_summary(name)
        print(
            f"  {name:12} | local: {summary['local_facts']:>3} | "
            f"hive: {summary['hive_facts_available']:>3} | "
            f"gossip recv: {summary['gossip_facts_received']:>3}"
        )


if __name__ == "__main__":
    run_evaluation()
