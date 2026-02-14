"""
Unit tests for Pattern Recognition Algorithm.

All tests are written to FAIL initially (TDD approach).
"""

from datetime import datetime

from amplihack_memory import Experience, ExperienceType
from amplihack_memory.pattern_recognition import (
    PatternDetector,
    calculate_pattern_confidence,
    extract_pattern_key,
    recognize_patterns,
)


class TestPatternDetector:
    """Test PatternDetector class."""

    def test_initializes_with_threshold(self):
        """PatternDetector initializes with recognition threshold."""
        detector = PatternDetector(threshold=3)
        assert detector.threshold == 3

    def test_defaults_to_threshold_of_3(self):
        """PatternDetector defaults to threshold of 3."""
        detector = PatternDetector()
        assert detector.threshold == 3

    def test_tracks_pattern_occurrences(self):
        """PatternDetector tracks number of occurrences per pattern."""
        detector = PatternDetector(threshold=3)

        # Add same discovery 3 times
        for i in range(3):
            detector.add_discovery({"type": "missing_example", "file": f"tutorial_{i}.md"})

        assert detector.get_occurrence_count("missing_example") == 3

    def test_recognizes_pattern_at_threshold(self):
        """PatternDetector recognizes pattern when threshold reached."""
        detector = PatternDetector(threshold=3)

        # Add discoveries
        for i in range(2):
            detector.add_discovery({"type": "broken_link", "url": f"http://example{i}.com"})

        # Not yet recognized
        assert not detector.is_pattern_recognized("broken_link")

        # Add one more to reach threshold
        detector.add_discovery({"type": "broken_link", "url": "http://example3.com"})

        # Should now be recognized
        assert detector.is_pattern_recognized("broken_link")

    def test_creates_pattern_experience_from_discoveries(self):
        """PatternDetector creates PATTERN experience when threshold reached."""
        detector = PatternDetector(threshold=3)

        discoveries = [
            {"type": "hardcoded_credential", "file": "auth.py", "line": 42},
            {"type": "hardcoded_credential", "file": "config.py", "line": 18},
            {"type": "hardcoded_credential", "file": "api.py", "line": 55},
        ]

        for disc in discoveries:
            detector.add_discovery(disc)

        # Get recognized patterns
        patterns = detector.get_recognized_patterns()

        assert len(patterns) == 1
        pattern = patterns[0]
        assert pattern.experience_type == ExperienceType.PATTERN
        assert "hardcoded_credential" in pattern.context
        assert pattern.confidence > 0.5

    def test_calculates_confidence_based_on_occurrences(self):
        """PatternDetector increases confidence with more occurrences."""
        detector = PatternDetector(threshold=2)

        # Pattern with 2 occurrences
        for i in range(2):
            detector.add_discovery({"type": "pattern_a"})

        patterns_a = detector.get_recognized_patterns()
        confidence_2 = patterns_a[0].confidence

        # Pattern with 5 occurrences
        detector2 = PatternDetector(threshold=2)
        for i in range(5):
            detector2.add_discovery({"type": "pattern_b"})

        patterns_b = detector2.get_recognized_patterns()
        confidence_5 = patterns_b[0].confidence

        # More occurrences = higher confidence
        assert confidence_5 > confidence_2

    def test_caps_confidence_at_0_95(self):
        """PatternDetector caps maximum confidence at 0.95."""
        detector = PatternDetector(threshold=2)

        # Add many occurrences
        for i in range(100):
            detector.add_discovery({"type": "common_pattern"})

        patterns = detector.get_recognized_patterns()
        assert patterns[0].confidence <= 0.95

    def test_stores_example_occurrences_in_metadata(self):
        """PatternDetector stores example occurrences in pattern metadata."""
        detector = PatternDetector(threshold=3)

        discoveries = [
            {"type": "issue", "file": "file1.py", "line": 10},
            {"type": "issue", "file": "file2.py", "line": 20},
            {"type": "issue", "file": "file3.py", "line": 30},
            {"type": "issue", "file": "file4.py", "line": 40},
        ]

        for disc in discoveries:
            detector.add_discovery(disc)

        patterns = detector.get_recognized_patterns()
        pattern = patterns[0]

        # Should store examples (typically first 5)
        assert "examples" in pattern.metadata
        examples = pattern.metadata["examples"]
        assert len(examples) > 0
        assert len(examples) <= 5


class TestExtractPatternKey:
    """Test pattern key extraction function."""

    def test_extracts_key_from_documentation_issue(self):
        """extract_pattern_key() extracts key from documentation discovery."""
        discovery = {
            "type": "missing_example",
            "file": "tutorial_1.md",
            "heading": "Getting Started",
        }

        key = extract_pattern_key(discovery)
        assert key == "tutorial_missing_example"

    def test_extracts_key_from_security_issue(self):
        """extract_pattern_key() extracts key from security discovery."""
        discovery = {"type": "sql_injection", "file": "api.py", "line": 42, "severity": "high"}

        key = extract_pattern_key(discovery)
        assert "sql_injection" in key

    def test_distinguishes_similar_patterns(self):
        """extract_pattern_key() distinguishes between similar patterns."""
        disc1 = {"type": "broken_link", "url": "http://external.com", "link_type": "external"}

        disc2 = {"type": "broken_link", "url": "/internal/page", "link_type": "internal"}

        key1 = extract_pattern_key(disc1)
        key2 = extract_pattern_key(disc2)

        # Should generate different keys for external vs internal links
        assert key1 != key2
        assert "external" in key1
        assert "internal" in key2

    def test_normalizes_similar_discoveries(self):
        """extract_pattern_key() normalizes similar discoveries to same key."""
        disc1 = {"type": "missing_test", "file": "module_a.py"}
        disc2 = {"type": "missing_test", "file": "module_b.py"}
        disc3 = {"type": "missing_test", "file": "module_c.py"}

        key1 = extract_pattern_key(disc1)
        key2 = extract_pattern_key(disc2)
        key3 = extract_pattern_key(disc3)

        # All should have same key (different files, same issue)
        assert key1 == key2 == key3

    def test_handles_unknown_discovery_types(self):
        """extract_pattern_key() handles unknown discovery types gracefully."""
        discovery = {"type": "unknown_issue_type", "data": "some data"}

        key = extract_pattern_key(discovery)
        assert key is not None
        assert "unknown" in key.lower()


class TestCalculatePatternConfidence:
    """Test confidence calculation function."""

    def test_calculates_base_confidence(self):
        """calculate_pattern_confidence() returns base confidence for threshold occurrences."""
        # Exactly at threshold (3 occurrences)
        confidence = calculate_pattern_confidence(occurrences=3, threshold=3)
        assert 0.5 <= confidence <= 0.7  # Base range

    def test_increases_confidence_with_occurrences(self):
        """calculate_pattern_confidence() increases with more occurrences."""
        conf_3 = calculate_pattern_confidence(occurrences=3, threshold=3)
        conf_5 = calculate_pattern_confidence(occurrences=5, threshold=3)
        conf_10 = calculate_pattern_confidence(occurrences=10, threshold=3)

        assert conf_3 < conf_5 < conf_10

    def test_caps_at_maximum_confidence(self):
        """calculate_pattern_confidence() caps at 0.95."""
        confidence = calculate_pattern_confidence(occurrences=1000, threshold=3)
        assert confidence <= 0.95

    def test_formula_is_consistent(self):
        """calculate_pattern_confidence() uses consistent formula."""
        # Formula: min(0.5 + (occurrences * 0.1), 0.95)
        assert calculate_pattern_confidence(3, 3) == min(0.5 + (3 * 0.1), 0.95)
        assert calculate_pattern_confidence(5, 3) == min(0.5 + (5 * 0.1), 0.95)


class TestRecognizePatternsFunction:
    """Test main pattern recognition function."""

    def test_recognizes_patterns_from_discoveries(self):
        """recognize_patterns() identifies patterns from discoveries."""
        discoveries = [
            {"type": "issue_a", "file": "1.py"},
            {"type": "issue_a", "file": "2.py"},
            {"type": "issue_a", "file": "3.py"},
            {"type": "issue_b", "file": "4.py"},
            {"type": "issue_b", "file": "5.py"},
        ]

        patterns = recognize_patterns(current_discoveries=discoveries, threshold=3)

        # Should recognize issue_a (3 occurrences)
        # Should NOT recognize issue_b (only 2 occurrences)
        assert len(patterns) == 1
        assert "issue_a" in patterns[0].context

    def test_excludes_already_known_patterns(self):
        """recognize_patterns() excludes patterns already known."""
        known_patterns = [
            Experience(
                experience_type=ExperienceType.PATTERN,
                context="known_pattern_key",
                outcome="Already recognized",
                confidence=0.9,
                timestamp=datetime.now(),
            )
        ]

        discoveries = [
            {"type": "known_pattern", "file": "1.py"},
            {"type": "known_pattern", "file": "2.py"},
            {"type": "known_pattern", "file": "3.py"},
        ]

        # Mock extract_pattern_key to return "known_pattern_key"
        patterns = recognize_patterns(
            current_discoveries=discoveries, known_patterns=known_patterns, threshold=3
        )

        # Should not create new pattern for already known pattern
        assert len(patterns) == 0

    def test_recognizes_multiple_new_patterns(self):
        """recognize_patterns() can recognize multiple patterns in one pass."""
        discoveries = (
            [{"type": "pattern_a", "data": "x"} for _ in range(4)]
            + [{"type": "pattern_b", "data": "y"} for _ in range(3)]
            + [{"type": "pattern_c", "data": "z"} for _ in range(5)]
        )

        patterns = recognize_patterns(current_discoveries=discoveries, threshold=3)

        # Should recognize all three patterns
        assert len(patterns) == 3

        pattern_contexts = {p.context for p in patterns}
        # All three pattern types should be present
        assert len(pattern_contexts) == 3

    def test_returns_empty_list_when_no_patterns(self):
        """recognize_patterns() returns empty list when no patterns found."""
        discoveries = [{"type": "unique_1", "data": "x"}, {"type": "unique_2", "data": "y"}]

        patterns = recognize_patterns(current_discoveries=discoveries, threshold=3)

        assert len(patterns) == 0


class TestPatternEvolution:
    """Test how patterns evolve over time."""

    def test_pattern_confidence_increases_with_validation(self):
        """Pattern confidence increases when applied successfully."""
        detector = PatternDetector(threshold=3)

        # Initial pattern recognition
        for i in range(3):
            detector.add_discovery({"type": "pattern_x"})

        initial_patterns = detector.get_recognized_patterns()
        initial_conf = initial_patterns[0].confidence

        # Apply pattern successfully multiple times
        for i in range(5):
            detector.validate_pattern("pattern_x", success=True)

        updated_patterns = detector.get_recognized_patterns()
        updated_conf = updated_patterns[0].confidence

        assert updated_conf > initial_conf

    def test_pattern_confidence_decreases_with_failures(self):
        """Pattern confidence decreases when applied unsuccessfully."""
        detector = PatternDetector(threshold=3)

        # Initial pattern recognition
        for i in range(3):
            detector.add_discovery({"type": "pattern_y"})

        initial_patterns = detector.get_recognized_patterns()
        initial_conf = initial_patterns[0].confidence

        # Apply pattern unsuccessfully
        for i in range(3):
            detector.validate_pattern("pattern_y", success=False)

        updated_patterns = detector.get_recognized_patterns()
        updated_conf = updated_patterns[0].confidence

        assert updated_conf < initial_conf

    def test_pattern_can_be_demoted_if_unreliable(self):
        """Pattern can be demoted if confidence drops too low."""
        detector = PatternDetector(threshold=3, min_confidence=0.5)

        # Recognize pattern
        for i in range(3):
            detector.add_discovery({"type": "unreliable_pattern"})

        # Many failures
        for i in range(10):
            detector.validate_pattern("unreliable_pattern", success=False)

        # Check if pattern is still active
        patterns = detector.get_recognized_patterns(min_confidence=0.5)

        # Pattern should be demoted (not in active patterns)
        assert len([p for p in patterns if "unreliable_pattern" in p.context]) == 0


class TestPatternContextDescription:
    """Test pattern context description generation."""

    def test_generates_descriptive_context(self):
        """Pattern context clearly describes what pattern detects."""
        detector = PatternDetector(threshold=3)

        discoveries = [
            {"type": "missing_example", "file": "tutorial.md", "section": "Getting Started"}
            for _ in range(3)
        ]

        for disc in discoveries:
            detector.add_discovery(disc)

        patterns = detector.get_recognized_patterns()
        context = patterns[0].context

        # Context should be descriptive and helpful
        assert len(context) > 10
        assert context != "missing_example"  # Not just the type
        # Should provide context about what it means
        assert any(word in context.lower() for word in ["tutorial", "example", "missing"])

    def test_generates_actionable_outcome(self):
        """Pattern outcome provides actionable guidance."""
        detector = PatternDetector(threshold=3)

        discoveries = [{"type": "sql_injection_risk", "file": f"api_{i}.py"} for i in range(3)]

        for disc in discoveries:
            detector.add_discovery(disc)

        patterns = detector.get_recognized_patterns()
        outcome = patterns[0].outcome

        # Outcome should tell agent what to do
        assert len(outcome) > 20
        # Should provide guidance
        assert any(word in outcome.lower() for word in ["check", "look", "pattern", "occurs"])


class TestPatternMetadata:
    """Test pattern metadata structure."""

    def test_includes_occurrence_count(self):
        """Pattern metadata includes total occurrence count."""
        detector = PatternDetector(threshold=3)

        for i in range(7):
            detector.add_discovery({"type": "counted_pattern"})

        patterns = detector.get_recognized_patterns()
        assert patterns[0].metadata["occurrences"] == 7

    def test_includes_example_discoveries(self):
        """Pattern metadata includes example discoveries."""
        detector = PatternDetector(threshold=3)

        discoveries = [
            {"type": "example_pattern", "file": f"file_{i}.py", "line": i * 10} for i in range(6)
        ]

        for disc in discoveries:
            detector.add_discovery(disc)

        patterns = detector.get_recognized_patterns()
        examples = patterns[0].metadata["examples"]

        # Should store some examples (typically 5)
        assert len(examples) <= 5
        assert all("file" in ex for ex in examples)

    def test_includes_first_seen_timestamp(self):
        """Pattern metadata includes when pattern was first seen."""
        detector = PatternDetector(threshold=3)

        before = datetime.now()

        for i in range(3):
            detector.add_discovery({"type": "timed_pattern"})

        after = datetime.now()

        patterns = detector.get_recognized_patterns()
        first_seen = patterns[0].metadata["first_seen"]

        # Should be within the time window
        assert before <= datetime.fromisoformat(first_seen) <= after
