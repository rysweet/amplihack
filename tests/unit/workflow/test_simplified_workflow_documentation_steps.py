"""
Test suite for documentation-specific steps in SIMPLIFIED_WORKFLOW.md.

Tests validate:
- Step 5: Documentation Outline (replaces Design step)
- Step 6: Write Documentation Content
- Step 7: Verify Examples Runnable (replaces TDD)
- Step 8: Markdown Quality Check (replaces Compilation)
- Step 9: Link Validation (replaces Type Checking)
"""

import re
from pathlib import Path

import pytest


@pytest.fixture
def workflow_file():
    """Path to SIMPLIFIED_WORKFLOW.md"""
    return Path(".claude/workflow/SIMPLIFIED_WORKFLOW.md")


@pytest.fixture
def workflow_content(workflow_file):
    """Load workflow file content"""
    assert workflow_file.exists(), f"SIMPLIFIED_WORKFLOW.md not found at {workflow_file}"
    return workflow_file.read_text(encoding="utf-8")


def extract_step_content(workflow_content: str, step_num: int) -> str:
    """Extract content of a specific step"""
    pattern = rf"##\s+Step {step_num}:.*?(?=##\s+Step \d+:|##\s+[^S]|\Z)"
    match = re.search(pattern, workflow_content, re.DOTALL)
    assert match, f"Could not extract Step {step_num} content"
    return match.group(0)


class TestStep5DocumentationOutline:
    """Test Step 5: Documentation Outline - replaces Design step"""

    def test_step5_exists(self, workflow_content):
        """Step 5 must exist"""
        assert re.search(r"##\s+Step 5:", workflow_content), "Missing Step 5"

    def test_step5_focuses_on_documentation_structure(self, workflow_content):
        """Step 5 must focus on documentation structure/outline"""
        step5 = extract_step_content(workflow_content, 5)

        # Check for outline, structure, organization concepts
        assert re.search(
            r"outline|structure|organization|table of contents|section", step5, re.IGNORECASE
        ), "Step 5 must focus on documentation outline/structure"

    def test_step5_addresses_content_hierarchy(self, workflow_content):
        """Step 5 must address content hierarchy (headings, sections)"""
        step5 = extract_step_content(workflow_content, 5)

        assert re.search(r"heading|hierarchy|section.*order|flow", step5, re.IGNORECASE), (
            "Step 5 must address content hierarchy"
        )

    def test_step5_considers_reader_needs(self, workflow_content):
        """Step 5 must consider reader needs and documentation goals"""
        step5 = extract_step_content(workflow_content, 5)

        assert re.search(r"reader|audience|user|purpose|goal", step5, re.IGNORECASE), (
            "Step 5 must consider reader needs"
        )


class TestStep6WriteContent:
    """Test Step 6: Write Documentation Content"""

    def test_step6_exists(self, workflow_content):
        """Step 6 must exist"""
        assert re.search(r"##\s+Step 6:", workflow_content), "Missing Step 6"

    def test_step6_focuses_on_writing(self, workflow_content):
        """Step 6 must focus on writing documentation content"""
        step6 = extract_step_content(workflow_content, 6)

        assert re.search(r"write|content|documentation|draft", step6, re.IGNORECASE), (
            "Step 6 must focus on writing content"
        )

    def test_step6_emphasizes_clarity(self, workflow_content):
        """Step 6 must emphasize clear, concise writing"""
        step6 = extract_step_content(workflow_content, 6)

        assert re.search(r"clear|concise|simple|plain.*language", step6, re.IGNORECASE), (
            "Step 6 must emphasize clarity"
        )

    def test_step6_includes_examples_guidance(self, workflow_content):
        """Step 6 must guide inclusion of code examples"""
        step6 = extract_step_content(workflow_content, 6)

        assert re.search(r"example|code.*snippet|sample", step6, re.IGNORECASE), (
            "Step 6 must guide example inclusion"
        )


class TestStep7VerifyExamples:
    """Test Step 7: Verify Examples Runnable - replaces TDD"""

    def test_step7_exists(self, workflow_content):
        """Step 7 must exist"""
        assert re.search(r"##\s+Step 7:", workflow_content), "Missing Step 7"

    def test_step7_requires_example_testing(self, workflow_content):
        """Step 7 must require testing all code examples"""
        step7 = extract_step_content(workflow_content, 7)

        assert re.search(
            r"test.*example|verify.*example|run.*example|example.*work", step7, re.IGNORECASE
        ), "Step 7 must require example testing"

    def test_step7_requires_fresh_environment(self, workflow_content):
        """Step 7 must require testing in fresh environment"""
        step7 = extract_step_content(workflow_content, 7)

        assert re.search(
            r"fresh.*environment|clean.*environment|new.*environment", step7, re.IGNORECASE
        ), "Step 7 must require fresh environment testing"

    def test_step7_covers_code_snippets(self, workflow_content):
        """Step 7 must cover testing code snippets from markdown"""
        step7 = extract_step_content(workflow_content, 7)

        assert re.search(r"code.*snippet|snippet|inline.*code", step7, re.IGNORECASE), (
            "Step 7 must cover code snippets"
        )

    def test_step7_covers_cli_commands(self, workflow_content):
        """Step 7 must cover testing CLI commands"""
        step7 = extract_step_content(workflow_content, 7)

        assert re.search(r"CLI.*command|command.*line|shell.*command", step7, re.IGNORECASE), (
            "Step 7 must cover CLI commands"
        )

    def test_step7_requires_evidence(self, workflow_content):
        """Step 7 must require evidence that examples work"""
        step7 = extract_step_content(workflow_content, 7)

        # Check for evidence, confirmation, verification requirements
        assert re.search(
            r"evidence|confirm|verify.*output|cannot proceed without", step7, re.IGNORECASE
        ), "Step 7 must require evidence"

    def test_step7_has_testing_template_or_checklist(self, workflow_content):
        """Step 7 should provide testing template or checklist"""
        step7 = extract_step_content(workflow_content, 7)

        # Check for table, checklist, or structured testing approach
        assert re.search(r"\|.*\||checklist|- \[|testing.*table", step7, re.IGNORECASE), (
            "Step 7 should provide testing template or checklist"
        )


class TestStep8MarkdownQuality:
    """Test Step 8: Markdown Quality Check - replaces Compilation"""

    def test_step8_exists(self, workflow_content):
        """Step 8 must exist"""
        assert re.search(r"##\s+Step 8:", workflow_content), "Missing Step 8"

    def test_step8_focuses_on_markdown_quality(self, workflow_content):
        """Step 8 must focus on markdown quality and formatting"""
        step8 = extract_step_content(workflow_content, 8)

        assert re.search(r"markdown|formatting|quality|consistency", step8, re.IGNORECASE), (
            "Step 8 must focus on markdown quality"
        )

    def test_step8_checks_heading_hierarchy(self, workflow_content):
        """Step 8 must check heading hierarchy"""
        step8 = extract_step_content(workflow_content, 8)

        assert re.search(
            r"heading.*hierarchy|heading.*level|skip.*heading", step8, re.IGNORECASE
        ), "Step 8 must check heading hierarchy"

    def test_step8_checks_code_block_syntax(self, workflow_content):
        """Step 8 must check code block syntax and language identifiers"""
        step8 = extract_step_content(workflow_content, 8)

        assert re.search(
            r"code.*block|language.*identifier|syntax.*highlight|```", step8, re.IGNORECASE
        ), "Step 8 must check code block syntax"

    def test_step8_checks_list_formatting(self, workflow_content):
        """Step 8 must check list formatting consistency"""
        step8 = extract_step_content(workflow_content, 8)

        assert re.search(
            r"list.*format|bullet|numbered.*list|consistent.*list", step8, re.IGNORECASE
        ), "Step 8 must check list formatting"

    def test_step8_checks_whitespace(self, workflow_content):
        """Step 8 must check for trailing whitespace"""
        step8 = extract_step_content(workflow_content, 8)

        assert re.search(r"trailing.*whitespace|whitespace|line.*break", step8, re.IGNORECASE), (
            "Step 8 must check whitespace"
        )

    def test_step8_supports_precommit_hooks(self, workflow_content):
        """Step 8 should mention pre-commit hooks if available"""
        step8 = extract_step_content(workflow_content, 8)

        # Optional check - should mention pre-commit as an option
        assert re.search(r"pre-commit|pre commit|hook", step8, re.IGNORECASE), (
            "Step 8 should mention pre-commit hooks option"
        )


class TestStep9LinkValidation:
    """Test Step 9: Link Validation - replaces Type Checking"""

    def test_step9_exists(self, workflow_content):
        """Step 9 must exist"""
        assert re.search(r"##\s+Step 9:", workflow_content), "Missing Step 9"

    def test_step9_validates_internal_links(self, workflow_content):
        """Step 9 must validate internal/relative links"""
        step9 = extract_step_content(workflow_content, 9)

        assert re.search(r"internal.*link|relative.*link|link.*resolve", step9, re.IGNORECASE), (
            "Step 9 must validate internal links"
        )

    def test_step9_validates_anchor_links(self, workflow_content):
        """Step 9 must validate anchor links to sections"""
        step9 = extract_step_content(workflow_content, 9)

        assert re.search(r"anchor.*link|#.*link|section.*link", step9, re.IGNORECASE), (
            "Step 9 must validate anchor links"
        )

    def test_step9_validates_external_links(self, workflow_content):
        """Step 9 must validate external links"""
        step9 = extract_step_content(workflow_content, 9)

        assert re.search(r"external.*link|http|URL|link.*check", step9, re.IGNORECASE), (
            "Step 9 must validate external links"
        )

    def test_step9_checks_broken_links(self, workflow_content):
        """Step 9 must check for broken links"""
        step9 = extract_step_content(workflow_content, 9)

        assert re.search(r"broken.*link|404|link.*work|dead.*link", step9, re.IGNORECASE), (
            "Step 9 must check for broken links"
        )

    def test_step9_provides_validation_method(self, workflow_content):
        """Step 9 must provide manual or automated validation method"""
        step9 = extract_step_content(workflow_content, 9)

        # Should mention curl, browser testing, or link checking tools
        assert re.search(r"curl|browser|tool|manual|check", step9, re.IGNORECASE), (
            "Step 9 must provide validation method"
        )

    def test_step9_includes_checklist(self, workflow_content):
        """Step 9 should include link validation checklist"""
        step9 = extract_step_content(workflow_content, 9)

        # Check for checklist format
        assert re.search(r"- \[|checklist", step9, re.IGNORECASE), "Step 9 should include checklist"


class TestDocumentationPhaseCoherence:
    """Test coherence of documentation phase (Steps 5-9)"""

    def test_steps_form_logical_sequence(self, workflow_content):
        """Steps 5-9 must form logical documentation workflow"""
        # Extract all doc phase steps
        step5 = extract_step_content(workflow_content, 5)
        step6 = extract_step_content(workflow_content, 6)
        step7 = extract_step_content(workflow_content, 7)
        step8 = extract_step_content(workflow_content, 8)
        step9 = extract_step_content(workflow_content, 9)

        # Verify logical progression: outline → write → verify examples → check format → validate links
        assert "outline" in step5.lower() or "structure" in step5.lower(), (
            "Step 5 should cover outlining"
        )
        assert "write" in step6.lower() or "content" in step6.lower(), "Step 6 should cover writing"
        assert "example" in step7.lower() and (
            "verify" in step7.lower() or "test" in step7.lower()
        ), "Step 7 should cover example verification"
        assert "markdown" in step8.lower() or "format" in step8.lower(), (
            "Step 8 should cover formatting"
        )
        assert "link" in step9.lower(), "Step 9 should cover link validation"

    def test_documentation_phase_marked_in_frontmatter(self, workflow_content):
        """Documentation phase (Steps 5-9) should be identified in frontmatter or overview"""
        # Check that frontmatter or overview identifies these as documentation phase
        assert re.search(
            r"documentation.*phase|phase.*documentation", workflow_content, re.IGNORECASE
        ), "Documentation phase should be identified"

    def test_no_code_compilation_steps(self, workflow_content):
        """Documentation workflow must not include code compilation steps"""
        # Extract documentation phase steps
        doc_phase = ""
        for step_num in range(5, 10):
            doc_phase += extract_step_content(workflow_content, step_num)

        # Should NOT mention compilation, building, pytest (except as examples)
        compilation_terms = [r"(?<!\w)compile(?!\w)", r"(?<!\w)build(?!\w)", r"make.*build"]
        for term in compilation_terms:
            matches = re.findall(term, doc_phase, re.IGNORECASE)
            # Filter out matches that are in example contexts
            non_example_matches = [
                m
                for m in matches
                if "example"
                not in doc_phase[max(0, doc_phase.find(m) - 50) : doc_phase.find(m) + 50].lower()
            ]
            assert len(non_example_matches) == 0, (
                f"Documentation phase should not mention '{term}' (found {len(non_example_matches)} instances)"
            )
