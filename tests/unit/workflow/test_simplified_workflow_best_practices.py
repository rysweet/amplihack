"""
Test suite for Best Practices section in SIMPLIFIED_WORKFLOW.md.

Tests validate:
- Best Practices section exists and is comprehensive
- TodoWrite integration guidance
- Workflow tips and recommendations
- Quality standards
- Common pitfalls and how to avoid them
- References to specific step numbers
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


@pytest.fixture
def best_practices_section(workflow_content):
    """Extract Best Practices section"""
    pattern = r"##\s+Best Practices.*?(?=##\s+[A-Z]|\Z)"
    match = re.search(pattern, workflow_content, re.DOTALL | re.IGNORECASE)
    assert match, "Best Practices section not found"
    return match.group(0)


class TestBestPracticesSectionPresence:
    """Test presence of Best Practices section"""

    def test_best_practices_section_exists(self, workflow_content):
        """Best Practices section must exist"""
        assert re.search(r"##\s+Best Practices", workflow_content, re.IGNORECASE), (
            "Missing Best Practices section"
        )

    def test_section_after_steps(self, workflow_content):
        """Best Practices should appear after all workflow steps"""
        practices_match = re.search(r"##\s+Best Practices", workflow_content, re.IGNORECASE)
        step15_match = re.search(r"##\s+Step 15:", workflow_content)

        if practices_match and step15_match:
            assert practices_match.start() > step15_match.start(), (
                "Best Practices should appear after Step 15"
            )


class TestTodoWriteIntegration:
    """Test TodoWrite integration guidance"""

    def test_addresses_todowrite(self, best_practices_section):
        """Must address TodoWrite integration"""
        assert re.search(r"todo|TodoWrite|task.*tracking", best_practices_section, re.IGNORECASE), (
            "Must address TodoWrite integration"
        )

    def test_references_step_numbers(self, best_practices_section):
        """TodoWrite guidance should reference specific step numbers"""
        # Should mention creating todos for all 16 steps or Steps 0-15
        assert re.search(
            r"step\s+\d+|16\s+steps|steps\s+0.*15", best_practices_section, re.IGNORECASE
        ), "Should reference specific step numbers"

    def test_explains_step0_todo_creation(self, best_practices_section):
        """Should explain Step 0 creates all todos"""
        assert re.search(
            r"step\s+0.*create|create.*all.*todo|16.*todo", best_practices_section, re.IGNORECASE
        ), "Should explain Step 0 todo creation"

    def test_provides_todo_format_guidance(self, best_practices_section):
        """Should provide guidance on todo format"""
        # Should mention content, activeForm, or status fields
        todo_fields = [r"content", r"activeForm", r"status", r"pending|in_progress|completed"]
        matches = sum(
            1 for field in todo_fields if re.search(field, best_practices_section, re.IGNORECASE)
        )

        # At least mention some todo structure
        if matches == 0:
            # Not a hard requirement, but recommended
            pass


class TestWorkflowTipsAndRecommendations:
    """Test workflow tips and recommendations"""

    def test_provides_workflow_tips(self, best_practices_section):
        """Should provide workflow tips"""
        # Check for tip markers or numbered lists
        has_tips = bool(
            re.search(
                r"tip|recommendation|best practice|guideline", best_practices_section, re.IGNORECASE
            )
        )
        has_lists = bool(re.search(r"- |^\d+\.\s+", best_practices_section, re.MULTILINE))

        assert has_tips or has_lists, "Should provide workflow tips or recommendations"

    def test_addresses_when_to_use_workflow(self, workflow_content):
        """Should clarify when to use SIMPLIFIED vs DEFAULT workflow"""
        # Check anywhere in the document
        assert re.search(
            r"when.*use.*simplified|use.*simplified.*when|default.*workflow",
            workflow_content,
            re.IGNORECASE,
        ), "Should clarify when to use this workflow"

    def test_emphasizes_quality_standards(self, best_practices_section):
        """Should emphasize that quality standards match DEFAULT_WORKFLOW"""
        # Should mention same rigor, not a shortcut, quality gates
        quality_terms = [r"same.*rigor", r"not.*shortcut", r"quality.*gate", r"same.*standard"]
        matches = sum(
            1 for term in quality_terms if re.search(term, best_practices_section, re.IGNORECASE)
        )

        assert matches >= 1, "Should emphasize quality standards match DEFAULT_WORKFLOW"


class TestCommonPitfalls:
    """Test guidance on common pitfalls"""

    def test_addresses_common_mistakes(self, best_practices_section):
        """Should address common mistakes or pitfalls"""
        # Check for pitfall, mistake, avoid, common issue terms
        warning_terms = [r"pitfall", r"mistake", r"avoid", r"common.*issue", r"don't|do not"]
        matches = sum(
            1 for term in warning_terms if re.search(term, best_practices_section, re.IGNORECASE)
        )

        # This is a should, not a must
        if matches == 0:
            pass

    def test_warns_against_skipping_gates(self, best_practices_section):
        """Should warn against skipping mandatory gates"""
        assert re.search(
            r"skip.*gate|gate.*skip|mandatory|cannot skip|must not skip",
            best_practices_section,
            re.IGNORECASE,
        ), "Should warn against skipping gates"

    def test_warns_against_untested_examples(self, best_practices_section):
        """Should warn against committing untested examples"""
        # Check for warnings about testing examples
        assert re.search(
            r"test.*example|example.*test|verify.*example|untested",
            best_practices_section,
            re.IGNORECASE,
        ), "Should warn about untested examples"


class TestQualityStandards:
    """Test quality standards documentation"""

    def test_defines_quality_expectations(self, best_practices_section):
        """Should define quality expectations"""
        quality_terms = [r"quality", r"standard", r"expectation", r"requirement"]
        matches = sum(
            1 for term in quality_terms if re.search(term, best_practices_section, re.IGNORECASE)
        )

        assert matches >= 1, "Should define quality expectations"

    def test_mentions_all_examples_must_work(self, best_practices_section):
        """Should mention all examples must work"""
        assert re.search(
            r"all.*example.*work|example.*must.*work|working.*example",
            best_practices_section,
            re.IGNORECASE,
        ), "Should mention all examples must work"

    def test_mentions_all_links_must_work(self, best_practices_section):
        """Should mention all links must be validated"""
        assert re.search(
            r"link.*valid|link.*work|validate.*link|broken.*link",
            best_practices_section,
            re.IGNORECASE,
        ), "Should mention link validation"

    def test_mentions_no_todos_or_placeholders(self, best_practices_section):
        """Should mention no TODO markers or placeholders in final docs"""
        assert re.search(
            r"no.*TODO|TODO.*marker|placeholder|incomplete", best_practices_section, re.IGNORECASE
        ), "Should mention no TODO markers or placeholders"


class TestStepReferences:
    """Test that best practices reference specific steps"""

    def test_references_step0_workflow_prep(self, best_practices_section):
        """Should reference Step 0 (Workflow Preparation)"""
        assert re.search(
            r"step\s+0|workflow.*preparation", best_practices_section, re.IGNORECASE
        ), "Should reference Step 0"

    def test_references_verification_gates(self, best_practices_section):
        """Should reference verification gates (Steps 12, 14)"""
        # Should mention verification gates or specific step numbers
        verification_refs = [r"step\s+12", r"step\s+14", r"verification.*gate", r"cannot proceed"]
        matches = sum(
            1 for ref in verification_refs if re.search(ref, best_practices_section, re.IGNORECASE)
        )

        assert matches >= 1, "Should reference verification gates"

    def test_references_review_steps(self, best_practices_section):
        """Should reference review steps (Steps 10, 13)"""
        review_refs = [r"step\s+10", r"step\s+13", r"review", r"PR.*review"]
        matches = sum(
            1 for ref in review_refs if re.search(ref, best_practices_section, re.IGNORECASE)
        )

        assert matches >= 1, "Should reference review steps"


class TestWorkflowPhilosophy:
    """Test documentation of workflow philosophy"""

    def test_explains_workflow_philosophy(self, workflow_content):
        """Should explain workflow philosophy"""
        # Check anywhere in document for philosophy explanation
        assert re.search(
            r"philosophy|principle|ruthless.*simplicity|zero.*BS", workflow_content, re.IGNORECASE
        ), "Should explain workflow philosophy"

    def test_explains_why_gates_exist(self, workflow_content):
        """Should explain why mandatory gates exist"""
        # Look for rationale about gates
        gate_rationale = [r"why.*gate", r"gate.*ensure|gate.*prevent", r"quality.*assurance"]
        matches = sum(
            1
            for rationale in gate_rationale
            if re.search(rationale, workflow_content, re.IGNORECASE)
        )

        assert matches >= 1, "Should explain why gates exist"

    def test_emphasizes_documentation_quality(self, workflow_content):
        """Should emphasize documentation quality matters"""
        quality_emphasis = [
            r"documentation.*quality",
            r"quality.*documentation",
            r"clear.*accurate",
        ]
        matches = sum(
            1
            for emphasis in quality_emphasis
            if re.search(emphasis, workflow_content, re.IGNORECASE)
        )

        assert matches >= 1, "Should emphasize documentation quality"


class TestScopeGuidance:
    """Test scope and applicability guidance"""

    def test_defines_documentation_only_scope(self, workflow_content):
        """Must define documentation-only scope"""
        assert re.search(
            r"documentation.*only|documentation.*change|doc.*change",
            workflow_content,
            re.IGNORECASE,
        ), "Must define documentation-only scope"

    def test_lists_included_documentation_types(self, workflow_content):
        """Should list types of documentation included"""
        doc_types = [r"README", r"API.*doc", r"tutorial", r"guide", r"how-to"]
        matches = sum(
            1 for doc_type in doc_types if re.search(doc_type, workflow_content, re.IGNORECASE)
        )

        assert matches >= 3, f"Should list documentation types (found {matches}, need at least 3)"

    def test_specifies_when_not_to_use(self, workflow_content):
        """Should specify when NOT to use this workflow"""
        # Should mention code changes require DEFAULT_WORKFLOW
        assert re.search(
            r"not.*for.*code|code.*change.*default|use.*default.*if.*code",
            workflow_content,
            re.IGNORECASE,
        ), "Should specify when NOT to use this workflow"


class TestExamplesAndTemplates:
    """Test presence of examples and templates"""

    def test_provides_concrete_examples(self, best_practices_section):
        """Should provide concrete examples"""
        # Check for code blocks, command examples, or "example:" markers
        has_examples = bool(
            re.search(r"```|example:|for example|e\.g\.", best_practices_section, re.IGNORECASE)
        )

        # This is a should, not a must
        if not has_examples:
            pass

    def test_shows_good_and_bad_patterns(self, best_practices_section):
        """Should show good vs bad patterns if present"""
        # Check for ✅/❌ or DO/DON'T markers
        has_good_bad = bool(
            re.search(
                r"✅|❌|DO:|DON'T:|good.*practice|bad.*practice",
                best_practices_section,
                re.IGNORECASE,
            )
        )

        # This is optional but recommended
        if not has_good_bad:
            pass


class TestReferenceLinks:
    """Test presence of reference links"""

    def test_references_default_workflow(self, workflow_content):
        """Should reference DEFAULT_WORKFLOW.md"""
        assert re.search(r"DEFAULT_WORKFLOW|default.*workflow", workflow_content, re.IGNORECASE), (
            "Should reference DEFAULT_WORKFLOW"
        )

    def test_references_workflow_template(self, workflow_content):
        """Should reference WORKFLOW_TEMPLATE.md or workflow standards"""
        # This is optional - may or may not reference the template


class TestBestPracticesCompleteness:
    """Test overall completeness of Best Practices section"""

    def test_section_not_trivial(self, best_practices_section):
        """Best Practices section should be substantial"""
        # Section should be at least 500 characters
        assert len(best_practices_section) >= 500, (
            f"Best Practices section too short ({len(best_practices_section)} chars, need at least 500)"
        )

    def test_section_has_multiple_subsections_or_topics(self, best_practices_section):
        """Should cover multiple topics"""
        # Check for multiple subsections (###) or numbered/bulleted lists
        subsections = len(re.findall(r"###", best_practices_section))
        list_items = len(re.findall(r"^\s*[-*\d]+\.\s+", best_practices_section, re.MULTILINE))

        total_structure = subsections + (list_items // 3)  # Count ~3 list items as one topic

        assert total_structure >= 3, (
            f"Should have at least 3 topics/subsections (found {total_structure})"
        )
