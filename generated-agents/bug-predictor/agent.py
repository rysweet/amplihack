"""
Bug Predictor Learning Agent

A learning agent that analyzes Python code to predict potential bugs,
stores bug patterns in memory, and improves prediction accuracy over time.
"""

import ast
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from amplihack_memory_lib import ExperienceStore, ExperienceType, MemoryConnector
except ImportError:
    raise ImportError(
        "amplihack-memory-lib is required. Install with: pip install amplihack-memory-lib"
    )


@dataclass
class BugPattern:
    """A detected bug pattern in code."""

    bug_type: str
    severity: str  # "critical", "high", "medium", "low"
    confidence: float  # 0.0 to 1.0
    line_number: int
    code_snippet: str
    explanation: str
    suggested_fix: str | None = None


@dataclass
class BugPrediction:
    """Complete bug prediction result."""

    file_path: str
    total_issues: int
    critical_issues: int
    high_confidence: list[BugPattern]
    medium_confidence: list[BugPattern]
    low_confidence: list[BugPattern]

    # Learning metadata
    prediction_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    used_learned_patterns: int = 0
    analysis_runtime: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert prediction to dictionary."""
        return {
            "file_path": self.file_path,
            "total_issues": self.total_issues,
            "critical_issues": self.critical_issues,
            "high_confidence_count": len(self.high_confidence),
            "medium_confidence_count": len(self.medium_confidence),
            "low_confidence_count": len(self.low_confidence),
            "prediction_timestamp": self.prediction_timestamp,
            "used_learned_patterns": self.used_learned_patterns,
            "analysis_runtime": self.analysis_runtime,
        }


class BugPredictor:
    """
    Learning agent that predicts bugs in Python code and improves through experience.

    Key capabilities:
    1. AST-based static analysis for bug detection
    2. Stores bug patterns in memory
    3. Retrieves past patterns to improve predictions
    4. Learns from discovered bugs
    5. Tracks prediction accuracy over time
    """

    # Bug pattern signatures for detection
    BUG_PATTERNS = {
        "none_reference": {
            "severity": "high",
            "keywords": ["None", "is None", "== None"],
            "ast_patterns": ["Compare", "Attribute"],
        },
        "resource_leak": {
            "severity": "high",
            "keywords": ["open(", "connect(", "cursor("],
            "ast_patterns": ["Call", "With"],
        },
        "sql_injection": {
            "severity": "critical",
            "keywords": ["execute(", "cursor.execute", "query"],
            "ast_patterns": ["Call", "BinOp"],
        },
        "race_condition": {
            "severity": "high",
            "keywords": ["threading", "Thread", "Lock", "global"],
            "ast_patterns": ["Global", "Call"],
        },
        "memory_leak": {
            "severity": "medium",
            "keywords": ["append", "global", "cache", "[]"],
            "ast_patterns": ["Global", "List"],
        },
        "off_by_one": {
            "severity": "medium",
            "keywords": ["range(", "len(", "[-1]", "[0]"],
            "ast_patterns": ["Subscript", "Call"],
        },
        "type_mismatch": {
            "severity": "medium",
            "keywords": ["int(", "str(", "float(", "+", "*"],
            "ast_patterns": ["Call", "BinOp"],
        },
        "uncaught_exception": {
            "severity": "high",
            "keywords": ["raise", "Exception", "Error"],
            "ast_patterns": ["Raise", "Try"],
        },
    }

    def __init__(self, memory_connector: MemoryConnector | None = None):
        """Initialize the bug predictor with memory integration."""
        self.memory = memory_connector or MemoryConnector(agent_name="bug-predictor")
        self.store = ExperienceStore(self.memory)

        # Pattern confidence weights (learned from experience)
        self.pattern_weights = {
            "none_reference": 0.7,
            "resource_leak": 0.8,
            "sql_injection": 0.9,
            "race_condition": 0.6,
            "memory_leak": 0.5,
            "off_by_one": 0.6,
            "type_mismatch": 0.5,
            "uncaught_exception": 0.7,
        }

    def predict_bugs(self, code_file: str) -> BugPrediction:
        """
        Predict bugs in a Python code file using learned patterns.

        Args:
            code_file: Path to Python file or Python code as string

        Returns:
            BugPrediction with detected issues and confidence levels
        """
        import time

        start_time = time.time()

        # 1. Load code
        if Path(code_file).exists():
            with open(code_file, encoding="utf-8") as f:
                code = f.read()
            file_path = str(code_file)
        else:
            code = code_file
            file_path = "inline_code"

        # 2. Retrieve known bug patterns from memory
        learned_patterns = self._retrieve_bug_patterns()

        # 3. Parse code into AST
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return BugPrediction(
                file_path=file_path,
                total_issues=1,
                critical_issues=1,
                high_confidence=[
                    BugPattern(
                        bug_type="syntax_error",
                        severity="critical",
                        confidence=1.0,
                        line_number=getattr(e, "lineno", 0),
                        code_snippet=str(e),
                        explanation="Syntax error prevents parsing",
                    )
                ],
                medium_confidence=[],
                low_confidence=[],
            )

        # 4. Analyze code with both built-in and learned patterns
        detected_bugs = self._analyze_ast(tree, code, learned_patterns)

        # 5. Classify bugs by confidence
        high_conf = [b for b in detected_bugs if b.confidence >= 0.7]
        medium_conf = [b for b in detected_bugs if 0.4 <= b.confidence < 0.7]
        low_conf = [b for b in detected_bugs if b.confidence < 0.4]

        critical_count = sum(1 for b in detected_bugs if b.severity == "critical")

        # 6. Create prediction result
        prediction = BugPrediction(
            file_path=file_path,
            total_issues=len(detected_bugs),
            critical_issues=critical_count,
            high_confidence=high_conf,
            medium_confidence=medium_conf,
            low_confidence=low_conf,
            used_learned_patterns=len(learned_patterns),
            analysis_runtime=time.time() - start_time,
        )

        # 7. Store new bug patterns in memory
        self._store_bug_patterns(prediction, detected_bugs)

        return prediction

    def _retrieve_bug_patterns(self) -> list[dict[str, Any]]:
        """Retrieve known bug patterns from memory."""
        try:
            patterns = self.store.retrieve_relevant(context={"type": "bug_pattern"}, limit=50)
            return patterns
        except Exception:
            return []

    def _analyze_ast(
        self, tree: ast.AST, code: str, learned_patterns: list[dict[str, Any]]
    ) -> list[BugPattern]:
        """Analyze AST for bug patterns."""
        bugs = []
        lines = code.split("\n")

        # Apply learned pattern weights
        self._update_pattern_weights(learned_patterns)

        # Walk AST and detect patterns
        for node in ast.walk(tree):
            # Check each bug pattern type
            for bug_type, pattern_def in self.BUG_PATTERNS.items():
                if self._matches_pattern(node, pattern_def, lines):
                    bug = self._create_bug_pattern(node, bug_type, pattern_def, lines)
                    if bug:
                        bugs.append(bug)

        # Apply learned pattern boosting
        bugs = self._boost_with_learned_patterns(bugs, learned_patterns)

        return bugs

    def _matches_pattern(
        self, node: ast.AST, pattern_def: dict[str, Any], lines: list[str]
    ) -> bool:
        """Check if AST node matches a bug pattern."""
        node_type = type(node).__name__

        # Check if node type matches pattern
        if node_type not in pattern_def["ast_patterns"]:
            return False

        # Get source code line if available
        line_num = getattr(node, "lineno", 0)
        if line_num == 0 or line_num > len(lines):
            return False

        line = lines[line_num - 1]

        # Check if keywords present in line
        return any(keyword in line for keyword in pattern_def["keywords"])

    def _create_bug_pattern(
        self, node: ast.AST, bug_type: str, pattern_def: dict[str, Any], lines: list[str]
    ) -> BugPattern | None:
        """Create a BugPattern from detected issue."""
        line_num = getattr(node, "lineno", 0)
        if line_num == 0 or line_num > len(lines):
            return None

        snippet = lines[line_num - 1].strip()

        # Get base confidence from pattern weights
        confidence = self.pattern_weights.get(bug_type, 0.5)

        # Adjust confidence based on context
        confidence = self._adjust_confidence(node, bug_type, lines, confidence)

        explanation = self._generate_explanation(bug_type, snippet)
        suggested_fix = self._generate_fix(bug_type, snippet)

        return BugPattern(
            bug_type=bug_type,
            severity=pattern_def["severity"],
            confidence=confidence,
            line_number=line_num,
            code_snippet=snippet,
            explanation=explanation,
            suggested_fix=suggested_fix,
        )

    def _adjust_confidence(
        self, node: ast.AST, bug_type: str, lines: list[str], base_confidence: float
    ) -> float:
        """Adjust confidence based on context."""
        confidence = base_confidence
        line_num = getattr(node, "lineno", 0)

        if line_num == 0 or line_num > len(lines):
            return confidence

        line = lines[line_num - 1]

        # Boost confidence for common anti-patterns
        if bug_type == "none_reference":
            # Lower confidence if inside try/except
            if self._is_in_try_except(node):
                confidence *= 0.7
            # Higher confidence if no null check nearby
            elif not self._has_null_check_nearby(lines, line_num):
                confidence *= 1.2

        elif bug_type == "resource_leak":
            # Lower confidence if using context manager
            if "with " in line:
                confidence *= 0.3
            else:
                confidence *= 1.3

        elif bug_type == "sql_injection":
            # Higher confidence if string concatenation
            if "+" in line or 'f"' in line or "%" in line:
                confidence *= 1.5
            # Lower confidence if parameterized
            elif "?" in line or "%s" in line:
                confidence *= 0.5

        return min(confidence, 1.0)

    def _is_in_try_except(self, node: ast.AST) -> bool:
        """Check if node is inside try/except block."""
        # Simplified check - in production would need parent tracking
        return False

    def _has_null_check_nearby(self, lines: list[str], line_num: int) -> bool:
        """Check if there's a null check near this line."""
        start = max(0, line_num - 3)
        end = min(len(lines), line_num + 2)

        nearby_lines = lines[start:end]
        return any("is not None" in line or "is None" in line for line in nearby_lines)

    def _generate_explanation(self, bug_type: str, snippet: str) -> str:
        """Generate human-readable explanation for bug."""
        explanations = {
            "none_reference": f"Potential None/null reference error in: {snippet[:50]}",
            "resource_leak": f"Resource may not be properly closed: {snippet[:50]}",
            "sql_injection": f"Possible SQL injection vulnerability: {snippet[:50]}",
            "race_condition": f"Potential race condition with shared state: {snippet[:50]}",
            "memory_leak": f"Possible memory leak from unbounded growth: {snippet[:50]}",
            "off_by_one": f"Potential off-by-one error in indexing: {snippet[:50]}",
            "type_mismatch": f"Possible type mismatch or conversion error: {snippet[:50]}",
            "uncaught_exception": f"Exception may not be properly handled: {snippet[:50]}",
        }
        return explanations.get(bug_type, f"Potential issue detected: {snippet[:50]}")

    def _generate_fix(self, bug_type: str, snippet: str) -> str:
        """Generate suggested fix for bug."""
        fixes = {
            "none_reference": "Add null check: if obj is not None:",
            "resource_leak": "Use context manager: with open(...) as f:",
            "sql_injection": "Use parameterized queries: cursor.execute('...', params)",
            "race_condition": "Add synchronization: with lock:",
            "memory_leak": "Clear cache periodically or use weak references",
            "off_by_one": "Verify range bounds: range(len(items))",
            "type_mismatch": "Add type checking or explicit conversion",
            "uncaught_exception": "Add try/except or propagate exception",
        }
        return fixes.get(bug_type, "Review code logic")

    def _update_pattern_weights(self, learned_patterns: list[dict[str, Any]]):
        """Update pattern weights based on learned patterns."""
        if not learned_patterns:
            return

        # Count pattern occurrences
        pattern_counts = {}
        for exp in learned_patterns:
            outcome = exp.get("outcome", {})
            bug_type = outcome.get("bug_type", "")
            if bug_type:
                pattern_counts[bug_type] = pattern_counts.get(bug_type, 0) + 1

        # Boost weights for frequently seen patterns
        total = sum(pattern_counts.values())
        if total > 0:
            for bug_type, count in pattern_counts.items():
                if bug_type in self.pattern_weights:
                    boost = min(count / total * 0.2, 0.3)  # Max 30% boost
                    self.pattern_weights[bug_type] = min(
                        self.pattern_weights[bug_type] + boost, 1.0
                    )

    def _boost_with_learned_patterns(
        self, bugs: list[BugPattern], learned_patterns: list[dict[str, Any]]
    ) -> list[BugPattern]:
        """Boost confidence of bugs matching learned patterns."""
        if not learned_patterns:
            return bugs

        # Build learned pattern signatures
        learned_signatures = set()
        for exp in learned_patterns:
            outcome = exp.get("outcome", {})
            signature = f"{outcome.get('bug_type', '')}:{outcome.get('pattern', '')}"
            learned_signatures.add(signature)

        # Boost matching bugs
        for bug in bugs:
            signature = f"{bug.bug_type}:{bug.code_snippet[:20]}"
            if any(sig.startswith(bug.bug_type) for sig in learned_signatures):
                bug.confidence = min(bug.confidence * 1.2, 1.0)

        return bugs

    def _store_bug_patterns(self, prediction: BugPrediction, bugs: list[BugPattern]):
        """Store detected bug patterns in memory for learning."""
        try:
            # Store high-confidence bugs as patterns
            for bug in prediction.high_confidence:
                exp_id = hashlib.md5(
                    f"{prediction.file_path}:{bug.line_number}:{bug.bug_type}".encode()
                ).hexdigest()[:16]

                self.store.store_experience(
                    exp_type=ExperienceType.PATTERN,
                    context={
                        "type": "bug_pattern",
                        "file": prediction.file_path,
                        "bug_type": bug.bug_type,
                    },
                    action="detected_bug",
                    outcome={
                        "bug_type": bug.bug_type,
                        "severity": bug.severity,
                        "pattern": bug.code_snippet[:50],
                        "confidence": bug.confidence,
                    },
                    metadata={
                        "experience_id": exp_id,
                        "line_number": bug.line_number,
                    },
                )

            # Store overall prediction as success/failure
            exp_type = (
                ExperienceType.SUCCESS
                if prediction.critical_issues == 0
                else ExperienceType.FAILURE
            )

            self.store.store_experience(
                exp_type=exp_type,
                context={
                    "type": "bug_prediction",
                    "file": prediction.file_path,
                },
                action="analyzed_code",
                outcome=prediction.to_dict(),
                metadata={
                    "timestamp": prediction.prediction_timestamp,
                    "runtime": prediction.analysis_runtime,
                },
            )
        except Exception as e:
            # Graceful degradation
            print(f"Warning: Could not store bug patterns: {e}")

    def get_learning_stats(self) -> dict[str, Any]:
        """Get statistics about the agent's learning progress."""
        try:
            # Get all predictions
            predictions = self.store.retrieve_relevant(
                context={"type": "bug_prediction"}, limit=100
            )

            if not predictions:
                return {
                    "total_predictions": 0,
                    "avg_accuracy": 0.0,
                    "improvement": 0.0,
                    "trend": "no_data",
                }

            # Calculate metrics from outcomes
            total_issues = []
            runtimes = []
            used_patterns = []

            for exp in predictions:
                outcome = exp.get("outcome", {})
                if isinstance(outcome, dict):
                    total_issues.append(outcome.get("total_issues", 0))
                    used_patterns.append(outcome.get("used_learned_patterns", 0))

                metadata = exp.get("metadata", {})
                if isinstance(metadata, dict):
                    runtime = metadata.get("runtime", 0)
                    if runtime:
                        runtimes.append(runtime)

            # Calculate improvement (more patterns used over time = learning)
            mid = len(used_patterns) // 2
            first_half_patterns = sum(used_patterns[:mid]) / max(mid, 1)
            second_half_patterns = sum(used_patterns[mid:]) / max(len(used_patterns[mid:]), 1)

            improvement = second_half_patterns - first_half_patterns

            # Calculate runtime improvement
            if len(runtimes) >= 2:
                runtime_improvement = (runtimes[0] - runtimes[-1]) / runtimes[0] * 100
            else:
                runtime_improvement = 0.0

            return {
                "total_predictions": len(predictions),
                "avg_issues_detected": sum(total_issues) / len(total_issues) if total_issues else 0,
                "avg_patterns_used": sum(used_patterns) / len(used_patterns)
                if used_patterns
                else 0,
                "pattern_usage_improvement": improvement,
                "runtime_improvement_pct": runtime_improvement,
                "trend": "improving" if improvement > 0.1 else "stable",
            }
        except Exception as e:
            return {
                "error": str(e),
                "total_predictions": 0,
                "avg_accuracy": 0.0,
                "improvement": 0.0,
            }
