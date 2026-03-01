#!/usr/bin/env python3
"""20-agent distributed hive mind evaluation.

Each agent has its OWN independent Kuzu database. The hive mind is a
coordination protocol (event bus + coordinator), NOT a shared database.

Evaluation phases:
    Phase 1: Each agent learns 15 domain-specific facts into its own DB
    Phase 2: Events propagate through the bus (5 rounds)
    Phase 3: Query each agent -- they should have own + incorporated peer facts
    Phase 4: Score cross-domain queries

Compares: ISOLATED (no hive) vs DISTRIBUTED (event-based sharing)
"""

from __future__ import annotations

import os
import sys
import tempfile
import time

# Ensure amplihack-memory-lib is importable
_MEMORY_LIB_PATH = "/home/azureuser/src/amplihack-memory-lib-real/src"
if _MEMORY_LIB_PATH not in sys.path:
    sys.path.insert(0, _MEMORY_LIB_PATH)

# Ensure amplihack5 src is importable
_SRC_PATH = "/home/azureuser/src/amplihack5/src"
if _SRC_PATH not in sys.path:
    sys.path.insert(0, _SRC_PATH)

from amplihack.agents.goal_seeking.hive_mind.distributed import (
    AgentNode,
    DistributedHiveMind,
)

# ---------------------------------------------------------------------------
# Domain knowledge: 10 domains x 2 agents = 20 agents, 15 facts each
# ---------------------------------------------------------------------------

DOMAINS = {
    "biology": [
        "DNA stores genetic information in a double helix structure",
        "Mitochondria are the powerhouse of the cell",
        "Photosynthesis converts sunlight into chemical energy",
        "Proteins are made of amino acid chains",
        "RNA carries genetic instructions from DNA to ribosomes",
        "Cells are the basic structural unit of all living organisms",
        "ATP is the primary energy currency of cells",
        "Enzymes are biological catalysts that speed up reactions",
        "The human genome contains about 3 billion base pairs",
        "Meiosis produces four haploid cells from one diploid cell",
        "Chloroplasts contain chlorophyll for photosynthesis",
        "The cell membrane is a phospholipid bilayer",
        "Mitosis produces two identical daughter cells",
        "Bacteria can reproduce through binary fission",
        "Antibodies are proteins produced by the immune system",
    ],
    "chemistry": [
        "Water molecule H2O has a bent molecular geometry",
        "The periodic table organizes elements by atomic number",
        "Covalent bonds share electrons between atoms",
        "pH measures the hydrogen ion concentration in a solution",
        "NaCl is common table salt with ionic bonding",
        "Avogadro number is approximately 6.022 times 10 to the 23rd",
        "Oxidation involves loss of electrons",
        "Carbon forms four covalent bonds in organic chemistry",
        "Acids donate protons while bases accept protons",
        "Entropy measures the disorder of a system",
        "Catalysts lower the activation energy of reactions",
        "The mole is a unit measuring 6.022e23 particles",
        "Electronegativity increases across a period left to right",
        "Noble gases have full outer electron shells",
        "Redox reactions involve transfer of electrons",
    ],
    "physics": [
        "E equals mc squared relates energy and mass",
        "The speed of light in vacuum is 299792458 meters per second",
        "Newton first law states objects at rest stay at rest",
        "Gravity is 9.81 m/s squared on Earth surface",
        "Quantum mechanics describes behavior at atomic scales",
        "Electromagnetic waves travel at the speed of light",
        "Entropy always increases in an isolated system",
        "The Heisenberg uncertainty principle limits measurement precision",
        "Protons and neutrons are made of quarks",
        "Photons are massless particles of light",
        "Nuclear fission splits heavy atoms releasing energy",
        "Superconductors have zero electrical resistance below critical temp",
        "Dark matter makes up about 27 percent of the universe",
        "String theory proposes one-dimensional vibrating strings",
        "The Higgs boson gives particles their mass",
    ],
    "mathematics": [
        "Pi is approximately 3.14159265358979",
        "The Pythagorean theorem states a2 plus b2 equals c2",
        "Euler number e is approximately 2.71828",
        "Prime numbers are divisible only by 1 and themselves",
        "The derivative measures rate of change of a function",
        "Integration finds the area under a curve",
        "Fibonacci sequence: each number is sum of two preceding",
        "Set theory is the foundation of modern mathematics",
        "Complex numbers include a real and imaginary part",
        "Matrix multiplication is not commutative",
        "The golden ratio phi is approximately 1.618",
        "Infinity is not a number but a concept of unboundedness",
        "Bayes theorem updates probability based on new evidence",
        "The Riemann hypothesis concerns zeros of the zeta function",
        "Topology studies properties preserved under deformation",
    ],
    "history": [
        "The Roman Empire fell in 476 AD",
        "The French Revolution began in 1789",
        "World War 2 lasted from 1939 to 1945",
        "The printing press was invented by Gutenberg around 1440",
        "The Renaissance began in Italy in the 14th century",
        "The Industrial Revolution started in Britain in the 1760s",
        "The Declaration of Independence was signed in 1776",
        "Ancient Egypt built the Great Pyramids around 2580 BC",
        "The Byzantine Empire lasted until 1453 AD",
        "The Silk Road connected China to the Mediterranean",
        "The Black Death killed about a third of Europe population",
        "Mesopotamia is considered the cradle of civilization",
        "The Magna Carta was signed in 1215",
        "The Cold War lasted from 1947 to 1991",
        "The Moon landing happened on July 20 1969",
    ],
    "geography": [
        "Mount Everest is the tallest mountain at 8849 meters",
        "The Pacific Ocean is the largest ocean on Earth",
        "The Amazon River is the second longest river in the world",
        "The Sahara Desert is the largest hot desert",
        "Antarctica is the coldest continent on Earth",
        "The Mariana Trench is the deepest point in the ocean",
        "The Great Barrier Reef is the largest coral reef system",
        "The Nile River flows through 11 African countries",
        "Russia is the largest country by land area",
        "The Dead Sea is the lowest point on land at 430m below sea level",
        "The Ring of Fire circles the Pacific Ocean with volcanoes",
        "The Grand Canyon is 446 km long and up to 1800m deep",
        "Lake Baikal in Russia is the deepest freshwater lake",
        "The Himalayas are still growing about 1cm per year",
        "Iceland sits on the Mid-Atlantic Ridge",
    ],
    "computer_science": [
        "Binary uses only 0 and 1 to represent data",
        "TCP IP is the fundamental protocol of the internet",
        "Big O notation describes algorithm time complexity",
        "Hash tables provide O(1) average lookup time",
        "SQL is used to query relational databases",
        "Object-oriented programming uses classes and objects",
        "Recursion is when a function calls itself",
        "The Turing machine is a theoretical model of computation",
        "HTTP is the protocol for web communication",
        "Machine learning finds patterns in data without explicit programming",
        "Encryption converts plaintext to ciphertext for security",
        "Git is a distributed version control system",
        "Linked lists store elements with pointers to next nodes",
        "The halting problem is undecidable by Turing machines",
        "Moore Law predicts transistor density doubles roughly every 2 years",
    ],
    "medicine": [
        "Penicillin was the first widely used antibiotic",
        "The heart pumps about 5 liters of blood per minute",
        "Insulin regulates blood sugar levels in the body",
        "Vaccines stimulate the immune system to build resistance",
        "Red blood cells carry oxygen using hemoglobin",
        "The human brain has approximately 86 billion neurons",
        "DNA mutations can cause genetic disorders",
        "Blood pressure is measured as systolic over diastolic",
        "White blood cells fight infections in the body",
        "The liver is the largest internal organ",
        "Aspirin inhibits cyclooxygenase reducing inflammation",
        "MRI uses magnetic fields to image body structures",
        "Cholesterol is transported by LDL and HDL lipoproteins",
        "The human body has 206 bones in adulthood",
        "Antibiotics do not work against viral infections",
    ],
    "astronomy": [
        "The Sun is a G-type main sequence star",
        "Jupiter is the largest planet in our solar system",
        "Light from the Sun takes about 8 minutes to reach Earth",
        "The Milky Way contains roughly 100 billion stars",
        "Black holes have gravity so strong light cannot escape",
        "Mars has the largest volcano Olympus Mons",
        "Saturn rings are made mostly of ice particles",
        "The universe is approximately 13.8 billion years old",
        "Neutron stars are incredibly dense collapsed star cores",
        "The cosmic microwave background is radiation from the early universe",
        "Pluto was reclassified as a dwarf planet in 2006",
        "Venus rotates backwards compared to most planets",
        "The Andromeda galaxy will merge with Milky Way in 4.5 billion years",
        "Pulsars are rotating neutron stars emitting beams of radiation",
        "Exoplanets orbit stars outside our solar system",
    ],
    "economics": [
        "Supply and demand determine market prices",
        "GDP measures the total value of goods and services produced",
        "Inflation is the general increase in prices over time",
        "The Federal Reserve controls US monetary policy",
        "Compound interest means earning interest on interest",
        "Opportunity cost is the value of the next best alternative",
        "Adam Smith wrote The Wealth of Nations in 1776",
        "Monopolies exist when one firm dominates a market",
        "The stock market allows buying and selling company shares",
        "Trade deficits occur when imports exceed exports",
        "Keynesian economics advocates government spending in recessions",
        "Marginal utility decreases as consumption increases",
        "Central banks use interest rates to control money supply",
        "Fiscal policy involves government taxation and spending",
        "The law of diminishing returns applies to additional input",
    ],
}


# Cross-domain queries for scoring
CROSS_DOMAIN_QUERIES = [
    ("biology", "What molecule stores genetic information", "DNA"),
    ("chemistry", "What is the formula for water", "H2O"),
    ("physics", "What is the speed of light", "299792"),
    ("mathematics", "What is the value of Pi", "3.14"),
    ("history", "When did the Roman Empire fall", "476"),
    ("geography", "What is the tallest mountain", "Everest"),
    ("computer_science", "What notation describes algorithm complexity", "Big O"),
    ("medicine", "What was the first antibiotic", "Penicillin"),
    ("astronomy", "What is the largest planet", "Jupiter"),
    ("economics", "What determines market prices", "Supply"),
]


def run_isolated_eval(base_dir: str) -> dict:
    """Run evaluation with isolated agents (no hive communication)."""
    print("\n" + "=" * 60)
    print("PHASE: ISOLATED EVALUATION (no hive)")
    print("=" * 60)

    agents: dict[str, AgentNode] = {}
    domain_list = list(DOMAINS.keys())

    # Create 20 agents (2 per domain), each with own DB, NO hive
    for i, domain in enumerate(domain_list):
        for j in range(2):
            agent_id = f"{domain}_agent_{j}"
            agent_dir = os.path.join(base_dir, "isolated", agent_id, "kuzu_db")
            agent = AgentNode(agent_id, agent_dir, domain=domain)
            # Learn 15 domain facts
            for fact in DOMAINS[domain]:
                agent.learn(domain, fact, confidence=0.85 + (j * 0.05))
            agents[agent_id] = agent
            print(f"  Created isolated agent {agent_id}: {agent.get_fact_count()} facts")

    # Score cross-domain queries
    correct = 0
    total = 0
    for query_domain, query_text, expected_substr in CROSS_DOMAIN_QUERIES:
        for agent_id, agent in agents.items():
            if agent.domain != query_domain:
                total += 1
                results = agent.query(query_text, limit=5)
                if any(expected_substr in r["content"] for r in results):
                    correct += 1

    score = correct / total * 100 if total > 0 else 0
    print(f"\n  ISOLATED score: {correct}/{total} = {score:.1f}%")
    return {"correct": correct, "total": total, "score": score}


def run_distributed_eval(base_dir: str) -> dict:
    """Run evaluation with distributed hive (event-based sharing)."""
    print("\n" + "=" * 60)
    print("PHASE: DISTRIBUTED EVALUATION (event-based hive)")
    print("=" * 60)

    hive = DistributedHiveMind(base_dir=os.path.join(base_dir, "distributed"))
    domain_list = list(DOMAINS.keys())

    # Phase 1: Create 20 agents, then each learns 15 facts
    # Create all agents FIRST so all are subscribed before any learning begins.
    # This ensures every agent receives every peer's events.
    print("\n  Phase 1a: Agent creation (all agents subscribe first)")
    t_start = time.time()
    agent_ids_in_order = []
    for i, domain in enumerate(domain_list):
        for j in range(2):
            agent_id = f"{domain}_agent_{j}"
            hive.create_agent(agent_id, domain=domain)
            agent_ids_in_order.append((agent_id, domain))
            print(f"    Created {agent_id} (domain={domain})")

    print("\n  Phase 1b: Learning (all agents learn their domain facts)")
    for agent_id, domain in agent_ids_in_order:
        agent = hive.get_agent(agent_id)
        j = 0 if agent_id.endswith("_0") else 1
        for fact in DOMAINS[domain]:
            agent.learn(domain, fact, confidence=0.85 + (j * 0.05))
        print(f"    {agent_id}: {agent.get_fact_count()} local facts")
    t_phase1 = time.time() - t_start
    print(f"  Phase 1 complete in {t_phase1:.1f}s")

    # Phase 2: Propagate events (5 rounds)
    print("\n  Phase 2: Event propagation (5 rounds)")
    t_start = time.time()
    total_incorporated = 0
    for round_num in range(5):
        results = hive.propagate()
        round_total = sum(results.values())
        total_incorporated += round_total
        if round_total > 0:
            print(f"    Round {round_num + 1}: {round_total} facts incorporated")
        else:
            print(f"    Round {round_num + 1}: no new facts (converged)")
            break
    t_phase2 = time.time() - t_start
    print(f"  Phase 2 complete in {t_phase2:.1f}s ({total_incorporated} total incorporated)")

    # Phase 3: Report each agent's DB contents
    print("\n  Phase 3: Agent database contents")
    for agent_id in sorted(hive._agents.keys()):
        agent = hive._agents[agent_id]
        count = agent.get_fact_count()
        all_facts = agent.get_all_facts(limit=500)
        own_facts = [f for f in all_facts if not any("from:" in t for t in f["tags"])]
        peer_facts = [f for f in all_facts if any("from:" in t for t in f["tags"])]
        print(f"    {agent_id}: {count} total ({len(own_facts)} own, {len(peer_facts)} peer)")

    # Phase 4: Score cross-domain queries
    print("\n  Phase 4: Cross-domain query scoring")
    correct = 0
    total = 0
    for query_domain, query_text, expected_substr in CROSS_DOMAIN_QUERIES:
        for agent_id, agent in hive._agents.items():
            if agent.domain != query_domain:
                total += 1
                results = agent.query(query_text, limit=5)
                found = any(expected_substr in r["content"] for r in results)
                if found:
                    correct += 1

    score = correct / total * 100 if total > 0 else 0
    print(f"\n  DISTRIBUTED score: {correct}/{total} = {score:.1f}%")

    # Also test routed queries
    print("\n  Phase 4b: Routed query scoring")
    routed_correct = 0
    routed_total = 0
    for query_domain, query_text, expected_substr in CROSS_DOMAIN_QUERIES:
        routed_total += 1
        # Ask a non-expert agent
        asking = None
        for aid, a in hive._agents.items():
            if a.domain != query_domain:
                asking = aid
                break
        if asking:
            results = hive.query_routed(asking, query_text, limit=5)
            if any(expected_substr in r["content"] for r in results):
                routed_correct += 1
    routed_score = routed_correct / routed_total * 100 if routed_total > 0 else 0
    print(f"  ROUTED score: {routed_correct}/{routed_total} = {routed_score:.1f}%")

    hive_stats = hive.get_stats()
    hive.close()

    return {
        "correct": correct,
        "total": total,
        "score": score,
        "routed_correct": routed_correct,
        "routed_total": routed_total,
        "routed_score": routed_score,
        "total_incorporated": total_incorporated,
        "phase1_time": t_phase1,
        "phase2_time": t_phase2,
        "hive_stats": hive_stats,
    }


def main() -> None:
    """Run the full 20-agent distributed hive mind evaluation."""
    print("=" * 60)
    print("DISTRIBUTED HIVE MIND EVALUATION")
    print("20 agents, 10 domains x 2 agents each")
    print("Each agent has its OWN independent Kuzu database")
    print("=" * 60)

    with tempfile.TemporaryDirectory(prefix="hive_eval_") as base_dir:
        # Run isolated (baseline)
        t0 = time.time()
        isolated = run_isolated_eval(base_dir)
        t_isolated = time.time() - t0

        # Run distributed (event-based sharing)
        t0 = time.time()
        distributed = run_distributed_eval(base_dir)
        t_distributed = time.time() - t0

        # Final comparison
        print("\n" + "=" * 60)
        print("FINAL COMPARISON")
        print("=" * 60)
        print(f"  {'Metric':<35} {'ISOLATED':>10} {'DISTRIBUTED':>12}")
        print(f"  {'-' * 35} {'-' * 10} {'-' * 12}")
        print(
            f"  {'Cross-domain accuracy':<35} {isolated['score']:>9.1f}% {distributed['score']:>11.1f}%"
        )
        print(f"  {'Correct answers':<35} {isolated['correct']:>10} {distributed['correct']:>12}")
        print(f"  {'Total queries':<35} {isolated['total']:>10} {distributed['total']:>12}")
        print(f"  {'Routed query accuracy':<35} {'N/A':>10} {distributed['routed_score']:>11.1f}%")
        print(
            f"  {'Facts incorporated via events':<35} {'0':>10} {distributed['total_incorporated']:>12}"
        )
        print(f"  {'Total time (seconds)':<35} {t_isolated:>10.1f} {t_distributed:>12.1f}")

        improvement = distributed["score"] - isolated["score"]
        print(f"\n  Improvement: {improvement:+.1f} percentage points")
        print("  Architecture: Each agent owns its OWN Kuzu database")
        print("  Communication: Event bus (LocalEventBus)")
        print("  Coordination: Lightweight in-memory HiveCoordinator")


if __name__ == "__main__":
    main()
