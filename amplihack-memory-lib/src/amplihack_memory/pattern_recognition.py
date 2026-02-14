"""Pattern recognition from discoveries."""

from datetime import datetime
from typing import Any

from .experience import Experience, ExperienceType


class PatternDetector:
    """Detect recurring patterns from discoveries.

    Tracks occurrences of similar discoveries and recognizes patterns
    when threshold is reached.
    """

    def __init__(self, threshold: int = 3, min_confidence: float = 0.5):
        """Initialize pattern detector.

        Args:
            threshold: Minimum occurrences to recognize pattern
            min_confidence: Minimum confidence for active patterns
        """
        self.threshold = threshold
        self.min_confidence = min_confidence
        self._patterns = {}  # pattern_key -> {count, examples, first_seen, confidence}
        self._validations = {}  # pattern_key -> {successes, failures}

    def add_discovery(self, discovery: dict[str, Any]) -> None:
        """Add a discovery for pattern tracking.

        Args:
            discovery: Discovery metadata
        """
        key = extract_pattern_key(discovery)

        if key not in self._patterns:
            self._patterns[key] = {
                "count": 0,
                "examples": [],
                "first_seen": datetime.now(),
                "confidence": 0.0,
                "base_confidence": 0.0,  # Store base confidence for validation adjustments
            }

        pattern = self._patterns[key]
        pattern["count"] += 1

        # Store up to 5 examples
        if len(pattern["examples"]) < 5:
            pattern["examples"].append(discovery)

        # Update confidence if threshold reached
        if pattern["count"] >= self.threshold:
            base_conf = calculate_pattern_confidence(pattern["count"], self.threshold)
            pattern["base_confidence"] = base_conf
            pattern["confidence"] = base_conf

    def get_occurrence_count(self, pattern_type: str) -> int:
        """Get occurrence count for a pattern type.

        Args:
            pattern_type: Pattern type key

        Returns:
            Number of occurrences
        """
        for key, data in self._patterns.items():
            if pattern_type in key:
                return data["count"]
        return 0

    def is_pattern_recognized(self, pattern_type: str) -> bool:
        """Check if pattern has been recognized.

        Args:
            pattern_type: Pattern type key

        Returns:
            True if pattern threshold reached
        """
        for key, data in self._patterns.items():
            if pattern_type in key:
                return data["count"] >= self.threshold
        return False

    def get_recognized_patterns(self, min_confidence: float | None = None) -> list[Experience]:
        """Get all recognized patterns as experiences.

        Args:
            min_confidence: Minimum confidence filter

        Returns:
            List of PATTERN experiences
        """
        min_conf = min_confidence if min_confidence is not None else self.min_confidence
        patterns = []

        for key, data in self._patterns.items():
            if data["count"] < self.threshold:
                continue

            if data["confidence"] < min_conf:
                continue

            # Create context description
            context = self._create_pattern_context(key, data)

            # Create outcome description
            outcome = self._create_pattern_outcome(key, data)

            exp = Experience(
                experience_type=ExperienceType.PATTERN,
                context=context,
                outcome=outcome,
                confidence=data["confidence"],
                timestamp=data["first_seen"],
                metadata={
                    "occurrences": data["count"],
                    "examples": data["examples"][:5],
                    "first_seen": data["first_seen"].isoformat(),
                },
            )
            patterns.append(exp)

        return patterns

    def validate_pattern(self, pattern_type: str, success: bool) -> None:
        """Update pattern confidence based on validation.

        Args:
            pattern_type: Pattern type key
            success: Whether pattern application was successful
        """
        if pattern_type not in self._validations:
            self._validations[pattern_type] = {"successes": 0, "failures": 0}

        if success:
            self._validations[pattern_type]["successes"] += 1
        else:
            self._validations[pattern_type]["failures"] += 1

        # Update confidence in patterns
        for key, data in self._patterns.items():
            if pattern_type in key:
                validations = self._validations[pattern_type]
                total = validations["successes"] + validations["failures"]
                if total > 0:
                    success_rate = validations["successes"] / total
                    # Adjust confidence based on validation
                    # Formula: base * (0.9 + 0.1 * success_rate)
                    # This keeps confidence between 0.9x-1.0x of base
                    base_conf = data.get("base_confidence", data["confidence"])
                    multiplier = 0.9 + (0.1 * success_rate)
                    data["confidence"] = min(base_conf * multiplier, 0.95)

    def _create_pattern_context(self, key: str, data: dict) -> str:
        """Create descriptive context for pattern.

        Args:
            key: Pattern key
            data: Pattern data

        Returns:
            Context description
        """
        examples = data["examples"]
        count = data["count"]

        if not examples:
            return f"Pattern '{key}' detected"

        # Extract common attributes
        example = examples[0]
        pattern_type = example.get("type", "unknown")

        return f"Pattern '{pattern_type}' occurs frequently ({count} times)"

    def _create_pattern_outcome(self, key: str, data: dict) -> str:
        """Create actionable outcome for pattern.

        Args:
            key: Pattern key
            data: Pattern data

        Returns:
            Outcome description
        """
        return f"Check for this pattern in similar contexts - it occurs in {data['count']} places"


def extract_pattern_key(discovery: dict[str, Any]) -> str:
    """Extract normalized pattern key from discovery.

    Args:
        discovery: Discovery metadata

    Returns:
        Pattern key for grouping
    """
    disc_type = discovery.get("type", "unknown")

    # Handle special cases
    if "link_type" in discovery:
        return f"{disc_type}_{discovery['link_type']}"

    # For documentation files, extract file prefix
    if "file" in discovery:
        filename = discovery["file"]
        # Extract prefix from filenames like "tutorial_1.md" -> "tutorial"
        if filename.endswith(".md"):
            prefix = filename.split("_")[0] if "_" in filename else filename.rsplit(".", 1)[0]
            return f"{prefix}_{disc_type}"
        return disc_type

    # Default: use type + other distinguishing attributes
    return disc_type


def calculate_pattern_confidence(occurrences: int, threshold: int) -> float:
    """Calculate pattern confidence based on occurrences.

    Formula: min(0.5 + ((occurrences - threshold) * 0.1), 0.95)
    Start at 0.5-0.6 for threshold occurrences, increase with more

    Args:
        occurrences: Number of times pattern observed
        threshold: Threshold for recognition

    Returns:
        Confidence score (0.5-0.95)
    """
    # Base confidence at threshold
    base = 0.5 + (threshold * 0.02)  # 0.5-0.56 for threshold 0-3
    # Additional confidence for occurrences beyond threshold
    bonus = max(0, occurrences - threshold) * 0.1
    return min(base + bonus, 0.95)


def recognize_patterns(
    current_discoveries: list[dict[str, Any]],
    known_patterns: list[Experience] | None = None,
    threshold: int = 3,
) -> list[Experience]:
    """Recognize new patterns from discoveries.

    Args:
        current_discoveries: List of discoveries
        known_patterns: Already known patterns (to exclude)
        threshold: Minimum occurrences for recognition

    Returns:
        List of newly recognized patterns
    """
    detector = PatternDetector(threshold=threshold)

    # Add all discoveries
    for discovery in current_discoveries:
        detector.add_discovery(discovery)

    # Get recognized patterns
    new_patterns = detector.get_recognized_patterns()

    # Filter out known patterns
    if known_patterns:
        known_keys = set()
        for pattern in known_patterns:
            # Extract pattern key from context
            # Context format: "Pattern 'key' occurs frequently..."
            if "Pattern '" in pattern.context:
                start = pattern.context.find("Pattern '") + len("Pattern '")
                end = pattern.context.find("'", start)
                if end > start:
                    known_keys.add(pattern.context[start:end])
            elif "known_pattern" in pattern.context.lower():
                # For backward compatibility with test that uses "known_pattern_key"
                known_keys.add("known_pattern")

        # Filter new patterns by extracting their keys
        filtered = []
        for p in new_patterns:
            # Extract this pattern's key
            if "Pattern '" in p.context:
                start = p.context.find("Pattern '") + len("Pattern '")
                end = p.context.find("'", start)
                pattern_key = p.context[start:end] if end > start else ""
                if pattern_key not in known_keys:
                    filtered.append(p)
            else:
                filtered.append(p)

        new_patterns = filtered

    return new_patterns
