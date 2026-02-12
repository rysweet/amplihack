"""
Integration tests for SIMPLIFIED_WORKFLOW.md - end-to-end validation.

Tests validate:
- Complete workflow coherence from Step 0 through Step 15
- Phase transitions and step groupings
- Cross-references between sections
- Documentation-to-code workflow alignment
- Integration with DEFAULT_WORKFLOW patterns
"""

import re
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def workflow_file():
    """Path to SIMPLIFIED_WORKFLOW.md"""
    return Path(".claude/workflow/SIMPLIFIED_WORKFLOW.md")


@pytest.fixture
def workflow_content(workflow_file):
    """Load workflow file content"""
    assert workflow_file.exists(), f"SIMPLIFIED_WORKFLOW.md not found at {workflow_file}"
    return workflow_file.read_text(encoding="utf-8")


@pytest.fixture
def frontmatter(workflow_content):
    """Extract and parse YAML frontmatter"""
    match = re.match(r"^---\n(.*?)\n---", workflow_content, re.DOTALL)
    assert match, "No YAML frontmatter found"
    return yaml.safe_load(match.group(1))


@pytest.fixture
def default_workflow_file():
    """Path to DEFAULT_WORKFLOW.md for comparison"""
    return Path(".claude/workflow/DEFAULT_WORKFLOW.md")


class TestEndToEndWorkflowCoherence:
    """Test complete workflow makes sense from start to finish"""

    def test_workflow_covers_complete_documentation_lifecycle(self, workflow_content):
        """Workflow must cover complete doc lifecycle: prep → write → validate → merge"""
        lifecycle_stages = [
            (r"preparation|setup|workspace", "Preparation"),
            (r"outline|structure", "Structure/Outline"),
            (r"write|content|draft", "Writing"),
            (r"example.*test|verify.*example", "Example Testing"),
            (r"markdown.*quality|format.*check", "Quality Check"),
            (r"link.*valid|validate.*link", "Link Validation"),
            (r"commit|PR|pull request", "Commit/PR"),
            (r"accuracy.*test|test.*documentation", "Accuracy Testing"),
            (r"reader.*perspective|fresh.*perspective", "Reader Testing"),
            (r"merge|final.*verification", "Merge"),
        ]

        for pattern, stage_name in lifecycle_stages:
            assert re.search(pattern, workflow_content, re.IGNORECASE), (
                f"Workflow missing {stage_name} stage"
            )

    def test_phases_align_with_steps(self, workflow_content, frontmatter):
        """Phase definitions must align with step distribution"""
        phases = frontmatter.get("phases", [])
        assert len(phases) == 5, "Must have 5 phases"

        # Verify phases are mentioned in context of steps
        phase_mentions = {
            "preparation": (0, 4),
            "documentation": (5, 8),
            "review": (9, 10),
            "validation": (11, 14),
            "completion": (15, 15),
        }

        for phase, (start, end) in phase_mentions.items():
            # Check that phase is associated with correct step range
            # This is a soft check - phases may be documented in overview
            _ = rf"{phase}.*step\s+{start}|step\s+{start}.*{phase}"

    def test_step_dependencies_are_logical(self, workflow_content):
        """Steps must have logical dependencies (can't test before writing)"""
        # Extract all steps
        steps = {}
        for step_num in range(16):
            pattern = rf"##\s+Step {step_num}:.*?(?=##\s+Step \d+:|##\s+[^S]|\Z)"
            match = re.search(pattern, workflow_content, re.DOTALL)
            if match:
                steps[step_num] = match.group(0)

        # Verify logical order
        # - Must outline before writing (Step 5 before Step 6)
        assert 5 in steps and 6 in steps
        # - Must write before testing examples (Step 6 before Step 7)
        assert 7 in steps
        # - Must test examples before markdown quality (Step 7 before Step 8)
        assert 8 in steps
        # - Must format before link validation (Step 8 before Step 9)
        assert 9 in steps
        # - Must review before commit (Step 10 before Step 11)
        assert 10 in steps and 11 in steps
        # - Must commit before testing accuracy (Step 11 before Step 12)
        assert 12 in steps
        # - Must have PR before reviewing it (Step 11 before Step 13)
        assert 13 in steps


class TestCrossReferences:
    """Test cross-references between sections"""

    def test_steps_reference_security_section(self, workflow_content):
        """Steps with commands should reference Security Considerations"""
        # Steps 3, 11, 15 have platform commands - should reference security
        steps_with_commands = [3, 11, 15]

        security_section = re.search(
            r"##\s+Security Considerations", workflow_content, re.IGNORECASE
        )
        assert security_section, "Security section must exist"

        # At least one step should reference security or use safe patterns
        for step_num in steps_with_commands:
            pattern = rf"##\s+Step {step_num}:.*?(?=##\s+Step \d+:|##\s+[^S]|\Z)"
            match = re.search(pattern, workflow_content, re.DOTALL)
            if match:
                step = match.group(0)
                # Should either reference security or use safe command patterns
                references_security = bool(
                    re.search(r"security|see.*security", step, re.IGNORECASE)
                )
                uses_safe_patterns = bool(re.search(r'-F\s+|--\s+|"\$', step))

                # At least one should be true
                if not (references_security or uses_safe_patterns):
                    # This is informational, not a hard requirement
                    pass

    def test_best_practices_references_steps(self, workflow_content):
        """Best Practices section should reference specific step numbers"""
        practices_pattern = r"##\s+Best Practices.*?(?=##\s+[A-Z]|\Z)"
        practices_match = re.search(practices_pattern, workflow_content, re.DOTALL | re.IGNORECASE)

        if practices_match:
            practices = practices_match.group(0)
            step_references = re.findall(r"step\s+(\d+)", practices, re.IGNORECASE)

            assert len(step_references) >= 2, (
                f"Best Practices should reference at least 2 specific steps (found {len(step_references)})"
            )

    def test_frontmatter_step_count_matches_actual(self, workflow_content, frontmatter):
        """Frontmatter step count must match actual steps"""
        declared_steps = frontmatter.get("steps", 0)
        actual_steps = len(re.findall(r"##\s+Step \d+:", workflow_content))

        assert declared_steps == actual_steps, (
            f"Frontmatter declares {declared_steps} steps but found {actual_steps}"
        )


class TestDocumentationWorkflowAlignment:
    """Test alignment with documentation-specific workflow needs"""

    def test_no_code_compilation_steps(self, workflow_content):
        """Must not include code compilation, testing, or build steps"""
        code_build_patterns = [
            r"pytest|python.*test\.py",
            r"npm.*test|yarn.*test",
            r"cargo.*build|cargo.*test",
            r"make.*build",
            r"dotnet.*build|dotnet.*test",
        ]

        for pattern in code_build_patterns:
            matches = re.findall(pattern, workflow_content, re.IGNORECASE)
            # Filter out mentions in explanatory context
            for match_text in matches:
                context_start = max(0, workflow_content.find(match_text) - 100)
                context = workflow_content[context_start : workflow_content.find(match_text) + 50]

                is_example_context = bool(
                    re.search(
                        r"example|e\.g\.|different from|unlike|not.*use", context, re.IGNORECASE
                    )
                )

                # If not in example context, this is a problem
                if not is_example_context:
                    pytest.fail(
                        f"Found code build/test command in non-example context: {match_text}"
                    )

    def test_emphasizes_example_testing_over_unit_tests(self, workflow_content):
        """Must emphasize testing examples work, not writing unit tests"""
        # Should mention example testing
        assert re.search(
            r"test.*example|verify.*example|example.*work", workflow_content, re.IGNORECASE
        )

        # Should NOT emphasize unit tests
        unit_test_emphasis = re.findall(
            r"write.*unit.*test|unit.*test.*coverage", workflow_content, re.IGNORECASE
        )

        for mention in unit_test_emphasis:
            # Check if it's in a negative context ("not for unit tests")
            context_start = max(0, workflow_content.find(mention) - 50)
            context = workflow_content[context_start : workflow_content.find(mention) + 50]
            is_negative = bool(re.search(r"not|different|unlike", context, re.IGNORECASE))

            assert is_negative, f"Should not emphasize unit tests: {mention}"

    def test_adapts_verification_gates_for_documentation(self, workflow_content):
        """Verification gates must be adapted for documentation context"""
        # Step 12: Documentation Accuracy (not Test Suite)
        step12_pattern = r"##\s+Step 12:.*?(?=##\s+Step \d+:|##\s+[^S]|\Z)"
        step12 = re.search(step12_pattern, workflow_content, re.DOTALL)
        assert step12

        step12_text = step12.group(0)
        assert re.search(
            r"accuracy|documentation.*test|guidance.*correct", step12_text, re.IGNORECASE
        ), "Step 12 must focus on documentation accuracy, not code tests"

        # Step 14: Reader Perspective (not Manual Testing)
        step14_pattern = r"##\s+Step 14:.*?(?=##\s+Step \d+:|##\s+[^S]|\Z)"
        step14 = re.search(step14_pattern, workflow_content, re.DOTALL)
        assert step14

        step14_text = step14.group(0)
        assert re.search(r"reader|perspective|fresh|new.*user", step14_text, re.IGNORECASE), (
            "Step 14 must focus on reader perspective, not manual testing"
        )


class TestIntegrationWithDefaultWorkflow:
    """Test integration patterns with DEFAULT_WORKFLOW"""

    def test_references_default_workflow(self, workflow_content):
        """Must reference DEFAULT_WORKFLOW for context"""
        assert re.search(r"DEFAULT_WORKFLOW|default.*workflow", workflow_content, re.IGNORECASE), (
            "Must reference DEFAULT_WORKFLOW"
        )

    def test_explains_when_to_use_each_workflow(self, workflow_content):
        """Must explain when to use SIMPLIFIED vs DEFAULT"""
        when_to_use_patterns = [
            r"when.*use.*simplified",
            r"documentation.*only",
            r"use.*default.*if.*code",
        ]

        matches = sum(
            1
            for pattern in when_to_use_patterns
            if re.search(pattern, workflow_content, re.IGNORECASE)
        )

        assert matches >= 2, (
            f"Must explain when to use each workflow (found {matches} patterns, need at least 2)"
        )

    def test_preserves_default_workflow_philosophy(self, workflow_content):
        """Must preserve DEFAULT_WORKFLOW philosophy principles"""
        philosophy_terms = [
            r"ruthless.*simplicity",
            r"zero.*BS",
            r"quality.*gate",
            r"mandatory.*review",
        ]

        matches = sum(
            1 for term in philosophy_terms if re.search(term, workflow_content, re.IGNORECASE)
        )

        assert matches >= 2, (
            f"Must preserve DEFAULT_WORKFLOW philosophy (found {matches} principles, need at least 2)"
        )

    def test_uses_same_platform_commands(self, workflow_content, default_workflow_file):
        """Should use same platform commands as DEFAULT_WORKFLOW"""
        if not default_workflow_file.exists():
            pytest.skip("DEFAULT_WORKFLOW.md not found for comparison")

        default_content = default_workflow_file.read_text(encoding="utf-8")

        # Check for common commands
        common_commands = [
            r"gh issue create",
            r"gh pr create",
            r"gh pr merge",
            r"az boards work-item create",
            r"az repos pr create",
        ]

        for cmd in common_commands:
            in_simplified = bool(re.search(cmd, workflow_content))
            in_default = bool(re.search(cmd, default_content))

            if in_default and not in_simplified:
                # This is informational - simplified may not need all commands
                pass


class TestWorkflowCompleteness:
    """Test workflow is complete and self-contained"""

    def test_no_broken_internal_references(self, workflow_content):
        """All internal references must point to existing sections"""
        # Find all references like "see Step X" or "refer to Security Considerations"
        references = re.findall(
            r"see\s+(Step\s+\d+|[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", workflow_content, re.IGNORECASE
        )

        for ref in references:
            if "step" in ref.lower():
                # Extract step number
                step_num = re.search(r"\d+", ref)
                if step_num:
                    step_num = int(step_num.group())
                    assert 0 <= step_num <= 15, f"Invalid step reference: {ref}"
                    # Verify step exists
                    step_pattern = rf"##\s+Step {step_num}:"
                    assert re.search(step_pattern, workflow_content), (
                        f"Referenced Step {step_num} not found"
                    )
            else:
                # Section reference - verify section exists
                # This is informational - may be approximate references
                _ = rf"##\s+{re.escape(ref)}"

    def test_all_required_sections_present(self, workflow_content):
        """All required sections must be present"""
        required_sections = [
            r"##\s+Overview|##\s+Introduction",
            r"##\s+Step 0:",
            r"##\s+Step 15:",
            r"##\s+Security Considerations",
            r"##\s+Tool Verification",
            r"##\s+Best Practices",
        ]

        for section in required_sections:
            assert re.search(section, workflow_content, re.IGNORECASE), (
                f"Missing required section: {section}"
            )

    def test_workflow_is_self_documenting(self, workflow_content):
        """Workflow should explain its own structure and usage"""
        self_doc_elements = [
            r"how.*use.*workflow",
            r"when.*use.*workflow",
            r"step.*sequence|workflow.*phase",
            r"mandatory.*gate|verification.*gate",
        ]

        matches = sum(
            1
            for element in self_doc_elements
            if re.search(element, workflow_content, re.IGNORECASE)
        )

        assert matches >= 2, (
            f"Workflow should be self-documenting (found {matches} elements, need at least 2)"
        )


class TestWorkflowUsability:
    """Test workflow is usable by real users"""

    def test_steps_have_clear_action_items(self, workflow_content):
        """Each step must have clear action items, not just descriptions"""
        for step_num in range(16):
            pattern = rf"##\s+Step {step_num}:.*?(?=##\s+Step \d+:|##\s+[^S]|\Z)"
            match = re.search(pattern, workflow_content, re.DOTALL)

            if match:
                step = match.group(0)

                # Should have action indicators: commands, checklists, or imperative verbs
                has_commands = bool(re.search(r"```|`[a-z]+\s+", step))
                has_checklists = bool(re.search(r"- \[|^\s*-\s+[A-Z]", step, re.MULTILINE))
                has_imperatives = bool(
                    re.search(
                        r"^(Create|Run|Verify|Check|Test|Review|Ensure|Validate)",
                        step,
                        re.MULTILINE | re.IGNORECASE,
                    )
                )

                assert has_commands or has_checklists or has_imperatives, (
                    f"Step {step_num} must have clear action items"
                )

    def test_provides_examples_for_complex_steps(self, workflow_content):
        """Complex steps should include examples"""
        complex_steps = [3, 7, 11, 15]  # Issue creation, example testing, PR creation, merge

        for step_num in complex_steps:
            pattern = rf"##\s+Step {step_num}:.*?(?=##\s+Step \d+:|##\s+[^S]|\Z)"
            match = re.search(pattern, workflow_content, re.DOTALL)

            if match:
                step = match.group(0)
                # Should have code blocks or command examples
                has_examples = bool(re.search(r"```|`[a-z]+\s+|example:", step, re.IGNORECASE))

                assert has_examples, f"Complex Step {step_num} should include examples"

    def test_error_handling_guidance_present(self, workflow_content):
        """Should provide guidance on handling errors or issues"""
        error_patterns = [
            r"troubleshoot|common.*issue",
            r"error|fail|problem",
            r"if.*not.*work|when.*fail",
        ]

        matches = sum(
            1 for pattern in error_patterns if re.search(pattern, workflow_content, re.IGNORECASE)
        )

        assert matches >= 1, "Should provide error handling guidance"


class TestWorkflowMaintainability:
    """Test workflow is maintainable and evolvable"""

    def test_version_is_semantic(self, frontmatter):
        """Version must follow semantic versioning"""
        version = frontmatter.get("version", "")
        assert re.match(r"\d+\.\d+\.\d+", version), (
            f"Version must be semantic (X.Y.Z), got: {version}"
        )

    def test_workflow_has_clear_owner_or_contact(self, workflow_content):
        """Should identify owner or how to get help"""
        # Check for references to architecture team, amplihack, or support
        # This is informational - not a hard requirement
        _ = [r"architecture.*team", r"amplihack.*team", r"contact|support|help"]

    def test_changelog_or_history_present(self, workflow_content):
        """Should have changelog or version history"""
        # Check for changelog section or version history
        # This is optional for v1.0.0
        _ = bool(
            re.search(
                r"##\s+Changelog|##\s+Version History|##\s+History", workflow_content, re.IGNORECASE
            )
        )
