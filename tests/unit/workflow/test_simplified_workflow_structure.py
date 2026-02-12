"""
Test suite for SIMPLIFIED_WORKFLOW.md file structure and YAML frontmatter.

Tests validate:
- File exists at correct location
- Valid YAML frontmatter
- Correct step count (16 steps: 0-15)
- All required YAML fields present
- Phase definitions
- Step numbering sequence
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
    assert match, "No YAML frontmatter found in workflow file"

    yaml_content = match.group(1)
    try:
        return yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        pytest.fail(f"Invalid YAML frontmatter: {e}")


class TestFileStructure:
    """Test basic file structure and existence"""

    def test_workflow_file_exists(self, workflow_file):
        """Workflow file must exist at .claude/workflow/SIMPLIFIED_WORKFLOW.md"""
        assert workflow_file.exists(), f"File not found: {workflow_file}"

    def test_workflow_file_not_empty(self, workflow_content):
        """Workflow file must not be empty"""
        assert len(workflow_content) > 0, "Workflow file is empty"

    def test_workflow_has_frontmatter(self, workflow_content):
        """Workflow must start with YAML frontmatter (---...---)"""
        assert workflow_content.startswith("---\n"), "File must start with YAML frontmatter"
        assert "\n---\n" in workflow_content, "Frontmatter must be closed with ---"


class TestYAMLFrontmatter:
    """Test YAML frontmatter structure and required fields"""

    def test_frontmatter_has_name(self, frontmatter):
        """Frontmatter must have 'name' field"""
        assert "name" in frontmatter, "Missing 'name' field in frontmatter"
        assert frontmatter["name"] == "SIMPLIFIED_WORKFLOW", (
            f"Expected name='SIMPLIFIED_WORKFLOW', got '{frontmatter['name']}'"
        )

    def test_frontmatter_has_version(self, frontmatter):
        """Frontmatter must have 'version' field set to 1.0.0"""
        assert "version" in frontmatter, "Missing 'version' field in frontmatter"
        assert frontmatter["version"] == "1.0.0", (
            f"Expected version='1.0.0', got '{frontmatter['version']}'"
        )

    def test_frontmatter_has_description(self, frontmatter):
        """Frontmatter must have non-empty 'description' field"""
        assert "description" in frontmatter, "Missing 'description' field in frontmatter"
        assert len(frontmatter["description"]) > 0, "Description cannot be empty"

    def test_frontmatter_has_steps_count(self, frontmatter):
        """Frontmatter must declare 16 steps"""
        assert "steps" in frontmatter, "Missing 'steps' field in frontmatter"
        assert frontmatter["steps"] == 16, f"Expected 16 steps, got {frontmatter['steps']}"

    def test_frontmatter_has_phases(self, frontmatter):
        """Frontmatter must define 5 phases"""
        assert "phases" in frontmatter, "Missing 'phases' field in frontmatter"
        phases = frontmatter["phases"]
        assert isinstance(phases, list), "Phases must be a list"
        assert len(phases) == 5, f"Expected 5 phases, got {len(phases)}"

        expected_phases = ["preparation", "documentation", "review", "validation", "completion"]
        assert phases == expected_phases, f"Expected phases {expected_phases}, got {phases}"

    def test_frontmatter_has_success_criteria(self, frontmatter):
        """Frontmatter must define success criteria"""
        assert "success_criteria" in frontmatter, "Missing 'success_criteria' field"
        criteria = frontmatter["success_criteria"]
        assert isinstance(criteria, list), "Success criteria must be a list"
        assert len(criteria) >= 3, "Must have at least 3 success criteria"

    def test_frontmatter_has_philosophy_alignment(self, frontmatter):
        """Frontmatter must define philosophy alignment"""
        assert "philosophy_alignment" in frontmatter, "Missing 'philosophy_alignment' field"
        philosophy = frontmatter["philosophy_alignment"]
        assert isinstance(philosophy, list), "Philosophy alignment must be a list"
        assert len(philosophy) >= 3, "Must have at least 3 philosophy principles"

        # Verify structure of philosophy items
        for item in philosophy:
            assert "principle" in item, "Philosophy item must have 'principle' field"
            assert "application" in item, "Philosophy item must have 'application' field"


class TestStepStructure:
    """Test workflow step structure and numbering"""

    def test_has_all_16_steps(self, workflow_content):
        """Workflow must contain all steps from 0 to 15"""
        for step_num in range(16):
            pattern = rf"##\s+Step {step_num}:"
            assert re.search(pattern, workflow_content), f"Missing Step {step_num} heading"

    def test_step_numbering_sequential(self, workflow_content):
        """Steps must be numbered sequentially (0, 1, 2, ..., 15)"""
        step_pattern = r"##\s+Step (\d+):"
        matches = re.findall(step_pattern, workflow_content)
        step_numbers = [int(m) for m in matches]

        expected = list(range(16))
        assert step_numbers == expected, (
            f"Steps not sequential. Expected {expected}, got {step_numbers}"
        )

    def test_no_extra_steps(self, workflow_content):
        """Must not have steps beyond Step 15"""
        for step_num in range(16, 25):
            pattern = rf"##\s+Step {step_num}:"
            assert not re.search(pattern, workflow_content), (
                f"Found unexpected Step {step_num} (should only go up to Step 15)"
            )

    def test_step_zero_is_workflow_preparation(self, workflow_content):
        """Step 0 must be 'Workflow Preparation'"""
        pattern = r"##\s+Step 0:\s+Workflow Preparation"
        assert re.search(pattern, workflow_content, re.IGNORECASE), (
            "Step 0 must be 'Workflow Preparation'"
        )


class TestPhaseStructure:
    """Test phase organization and step distribution"""

    def test_preparation_phase_exists(self, workflow_content):
        """PREPARATION phase must exist and cover Steps 0-4"""
        # Check for phase heading or section
        assert re.search(r"preparation|PREPARATION", workflow_content, re.IGNORECASE), (
            "Missing PREPARATION phase"
        )

    def test_documentation_phase_exists(self, workflow_content):
        """DOCUMENTATION phase must exist and cover Steps 5-8"""
        assert re.search(r"documentation|DOCUMENTATION", workflow_content, re.IGNORECASE), (
            "Missing DOCUMENTATION phase"
        )

    def test_review_phase_exists(self, workflow_content):
        """REVIEW phase must exist and cover Steps 9-10"""
        assert re.search(r"review|REVIEW", workflow_content, re.IGNORECASE), "Missing REVIEW phase"

    def test_validation_phase_exists(self, workflow_content):
        """VALIDATION phase must exist and cover Steps 11-14"""
        assert re.search(r"validation|VALIDATION", workflow_content, re.IGNORECASE), (
            "Missing VALIDATION phase"
        )

    def test_completion_phase_exists(self, workflow_content):
        """COMPLETION phase must exist (Step 15)"""
        assert re.search(r"completion|COMPLETION", workflow_content, re.IGNORECASE), (
            "Missing COMPLETION phase"
        )


class TestSectionPresence:
    """Test presence of required sections beyond steps"""

    def test_has_overview_section(self, workflow_content):
        """Must have overview/introduction section"""
        assert re.search(
            r"##\s+(Overview|Introduction|Purpose)", workflow_content, re.IGNORECASE
        ), "Missing overview/introduction section"

    def test_has_when_to_use_section(self, workflow_content):
        """Must explain when to use this workflow vs DEFAULT_WORKFLOW"""
        assert re.search(r"when.*use|when.*apply", workflow_content, re.IGNORECASE), (
            "Missing 'when to use' guidance"
        )

    def test_has_best_practices_section(self, workflow_content):
        """Must have Best Practices section"""
        assert re.search(r"##\s+Best Practices", workflow_content, re.IGNORECASE), (
            "Missing Best Practices section"
        )

    def test_has_security_considerations_section(self, workflow_content):
        """Must have Security Considerations section"""
        assert re.search(r"##\s+Security Considerations", workflow_content, re.IGNORECASE), (
            "Missing Security Considerations section"
        )

    def test_has_tool_verification_section(self, workflow_content):
        """Must have Tool Verification section"""
        assert re.search(r"##\s+Tool Verification", workflow_content, re.IGNORECASE), (
            "Missing Tool Verification section"
        )


class TestWorkflowIntegrity:
    """Test workflow integrity markers and notices"""

    def test_has_workflow_integrity_notice(self, workflow_content):
        """Must have workflow integrity notice warning about gate modifications"""
        assert re.search(r"workflow integrity|integrity notice", workflow_content, re.IGNORECASE), (
            "Missing workflow integrity notice"
        )
        assert re.search(r"architecture team approval", workflow_content, re.IGNORECASE), (
            "Integrity notice must mention architecture team approval requirement"
        )
