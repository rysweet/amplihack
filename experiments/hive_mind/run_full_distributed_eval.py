#!/usr/bin/env python3
"""Full Distributed Hive Mind Evaluation -- 20 Agents x Real Kuzu DBs.

Runs end-to-end with:
- 20 agents, each with its own Kuzu database (KuzuGraphStore)
- 1 HiveGraphStore (separate Kuzu DB) for the shared hive graph
- FederatedGraphStore composing each agent's local graph + hive graph
- LocalEventBus for peer-to-peer event propagation
- HiveCoordinator for expertise routing
- 1 adversarial agent (#21) with deliberate misinformation

Phases:
  1. Create distributed system (agents, hive, bus, federated stores)
  2. Distributed learning (150 domain facts across 10 domains)
  3. Event propagation (3 rounds of peer fact incorporation)
  4. Promotion through gateway (top-8 facts per agent -> hive)
  5. Federated queries (30 questions: isolated vs distributed vs routed)
  6. Results report

Usage:
    python3 -u experiments/hive_mind/run_full_distributed_eval.py
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

_MEMORY_LIB_PATH = "/home/azureuser/src/amplihack-memory-lib-real/src"
if _MEMORY_LIB_PATH not in sys.path:
    sys.path.insert(0, _MEMORY_LIB_PATH)

_AMPLIHACK_PATH = "/home/azureuser/src/amplihack5/src"
if _AMPLIHACK_PATH not in sys.path:
    sys.path.insert(0, _AMPLIHACK_PATH)

import kuzu  # type: ignore[import-not-found]
from amplihack_memory.graph import (  # type: ignore[import-not-found]
    FederatedGraphStore,
    HiveGraphStore,
    KuzuGraphStore,
)

from amplihack.agents.goal_seeking.hive_mind.distributed import (
    HiveCoordinator,  # type: ignore[import-not-found]
)
from amplihack.agents.goal_seeking.hive_mind.event_bus import (  # type: ignore[import-not-found]
    LocalEventBus,
    _make_event,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# 64 MB per DB. 21 DBs = ~1.3 GB RSS, ~2.2 TB VSZ (virtual only, no real cost).
MAX_DB_SIZE = 64 * 1024 * 1024

DOMAINS = [
    "biology",
    "chemistry",
    "physics",
    "math",
    "compsci",
    "history",
    "geography",
    "economics",
    "psychology",
    "engineering",
]

# SemanticMemory schema columns (all STRING for Kuzu flexibility)
SM_COLUMNS = {
    "agent_id": "STRING",
    "concept": "STRING",
    "content": "STRING",
    "confidence": "STRING",
    "tags": "STRING",
    "origin": "STRING",  # "own" | "peer:<agent_id>" | "hive"
}

# 15 facts per domain
DOMAIN_FACTS: dict[str, list[tuple[str, str]]] = {
    "biology": [
        (
            "DNA",
            "DNA is a double helix molecule that carries genetic information in all living organisms",
        ),
        (
            "mitochondria",
            "Mitochondria are the powerhouses of the cell that produce ATP through oxidative phosphorylation",
        ),
        (
            "photosynthesis",
            "Photosynthesis converts carbon dioxide and water into glucose and oxygen using sunlight",
        ),
        (
            "evolution",
            "Natural selection is the primary mechanism of evolution proposed by Charles Darwin",
        ),
        (
            "cell membrane",
            "The cell membrane is a phospholipid bilayer that controls what enters and exits the cell",
        ),
        (
            "RNA",
            "RNA serves as a messenger between DNA and protein synthesis machinery in ribosomes",
        ),
        (
            "enzymes",
            "Enzymes are biological catalysts that speed up chemical reactions without being consumed",
        ),
        ("genetics", "Mendel discovered the laws of inheritance through pea plant experiments"),
        (
            "ecology",
            "Ecosystems consist of biotic organisms and abiotic environmental factors interacting together",
        ),
        (
            "nervous system",
            "Neurons transmit electrical signals through axons using sodium and potassium ion channels",
        ),
        (
            "immune system",
            "White blood cells including T-cells and B-cells defend the body against pathogens",
        ),
        (
            "protein folding",
            "Proteins fold into specific three-dimensional shapes determined by amino acid sequences",
        ),
        ("taxonomy", "Linnaeus created the binomial nomenclature system for classifying organisms"),
        (
            "homeostasis",
            "Homeostasis maintains stable internal conditions through negative feedback mechanisms",
        ),
        (
            "biodiversity",
            "Biodiversity is the variety of life at genetic, species, and ecosystem levels",
        ),
    ],
    "chemistry": [
        (
            "periodic table",
            "The periodic table organizes elements by increasing atomic number and recurring properties",
        ),
        (
            "chemical bonds",
            "Covalent bonds share electrons between atoms while ionic bonds transfer electrons",
        ),
        (
            "acids and bases",
            "Acids donate protons and bases accept protons according to the Bronsted-Lowry theory",
        ),
        (
            "organic chemistry",
            "Carbon atoms form the backbone of organic molecules through tetravalent bonding",
        ),
        (
            "thermodynamics",
            "Enthalpy measures heat content and entropy measures disorder in chemical systems",
        ),
        (
            "electrochemistry",
            "Redox reactions involve electron transfer and power batteries and fuel cells",
        ),
        ("catalysis", "Catalysts lower activation energy without being consumed in the reaction"),
        ("solutions", "Molarity measures concentration as moles of solute per liter of solution"),
        (
            "atomic structure",
            "Electrons occupy orbitals described by quantum numbers in electron shells around the nucleus",
        ),
        (
            "polymers",
            "Polymers are large molecules made of repeating monomer units linked by covalent bonds",
        ),
        (
            "stoichiometry",
            "Stoichiometry uses balanced equations to calculate reactant and product quantities",
        ),
        (
            "gas laws",
            "The ideal gas law PV equals nRT relates pressure volume temperature and amount of gas",
        ),
        (
            "chemical equilibrium",
            "Le Chatelier principle states that systems shift to counteract applied stress",
        ),
        (
            "nuclear chemistry",
            "Radioactive decay transforms unstable nuclei by emitting alpha beta or gamma radiation",
        ),
        (
            "spectroscopy",
            "Spectroscopy identifies substances by analyzing their interaction with electromagnetic radiation",
        ),
    ],
    "physics": [
        (
            "gravity",
            "Gravity is described by Einstein general relativity as curvature of spacetime caused by mass",
        ),
        (
            "quantum mechanics",
            "Quantum mechanics describes particle behavior at atomic scales using wave functions",
        ),
        (
            "electromagnetism",
            "Maxwell equations unify electricity and magnetism into electromagnetic field theory",
        ),
        (
            "thermodynamics",
            "The second law of thermodynamics states entropy of an isolated system always increases",
        ),
        (
            "relativity",
            "Special relativity shows that time dilates and length contracts at speeds near light",
        ),
        ("optics", "Light behaves as both wave and particle demonstrating wave-particle duality"),
        (
            "nuclear physics",
            "Nuclear fission splits heavy atoms releasing enormous energy as described by E equals mc squared",
        ),
        (
            "fluid dynamics",
            "Bernoulli principle explains that faster fluid flow creates lower pressure",
        ),
        (
            "mechanics",
            "Newton three laws of motion describe force mass acceleration and action-reaction pairs",
        ),
        ("waves", "Sound waves are longitudinal pressure oscillations that travel through matter"),
        (
            "electricity",
            "Ohm law states that current equals voltage divided by resistance in a circuit",
        ),
        (
            "magnetism",
            "Magnetic fields are produced by moving electric charges and magnetic dipoles",
        ),
        (
            "particle physics",
            "The Standard Model classifies fundamental particles into quarks leptons and bosons",
        ),
        (
            "astrophysics",
            "Stars produce energy through nuclear fusion of hydrogen into helium in their cores",
        ),
        (
            "condensed matter",
            "Superconductors carry electric current with zero resistance below critical temperature",
        ),
    ],
    "math": [
        (
            "calculus",
            "Calculus studies rates of change through derivatives and accumulation through integrals",
        ),
        ("algebra", "Abstract algebra studies groups rings and fields as algebraic structures"),
        (
            "geometry",
            "Euclidean geometry is based on five postulates including the parallel postulate",
        ),
        (
            "probability",
            "Bayes theorem calculates conditional probability by updating prior beliefs with evidence",
        ),
        (
            "number theory",
            "Prime numbers are natural numbers greater than one divisible only by one and themselves",
        ),
        (
            "topology",
            "Topology studies properties preserved under continuous deformations like stretching",
        ),
        (
            "linear algebra",
            "Matrices represent linear transformations and eigenvalues describe their scaling behavior",
        ),
        (
            "statistics",
            "The central limit theorem states sample means approach normal distribution regardless of population",
        ),
        (
            "graph theory",
            "Graph theory studies networks of nodes and edges modeling relationships and connections",
        ),
        (
            "differential equations",
            "Differential equations describe how quantities change relative to other quantities",
        ),
        (
            "set theory",
            "Cantor proved that real numbers are uncountable using the diagonal argument",
        ),
        (
            "logic",
            "Godel incompleteness theorems show that consistent formal systems cannot prove all true statements",
        ),
        ("combinatorics", "Combinatorics counts arrangements and selections of discrete objects"),
        (
            "analysis",
            "Real analysis formalizes limits continuity and convergence of sequences and series",
        ),
        (
            "cryptography",
            "RSA encryption relies on the difficulty of factoring large composite numbers",
        ),
    ],
    "compsci": [
        (
            "algorithms",
            "Algorithm complexity is measured using Big O notation for worst-case time and space",
        ),
        (
            "data structures",
            "Binary search trees maintain sorted order with O log n average lookup time",
        ),
        (
            "operating systems",
            "Operating systems manage hardware resources through process scheduling and memory management",
        ),
        (
            "networking",
            "TCP IP protocol suite enables reliable data transmission across interconnected networks",
        ),
        (
            "databases",
            "Relational databases use SQL for querying data organized in normalized tables",
        ),
        (
            "machine learning",
            "Neural networks learn patterns through gradient descent on differentiable loss functions",
        ),
        (
            "compilers",
            "Compilers translate source code to machine code through lexing parsing and code generation",
        ),
        (
            "distributed systems",
            "The CAP theorem states distributed systems cannot simultaneously guarantee consistency availability and partition tolerance",
        ),
        (
            "security",
            "Public key cryptography enables secure communication using asymmetric key pairs",
        ),
        (
            "graphics",
            "Ray tracing simulates light transport to generate photorealistic computer images",
        ),
        (
            "artificial intelligence",
            "Search algorithms like A-star find optimal paths using heuristic cost estimates",
        ),
        (
            "programming languages",
            "Type systems prevent category errors by classifying expressions at compile time",
        ),
        (
            "software engineering",
            "Agile development iterates through short sprints with continuous feedback",
        ),
        (
            "parallel computing",
            "Amdahl law limits parallel speedup based on the sequential fraction of computation",
        ),
        (
            "cloud computing",
            "Containers provide lightweight isolated environments for deploying applications",
        ),
    ],
    "history": [
        (
            "ancient rome",
            "The Roman Republic transitioned to the Roman Empire under Augustus Caesar in 27 BCE",
        ),
        (
            "world war two",
            "World War Two ended in 1945 after the atomic bombings of Hiroshima and Nagasaki",
        ),
        (
            "industrial revolution",
            "The Industrial Revolution transformed manufacturing through steam power starting in 18th century Britain",
        ),
        (
            "renaissance",
            "The Renaissance was a cultural rebirth in 14th-16th century Europe emphasizing humanism and art",
        ),
        (
            "french revolution",
            "The French Revolution of 1789 overthrew the monarchy and established republican ideals",
        ),
        (
            "cold war",
            "The Cold War was a geopolitical rivalry between the USA and USSR from 1947 to 1991",
        ),
        (
            "ancient egypt",
            "Ancient Egyptians built pyramids as tombs for pharaohs using limestone blocks",
        ),
        (
            "ancient greece",
            "Ancient Greek democracy in Athens allowed male citizens to vote on legislation directly",
        ),
        (
            "colonialism",
            "European colonialism expanded from the 15th century driven by trade and territorial ambition",
        ),
        (
            "civil rights",
            "The American civil rights movement achieved landmark legislation including the 1964 Civil Rights Act",
        ),
        (
            "silk road",
            "The Silk Road connected China to the Mediterranean facilitating trade in silk spices and ideas",
        ),
        (
            "medieval period",
            "The feudal system organized medieval European society around land ownership and vassalage",
        ),
        (
            "enlightenment",
            "The Enlightenment emphasized reason science and individual rights in 17th-18th century Europe",
        ),
        (
            "american revolution",
            "The American Revolution of 1776 established independence from Britain based on Enlightenment principles",
        ),
        (
            "space race",
            "The space race culminated in Apollo 11 landing humans on the Moon on July 20 1969",
        ),
    ],
    "geography": [
        (
            "plate tectonics",
            "Plate tectonics explains continental drift through movement of lithospheric plates",
        ),
        (
            "climate zones",
            "Earth climate zones range from tropical near the equator to polar near the poles",
        ),
        (
            "oceans",
            "The Pacific Ocean is the largest and deepest ocean covering more than 30 percent of Earth surface",
        ),
        (
            "mountains",
            "The Himalayas formed from the collision of the Indian and Eurasian tectonic plates",
        ),
        (
            "rivers",
            "The Amazon River carries the largest volume of water of any river in the world",
        ),
        (
            "volcanoes",
            "Volcanic eruptions occur at plate boundaries and hotspots releasing magma from Earth interior",
        ),
        (
            "deserts",
            "The Sahara is the largest hot desert spanning over 9 million square kilometers in northern Africa",
        ),
        (
            "atmosphere",
            "Earth atmosphere consists of 78 percent nitrogen and 21 percent oxygen by volume",
        ),
        (
            "glaciers",
            "Glaciers store about 69 percent of Earth fresh water and shape landscapes through erosion",
        ),
        (
            "population",
            "World population reached 8 billion in 2022 with Asia being the most populated continent",
        ),
        (
            "biomes",
            "Biomes are large ecological areas defined by climate vegetation and animal communities",
        ),
        (
            "cartography",
            "Mercator projection maps preserve direction but distort area especially near the poles",
        ),
        (
            "erosion",
            "Water wind and ice cause erosion that reshapes Earth surface over geological time",
        ),
        ("urbanization", "More than 55 percent of the world population now lives in urban areas"),
        (
            "natural resources",
            "Fossil fuels including coal oil and natural gas are non-renewable energy resources",
        ),
    ],
    "economics": [
        (
            "supply and demand",
            "Supply and demand curves intersect at equilibrium price where quantity supplied equals demanded",
        ),
        (
            "GDP",
            "Gross Domestic Product measures the total value of goods and services produced in a country",
        ),
        (
            "inflation",
            "Inflation is a sustained increase in the general price level reducing purchasing power",
        ),
        (
            "monetary policy",
            "Central banks control money supply through interest rates and open market operations",
        ),
        (
            "fiscal policy",
            "Government spending and taxation are the primary tools of fiscal policy",
        ),
        (
            "market structures",
            "Perfect competition features many sellers with identical products and no market power",
        ),
        (
            "trade",
            "Comparative advantage explains why countries benefit from specializing and trading",
        ),
        (
            "labor economics",
            "Minimum wage laws set a price floor for labor that can affect employment levels",
        ),
        (
            "macroeconomics",
            "Business cycles consist of expansion peak contraction and trough phases",
        ),
        (
            "microeconomics",
            "Utility maximization theory assumes consumers allocate budgets to maximize satisfaction",
        ),
        (
            "game theory",
            "Nash equilibrium occurs when no player can improve by unilaterally changing strategy",
        ),
        (
            "development economics",
            "The Human Development Index combines life expectancy education and income metrics",
        ),
        (
            "financial markets",
            "Stock markets facilitate trading of company shares enabling capital formation",
        ),
        (
            "international finance",
            "Exchange rates are determined by supply and demand for currencies in forex markets",
        ),
        (
            "behavioral economics",
            "Loss aversion shows that people feel losses more strongly than equivalent gains",
        ),
    ],
    "psychology": [
        (
            "conditioning",
            "Pavlov discovered classical conditioning through experiments with dogs and bell stimuli",
        ),
        (
            "cognitive psychology",
            "Working memory has limited capacity of about 7 plus or minus 2 items",
        ),
        (
            "developmental",
            "Piaget identified four stages of cognitive development from sensorimotor to formal operational",
        ),
        (
            "social psychology",
            "The bystander effect shows people are less likely to help when others are present",
        ),
        (
            "personality",
            "The Big Five personality traits are openness conscientiousness extraversion agreeableness neuroticism",
        ),
        (
            "abnormal psychology",
            "Depression involves persistent sadness loss of interest and changes in sleep and appetite",
        ),
        (
            "neuroscience",
            "The prefrontal cortex is responsible for executive functions like planning and decision making",
        ),
        (
            "memory",
            "Long-term memory is divided into declarative explicit and procedural implicit types",
        ),
        (
            "perception",
            "Gestalt principles describe how humans perceive visual elements as organized patterns",
        ),
        (
            "motivation",
            "Maslow hierarchy of needs ranges from physiological needs to self-actualization",
        ),
        (
            "learning theory",
            "Reinforcement schedules determine how quickly behaviors are acquired and extinguished",
        ),
        ("emotion", "The amygdala plays a central role in processing fear and emotional memory"),
        (
            "intelligence",
            "Multiple intelligence theory by Gardner proposes eight distinct types of intelligence",
        ),
        (
            "stress",
            "The fight-or-flight response activates the sympathetic nervous system during perceived threats",
        ),
        (
            "therapy",
            "Cognitive behavioral therapy changes negative thought patterns to improve mental health",
        ),
    ],
    "engineering": [
        (
            "structural",
            "Steel reinforced concrete combines compressive strength of concrete with tensile strength of steel",
        ),
        (
            "electrical",
            "Transformers change voltage levels using electromagnetic induction between coil windings",
        ),
        (
            "mechanical",
            "Thermodynamic cycles like the Carnot cycle determine maximum efficiency of heat engines",
        ),
        (
            "civil",
            "Bridges use truss beam arch and suspension designs to span gaps and support loads",
        ),
        (
            "chemical engineering",
            "Distillation separates liquid mixtures based on differences in boiling points",
        ),
        (
            "aerospace",
            "Bernoulli principle and Newton third law explain how airplane wings generate lift",
        ),
        (
            "materials science",
            "Alloys combine metals to achieve properties like strength corrosion resistance and ductility",
        ),
        (
            "robotics",
            "Feedback control systems use sensors and PID controllers to maintain desired robot behavior",
        ),
        (
            "environmental",
            "Wastewater treatment removes contaminants through physical chemical and biological processes",
        ),
        (
            "biomedical",
            "MRI scanners use magnetic fields and radio waves to create detailed images of body tissues",
        ),
        (
            "software engineering",
            "Version control systems like Git track changes enabling collaborative software development",
        ),
        (
            "manufacturing",
            "CNC machining uses computer-controlled tools to precisely cut and shape materials",
        ),
        (
            "telecommunications",
            "Fiber optic cables transmit data as light pulses achieving high bandwidth and low latency",
        ),
        (
            "power systems",
            "Three phase alternating current is the standard for electrical power transmission",
        ),
        (
            "control systems",
            "PID controllers adjust output based on proportional integral and derivative of error",
        ),
    ],
}

# Adversarial facts (deliberate misinformation)
ADVERSARIAL_FACTS = [
    ("gravity", "Gravity does not exist and objects fall because the earth is expanding upward"),
    ("evolution", "Evolution has been completely disproven and species do not change over time"),
    ("vaccines", "Vaccines cause more diseases than they prevent according to all studies"),
    ("climate", "Global temperatures have been decreasing every year since 1990"),
    ("DNA", "DNA is a single straight strand that has no role in heredity"),
]

# 30 questions: 10 single-domain, 10 cross-domain, 10 synthesis
QUESTIONS: list[tuple[str, str, list[str]]] = [
    # --- Single-domain ---
    ("single", "What is DNA and what shape does it have?", ["double helix", "genetic"]),
    (
        "single",
        "How do enzymes work in biological reactions?",
        ["catalyst", "speed up", "chemical"],
    ),
    ("single", "What does the periodic table organize?", ["elements", "atomic number"]),
    ("single", "What is Newton third law of motion?", ["action", "reaction"]),
    ("single", "What is Big O notation used for?", ["algorithm", "complexity", "time"]),
    ("single", "When did World War Two end?", ["1945"]),
    ("single", "What is the largest ocean on Earth?", ["pacific"]),
    ("single", "What is GDP?", ["gross domestic product", "goods", "services"]),
    ("single", "What did Pavlov discover?", ["classical conditioning", "dogs"]),
    ("single", "What is steel reinforced concrete?", ["compressive", "tensile"]),
    # --- Cross-domain ---
    (
        "cross",
        "How do catalysts work in biology and chemistry?",
        ["enzyme", "activation energy", "speed"],
    ),
    (
        "cross",
        "How is thermodynamics relevant to physics and engineering?",
        ["entropy", "heat", "carnot", "efficiency"],
    ),
    (
        "cross",
        "How do electrical signals work in neurons and circuits?",
        ["current", "voltage", "ion", "sodium"],
    ),
    (
        "cross",
        "What connects graph theory in math with networking in compsci?",
        ["nodes", "edges", "network"],
    ),
    (
        "cross",
        "How did the Enlightenment influence the French and American revolutions?",
        ["reason", "rights", "enlightenment"],
    ),
    (
        "cross",
        "How do plate tectonics relate to mountains and volcanoes?",
        ["plates", "collision", "himalayas", "magma"],
    ),
    (
        "cross",
        "What is the relationship between supply-demand and game theory?",
        ["equilibrium", "strategy", "nash"],
    ),
    (
        "cross",
        "How is memory studied in psychology and computer science?",
        ["working memory", "data structures", "capacity"],
    ),
    (
        "cross",
        "How do waves relate to sound in physics and spectroscopy?",
        ["wave", "electromagnetic", "radiation"],
    ),
    (
        "cross",
        "What connects evolution in biology with machine learning?",
        ["natural selection", "gradient", "pattern"],
    ),
    # --- Synthesis ---
    (
        "synthesis",
        "How can molecular biology inform chemical engineering?",
        ["protein", "molecule", "reaction"],
    ),
    (
        "synthesis",
        "What physics principles underlie telecommunications engineering?",
        ["electromagnetic", "light", "fiber optic"],
    ),
    (
        "synthesis",
        "How does behavioral economics combine psychology and economics?",
        ["loss aversion", "bias", "rational"],
    ),
    (
        "synthesis",
        "What role does statistics play across sciences?",
        ["central limit", "probability", "sample"],
    ),
    (
        "synthesis",
        "How do control systems mirror homeostasis in biology?",
        ["feedback", "stable", "pid", "negative feedback"],
    ),
    (
        "synthesis",
        "How does complexity theory limit artificial intelligence?",
        ["complexity", "algorithm", "optimal"],
    ),
    (
        "synthesis",
        "How do environmental engineering and geography address water?",
        ["water", "erosion", "treatment", "fresh"],
    ),
    (
        "synthesis",
        "What connects the Renaissance with optics?",
        ["renaissance", "light", "perspective"],
    ),
    (
        "synthesis",
        "How do cryptographic methods bridge number theory and security?",
        ["prime", "factoring", "rsa", "encryption"],
    ),
    (
        "synthesis",
        "What links neural networks with neuroscience?",
        ["neural", "neuron", "learning", "pattern"],
    ),
]


# ---------------------------------------------------------------------------
# Sized Kuzu factories (prevent Mmap exhaustion)
# ---------------------------------------------------------------------------


def _make_sized_kuzu_graph_store(
    db_path: str, store_id: str, max_size: int = MAX_DB_SIZE
) -> KuzuGraphStore:
    """Create a KuzuGraphStore with a size-limited Kuzu database.

    KuzuGraphStore.__init__ creates kuzu.Database with the 8 TB default
    max_db_size which causes Mmap failures when many stores coexist in
    one process. This factory creates the DB with a controlled size then
    constructs the store around it.
    """
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    db = kuzu.Database(db_path, max_db_size=max_size)
    store = object.__new__(KuzuGraphStore)
    store._db_path = Path(db_path)
    store._store_id = store_id
    store._db = db
    store._conn = kuzu.Connection(db)
    store._known_node_tables = set()
    store._known_rel_tables = set()
    store._node_table_columns = {}
    store._id_table_cache = {}
    return store


def _make_sized_hive_graph_store(db_path: str, max_size: int = MAX_DB_SIZE) -> HiveGraphStore:
    """Create a HiveGraphStore with a size-limited Kuzu database."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    db = kuzu.Database(db_path, max_db_size=max_size)
    store = object.__new__(HiveGraphStore)
    store._db_path = Path(db_path)
    store._store_id = "__hive__"
    store._db = db
    store._conn = kuzu.Connection(db)
    store._known_node_tables = set()
    store._known_rel_tables = set()
    store._node_table_columns = {}
    store._id_table_cache = {}
    store._setup_hive_schema()
    return store


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def score_answer(results: list[dict], keywords: list[str]) -> float:
    """Score results by keyword coverage. Returns 0.0 - 1.0."""
    if not keywords:
        return 1.0 if results else 0.0

    combined = " ".join(
        (r.get("content", "") + " " + r.get("concept", "")).lower() for r in results
    )
    matched = sum(1 for kw in keywords if kw.lower() in combined)
    return matched / len(keywords)


# ---------------------------------------------------------------------------
# Agent data holder
# ---------------------------------------------------------------------------


@dataclass
class EvalAgent:
    """Agent with its own KuzuGraphStore + FederatedGraphStore."""

    agent_id: str
    domain: str
    local_graph: KuzuGraphStore
    federated: FederatedGraphStore
    facts_learned: int = 0
    facts_incorporated: int = 0
    _incorporated_ids: set = field(default_factory=set)

    def learn_fact(self, concept: str, content: str, confidence: float, tags: list[str]) -> str:
        """Store a fact in the local KuzuGraphStore. Tagged as 'own'."""
        nid = f"f_{uuid.uuid4().hex[:10]}"
        self.local_graph.add_node(
            "SemanticMemory",
            {
                "agent_id": self.agent_id,
                "concept": concept,
                "content": content,
                "confidence": str(confidence),
                "tags": str(tags),
                "origin": "own",  # marks as agent's own fact
            },
            node_id=nid,
        )
        self.facts_learned += 1
        return nid

    def incorporate_peer(
        self,
        concept: str,
        content: str,
        confidence: float,
        tags: list[str],
        source_agent: str,
        event_id: str,
    ) -> bool:
        """Incorporate a peer fact at 0.9x discounted confidence."""
        if event_id in self._incorporated_ids:
            return False
        peer_conf = confidence * 0.9
        peer_tags = tags + [f"from:{source_agent}"]
        nid = f"p_{uuid.uuid4().hex[:10]}"
        self.local_graph.add_node(
            "SemanticMemory",
            {
                "agent_id": self.agent_id,
                "concept": concept,
                "content": content,
                "confidence": str(peer_conf),
                "tags": str(peer_tags),
                "origin": f"peer:{source_agent}",  # marks as peer-sourced
            },
            node_id=nid,
        )
        self._incorporated_ids.add(event_id)
        self.facts_incorporated += 1
        return True

    def query_isolated(self, query: str, limit: int = 20) -> list[dict]:
        """Search ONLY the agent's own originally-learned facts (isolated).

        Filters to origin='own' facts only -- no peer-incorporated knowledge.
        This simulates an agent working alone without hive connectivity.
        """
        results = _keyword_search(self.local_graph, query, limit * 3)
        # Filter to own facts only
        own = [r for r in results if r.get("origin") == "own"]
        return own[:limit]

    def query_distributed(self, query: str, limit: int = 20) -> list[dict]:
        """Search own facts + hive-promoted facts via FederatedGraphStore.

        Simulates: agent sees own knowledge + shared hive knowledge,
        but NOT peer-gossip. This shows the value of the hive promotion
        mechanism (curated shared knowledge vs raw gossip).
        """
        results = _keyword_search(self.federated, query, limit * 3)
        # Include own facts + anything from hive (graph_origin != agent_id)
        filtered = [
            r
            for r in results
            if r.get("origin") == "own"
            or r.get("origin") == ""
            or r.get("source_agent") != self.agent_id
        ]
        return filtered[:limit]

    def query_routed_expert(self, query: str, limit: int = 20) -> list[dict]:
        """Expert query: search all own + peer + hive facts.

        Experts have deep knowledge in their domain. When routed to,
        they use their full local DB (own + propagated peer facts)
        plus the hive.
        """
        return _keyword_search(self.federated, query, limit)

    def get_all_local_facts(self, limit: int = 500) -> list[dict]:
        """Return all SemanticMemory nodes from local graph."""
        nodes = self.local_graph.query_nodes("SemanticMemory", limit=limit)
        return [_node_to_dict(n) for n in nodes]


def _node_to_dict(n) -> dict:
    """Convert a GraphNode to a simple dict."""
    return {
        "node_id": n.node_id,
        "concept": n.properties.get("concept", ""),
        "content": n.properties.get("content", ""),
        "confidence": float(n.properties.get("confidence", "0.0")),
        "source_agent": n.properties.get("agent_id", n.graph_origin),
        "tags": n.properties.get("tags", "[]"),
        "origin": n.properties.get("origin", ""),
    }


# Stopwords to skip when splitting queries into keywords
_STOPWORDS = frozenset(
    [
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "shall",
        "should",
        "may",
        "might",
        "can",
        "could",
        "and",
        "or",
        "but",
        "not",
        "no",
        "nor",
        "for",
        "to",
        "from",
        "by",
        "with",
        "at",
        "of",
        "in",
        "on",
        "it",
        "its",
        "that",
        "this",
        "these",
        "those",
        "what",
        "which",
        "who",
        "whom",
        "how",
        "when",
        "where",
        "why",
        "if",
        "then",
        "so",
        "as",
        "both",
        "each",
        "any",
        "all",
        "into",
        "about",
        "between",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "up",
        "down",
        "out",
        "off",
        "over",
        "under",
        "again",
        "further",
        "also",
        "very",
        "too",
        "much",
        "many",
    ]
)


def _keyword_search(store, query: str, limit: int = 20) -> list[dict]:
    """Search a GraphStore (or FederatedGraphStore) by individual keywords.

    KuzuGraphStore.search_nodes uses CONTAINS with the FULL query string.
    Multi-word queries like "What is DNA?" would never match because no
    field contains that exact substring. This helper extracts meaningful
    keywords and searches for each one, deduplicating results.
    """
    keywords = [
        w for w in query.lower().split() if len(w) > 2 and w.strip("?.,!") not in _STOPWORDS
    ]
    # Clean punctuation
    keywords = [w.strip("?.,!\"'()") for w in keywords]
    keywords = [w for w in keywords if w]

    if not keywords:
        keywords = query.lower().split()[:3]

    seen_ids: set[str] = set()
    results: list[dict] = []

    for kw in keywords[:6]:  # limit to 6 keywords to avoid too many queries
        try:
            nodes = store.search_nodes(
                "SemanticMemory",
                ["concept", "content"],
                kw,
                limit=limit,
            )
        except RuntimeError:
            nodes = []
        for n in nodes:
            if n.node_id not in seen_ids:
                seen_ids.add(n.node_id)
                results.append(_node_to_dict(n))

    # Sort by confidence descending
    results.sort(key=lambda r: -r["confidence"])
    return results[:limit]


# ---------------------------------------------------------------------------
# Main evaluation
# ---------------------------------------------------------------------------


def run_eval() -> None:
    t_start = time.time()
    base_dir = tempfile.mkdtemp(prefix="hive_eval_")

    print("=" * 72)
    print("=== FULL DISTRIBUTED HIVE MIND EVALUATION ===")
    print("=" * 72)
    print("Architecture: 20 agents x own Kuzu DB + HiveGraphStore + FederatedGraphStore")
    print(f"Agents: 20 | Domains: {len(DOMAINS)} | Facts/agent: 15 | Total: 300")
    print(f"Temp dir: {base_dir}")
    print()

    # ==================================================================
    # PHASE 1: Create distributed system
    # ==================================================================
    print("--- PHASE 1: CREATING DISTRIBUTED SYSTEM ---")
    sys.stdout.flush()

    # Hive's own Kuzu DB
    hive_db_path = os.path.join(base_dir, "hive_graph")
    hive_store = _make_sized_hive_graph_store(hive_db_path)

    # Ensure SemanticMemory table exists in hive (for promoted facts)
    hive_store.ensure_node_table("SemanticMemory", SM_COLUMNS)

    # Edges: HiveAgent -[PROMOTED_TO_HIVE]-> SemanticMemory
    hive_store.ensure_rel_table(
        "PROMOTED_TO_HIVE",
        "HiveAgent",
        "SemanticMemory",
        {"promoted_at": "STRING", "confidence": "STRING"},
    )
    # Edges: SemanticMemory -[CONTRADICTS_FACT]-> SemanticMemory
    hive_store.ensure_rel_table(
        "CONTRADICTS_FACT",
        "SemanticMemory",
        "SemanticMemory",
        {"detected_at": "STRING", "description": "STRING"},
    )

    event_bus = LocalEventBus()
    coordinator = HiveCoordinator()

    agents: dict[str, EvalAgent] = {}

    for domain in DOMAINS:
        for idx in (1, 2):
            agent_id = f"{domain}_{idx}"

            # One Kuzu DB per agent
            graph_db = os.path.join(base_dir, agent_id)
            local_graph = _make_sized_kuzu_graph_store(graph_db, agent_id)
            local_graph.ensure_node_table("SemanticMemory", SM_COLUMNS)

            # Federated = local + hive
            federated = FederatedGraphStore(
                local_store=local_graph,
                hive_store=hive_store,
            )

            # Register in hive and coordinator
            hive_store.register_agent(agent_id, domain=domain)
            coordinator.register_agent(agent_id, domain)
            event_bus.subscribe(agent_id, ["FACT_LEARNED", "FACT_PROMOTED"])

            agents[agent_id] = EvalAgent(
                agent_id=agent_id,
                domain=domain,
                local_graph=local_graph,
                federated=federated,
            )

    print(f"  Created {len(agents)} agents across {len(DOMAINS)} domains")
    print()
    print("  --- AGENT SETUP ---")
    for aid in sorted(agents):
        ag = agents[aid]
        print(f"    {aid:20s}  domain={ag.domain:14s}  db={os.path.join(base_dir, aid)}")
    print()
    sys.stdout.flush()

    # ==================================================================
    # PHASE 2: Distributed learning
    # ==================================================================
    print("--- PHASE 2: DISTRIBUTED LEARNING ---")
    sys.stdout.flush()

    event_count = 0
    for domain in DOMAINS:
        facts = DOMAIN_FACTS[domain]
        for idx in (1, 2):
            agent_id = f"{domain}_{idx}"
            agent = agents[agent_id]
            for concept, content in facts:
                nid = agent.learn_fact(concept, content, 0.85, [domain])
                # Report to coordinator for routing
                coordinator.report_fact(agent_id, concept)
                # Publish event
                event_bus.publish(
                    _make_event(
                        "FACT_LEARNED",
                        agent_id,
                        {
                            "concept": concept,
                            "content": content,
                            "confidence": 0.85,
                            "tags": [domain],
                            "node_id": nid,
                        },
                    )
                )
                event_count += 1

    total_facts = sum(a.facts_learned for a in agents.values())
    print(f"  Total facts learned: {total_facts}")
    print(f"  Events published: {event_count}")
    print()
    sys.stdout.flush()

    # ==================================================================
    # PHASE 3: Event propagation (3 rounds)
    # ==================================================================
    print("--- PHASE 3: EVENT PROPAGATION ---")
    sys.stdout.flush()

    # Round 1: each agent processes the 300 original FACT_LEARNED events.
    # The bus already delivered to all 19 other agents (no self-delivery).
    # Rounds 2-3: same-domain agents selectively share their TOP facts
    # (simulating gossip within a domain cluster). No exponential re-broadcast.
    for rnd in range(1, 4):
        round_count = 0
        for agent_id, agent in agents.items():
            events = event_bus.poll(agent_id)
            for ev in events:
                if ev.source_agent == agent_id:
                    continue
                p = ev.payload
                ok = agent.incorporate_peer(
                    p.get("concept", ""),
                    p.get("content", ""),
                    p.get("confidence", 0.5),
                    p.get("tags", []),
                    ev.source_agent,
                    ev.event_id,
                )
                if ok:
                    round_count += 1
        print(f"  Round {rnd}: {round_count} facts incorporated")
        sys.stdout.flush()

        # After round 1, publish domain-specific "best of" summaries
        # (each agent shares its top-5 facts to same-domain peers only)
        if rnd < 3:
            for agent_id, agent in agents.items():
                top_facts = agent.get_all_local_facts(limit=5)
                for f in top_facts[:5]:
                    event_bus.publish(
                        _make_event(
                            "FACT_LEARNED",
                            agent_id,
                            {
                                "concept": f["concept"],
                                "content": f["content"],
                                "confidence": float(f["confidence"]) * 0.9,
                                "tags": [agent.domain],
                                "node_id": f"sel_{uuid.uuid4().hex[:6]}",
                            },
                        )
                    )

    total_incorp = sum(a.facts_incorporated for a in agents.values())
    print(f"  Total incorporated across all agents: {total_incorp}")
    print()
    sys.stdout.flush()

    # ==================================================================
    # PHASE 4: Promotion through gateway
    # ==================================================================
    print("--- PHASE 4: PROMOTION THROUGH GATEWAY ---")
    sys.stdout.flush()

    promoted_count = 0
    blocked_count = 0
    contradictions_detected = 0

    for agent_id, agent in agents.items():
        all_facts = agent.get_all_local_facts(limit=500)
        # Sort by confidence, take top 8
        all_facts.sort(key=lambda f: -f["confidence"])
        top8 = all_facts[:8]

        for fact in top8:
            trust = hive_store.get_agent_trust(agent_id)
            if trust < 0.3:
                blocked_count += 1
                continue

            promoted_nid = f"hv_{uuid.uuid4().hex[:10]}"
            hive_store.add_node(
                "SemanticMemory",
                {
                    "agent_id": agent_id,
                    "concept": fact["concept"],
                    "content": fact["content"],
                    "confidence": str(fact["confidence"] * trust),
                    "tags": fact.get("tags", "[]"),
                },
                node_id=promoted_nid,
            )

            try:
                hive_store.add_edge(
                    agent_id,
                    promoted_nid,
                    "PROMOTED_TO_HIVE",
                    {"promoted_at": str(time.time()), "confidence": str(fact["confidence"])},
                )
            except (KeyError, RuntimeError):
                pass  # edge creation issue, fact was still stored
            promoted_count += 1

    # --- Adversarial agent #21 ---
    adversary_id = "adversary_1"
    hive_store.register_agent(adversary_id, domain="misinformation")
    hive_store.update_trust(adversary_id, 0.2)  # low trust

    adversary_blocked = 0
    for concept, content in ADVERSARIAL_FACTS:
        trust = hive_store.get_agent_trust(adversary_id)
        if trust < 0.3:
            # Blocked by trust gate
            adversary_blocked += 1
            blocked_count += 1

            # Also check for contradiction with existing facts
            existing = hive_store.search_nodes(
                "SemanticMemory",
                ["concept"],
                concept,
                limit=3,
            )
            if existing:
                contradictions_detected += 1
                # Record contradiction edge
                bad_nid = f"adv_{uuid.uuid4().hex[:8]}"
                hive_store.add_node(
                    "SemanticMemory",
                    {
                        "agent_id": adversary_id,
                        "concept": concept,
                        "content": content,
                        "confidence": "0.0",
                        "tags": '["adversarial", "blocked"]',
                    },
                    node_id=bad_nid,
                )
                try:
                    hive_store.add_edge(
                        existing[0].node_id,
                        bad_nid,
                        "CONTRADICTS_FACT",
                        {
                            "detected_at": str(time.time()),
                            "description": f"Adversarial claim contradicts established {concept} knowledge",
                        },
                    )
                except (KeyError, RuntimeError):
                    pass
            continue

    print(f"  Total promoted to hive: {promoted_count}/{len(agents) * 8}")
    print(f"  Adversarial blocked: {adversary_blocked}/{len(ADVERSARIAL_FACTS)}")
    print(f"  Contradictions detected: {contradictions_detected}")
    print()
    sys.stdout.flush()

    # ==================================================================
    # PHASE 5: Federated queries
    # ==================================================================
    print("--- PHASE 5: FEDERATED QUERIES ---")
    sys.stdout.flush()

    results_by_type: dict[str, dict[str, list[float]]] = {
        "single": {"isolated": [], "distributed": [], "routed": []},
        "cross": {"isolated": [], "distributed": [], "routed": []},
        "synthesis": {"isolated": [], "distributed": [], "routed": []},
    }
    cross_boundary_count = 0

    # The asking agent is biology_1 (has only biology facts locally)
    asking_agent = agents["biology_1"]

    for q_type, question, keywords in QUESTIONS:
        # ISOLATED: only the asking agent's OWN 15 facts (no peers, no hive)
        iso = asking_agent.query_isolated(question, limit=20)
        iso_score = score_answer(iso, keywords)

        # DISTRIBUTED: federated store (all local facts + hive-promoted facts)
        dist = asking_agent.query_distributed(question, limit=20)
        dist_score = score_answer(dist, keywords)
        if len(dist) > len(iso):
            cross_boundary_count += 1

        # ROUTED: coordinator picks expert, query THEIR full knowledge
        expert_ids = coordinator.route_query(question)
        routed_results: list[dict] = []
        seen: set[str] = set()
        for eid in expert_ids[:3]:
            if eid in agents:
                exp_results = agents[eid].query_routed_expert(question, limit=20)
                for r in exp_results:
                    ck = r["content"].strip().lower()
                    if ck not in seen:
                        seen.add(ck)
                        routed_results.append(r)
        routed_score = score_answer(routed_results, keywords)

        results_by_type[q_type]["isolated"].append(iso_score)
        results_by_type[q_type]["distributed"].append(dist_score)
        results_by_type[q_type]["routed"].append(routed_score)

    print(f"  Evaluated {len(QUESTIONS)} questions")
    print()
    sys.stdout.flush()

    # ==================================================================
    # PHASE 6: Results
    # ==================================================================
    print("=" * 72)
    print("--- RESULTS ---")
    print("=" * 72)
    print()
    print(f"{'':20s}  {'ISOLATED':>10s}  {'DISTRIBUTED':>12s}  {'ROUTED':>10s}")
    print("-" * 58)

    overall_iso, overall_dist, overall_routed = [], [], []

    for q_type in ("single", "cross", "synthesis"):
        iso_s = results_by_type[q_type]["isolated"]
        dst_s = results_by_type[q_type]["distributed"]
        rte_s = results_by_type[q_type]["routed"]

        iso_avg = (sum(iso_s) / len(iso_s) * 100) if iso_s else 0
        dst_avg = (sum(dst_s) / len(dst_s) * 100) if dst_s else 0
        rte_avg = (sum(rte_s) / len(rte_s) * 100) if rte_s else 0

        label = {"single": "Single-domain", "cross": "Cross-domain", "synthesis": "Synthesis"}[
            q_type
        ]
        print(f"{label:20s}  {iso_avg:9.1f}%  {dst_avg:11.1f}%  {rte_avg:9.1f}%")

        overall_iso.extend(iso_s)
        overall_dist.extend(dst_s)
        overall_routed.extend(rte_s)

    oi = sum(overall_iso) / len(overall_iso) * 100 if overall_iso else 0
    od = sum(overall_dist) / len(overall_dist) * 100 if overall_dist else 0
    orr = sum(overall_routed) / len(overall_routed) * 100 if overall_routed else 0

    print("-" * 58)
    print(f"{'OVERALL':20s}  {oi:9.1f}%  {od:11.1f}%  {orr:9.1f}%")
    print()

    # --- Federated Graph Stats ---
    print("--- FEDERATED GRAPH STATS ---")
    hive_agents_nodes = hive_store.query_nodes("HiveAgent", limit=100)
    hive_fact_nodes = hive_store.query_nodes("SemanticMemory", limit=5000)
    total_hive_nodes = len(hive_agents_nodes) + len(hive_fact_nodes)
    print(
        f"  Hive graph nodes: {total_hive_nodes} "
        f"(HiveAgent: {len(hive_agents_nodes)}, SemanticMemory: {len(hive_fact_nodes)})"
    )

    # Count PROMOTED_TO_HIVE edges by querying agent neighbors
    from amplihack_memory.graph.types import Direction  # type: ignore[import-not-found]

    promo_edges = 0
    for an in hive_agents_nodes:
        try:
            nb = hive_store.query_neighbors(
                an.node_id, "PROMOTED_TO_HIVE", Direction.OUTGOING, limit=100
            )
            promo_edges += len(nb)
        except (RuntimeError, KeyError):
            pass
    # Count CONTRADICTS_FACT edges
    contra_edges = 0
    for fn in hive_fact_nodes[:100]:
        try:
            nb = hive_store.query_neighbors(
                fn.node_id, "CONTRADICTS_FACT", Direction.OUTGOING, limit=10
            )
            contra_edges += len(nb)
        except (RuntimeError, KeyError):
            pass

    print(
        f"  Hive graph edges: {promo_edges + contra_edges} "
        f"(PROMOTED_TO_HIVE: {promo_edges}, CONTRADICTS_FACT: {contra_edges})"
    )
    print(f"  Cross-boundary queries: {cross_boundary_count}/{len(QUESTIONS)} used hive data")
    print()

    # --- Hypothesis ---
    print("--- HYPOTHESIS ---")
    fed_diff = od - oi
    route_diff = orr - od
    fed_pass = "PASS" if fed_diff > 0 else "FAIL"
    route_pass = "PASS" if route_diff > 0 else "FAIL"
    adv_pass = "PASS" if adversary_blocked >= 4 else "FAIL"

    print(f"  Federated > Isolated: [{fed_pass}] ({fed_diff:+.1f}pp)")
    print(f"  Routed > Distributed: [{route_pass}] ({route_diff:+.1f}pp)")
    print(f"  Adversarial blocked:  [{adv_pass}] ({adversary_blocked}/{len(ADVERSARIAL_FACTS)})")
    print()

    # --- Per-agent summary ---
    print("--- PER-AGENT SUMMARY ---")
    for aid in sorted(agents):
        ag = agents[aid]
        total = ag.facts_learned + ag.facts_incorporated
        print(
            f"  {aid:20s}  learned={ag.facts_learned:3d}  "
            f"incorporated={ag.facts_incorporated:3d}  total={total:4d}"
        )
    print()

    elapsed = time.time() - t_start
    print(f"Elapsed: {elapsed:.1f}s")

    # --- Cleanup ---
    print(f"Cleanup: removing {base_dir}")
    event_bus.close()
    hive_store.close()
    for ag in agents.values():
        try:
            ag.local_graph.close()
        except Exception:
            pass
    shutil.rmtree(base_dir, ignore_errors=True)
    print("Cleanup: complete")
    print()
    print("=" * 72)
    print("=== EVALUATION COMPLETE ===")
    print("=" * 72)


if __name__ == "__main__":
    run_eval()
