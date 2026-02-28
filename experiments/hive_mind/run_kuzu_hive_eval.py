#!/usr/bin/env python3
"""Kuzu Hive Mind Evaluation: 5 domain agents + 1 adversarial, real Kuzu DB.

Each domain agent learns 20 facts, promotes its top 10, then we score
cross-domain queries in three modes:
    1. Isolated: each agent queries only local memory
    2. Hive: each agent queries via query_hive (promoted facts only)
    3. Combined: each agent queries via query_all (local + hive, deduplicated)

The adversarial agent stores wrong facts and tries to promote them (should be
blocked after trust is tanked).

Usage:
    python experiments/hive_mind/run_kuzu_hive_eval.py
"""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

# Ensure amplihack-memory-lib is importable
_MEMORY_LIB_PATH = "/home/azureuser/src/amplihack-memory-lib-real/src"
if _MEMORY_LIB_PATH not in sys.path:
    sys.path.insert(0, _MEMORY_LIB_PATH)

# Ensure amplihack package is importable
_SRC_PATH = "/home/azureuser/src/amplihack5/src"
if _SRC_PATH not in sys.path:
    sys.path.insert(0, _SRC_PATH)

from amplihack.agents.goal_seeking.hive_mind.kuzu_hive import KuzuHiveMind

# ---------------------------------------------------------------------------
# Domain fact corpora
# ---------------------------------------------------------------------------

DOMAIN_FACTS: dict[str, list[tuple[str, str, float]]] = {
    "biology": [
        ("cells", "Cells are the fundamental units of life", 0.95),
        ("cells", "Prokaryotic cells lack a nucleus", 0.90),
        ("cells", "Eukaryotic cells contain organelles", 0.92),
        ("dna", "DNA stores genetic information as nucleotide sequences", 0.97),
        ("dna", "DNA replication is semi-conservative", 0.93),
        ("dna", "The human genome contains about 3 billion base pairs", 0.94),
        ("proteins", "Proteins are chains of amino acids", 0.96),
        ("proteins", "Enzymes are biological catalysts made of protein", 0.91),
        ("photosynthesis", "Photosynthesis converts CO2 and water to glucose", 0.95),
        ("photosynthesis", "Chlorophyll absorbs red and blue light", 0.88),
        ("evolution", "Natural selection drives adaptation over generations", 0.94),
        ("evolution", "Mutations introduce genetic variation", 0.90),
        ("ecology", "Ecosystems consist of biotic and abiotic components", 0.89),
        ("ecology", "Trophic levels describe energy flow in food chains", 0.87),
        ("genetics", "Mendel discovered dominant and recessive traits", 0.93),
        ("genetics", "Genes are segments of DNA encoding proteins", 0.95),
        ("anatomy", "The human body has 206 bones in adulthood", 0.96),
        ("anatomy", "Red blood cells carry oxygen via hemoglobin", 0.94),
        ("microbiology", "Bacteria reproduce by binary fission", 0.91),
        ("microbiology", "Viruses require host cells to replicate", 0.93),
    ],
    "chemistry": [
        ("atoms", "Atoms consist of protons, neutrons, and electrons", 0.97),
        ("atoms", "The atomic number equals the number of protons", 0.96),
        ("bonds", "Covalent bonds share electron pairs between atoms", 0.94),
        ("bonds", "Ionic bonds form between oppositely charged ions", 0.93),
        ("bonds", "Hydrogen bonds are weak intermolecular forces", 0.91),
        ("water", "Water molecule is H2O with bent geometry", 0.98),
        ("water", "Water has a high specific heat capacity", 0.90),
        ("water", "Water is a universal solvent for polar substances", 0.89),
        ("acids", "Acids donate protons according to Bronsted-Lowry theory", 0.92),
        ("acids", "pH measures hydrogen ion concentration on a log scale", 0.95),
        ("reactions", "Chemical equations must be balanced", 0.96),
        ("reactions", "Catalysts lower activation energy without being consumed", 0.94),
        ("organic", "Carbon forms four covalent bonds", 0.97),
        ("organic", "Organic chemistry studies carbon-containing compounds", 0.93),
        ("periodic", "Elements are arranged by atomic number in the periodic table", 0.97),
        ("periodic", "Noble gases have full electron shells", 0.94),
        ("thermodynamics", "Enthalpy change measures heat of reaction", 0.90),
        ("thermodynamics", "Entropy increases in spontaneous processes", 0.92),
        ("electrochemistry", "Redox reactions involve electron transfer", 0.93),
        ("electrochemistry", "Galvanic cells convert chemical to electrical energy", 0.91),
    ],
    "physics": [
        ("mechanics", "Newton's first law states objects at rest stay at rest", 0.97),
        ("mechanics", "F equals ma is Newton's second law", 0.98),
        ("mechanics", "Every action has an equal and opposite reaction", 0.97),
        ("energy", "Energy is conserved in a closed system", 0.99),
        ("energy", "Kinetic energy equals half mv squared", 0.96),
        ("energy", "Potential energy depends on position in a force field", 0.94),
        ("waves", "Light travels at 299792 km/s in vacuum", 0.99),
        ("waves", "Sound travels faster in solids than in gases", 0.92),
        ("waves", "Electromagnetic waves do not require a medium", 0.95),
        ("relativity", "E equals mc squared relates mass and energy", 0.99),
        ("relativity", "Time dilates at velocities approaching light speed", 0.96),
        ("quantum", "Heisenberg uncertainty limits simultaneous measurement precision", 0.94),
        ("quantum", "Wave-particle duality applies to all quantum objects", 0.93),
        ("thermo", "Absolute zero is 0 Kelvin or minus 273.15 Celsius", 0.97),
        ("thermo", "Heat flows from hot to cold spontaneously", 0.96),
        ("gravity", "Gravitational force is proportional to mass product", 0.97),
        ("gravity", "Earth surface gravity is approximately 9.81 m/s^2", 0.98),
        ("electricity", "Current equals voltage divided by resistance (Ohm's law)", 0.96),
        ("electricity", "Electric charge is quantized in units of electron charge", 0.94),
        ("magnetism", "Moving charges create magnetic fields", 0.95),
    ],
    "mathematics": [
        ("algebra", "Quadratic formula solves ax^2 + bx + c = 0", 0.97),
        ("algebra", "The distributive property links multiplication and addition", 0.95),
        ("calculus", "Derivatives measure instantaneous rate of change", 0.98),
        ("calculus", "Integrals compute area under curves", 0.97),
        ("calculus", "Fundamental theorem of calculus links derivatives and integrals", 0.99),
        ("geometry", "Pi is the ratio of circumference to diameter", 0.99),
        ("geometry", "Pythagorean theorem: a^2 + b^2 = c^2", 0.99),
        ("geometry", "Area of a circle is pi times radius squared", 0.98),
        ("statistics", "Mean is the sum of values divided by count", 0.97),
        ("statistics", "Standard deviation measures spread around the mean", 0.95),
        ("statistics", "Normal distribution is symmetric about the mean", 0.94),
        ("number_theory", "Every integer greater than 1 has a prime factorization", 0.98),
        ("number_theory", "There are infinitely many prime numbers", 0.99),
        ("logic", "Modus ponens: if P then Q, P, therefore Q", 0.97),
        ("logic", "De Morgan's laws relate AND and OR with NOT", 0.95),
        ("sets", "The empty set is a subset of every set", 0.98),
        ("sets", "Union combines elements of two sets", 0.96),
        ("linear_algebra", "Matrices represent linear transformations", 0.95),
        ("linear_algebra", "Eigenvalues indicate scaling factors of eigenvectors", 0.93),
        ("topology", "A Mobius strip has only one surface and one edge", 0.92),
    ],
    "computer_science": [
        ("algorithms", "Binary search runs in O(log n) time", 0.97),
        ("algorithms", "Quicksort average case is O(n log n)", 0.95),
        ("algorithms", "Dijkstra's algorithm finds shortest paths in weighted graphs", 0.96),
        ("data_structures", "Hash tables provide O(1) average lookup time", 0.96),
        ("data_structures", "Balanced BSTs guarantee O(log n) operations", 0.94),
        ("data_structures", "Linked lists allow O(1) insertion at head", 0.95),
        ("complexity", "P vs NP asks if verification implies efficient solution", 0.97),
        ("complexity", "NP-complete problems reduce to each other", 0.94),
        ("databases", "SQL is the standard language for relational databases", 0.96),
        ("databases", "ACID properties ensure transaction reliability", 0.95),
        ("databases", "Graph databases store relationships as first-class citizens", 0.93),
        ("networking", "TCP ensures reliable ordered delivery of packets", 0.95),
        ("networking", "HTTP is stateless request-response protocol", 0.94),
        ("os", "Process scheduling allocates CPU time to competing processes", 0.93),
        ("os", "Virtual memory maps logical to physical addresses", 0.94),
        ("security", "Public key cryptography uses key pairs", 0.96),
        ("security", "Hashing produces fixed-length digests from variable input", 0.95),
        ("ml", "Neural networks learn through backpropagation", 0.94),
        ("ml", "Gradient descent minimizes loss functions iteratively", 0.93),
        ("distributed", "CAP theorem limits consistency, availability, partition tolerance", 0.95),
    ],
}

# Adversarial agent with wrong facts
ADVERSARY_FACTS: list[tuple[str, str, float]] = [
    ("cells", "Cells are made of pure silicon", 0.99),
    ("water", "Water molecule is H3O", 0.99),
    ("mechanics", "F equals ma squared", 0.99),
    ("geometry", "Pi equals exactly 3", 0.99),
    ("algorithms", "Binary search runs in O(n^2) time", 0.99),
    ("gravity", "Gravity repels objects from each other", 0.99),
    ("calculus", "Derivatives measure total area under curves", 0.99),
    ("atoms", "Atoms are indivisible and have no internal structure", 0.99),
    ("dna", "DNA is made of three strands", 0.99),
    ("relativity", "Nothing is faster than sound", 0.99),
]

# Cross-domain queries with expected answer keywords
CROSS_DOMAIN_QUERIES: list[tuple[str, str, list[str]]] = [
    ("biology", "What are cells made of?", ["unit", "life"]),
    ("biology", "How does DNA store information?", ["nucleotide", "genetic"]),
    ("chemistry", "What is the structure of water?", ["H2O", "bent"]),
    ("chemistry", "How do covalent bonds work?", ["electron", "share"]),
    ("physics", "What is Newton's second law?", ["F", "ma"]),
    ("physics", "Speed of light in vacuum?", ["299792"]),
    ("mathematics", "What is the Pythagorean theorem?", ["a^2", "b^2", "c^2"]),
    ("mathematics", "What does a derivative measure?", ["rate", "change"]),
    ("computer_science", "Time complexity of binary search?", ["log", "n"]),
    ("computer_science", "What are ACID properties?", ["transaction", "reliab"]),
]


# ---------------------------------------------------------------------------
# Evaluation logic
# ---------------------------------------------------------------------------


def run_eval() -> None:
    """Run the full evaluation."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = str(Path(tmp_dir) / "hive_eval.db")
        hive = KuzuHiveMind(db_path=db_path)

        # --- Phase 1: Register agents ---
        print("=" * 70)
        print("KUZU HIVE MIND EVALUATION")
        print("=" * 70)
        print()

        t0 = time.time()

        for domain in DOMAIN_FACTS:
            hive.register_agent(domain, domain=domain)
            print(f"  Registered agent: {domain}")

        hive.register_agent("adversary", domain="adversary")
        print("  Registered agent: adversary")
        print()

        # --- Phase 2: Learn facts ---
        print("Phase 1: Learning facts...")
        for domain, facts in DOMAIN_FACTS.items():
            for concept, content, confidence in facts:
                hive.store_fact(domain, concept, content, confidence)
            print(f"  {domain}: stored {len(facts)} facts")

        for concept, content, confidence in ADVERSARY_FACTS:
            hive.store_fact("adversary", concept, content, confidence)
        print(f"  adversary: stored {len(ADVERSARY_FACTS)} wrong facts")
        print()

        # --- Phase 3: Promote top 10 per domain ---
        print("Phase 2: Promoting top 10 facts per agent...")
        for domain, facts in DOMAIN_FACTS.items():
            # Sort by confidence, take top 10
            top_10 = sorted(facts, key=lambda f: -f[2])[:10]
            promoted_count = 0
            for concept, content, confidence in top_10:
                result = hive.promote_fact(domain, concept, content, confidence)
                if result["status"] == "promoted":
                    promoted_count += 1
            print(f"  {domain}: promoted {promoted_count}/10")

        # Tank adversary trust then try to promote
        hive.registry.update_trust("adversary", -0.8)
        adversary_promoted = 0
        for concept, content, confidence in ADVERSARY_FACTS[:5]:
            result = hive.promote_fact("adversary", concept, content, confidence)
            if result["status"] == "promoted":
                adversary_promoted += 1
        print(f"  adversary: promoted {adversary_promoted}/5 (should be 0)")
        print()

        # --- Phase 4: Score cross-domain queries ---
        print("Phase 3: Scoring cross-domain queries...")
        print("-" * 70)

        isolated_score = 0
        hive_score = 0
        combined_score = 0
        total_queries = len(CROSS_DOMAIN_QUERIES)

        for target_domain, query, expected_keywords in CROSS_DOMAIN_QUERIES:
            # Pick a querying agent that is NOT the target domain
            query_agents = [d for d in DOMAIN_FACTS if d != target_domain]
            querying_agent = query_agents[0]

            # Mode 1: Isolated (local only)
            local_results = hive.query_local(querying_agent, query, limit=5)
            local_hit = _check_keywords(local_results, expected_keywords)

            # Mode 2: Hive only
            hive_results = hive.query_hive(query, limit=5)
            hive_hit = _check_keywords(hive_results, expected_keywords)

            # Mode 3: Combined
            all_results = hive.query_all(querying_agent, query, limit=10)
            combined_hit = _check_keywords(all_results, expected_keywords)

            isolated_score += int(local_hit)
            hive_score += int(hive_hit)
            combined_score += int(combined_hit)

            status_str = (
                f"  [{target_domain:18s}] "
                f"iso={'Y' if local_hit else 'N'} "
                f"hive={'Y' if hive_hit else 'N'} "
                f"all={'Y' if combined_hit else 'N'} "
                f"| {query[:50]}"
            )
            print(status_str)

        elapsed = time.time() - t0
        print("-" * 70)
        print()

        # --- Phase 5: Report ---
        print("=" * 70)
        print("RESULTS")
        print("=" * 70)
        print(f"  Queries:     {total_queries}")
        print(
            f"  Isolated:    {isolated_score}/{total_queries} ({100 * isolated_score / total_queries:.0f}%)"
        )
        print(
            f"  Hive:        {hive_score}/{total_queries} ({100 * hive_score / total_queries:.0f}%)"
        )
        print(
            f"  Combined:    {combined_score}/{total_queries} ({100 * combined_score / total_queries:.0f}%)"
        )
        print(f"  Adversary:   {adversary_promoted} facts leaked (target: 0)")
        print(f"  Elapsed:     {elapsed:.2f}s")
        print()

        # Stats
        stats = hive.get_stats()
        print("HIVE STATISTICS:")
        print(f"  Agents:      {stats['agent_count']}")
        print(f"  Local facts: {stats['total_local_facts']}")
        print(f"  Hive facts:  {stats['total_hive_facts']}")
        for aid, agent_stats in stats.get("per_agent", {}).items():
            print(
                f"  {aid:18s}: local={agent_stats['local_facts']:3d} "
                f"promoted={agent_stats['promoted_facts']:3d} "
                f"trust={agent_stats['trust_score']:.2f}"
            )
        print("=" * 70)


def _check_keywords(results: list[dict], keywords: list[str]) -> bool:
    """Check if any result contains all expected keywords."""
    for result in results:
        content = result.get("content", "").lower()
        if all(kw.lower() in content for kw in keywords):
            return True
    return False


if __name__ == "__main__":
    run_eval()
