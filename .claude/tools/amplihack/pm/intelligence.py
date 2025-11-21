"""PM intelligence module for AI-assisted backlog analysis and recommendations.

This module provides AI capabilities for analyzing backlog items, detecting
dependencies, estimating complexity, and providing smart recommendations for
what work to tackle next.

Public API:
    - BacklogAnalyzer: Analyze backlog items for selection criteria
    - ProjectAnalyzer: Understand project structure and patterns
    - DependencyAnalyzer: Identify dependencies between items
    - ComplexityEstimator: Estimate effort and complexity
    - RecommendationEngine: Multi-criteria ranking and suggestions

Philosophy:
    - Practical AI assistance (not over-engineered)
    - Transparent reasoning (always explain why)
    - Confidence scores (honest about uncertainty)
    - Ruthless simplicity
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .state import BacklogItem, PMConfig, PMStateManager

__all__ = [
    "BacklogAnalyzer",
    "ProjectAnalyzer",
    "DependencyAnalyzer",
    "ComplexityEstimator",
    "RecommendationEngine",
    "Recommendation",
    "RichDelegationPackage",
]


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class Recommendation:
    """Smart recommendation for backlog item to work on next."""

    backlog_item: BacklogItem
    rank: int  # 1, 2, 3
    score: float  # 0.0-100.0
    confidence: float  # 0.0-1.0
    rationale: str  # Why this item now
    complexity: str  # simple, medium, complex
    blocking_count: int  # How many items this unblocks
    dependencies: List[str]  # IDs of items this depends on


@dataclass
class RichDelegationPackage:
    """Enhanced delegation package with AI-generated context.

    Includes everything from DelegationPackage plus:
    - Relevant code patterns found in project
    - Similar implementations for reference
    - Comprehensive test requirements
    - Architectural notes and constraints
    """

    backlog_item: BacklogItem
    agent_role: str
    project_context: str
    instructions: str
    success_criteria: List[str]
    estimated_hours: int
    complexity: str  # simple, medium, complex
    relevant_files: List[str]  # Files agent should examine
    similar_patterns: List[str]  # Similar code in project
    test_requirements: List[str]  # Specific tests needed
    architectural_notes: str  # Design constraints/patterns
    dependencies: List[str]  # Other backlog items this depends on


# =============================================================================
# Backlog Analyzer
# =============================================================================


class BacklogAnalyzer:
    """Analyze backlog items for selection and prioritization.

    Capabilities:
    - Parse item titles/descriptions for keywords
    - Identify item types (feature, bug, refactor, etc.)
    - Extract technical requirements
    - Assess business value signals
    """

    # Keywords for categorization
    FEATURE_KEYWORDS = {"add", "implement", "create", "new", "feature"}
    BUG_KEYWORDS = {"fix", "bug", "issue", "error", "broken"}
    REFACTOR_KEYWORDS = {"refactor", "clean", "improve", "optimize", "restructure"}
    DOC_KEYWORDS = {"document", "docs", "readme", "comment", "explain"}
    TEST_KEYWORDS = {"test", "coverage", "verify", "validate"}

    def __init__(self, config: PMConfig):
        """Initialize analyzer with project config."""
        self.config = config

    def categorize_item(self, item: BacklogItem) -> str:
        """Categorize item as feature, bug, refactor, doc, or test."""
        text = (item.title + " " + item.description).lower()

        # Check each category
        if any(kw in text for kw in self.BUG_KEYWORDS):
            return "bug"
        if any(kw in text for kw in self.TEST_KEYWORDS):
            return "test"
        if any(kw in text for kw in self.DOC_KEYWORDS):
            return "documentation"
        if any(kw in text for kw in self.REFACTOR_KEYWORDS):
            return "refactor"
        if any(kw in text for kw in self.FEATURE_KEYWORDS):
            return "feature"

        return "other"

    def extract_technical_signals(self, item: BacklogItem) -> Dict[str, Any]:
        """Extract technical signals from item.

        Returns dict with:
        - has_api_changes: bool
        - has_db_changes: bool
        - has_ui_changes: bool
        - mentions_testing: bool
        - mentions_security: bool
        """
        text = (item.title + " " + item.description).lower()

        return {
            "has_api_changes": any(kw in text for kw in ["api", "endpoint", "route"]),
            "has_db_changes": any(kw in text for kw in ["database", "db", "schema", "migration"]),
            "has_ui_changes": any(kw in text for kw in ["ui", "interface", "frontend", "view"]),
            "mentions_testing": any(kw in text for kw in ["test", "coverage", "verify"]),
            "mentions_security": any(kw in text for kw in ["security", "auth", "permission", "encryption"]),
        }

    def assess_business_value(self, item: BacklogItem, config: PMConfig) -> float:
        """Assess business value based on alignment with project goals.

        Returns score 0.0-1.0 based on:
        - Priority level (HIGH=1.0, MEDIUM=0.6, LOW=0.3)
        - Goal alignment (does item mention primary goals?)
        - Category (bugs higher than docs)
        """
        # Base score from priority
        priority_scores = {"HIGH": 1.0, "MEDIUM": 0.6, "LOW": 0.3}
        score = priority_scores.get(item.priority, 0.5)

        # Goal alignment bonus
        text = (item.title + " " + item.description).lower()
        for goal in config.primary_goals:
            if any(word in text for word in goal.lower().split()):
                score += 0.1  # +10% per matching goal

        # Category adjustments
        category = self.categorize_item(item)
        if category == "bug":
            score += 0.15  # Bugs get priority boost
        elif category == "documentation":
            score -= 0.05  # Docs slightly lower

        return min(score, 1.0)  # Cap at 1.0


# =============================================================================
# Project Analyzer
# =============================================================================


class ProjectAnalyzer:
    """Analyze project structure, patterns, and codebase."""

    def __init__(self, project_root: Path):
        """Initialize analyzer with project root."""
        self.project_root = project_root

    def find_relevant_files(self, item: BacklogItem, max_files: int = 10) -> List[str]:
        """Find files relevant to backlog item.

        Strategy:
        1. Extract keywords from title/description
        2. Search for files matching keywords
        3. Prioritize by file type and location
        """
        # Extract keywords (simple approach)
        text = item.title + " " + item.description
        words = re.findall(r'\b\w{3,}\b', text.lower())
        keywords = set(words) - {"the", "and", "for", "with", "from", "this", "that"}

        relevant = []

        # Search Python files in common locations
        search_paths = [
            self.project_root / "src",
            self.project_root / ".claude" / "tools",
            self.project_root / "tests",
        ]

        for search_path in search_paths:
            if not search_path.exists():
                continue

            for py_file in search_path.rglob("*.py"):
                # Check if filename or parent dir matches keywords
                file_parts = py_file.stem.lower().split("_")
                if any(kw in file_parts for kw in keywords):
                    relevant.append(str(py_file.relative_to(self.project_root)))

        return relevant[:max_files]

    def find_similar_patterns(self, item: BacklogItem, max_patterns: int = 5) -> List[str]:
        """Find similar code patterns in project.

        Returns list of descriptions like:
        - "Similar class structure in src/foo/bar.py"
        - "Similar API pattern in src/api/endpoints.py"
        """
        category = BacklogAnalyzer(PMConfig(
            project_name="temp",
            project_type="other",
            primary_goals=[],
            quality_bar="balanced",
            initialized_at="",
        )).categorize_item(item)

        patterns = []

        # Category-specific pattern hints
        if category == "feature":
            patterns.append("Look for similar feature implementations in src/")
            patterns.append("Check existing tests for pattern examples")
        elif category == "bug":
            patterns.append("Search for similar error handling patterns")
            patterns.append("Look for existing fixes to similar issues")
        elif category == "test":
            patterns.append("Review existing test structure in tests/")
            patterns.append("Check conftest.py for fixture patterns")

        # Generic patterns
        patterns.append("Follow existing code organization patterns")
        patterns.append("Match current naming conventions")

        return patterns[:max_patterns]

    def analyze_codebase_size(self) -> Dict[str, int]:
        """Get basic codebase metrics."""
        metrics = {
            "python_files": 0,
            "total_lines": 0,
            "test_files": 0,
        }

        src_paths = [
            self.project_root / "src",
            self.project_root / ".claude" / "tools",
        ]

        for src_path in src_paths:
            if not src_path.exists():
                continue

            for py_file in src_path.rglob("*.py"):
                metrics["python_files"] += 1
                try:
                    metrics["total_lines"] += len(py_file.read_text().splitlines())
                except Exception:
                    pass

        # Count test files
        test_path = self.project_root / "tests"
        if test_path.exists():
            metrics["test_files"] = len(list(test_path.rglob("test_*.py")))

        return metrics


# =============================================================================
# Dependency Analyzer
# =============================================================================


class DependencyAnalyzer:
    """Detect dependencies between backlog items."""

    def __init__(self, backlog_items: List[BacklogItem]):
        """Initialize with all backlog items."""
        self.items = {item.id: item for item in backlog_items}

    def detect_dependencies(self, item: BacklogItem) -> List[str]:
        """Detect which items this item depends on.

        Strategy:
        1. Look for explicit references (BL-001, BL-002)
        2. Look for blocking keywords ("blocks", "depends on")
        3. Check for shared components/areas
        """
        dependencies = []

        text = (item.title + " " + item.description).lower()

        # Explicit ID references
        id_pattern = r'bl-\d{3}'
        matches = re.findall(id_pattern, text, re.IGNORECASE)
        dependencies.extend(m.upper() for m in matches if m.upper() in self.items)

        # Check for blocking relationships in other items
        for other_id, other_item in self.items.items():
            if other_id == item.id:
                continue

            other_text = (other_item.title + " " + other_item.description).lower()

            # Does other item mention this item as blocking?
            if item.id.lower() in other_text and any(kw in other_text for kw in ["blocks", "required for", "prerequisite"]):
                if other_id not in dependencies:
                    dependencies.append(other_id)

        return dependencies

    def count_blocking(self, item: BacklogItem) -> int:
        """Count how many items this item would unblock.

        Items that are blocked by this item.
        """
        count = 0
        for other_item in self.items.values():
            if other_item.id == item.id:
                continue

            deps = self.detect_dependencies(other_item)
            if item.id in deps:
                count += 1

        return count


# =============================================================================
# Complexity Estimator
# =============================================================================


class ComplexityEstimator:
    """Estimate complexity and effort for backlog items."""

    def estimate_complexity(self, item: BacklogItem) -> str:
        """Estimate complexity: simple, medium, complex.

        Based on:
        - Estimated hours (< 2 = simple, 2-6 = medium, > 6 = complex)
        - Technical signals (API/DB changes increase complexity)
        - Description length (longer = more complex)
        """
        # Start with estimated hours
        if item.estimated_hours < 2:
            base = "simple"
        elif item.estimated_hours <= 6:
            base = "medium"
        else:
            base = "complex"

        # Check technical signals
        analyzer = BacklogAnalyzer(PMConfig(
            project_name="temp",
            project_type="other",
            primary_goals=[],
            quality_bar="balanced",
            initialized_at="",
        ))
        signals = analyzer.extract_technical_signals(item)

        # Multiple technical areas = higher complexity
        complexity_count = sum(1 for v in signals.values() if v)
        if complexity_count >= 3:
            if base == "simple":
                base = "medium"
            elif base == "medium":
                base = "complex"

        return base

    def estimate_confidence(self, item: BacklogItem) -> float:
        """Estimate confidence in our analysis (0.0-1.0).

        Higher confidence when:
        - Description is detailed
        - Clear technical requirements
        - Explicit priority set
        """
        confidence = 0.5  # Start neutral

        # Detailed description = higher confidence
        if len(item.description) > 100:
            confidence += 0.2
        elif len(item.description) > 50:
            confidence += 0.1

        # Explicit priority = higher confidence
        if item.priority in ["HIGH", "LOW"]:  # Explicit choice
            confidence += 0.1

        # Tags provide context = higher confidence
        if item.tags:
            confidence += 0.1

        return min(confidence, 1.0)


# =============================================================================
# Recommendation Engine
# =============================================================================


class RecommendationEngine:
    """Multi-criteria recommendation engine for backlog selection.

    Scoring formula:
    - Priority weight: 40% (HIGH=1.0, MEDIUM=0.6, LOW=0.3)
    - Blocking impact: 30% (normalized by max blocking count)
    - Ease: 20% (inverse of complexity)
    - Goal alignment: 10% (business value)
    """

    def __init__(
        self,
        state_manager: PMStateManager,
        project_root: Path,
    ):
        """Initialize recommendation engine."""
        self.state_manager = state_manager
        self.project_root = project_root
        self.config = state_manager.get_config()

    def generate_recommendations(
        self,
        max_recommendations: int = 3,
    ) -> List[Recommendation]:
        """Generate top N recommendations for what to work on next.

        Process:
        1. Get all READY backlog items
        2. Analyze each item (dependencies, complexity, value)
        3. Score each item using multi-criteria formula
        4. Return top N with rationale
        """
        # Get ready items
        items = self.state_manager.get_backlog_items(status="READY")
        if not items:
            return []

        # Initialize analyzers
        backlog_analyzer = BacklogAnalyzer(self.config)
        project_analyzer = ProjectAnalyzer(self.project_root)
        dep_analyzer = DependencyAnalyzer(items)
        complexity_estimator = ComplexityEstimator()

        # Score each item
        recommendations = []
        for item in items:
            # Analyze item
            complexity = complexity_estimator.estimate_complexity(item)
            dependencies = dep_analyzer.detect_dependencies(item)
            blocking_count = dep_analyzer.count_blocking(item)
            business_value = backlog_analyzer.assess_business_value(item, self.config)
            confidence = complexity_estimator.estimate_confidence(item)

            # Skip if has unmet dependencies
            if dependencies:
                unmet = [dep for dep in dependencies if self.state_manager.get_backlog_item(dep).status != "DONE"]
                if unmet:
                    continue  # Can't do this yet

            # Calculate score components
            priority_score = self._priority_score(item.priority)
            blocking_score = self._blocking_score(blocking_count, len(items))
            ease_score = self._ease_score(complexity)
            goal_score = business_value

            # Weighted total
            total_score = (
                priority_score * 0.40 +
                blocking_score * 0.30 +
                ease_score * 0.20 +
                goal_score * 0.10
            ) * 100

            # Generate rationale
            rationale = self._generate_rationale(
                item=item,
                complexity=complexity,
                blocking_count=blocking_count,
                priority_score=priority_score,
                business_value=business_value,
            )

            recommendations.append(Recommendation(
                backlog_item=item,
                rank=0,  # Set after sorting
                score=total_score,
                confidence=confidence,
                rationale=rationale,
                complexity=complexity,
                blocking_count=blocking_count,
                dependencies=dependencies,
            ))

        # Sort by score descending
        recommendations.sort(key=lambda r: r.score, reverse=True)

        # Assign ranks
        for i, rec in enumerate(recommendations[:max_recommendations]):
            rec.rank = i + 1

        return recommendations[:max_recommendations]

    def create_rich_delegation_package(
        self,
        backlog_id: str,
        agent: str = "builder",
    ) -> RichDelegationPackage:
        """Create enhanced delegation package with AI analysis.

        Includes:
        - All standard delegation info
        - Relevant files to examine
        - Similar patterns in codebase
        - Comprehensive test requirements
        - Architectural notes
        """
        # Load backlog item
        item = self.state_manager.get_backlog_item(backlog_id)
        if not item:
            raise ValueError(f"Backlog item {backlog_id} not found")

        # Initialize analyzers
        backlog_analyzer = BacklogAnalyzer(self.config)
        project_analyzer = ProjectAnalyzer(self.project_root)
        dep_analyzer = DependencyAnalyzer(self.state_manager.get_backlog_items())
        complexity_estimator = ComplexityEstimator()

        # Analyze item
        complexity = complexity_estimator.estimate_complexity(item)
        relevant_files = project_analyzer.find_relevant_files(item)
        similar_patterns = project_analyzer.find_similar_patterns(item)
        dependencies = dep_analyzer.detect_dependencies(item)
        category = backlog_analyzer.categorize_item(item)

        # Generate test requirements
        test_requirements = self._generate_test_requirements(item, category)

        # Generate architectural notes
        arch_notes = self._generate_architectural_notes(item, category, complexity)

        # Generate instructions (agent-specific)
        instructions = self._generate_rich_instructions(agent, item, category)

        # Success criteria
        success_criteria = [
            "All requirements implemented and working",
            "Tests pass (if applicable)",
            "Code follows project philosophy (ruthless simplicity)",
            "No stubs or placeholders",
            "Documentation updated",
        ]

        # Load project context
        project_context = self._load_project_context()

        return RichDelegationPackage(
            backlog_item=item,
            agent_role=agent,
            project_context=project_context,
            instructions=instructions,
            success_criteria=success_criteria,
            estimated_hours=item.estimated_hours,
            complexity=complexity,
            relevant_files=relevant_files,
            similar_patterns=similar_patterns,
            test_requirements=test_requirements,
            architectural_notes=arch_notes,
            dependencies=dependencies,
        )

    # =========================================================================
    # Private Helpers
    # =========================================================================

    def _priority_score(self, priority: str) -> float:
        """Convert priority to score (0.0-1.0)."""
        return {"HIGH": 1.0, "MEDIUM": 0.6, "LOW": 0.3}.get(priority, 0.5)

    def _blocking_score(self, blocking_count: int, total_items: int) -> float:
        """Calculate blocking impact score (0.0-1.0)."""
        if total_items == 0:
            return 0.0
        return min(blocking_count / max(total_items * 0.3, 1), 1.0)  # Normalize

    def _ease_score(self, complexity: str) -> float:
        """Calculate ease score (inverse of complexity)."""
        return {"simple": 1.0, "medium": 0.6, "complex": 0.3}.get(complexity, 0.5)

    def _generate_rationale(
        self,
        item: BacklogItem,
        complexity: str,
        blocking_count: int,
        priority_score: float,
        business_value: float,
    ) -> str:
        """Generate human-readable rationale for recommendation."""
        reasons = []

        # Priority
        if priority_score >= 0.9:
            reasons.append("HIGH priority")
        elif priority_score <= 0.4:
            reasons.append("LOW priority but valuable")

        # Blocking
        if blocking_count > 0:
            reasons.append(f"unblocks {blocking_count} other item(s)")

        # Complexity
        if complexity == "simple":
            reasons.append("quick win (simple)")
        elif complexity == "complex":
            reasons.append("complex but important")

        # Business value
        if business_value > 0.7:
            reasons.append("high business value")

        if not reasons:
            reasons.append("good next step")

        return "Recommended because: " + ", ".join(reasons)

    def _generate_test_requirements(self, item: BacklogItem, category: str) -> List[str]:
        """Generate specific test requirements for item."""
        requirements = []

        if category == "feature":
            requirements.extend([
                "Unit tests for new functions/classes",
                "Integration tests for feature workflow",
                "Edge case coverage (empty inputs, invalid data)",
                "Test success and error paths",
            ])
        elif category == "bug":
            requirements.extend([
                "Regression test that fails before fix",
                "Test passes after fix",
                "Test edge cases related to bug",
            ])
        elif category == "refactor":
            requirements.extend([
                "All existing tests still pass",
                "No behavior changes",
                "Code coverage maintained or improved",
            ])
        elif category == "test":
            requirements.extend([
                "Tests cover stated requirements",
                "Tests are maintainable and clear",
                "Tests run quickly (< 1s per test)",
            ])
        else:
            requirements.extend([
                "Add tests appropriate for changes",
                "Ensure existing tests pass",
            ])

        return requirements

    def _generate_architectural_notes(
        self,
        item: BacklogItem,
        category: str,
        complexity: str,
    ) -> str:
        """Generate architectural guidance for item."""
        notes = []

        # Complexity-based guidance
        if complexity == "simple":
            notes.append("Keep it simple - single file or function if possible")
        elif complexity == "complex":
            notes.append("Break into smaller, testable components")
            notes.append("Consider creating module structure with clear contracts")

        # Category-specific guidance
        if category == "feature":
            notes.append("Follow existing patterns in codebase")
            notes.append("Consider extension points for future needs")
        elif category == "refactor":
            notes.append("Maintain backward compatibility unless explicitly removing")
            notes.append("Make changes incrementally if possible")

        # Project quality bar
        config = self.state_manager.get_config()
        if config.quality_bar == "strict":
            notes.append("High quality bar - thorough testing required")
        elif config.quality_bar == "relaxed":
            notes.append("Move quickly - iterate and improve later")

        return "\n".join(f"- {note}" for note in notes)

    def _generate_rich_instructions(
        self,
        agent: str,
        item: BacklogItem,
        category: str,
    ) -> str:
        """Generate enhanced agent-specific instructions."""
        # Start with agent-specific template
        templates = {
            "builder": """1. Analyze requirements and examine relevant files listed below
2. Design solution following existing patterns
3. Implement working code (no stubs or placeholders)
4. Add comprehensive tests per test requirements
5. Follow architectural notes
6. Update documentation

Focus on ruthless simplicity. Start with simplest solution that works.""",
            "reviewer": """1. Review code for philosophy compliance
2. Verify no stubs, placeholders, or dead code
3. Check test coverage against requirements
4. Validate architectural notes followed
5. Look for unnecessary complexity
6. Ensure documentation updated

Focus on ruthless simplicity and zero-BS implementation.""",
            "tester": """1. Analyze behavior and contracts
2. Review test requirements below
3. Design tests for edge cases
4. Implement comprehensive coverage
5. Verify all tests pass
6. Document test scenarios

Focus on testing behavior, not implementation details.""",
        }

        base = templates.get(agent, "Complete task following project philosophy")

        # Add category-specific guidance
        if category == "bug":
            base += "\n\n**Bug Fix Workflow**: Write failing test first, then fix, verify test passes."
        elif category == "refactor":
            base += "\n\n**Refactor Workflow**: Ensure tests pass before and after. No behavior changes."

        return base

    def _load_project_context(self) -> str:
        """Load project context from config and roadmap."""
        config = self.state_manager.get_config()

        context = f"""**Project**: {config.project_name}
**Type**: {config.project_type}
**Quality Bar**: {config.quality_bar}

**Primary Goals**:
"""
        for goal in config.primary_goals:
            context += f"- {goal}\n"

        # Add roadmap snippet
        roadmap_path = self.state_manager.pm_dir / "roadmap.md"
        if roadmap_path.exists():
            roadmap = roadmap_path.read_text()
            context += f"\n**Roadmap Summary**:\n{roadmap[:500]}"

        return context
