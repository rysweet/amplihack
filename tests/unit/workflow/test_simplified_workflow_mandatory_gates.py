"""
Test suite for mandatory quality gates in SIMPLIFIED_WORKFLOW.md.

Tests validate:
- Step 0: Workflow Preparation (prevents step skipping)
- Step 10: Review Pass Before Commit (MANDATORY marker)
- Step 12: Test Documentation Accuracy (VERIFICATION GATE)
- Step 13: Review the PR + Implement Feedback (MANDATORY marker)
- Step 14: Reader Perspective Testing (VERIFICATION GATE)
- Step 15: Final Verification and Merge (philosophy check, cleanup)
- "CANNOT PROCEED WITHOUT" language in verification gates
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
    # Find step heading and extract until next step or end
    pattern = rf"##\s+Step {step_num}:.*?(?=##\s+Step \d+:|##\s+[^S]|\Z)"
    match = re.search(pattern, workflow_content, re.DOTALL)
    assert match, f"Could not extract Step {step_num} content"
    return match.group(0)


class TestStep0WorkflowPreparation:
    """Test Step 0: Workflow Preparation - prevents step skipping"""

    def test_step0_exists(self, workflow_content):
        """Step 0 must exist"""
        assert re.search(r"##\s+Step 0:", workflow_content), "Missing Step 0"

    def test_step0_is_workflow_preparation(self, workflow_content):
        """Step 0 must be titled 'Workflow Preparation'"""
        step0 = extract_step_content(workflow_content, 0)
        assert re.search(r"Workflow Preparation", step0, re.IGNORECASE), (
            "Step 0 must be 'Workflow Preparation'"
        )

    def test_step0_creates_all_16_todos(self, workflow_content):
        """Step 0 must create all 16 todos (Steps 0-15)"""
        step0 = extract_step_content(workflow_content, 0)

        # Check for todo creation instruction
        assert re.search(r"todo.*create|create.*todo", step0, re.IGNORECASE), (
            "Step 0 must instruct creating todos"
        )

        # Check that it mentions creating 16 steps or Steps 0-15
        assert re.search(
            r"16\s+steps|steps?\s+0.*15|step\s+0\s+through\s+step\s+15", step0, re.IGNORECASE
        ), "Step 0 must mention creating all 16 steps (0-15)"

    def test_step0_prevents_step_skipping(self, workflow_content):
        """Step 0 must explain why it exists (prevents step skipping)"""
        step0 = extract_step_content(workflow_content, 0)

        # Check for rationale about step skipping or workflow discipline
        assert re.search(r"skip|discipline|temptation|accountability", step0, re.IGNORECASE), (
            "Step 0 must explain rationale (prevents step skipping)"
        )


class TestStep10ReviewBeforeCommit:
    """Test Step 10: Review Pass Before Commit - MANDATORY gate"""

    def test_step10_has_mandatory_marker(self, workflow_content):
        """Step 10 must be marked as MANDATORY"""
        step10 = extract_step_content(workflow_content, 10)

        # Check for MANDATORY marker (emoji + text or just text)
        assert re.search(r"⚠️\s*MANDATORY|MANDATORY", step10, re.IGNORECASE), (
            "Step 10 must be marked as MANDATORY"
        )

    def test_step10_includes_pr_cleanliness_check(self, workflow_content):
        """Step 10 must include PR cleanliness check"""
        step10 = extract_step_content(workflow_content, 10)

        assert re.search(r"PR cleanliness|temporary.*artifact|git status", step10, re.IGNORECASE), (
            "Step 10 must include PR cleanliness check"
        )

    def test_step10_detects_temporary_artifacts(self, workflow_content):
        """Step 10 must list patterns for temporary documentation artifacts"""
        step10 = extract_step_content(workflow_content, 10)

        # Check for common temporary file patterns
        patterns_to_check = [
            r"ANALYSIS_.*\.md",
            r"INVESTIGATION_.*\.md",
            r"NOTES_.*\.md",
            r"scratch_.*\.md",
            r"DRAFT_.*\.md",
            r"TODO_.*\.md",
        ]

        found_patterns = sum(1 for pattern in patterns_to_check if re.search(pattern, step10))
        assert found_patterns >= 3, (
            f"Step 10 must list at least 3 temporary artifact patterns (found {found_patterns})"
        )

    def test_step10_specifies_artifact_handling(self, workflow_content):
        """Step 10 must specify how to handle temporary artifacts"""
        step10 = extract_step_content(workflow_content, 10)

        # Must mention moving to logs or deleting
        assert re.search(r"move.*\.amplihack.*logs|delete|remove|archive", step10, re.IGNORECASE), (
            "Step 10 must specify artifact handling (move to logs or delete)"
        )


class TestStep12DocumentationAccuracy:
    """Test Step 12: Test Documentation Accuracy - VERIFICATION GATE"""

    def test_step12_has_verification_gate_marker(self, workflow_content):
        """Step 12 must be marked as VERIFICATION GATE"""
        step12 = extract_step_content(workflow_content, 12)

        assert re.search(r"🚨\s*VERIFICATION GATE|VERIFICATION GATE", step12, re.IGNORECASE), (
            "Step 12 must be marked as VERIFICATION GATE"
        )

    def test_step12_has_cannot_proceed_language(self, workflow_content):
        """Step 12 must use 'CANNOT PROCEED WITHOUT' language"""
        step12 = extract_step_content(workflow_content, 12)

        assert re.search(
            r"CANNOT PROCEED WITHOUT|cannot proceed|must not proceed", step12, re.IGNORECASE
        ), "Step 12 must use 'CANNOT PROCEED WITHOUT' language"

    def test_step12_requires_accuracy_validation(self, workflow_content):
        """Step 12 must require documentation accuracy validation"""
        step12 = extract_step_content(workflow_content, 12)

        # Check for accuracy testing requirements
        assert re.search(
            r"accuracy|correct|verify.*guidance|test.*instructions", step12, re.IGNORECASE
        ), "Step 12 must require accuracy validation"

    def test_step12_requires_example_verification(self, workflow_content):
        """Step 12 must require verification that examples produce correct results"""
        step12 = extract_step_content(workflow_content, 12)

        assert re.search(
            r"example.*work|example.*correct|verify.*example", step12, re.IGNORECASE
        ), "Step 12 must require example verification"


class TestStep13PRReview:
    """Test Step 13: Review the PR + Implement Feedback - MANDATORY gate"""

    def test_step13_has_mandatory_marker(self, workflow_content):
        """Step 13 must be marked as MANDATORY"""
        step13 = extract_step_content(workflow_content, 13)

        assert re.search(r"⚠️\s*MANDATORY|MANDATORY", step13, re.IGNORECASE), (
            "Step 13 must be marked as MANDATORY"
        )

    def test_step13_requires_pr_review(self, workflow_content):
        """Step 13 must require PR review"""
        step13 = extract_step_content(workflow_content, 13)

        assert re.search(r"review.*PR|PR.*review|pull request.*review", step13, re.IGNORECASE), (
            "Step 13 must require PR review"
        )

    def test_step13_requires_feedback_implementation(self, workflow_content):
        """Step 13 must require implementing reviewer feedback"""
        step13 = extract_step_content(workflow_content, 13)

        assert re.search(
            r"implement.*feedback|address.*comment|respond.*review", step13, re.IGNORECASE
        ), "Step 13 must require implementing feedback"

    def test_step13_prevents_self_merge(self, workflow_content):
        """Step 13 must prevent or discourage self-merging"""
        step13 = extract_step_content(workflow_content, 13)

        # Check for guidance about requiring approval or not self-merging
        assert re.search(
            r"approval|reviewer|do not.*merge|wait for.*review", step13, re.IGNORECASE
        ), "Step 13 must address PR approval requirements"


class TestStep14ReaderPerspective:
    """Test Step 14: Reader Perspective Testing - VERIFICATION GATE"""

    def test_step14_has_verification_gate_marker(self, workflow_content):
        """Step 14 must be marked as VERIFICATION GATE"""
        step14 = extract_step_content(workflow_content, 14)

        assert re.search(r"🚨\s*VERIFICATION GATE|VERIFICATION GATE", step14, re.IGNORECASE), (
            "Step 14 must be marked as VERIFICATION GATE"
        )

    def test_step14_has_cannot_proceed_language(self, workflow_content):
        """Step 14 must use 'CANNOT PROCEED WITHOUT' language"""
        step14 = extract_step_content(workflow_content, 14)

        assert re.search(
            r"CANNOT PROCEED WITHOUT|cannot proceed|must not proceed", step14, re.IGNORECASE
        ), "Step 14 must use 'CANNOT PROCEED WITHOUT' language"

    def test_step14_requires_fresh_perspective(self, workflow_content):
        """Step 14 must require testing from fresh/reader perspective"""
        step14 = extract_step_content(workflow_content, 14)

        # Check for reader perspective, new user, fresh eyes concepts
        assert re.search(
            r"reader.*perspective|fresh.*perspective|new user|unfamiliar", step14, re.IGNORECASE
        ), "Step 14 must require reader perspective testing"

    def test_step14_validates_clarity(self, workflow_content):
        """Step 14 must validate documentation clarity"""
        step14 = extract_step_content(workflow_content, 14)

        assert re.search(r"clear|understandable|comprehensible|readable", step14, re.IGNORECASE), (
            "Step 14 must validate clarity"
        )

    def test_step14_validates_completeness(self, workflow_content):
        """Step 14 must validate documentation completeness"""
        step14 = extract_step_content(workflow_content, 14)

        assert re.search(
            r"complete|missing.*information|gap|prerequisite", step14, re.IGNORECASE
        ), "Step 14 must validate completeness"


class TestStep15FinalVerification:
    """Test Step 15: Final Verification and Merge - combines multiple checks"""

    def test_step15_includes_philosophy_check(self, workflow_content):
        """Step 15 must include philosophy compliance check"""
        step15 = extract_step_content(workflow_content, 15)

        assert re.search(r"philosophy|principle|ruthless simplicity", step15, re.IGNORECASE), (
            "Step 15 must include philosophy check"
        )

    def test_step15_includes_cleanup_verification(self, workflow_content):
        """Step 15 must verify cleanup was performed"""
        step15 = extract_step_content(workflow_content, 15)

        assert re.search(
            r"cleanup|temporary.*artifact|git status|clean.*working", step15, re.IGNORECASE
        ), "Step 15 must verify cleanup"

    def test_step15_checks_mergeable_status(self, workflow_content):
        """Step 15 must verify PR is mergeable"""
        step15 = extract_step_content(workflow_content, 15)

        assert re.search(
            r"mergeable|merge.*conflict|CI.*pass|check.*pass", step15, re.IGNORECASE
        ), "Step 15 must check mergeable status"

    def test_step15_includes_merge_command(self, workflow_content):
        """Step 15 must include merge command examples"""
        step15 = extract_step_content(workflow_content, 15)

        # Check for gh pr merge or az repos pr update commands
        assert re.search(r"gh pr merge|az repos pr update.*completed", step15), (
            "Step 15 must include merge command examples"
        )


class TestMandatoryGateConsistency:
    """Test consistency of mandatory gate markers across workflow"""

    def test_all_mandatory_gates_marked(self, workflow_content):
        """All mandatory gates must be clearly marked"""
        # Steps 10, 13 should have MANDATORY markers
        # Steps 12, 14 should have VERIFICATION GATE markers

        mandatory_steps = [10, 13]
        verification_steps = [12, 14]

        for step_num in mandatory_steps:
            step_content = extract_step_content(workflow_content, step_num)
            assert re.search(r"⚠️\s*MANDATORY|MANDATORY", step_content, re.IGNORECASE), (
                f"Step {step_num} must be marked as MANDATORY"
            )

        for step_num in verification_steps:
            step_content = extract_step_content(workflow_content, step_num)
            assert re.search(
                r"🚨\s*VERIFICATION GATE|VERIFICATION GATE", step_content, re.IGNORECASE
            ), f"Step {step_num} must be marked as VERIFICATION GATE"

    def test_verification_gates_use_strong_language(self, workflow_content):
        """Verification gates must use strong 'cannot proceed' language"""
        verification_steps = [12, 14]

        for step_num in verification_steps:
            step_content = extract_step_content(workflow_content, step_num)
            assert re.search(
                r"CANNOT PROCEED|cannot proceed|must not proceed|blocking",
                step_content,
                re.IGNORECASE,
            ), f"Step {step_num} (VERIFICATION GATE) must use strong blocking language"

    def test_no_unauthorized_gate_weakening(self, workflow_content):
        """Workflow must not contain language that weakens gates"""
        # Check for phrases that suggest gates are optional
        weakening_phrases = [
            r"optional.*gate",
            r"skip.*if.*simple",
            r"may.*skip",
            r"not required.*for",
            r"can skip",
        ]

        for phrase in weakening_phrases:
            matches = re.findall(phrase, workflow_content, re.IGNORECASE)
            assert len(matches) == 0, (
                f"Workflow contains gate-weakening language: '{phrase}' (matches: {matches})"
            )
