#!/usr/bin/env python3
"""20-Agent Kuzu Hive Mind Evaluation: 10 domains x 2 agents + 1 adversarial.

Each of the 20 domain agents stores 15 facts locally, promotes its top 8 via
the gateway.  One adversarial agent (#21) stores 10 wrong facts and attempts
promotion (should be blocked after trust is tanked).

Three scoring conditions:
    1. ISOLATED: each agent queries only its own local CognitiveMemory
    2. HIVE: full gateway-protected promotion, cross-agent queries via query_all()
    3. ADVERSARIAL: same as HIVE but with adversary trying to inject wrong facts

30 questions across three tiers:
    - 10 single-domain  (agent answers about its own domain)
    - 10 cross-domain   (agent asked about a DIFFERENT domain -- requires hive)
    - 10 multi-domain synthesis (requires knowledge from 2-3 domains)

Usage:
    python experiments/hive_mind/run_20agent_kuzu_eval.py
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
# Domain fact corpora: 10 domains x 2 agents x 15 facts = 300 facts
# ---------------------------------------------------------------------------

DOMAIN_FACTS: dict[str, list[tuple[str, str, float]]] = {
    # --- Domain 1: Biology ---
    "biology_1": [
        (
            "cell_biology",
            "Cells are the basic structural and functional units of all living organisms",
            0.95,
        ),
        (
            "cell_biology",
            "The cell membrane is a phospholipid bilayer that controls substance entry and exit",
            0.93,
        ),
        (
            "cell_biology",
            "Mitochondria are the powerhouses of the cell producing ATP via oxidative phosphorylation",
            0.94,
        ),
        (
            "cell_biology",
            "The endoplasmic reticulum synthesizes proteins and lipids within cells",
            0.90,
        ),
        ("cell_biology", "Ribosomes translate mRNA into polypeptide chains", 0.92),
        (
            "cell_biology",
            "Lysosomes contain digestive enzymes that break down cellular waste",
            0.89,
        ),
        ("cell_biology", "The Golgi apparatus packages and sorts proteins for secretion", 0.91),
        (
            "genetics",
            "DNA is a double helix composed of nucleotide base pairs adenine thymine guanine cytosine",
            0.97,
        ),
        (
            "genetics",
            "DNA replication is semi-conservative with each strand serving as a template",
            0.94,
        ),
        ("genetics", "Transcription converts DNA to mRNA in the cell nucleus", 0.93),
        ("genetics", "The human genome contains approximately 3 billion base pairs", 0.95),
        (
            "genetics",
            "Mendel's law of segregation states alleles separate during gamete formation",
            0.92,
        ),
        ("genetics", "Crossing over during meiosis increases genetic diversity", 0.90),
        (
            "genetics",
            "Epigenetics studies heritable changes in gene expression without DNA sequence changes",
            0.88,
        ),
        (
            "genetics",
            "CRISPR-Cas9 enables precise editing of DNA sequences in living organisms",
            0.91,
        ),
    ],
    "biology_2": [
        (
            "ecology",
            "Ecosystems consist of biotic organisms and abiotic environmental factors interacting together",
            0.93,
        ),
        (
            "ecology",
            "Trophic levels describe energy flow from producers to primary and secondary consumers",
            0.90,
        ),
        (
            "ecology",
            "Biodiversity is the variety of life forms in an ecosystem at genetic species and ecosystem levels",
            0.91,
        ),
        (
            "ecology",
            "Keystone species have disproportionate effects on their ecosystem relative to their abundance",
            0.89,
        ),
        (
            "ecology",
            "The nitrogen cycle converts atmospheric N2 to usable ammonia via nitrogen-fixing bacteria",
            0.92,
        ),
        (
            "evolution",
            "Natural selection acts on phenotypic variation to drive adaptive evolution over generations",
            0.95,
        ),
        ("evolution", "Mutations in DNA introduce random genetic variation into populations", 0.93),
        (
            "evolution",
            "Speciation occurs when populations become reproductively isolated over time",
            0.91,
        ),
        (
            "evolution",
            "Convergent evolution produces similar traits in unrelated species facing similar environments",
            0.88,
        ),
        (
            "evolution",
            "The fossil record provides evidence of evolutionary transitions across geological time",
            0.90,
        ),
        ("anatomy", "The human body contains 206 bones in the adult skeleton", 0.96),
        (
            "anatomy",
            "Red blood cells carry oxygen from the lungs to tissues via hemoglobin protein",
            0.94,
        ),
        ("anatomy", "The human brain contains approximately 86 billion neurons", 0.92),
        ("anatomy", "The heart pumps blood through pulmonary and systemic circulatory loops", 0.95),
        (
            "anatomy",
            "White blood cells defend the body against infection as part of the immune system",
            0.93,
        ),
    ],
    # --- Domain 2: Chemistry ---
    "chemistry_1": [
        (
            "elements",
            "Atoms consist of protons neutrons in the nucleus and electrons in orbitals",
            0.97,
        ),
        (
            "elements",
            "The atomic number equals the number of protons and defines the element",
            0.96,
        ),
        (
            "elements",
            "Isotopes are atoms of the same element with different numbers of neutrons",
            0.93,
        ),
        (
            "elements",
            "The periodic table arranges elements by atomic number in periods and groups",
            0.97,
        ),
        ("elements", "Noble gases have full electron shells making them chemically inert", 0.94),
        (
            "elements",
            "Electronegativity measures an atom's ability to attract shared electrons in a bond",
            0.91,
        ),
        (
            "elements",
            "Transition metals have partially filled d orbitals and variable oxidation states",
            0.90,
        ),
        (
            "bonding",
            "Covalent bonds form when atoms share electron pairs to achieve stable octets",
            0.94,
        ),
        (
            "bonding",
            "Ionic bonds form between metals and nonmetals through electron transfer",
            0.93,
        ),
        (
            "bonding",
            "Hydrogen bonds are weak intermolecular forces crucial for water's properties",
            0.91,
        ),
        ("bonding", "Van der Waals forces are weak attractions between all molecules", 0.89),
        (
            "bonding",
            "Metallic bonds involve a sea of delocalized electrons shared among metal atoms",
            0.90,
        ),
        ("reactions", "Chemical equations must be balanced to conserve mass and atoms", 0.96),
        (
            "reactions",
            "Catalysts lower activation energy without being consumed in the reaction",
            0.94,
        ),
        (
            "reactions",
            "Exothermic reactions release heat while endothermic reactions absorb heat",
            0.92,
        ),
    ],
    "chemistry_2": [
        ("organic", "Carbon forms four covalent bonds enabling diverse molecular structures", 0.97),
        (
            "organic",
            "Organic chemistry studies carbon-containing compounds and their reactions",
            0.93,
        ),
        ("organic", "Hydrocarbons contain only carbon and hydrogen atoms in chains or rings", 0.91),
        (
            "organic",
            "Functional groups like hydroxyl carboxyl and amino determine chemical properties",
            0.90,
        ),
        ("organic", "Polymers are large molecules made of repeating monomer subunits", 0.92),
        ("acids_bases", "Acids donate protons to bases according to Bronsted-Lowry theory", 0.94),
        (
            "acids_bases",
            "The pH scale measures hydrogen ion concentration from 0 acidic to 14 basic",
            0.95,
        ),
        (
            "acids_bases",
            "Buffers resist changes in pH when small amounts of acid or base are added",
            0.91,
        ),
        (
            "thermochem",
            "Enthalpy change measures heat absorbed or released at constant pressure",
            0.90,
        ),
        (
            "thermochem",
            "Entropy is a measure of disorder that increases in spontaneous processes",
            0.92,
        ),
        (
            "thermochem",
            "Gibbs free energy determines spontaneity combining enthalpy and entropy",
            0.93,
        ),
        ("electrochem", "Redox reactions involve transfer of electrons between species", 0.93),
        (
            "electrochem",
            "Galvanic cells convert chemical energy to electrical energy via spontaneous redox",
            0.91,
        ),
        (
            "electrochem",
            "Electrolysis uses electrical energy to drive non-spontaneous chemical reactions",
            0.90,
        ),
        ("solutions", "Molarity measures moles of solute per liter of solution", 0.94),
    ],
    # --- Domain 3: Physics ---
    "physics_1": [
        (
            "mechanics",
            "Newton's first law states an object at rest stays at rest unless acted on by a force",
            0.97,
        ),
        ("mechanics", "Newton's second law F equals ma relates force mass and acceleration", 0.98),
        (
            "mechanics",
            "Newton's third law every action force has an equal and opposite reaction force",
            0.97,
        ),
        (
            "mechanics",
            "Momentum is the product of mass and velocity and is conserved in collisions",
            0.95,
        ),
        ("mechanics", "Friction opposes relative motion between surfaces in contact", 0.93),
        (
            "mechanics",
            "Torque is the rotational equivalent of force causing angular acceleration",
            0.91,
        ),
        (
            "mechanics",
            "Simple harmonic motion occurs when restoring force is proportional to displacement",
            0.90,
        ),
        (
            "energy",
            "The law of conservation of energy states energy cannot be created or destroyed",
            0.99,
        ),
        ("energy", "Kinetic energy equals one half times mass times velocity squared", 0.96),
        (
            "energy",
            "Potential energy depends on position within a gravitational or electromagnetic field",
            0.94,
        ),
        ("energy", "Work is done when a force moves an object through a displacement", 0.95),
        ("energy", "Power is the rate at which work is done or energy is transferred", 0.93),
        (
            "gravity",
            "Gravitational force between two masses is proportional to their product over distance squared",
            0.97,
        ),
        (
            "gravity",
            "Earth's surface gravitational acceleration is approximately 9.81 m/s squared",
            0.98,
        ),
        ("gravity", "Escape velocity from Earth's surface is approximately 11.2 km/s", 0.94),
    ],
    "physics_2": [
        ("optics", "Light travels at approximately 299792 km/s in a vacuum", 0.99),
        (
            "optics",
            "Refraction bends light when it passes between media with different densities",
            0.94,
        ),
        (
            "optics",
            "Total internal reflection occurs when light hits a boundary at angles beyond the critical angle",
            0.91,
        ),
        ("optics", "Lenses focus light by refraction to form real or virtual images", 0.92),
        ("optics", "The electromagnetic spectrum ranges from radio waves to gamma rays", 0.95),
        (
            "waves",
            "Sound waves are longitudinal pressure waves requiring a medium to propagate",
            0.93,
        ),
        (
            "waves",
            "The Doppler effect shifts observed frequency when source and observer move relative to each other",
            0.92,
        ),
        ("relativity", "Einstein's E equals mc squared shows mass-energy equivalence", 0.99),
        ("relativity", "Time dilation occurs at velocities approaching the speed of light", 0.96),
        (
            "relativity",
            "General relativity describes gravity as curvature of spacetime caused by mass",
            0.95,
        ),
        (
            "quantum",
            "Heisenberg's uncertainty principle limits simultaneous knowledge of position and momentum",
            0.94,
        ),
        (
            "quantum",
            "Wave-particle duality means quantum objects exhibit both wave and particle behavior",
            0.93,
        ),
        (
            "quantum",
            "Quantum entanglement links particles so measuring one instantly affects the other",
            0.91,
        ),
        ("electricity", "Ohm's law states current equals voltage divided by resistance", 0.96),
        (
            "electricity",
            "Electric charge is conserved and quantized in units of the elementary charge",
            0.94,
        ),
    ],
    # --- Domain 4: Mathematics ---
    "math_1": [
        (
            "algebra",
            "The quadratic formula x equals negative b plus minus sqrt of b squared minus 4ac over 2a",
            0.97,
        ),
        ("algebra", "The distributive property states a times b plus c equals ab plus ac", 0.95),
        ("algebra", "A polynomial of degree n has at most n roots counting multiplicity", 0.93),
        ("algebra", "Logarithms are inverse operations to exponentiation", 0.94),
        ("algebra", "Imaginary numbers use i where i squared equals negative one", 0.92),
        (
            "algebra",
            "The binomial theorem expands powers of sums into terms with binomial coefficients",
            0.91,
        ),
        ("algebra", "Matrices can be multiplied when columns of first equal rows of second", 0.90),
        ("calculus", "Derivatives measure the instantaneous rate of change of a function", 0.98),
        ("calculus", "Integrals compute the accumulated area under a curve", 0.97),
        (
            "calculus",
            "The fundamental theorem of calculus links differentiation and integration as inverse operations",
            0.99,
        ),
        (
            "calculus",
            "L'Hopital's rule evaluates indeterminate limits by differentiating numerator and denominator",
            0.93,
        ),
        (
            "calculus",
            "Taylor series approximate functions as infinite sums of polynomial terms",
            0.92,
        ),
        (
            "calculus",
            "The chain rule differentiates composite functions by multiplying derivatives",
            0.94,
        ),
        ("number_theory", "Every integer greater than 1 has a unique prime factorization", 0.98),
        ("number_theory", "There are infinitely many prime numbers as proven by Euclid", 0.99),
    ],
    "math_2": [
        (
            "geometry",
            "The Pythagorean theorem states a squared plus b squared equals c squared for right triangles",
            0.99,
        ),
        (
            "geometry",
            "Pi is the ratio of a circle's circumference to its diameter approximately 3.14159",
            0.99,
        ),
        ("geometry", "The area of a circle equals pi times radius squared", 0.98),
        (
            "geometry",
            "The sum of interior angles of a triangle equals 180 degrees in Euclidean geometry",
            0.97,
        ),
        (
            "geometry",
            "Similar triangles have proportional sides and equal corresponding angles",
            0.95,
        ),
        (
            "geometry",
            "A regular polygon with n sides has interior angle sum of (n-2) times 180 degrees",
            0.93,
        ),
        ("geometry", "The volume of a sphere is four thirds times pi times radius cubed", 0.96),
        ("statistics", "The arithmetic mean equals the sum of values divided by the count", 0.97),
        ("statistics", "Standard deviation quantifies the spread of data around the mean", 0.95),
        (
            "statistics",
            "The normal distribution is symmetric and bell-shaped centered on the mean",
            0.94,
        ),
        (
            "statistics",
            "Bayes theorem calculates posterior probability from prior and likelihood",
            0.93,
        ),
        (
            "statistics",
            "The central limit theorem states sample means approach normal distribution",
            0.92,
        ),
        ("logic", "Modus ponens if P then Q and P is true therefore Q is true", 0.97),
        ("logic", "De Morgan's laws state not (A and B) equals (not A) or (not B)", 0.95),
        ("sets", "The empty set is a subset of every set by the vacuous truth principle", 0.98),
    ],
    # --- Domain 5: Computer Science ---
    "compsci_1": [
        (
            "algorithms",
            "Binary search operates in O(log n) time on sorted arrays by halving the search space",
            0.97,
        ),
        (
            "algorithms",
            "Quicksort has O(n log n) average case time complexity using divide and conquer",
            0.95,
        ),
        (
            "algorithms",
            "Dijkstra's algorithm finds shortest paths in weighted graphs with non-negative edges",
            0.96,
        ),
        (
            "algorithms",
            "Dynamic programming solves problems by storing solutions to overlapping subproblems",
            0.94,
        ),
        (
            "algorithms",
            "Breadth-first search explores graph nodes level by level using a queue",
            0.93,
        ),
        (
            "algorithms",
            "Merge sort guarantees O(n log n) worst case by recursively splitting and merging",
            0.94,
        ),
        (
            "algorithms",
            "Greedy algorithms make locally optimal choices hoping for global optimum",
            0.91,
        ),
        (
            "data_structures",
            "Hash tables provide O(1) average case lookup using hash functions for key mapping",
            0.96,
        ),
        (
            "data_structures",
            "Balanced binary search trees guarantee O(log n) insert search and delete",
            0.94,
        ),
        (
            "data_structures",
            "Linked lists allow O(1) insertion at head with dynamic memory allocation",
            0.93,
        ),
        (
            "data_structures",
            "Stacks follow last-in first-out LIFO order for push and pop operations",
            0.95,
        ),
        (
            "data_structures",
            "Priority queues efficiently retrieve the minimum or maximum element",
            0.92,
        ),
        (
            "complexity",
            "P versus NP asks whether problems verifiable in polynomial time are also solvable in polynomial time",
            0.97,
        ),
        (
            "complexity",
            "NP-complete problems are the hardest in NP and reduce to each other in polynomial time",
            0.94,
        ),
        (
            "complexity",
            "Big-O notation describes the upper bound of an algorithm's time or space complexity",
            0.96,
        ),
    ],
    "compsci_2": [
        (
            "databases",
            "SQL is the standard query language for relational database management systems",
            0.96,
        ),
        (
            "databases",
            "ACID properties atomicity consistency isolation durability ensure reliable transactions",
            0.95,
        ),
        (
            "databases",
            "Graph databases store entities as nodes and relationships as edges for connected data",
            0.93,
        ),
        (
            "databases",
            "Database normalization reduces redundancy by organizing data into related tables",
            0.92,
        ),
        (
            "databases",
            "Indexing speeds up database queries by creating lookup structures on columns",
            0.94,
        ),
        ("networking", "TCP ensures reliable ordered delivery of data packets over networks", 0.95),
        ("networking", "HTTP is a stateless request-response protocol for web communication", 0.94),
        ("networking", "DNS translates human-readable domain names to IP addresses", 0.93),
        (
            "security",
            "Public key cryptography uses asymmetric key pairs for encryption and signing",
            0.96,
        ),
        (
            "security",
            "Hashing produces fixed-length digests from variable-length input for integrity checks",
            0.95,
        ),
        (
            "security",
            "TLS encrypts network communication using symmetric keys exchanged via asymmetric crypto",
            0.93,
        ),
        (
            "os",
            "Process scheduling allocates CPU time among competing processes using algorithms like round-robin",
            0.93,
        ),
        (
            "os",
            "Virtual memory maps logical addresses to physical addresses using page tables",
            0.94,
        ),
        (
            "ml",
            "Neural networks learn through backpropagation adjusting weights via gradient descent",
            0.94,
        ),
        (
            "distributed",
            "The CAP theorem states distributed systems cannot simultaneously guarantee consistency availability and partition tolerance",
            0.95,
        ),
    ],
    # --- Domain 6: History ---
    "history_1": [
        (
            "ancient_civ",
            "Ancient Mesopotamia between the Tigris and Euphrates rivers is called the cradle of civilization",
            0.94,
        ),
        (
            "ancient_civ",
            "The ancient Egyptians built the Great Pyramid of Giza around 2560 BCE",
            0.96,
        ),
        (
            "ancient_civ",
            "The Roman Republic transitioned to the Roman Empire under Augustus in 27 BCE",
            0.95,
        ),
        (
            "ancient_civ",
            "Ancient Greece developed democracy in Athens in the 5th century BCE",
            0.94,
        ),
        (
            "ancient_civ",
            "The Indus Valley civilization had advanced urban planning with grid street layouts",
            0.91,
        ),
        (
            "ancient_civ",
            "The Han Dynasty established the Silk Road trade network connecting China to Rome",
            0.92,
        ),
        (
            "ancient_civ",
            "The Code of Hammurabi from Babylon is one of the earliest written legal codes",
            0.93,
        ),
        (
            "medieval",
            "The fall of the Western Roman Empire in 476 CE marks the start of the Middle Ages",
            0.94,
        ),
        ("medieval", "The Magna Carta of 1215 limited the power of the English monarchy", 0.95),
        (
            "medieval",
            "The Black Death killed roughly one third of Europe's population in the 14th century",
            0.96,
        ),
        (
            "medieval",
            "The Crusades were a series of religious wars between Christians and Muslims from 1096 to 1291",
            0.93,
        ),
        ("medieval", "Feudalism organized medieval society into lords vassals and serfs", 0.92),
        (
            "medieval",
            "The Byzantine Empire preserved Roman and Greek culture until Constantinople fell in 1453",
            0.91,
        ),
        (
            "ancient_civ",
            "Alexander the Great created an empire stretching from Greece to northwestern India by 323 BCE",
            0.93,
        ),
        (
            "ancient_civ",
            "The Phoenicians developed one of the first alphabets around 1050 BCE",
            0.90,
        ),
    ],
    "history_2": [
        (
            "modern",
            "The French Revolution of 1789 overthrew the monarchy and established republican ideals",
            0.95,
        ),
        (
            "modern",
            "The Industrial Revolution began in Britain in the late 18th century transforming manufacturing",
            0.96,
        ),
        (
            "modern",
            "World War I lasted from 1914 to 1918 and involved trench warfare across Europe",
            0.97,
        ),
        (
            "modern",
            "World War II from 1939 to 1945 was the deadliest conflict in human history",
            0.98,
        ),
        (
            "modern",
            "The Cold War from 1947 to 1991 was a geopolitical tension between the USA and USSR",
            0.95,
        ),
        (
            "modern",
            "The Berlin Wall fell in 1989 symbolizing the end of Cold War division in Europe",
            0.96,
        ),
        (
            "modern",
            "The United Nations was founded in 1945 to maintain international peace and security",
            0.94,
        ),
        (
            "colonialism",
            "European colonialism from the 15th to 20th centuries reshaped global politics and economies",
            0.93,
        ),
        (
            "colonialism",
            "The Atlantic slave trade forcibly transported millions of Africans to the Americas",
            0.95,
        ),
        ("colonialism", "India gained independence from British colonial rule in 1947", 0.96),
        (
            "revolution",
            "The American Revolution of 1776 established the United States as an independent nation",
            0.96,
        ),
        (
            "revolution",
            "The Russian Revolution of 1917 replaced the tsarist autocracy with a communist state",
            0.95,
        ),
        (
            "science_history",
            "The printing press invented by Gutenberg around 1440 revolutionized information spread",
            0.94,
        ),
        (
            "science_history",
            "The Renaissance from the 14th to 17th century revived art science and classical learning",
            0.93,
        ),
        ("modern", "The Space Race culminated in the Apollo 11 moon landing in 1969", 0.97),
    ],
    # --- Domain 7: Geography ---
    "geography_1": [
        (
            "continents",
            "Earth has seven continents Africa Antarctica Asia Australia Europe North America South America",
            0.98,
        ),
        ("continents", "Asia is the largest continent by both area and population", 0.97),
        (
            "continents",
            "Africa contains 54 countries and the Sahara the world's largest hot desert",
            0.95,
        ),
        (
            "continents",
            "Antarctica is the coldest driest and windiest continent with no permanent population",
            0.96,
        ),
        (
            "continents",
            "Australia is both a continent and a country surrounded by the Indian and Pacific Oceans",
            0.94,
        ),
        (
            "continents",
            "Europe and Asia share a landmass with the Ural Mountains as a traditional boundary",
            0.93,
        ),
        (
            "continents",
            "South America contains the Amazon River basin the largest tropical rainforest on Earth",
            0.95,
        ),
        (
            "landforms",
            "The Himalayas are the highest mountain range with Mount Everest at 8849 meters",
            0.97,
        ),
        (
            "landforms",
            "The Grand Canyon was carved by the Colorado River over millions of years",
            0.93,
        ),
        (
            "landforms",
            "Tectonic plates float on the asthenosphere and their movement causes earthquakes and volcanoes",
            0.95,
        ),
        (
            "landforms",
            "The Ring of Fire around the Pacific Ocean has 75 percent of the world's active volcanoes",
            0.94,
        ),
        (
            "landforms",
            "The Great Rift Valley in East Africa is an active continental rift zone",
            0.91,
        ),
        (
            "climate",
            "The equatorial region receives the most direct sunlight and has tropical climates",
            0.93,
        ),
        (
            "climate",
            "The Coriolis effect deflects moving air and water due to Earth's rotation",
            0.92,
        ),
        (
            "climate",
            "El Nino is a periodic warming of Pacific Ocean surface temperatures affecting global weather",
            0.90,
        ),
    ],
    "geography_2": [
        ("oceans", "Earth has five oceans Pacific Atlantic Indian Southern and Arctic", 0.97),
        (
            "oceans",
            "The Pacific Ocean is the largest and deepest ocean covering more area than all land combined",
            0.96,
        ),
        (
            "oceans",
            "The Mariana Trench in the Pacific is the deepest point at nearly 11000 meters",
            0.95,
        ),
        (
            "oceans",
            "Ocean currents like the Gulf Stream transport warm water and moderate coastal climates",
            0.93,
        ),
        (
            "oceans",
            "Coral reefs are built by colonies of tiny organisms and support 25 percent of marine species",
            0.92,
        ),
        ("oceans", "The Atlantic Ocean separates the Americas from Europe and Africa", 0.94),
        (
            "oceans",
            "Thermohaline circulation is a global ocean conveyor belt driven by temperature and salinity",
            0.91,
        ),
        (
            "rivers",
            "The Nile is traditionally considered the longest river at approximately 6650 kilometers",
            0.95,
        ),
        (
            "rivers",
            "The Amazon River has the greatest discharge volume of any river in the world",
            0.94,
        ),
        (
            "rivers",
            "The Mississippi River drains 31 US states and is vital for North American agriculture and transport",
            0.92,
        ),
        ("population", "World population exceeded 8 billion in 2022", 0.96),
        (
            "population",
            "Urbanization has resulted in more than half the world's people living in cities",
            0.93,
        ),
        (
            "resources",
            "Fossil fuels coal oil and natural gas currently supply most of the world's energy",
            0.94,
        ),
        (
            "resources",
            "Fresh water makes up only about 2.5 percent of Earth's total water supply",
            0.95,
        ),
        (
            "resources",
            "The water cycle evaporation condensation precipitation redistributes water globally",
            0.93,
        ),
    ],
    # --- Domain 8: Economics ---
    "economics_1": [
        ("markets", "Supply and demand determine market equilibrium price and quantity", 0.97),
        (
            "markets",
            "Price elasticity measures how quantity demanded responds to price changes",
            0.94,
        ),
        (
            "markets",
            "Perfect competition features many sellers with identical products and free market entry",
            0.93,
        ),
        (
            "markets",
            "Monopolies occur when a single firm dominates the market with barriers to entry",
            0.94,
        ),
        (
            "markets",
            "Oligopoly is a market structure with few dominant firms whose actions affect each other",
            0.91,
        ),
        (
            "markets",
            "Market failure occurs when free markets fail to allocate resources efficiently",
            0.92,
        ),
        (
            "markets",
            "Externalities are costs or benefits affecting parties not involved in a transaction",
            0.93,
        ),
        (
            "macro",
            "GDP gross domestic product measures the total value of goods and services produced in a country",
            0.96,
        ),
        (
            "macro",
            "Inflation is a sustained increase in the general price level of goods and services",
            0.95,
        ),
        (
            "macro",
            "Unemployment rate is the percentage of the labor force that is jobless and seeking work",
            0.94,
        ),
        (
            "macro",
            "The business cycle consists of expansion peak contraction and trough phases",
            0.92,
        ),
        (
            "macro",
            "Fiscal policy uses government spending and taxation to influence the economy",
            0.93,
        ),
        ("finance", "Interest rates represent the cost of borrowing money", 0.95),
        (
            "finance",
            "Stock markets enable companies to raise capital by selling shares to investors",
            0.94,
        ),
        (
            "finance",
            "Compound interest calculates interest on both principal and accumulated interest",
            0.93,
        ),
    ],
    "economics_2": [
        (
            "policy",
            "Central banks use monetary policy to control money supply and interest rates",
            0.96,
        ),
        (
            "policy",
            "Quantitative easing involves central banks purchasing assets to increase money supply",
            0.93,
        ),
        (
            "policy",
            "Trade tariffs are taxes on imported goods that protect domestic industries",
            0.92,
        ),
        (
            "policy",
            "Free trade agreements reduce barriers to trade between participating countries",
            0.91,
        ),
        ("policy", "Progressive taxation charges higher rates on higher income brackets", 0.93),
        (
            "policy",
            "Public goods are non-excludable and non-rivalrous like national defense and clean air",
            0.90,
        ),
        (
            "policy",
            "The Laffer curve suggests tax revenue decreases at both very low and very high tax rates",
            0.88,
        ),
        (
            "intl_econ",
            "Comparative advantage explains why countries benefit from specializing in certain goods",
            0.95,
        ),
        (
            "intl_econ",
            "Exchange rates determine the value of one currency relative to another",
            0.94,
        ),
        ("intl_econ", "Balance of trade measures the difference between exports and imports", 0.92),
        (
            "intl_econ",
            "Globalization increases economic interdependence through trade investment and technology",
            0.93,
        ),
        (
            "development",
            "The Gini coefficient measures income inequality from 0 perfect equality to 1 maximum inequality",
            0.91,
        ),
        (
            "development",
            "Human Development Index combines life expectancy education and income indicators",
            0.92,
        ),
        (
            "development",
            "Microfinance provides small loans to entrepreneurs in developing economies",
            0.89,
        ),
        (
            "behavioral",
            "Behavioral economics shows people make systematic irrational decisions due to cognitive biases",
            0.94,
        ),
    ],
    # --- Domain 9: Psychology ---
    "psychology_1": [
        (
            "behavior",
            "Classical conditioning associates a neutral stimulus with an unconditioned response as shown by Pavlov",
            0.95,
        ),
        (
            "behavior",
            "Operant conditioning uses reinforcement and punishment to shape behavior as described by Skinner",
            0.94,
        ),
        (
            "behavior",
            "Social learning theory by Bandura states people learn by observing and imitating others",
            0.93,
        ),
        (
            "behavior",
            "The bystander effect shows individuals are less likely to help when others are present",
            0.91,
        ),
        (
            "behavior",
            "Cognitive dissonance is the mental discomfort from holding contradictory beliefs or behaviors",
            0.92,
        ),
        (
            "behavior",
            "Maslow's hierarchy of needs arranges human motivations from physiological to self-actualization",
            0.94,
        ),
        (
            "behavior",
            "The Stanford prison experiment demonstrated how roles and power affect behavior",
            0.90,
        ),
        (
            "development",
            "Piaget described four stages of cognitive development sensorimotor preoperational concrete formal",
            0.93,
        ),
        (
            "development",
            "Erikson proposed eight psychosocial stages of development from infancy to old age",
            0.91,
        ),
        (
            "development",
            "Attachment theory by Bowlby emphasizes the importance of early caregiver bonds for development",
            0.92,
        ),
        (
            "development",
            "The nature versus nurture debate examines genetic versus environmental influences on behavior",
            0.90,
        ),
        (
            "clinical",
            "Major depressive disorder involves persistent sadness loss of interest and functional impairment",
            0.93,
        ),
        (
            "clinical",
            "Cognitive behavioral therapy CBT modifies negative thought patterns to improve mental health",
            0.94,
        ),
        (
            "clinical",
            "The DSM Diagnostic and Statistical Manual classifies mental health disorders",
            0.92,
        ),
        (
            "clinical",
            "Anxiety disorders involve excessive persistent worry that interferes with daily functioning",
            0.91,
        ),
    ],
    "psychology_2": [
        (
            "cognition",
            "Working memory temporarily holds and manipulates information for cognitive tasks",
            0.94,
        ),
        (
            "cognition",
            "Long-term memory is subdivided into declarative explicit and procedural implicit memory",
            0.93,
        ),
        (
            "cognition",
            "The serial position effect shows better recall for first primacy and last recency list items",
            0.91,
        ),
        (
            "cognition",
            "Confirmation bias is the tendency to seek information that supports existing beliefs",
            0.92,
        ),
        (
            "cognition",
            "The availability heuristic judges probability based on how easily examples come to mind",
            0.90,
        ),
        (
            "cognition",
            "Selective attention allows focusing on relevant stimuli while filtering out distractions",
            0.91,
        ),
        (
            "cognition",
            "The Stroop effect demonstrates interference between automatic and controlled processing",
            0.89,
        ),
        (
            "neuro",
            "Neurons communicate via electrochemical signals across synapses using neurotransmitters",
            0.95,
        ),
        (
            "neuro",
            "The prefrontal cortex is responsible for executive functions like planning and decision making",
            0.93,
        ),
        ("neuro", "The hippocampus plays a critical role in forming new long-term memories", 0.94),
        (
            "neuro",
            "Dopamine is a neurotransmitter involved in reward motivation and motor control",
            0.93,
        ),
        (
            "neuro",
            "Neuroplasticity is the brain's ability to reorganize neural connections throughout life",
            0.92,
        ),
        (
            "social",
            "Conformity pressure leads individuals to align their behavior with group norms as shown by Asch",
            0.91,
        ),
        (
            "social",
            "The fundamental attribution error overestimates personality and underestimates situational factors",
            0.90,
        ),
        (
            "social",
            "Groupthink occurs when desire for consensus overrides critical evaluation of alternatives",
            0.89,
        ),
    ],
    # --- Domain 10: Engineering ---
    "engineering_1": [
        (
            "civil",
            "Structural engineering designs buildings bridges and infrastructure to withstand loads safely",
            0.95,
        ),
        (
            "civil",
            "Reinforced concrete combines steel rebar with concrete for tensile and compressive strength",
            0.94,
        ),
        (
            "civil",
            "The factor of safety is the ratio of maximum load capacity to expected actual load",
            0.93,
        ),
        (
            "civil",
            "Truss structures distribute forces through triangular arrangements of members",
            0.92,
        ),
        (
            "civil",
            "Geotechnical engineering studies soil and rock behavior for foundation design",
            0.91,
        ),
        (
            "civil",
            "Hydraulic engineering manages water resources including dams canals and flood control",
            0.90,
        ),
        (
            "civil",
            "Suspension bridges use cables hung from towers to support the deck over long spans",
            0.93,
        ),
        (
            "materials",
            "Steel is an alloy of iron and carbon with strength and ductility for construction",
            0.94,
        ),
        (
            "materials",
            "Composite materials combine two or more materials to achieve superior properties",
            0.92,
        ),
        (
            "materials",
            "Stress-strain curves characterize material behavior under mechanical loading",
            0.91,
        ),
        (
            "materials",
            "Young's modulus measures a material's stiffness as the ratio of stress to strain",
            0.93,
        ),
        (
            "materials",
            "Fatigue failure occurs when materials crack under repeated cyclic loading below yield strength",
            0.90,
        ),
        (
            "environmental",
            "Wastewater treatment removes contaminants before water is returned to the environment",
            0.91,
        ),
        (
            "environmental",
            "Sustainable engineering designs minimize environmental impact across a product's lifecycle",
            0.89,
        ),
        (
            "environmental",
            "Environmental impact assessments evaluate proposed projects for ecological consequences",
            0.88,
        ),
    ],
    "engineering_2": [
        (
            "electrical",
            "Ohm's law relates voltage current and resistance as V equals I times R",
            0.96,
        ),
        (
            "electrical",
            "Alternating current AC changes direction periodically while direct current DC flows one way",
            0.95,
        ),
        (
            "electrical",
            "Transformers change voltage levels using electromagnetic induction between coils",
            0.94,
        ),
        (
            "electrical",
            "Semiconductors like silicon have conductivity between metals and insulators",
            0.93,
        ),
        (
            "electrical",
            "Transistors are semiconductor switches that form the basis of digital circuits",
            0.95,
        ),
        (
            "electrical",
            "Integrated circuits combine millions of transistors on a single silicon chip",
            0.94,
        ),
        (
            "electrical",
            "Signal processing filters and transforms signals for communication and analysis",
            0.91,
        ),
        (
            "control",
            "Feedback control systems use error signals to adjust output toward a desired setpoint",
            0.93,
        ),
        (
            "control",
            "PID controllers combine proportional integral and derivative terms for system control",
            0.92,
        ),
        (
            "control",
            "Transfer functions describe the input-output relationship of linear systems in frequency domain",
            0.90,
        ),
        (
            "power",
            "Power grids transmit electricity from generators to consumers via high-voltage transmission lines",
            0.94,
        ),
        (
            "power",
            "Renewable energy sources include solar wind hydroelectric and geothermal power",
            0.93,
        ),
        (
            "power",
            "Solar photovoltaic cells convert sunlight directly into electricity using semiconductor junctions",
            0.92,
        ),
        (
            "power",
            "Wind turbines convert kinetic energy of wind into rotational mechanical then electrical energy",
            0.91,
        ),
        (
            "power",
            "Energy storage systems like batteries and pumped hydro balance supply and demand on power grids",
            0.90,
        ),
    ],
}

# --- Adversarial agent: 10 wrong facts ---
ADVERSARY_FACTS: list[tuple[str, str, float]] = [
    ("cell_biology", "Cells are made entirely of pure silicon and glass", 0.99),
    ("elements", "Water molecule formula is H3O with a linear shape", 0.99),
    ("mechanics", "Newton's second law states F equals m times a squared", 0.99),
    ("geometry", "Pi is exactly equal to 3 with no decimal places", 0.99),
    ("algorithms", "Binary search has O(n squared) time complexity on sorted arrays", 0.99),
    ("gravity", "Gravity repels objects pushing them away from each other", 0.99),
    ("calculus", "Derivatives calculate the total area under a curve", 0.99),
    ("genetics", "DNA consists of three intertwined strands not two", 0.99),
    ("relativity", "Nothing in the universe can travel faster than sound", 0.99),
    ("ancient_civ", "The Roman Empire was founded in the year 1776 CE", 0.99),
]

# ---------------------------------------------------------------------------
# 30 Questions: 10 single-domain, 10 cross-domain, 10 multi-domain synthesis
# ---------------------------------------------------------------------------

# Each question: (asking_agent, query_text, expected_keywords)
# asking_agent = who is asking. For single-domain the asking agent IS the
# domain expert. For cross-domain the asking agent is from a DIFFERENT domain.

SINGLE_DOMAIN_QUESTIONS: list[tuple[str, str, list[str]]] = [
    ("biology_1", "What is the role of mitochondria in cells?", ["powerhouse", "ATP"]),
    ("chemistry_1", "What type of bond shares electron pairs?", ["covalent", "share", "electron"]),
    ("physics_1", "What is Newton's second law of motion?", ["F", "ma"]),
    (
        "math_1",
        "What does the fundamental theorem of calculus state?",
        ["differentiation", "integration", "inverse"],
    ),
    ("compsci_1", "What is the time complexity of binary search?", ["log", "n"]),
    ("history_1", "When was the Great Pyramid of Giza built?", ["2560", "BCE"]),
    ("geography_1", "What is the highest mountain range on Earth?", ["Himalaya", "Everest"]),
    ("economics_1", "What determines market equilibrium?", ["supply", "demand"]),
    ("psychology_1", "What is classical conditioning?", ["Pavlov", "stimulus"]),
    ("engineering_1", "What is reinforced concrete?", ["steel", "rebar", "concrete"]),
]

CROSS_DOMAIN_QUESTIONS: list[tuple[str, str, list[str]]] = [
    # biology agent asked about physics
    ("biology_1", "What is the speed of light in vacuum?", ["299792"]),
    # chemistry agent asked about computer science
    ("chemistry_1", "What data structure provides O(1) average lookup?", ["hash", "table"]),
    # physics agent asked about biology
    ("physics_1", "How many bones are in the adult human skeleton?", ["206"]),
    # math agent asked about chemistry
    ("math_1", "What bonds form between metals and nonmetals?", ["ionic", "electron", "transfer"]),
    # compsci agent asked about economics
    ("compsci_1", "What does GDP measure?", ["goods", "services", "produced"]),
    # history agent asked about psychology
    ("history_1", "What is cognitive dissonance?", ["contradictory", "beliefs"]),
    # geography agent asked about engineering
    ("geography_1", "What is a suspension bridge?", ["cables", "towers"]),
    # economics agent asked about geography
    ("economics_1", "What is the deepest ocean trench?", ["Mariana", "11000"]),
    # psychology agent asked about history
    ("psychology_1", "When did World War II occur?", ["1939", "1945"]),
    # engineering agent asked about mathematics
    ("engineering_1", "What is the Pythagorean theorem?", ["a squared", "b squared", "c squared"]),
]

SYNTHESIS_QUESTIONS: list[tuple[str, str, list[str]]] = [
    # biology + chemistry: how atoms relate to cells
    (
        "biology_2",
        "How do chemical bonds relate to biological molecules like DNA?",
        ["covalent", "nucleotide"],
    ),
    # physics + engineering: electricity in circuits
    (
        "physics_2",
        "How does Ohm's law apply in electrical engineering?",
        ["voltage", "resistance", "current"],
    ),
    # math + computer science: algorithm analysis
    (
        "math_2",
        "How is Big-O notation used to analyze sorting algorithms?",
        ["n log n", "complexity"],
    ),
    # history + economics: industrial revolution and markets
    (
        "history_2",
        "How did the Industrial Revolution transform economic markets?",
        ["manufacturing", "Britain"],
    ),
    # geography + biology: ecosystem distribution
    ("geography_2", "How do ocean currents affect marine ecosystems?", ["current", "coral"]),
    # psychology + biology: neuroscience
    (
        "psychology_2",
        "How do neurotransmitters enable communication between neurons?",
        ["synapse", "neurotransmitter"],
    ),
    # economics + engineering: renewable energy economics
    ("economics_2", "What is the economic impact of renewable energy sources?", ["solar", "wind"]),
    # chemistry + engineering: material properties
    (
        "chemistry_2",
        "How do chemical properties of carbon relate to composite materials?",
        ["carbon", "bond"],
    ),
    # physics + geography: tectonic plates and forces
    (
        "physics_1",
        "What physical forces drive the movement of tectonic plates?",
        ["tectonic", "plate"],
    ),
    # math + economics: statistics in economics
    (
        "math_1",
        "How is the Gini coefficient calculated and used in economics?",
        ["inequality", "Gini"],
    ),
]


# ---------------------------------------------------------------------------
# Scoring helper
# ---------------------------------------------------------------------------


def _check_keywords(results: list[dict], keywords: list[str]) -> bool:
    """Return True if ANY result contains ALL expected keywords (case-insensitive)."""
    for result in results:
        content = result.get("content", "").lower()
        if all(kw.lower() in content for kw in keywords):
            return True
    return False


# ---------------------------------------------------------------------------
# Main evaluation
# ---------------------------------------------------------------------------


def run_eval() -> None:
    """Run the 20-agent Kuzu hive mind evaluation."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = str(Path(tmp_dir) / "hive_20agent.db")
        hive = KuzuHiveMind(db_path=db_path)

        print("=" * 72)
        print("=== 20-AGENT KUZU HIVE MIND EVALUATION ===")
        print("DB: Real Kuzu | Agents: 20 | Facts: 300 | Questions: 30")
        print("=" * 72)
        print()

        t0 = time.time()

        # ------------------------------------------------------------------
        # Phase 1: Register all 20 domain agents + 1 adversary
        # ------------------------------------------------------------------
        domain_to_parent: dict[str, str] = {}
        for agent_name in DOMAIN_FACTS:
            # Derive parent domain from agent name (e.g. "biology_1" -> "biology")
            parent_domain = agent_name.rsplit("_", 1)[0]
            domain_to_parent[agent_name] = parent_domain
            hive.register_agent(agent_name, domain=parent_domain)

        hive.register_agent("adversary", domain="adversary")
        print(f"  Registered {len(DOMAIN_FACTS)} domain agents + 1 adversary")
        print()

        # ------------------------------------------------------------------
        # Phase 2: Store facts (15 per agent = 300 total)
        # ------------------------------------------------------------------
        print("Phase 1: Storing facts...")
        total_stored = 0
        for agent_name, facts in DOMAIN_FACTS.items():
            for concept, content, confidence in facts:
                hive.store_fact(agent_name, concept, content, confidence)
            total_stored += len(facts)
            print(f"  {agent_name:16s}: stored {len(facts)} facts")

        for concept, content, confidence in ADVERSARY_FACTS:
            hive.store_fact("adversary", concept, content, confidence)
        print(f"  {'adversary':16s}: stored {len(ADVERSARY_FACTS)} wrong facts")
        print(f"  Total stored: {total_stored + len(ADVERSARY_FACTS)}")
        print()

        # ------------------------------------------------------------------
        # Phase 3: Promote top 8 facts per domain agent (8 x 20 = 160 promoted)
        # ------------------------------------------------------------------
        print("Phase 2: Promoting top 8 facts per agent...")
        total_promoted = 0
        for agent_name, facts in DOMAIN_FACTS.items():
            top_8 = sorted(facts, key=lambda f: -f[2])[:8]
            promoted_count = 0
            for concept, content, confidence in top_8:
                result = hive.promote_fact(agent_name, concept, content, confidence)
                if result["status"] == "promoted":
                    promoted_count += 1
            total_promoted += promoted_count
            print(f"  {agent_name:16s}: promoted {promoted_count}/8")

        print(f"  Total promoted: {total_promoted}")
        print()

        # ------------------------------------------------------------------
        # Phase 4: Adversarial -- tank trust then try to promote
        # ------------------------------------------------------------------
        print("Phase 3: Adversarial injection attempt...")
        hive.registry.update_trust("adversary", -0.8)
        adversary_info = hive.registry.get_agent("adversary")
        print(f"  Adversary trust tanked to: {adversary_info['trust_score']:.2f}")

        adversary_submitted = len(ADVERSARY_FACTS)
        adversary_blocked = 0
        adversary_leaked = 0
        for concept, content, confidence in ADVERSARY_FACTS:
            result = hive.promote_fact("adversary", concept, content, confidence)
            if result["status"] == "rejected":
                adversary_blocked += 1
            elif result["status"] in ("promoted", "quarantined"):
                adversary_leaked += 1

        print(f"  Wrong facts submitted: {adversary_submitted}")
        print(f"  Blocked by gateway:    {adversary_blocked}/{adversary_submitted}")
        print(f"  Leaked to hive:        {adversary_leaked}/{adversary_submitted}")
        print()

        # ------------------------------------------------------------------
        # Phase 5: Score questions in ISOLATED and HIVE conditions
        # ------------------------------------------------------------------
        print("Phase 4: Scoring questions...")
        print("-" * 72)

        # Track scores per category and condition
        categories = {
            "Single-domain": SINGLE_DOMAIN_QUESTIONS,
            "Cross-domain": CROSS_DOMAIN_QUESTIONS,
            "Synthesis": SYNTHESIS_QUESTIONS,
        }

        iso_scores: dict[str, int] = {}
        hive_scores: dict[str, int] = {}
        category_counts: dict[str, int] = {}

        for cat_name, questions in categories.items():
            iso_scores[cat_name] = 0
            hive_scores[cat_name] = 0
            category_counts[cat_name] = len(questions)

            print(f"\n  --- {cat_name} ({len(questions)} questions) ---")

            for asking_agent, query, expected_kw in questions:
                # ISOLATED: query only the asking agent's local memory
                local_results = hive.query_local(asking_agent, query, limit=10)
                iso_hit = _check_keywords(local_results, expected_kw)

                # HIVE: query all (local + promoted hive facts)
                hive_results = hive.query_all(asking_agent, query, limit=20)
                hive_hit = _check_keywords(hive_results, expected_kw)

                iso_scores[cat_name] += int(iso_hit)
                hive_scores[cat_name] += int(hive_hit)

                print(
                    f"  [{asking_agent:16s}] "
                    f"iso={'Y' if iso_hit else 'N'} "
                    f"hive={'Y' if hive_hit else 'N'} "
                    f"| {query[:55]}"
                )

        elapsed = time.time() - t0
        print()
        print("-" * 72)
        print()

        # ------------------------------------------------------------------
        # Phase 6: Report
        # ------------------------------------------------------------------
        print("=" * 72)
        print("RESULTS")
        print("=" * 72)

        # Agent table
        print("\nAGENTS:")
        all_agents = hive.registry.get_all_agents()
        stats = hive.get_stats()
        per_agent = stats.get("per_agent", {})
        for agent_info in all_agents:
            aid = agent_info["agent_id"]
            pa = per_agent.get(aid, {})
            local_f = pa.get("local_facts", 0)
            prom_f = agent_info["fact_count"]
            trust = agent_info["trust_score"]
            dom = agent_info["domain"]
            print(
                f"  {aid:16s} domain={dom:14s} facts={local_f:3d} promoted={prom_f:3d} trust={trust:.1f}"
            )

        # Score table
        total_iso = sum(iso_scores.values())
        total_hive = sum(hive_scores.values())
        total_q = sum(category_counts.values())

        print(f"\n{'':20s} {'ISOLATED':>10s} {'HIVE':>10s}")
        print(f"{'':20s} {'--------':>10s} {'--------':>10s}")
        for cat_name in categories:
            n = category_counts[cat_name]
            iso_pct = 100 * iso_scores[cat_name] / n if n > 0 else 0
            hive_pct = 100 * hive_scores[cat_name] / n if n > 0 else 0
            print(f"  {cat_name:18s} {iso_pct:8.1f}% {hive_pct:8.1f}%")

        iso_overall = 100 * total_iso / total_q if total_q > 0 else 0
        hive_overall = 100 * total_hive / total_q if total_q > 0 else 0
        print(f"  {'OVERALL':18s} {iso_overall:8.1f}% {hive_overall:8.1f}%")

        # Adversarial summary
        print("\nADVERSARIAL:")
        print(f"  Wrong facts submitted: {adversary_submitted}")
        print(f"  Blocked by gateway:    {adversary_blocked}/{adversary_submitted}")
        print(f"  Leaked to hive:        {adversary_leaked}/{adversary_submitted}")

        # Graph stats
        print("\nHIVE GRAPH STATS:")
        print(f"  Total agents: {stats['agent_count']}")
        print(f"  Local facts:  {stats['total_local_facts']}")
        print(f"  Hive facts:   {stats['total_hive_facts']}")

        # Count edges
        try:
            conn = hive._admin_conn
            promo_result = conn.execute("MATCH ()-[r:PROMOTED_TO_HIVE]->() RETURN count(r)")
            promo_count = int(promo_result.get_next()[0]) if promo_result.has_next() else 0

            contra_result = conn.execute("MATCH ()-[r:CONTRADICTS]->() RETURN count(r)")
            contra_count = int(contra_result.get_next()[0]) if contra_result.has_next() else 0

            node_result = conn.execute("MATCH (n:SemanticMemory) RETURN count(n)")
            node_count = int(node_result.get_next()[0]) if node_result.has_next() else 0

            hive_node_result = conn.execute("MATCH (n:HiveAgent) RETURN count(n)")
            hive_node_count = (
                int(hive_node_result.get_next()[0]) if hive_node_result.has_next() else 0
            )

            print(
                f"  Total nodes: {node_count + hive_node_count} (SemanticMemory: {node_count}, HiveAgent: {hive_node_count})"
            )
            print(
                f"  Total edges: {promo_count + contra_count} (PROMOTED_TO_HIVE: {promo_count}, CONTRADICTS: {contra_count})"
            )
        except Exception as exc:
            print(f"  Edge counting failed: {exc}")

        # Trust scores
        print("\n  Agent trust scores:")
        for agent_info in all_agents:
            print(f"    {agent_info['agent_id']:16s}: {agent_info['trust_score']:.2f}")

        print(f"\n  Elapsed: {elapsed:.2f}s")
        print("=" * 72)


if __name__ == "__main__":
    run_eval()
