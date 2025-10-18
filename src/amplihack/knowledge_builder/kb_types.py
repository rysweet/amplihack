"""Type definitions for Knowledge Builder."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class Question:
    """A question in the knowledge graph."""

    text: str
    depth: int  # 0 = initial, 1-3 = Socratic levels
    parent_index: int | None = None  # Index of parent question
    answer: str = ""  # Populated after web search


@dataclass
class Answer:
    """An answer with source attribution."""

    text: str
    sources: List[str] = field(default_factory=list)


@dataclass
class KnowledgeTriplet:
    """A knowledge triplet (subject, predicate, object)."""

    subject: str
    predicate: str
    object: str
    source: str


@dataclass
class KnowledgeGraph:
    """Complete knowledge graph for a topic."""

    topic: str
    questions: List[Question] = field(default_factory=list)
    triplets: List[KnowledgeTriplet] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    timestamp: str = ""
