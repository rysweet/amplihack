"""
Standalone unit tests for task classification logic in prompt-writer agent.

This version doesn't require pytest and can be run directly with Python.
Tests the keyword-based classification system that distinguishes between
EXECUTABLE code requests and DOCUMENTATION requests.
"""


class TestTaskClassification:
    """Test task classification scenarios for prompt-writer agent."""

    # Classification keywords defined in prompt-writer.md
    EXECUTABLE_KEYWORDS = [
        "cli", "command-line", "program", "script", "application", "app",
        "run", "execute", "binary", "executable", "service", "daemon",
        "api server", "web server", "microservice", "backend"
    ]

    DOCUMENTATION_KEYWORDS = [
        "skill", "guide", "template", "documentation", "docs",
        "tutorial", "how-to", "instructions", "reference",
        "specification", "design document"
    ]

    AMBIGUOUS_KEYWORDS = ["tool"]

    def classify_request(self, request_text: str) -> str:
        """
        Simulate the classification logic from prompt-writer.md.

        This implements the keyword-based classification that should match
        the behavior described in the prompt-writer agent.

        Args:
            request_text: The user's request text

        Returns:
            Classification as "EXECUTABLE", "DOCUMENTATION", or "AMBIGUOUS"
        """
        request_lower = request_text.lower()

        # Check for executable keywords
        has_executable = any(keyword in request_lower for keyword in self.EXECUTABLE_KEYWORDS)

        # Check for documentation keywords
        has_documentation = any(keyword in request_lower for keyword in self.DOCUMENTATION_KEYWORDS)

        # If both or neither, check for ambiguous keywords
        if has_executable and not has_documentation:
            return "EXECUTABLE"
        elif has_documentation and not has_executable:
            return "DOCUMENTATION"
        elif any(keyword in request_lower for keyword in self.AMBIGUOUS_KEYWORDS):
            # Check if it's just "tool" without clarifying context
            if not has_executable and not has_documentation:
                return "AMBIGUOUS"

        # Default to requiring clarification if unclear
        if has_executable and has_documentation:
            return "AMBIGUOUS"

        return "AMBIGUOUS"  # Fail-secure: default to asking user when uncertain

    def run_all_tests(self):
        """Run all test methods and report results."""
        tests = [
            self.test_executable_classification_cli_tool,
            self.test_executable_classification_script,
            self.test_executable_classification_application,
            self.test_executable_classification_program,
            self.test_executable_classification_api_server,
            self.test_documentation_classification_skill,
            self.test_documentation_classification_guide,
            self.test_documentation_classification_tutorial,
            self.test_documentation_classification_template,
            self.test_ambiguous_classification_tool_only,
            self.test_classification_keywords_completeness,
            self.test_classification_speed_requirement,
            self.test_classification_deterministic,
            self.test_classification_examples,
        ]

        passed = 0
        failed = 0
        errors = []

        for test in tests:
            try:
                test()
                passed += 1
                print(f"✓ {test.__name__}")
            except AssertionError as e:
                failed += 1
                errors.append((test.__name__, str(e)))
                print(f"✗ {test.__name__}: {e}")
            except Exception as e:
                failed += 1
                errors.append((test.__name__, str(e)))
                print(f"✗ {test.__name__}: ERROR - {e}")

        print(f"\n{'='*70}")
        print(f"Test Results: {passed} passed, {failed} failed")
        print(f"{'='*70}")

        if errors:
            print("\nFailures:")
            for test_name, error in errors:
                print(f"  {test_name}: {error}")

        return failed == 0

    def test_executable_classification_cli_tool(self):
        """Test that CLI tool requests are classified as EXECUTABLE."""
        request = "Create a CLI tool for analyzing log files"
        classification = self.classify_request(request)
        assert classification == "EXECUTABLE", \
            "CLI tool requests should be classified as EXECUTABLE"

    def test_executable_classification_script(self):
        """Test that script requests are classified as EXECUTABLE."""
        request = "Build a Python script to process CSV files"
        classification = self.classify_request(request)
        assert classification == "EXECUTABLE", \
            "Script requests should be classified as EXECUTABLE"

    def test_executable_classification_application(self):
        """Test that application requests are classified as EXECUTABLE."""
        request = "Develop an application for managing tasks"
        classification = self.classify_request(request)
        assert classification == "EXECUTABLE", \
            "Application requests should be classified as EXECUTABLE"

    def test_executable_classification_program(self):
        """Test that program requests are classified as EXECUTABLE."""
        request = "Write a program to automate backups"
        classification = self.classify_request(request)
        assert classification == "EXECUTABLE", \
            "Program requests should be classified as EXECUTABLE"

    def test_executable_classification_api_server(self):
        """Test that API server requests are classified as EXECUTABLE."""
        request = "Create an API server for handling webhooks"
        classification = self.classify_request(request)
        assert classification == "EXECUTABLE", \
            "API server requests should be classified as EXECUTABLE"

    def test_documentation_classification_skill(self):
        """Test that Claude Code Skill requests are classified as DOCUMENTATION."""
        request = "Create a Claude Code Skill for JSON processing"
        classification = self.classify_request(request)
        assert classification == "DOCUMENTATION", \
            "Claude Code Skill requests should be classified as DOCUMENTATION"

    def test_documentation_classification_guide(self):
        """Test that guide requests are classified as DOCUMENTATION."""
        request = "Write a guide for using the API"
        classification = self.classify_request(request)
        assert classification == "DOCUMENTATION", \
            "Guide requests should be classified as DOCUMENTATION"

    def test_documentation_classification_tutorial(self):
        """Test that tutorial requests are classified as DOCUMENTATION."""
        request = "Create a tutorial on setting up the development environment"
        classification = self.classify_request(request)
        assert classification == "DOCUMENTATION", \
            "Tutorial requests should be classified as DOCUMENTATION"

    def test_documentation_classification_template(self):
        """Test that template requests are classified as DOCUMENTATION."""
        request = "Build a template for feature specifications"
        classification = self.classify_request(request)
        assert classification == "DOCUMENTATION", \
            "Template requests should be classified as DOCUMENTATION"

    def test_ambiguous_classification_tool_only(self):
        """Test that 'tool' alone without context is classified as AMBIGUOUS."""
        request = "Create a tool"
        classification = self.classify_request(request)
        assert classification == "AMBIGUOUS", \
            "'tool' alone without context should be classified as AMBIGUOUS"

    def test_classification_keywords_completeness(self):
        """Test that classification keyword sets are comprehensive."""
        # Verify we have sufficient keywords for reliable classification
        assert len(self.EXECUTABLE_KEYWORDS) >= 10, \
            "Should have at least 10 executable keywords"
        assert len(self.DOCUMENTATION_KEYWORDS) >= 8, \
            "Should have at least 8 documentation keywords"

        # Verify no overlap between keyword sets
        executable_set = set(self.EXECUTABLE_KEYWORDS)
        documentation_set = set(self.DOCUMENTATION_KEYWORDS)
        ambiguous_set = set(self.AMBIGUOUS_KEYWORDS)

        assert not (executable_set & documentation_set), \
            "Executable and documentation keywords should not overlap"
        assert not (executable_set & ambiguous_set), \
            "Executable and ambiguous keywords should not overlap"
        assert not (documentation_set & ambiguous_set), \
            "Documentation and ambiguous keywords should not overlap"

    def test_classification_speed_requirement(self):
        """Test that classification completes quickly (< 5 seconds)."""
        import time

        test_requests = [
            "Create a CLI tool",
            "Build a Claude Code Skill",
            "Create a tool",
            "Develop an application",
            "Write a guide"
        ]

        start_time = time.time()
        for request in test_requests:
            self.classify_request(request)
        end_time = time.time()

        elapsed_time = end_time - start_time
        assert elapsed_time < 5.0, \
            f"Classification should complete in < 5 seconds, took {elapsed_time:.2f}s"

    def test_classification_deterministic(self):
        """Test that classification is deterministic (same input = same output)."""
        request = "Create a CLI tool for log analysis"

        # Run classification multiple times
        results = [self.classify_request(request) for _ in range(10)]

        # All results should be identical
        assert len(set(results)) == 1, \
            "Classification should be deterministic for the same input"
        assert results[0] == "EXECUTABLE", \
            "CLI tool should consistently classify as EXECUTABLE"

    def test_classification_examples(self):
        """Test classification for various example requests."""
        test_cases = [
            ("Create a CLI program", "EXECUTABLE"),
            ("Build a Python script", "EXECUTABLE"),
            ("Write an application", "EXECUTABLE"),
            ("Create a Claude Code Skill", "DOCUMENTATION"),
            ("Write a tutorial", "DOCUMENTATION"),
            ("Build a guide", "DOCUMENTATION"),
            ("Create a tool", "AMBIGUOUS"),
        ]

        for request, expected in test_cases:
            classification = self.classify_request(request)
            assert classification == expected, \
                f"Request '{request}' should be classified as {expected}, got {classification}"


def main():
    """Main test runner."""
    print("Running Task Classification Tests")
    print("="*70)

    tester = TestTaskClassification()
    success = tester.run_all_tests()

    if success:
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
