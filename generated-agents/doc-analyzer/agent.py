"""
Documentation Analyzer Agent

A learning agent that analyzes Microsoft Learn documentation patterns,
stores learned patterns in memory, and improves analysis quality over time.
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

try:
    from amplihack_memory_lib import Experience, ExperienceStore, ExperienceType, MemoryConnector
except ImportError:
    raise ImportError(
        "amplihack-memory-lib is required. Install with: pip install amplihack-memory-lib"
    )


@dataclass
class SectionInfo:
    """Information about a documentation section."""

    heading: str
    level: int
    content: str
    word_count: int
    has_code_examples: bool
    has_links: bool


@dataclass
class DocAnalysis:
    """Complete documentation analysis result."""

    url: str
    title: str
    sections: list[SectionInfo]

    # Structure metrics
    heading_structure: list[int]  # Levels of headings
    max_depth: int
    section_count: int

    # Content metrics
    total_words: int
    code_examples_count: int
    links_count: int

    # Quality metrics
    structure_score: float  # 0-100
    completeness_score: float  # 0-100
    clarity_score: float  # 0-100
    overall_score: float  # 0-100

    # Learning metadata
    analysis_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    pattern_matches: dict[str, int] = field(default_factory=dict)
    learned_insights: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert analysis to dictionary."""
        return {
            "url": self.url,
            "title": self.title,
            "section_count": self.section_count,
            "total_words": self.total_words,
            "code_examples_count": self.code_examples_count,
            "links_count": self.links_count,
            "structure_score": self.structure_score,
            "completeness_score": self.completeness_score,
            "clarity_score": self.clarity_score,
            "overall_score": self.overall_score,
            "max_depth": self.max_depth,
            "heading_structure": self.heading_structure,
            "pattern_matches": self.pattern_matches,
            "learned_insights": self.learned_insights,
            "analysis_timestamp": self.analysis_timestamp,
        }


class DocumentationAnalyzer:
    """
    Learning agent that analyzes documentation and improves through experience.

    Key capabilities:
    1. Analyzes documentation structure and quality
    2. Stores analysis experiences in memory
    3. Retrieves past experiences to improve future analysis
    4. Learns patterns from high-quality documentation
    5. Tracks learning metrics over time
    """

    def __init__(self, memory_connector: MemoryConnector | None = None):
        """Initialize the analyzer with memory integration."""
        self.memory = memory_connector or MemoryConnector(agent_name="doc-analyzer")
        self.store = ExperienceStore(self.memory)

        # Pattern weights (learned from experience)
        self.pattern_weights = {
            "has_overview_section": 10,
            "has_prerequisites": 8,
            "has_code_examples": 15,
            "has_next_steps": 8,
            "balanced_depth": 12,
            "clear_headings": 10,
            "sufficient_content": 15,
            "good_link_density": 7,
            "logical_flow": 15,
        }

    def analyze_document(self, content: str, url: str = "unknown") -> DocAnalysis:
        """
        Analyze a documentation page with learned patterns.

        Args:
            content: Markdown content of the document
            url: URL of the document for tracking

        Returns:
            DocAnalysis with quality scores and learned insights
        """
        # 1. Retrieve past relevant experiences
        past_experiences = self._retrieve_relevant_experiences()

        # 2. Extract document structure
        title = self._extract_title(content)
        sections = self._parse_sections(content)

        # 3. Calculate base metrics
        heading_structure = [s.level for s in sections]
        max_depth = max(heading_structure) if heading_structure else 0
        total_words = sum(s.word_count for s in sections)
        code_examples_count = sum(1 for s in sections if s.has_code_examples)
        links_count = sum(1 for s in sections if s.has_links)

        # 4. Apply learned patterns for quality scoring
        pattern_matches = self._detect_patterns(sections, content)
        structure_score = self._calculate_structure_score(
            sections, heading_structure, pattern_matches, past_experiences
        )
        completeness_score = self._calculate_completeness_score(
            sections, code_examples_count, pattern_matches, past_experiences
        )
        clarity_score = self._calculate_clarity_score(
            sections, total_words, pattern_matches, past_experiences
        )

        # 5. Calculate overall score (weighted average)
        overall_score = structure_score * 0.35 + completeness_score * 0.35 + clarity_score * 0.30

        # 6. Generate learned insights
        learned_insights = self._generate_insights(pattern_matches, past_experiences, overall_score)

        # 7. Create analysis result
        analysis = DocAnalysis(
            url=url,
            title=title,
            sections=sections,
            heading_structure=heading_structure,
            max_depth=max_depth,
            section_count=len(sections),
            total_words=total_words,
            code_examples_count=code_examples_count,
            links_count=links_count,
            structure_score=structure_score,
            completeness_score=completeness_score,
            clarity_score=clarity_score,
            overall_score=overall_score,
            pattern_matches=pattern_matches,
            learned_insights=learned_insights,
        )

        # 8. Store experience for future learning
        self._store_analysis_experience(analysis)

        return analysis

    def _retrieve_relevant_experiences(self) -> list[dict[str, Any]]:
        """Retrieve past documentation analysis experiences."""
        try:
            experiences = self.store.search(query="documentation_analysis", limit=10)
            return [{"context": exp.context, "outcome": exp.outcome} for exp in experiences]
        except Exception:
            # Graceful degradation if memory unavailable
            return []

    def _extract_title(self, content: str) -> str:
        """Extract document title from content."""
        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
        return "Untitled Document"

    def _parse_sections(self, content: str) -> list[SectionInfo]:
        """Parse document into sections based on headings."""
        sections = []
        lines = content.split("\n")

        current_heading = None
        current_level = 0
        current_content = []

        for line in lines:
            # Check for markdown heading
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", line.strip())

            if heading_match:
                # Save previous section
                if current_heading:
                    sections.append(
                        self._create_section_info(
                            current_heading, current_level, "\n".join(current_content)
                        )
                    )

                # Start new section
                current_level = len(heading_match.group(1))
                current_heading = heading_match.group(2)
                current_content = []
            else:
                current_content.append(line)

        # Add final section
        if current_heading:
            sections.append(
                self._create_section_info(
                    current_heading, current_level, "\n".join(current_content)
                )
            )

        return sections

    def _create_section_info(self, heading: str, level: int, content: str) -> SectionInfo:
        """Create SectionInfo from heading and content."""
        word_count = len(content.split())
        has_code_examples = "```" in content or "    " in content
        has_links = "[" in content and "](" in content

        return SectionInfo(
            heading=heading,
            level=level,
            content=content,
            word_count=word_count,
            has_code_examples=has_code_examples,
            has_links=has_links,
        )

    def _detect_patterns(self, sections: list[SectionInfo], content: str) -> dict[str, int]:
        """Detect documentation patterns in the document."""
        patterns = {}

        # Check for common documentation sections
        section_headings = [s.heading.lower() for s in sections]
        patterns["has_overview_section"] = int(
            any("overview" in h or "introduction" in h for h in section_headings)
        )
        patterns["has_prerequisites"] = int(
            any("prerequisite" in h or "requirement" in h for h in section_headings)
        )
        patterns["has_next_steps"] = int(
            any("next step" in h or "what's next" in h for h in section_headings)
        )

        # Check structural patterns
        patterns["has_code_examples"] = int(any(s.has_code_examples for s in sections))
        patterns["balanced_depth"] = int(
            len(sections) > 0
            and max(s.level for s in sections) <= 4  # Not too deep
            and min(s.level for s in sections) >= 1  # Not too shallow
        )
        patterns["clear_headings"] = int(
            all(len(s.heading.split()) <= 8 for s in sections)  # Concise headings
        )

        # Check content patterns
        total_words = sum(s.word_count for s in sections)
        patterns["sufficient_content"] = int(total_words >= 300)  # Minimum content

        # Check link density
        links_count = sum(1 for s in sections if s.has_links)
        patterns["good_link_density"] = int(
            len(sections) > 0 and 0.2 <= (links_count / len(sections)) <= 0.8
        )

        # Check logical flow (increasing then decreasing depth suggests good structure)
        if len(sections) > 3:
            depths = [s.level for s in sections]
            has_progression = any(depths[i] > depths[i - 1] for i in range(1, len(depths)))
            patterns["logical_flow"] = int(has_progression)
        else:
            patterns["logical_flow"] = 0

        return patterns

    def _calculate_structure_score(
        self,
        sections: list[SectionInfo],
        heading_structure: list[int],
        patterns: dict[str, int],
        past_experiences: list[dict[str, Any]],
    ) -> float:
        """Calculate structure quality score using learned patterns."""
        if not sections:
            return 0.0

        score = 50.0  # Base score

        # Apply pattern weights
        if patterns.get("balanced_depth"):
            score += self.pattern_weights["balanced_depth"]
        if patterns.get("clear_headings"):
            score += self.pattern_weights["clear_headings"]
        if patterns.get("logical_flow"):
            score += self.pattern_weights["logical_flow"]

        # Learn from past experiences
        if past_experiences:
            avg_past_depth = self._get_avg_metric(past_experiences, "max_depth")
            if avg_past_depth and heading_structure:
                current_depth = max(heading_structure)
                # Reward similarity to successful past structures
                depth_similarity = 1.0 - abs(current_depth - avg_past_depth) / max(
                    current_depth, avg_past_depth
                )
                score += depth_similarity * 10

        return min(score, 100.0)

    def _calculate_completeness_score(
        self,
        sections: list[SectionInfo],
        code_examples_count: int,
        patterns: dict[str, int],
        past_experiences: list[dict[str, Any]],
    ) -> float:
        """Calculate completeness score using learned patterns."""
        score = 40.0  # Base score

        # Apply pattern weights
        if patterns.get("has_overview_section"):
            score += self.pattern_weights["has_overview_section"]
        if patterns.get("has_prerequisites"):
            score += self.pattern_weights["has_prerequisites"]
        if patterns.get("has_code_examples"):
            score += self.pattern_weights["has_code_examples"]
        if patterns.get("has_next_steps"):
            score += self.pattern_weights["has_next_steps"]
        if patterns.get("sufficient_content"):
            score += self.pattern_weights["sufficient_content"]

        # Learn from past experiences
        if past_experiences:
            avg_past_examples = self._get_avg_metric(past_experiences, "code_examples_count")
            if avg_past_examples is not None:
                # Reward having similar or more examples than past successful docs
                if code_examples_count >= avg_past_examples:
                    score += 10

        return min(score, 100.0)

    def _calculate_clarity_score(
        self,
        sections: list[SectionInfo],
        total_words: int,
        patterns: dict[str, int],
        past_experiences: list[dict[str, Any]],
    ) -> float:
        """Calculate clarity score using learned patterns."""
        score = 50.0  # Base score

        # Apply pattern weights
        if patterns.get("clear_headings"):
            score += self.pattern_weights["clear_headings"]
        if patterns.get("good_link_density"):
            score += self.pattern_weights["good_link_density"]

        # Check average section length (not too long, not too short)
        if sections:
            avg_section_words = total_words / len(sections)
            if 50 <= avg_section_words <= 400:
                score += 15
            elif 30 <= avg_section_words < 50 or 400 < avg_section_words <= 600:
                score += 8

        # Learn from past experiences
        if past_experiences:
            avg_past_words = self._get_avg_metric(past_experiences, "total_words")
            if avg_past_words and total_words:
                # Reward similarity to successful past word counts
                words_ratio = min(total_words, avg_past_words) / max(total_words, avg_past_words)
                score += words_ratio * 10

        return min(score, 100.0)

    def _get_avg_metric(self, experiences: list[dict[str, Any]], metric: str) -> float | None:
        """Calculate average of a metric from past experiences."""
        values = []
        for exp in experiences:
            outcome = exp.get("outcome", {})
            if isinstance(outcome, dict) and metric in outcome:
                values.append(outcome[metric])

        return sum(values) / len(values) if values else None

    def _generate_insights(
        self, patterns: dict[str, int], past_experiences: list[dict[str, Any]], overall_score: float
    ) -> list[str]:
        """Generate insights based on learned patterns."""
        insights = []

        # Pattern-based insights
        if not patterns.get("has_overview_section"):
            insights.append("Missing overview/introduction section")
        if not patterns.get("has_code_examples"):
            insights.append("No code examples found")
        if not patterns.get("balanced_depth"):
            insights.append("Heading depth imbalance detected")
        if not patterns.get("logical_flow"):
            insights.append("Consider improving section flow")

        # Learning-based insights
        if past_experiences:
            avg_past_score = self._get_avg_metric(past_experiences, "overall_score")
            if avg_past_score:
                if overall_score > avg_past_score + 10:
                    insights.append("Quality exceeds learned baseline (+improvement)")
                elif overall_score < avg_past_score - 10:
                    insights.append("Quality below learned baseline (-needs work)")

        # Quality threshold insights
        if overall_score >= 80:
            insights.append("High-quality documentation")
        elif overall_score < 60:
            insights.append("Significant improvements needed")

        return insights

    def _store_analysis_experience(self, analysis: DocAnalysis):
        """Store analysis as experience for future learning."""
        try:
            # Create experience object
            exp = Experience(
                experience_type=ExperienceType.SUCCESS
                if analysis.overall_score >= 70
                else ExperienceType.FAILURE,
                context=f"doc_analysis: {analysis.url[:100]}",
                outcome=json.dumps(
                    {
                        "score": analysis.overall_score,
                        "sections": len(analysis.sections_found),
                        "patterns": len(analysis.patterns_matched),
                    }
                ),
                confidence=min(analysis.overall_score / 100.0, 1.0),
                tags=["documentation", "ms_learn"]
                if "learn.microsoft" in analysis.url
                else ["documentation"],
            )

            # Store experience
            self.store.add(exp)
        except Exception as e:
            # Graceful degradation - analysis still works without memory storage
            print(f"Warning: Could not store experience: {e}")

    def get_learning_stats(self) -> dict[str, Any]:
        """Get statistics about the agent's learning progress."""
        try:
            experiences = self.store.retrieve_relevant(
                context={"type": "documentation_analysis"}, limit=100
            )

            if not experiences:
                return {
                    "total_analyses": 0,
                    "avg_quality": 0.0,
                    "trend": "no_data",
                }

            scores = [
                exp["outcome"].get("overall_score", 0)
                for exp in experiences
                if isinstance(exp.get("outcome"), dict)
            ]

            if not scores:
                return {
                    "total_analyses": len(experiences),
                    "avg_quality": 0.0,
                    "trend": "no_data",
                }

            # Calculate trend (comparing first half vs second half)
            mid = len(scores) // 2
            first_half_avg = sum(scores[:mid]) / len(scores[:mid]) if mid > 0 else 0
            second_half_avg = sum(scores[mid:]) / len(scores[mid:]) if len(scores[mid:]) > 0 else 0

            trend = (
                "improving"
                if second_half_avg > first_half_avg + 5
                else "declining"
                if second_half_avg < first_half_avg - 5
                else "stable"
            )

            return {
                "total_analyses": len(experiences),
                "avg_quality": sum(scores) / len(scores),
                "min_quality": min(scores),
                "max_quality": max(scores),
                "trend": trend,
                "first_half_avg": first_half_avg,
                "second_half_avg": second_half_avg,
                "improvement": second_half_avg - first_half_avg,
            }
        except Exception as e:
            return {
                "error": str(e),
                "total_analyses": 0,
                "avg_quality": 0.0,
                "trend": "error",
            }
