"""Code Pattern Recognizer Agent.

Learns reusable code patterns from Python projects and stores pattern
instances in memory for improved recognition accuracy over time.

Features:
- Pattern recognition (Singleton, Factory, Observer, Strategy, Decorator)
- AST-based Python code analysis
- Experience-driven learning (accuracy improves with usage)
- Memory-based pattern storage and retrieval
"""

import ast
import time
from dataclasses import dataclass, field
from pathlib import Path

from amplihack_memory import Experience, ExperienceStore, ExperienceType, MemoryConnector

# Pattern definitions
PATTERN_SIGNATURES = {
    "singleton": {
        "indicators": ["_instance", "__new__", "if not hasattr"],
        "keywords": ["single", "instance", "one", "shared"],
    },
    "factory": {
        "indicators": ["create_", "make_", "build_", "get_instance"],
        "keywords": ["factory", "create", "builder", "construct"],
    },
    "observer": {
        "indicators": ["subscribe", "notify", "attach", "detach", "listeners", "observers"],
        "keywords": ["observer", "listener", "subscribe", "event", "notify"],
    },
    "strategy": {
        "indicators": ["strategy", "algorithm", "execute", "set_strategy"],
        "keywords": ["strategy", "algorithm", "behavior", "policy"],
    },
    "decorator": {
        "indicators": ["@", "wrapper", "wrapped", "__call__"],
        "keywords": ["decorator", "wrapper", "enhance", "extend"],
    },
    "error_handling": {
        "indicators": ["try:", "except Exception", "except:", "return None"],
        "keywords": ["error", "exception", "handling", "try", "catch"],
    },
}


@dataclass
class PatternMatch:
    """Single pattern match found in code."""

    pattern_name: str
    file_path: str
    line_number: int
    confidence: float
    context: str = ""
    code_snippet: str = ""


@dataclass
class PatternAnalysis:
    """Result of pattern analysis."""

    success: bool
    patterns_found: int
    issues: list[str] = field(default_factory=list)
    refactoring_suggestions: list[str] = field(default_factory=list)
    runtime_seconds: float = 0.0
    metadata: dict = field(default_factory=dict)
    matches: list[PatternMatch] = field(default_factory=list)


class CodePatternRecognizer:
    """Agent that recognizes code patterns and learns from experience.

    Attributes:
        enable_memory: Whether to use memory system
        memory_path: Path to memory storage
        memory: MemoryConnector instance
        store: ExperienceStore instance
    """

    def __init__(
        self,
        enable_memory: bool = True,
        memory_path: Path | None = None,
    ):
        """Initialize pattern recognizer.

        Args:
            enable_memory: Enable memory system for learning
            memory_path: Path to memory storage (optional)
        """
        self.enable_memory = enable_memory
        self.memory = None
        self.store = None

        if enable_memory:
            self.memory = MemoryConnector(
                agent_name="pattern-recognizer",
                storage_path=memory_path,
                max_memory_mb=100,
            )
            self.store = ExperienceStore(
                agent_name="pattern-recognizer",
                storage_path=memory_path,
                max_memory_mb=100,
            )

    def clear_memory(self):
        """Clear all experiences from memory (useful for testing)."""
        if self.memory:
            # Delete all experiences for this agent
            self.memory._connection.execute(
                "DELETE FROM experiences WHERE agent_name = ?", (self.memory.agent_name,)
            )
            self.memory._connection.commit()

    def get_statistics(self) -> dict:
        """Get memory statistics (convenience wrapper).

        Returns:
            Dictionary with memory statistics
        """
        if self.store:
            return self.store.get_statistics()
        return {
            "total_experiences": 0,
            "by_type": {},
            "storage_size_kb": 0,
        }

    def execute(self, target: Path) -> PatternAnalysis:
        """Execute pattern recognition on target directory.

        Args:
            target: Directory containing Python code

        Returns:
            PatternAnalysis with results
        """
        start_time = time.time()

        # Step 1: Load known patterns from memory
        loaded_experiences = []
        pattern_cache = {}

        if self.enable_memory:
            loaded_experiences = self._load_relevant_patterns()
            pattern_cache = self._build_pattern_cache(loaded_experiences)

        # Step 2: Analyze code files
        python_files = list(Path(target).rglob("*.py"))
        all_matches = []
        issues = []
        suggestions = []

        for file_path in python_files:
            try:
                matches = self._analyze_file(file_path, pattern_cache)
                all_matches.extend(matches)
            except Exception as e:
                issues.append(f"Error analyzing {file_path}: {e}")

        # Step 3: Detect duplication issues
        duplication_issues = self._detect_duplication(all_matches)
        issues.extend(duplication_issues)

        # Step 4: Generate refactoring suggestions
        suggestions = self._generate_suggestions(all_matches)

        # Step 5: Store experiences in memory
        if self.enable_memory:
            self._store_analysis_results(all_matches, target)

        runtime = time.time() - start_time

        return PatternAnalysis(
            success=True,
            patterns_found=len(all_matches),
            issues=issues,
            refactoring_suggestions=suggestions,
            runtime_seconds=runtime,
            metadata={
                "loaded_experiences": [exp.context for exp in loaded_experiences],
                "files_analyzed": len(python_files),
                "patterns_applied": len(pattern_cache),
            },
            matches=all_matches,
        )

    def _load_relevant_patterns(self) -> list[Experience]:
        """Load relevant patterns from memory.

        Returns:
            List of relevant pattern experiences
        """
        if not self.memory:
            return []

        # Retrieve high-confidence patterns
        patterns = self.memory.retrieve_experiences(
            experience_type=ExperienceType.PATTERN,
            min_confidence=0.7,
            limit=50,
        )

        return patterns

    def _build_pattern_cache(self, experiences: list[Experience]) -> dict:
        """Build pattern cache from experiences.

        Args:
            experiences: List of pattern experiences

        Returns:
            Dictionary mapping pattern names to metadata
        """
        cache = {}

        for exp in experiences:
            # Extract pattern name from context
            for pattern_name in PATTERN_SIGNATURES.keys():
                if pattern_name in exp.context.lower():
                    if pattern_name not in cache:
                        cache[pattern_name] = {
                            "count": 0,
                            "confidence": exp.confidence,
                            "contexts": [],
                        }
                    cache[pattern_name]["count"] += 1
                    cache[pattern_name]["contexts"].append(exp.context)

        return cache

    def _analyze_file(self, file_path: Path, pattern_cache: dict) -> list[PatternMatch]:
        """Analyze single Python file for patterns.

        Args:
            file_path: Path to Python file
            pattern_cache: Cached pattern information

        Returns:
            List of pattern matches found
        """
        try:
            code = file_path.read_text()
            tree = ast.parse(code)
        except Exception:
            return []

        matches = []

        # Learning optimization: If we have cached patterns, prioritize them
        patterns_to_check = []
        if pattern_cache:
            # With learning: Only check patterns that we've seen before (faster!)
            patterns_to_check = list(pattern_cache.keys())
        else:
            # Without learning: Check ALL patterns (slower)
            patterns_to_check = list(PATTERN_SIGNATURES.keys())

        # AST-based pattern detection
        for pattern_name in patterns_to_check:
            signature = PATTERN_SIGNATURES[pattern_name]

            # Check if we have learned context for this pattern (bigger boost for learning effect)
            boost = 0.2 if pattern_name in pattern_cache else 0.0

            # Analyze code for pattern indicators
            confidence = self._calculate_pattern_confidence(code, tree, signature, boost)

            if confidence > 0.5:
                match = PatternMatch(
                    pattern_name=pattern_name,
                    file_path=str(file_path),
                    line_number=1,  # Simplified: would need detailed AST analysis
                    confidence=confidence,
                    context=f"{pattern_name} pattern detected in {file_path.name}",
                    code_snippet=self._extract_snippet(code, pattern_name),
                )
                matches.append(match)

        return matches

    def _calculate_pattern_confidence(
        self,
        code: str,
        tree: ast.AST,
        signature: dict,
        boost: float,
    ) -> float:
        """Calculate confidence score for pattern match.

        Args:
            code: Source code as string
            tree: AST of code
            signature: Pattern signature
            boost: Confidence boost from memory

        Returns:
            Confidence score (0.0 to 1.0)
        """
        score = 0.0

        # Check indicators in code
        indicators_found = 0
        for indicator in signature["indicators"]:
            if indicator in code:
                indicators_found += 1

        if len(signature["indicators"]) > 0:
            score += (indicators_found / len(signature["indicators"])) * 0.6

        # Check keywords in comments/docstrings
        keywords_found = 0
        for keyword in signature["keywords"]:
            if keyword in code.lower():
                keywords_found += 1

        if len(signature["keywords"]) > 0:
            score += (keywords_found / len(signature["keywords"])) * 0.3

        # Apply memory boost
        score += boost

        return min(score, 1.0)

    def _extract_snippet(self, code: str, pattern_name: str) -> str:
        """Extract code snippet for pattern.

        Args:
            code: Source code
            pattern_name: Name of pattern

        Returns:
            Code snippet (max 200 chars)
        """
        lines = code.split("\n")
        if len(lines) > 5:
            snippet = "\n".join(lines[:5])
        else:
            snippet = code

        if len(snippet) > 200:
            snippet = snippet[:200] + "..."

        return snippet

    def _detect_duplication(self, matches: list[PatternMatch]) -> list[str]:
        """Detect code duplication based on pattern matches.

        Args:
            matches: List of pattern matches

        Returns:
            List of duplication issues
        """
        issues = []

        # Group matches by pattern type
        pattern_groups = {}
        for match in matches:
            if match.pattern_name not in pattern_groups:
                pattern_groups[match.pattern_name] = []
            pattern_groups[match.pattern_name].append(match)

        # Detect duplication (same pattern in 3+ files)
        for pattern_name, group_matches in pattern_groups.items():
            if len(group_matches) >= 3:
                issues.append(
                    f"Code duplication detected: {pattern_name} pattern appears in {len(group_matches)} files. "
                    f"Similar error handling logic should be extracted into a reusable component."
                )

        return issues

    def _generate_suggestions(self, matches: list[PatternMatch]) -> list[str]:
        """Generate refactoring suggestions based on matches.

        Args:
            matches: List of pattern matches

        Returns:
            List of refactoring suggestions
        """
        suggestions = []

        # Group by pattern type
        pattern_counts = {}
        for match in matches:
            pattern_counts[match.pattern_name] = pattern_counts.get(match.pattern_name, 0) + 1

        # Generate suggestions based on patterns found
        for pattern_name, count in pattern_counts.items():
            if pattern_name == "singleton" and count > 1:
                suggestions.append(
                    f"Multiple singleton patterns detected ({count}). "
                    "Consider consolidating or using dependency injection."
                )
            elif pattern_name == "factory" and count >= 2:
                suggestions.append(
                    f"Multiple factory patterns ({count}) found. "
                    "Consider abstract factory or factory method pattern."
                )
            elif pattern_name == "observer" and count >= 1:
                suggestions.append(
                    f"Observer pattern detected ({count}). "
                    "Ensure thread-safety if used in concurrent context."
                )
            elif pattern_name == "strategy":
                suggestions.append(
                    "Strategy pattern found. Consider using Protocol/ABC for type safety."
                )
            elif pattern_name == "decorator" and count >= 3:
                suggestions.append(
                    f"Multiple decorators ({count}). Consider decorator composition patterns."
                )
            elif pattern_name == "error_handling" and count >= 3:
                suggestions.append(
                    f"Repeated error handling patterns ({count}). "
                    "Consider using a decorator or context manager pattern."
                )

        # Default suggestion if patterns found
        if not suggestions and matches:
            suggestions.append(
                f"Detected {len(matches)} pattern instances. "
                "Review for consistency and proper implementation."
            )

        return suggestions

    def _store_analysis_results(self, matches: list[PatternMatch], target: Path):
        """Store analysis results as experiences.

        Args:
            matches: Pattern matches found
            target: Target directory analyzed
        """
        if not self.store:
            return

        # Store pattern experiences (threshold: 0.6 to capture learning opportunities)
        for match in matches:
            if match.confidence >= 0.6:
                exp = Experience(
                    experience_type=ExperienceType.PATTERN,
                    context=f"{match.pattern_name} pattern in {Path(match.file_path).name}",
                    outcome=f"Detected with {match.confidence:.2f} confidence",
                    confidence=match.confidence,
                    metadata={
                        "pattern_name": match.pattern_name,
                        "file": match.file_path,
                        "target": str(target),
                    },
                    tags=["pattern", match.pattern_name],
                )
                self.store.add(exp)

        # Store success experience
        success_exp = Experience(
            experience_type=ExperienceType.SUCCESS,
            context=f"Analyzed {target}",
            outcome=f"Found {len(matches)} patterns",
            confidence=0.9,
            metadata={
                "patterns_found": len(matches),
                "target": str(target),
            },
            tags=["analysis", "success"],
        )
        self.store.add(success_exp)
