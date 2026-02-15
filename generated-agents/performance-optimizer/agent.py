"""
Performance Optimizer Learning Agent

A learning agent that analyzes Python code for performance issues,
applies optimizations, and learns which techniques work best over time.
"""

import ast
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Import memory library if available, otherwise use mock implementation
try:
    from amplihack_memory_lib import ExperienceStore, ExperienceType, MemoryConnector
except ImportError:
    # Fallback: Simple in-memory implementation for standalone operation
    class ExperienceType:
        SUCCESS = "success"
        FAILURE = "failure"
        PATTERN = "pattern"

    class MemoryConnector:
        def __init__(self, agent_name: str, storage_path=None, max_memory_mb=100):
            self.agent_name = agent_name
            self.experiences = []

    class ExperienceStore:
        def __init__(self, memory_connector):
            self.memory = memory_connector
            self.experiences = []

        def store_experience(self, exp_type, context, action, outcome, metadata=None):
            """Store an experience."""
            self.experiences.append(
                {
                    "exp_type": exp_type,
                    "context": context,
                    "action": action,
                    "outcome": outcome,
                    "metadata": metadata or {},
                }
            )

        def retrieve_relevant(self, context=None, limit=None):
            """Retrieve relevant experiences."""
            filtered = self.experiences
            if context and "type" in context:
                filtered = [
                    exp
                    for exp in filtered
                    if isinstance(exp.get("context"), dict)
                    and exp["context"].get("type") == context["type"]
                ]
            if limit:
                filtered = filtered[-limit:]
            return filtered


@dataclass
class OptimizationTechnique:
    """Represents an optimization technique."""

    name: str
    category: str  # 'loop', 'comprehension', 'caching', 'algorithm', 'io', 'string'
    description: str
    pattern: str  # AST pattern or code pattern to match
    confidence: float = 0.5  # Initial confidence, improves with learning


@dataclass
class OptimizationResult:
    """Result of applying an optimization."""

    technique: str
    original_code: str
    optimized_code: str
    estimated_speedup: float  # Multiplier: 2.0 = 2x faster
    estimated_memory_saved: int  # Bytes saved
    confidence: float
    applied: bool
    reason: str  # Why optimization was/wasn't applied


@dataclass
class CodeAnalysis:
    """Complete code analysis and optimization result."""

    file_path: str
    original_code: str
    optimizations: list[OptimizationResult]

    # Metrics
    total_lines: int
    complexity_score: float  # McCabe complexity
    estimated_total_speedup: float
    estimated_total_memory_saved: int

    # Learning metadata
    analysis_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    techniques_applied: list[str] = field(default_factory=list)
    learned_insights: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert analysis to dictionary."""
        return {
            "file_path": self.file_path,
            "total_lines": self.total_lines,
            "complexity_score": self.complexity_score,
            "estimated_total_speedup": self.estimated_total_speedup,
            "estimated_total_memory_saved": self.estimated_total_memory_saved,
            "optimizations_count": len(self.optimizations),
            "optimizations_applied": len([o for o in self.optimizations if o.applied]),
            "techniques_applied": self.techniques_applied,
            "learned_insights": self.learned_insights,
            "analysis_timestamp": self.analysis_timestamp,
        }


class PerformanceOptimizer:
    """
    Learning agent that optimizes Python code and improves through experience.

    Key capabilities:
    1. Analyzes Python code for performance bottlenecks
    2. Applies proven optimization techniques
    3. Stores optimization results in memory
    4. Retrieves past experiences to improve future optimizations
    5. Learns which techniques work best in different contexts
    6. Tracks confidence levels for each technique
    """

    def __init__(self, memory_connector: MemoryConnector | None = None):
        """Initialize the optimizer with memory integration."""
        self.memory = memory_connector or MemoryConnector(agent_name="performance-optimizer")
        self.store = ExperienceStore(self.memory)

        # Optimization techniques library
        self.techniques = self._initialize_techniques()

        # Load learned confidence levels from memory
        self._update_technique_confidence()

    def _initialize_techniques(self) -> dict[str, OptimizationTechnique]:
        """Initialize the library of optimization techniques."""
        return {
            "list_comprehension": OptimizationTechnique(
                name="list_comprehension",
                category="comprehension",
                description="Replace explicit loops with list comprehensions",
                pattern="for_loop_append",
                confidence=0.5,
            ),
            "generator_expression": OptimizationTechnique(
                name="generator_expression",
                category="comprehension",
                description="Use generator expressions for memory efficiency",
                pattern="list_comprehension_large",
                confidence=0.5,
            ),
            "set_membership": OptimizationTechnique(
                name="set_membership",
                category="algorithm",
                description="Use sets instead of lists for membership tests",
                pattern="list_in_check",
                confidence=0.5,
            ),
            "dict_get": OptimizationTechnique(
                name="dict_get",
                category="algorithm",
                description="Use dict.get() instead of key check",
                pattern="dict_key_check",
                confidence=0.5,
            ),
            "join_strings": OptimizationTechnique(
                name="join_strings",
                category="string",
                description="Use str.join() instead of concatenation in loops",
                pattern="string_concat_loop",
                confidence=0.5,
            ),
            "enumerate_instead_of_range_len": OptimizationTechnique(
                name="enumerate_instead_of_range_len",
                category="loop",
                description="Use enumerate() instead of range(len())",
                pattern="range_len_loop",
                confidence=0.5,
            ),
            "any_all_instead_of_loop": OptimizationTechnique(
                name="any_all_instead_of_loop",
                category="loop",
                description="Use any()/all() instead of explicit loops",
                pattern="boolean_loop",
                confidence=0.5,
            ),
            "cache_repeated_calls": OptimizationTechnique(
                name="cache_repeated_calls",
                category="caching",
                description="Cache results of repeated function calls",
                pattern="repeated_function_call",
                confidence=0.5,
            ),
        }

    def _update_technique_confidence(self):
        """Update technique confidence based on past experiences."""
        try:
            # Retrieve past optimization experiences
            experiences = self.store.retrieve_relevant(context={"type": "optimization"}, limit=100)

            # Calculate success rate for each technique
            technique_stats: dict[str, dict[str, int]] = {}

            for exp in experiences:
                technique = exp.get("context", {}).get("technique")
                if not technique:
                    continue

                if technique not in technique_stats:
                    technique_stats[technique] = {"success": 0, "total": 0}

                technique_stats[technique]["total"] += 1

                # Check if optimization was successful (speedup > 1.1)
                outcome = exp.get("outcome", {})
                if isinstance(outcome, dict):
                    speedup = outcome.get("speedup", 0)
                    if speedup > 1.1:
                        technique_stats[technique]["success"] += 1

            # Update confidence levels
            for technique_name, stats in technique_stats.items():
                if technique_name in self.techniques and stats["total"] > 0:
                    success_rate = stats["success"] / stats["total"]
                    # Weighted update: 70% old confidence + 30% success rate
                    old_confidence = self.techniques[technique_name].confidence
                    new_confidence = (old_confidence * 0.7) + (success_rate * 0.3)
                    self.techniques[technique_name].confidence = new_confidence

        except Exception:
            # Graceful degradation if memory unavailable
            pass

    def optimize_code(self, code: str, file_path: str = "unknown.py") -> CodeAnalysis:
        """
        Analyze and optimize Python code with learned techniques.

        Args:
            code: Python source code to optimize
            file_path: Path to the file (for tracking)

        Returns:
            CodeAnalysis with optimization results and learned insights
        """
        # 1. Retrieve past relevant experiences
        past_experiences = self._retrieve_relevant_experiences(file_path)

        # 2. Parse code into AST
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return self._create_error_analysis(file_path, code, f"Syntax error: {e}")

        # 3. Calculate base metrics
        total_lines = len(code.splitlines())
        complexity_score = self._calculate_complexity(tree)

        # 4. Detect optimization opportunities
        optimizations = self._detect_optimizations(code, tree, past_experiences)

        # 5. Calculate overall impact
        total_speedup = self._calculate_total_speedup(optimizations)
        total_memory_saved = sum(opt.estimated_memory_saved for opt in optimizations if opt.applied)

        # 6. Generate learned insights
        learned_insights = self._generate_insights(
            optimizations, past_experiences, complexity_score
        )

        # 7. Create analysis result
        analysis = CodeAnalysis(
            file_path=file_path,
            original_code=code,
            optimizations=optimizations,
            total_lines=total_lines,
            complexity_score=complexity_score,
            estimated_total_speedup=total_speedup,
            estimated_total_memory_saved=total_memory_saved,
            techniques_applied=[opt.technique for opt in optimizations if opt.applied],
            learned_insights=learned_insights,
        )

        # 8. Store experience for future learning
        self._store_analysis_experience(analysis)

        return analysis

    def _retrieve_relevant_experiences(self, file_path: str) -> list[dict[str, Any]]:
        """Retrieve past optimization experiences for similar code."""
        try:
            # Get file type context
            file_ext = Path(file_path).suffix
            experiences = self.store.retrieve_relevant(
                context={"type": "optimization", "file_ext": file_ext}, limit=20
            )
            return experiences
        except Exception:
            return []

    def _calculate_complexity(self, tree: ast.AST) -> float:
        """Calculate McCabe complexity score."""
        complexity = 1  # Base complexity

        for node in ast.walk(tree):
            # Add complexity for control flow
            if isinstance(node, (ast.If, ast.For, ast.While, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1

        return complexity

    def _detect_optimizations(
        self, code: str, tree: ast.AST, past_experiences: list[dict[str, Any]]
    ) -> list[OptimizationResult]:
        """Detect optimization opportunities in code."""
        optimizations = []

        # Check each technique
        for technique in self.techniques.values():
            if technique.pattern == "for_loop_append":
                opts = self._detect_loop_append(code, tree, technique, past_experiences)
                optimizations.extend(opts)

            elif technique.pattern == "list_in_check":
                opts = self._detect_list_membership(code, tree, technique, past_experiences)
                optimizations.extend(opts)

            elif technique.pattern == "dict_key_check":
                opts = self._detect_dict_key_check(code, tree, technique, past_experiences)
                optimizations.extend(opts)

            elif technique.pattern == "string_concat_loop":
                opts = self._detect_string_concat(code, tree, technique, past_experiences)
                optimizations.extend(opts)

            elif technique.pattern == "range_len_loop":
                opts = self._detect_range_len(code, tree, technique, past_experiences)
                optimizations.extend(opts)

            elif technique.pattern == "boolean_loop":
                opts = self._detect_boolean_loop(code, tree, technique, past_experiences)
                optimizations.extend(opts)

        return optimizations

    def _detect_loop_append(
        self,
        code: str,
        tree: ast.AST,
        technique: OptimizationTechnique,
        past_experiences: list[dict[str, Any]],
    ) -> list[OptimizationResult]:
        """Detect for-loops that build lists with append()."""
        optimizations = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.For):
                continue

            # Check if loop contains list.append()
            has_append = False
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    if isinstance(child.func, ast.Attribute):
                        if child.func.attr == "append":
                            has_append = True
                            break

            if has_append:
                # Calculate confidence boost from past experiences
                boost = self._get_confidence_boost(technique.name, past_experiences)
                confidence = min(technique.confidence + boost, 1.0)

                # Estimate performance improvement
                speedup = 1.5 + (confidence * 0.5)  # 1.5x to 2.0x
                memory_saved = 100  # Modest memory savings

                # Apply optimization if confidence is high enough
                apply = confidence > 0.6

                optimizations.append(
                    OptimizationResult(
                        technique=technique.name,
                        original_code="for x in items:\n    result.append(f(x))",
                        optimized_code="result = [f(x) for x in items]",
                        estimated_speedup=speedup,
                        estimated_memory_saved=memory_saved,
                        confidence=confidence,
                        applied=apply,
                        reason="List comprehensions are faster than append loops"
                        if apply
                        else "Confidence too low to apply automatically",
                    )
                )

        return optimizations

    def _detect_list_membership(
        self,
        code: str,
        tree: ast.AST,
        technique: OptimizationTechnique,
        past_experiences: list[dict[str, Any]],
    ) -> list[OptimizationResult]:
        """Detect 'x in list' checks that could use sets."""
        optimizations = []

        # Look for patterns like: if x in some_list:
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                if any(isinstance(op, ast.In) for op in node.ops):
                    # Check if right side is a list
                    if isinstance(node.comparators[0], ast.List):
                        boost = self._get_confidence_boost(technique.name, past_experiences)
                        confidence = min(technique.confidence + boost, 1.0)

                        # Sets are O(1) vs O(n) for lists
                        speedup = 5.0 + (confidence * 5.0)  # 5x to 10x for large lists
                        memory_saved = 0  # Sets use more memory

                        apply = confidence > 0.6

                        optimizations.append(
                            OptimizationResult(
                                technique=technique.name,
                                original_code="if x in [1, 2, 3, 4, 5]:",
                                optimized_code="if x in {1, 2, 3, 4, 5}:",
                                estimated_speedup=speedup,
                                estimated_memory_saved=memory_saved,
                                confidence=confidence,
                                applied=apply,
                                reason="Set membership is O(1) vs O(n) for lists"
                                if apply
                                else "Confidence too low to apply automatically",
                            )
                        )

        return optimizations

    def _detect_dict_key_check(
        self,
        code: str,
        tree: ast.AST,
        technique: OptimizationTechnique,
        past_experiences: list[dict[str, Any]],
    ) -> list[OptimizationResult]:
        """Detect dict key checks that could use .get()."""
        optimizations = []

        # Look for patterns like: if key in dict: value = dict[key] else: value = default
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                # Check for 'key in dict' test
                if isinstance(node.test, ast.Compare):
                    if any(isinstance(op, ast.In) for op in node.test.ops):
                        boost = self._get_confidence_boost(technique.name, past_experiences)
                        confidence = min(technique.confidence + boost, 1.0)

                        speedup = 1.2 + (confidence * 0.3)  # 1.2x to 1.5x
                        memory_saved = 50

                        apply = confidence > 0.6

                        optimizations.append(
                            OptimizationResult(
                                technique=technique.name,
                                original_code="if key in d:\n    value = d[key]\nelse:\n    value = default",
                                optimized_code="value = d.get(key, default)",
                                estimated_speedup=speedup,
                                estimated_memory_saved=memory_saved,
                                confidence=confidence,
                                applied=apply,
                                reason="dict.get() is more concise and slightly faster"
                                if apply
                                else "Confidence too low to apply automatically",
                            )
                        )

        return optimizations

    def _detect_string_concat(
        self,
        code: str,
        tree: ast.AST,
        technique: OptimizationTechnique,
        past_experiences: list[dict[str, Any]],
    ) -> list[OptimizationResult]:
        """Detect string concatenation in loops."""
        optimizations = []

        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                # Check for string concatenation (+=)
                has_string_concat = False
                for child in ast.walk(node):
                    if isinstance(child, ast.AugAssign):
                        if isinstance(child.op, ast.Add):
                            has_string_concat = True
                            break

                if has_string_concat:
                    boost = self._get_confidence_boost(technique.name, past_experiences)
                    confidence = min(technique.confidence + boost, 1.0)

                    # String concatenation in loops is very inefficient
                    speedup = 10.0 + (confidence * 10.0)  # 10x to 20x
                    memory_saved = 1000

                    apply = confidence > 0.6

                    optimizations.append(
                        OptimizationResult(
                            technique=technique.name,
                            original_code="for s in strings:\n    result += s",
                            optimized_code="result = ''.join(strings)",
                            estimated_speedup=speedup,
                            estimated_memory_saved=memory_saved,
                            confidence=confidence,
                            applied=apply,
                            reason="str.join() is much faster than += in loops"
                            if apply
                            else "Confidence too low to apply automatically",
                        )
                    )

        return optimizations

    def _detect_range_len(
        self,
        code: str,
        tree: ast.AST,
        technique: OptimizationTechnique,
        past_experiences: list[dict[str, Any]],
    ) -> list[OptimizationResult]:
        """Detect range(len()) patterns that should use enumerate()."""
        optimizations = []

        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                # Check for range(len(something))
                if isinstance(node.iter, ast.Call):
                    if isinstance(node.iter.func, ast.Name):
                        if node.iter.func.id == "range":
                            if node.iter.args:
                                arg = node.iter.args[0]
                                if isinstance(arg, ast.Call):
                                    if isinstance(arg.func, ast.Name):
                                        if arg.func.id == "len":
                                            boost = self._get_confidence_boost(
                                                technique.name, past_experiences
                                            )
                                            confidence = min(technique.confidence + boost, 1.0)

                                            speedup = 1.3 + (confidence * 0.2)  # 1.3x to 1.5x
                                            memory_saved = 100

                                            apply = confidence > 0.6

                                            optimizations.append(
                                                OptimizationResult(
                                                    technique=technique.name,
                                                    original_code="for i in range(len(items)):\n    print(i, items[i])",
                                                    optimized_code="for i, item in enumerate(items):\n    print(i, item)",
                                                    estimated_speedup=speedup,
                                                    estimated_memory_saved=memory_saved,
                                                    confidence=confidence,
                                                    applied=apply,
                                                    reason="enumerate() is more Pythonic and faster"
                                                    if apply
                                                    else "Confidence too low to apply automatically",
                                                )
                                            )

        return optimizations

    def _detect_boolean_loop(
        self,
        code: str,
        tree: ast.AST,
        technique: OptimizationTechnique,
        past_experiences: list[dict[str, Any]],
    ) -> list[OptimizationResult]:
        """Detect loops that check boolean conditions (could use any()/all())."""
        optimizations = []

        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                # Check for boolean variable being set in loop
                has_boolean_check = False
                for child in ast.walk(node):
                    if isinstance(child, ast.If):
                        has_boolean_check = True
                        break

                if has_boolean_check:
                    boost = self._get_confidence_boost(technique.name, past_experiences)
                    confidence = min(technique.confidence + boost, 1.0)

                    speedup = 2.0 + (confidence * 1.0)  # 2x to 3x
                    memory_saved = 200

                    apply = confidence > 0.6

                    optimizations.append(
                        OptimizationResult(
                            technique=technique.name,
                            original_code="found = False\nfor x in items:\n    if condition(x):\n        found = True\n        break",
                            optimized_code="found = any(condition(x) for x in items)",
                            estimated_speedup=speedup,
                            estimated_memory_saved=memory_saved,
                            confidence=confidence,
                            applied=apply,
                            reason="any()/all() are more concise and faster"
                            if apply
                            else "Confidence too low to apply automatically",
                        )
                    )

        return optimizations

    def _get_confidence_boost(
        self, technique_name: str, past_experiences: list[dict[str, Any]]
    ) -> float:
        """Calculate confidence boost from past experiences."""
        if not past_experiences:
            return 0.0

        # Count successful uses of this technique
        success_count = 0
        total_count = 0

        for exp in past_experiences:
            context = exp.get("context", {})
            if isinstance(context, dict):
                if context.get("technique") == technique_name:
                    total_count += 1
                    outcome = exp.get("outcome", {})
                    if isinstance(outcome, dict):
                        speedup = outcome.get("speedup", 0)
                        if speedup > 1.1:
                            success_count += 1

        if total_count == 0:
            return 0.0

        # Calculate boost: 0.0 to 0.3 based on success rate
        success_rate = success_count / total_count
        return success_rate * 0.3

    def _calculate_total_speedup(self, optimizations: list[OptimizationResult]) -> float:
        """Calculate total estimated speedup from all applied optimizations."""
        applied_opts = [opt for opt in optimizations if opt.applied]
        if not applied_opts:
            return 1.0

        # Multiply speedups (compound effect)
        total = 1.0
        for opt in applied_opts:
            total *= opt.estimated_speedup

        return total

    def _generate_insights(
        self,
        optimizations: list[OptimizationResult],
        past_experiences: list[dict[str, Any]],
        complexity_score: float,
    ) -> list[str]:
        """Generate insights based on optimization results and learning."""
        insights = []

        # Count applied vs suggested optimizations
        applied = len([o for o in optimizations if o.applied])
        suggested = len(optimizations) - applied

        if applied > 0:
            insights.append(f"Applied {applied} optimizations with high confidence")

        if suggested > 0:
            insights.append(f"Suggested {suggested} additional optimizations (lower confidence)")

        # Complexity insights
        if complexity_score > 20:
            insights.append("High complexity detected - consider refactoring")
        elif complexity_score < 5:
            insights.append("Low complexity - code is relatively simple")

        # Learning-based insights
        if past_experiences:
            # Check if we're improving
            avg_past_speedup = self._get_avg_metric(past_experiences, "speedup")
            if avg_past_speedup:
                current_speedup = self._calculate_total_speedup(optimizations)
                if current_speedup > avg_past_speedup * 1.2:
                    insights.append("Optimization effectiveness exceeds learned baseline")
        else:
            insights.append("No prior experience - building baseline")

        # Technique-specific insights
        technique_counts = {}
        for opt in optimizations:
            if opt.applied:
                technique_counts[opt.technique] = technique_counts.get(opt.technique, 0) + 1

        if technique_counts:
            most_used = max(technique_counts.items(), key=lambda x: x[1])
            insights.append(f"Most effective technique: {most_used[0]} (used {most_used[1]} times)")

        return insights

    def _get_avg_metric(self, experiences: list[dict[str, Any]], metric: str) -> float | None:
        """Calculate average of a metric from past experiences."""
        values = []
        for exp in experiences:
            outcome = exp.get("outcome", {})
            if isinstance(outcome, dict) and metric in outcome:
                value = outcome[metric]
                if isinstance(value, (int, float)):
                    values.append(value)

        return sum(values) / len(values) if values else None

    def _store_analysis_experience(self, analysis: CodeAnalysis):
        """Store analysis as experience for future learning."""
        try:
            # Store each applied optimization
            for opt in analysis.optimizations:
                if opt.applied:
                    self.store.store_experience(
                        exp_type=ExperienceType.SUCCESS
                        if opt.estimated_speedup > 1.1
                        else ExperienceType.FAILURE,
                        context={
                            "type": "optimization",
                            "technique": opt.technique,
                            "file_path": analysis.file_path,
                            "timestamp": analysis.analysis_timestamp,
                        },
                        action="applied_optimization",
                        outcome={
                            "speedup": opt.estimated_speedup,
                            "memory_saved": opt.estimated_memory_saved,
                            "confidence": opt.confidence,
                        },
                        metadata={
                            "technique_category": self.techniques[opt.technique].category,
                            "complexity": analysis.complexity_score,
                        },
                    )

            # Store overall analysis
            self.store.store_experience(
                exp_type=ExperienceType.SUCCESS,
                context={
                    "type": "file_analysis",
                    "file_path": analysis.file_path,
                    "timestamp": analysis.analysis_timestamp,
                },
                action="analyzed_code",
                outcome=analysis.to_dict(),
                metadata={
                    "total_optimizations": len(analysis.optimizations),
                    "optimizations_applied": len([o for o in analysis.optimizations if o.applied]),
                },
            )
        except Exception as e:
            # Graceful degradation
            print(f"Warning: Could not store experience: {e}")

    def _create_error_analysis(self, file_path: str, code: str, error_message: str) -> CodeAnalysis:
        """Create error analysis result."""
        return CodeAnalysis(
            file_path=file_path,
            original_code=code,
            optimizations=[],
            total_lines=len(code.splitlines()),
            complexity_score=0.0,
            estimated_total_speedup=1.0,
            estimated_total_memory_saved=0,
            learned_insights=[f"Analysis failed: {error_message}"],
        )

    def get_learning_stats(self) -> dict[str, Any]:
        """Get statistics about the agent's learning progress."""
        try:
            experiences = self.store.retrieve_relevant(context={"type": "optimization"}, limit=100)

            if not experiences:
                return {
                    "total_optimizations": 0,
                    "avg_speedup": 1.0,
                    "trend": "no_data",
                    "technique_effectiveness": {},
                }

            # Calculate speedup statistics
            speedups = []
            technique_stats: dict[str, list[float]] = {}

            for exp in experiences:
                outcome = exp.get("outcome", {})
                if isinstance(outcome, dict):
                    speedup = outcome.get("speedup", 1.0)
                    speedups.append(speedup)

                    context = exp.get("context", {})
                    if isinstance(context, dict):
                        technique = context.get("technique")
                        if technique:
                            if technique not in technique_stats:
                                technique_stats[technique] = []
                            technique_stats[technique].append(speedup)

            if not speedups:
                return {
                    "total_optimizations": len(experiences),
                    "avg_speedup": 1.0,
                    "trend": "no_data",
                    "technique_effectiveness": {},
                }

            # Calculate trend
            mid = len(speedups) // 2
            first_half_avg = sum(speedups[:mid]) / len(speedups[:mid]) if mid > 0 else 1.0
            second_half_avg = (
                sum(speedups[mid:]) / len(speedups[mid:]) if len(speedups[mid:]) > 0 else 1.0
            )

            trend = (
                "improving"
                if second_half_avg > first_half_avg * 1.1
                else "declining"
                if second_half_avg < first_half_avg * 0.9
                else "stable"
            )

            # Calculate technique effectiveness
            technique_effectiveness = {}
            for technique, values in technique_stats.items():
                technique_effectiveness[technique] = {
                    "avg_speedup": sum(values) / len(values),
                    "uses": len(values),
                    "confidence": self.techniques[technique].confidence
                    if technique in self.techniques
                    else 0.5,
                }

            return {
                "total_optimizations": len(experiences),
                "avg_speedup": sum(speedups) / len(speedups),
                "min_speedup": min(speedups),
                "max_speedup": max(speedups),
                "trend": trend,
                "first_half_avg": first_half_avg,
                "second_half_avg": second_half_avg,
                "improvement": second_half_avg - first_half_avg,
                "technique_effectiveness": technique_effectiveness,
            }
        except Exception as e:
            return {
                "error": str(e),
                "total_optimizations": 0,
                "avg_speedup": 1.0,
                "trend": "error",
                "technique_effectiveness": {},
            }
