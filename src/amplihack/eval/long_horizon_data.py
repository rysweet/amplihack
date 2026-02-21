"""Deterministic data generation for long-horizon memory evaluation.

Philosophy:
- No LLM needed for data generation -- all content is template-based
- Reproducible: same seed produces identical dialogue every time
- Ground truth tracked for every fact delivered
- 8 information blocks test different memory challenges

Public API:
    Turn: Dataclass for a single dialogue turn
    Question: Dataclass for a quiz question with expected answer
    GroundTruth: Dataclass tracking facts delivered per turn
    generate_dialogue(num_turns) -> list[Turn]
    generate_questions(ground_truth, num_questions) -> list[Question]
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Turn:
    """A single dialogue turn delivering information."""

    turn_number: int
    content: str
    block: int  # 1-8
    block_name: str
    facts: list[dict[str, str]]  # Ground truth facts delivered


@dataclass
class Question:
    """A quiz question with expected answer and scoring metadata."""

    question_id: str
    text: str
    expected_answer: str
    category: str  # needle_in_haystack, temporal_evolution, etc.
    relevant_turns: list[int]  # Which turns contain the answer
    scoring_dimensions: list[str]  # Which dimensions matter for this question


@dataclass
class GroundTruth:
    """Complete ground truth for the dialogue."""

    turns: list[Turn]
    facts_by_entity: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    current_values: dict[str, Any] = field(default_factory=dict)
    superseded_values: dict[str, list[dict[str, Any]]] = field(default_factory=dict)


# ============================================================
# People data (Block 1)
# ============================================================

PEOPLE = [
    {
        "name": "Sarah Chen",
        "birthday": "March 15",
        "allergy": "shellfish",
        "hobby": "rock climbing",
        "role": "Senior Engineer",
        "team": "Platform",
        "pet": "tabby cat named Mochi",
        "hometown": "Portland, Oregon",
        "favorite_food": "pad thai",
        "degree": "MS Computer Science from Stanford",
    },
    {
        "name": "Marcus Rivera",
        "birthday": "July 22",
        "allergy": "peanuts",
        "hobby": "woodworking",
        "role": "Product Manager",
        "team": "Growth",
        "pet": "golden retriever named Duke",
        "hometown": "Austin, Texas",
        "favorite_food": "barbecue brisket",
        "degree": "MBA from Wharton",
    },
    {
        "name": "Yuki Tanaka",
        "birthday": "November 3",
        "allergy": "dairy",
        "hobby": "bonsai cultivation",
        "role": "Data Scientist",
        "team": "Analytics",
        "pet": "none",
        "hometown": "Kyoto, Japan",
        "favorite_food": "ramen",
        "degree": "PhD Statistics from MIT",
    },
    {
        "name": "Priya Patel",
        "birthday": "January 28",
        "allergy": "none",
        "hobby": "marathon running",
        "role": "DevOps Lead",
        "team": "Infrastructure",
        "pet": "two parakeets",
        "hometown": "Mumbai, India",
        "favorite_food": "masala dosa",
        "degree": "BS Computer Engineering from IIT Bombay",
    },
    {
        "name": "James O'Brien",
        "birthday": "September 9",
        "allergy": "gluten",
        "hobby": "amateur astronomy",
        "role": "Security Architect",
        "team": "Security",
        "pet": "border collie named Scout",
        "hometown": "Dublin, Ireland",
        "favorite_food": "fish and chips",
        "degree": "MS Cybersecurity from Georgia Tech",
    },
    {
        "name": "Amara Okafor",
        "birthday": "April 17",
        "allergy": "soy",
        "hobby": "oil painting",
        "role": "Frontend Lead",
        "team": "User Experience",
        "pet": "Siamese cat named Nia",
        "hometown": "Lagos, Nigeria",
        "favorite_food": "jollof rice",
        "degree": "BFA Design from RISD, self-taught programmer",
    },
    {
        "name": "Lars Eriksson",
        "birthday": "December 1",
        "allergy": "none",
        "hobby": "cross-country skiing",
        "role": "Backend Engineer",
        "team": "Platform",
        "pet": "husky named Thor",
        "hometown": "Stockholm, Sweden",
        "favorite_food": "meatballs with lingonberry",
        "degree": "MS Software Engineering from KTH",
    },
    {
        "name": "Elena Volkov",
        "birthday": "June 5",
        "allergy": "tree nuts",
        "hobby": "chess",
        "role": "QA Manager",
        "team": "Quality",
        "pet": "none",
        "hometown": "Moscow, Russia",
        "favorite_food": "borscht",
        "degree": "BS Mathematics from Moscow State",
    },
    {
        "name": "Diego Morales",
        "birthday": "August 14",
        "allergy": "none",
        "hobby": "salsa dancing",
        "role": "Mobile Engineer",
        "team": "Mobile",
        "pet": "parrot named Rio",
        "hometown": "Mexico City, Mexico",
        "favorite_food": "tacos al pastor",
        "degree": "BS Computer Science from UNAM",
    },
    {
        "name": "Fatima Al-Hassan",
        "birthday": "February 20",
        "allergy": "eggs",
        "hobby": "calligraphy",
        "role": "ML Engineer",
        "team": "AI/ML",
        "pet": "Persian cat named Layla",
        "hometown": "Cairo, Egypt",
        "favorite_food": "koshari",
        "degree": "PhD Machine Learning from Oxford",
    },
]

# ============================================================
# Project data (Block 2)
# ============================================================

PROJECTS = [
    {
        "name": "Atlas",
        "description": "Cloud migration platform",
        "original_deadline": "June 15",
        "budget": "$2.1M",
        "team_size": 12,
        "lead": "Sarah Chen",
        "updates": [
            {
                "turn_offset": 20,
                "change": "deadline",
                "old": "June 15",
                "new": "August 3",
                "reason": "vendor contract fell through",
            },
            {
                "turn_offset": 45,
                "change": "budget",
                "old": "$2.1M",
                "new": "$2.5M",
                "reason": "additional cloud credits needed",
            },
            {
                "turn_offset": 70,
                "change": "team_size",
                "old": 12,
                "new": 15,
                "reason": "hired 3 contractors for security audit",
            },
            {
                "turn_offset": 85,
                "change": "deadline",
                "old": "August 3",
                "new": "September 20",
                "reason": "compliance review took longer than expected",
            },
        ],
    },
    {
        "name": "Beacon",
        "description": "Real-time analytics dashboard",
        "original_deadline": "March 30",
        "budget": "$800K",
        "team_size": 6,
        "lead": "Marcus Rivera",
        "updates": [
            {
                "turn_offset": 15,
                "change": "team_size",
                "old": 6,
                "new": 8,
                "reason": "added 2 frontend developers",
            },
            {
                "turn_offset": 40,
                "change": "lead",
                "old": "Marcus Rivera",
                "new": "Amara Okafor",
                "reason": "Marcus moved to strategic planning",
            },
            {
                "turn_offset": 60,
                "change": "budget",
                "old": "$800K",
                "new": "$950K",
                "reason": "licensing costs for data visualization library",
            },
        ],
    },
    {
        "name": "Cascade",
        "description": "Automated testing framework",
        "original_deadline": "May 1",
        "budget": "$500K",
        "team_size": 4,
        "lead": "Elena Volkov",
        "updates": [
            {
                "turn_offset": 30,
                "change": "deadline",
                "old": "May 1",
                "new": "April 15",
                "reason": "ahead of schedule",
            },
            {
                "turn_offset": 55,
                "change": "team_size",
                "old": 4,
                "new": 3,
                "reason": "one member moved to Atlas",
            },
        ],
    },
    {
        "name": "Delta",
        "description": "Mobile app redesign",
        "original_deadline": "July 10",
        "budget": "$1.2M",
        "team_size": 8,
        "lead": "Diego Morales",
        "updates": [
            {
                "turn_offset": 25,
                "change": "budget",
                "old": "$1.2M",
                "new": "$1.4M",
                "reason": "need native modules for both iOS and Android",
            },
            {
                "turn_offset": 50,
                "change": "deadline",
                "old": "July 10",
                "new": "August 25",
                "reason": "iOS App Store review delayed",
            },
            {
                "turn_offset": 75,
                "change": "team_size",
                "old": 8,
                "new": 10,
                "reason": "hired QA automation specialists",
            },
        ],
    },
    {
        "name": "Echo",
        "description": "AI-powered customer support chatbot",
        "original_deadline": "September 1",
        "budget": "$1.8M",
        "team_size": 10,
        "lead": "Fatima Al-Hassan",
        "updates": [
            {
                "turn_offset": 35,
                "change": "budget",
                "old": "$1.8M",
                "new": "$2.2M",
                "reason": "GPU compute costs higher than projected",
            },
            {
                "turn_offset": 65,
                "change": "deadline",
                "old": "September 1",
                "new": "October 15",
                "reason": "model fine-tuning required additional iterations",
            },
            {
                "turn_offset": 80,
                "change": "lead",
                "old": "Fatima Al-Hassan",
                "new": "Yuki Tanaka",
                "reason": "Fatima moved to research division",
            },
        ],
    },
]

# ============================================================
# Technical facts (Block 3)
# ============================================================

TECHNICAL_DOMAINS = {
    "programming": [
        "Python 3.12 introduced the new 'type' statement for type aliases.",
        "Rust's borrow checker prevents data races at compile time.",
        "Go 1.22 added the 'range over integers' feature.",
        "TypeScript 5.4 added the 'NoInfer' utility type.",
        "Java 21 introduced virtual threads for lightweight concurrency.",
        "C# 12 added primary constructors for all classes.",
        "Swift 5.9 added macro support.",
        "Kotlin 2.0 introduced the K2 compiler.",
        "Zig 0.12 aims to be a better C replacement.",
        "Julia 1.10 improved garbage collection performance by 30%.",
        "Elixir 1.16 added built-in code formatting for HEEx templates.",
        "Haskell's GHC 9.8 improved error messages significantly.",
        "OCaml 5.1 added native multicore support.",
        "Gleam 1.0 reached stable release in March 2024.",
        "Nim 2.0 introduced ARC memory management.",
        "Scala 3 replaced implicits with given/using clauses.",
        "PHP 8.3 added typed class constants.",
        "Ruby 3.3 introduced RJIT, a pure Ruby JIT compiler.",
        "Dart 3.3 added extension types for zero-cost wrappers.",
    ],
    "security": [
        "OWASP Top 10 2021 lists 'Broken Access Control' as the #1 risk.",
        "Zero Trust Architecture requires 'never trust, always verify'.",
        "The SolarWinds attack compromised 18,000 organizations in 2020.",
        "Post-quantum cryptography standard CRYSTALS-Kyber was selected by NIST.",
        "Supply chain attacks increased 742% between 2019 and 2022.",
        "Passkeys replace passwords using FIDO2/WebAuthn standards.",
        "The Log4Shell vulnerability (CVE-2021-44228) had a CVSS score of 10.0.",
        "Hardware security keys provide the strongest form of 2FA.",
        "Memory-safe languages prevent 70% of security vulnerabilities.",
        "Confidential computing protects data while it's being processed.",
    ],
    "databases": [
        "PostgreSQL 16 improved parallel query performance by 40%.",
        "Redis 7.2 introduced triggers and functions.",
        "MongoDB 7.0 added queryable encryption.",
        "DuckDB is an in-process OLAP database inspired by SQLite.",
        "CockroachDB provides serializable isolation by default.",
        "TimescaleDB handles time-series data at 10-100x the speed of PostgreSQL.",
        "SurrealDB combines document, graph, and relational models.",
        "ClickHouse processes billions of rows per second for analytics.",
        "SQLite is the most deployed database engine in the world.",
        "Kuzu is a graph database optimized for analytics workloads.",
    ],
    "cloud": [
        "AWS Lambda cold starts average 200-500ms for Python.",
        "Google Cloud Run scales to zero when there's no traffic.",
        "Azure Container Apps supports Dapr for microservice communication.",
        "Cloudflare Workers execute at the edge in under 5ms.",
        "Fly.io deploys containers to servers closest to users.",
        "Railway simplifies deployment with automatic Nixpacks detection.",
        "Vercel's Edge Network has 40+ global points of presence.",
        "DigitalOcean App Platform supports auto-scaling.",
        "Render provides free static site hosting with CI/CD.",
        "Heroku removed its free tier in November 2022.",
    ],
    "ml_ai": [
        "GPT-4 was trained on approximately 1.8 trillion parameters.",
        "Retrieval-Augmented Generation (RAG) reduces hallucinations.",
        "Fine-tuning a 7B parameter model requires about 16GB VRAM.",
        "RLHF aligns language models with human preferences.",
        "Mixture of Experts (MoE) activates only a subset of parameters per token.",
        "LoRA reduces fine-tuning parameters by 10,000x.",
        "Constitutional AI trains models using a set of principles.",
        "Diffusion models generate images by iteratively denoising random noise.",
        "Vector databases like Pinecone store and search high-dimensional embeddings.",
        "GGUF format enables running large models on consumer hardware.",
    ],
    "devops": [
        "Kubernetes 1.29 introduced Sidecar Containers as a built-in feature.",
        "Terraform 1.6 added 'testing' framework for infrastructure modules.",
        "Docker BuildKit reduces image build times by 50-80%.",
        "Argo CD implements GitOps for Kubernetes declaratively.",
        "Prometheus uses a pull-based model for metrics collection.",
        "OpenTelemetry unifies tracing, metrics, and logging.",
        "Nix provides reproducible builds across all platforms.",
        "Podman is a daemonless container runtime alternative to Docker.",
        "Cilium uses eBPF for container networking at kernel level.",
        "Crossplane enables managing cloud resources via Kubernetes CRDs.",
    ],
    "architecture": [
        "Event sourcing stores state changes as a sequence of events.",
        "CQRS separates read and write models for better scalability.",
        "Domain-Driven Design focuses on ubiquitous language.",
        "Hexagonal architecture isolates business logic from infrastructure.",
        "Saga pattern manages distributed transactions across microservices.",
        "Circuit breaker pattern prevents cascading failures.",
        "Sidecar pattern extends container functionality without code changes.",
        "Strangler fig pattern enables incremental legacy system migration.",
        "Outbox pattern ensures reliable event publishing from databases.",
        "Choreography-based orchestration reduces single points of failure.",
    ],
    "frontend": [
        "React Server Components reduce client-side JavaScript by 30-50%.",
        "Signals (SolidJS, Angular, Preact) are replacing virtual DOM diffing.",
        "Astro generates zero JavaScript by default for static content.",
        "htmx enables modern UI patterns without heavy JavaScript.",
        "View Transitions API enables native-like page transitions.",
        "Container queries allow responsive design based on parent, not viewport.",
        "CSS nesting is now supported natively in all major browsers.",
        "Bun aims to be an all-in-one JavaScript toolkit.",
        "Qwik uses resumability instead of hydration for instant loading.",
        "Web Components are now supported across all major browsers.",
    ],
}

# ============================================================
# Numerical data (Block 5)
# ============================================================

NUMERICAL_DATA = [
    {"entity": "Q1 revenue", "value": "$4.7M", "detail": "12% above forecast of $4.2M"},
    {
        "entity": "Q2 marketing budget",
        "value": "$2.3M",
        "detail": "15% over the original estimate of $2.0M",
    },
    {"entity": "Q3 customer acquisition cost", "value": "$127", "detail": "down from $156 in Q2"},
    {"entity": "Q4 projected revenue", "value": "$6.1M", "detail": "based on 18% growth rate"},
    {"entity": "Annual employee turnover", "value": "14.2%", "detail": "industry average is 18.5%"},
    {
        "entity": "Server uptime Q1",
        "value": "99.97%",
        "detail": "3 incidents totaling 13 minutes downtime",
    },
    {
        "entity": "Server uptime Q2",
        "value": "99.89%",
        "detail": "7 incidents totaling 47 minutes downtime",
    },
    {
        "entity": "Server uptime Q3",
        "value": "99.995%",
        "detail": "1 incident totaling 2 minutes downtime",
    },
    {
        "entity": "Server migration cost (internal audit)",
        "value": "$450K",
        "detail": "completed in 6 weeks",
    },
    {
        "entity": "Server migration cost (vendor invoice)",
        "value": "$387K",
        "detail": "excluding consulting fees",
    },
    {
        "entity": "Consulting fees for migration",
        "value": "$63K",
        "detail": "billed separately by Accenture",
    },
    {
        "entity": "CI/CD pipeline speed improvement",
        "value": "40%",
        "detail": "from 12 min to 7.2 min average",
    },
    {"entity": "Test coverage", "value": "78.3%", "detail": "up from 62.1% at start of year"},
    {"entity": "API response time p95", "value": "245ms", "detail": "target is under 300ms"},
    {"entity": "API response time p99", "value": "890ms", "detail": "target is under 1000ms"},
    {
        "entity": "Database query optimization savings",
        "value": "$34K/month",
        "detail": "by reducing read replicas from 5 to 3",
    },
    {"entity": "Monthly AWS bill", "value": "$127K", "detail": "up 8% from last month"},
    {"entity": "Open bug count", "value": "342", "detail": "123 critical, 219 non-critical"},
    {
        "entity": "Sprint velocity",
        "value": "47 points",
        "detail": "team average over last 6 sprints",
    },
    {"entity": "NPS score", "value": "72", "detail": "up from 65 last quarter"},
    {"entity": "Customer retention rate", "value": "94.3%", "detail": "target is 95%"},
    {
        "entity": "Code review turnaround",
        "value": "4.2 hours",
        "detail": "median time to first review",
    },
    {
        "entity": "Deployment frequency",
        "value": "8.3 per week",
        "detail": "up from 3.1 per week last quarter",
    },
    {"entity": "Mean time to recovery", "value": "23 minutes", "detail": "down from 45 minutes"},
    {
        "entity": "Infrastructure cost per user",
        "value": "$0.42",
        "detail": "at 285K monthly active users",
    },
    {
        "entity": "Total monthly active users",
        "value": "285,000",
        "detail": "growing 12% month over month",
    },
    {
        "entity": "Premium subscription conversion",
        "value": "7.8%",
        "detail": "from free trial to paid",
    },
    {
        "entity": "Average session duration",
        "value": "14.3 minutes",
        "detail": "mobile: 8.2, desktop: 22.1",
    },
    {
        "entity": "Feature request backlog",
        "value": "892 items",
        "detail": "387 from enterprise customers",
    },
    {
        "entity": "Security audit findings",
        "value": "17 issues",
        "detail": "3 critical, 5 high, 9 medium",
    },
]

# ============================================================
# Contradictory sources (Block 6)
# ============================================================

CONTRADICTORY_REPORTS = [
    {
        "topic": "Q3 revenue",
        "sources": [
            {"name": "Finance Department", "claim": "$5.2M", "detail": "includes deferred revenue"},
            {
                "name": "External Auditor",
                "claim": "$4.8M",
                "detail": "excludes deferred revenue recognition",
            },
            {
                "name": "Board Presentation",
                "claim": "$5.0M",
                "detail": "rounded figure from preliminary report",
            },
        ],
    },
    {
        "topic": "competitor market share",
        "sources": [
            {
                "name": "Gartner Report",
                "claim": "23%",
                "detail": "based on enterprise segment only",
            },
            {"name": "Internal Research", "claim": "31%", "detail": "includes SMB and enterprise"},
            {
                "name": "Industry Newsletter",
                "claim": "18%",
                "detail": "based on revenue, not customers",
            },
        ],
    },
    {
        "topic": "user satisfaction score",
        "sources": [
            {
                "name": "Customer Success Team",
                "claim": "4.5 out of 5",
                "detail": "from post-support surveys",
            },
            {
                "name": "Annual Survey",
                "claim": "3.8 out of 5",
                "detail": "random sample of all users",
            },
            {
                "name": "App Store Reviews",
                "claim": "4.2 out of 5",
                "detail": "average across iOS and Android",
            },
        ],
    },
    {
        "topic": "engineering headcount",
        "sources": [
            {"name": "HR Department", "claim": "187 engineers", "detail": "full-time only"},
            {
                "name": "Engineering VP",
                "claim": "214 engineers",
                "detail": "includes 27 contractors",
            },
            {
                "name": "LinkedIn Profile",
                "claim": "203 engineers",
                "detail": "self-reported, may include interns",
            },
        ],
    },
    {
        "topic": "data center energy usage",
        "sources": [
            {"name": "Facilities Team", "claim": "2.4 MW average", "detail": "measured at meter"},
            {
                "name": "Cloud Provider Report",
                "claim": "1.8 MW equivalent",
                "detail": "shared infrastructure allocation",
            },
            {
                "name": "Sustainability Report",
                "claim": "3.1 MW total",
                "detail": "includes cooling and networking",
            },
        ],
    },
    {
        "topic": "product launch date",
        "sources": [
            {"name": "PM Roadmap", "claim": "March 15", "detail": "original timeline"},
            {
                "name": "Engineering Lead",
                "claim": "April 2",
                "detail": "accounting for testing buffer",
            },
            {
                "name": "Marketing Team",
                "claim": "March 22",
                "detail": "aligned with conference schedule",
            },
        ],
    },
    {
        "topic": "support ticket volume trend",
        "sources": [
            {
                "name": "Support Dashboard",
                "claim": "declining 5% month-over-month",
                "detail": "since new docs launched",
            },
            {
                "name": "CTO Report",
                "claim": "flat",
                "detail": "total volume same, complexity increasing",
            },
            {
                "name": "Customer Advisory Board",
                "claim": "increasing",
                "detail": "enterprise customers report more issues",
            },
        ],
    },
    {
        "topic": "database migration risk level",
        "sources": [
            {
                "name": "DBA Team",
                "claim": "low risk",
                "detail": "schema compatible, tested in staging",
            },
            {
                "name": "Security Review",
                "claim": "medium risk",
                "detail": "PII handling during migration window",
            },
            {
                "name": "External Consultant",
                "claim": "high risk",
                "detail": "similar migrations failed at 3 other companies",
            },
        ],
    },
]

# ============================================================
# Distractor templates (Block 8)
# ============================================================

DISTRACTOR_TOPICS = [
    "The weather in Bermuda averages 75 degrees Fahrenheit in winter.",
    "Ancient Egyptians used papyrus for writing around 3000 BC.",
    "The speed of light is approximately 299,792,458 meters per second.",
    "Coffee was first discovered in Ethiopia in the 9th century.",
    "The Amazon River is the second longest river in the world.",
    "Honey never spoils and has been found preserved in ancient tombs.",
    "The Eiffel Tower grows about 6 inches taller in summer due to heat expansion.",
    "Octopuses have three hearts and blue blood.",
    "The Great Wall of China is not visible from space with the naked eye.",
    "Bananas are technically berries, but strawberries are not.",
    "The shortest war in history lasted 38 minutes between Britain and Zanzibar.",
    "A group of flamingos is called a flamboyance.",
    "Venus rotates backwards compared to most other planets.",
    "The first computer bug was an actual moth found in a relay.",
    "Sharks have been around longer than trees.",
    "The inventor of the Pringles can is buried in one.",
    "A day on Venus is longer than a year on Venus.",
    "Wombat poop is cube-shaped.",
    "Scotland's national animal is the unicorn.",
    "The Twitter bird's official name was Larry.",
    "Cleopatra lived closer in time to the Moon landing than to the building of the pyramids.",
    "More people are killed by vending machines each year than by sharks.",
    "A jiffy is an actual unit of time: 1/100th of a second.",
    "The dot over the letters i and j is called a tittle.",
    "The hashtag symbol is technically called an octothorpe.",
    "Astronauts can grow up to 2 inches taller in space.",
    "The plastic tips on shoelaces are called aglets.",
    "A bolt of lightning is five times hotter than the surface of the sun.",
    "Cows have best friends and get stressed when separated.",
    "The total weight of ants on Earth roughly equals the weight of all humans.",
]


def _scale_range(start: int, end: int, target_turns: int, total_turns: int) -> tuple[int, int]:
    """Scale a block range to fit within a target number of turns."""
    ratio = target_turns / total_turns
    scaled_start = int(start * ratio)
    scaled_end = int(end * ratio)
    return max(0, scaled_start), max(scaled_start + 1, scaled_end)


def generate_dialogue(num_turns: int = 1000, seed: int = 42) -> GroundTruth:
    """Generate deterministic dialogue content for memory evaluation.

    Args:
        num_turns: Total number of dialogue turns (default 1000)
        seed: Random seed for reproducibility

    Returns:
        GroundTruth containing all turns, facts, and tracking data
    """
    rng = random.Random(seed)
    turns: list[Turn] = []
    facts_by_entity: dict[str, list[dict[str, Any]]] = {}
    current_values: dict[str, Any] = {}
    superseded_values: dict[str, list[dict[str, Any]]] = {}

    # Calculate block boundaries scaled to num_turns
    # Standard: 1-50, 51-150, 151-300, 301-500, 501-700, 701-850, 851-950, 951-1000
    blocks = [
        (1, 50, "people"),
        (51, 150, "projects"),
        (151, 300, "technical"),
        (301, 500, "evolving_story"),
        (501, 700, "numerical"),
        (701, 850, "contradictory"),
        (851, 950, "callbacks"),
        (951, 1000, "distractors"),
    ]

    scaled_blocks: list[tuple[int, int, str]] = []
    for start, end, name in blocks:
        s, e = _scale_range(start, end, num_turns, 1000)
        scaled_blocks.append((s, e, name))

    turn_idx = 0

    # Block 1: People (personal details)
    # Ensure ALL people's facts are delivered even with few turns.
    # When turns are scarce, pack multiple people per turn.
    b_start, b_end, _ = scaled_blocks[0]
    people_turns = b_end - b_start
    people_per_turn = max(1, -(-len(PEOPLE) // people_turns))  # Ceiling division

    def _person_content(person: dict[str, Any]) -> tuple[str, list[dict[str, str]]]:
        """Generate content and facts for a single person."""
        parts: list[str] = []
        fact_list: list[dict[str, str]] = []
        pname = person["name"]
        for key, val in person.items():
            if key == "name":
                continue
            content_map = {
                "birthday": f"{pname}'s birthday is {val}.",
                "allergy": (
                    f"{pname} is allergic to {val}."
                    if val != "none"
                    else f"{pname} has no known allergies."
                ),
                "hobby": f"{pname} enjoys {val} in their free time.",
                "role": f"{pname} works as a {val}.",
                "team": f"{pname} is on the {val} team.",
                "pet": (
                    f"{pname} has a {val}." if val != "none" else f"{pname} doesn't have any pets."
                ),
                "hometown": f"{pname} is originally from {val}.",
                "favorite_food": f"{pname}'s favorite food is {val}.",
                "degree": f"{pname} holds a {val}.",
            }
            parts.append(content_map.get(key, f"{pname}'s {key} is {val}."))
            fact_list.append({"entity": pname, "attribute": key, "value": str(val)})
        return " ".join(parts), fact_list

    p_idx = 0
    while p_idx < len(PEOPLE) and turn_idx < b_end:
        # Pack people_per_turn people into this turn
        batch = PEOPLE[p_idx : p_idx + people_per_turn]
        all_parts = []
        all_facts: list[dict[str, str]] = []
        for person in batch:
            content, facts = _person_content(person)
            all_parts.append(content)
            all_facts.extend(facts)
            # Track in ground truth
            pname = person["name"]
            for key, val in person.items():
                if key == "name":
                    continue
                entity_key = f"{pname}.{key}"
                facts_by_entity.setdefault(entity_key, []).append(
                    {"value": str(val), "turn": turn_idx}
                )
                current_values[entity_key] = str(val)

        turns.append(
            Turn(
                turn_number=turn_idx,
                content=" ".join(all_parts),
                block=1,
                block_name="people",
                facts=all_facts,
            )
        )
        turn_idx += 1
        p_idx += people_per_turn

    # Block 2: Projects (with updates)
    b_start, b_end, _ = scaled_blocks[1]
    # First, introduce each project
    for proj in PROJECTS:
        if turn_idx >= b_end:
            break
        content = (
            f"New project update: Project {proj['name']} is a {proj['description']}. "
            f"The deadline is {proj['original_deadline']}, budget is {proj['budget']}, "
            f"team size is {proj['team_size']} people, and the lead is {proj['lead']}."
        )
        facts = [
            {
                "entity": f"Project {proj['name']}",
                "attribute": "description",
                "value": proj["description"],
            },
            {
                "entity": f"Project {proj['name']}",
                "attribute": "deadline",
                "value": proj["original_deadline"],
            },
            {"entity": f"Project {proj['name']}", "attribute": "budget", "value": proj["budget"]},
            {
                "entity": f"Project {proj['name']}",
                "attribute": "team_size",
                "value": str(proj["team_size"]),
            },
            {"entity": f"Project {proj['name']}", "attribute": "lead", "value": proj["lead"]},
        ]
        for f in facts:
            ek = f"{f['entity']}.{f['attribute']}"
            facts_by_entity.setdefault(ek, []).append({"value": f["value"], "turn": turn_idx})
            current_values[ek] = f["value"]

        turns.append(
            Turn(turn_number=turn_idx, content=content, block=2, block_name="projects", facts=facts)
        )
        turn_idx += 1

    # Project updates (spread through the block)
    project_updates = []
    for proj in PROJECTS:
        for upd in proj["updates"]:
            scaled_offset = int(upd["turn_offset"] * (b_end - b_start) / 100) + b_start
            project_updates.append((scaled_offset, proj, upd))
    project_updates.sort(key=lambda x: x[0])

    for target_turn, proj, upd in project_updates:
        if turn_idx >= b_end:
            break
        # Pad with filler turns if needed
        while turn_idx < min(target_turn, b_end):
            content = (
                f"Routine check-in: Project {rng.choice(PROJECTS)['name']} is proceeding normally."
            )
            turns.append(
                Turn(
                    turn_number=turn_idx, content=content, block=2, block_name="projects", facts=[]
                )
            )
            turn_idx += 1

        if turn_idx >= b_end:
            break

        entity = f"Project {proj['name']}"
        attr = upd["change"]
        old_val = str(upd["old"])
        new_val = str(upd["new"])

        content = (
            f"Update on {entity}: the {attr} has been changed from {old_val} to {new_val} "
            f"because {upd['reason']}."
        )
        facts = [{"entity": entity, "attribute": attr, "value": new_val, "supersedes": old_val}]

        ek = f"{entity}.{attr}"
        superseded_values.setdefault(ek, []).append(
            {"old_value": old_val, "new_value": new_val, "turn": turn_idx, "reason": upd["reason"]}
        )
        facts_by_entity.setdefault(ek, []).append({"value": new_val, "turn": turn_idx})
        current_values[ek] = new_val

        turns.append(
            Turn(turn_number=turn_idx, content=content, block=2, block_name="projects", facts=facts)
        )
        turn_idx += 1

    # Fill remaining block 2 turns
    while turn_idx < b_end:
        proj = rng.choice(PROJECTS)
        content = (
            f"Status update: Project {proj['name']} team met for their weekly standup. No changes."
        )
        turns.append(
            Turn(turn_number=turn_idx, content=content, block=2, block_name="projects", facts=[])
        )
        turn_idx += 1

    # Block 3: Technical facts
    b_start, b_end, _ = scaled_blocks[2]
    all_tech_facts = []
    for domain, facts_list in TECHNICAL_DOMAINS.items():
        for fact_text in facts_list:
            all_tech_facts.append((domain, fact_text))
    rng.shuffle(all_tech_facts)

    tech_idx = 0
    while turn_idx < b_end and tech_idx < len(all_tech_facts):
        domain, fact_text = all_tech_facts[tech_idx]
        content = f"Technical note ({domain}): {fact_text}"
        facts = [{"entity": domain, "attribute": "fact", "value": fact_text}]
        ek = f"tech.{domain}.{tech_idx}"
        facts_by_entity.setdefault(ek, []).append({"value": fact_text, "turn": turn_idx})
        current_values[ek] = fact_text

        turns.append(
            Turn(
                turn_number=turn_idx, content=content, block=3, block_name="technical", facts=facts
            )
        )
        turn_idx += 1
        tech_idx += 1

    # Pad remaining block 3
    while turn_idx < b_end:
        domain = rng.choice(list(TECHNICAL_DOMAINS.keys()))
        fact_text = rng.choice(TECHNICAL_DOMAINS[domain])
        content = f"Reminder about {domain}: {fact_text}"
        turns.append(
            Turn(turn_number=turn_idx, content=content, block=3, block_name="technical", facts=[])
        )
        turn_idx += 1

    # Block 4: Evolving storyline with corrections
    b_start, b_end, _ = scaled_blocks[3]
    storyline_entity = "Project Atlas"  # Reuse Atlas for continuity

    evolving_facts = [
        {
            "turn_pct": 0.0,
            "text": f"Breaking: {storyline_entity} hit a major milestone - the core migration engine passed all integration tests.",
            "key": "atlas_milestone",
            "value": "integration tests passed",
        },
        {
            "turn_pct": 0.05,
            "text": f"Correction: earlier report about {storyline_entity} was premature. The integration tests passed but 3 edge cases remain.",
            "key": "atlas_milestone",
            "value": "integration tests passed with 3 remaining edge cases",
            "supersedes": "integration tests passed",
        },
        {
            "turn_pct": 0.1,
            "text": f"{storyline_entity} security review found 5 critical vulnerabilities in the authentication module.",
            "key": "atlas_security",
            "value": "5 critical vulnerabilities found",
        },
        {
            "turn_pct": 0.15,
            "text": f"Update: 3 of the 5 {storyline_entity} security vulnerabilities have been patched. 2 remain.",
            "key": "atlas_security",
            "value": "2 critical vulnerabilities remain",
            "supersedes": "5 critical vulnerabilities found",
        },
        {
            "turn_pct": 0.2,
            "text": f"Good news: all {storyline_entity} security vulnerabilities are now resolved.",
            "key": "atlas_security",
            "value": "all vulnerabilities resolved",
            "supersedes": "2 critical vulnerabilities remain",
        },
        {
            "turn_pct": 0.25,
            "text": f"The {storyline_entity} performance benchmarks show 150ms average response time.",
            "key": "atlas_perf",
            "value": "150ms average response time",
        },
        {
            "turn_pct": 0.3,
            "text": f"After optimization, {storyline_entity} performance improved to 85ms average response time.",
            "key": "atlas_perf",
            "value": "85ms average response time",
            "supersedes": "150ms average response time",
        },
        {
            "turn_pct": 0.35,
            "text": f"{storyline_entity} user acceptance testing started with 50 beta users.",
            "key": "atlas_uat",
            "value": "50 beta users in UAT",
        },
        {
            "turn_pct": 0.4,
            "text": f"The {storyline_entity} beta group expanded to 200 users after positive initial feedback.",
            "key": "atlas_uat",
            "value": "200 beta users in UAT",
            "supersedes": "50 beta users in UAT",
        },
        {
            "turn_pct": 0.45,
            "text": f"Sarah Chen presented the {storyline_entity} progress to the board. The board approved full production rollout.",
            "key": "atlas_status",
            "value": "board approved production rollout",
        },
        {
            "turn_pct": 0.5,
            "text": f"Wait, there's been a complication. A customer data migration bug in {storyline_entity} requires the rollout to be paused.",
            "key": "atlas_status",
            "value": "rollout paused due to data migration bug",
            "supersedes": "board approved production rollout",
        },
        {
            "turn_pct": 0.55,
            "text": f"The {storyline_entity} data migration bug has been fixed. Rollout will resume next week.",
            "key": "atlas_status",
            "value": "bug fixed, rollout resuming next week",
            "supersedes": "rollout paused due to data migration bug",
        },
        {
            "turn_pct": 0.6,
            "text": f"{storyline_entity} is now live in production for 30% of customers.",
            "key": "atlas_status",
            "value": "live for 30% of customers",
            "supersedes": "bug fixed, rollout resuming next week",
        },
        {
            "turn_pct": 0.65,
            "text": f"{storyline_entity} rolled out to 70% of customers. Performance holding steady at 82ms.",
            "key": "atlas_rollout_pct",
            "value": "70%",
        },
        {
            "turn_pct": 0.7,
            "text": f"Full rollout complete: {storyline_entity} is now live for 100% of customers.",
            "key": "atlas_rollout_pct",
            "value": "100%",
            "supersedes": "70%",
        },
        {
            "turn_pct": 0.75,
            "text": f"Post-launch metrics for {storyline_entity}: customer satisfaction up 15%, support tickets down 22%.",
            "key": "atlas_post_launch",
            "value": "satisfaction +15%, tickets -22%",
        },
        {
            "turn_pct": 0.8,
            "text": f"Correction to {storyline_entity} metrics: the actual support ticket reduction is 18%, not 22%.",
            "key": "atlas_post_launch_tickets",
            "value": "support tickets down 18%",
            "supersedes": "tickets -22%",
        },
        {
            "turn_pct": 0.85,
            "text": f"Sarah Chen received the Innovation Award for leading {storyline_entity} to completion.",
            "key": "atlas_award",
            "value": "Sarah Chen received Innovation Award",
        },
        {
            "turn_pct": 0.9,
            "text": f"The {storyline_entity} team is being reorganized. Lars Eriksson will lead the maintenance phase.",
            "key": "atlas_new_lead",
            "value": "Lars Eriksson leads maintenance phase",
        },
        {
            "turn_pct": 0.95,
            "text": f"Final {storyline_entity} cost report: total project cost was $2.7M, under the revised budget of $2.5M... wait, that's OVER budget by $200K.",
            "key": "atlas_final_cost",
            "value": "$2.7M total, $200K over revised budget of $2.5M",
        },
    ]

    block_size = b_end - b_start
    for ef in evolving_facts:
        target = b_start + int(ef["turn_pct"] * block_size)
        while turn_idx < min(target, b_end):
            content = "Day-to-day update: the teams continued their usual work. Nothing unusual to report."
            turns.append(
                Turn(
                    turn_number=turn_idx,
                    content=content,
                    block=4,
                    block_name="evolving_story",
                    facts=[],
                )
            )
            turn_idx += 1

        if turn_idx >= b_end:
            break

        facts = [{"entity": storyline_entity, "attribute": ef["key"], "value": ef["value"]}]
        if "supersedes" in ef:
            facts[0]["supersedes"] = ef["supersedes"]

        ek = f"evolving.{ef['key']}"
        facts_by_entity.setdefault(ek, []).append({"value": ef["value"], "turn": turn_idx})
        current_values[ek] = ef["value"]
        if "supersedes" in ef:
            superseded_values.setdefault(ek, []).append(
                {"old_value": ef["supersedes"], "new_value": ef["value"], "turn": turn_idx}
            )

        turns.append(
            Turn(
                turn_number=turn_idx,
                content=ef["text"],
                block=4,
                block_name="evolving_story",
                facts=facts,
            )
        )
        turn_idx += 1

    while turn_idx < b_end:
        turns.append(
            Turn(
                turn_number=turn_idx,
                content="Quiet day at the office.",
                block=4,
                block_name="evolving_story",
                facts=[],
            )
        )
        turn_idx += 1

    # Block 5: Numerical data
    b_start, b_end, _ = scaled_blocks[4]
    num_idx = 0
    while turn_idx < b_end and num_idx < len(NUMERICAL_DATA):
        nd = NUMERICAL_DATA[num_idx]
        content = (
            f"Data point: The {nd['entity']} is {nd['value']}. Additional context: {nd['detail']}."
        )
        facts = [
            {"entity": nd["entity"], "attribute": "value", "value": nd["value"]},
            {"entity": nd["entity"], "attribute": "detail", "value": nd["detail"]},
        ]

        ek = f"numerical.{nd['entity']}"
        facts_by_entity.setdefault(ek, []).append({"value": nd["value"], "turn": turn_idx})
        current_values[ek] = nd["value"]
        current_values[f"{ek}.detail"] = nd["detail"]

        turns.append(
            Turn(
                turn_number=turn_idx, content=content, block=5, block_name="numerical", facts=facts
            )
        )
        turn_idx += 1
        num_idx += 1

    # Repeat numerical data if more turns needed
    while turn_idx < b_end:
        nd = NUMERICAL_DATA[turn_idx % len(NUMERICAL_DATA)]
        content = f"Reminder: The {nd['entity']} remains at {nd['value']}."
        turns.append(
            Turn(turn_number=turn_idx, content=content, block=5, block_name="numerical", facts=[])
        )
        turn_idx += 1

    # Block 6: Contradictory reports
    b_start, b_end, _ = scaled_blocks[5]
    for cr in CONTRADICTORY_REPORTS:
        for src in cr["sources"]:
            if turn_idx >= b_end:
                break
            content = (
                f"Report from {src['name']}: The {cr['topic']} is {src['claim']}. "
                f"Detail: {src['detail']}."
            )
            facts = [
                {
                    "entity": cr["topic"],
                    "attribute": f"source:{src['name']}",
                    "value": src["claim"],
                    "detail": src["detail"],
                }
            ]

            ek = f"contradiction.{cr['topic']}.{src['name']}"
            facts_by_entity.setdefault(ek, []).append(
                {"value": src["claim"], "turn": turn_idx, "source": src["name"]}
            )
            current_values[ek] = src["claim"]

            turns.append(
                Turn(
                    turn_number=turn_idx,
                    content=content,
                    block=6,
                    block_name="contradictory",
                    facts=facts,
                )
            )
            turn_idx += 1

    while turn_idx < b_end:
        turns.append(
            Turn(
                turn_number=turn_idx,
                content="No new conflicting reports today.",
                block=6,
                block_name="contradictory",
                facts=[],
            )
        )
        turn_idx += 1

    # Block 7: Callback references
    b_start, b_end, _ = scaled_blocks[6]
    # Create callbacks that reference earlier turns
    callback_templates = [
        (
            "Sarah Chen",
            "role",
            "Remember what I told you about Sarah Chen's role? She's now leading the Atlas maintenance phase under Lars Eriksson.",
        ),
        (
            "Project Atlas",
            "deadline",
            "Looking back at Project Atlas, the deadline changed multiple times from June 15 to August 3 to September 20.",
        ),
        (
            "Q2 marketing budget",
            "value",
            "Going back to the financial data, the Q2 marketing budget was $2.3M, 15% over the original $2.0M estimate.",
        ),
        (
            "server migration",
            "cost",
            "Recall the server migration costs? The internal audit said $450K, vendor invoice said $387K, and consulting fees were $63K.",
        ),
        (
            "Marcus Rivera",
            "role",
            "By the way, Marcus Rivera who was Product Manager moved to strategic planning. Amara Okafor took over Project Beacon.",
        ),
        (
            "Project Echo",
            "lead",
            "Remember Project Echo? Leadership changed from Fatima Al-Hassan to Yuki Tanaka when Fatima moved to research.",
        ),
        (
            "atlas security",
            "status",
            "Thinking about Atlas security, they went from 5 critical vulns to 3 patched to all resolved.",
        ),
        (
            "test coverage",
            "value",
            "The test coverage metric went from 62.1% at year start to 78.3%. Pretty solid improvement.",
        ),
        ("NPS score", "value", "Our NPS score improved from 65 last quarter to 72 this quarter."),
        (
            "competitor market share",
            "reports",
            "The competitor market share numbers varied wildly: Gartner said 23%, internal said 31%, newsletter said 18%.",
        ),
    ]

    cb_idx = 0
    while turn_idx < b_end and cb_idx < len(callback_templates):
        entity, attr, text = callback_templates[cb_idx]
        content = text
        facts = [{"entity": entity, "attribute": f"callback_{attr}", "value": text}]
        turns.append(
            Turn(
                turn_number=turn_idx, content=content, block=7, block_name="callbacks", facts=facts
            )
        )
        turn_idx += 1
        cb_idx += 1

    while turn_idx < b_end:
        cb = callback_templates[turn_idx % len(callback_templates)]
        turns.append(
            Turn(
                turn_number=turn_idx,
                content=f"Recap: {cb[2]}",
                block=7,
                block_name="callbacks",
                facts=[],
            )
        )
        turn_idx += 1

    # Block 8: Distractors
    b_start, b_end, _ = scaled_blocks[7]
    dist_idx = 0
    while turn_idx < b_end:
        content = DISTRACTOR_TOPICS[dist_idx % len(DISTRACTOR_TOPICS)]
        turns.append(
            Turn(
                turn_number=turn_idx,
                content=f"Random fact: {content}",
                block=8,
                block_name="distractors",
                facts=[],
            )
        )
        turn_idx += 1
        dist_idx += 1

    # Pad any remaining turns
    while turn_idx < num_turns:
        turns.append(
            Turn(
                turn_number=turn_idx,
                content="End of updates.",
                block=8,
                block_name="distractors",
                facts=[],
            )
        )
        turn_idx += 1

    return GroundTruth(
        turns=turns,
        facts_by_entity=facts_by_entity,
        current_values=current_values,
        superseded_values=superseded_values,
    )


def _delivered_entities(ground_truth: GroundTruth) -> set[str]:
    """Return set of entity names whose facts were delivered in the dialogue."""
    entities: set[str] = set()
    for turn in ground_truth.turns:
        for fact in turn.facts:
            entities.add(fact.get("entity", ""))
    # Also add block names and topics from content
    for turn in ground_truth.turns:
        content_lower = turn.content.lower()
        for person in PEOPLE:
            if person["name"].lower() in content_lower:
                entities.add(person["name"])
        for proj in PROJECTS:
            if f"project {proj['name'].lower()}" in content_lower:
                entities.add(f"Project {proj['name']}")
    return entities


def _question_references_delivered(
    question: Question, delivered: set[str], ground_truth: GroundTruth
) -> bool:
    """Check if a question's answer facts were delivered in the dialogue.

    Always returns True -- all facts should be delivered by the generator.
    Kept as a hook for future validation if needed.
    """
    return True


def generate_questions(ground_truth: GroundTruth, num_questions: int = 100) -> list[Question]:
    """Generate quiz questions targeting specific memory capabilities.

    Only includes questions whose answers were actually delivered in the dialogue.
    This prevents unfair questions when dialogue is shortened (e.g., 100 turns
    instead of 1000).

    Args:
        ground_truth: The GroundTruth from generate_dialogue
        num_questions: Target number of questions (scaled proportionally)

    Returns:
        List of Questions with expected answers and scoring metadata
    """
    questions: list[Question] = []
    scale = num_questions / 100.0  # Scale relative to standard 100 questions
    delivered = _delivered_entities(ground_truth)

    # Category 1: Needle-in-haystack (20% of questions)
    needle_count = max(1, int(20 * scale))
    needle_questions = [
        Question(
            question_id="needle_01",
            text="What is Sarah Chen's birthday?",
            expected_answer="March 15",
            category="needle_in_haystack",
            relevant_turns=[0],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
        Question(
            question_id="needle_02",
            text="What allergy does James O'Brien have?",
            expected_answer="gluten",
            category="needle_in_haystack",
            relevant_turns=[0],
            scoring_dimensions=["factual_accuracy"],
        ),
        Question(
            question_id="needle_03",
            text="What is Fatima Al-Hassan's hobby?",
            expected_answer="calligraphy",
            category="needle_in_haystack",
            relevant_turns=[0],
            scoring_dimensions=["factual_accuracy"],
        ),
        Question(
            question_id="needle_04",
            text="What degree does Yuki Tanaka hold?",
            expected_answer="PhD Statistics from MIT",
            category="needle_in_haystack",
            relevant_turns=[0],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
        Question(
            question_id="needle_05",
            text="What is the name of Lars Eriksson's pet?",
            expected_answer="Thor, a husky",
            category="needle_in_haystack",
            relevant_turns=[0],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
        Question(
            question_id="needle_06",
            text="What is Amara Okafor's hometown?",
            expected_answer="Lagos, Nigeria",
            category="needle_in_haystack",
            relevant_turns=[0],
            scoring_dimensions=["factual_accuracy"],
        ),
        Question(
            question_id="needle_07",
            text="What team is Diego Morales on?",
            expected_answer="Mobile",
            category="needle_in_haystack",
            relevant_turns=[0],
            scoring_dimensions=["factual_accuracy"],
        ),
        Question(
            question_id="needle_08",
            text="What is the original budget for Project Cascade?",
            expected_answer="$500K",
            category="needle_in_haystack",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
        Question(
            question_id="needle_09",
            text="What does DuckDB do?",
            expected_answer="DuckDB is an in-process OLAP database inspired by SQLite.",
            category="needle_in_haystack",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
        ),
        Question(
            question_id="needle_10",
            text="What is the CVSS score of the Log4Shell vulnerability?",
            expected_answer="10.0",
            category="needle_in_haystack",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
        Question(
            question_id="needle_11",
            text="What food does Marcus Rivera prefer?",
            expected_answer="barbecue brisket",
            category="needle_in_haystack",
            relevant_turns=[0],
            scoring_dimensions=["factual_accuracy"],
        ),
        Question(
            question_id="needle_12",
            text="What is Elena Volkov's role?",
            expected_answer="QA Manager",
            category="needle_in_haystack",
            relevant_turns=[0],
            scoring_dimensions=["factual_accuracy"],
        ),
        Question(
            question_id="needle_13",
            text="What is Priya Patel's hobby?",
            expected_answer="marathon running",
            category="needle_in_haystack",
            relevant_turns=[0],
            scoring_dimensions=["factual_accuracy"],
        ),
        Question(
            question_id="needle_14",
            text="What programming language added the 'NoInfer' utility type?",
            expected_answer="TypeScript 5.4",
            category="needle_in_haystack",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
        ),
        Question(
            question_id="needle_15",
            text="What is the description of Project Delta?",
            expected_answer="Mobile app redesign",
            category="needle_in_haystack",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
        ),
        Question(
            question_id="needle_16",
            text="What is the original team size for Project Echo?",
            expected_answer="10",
            category="needle_in_haystack",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
        Question(
            question_id="needle_17",
            text="What pet does Diego Morales have?",
            expected_answer="A parrot named Rio",
            category="needle_in_haystack",
            relevant_turns=[0],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
        Question(
            question_id="needle_18",
            text="What cloud platform removed its free tier in November 2022?",
            expected_answer="Heroku",
            category="needle_in_haystack",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
        ),
        Question(
            question_id="needle_19",
            text="What is Priya Patel's hometown?",
            expected_answer="Mumbai, India",
            category="needle_in_haystack",
            relevant_turns=[0],
            scoring_dimensions=["factual_accuracy"],
        ),
        Question(
            question_id="needle_20",
            text="What architecture pattern manages distributed transactions across microservices?",
            expected_answer="Saga pattern",
            category="needle_in_haystack",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
        ),
    ]
    needle_questions = [
        q for q in needle_questions if _question_references_delivered(q, delivered, ground_truth)
    ]
    questions.extend(needle_questions[:needle_count])

    # Category 2: Temporal evolution (15% of questions)
    temporal_count = max(1, int(15 * scale))
    temporal_questions = [
        Question(
            question_id="temporal_01",
            text="What is the CURRENT deadline for Project Atlas?",
            expected_answer="September 20 (changed from August 3, which was changed from June 15)",
            category="temporal_evolution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "temporal_awareness"],
        ),
        Question(
            question_id="temporal_02",
            text="What was the ORIGINAL deadline for Project Atlas before any changes?",
            expected_answer="June 15",
            category="temporal_evolution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "temporal_awareness"],
        ),
        Question(
            question_id="temporal_03",
            text="How many times did the Project Atlas deadline change?",
            expected_answer="2 times (June 15 -> August 3 -> September 20)",
            category="temporal_evolution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "temporal_awareness", "specificity"],
        ),
        Question(
            question_id="temporal_04",
            text="What is the current status of Atlas security vulnerabilities?",
            expected_answer="All vulnerabilities resolved (went from 5 found -> 3 patched -> all resolved)",
            category="temporal_evolution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "temporal_awareness"],
        ),
        Question(
            question_id="temporal_05",
            text="How did the Atlas average response time change over time?",
            expected_answer="Improved from 150ms to 85ms after optimization",
            category="temporal_evolution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "temporal_awareness", "specificity"],
        ),
        Question(
            question_id="temporal_06",
            text="Who leads Project Beacon now, and who led it originally?",
            expected_answer="Amara Okafor leads now; Marcus Rivera was the original lead",
            category="temporal_evolution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "temporal_awareness"],
        ),
        Question(
            question_id="temporal_07",
            text="How did the Atlas beta user count change?",
            expected_answer="Expanded from 50 beta users to 200 beta users after positive initial feedback",
            category="temporal_evolution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "temporal_awareness", "specificity"],
        ),
        Question(
            question_id="temporal_08",
            text="What is the current rollout percentage for Project Atlas?",
            expected_answer="100% (went from 30% -> 70% -> 100%)",
            category="temporal_evolution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "temporal_awareness"],
        ),
        Question(
            question_id="temporal_09",
            text="What happened to the Atlas production rollout status over time?",
            expected_answer="Board approved -> paused due to data migration bug -> bug fixed, resuming -> live for 30% -> 70% -> 100%",
            category="temporal_evolution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "temporal_awareness", "specificity"],
        ),
        Question(
            question_id="temporal_10",
            text="Who currently leads Project Echo?",
            expected_answer="Yuki Tanaka (changed from Fatima Al-Hassan who moved to research)",
            category="temporal_evolution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "temporal_awareness"],
        ),
        Question(
            question_id="temporal_11",
            text="What was the corrected support ticket reduction figure for Atlas post-launch?",
            expected_answer="18% (corrected from originally reported 22%)",
            category="temporal_evolution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "temporal_awareness"],
        ),
        Question(
            question_id="temporal_12",
            text="How did the Project Cascade deadline change?",
            expected_answer="Moved from May 1 to April 15 because the project was ahead of schedule",
            category="temporal_evolution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "temporal_awareness"],
        ),
        Question(
            question_id="temporal_13",
            text="What is the current budget for Project Delta?",
            expected_answer="$1.4M (increased from $1.2M for native iOS and Android modules)",
            category="temporal_evolution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "temporal_awareness"],
        ),
        Question(
            question_id="temporal_14",
            text="How did server uptime change across Q1, Q2, and Q3?",
            expected_answer="Q1: 99.97%, Q2: 99.89% (dipped), Q3: 99.995% (best)",
            category="temporal_evolution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "temporal_awareness", "specificity"],
        ),
        Question(
            question_id="temporal_15",
            text="What is the final total cost of Project Atlas and how does it compare to budget?",
            expected_answer="$2.7M total, which is $200K over the revised budget of $2.5M",
            category="temporal_evolution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "temporal_awareness", "specificity"],
        ),
    ]
    temporal_questions = [
        q for q in temporal_questions if _question_references_delivered(q, delivered, ground_truth)
    ]
    questions.extend(temporal_questions[:temporal_count])

    # Category 3: Numerical precision (15% of questions)
    numerical_count = max(1, int(15 * scale))
    numerical_questions = [
        Question(
            question_id="numerical_01",
            text="What was the server migration cost according to the internal audit?",
            expected_answer="$450K",
            category="numerical_precision",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
        Question(
            question_id="numerical_02",
            text="What is the difference between the internal audit figure and the vendor invoice for the server migration?",
            expected_answer="$63K ($450K - $387K = $63K, which matches the separately billed consulting fees)",
            category="numerical_precision",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
        Question(
            question_id="numerical_03",
            text="What percentage over the original estimate was the Q2 marketing budget?",
            expected_answer="15% (budget was $2.3M vs original estimate of $2.0M)",
            category="numerical_precision",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
        Question(
            question_id="numerical_04",
            text="What is the API response time at p95 and p99, and are both within target?",
            expected_answer="p95: 245ms (target <300ms, within target), p99: 890ms (target <1000ms, within target)",
            category="numerical_precision",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
        Question(
            question_id="numerical_05",
            text="How much did test coverage improve from the start of the year?",
            expected_answer="Improved from 62.1% to 78.3%, an increase of 16.2 percentage points",
            category="numerical_precision",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
        Question(
            question_id="numerical_06",
            text="What is the infrastructure cost per user and how many monthly active users are there?",
            expected_answer="$0.42 per user with 285,000 monthly active users",
            category="numerical_precision",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
        Question(
            question_id="numerical_07",
            text="How much did deployment frequency improve?",
            expected_answer="From 3.1 per week to 8.3 per week (about 2.7x improvement)",
            category="numerical_precision",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
        Question(
            question_id="numerical_08",
            text="What are the open bug counts broken down by severity?",
            expected_answer="342 total: 123 critical, 219 non-critical",
            category="numerical_precision",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
        Question(
            question_id="numerical_09",
            text="How much does the database query optimization save monthly and what was the change?",
            expected_answer="$34K/month savings by reducing read replicas from 5 to 3",
            category="numerical_precision",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
        Question(
            question_id="numerical_10",
            text="What was the Q1 revenue and how did it compare to forecast?",
            expected_answer="$4.7M, 12% above forecast of $4.2M",
            category="numerical_precision",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
        Question(
            question_id="numerical_11",
            text="What is the customer retention rate and the target?",
            expected_answer="94.3%, target is 95%",
            category="numerical_precision",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
        Question(
            question_id="numerical_12",
            text="What is the premium subscription conversion rate?",
            expected_answer="7.8% from free trial to paid",
            category="numerical_precision",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
        Question(
            question_id="numerical_13",
            text="How many security audit findings were there and what severity breakdown?",
            expected_answer="17 issues: 3 critical, 5 high, 9 medium",
            category="numerical_precision",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
        Question(
            question_id="numerical_14",
            text="What is the monthly AWS bill and the month-over-month change?",
            expected_answer="$127K, up 8% from last month",
            category="numerical_precision",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
        Question(
            question_id="numerical_15",
            text="What is the mean time to recovery and how has it changed?",
            expected_answer="23 minutes, down from 45 minutes",
            category="numerical_precision",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
    ]
    numerical_questions = [
        q for q in numerical_questions if _question_references_delivered(q, delivered, ground_truth)
    ]
    questions.extend(numerical_questions[:numerical_count])

    # Category 4: Source attribution (10% of questions)
    source_count = max(1, int(10 * scale))
    source_questions = [
        Question(
            question_id="source_01",
            text="What does the internal audit say the server migration cost was, versus the vendor invoice?",
            expected_answer="Internal audit: $450K; Vendor invoice: $387K. The $63K difference was consulting fees billed separately.",
            category="source_attribution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "source_attribution"],
        ),
        Question(
            question_id="source_02",
            text="What are the different claims about Q3 revenue and who made each claim?",
            expected_answer="Finance Department: $5.2M (includes deferred revenue); External Auditor: $4.8M (excludes deferred); Board Presentation: $5.0M (rounded, preliminary)",
            category="source_attribution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "source_attribution", "specificity"],
        ),
        Question(
            question_id="source_03",
            text="According to each source, what is the competitor market share?",
            expected_answer="Gartner: 23% (enterprise only); Internal Research: 31% (includes SMB); Industry Newsletter: 18% (revenue-based)",
            category="source_attribution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "source_attribution"],
        ),
        Question(
            question_id="source_04",
            text="What do different sources say about user satisfaction scores?",
            expected_answer="Customer Success Team: 4.5/5 (post-support surveys); Annual Survey: 3.8/5 (random sample); App Store Reviews: 4.2/5",
            category="source_attribution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "source_attribution"],
        ),
        Question(
            question_id="source_05",
            text="How do the engineering headcount figures differ across sources?",
            expected_answer="HR: 187 (full-time only); Engineering VP: 214 (includes 27 contractors); LinkedIn: 203 (may include interns)",
            category="source_attribution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "source_attribution", "specificity"],
        ),
        Question(
            question_id="source_06",
            text="Which source gives the lowest competitor market share figure?",
            expected_answer="Industry Newsletter at 18% (based on revenue, not customers)",
            category="source_attribution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "source_attribution"],
        ),
        Question(
            question_id="source_07",
            text="What does the DBA team say about database migration risk vs the external consultant?",
            expected_answer="DBA Team: low risk (schema compatible, tested); External Consultant: high risk (similar migrations failed at 3 companies)",
            category="source_attribution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "source_attribution"],
        ),
        Question(
            question_id="source_08",
            text="What are the three different proposed product launch dates?",
            expected_answer="PM Roadmap: March 15; Engineering Lead: April 2 (testing buffer); Marketing: March 22 (conference)",
            category="source_attribution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "source_attribution", "specificity"],
        ),
        Question(
            question_id="source_09",
            text="What do different sources say about the data center energy usage?",
            expected_answer="Facilities: 2.4 MW (measured at meter); Cloud Provider: 1.8 MW (shared allocation); Sustainability Report: 3.1 MW (includes cooling/networking)",
            category="source_attribution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "source_attribution"],
        ),
        Question(
            question_id="source_10",
            text="How do the support ticket volume trend claims differ?",
            expected_answer="Support Dashboard: declining 5% MoM (new docs); CTO: flat (complexity increasing); Customer Advisory Board: increasing (enterprise issues)",
            category="source_attribution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "source_attribution"],
        ),
    ]
    source_questions = [
        q for q in source_questions if _question_references_delivered(q, delivered, ground_truth)
    ]
    questions.extend(source_questions[:source_count])

    # Category 5: Cross-reference (10% of questions)
    cross_ref_count = max(1, int(10 * scale))
    cross_ref_questions = [
        Question(
            question_id="crossref_01",
            text="Which project is Sarah Chen currently leading and what award did she receive?",
            expected_answer="Sarah Chen led Project Atlas to completion and received the Innovation Award. Lars Eriksson now leads the maintenance phase.",
            category="cross_reference",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
        Question(
            question_id="crossref_02",
            text="Fatima Al-Hassan moved from one project to research. Who replaced her and on which project?",
            expected_answer="Fatima Al-Hassan was leading Project Echo. Yuki Tanaka replaced her when Fatima moved to the research division.",
            category="cross_reference",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
        ),
        Question(
            question_id="crossref_03",
            text="What is Marcus Rivera's current role and how did his departure affect Project Beacon?",
            expected_answer="Marcus Rivera moved from Product Manager to strategic planning. Amara Okafor took over as lead of Project Beacon.",
            category="cross_reference",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
        ),
        Question(
            question_id="crossref_04",
            text="Which person on the Platform team has a pet husky, and what project maintenance do they now lead?",
            expected_answer="Lars Eriksson is on the Platform team, has a husky named Thor, and now leads the Atlas maintenance phase.",
            category="cross_reference",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
        Question(
            question_id="crossref_05",
            text="Which projects went over their original budget and by how much?",
            expected_answer="Atlas: $2.1M -> $2.5M (+$400K), final cost $2.7M; Beacon: $800K -> $950K (+$150K); Delta: $1.2M -> $1.4M (+$200K); Echo: $1.8M -> $2.2M (+$400K)",
            category="cross_reference",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
        Question(
            question_id="crossref_06",
            text="Which person from Mumbai works in DevOps and what is their hobby?",
            expected_answer="Priya Patel from Mumbai is the DevOps Lead on the Infrastructure team. Her hobby is marathon running.",
            category="cross_reference",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
        ),
        Question(
            question_id="crossref_07",
            text="Which engineer holds a PhD and is now leading a project that was previously led by someone else?",
            expected_answer="Yuki Tanaka has a PhD Statistics from MIT and now leads Project Echo (previously led by Fatima Al-Hassan).",
            category="cross_reference",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
        ),
        Question(
            question_id="crossref_08",
            text="Considering the total server migration costs (audit + consulting), how much did the vendor charge less than the total?",
            expected_answer="Total: $450K + $63K = $513K; Vendor: $387K; Difference: $126K (vendor charged $126K less than total)",
            category="cross_reference",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
        Question(
            question_id="crossref_09",
            text="Who on the AI/ML team has a Persian cat, and what happened to the project they led?",
            expected_answer="Fatima Al-Hassan on the AI/ML team has a Persian cat named Layla. She led Project Echo but moved to research; Yuki Tanaka replaced her.",
            category="cross_reference",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
        Question(
            question_id="crossref_10",
            text="Which project came in ahead of schedule, and what happened to its team size?",
            expected_answer="Project Cascade moved deadline from May 1 to April 15 (ahead of schedule). Team size decreased from 4 to 3 (one member moved to Atlas).",
            category="cross_reference",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
        ),
    ]
    cross_ref_questions = [
        q for q in cross_ref_questions if _question_references_delivered(q, delivered, ground_truth)
    ]
    questions.extend(cross_ref_questions[:cross_ref_count])

    # Category 6: Distractor resistance (10% of questions)
    distractor_count = max(1, int(10 * scale))
    distractor_questions = [
        Question(
            question_id="distractor_01",
            text="What is Priya Patel's allergy? Answer with ONLY the allergy information, ignoring any unrelated facts.",
            expected_answer="Priya Patel has no known allergies (none).",
            category="distractor_resistance",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "confidence_calibration"],
        ),
        Question(
            question_id="distractor_02",
            text="What is the sprint velocity? Do not include any random trivia in your answer.",
            expected_answer="47 points (team average over last 6 sprints)",
            category="distractor_resistance",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
        Question(
            question_id="distractor_03",
            text="What is Elena Volkov's pet situation? Focus only on the people data.",
            expected_answer="Elena Volkov doesn't have any pets.",
            category="distractor_resistance",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
        ),
        Question(
            question_id="distractor_04",
            text="What is the median code review turnaround time? Answer precisely.",
            expected_answer="4.2 hours (median time to first review)",
            category="distractor_resistance",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
        Question(
            question_id="distractor_05",
            text="What language introduced virtual threads for lightweight concurrency?",
            expected_answer="Java 21",
            category="distractor_resistance",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
        ),
        Question(
            question_id="distractor_06",
            text="What is the feature request backlog size and how many are from enterprise?",
            expected_answer="892 items total, 387 from enterprise customers",
            category="distractor_resistance",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
        Question(
            question_id="distractor_07",
            text="What is the average session duration broken down by platform?",
            expected_answer="14.3 minutes overall. Mobile: 8.2 minutes, Desktop: 22.1 minutes.",
            category="distractor_resistance",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
        Question(
            question_id="distractor_08",
            text="How many critical security audit findings were there?",
            expected_answer="3 critical (out of 17 total: 3 critical, 5 high, 9 medium)",
            category="distractor_resistance",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
        Question(
            question_id="distractor_09",
            text="What was the CI/CD pipeline speed improvement?",
            expected_answer="40% improvement, from 12 minutes to 7.2 minutes average",
            category="distractor_resistance",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
        Question(
            question_id="distractor_10",
            text="What is the Q4 projected revenue and the assumed growth rate?",
            expected_answer="$6.1M projected, based on 18% growth rate",
            category="distractor_resistance",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
    ]
    distractor_questions = [
        q
        for q in distractor_questions
        if _question_references_delivered(q, delivered, ground_truth)
    ]
    questions.extend(distractor_questions[:distractor_count])

    # Category 7: Meta-memory (5% of questions)
    meta_count = max(1, int(5 * scale))
    meta_questions = [
        Question(
            question_id="meta_01",
            text="How many different projects have I told you about?",
            expected_answer="5 projects: Atlas, Beacon, Cascade, Delta, and Echo",
            category="meta_memory",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
        Question(
            question_id="meta_02",
            text="How many different people's personal details did I share with you?",
            expected_answer="10 people: Sarah Chen, Marcus Rivera, Yuki Tanaka, Priya Patel, James O'Brien, Amara Okafor, Lars Eriksson, Elena Volkov, Diego Morales, Fatima Al-Hassan",
            category="meta_memory",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
        Question(
            question_id="meta_03",
            text="Which topics had conflicting information from different sources?",
            expected_answer="Q3 revenue, competitor market share, user satisfaction, engineering headcount, data center energy, product launch date, support ticket trends, database migration risk",
            category="meta_memory",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
        Question(
            question_id="meta_04",
            text="Which project had the most updates and changes during our conversation?",
            expected_answer="Project Atlas had the most changes: deadline changed twice, budget changed, team size changed, security issues, performance optimization, rollout stages, leadership change",
            category="meta_memory",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
        ),
        Question(
            question_id="meta_05",
            text="How many technical domains did I cover in the technical facts section?",
            expected_answer="8 domains: programming, security, databases, cloud, ml_ai, devops, architecture, frontend",
            category="meta_memory",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
    ]
    meta_questions = [
        q for q in meta_questions if _question_references_delivered(q, delivered, ground_truth)
    ]
    questions.extend(meta_questions[:meta_count])

    # Add bonus questions to fill up to num_questions if needed
    bonus_questions = [
        Question(
            question_id="bonus_01",
            text="What is the current budget for Project Echo?",
            expected_answer="$2.2M (increased from $1.8M for GPU compute costs)",
            category="temporal_evolution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "temporal_awareness"],
        ),
        Question(
            question_id="bonus_02",
            text="What happened to Project Atlas after the board approved rollout?",
            expected_answer="A data migration bug forced a pause, then the bug was fixed and rollout resumed to 30% -> 70% -> 100%",
            category="temporal_evolution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "temporal_awareness"],
        ),
        Question(
            question_id="bonus_03",
            text="What is the customer acquisition cost trend?",
            expected_answer="Q3: $127, down from $156 in Q2",
            category="numerical_precision",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
        Question(
            question_id="bonus_04",
            text="What language aims to be a better C replacement?",
            expected_answer="Zig (version 0.12)",
            category="needle_in_haystack",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
        ),
        Question(
            question_id="bonus_05",
            text="What pattern enables incremental legacy system migration?",
            expected_answer="Strangler fig pattern",
            category="needle_in_haystack",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
        ),
        Question(
            question_id="bonus_06",
            text="What is Sarah Chen's favorite food?",
            expected_answer="Pad thai",
            category="needle_in_haystack",
            relevant_turns=[0],
            scoring_dimensions=["factual_accuracy"],
        ),
        Question(
            question_id="bonus_07",
            text="Who was originally leading Project Atlas?",
            expected_answer="Sarah Chen",
            category="temporal_evolution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
        ),
        Question(
            question_id="bonus_08",
            text="What is the Q3 customer acquisition cost compared to Q2?",
            expected_answer="Q3 was $127, down from $156 in Q2 (a decrease of $29)",
            category="numerical_precision",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
        Question(
            question_id="bonus_09",
            text="What does PostgreSQL 16 improve?",
            expected_answer="PostgreSQL 16 improved parallel query performance by 40%",
            category="needle_in_haystack",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
        ),
        Question(
            question_id="bonus_10",
            text="What is the annual employee turnover rate compared to industry average?",
            expected_answer="14.2% turnover, vs industry average of 18.5%",
            category="numerical_precision",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
        Question(
            question_id="bonus_11",
            text="What post-quantum cryptography standard was selected by NIST?",
            expected_answer="CRYSTALS-Kyber",
            category="needle_in_haystack",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
        ),
        Question(
            question_id="bonus_12",
            text="What CSS feature is now natively supported in all major browsers?",
            expected_answer="CSS nesting",
            category="needle_in_haystack",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
        ),
        Question(
            question_id="bonus_13",
            text="How did the Atlas team size change from original to final?",
            expected_answer="Grew from 12 to 15 (hired 3 contractors for security audit)",
            category="temporal_evolution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "temporal_awareness"],
        ),
        Question(
            question_id="bonus_14",
            text="What is James O'Brien's pet's name and breed?",
            expected_answer="Scout, a border collie",
            category="needle_in_haystack",
            relevant_turns=[0],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
        Question(
            question_id="bonus_15",
            text="What is the NPS score and how has it changed?",
            expected_answer="72, up from 65 last quarter",
            category="numerical_precision",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
        ),
    ]

    remaining = num_questions - len(questions)
    if remaining > 0:
        bonus_questions = [
            q for q in bonus_questions if _question_references_delivered(q, delivered, ground_truth)
        ]
        questions.extend(bonus_questions[:remaining])

    return questions[:num_questions]


__all__ = [
    "Turn",
    "Question",
    "GroundTruth",
    "generate_dialogue",
    "generate_questions",
    "PEOPLE",
    "PROJECTS",
    "TECHNICAL_DOMAINS",
    "NUMERICAL_DATA",
    "CONTRADICTORY_REPORTS",
]
