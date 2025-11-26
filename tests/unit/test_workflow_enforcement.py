"""
Unit tests for workflow enforcement system.

Tests verify:
- Q&A_WORKFLOW.md exists and has required structure
- CLAUDE.md has mandatory workflow classification section
- Deprecated files have proper deprecation notices

Following test pyramid: 60% unit tests for comprehensive coverage.
"""

from pathlib import Path

# Project root for tests
PROJECT_ROOT = Path(__file__).parent.parent.parent


# =============================================================================
# Q&A Workflow Tests
# =============================================================================


def test_workflow_001_qa_workflow_exists():
    """WORKFLOW-001: Q&A_WORKFLOW.md must exist."""
    qa_workflow_path = PROJECT_ROOT / ".claude" / "workflow" / "Q&A_WORKFLOW.md"
    assert qa_workflow_path.exists(), f"Q&A_WORKFLOW.md not found at {qa_workflow_path}"


def test_workflow_002_qa_workflow_has_frontmatter():
    """WORKFLOW-002: Q&A_WORKFLOW.md must have proper frontmatter."""
    qa_workflow_path = PROJECT_ROOT / ".claude" / "workflow" / "Q&A_WORKFLOW.md"
    content = qa_workflow_path.read_text()

    # Must have YAML frontmatter
    assert content.startswith("---"), "Q&A_WORKFLOW.md must start with YAML frontmatter"
    assert "name: Q&A_WORKFLOW" in content, "Frontmatter must include name: Q&A_WORKFLOW"
    assert "steps: 3" in content, "Q&A_WORKFLOW must have exactly 3 steps"


def test_workflow_003_qa_workflow_has_required_sections():
    """WORKFLOW-003: Q&A_WORKFLOW.md must have Step 1, 2, 3."""
    qa_workflow_path = PROJECT_ROOT / ".claude" / "workflow" / "Q&A_WORKFLOW.md"
    content = qa_workflow_path.read_text()

    assert "Step 1" in content, "Must have Step 1"
    assert "Step 2" in content, "Must have Step 2"
    assert "Step 3" in content, "Must have Step 3"


def test_workflow_004_qa_workflow_has_escalation():
    """WORKFLOW-004: Q&A_WORKFLOW.md must document escalation paths."""
    qa_workflow_path = PROJECT_ROOT / ".claude" / "workflow" / "Q&A_WORKFLOW.md"
    content = qa_workflow_path.read_text()

    assert "escalat" in content.lower(), "Must document escalation to other workflows"


# =============================================================================
# CLAUDE.md Workflow Classification Tests
# =============================================================================


def test_workflow_005_claude_md_has_classification_section():
    """WORKFLOW-005: CLAUDE.md must have MANDATORY workflow classification section."""
    claude_md_path = PROJECT_ROOT / "CLAUDE.md"
    content = claude_md_path.read_text()

    # Check for the mandatory classification section
    assert "Workflow Classification" in content or "WORKFLOW SELECTION" in content.upper(), (
        "CLAUDE.md must have workflow classification section"
    )


def test_workflow_006_claude_md_mentions_three_workflows():
    """WORKFLOW-006: CLAUDE.md must reference all three workflow types."""
    claude_md_path = PROJECT_ROOT / "CLAUDE.md"
    content = claude_md_path.read_text()

    assert "Q&A" in content or "Q&A_WORKFLOW" in content, "Must mention Q&A workflow"
    assert "INVESTIGATION" in content or "INVESTIGATION_WORKFLOW" in content, (
        "Must mention INVESTIGATION workflow"
    )
    assert "DEFAULT_WORKFLOW" in content or "DEFAULT" in content, "Must mention DEFAULT workflow"


def test_workflow_007_claude_md_classification_keywords():
    """WORKFLOW-007: CLAUDE.md must list classification keywords."""
    claude_md_path = PROJECT_ROOT / "CLAUDE.md"
    content = claude_md_path.read_text()

    # Must mention common keywords for classification
    keywords_found = any(
        kw in content.lower() for kw in ["implement", "investigate", "what is", "add", "fix"]
    )
    assert keywords_found, "CLAUDE.md must list classification keywords"


# =============================================================================
# Deprecation Tests
# =============================================================================


def test_workflow_008_ultrathink_command_deprecated():
    """WORKFLOW-008: ultrathink.md command should be deprecated."""
    ultrathink_path = PROJECT_ROOT / ".claude" / "commands" / "amplihack" / "ultrathink.md"

    if ultrathink_path.exists():
        content = ultrathink_path.read_text()
        # Should have deprecation notice OR be removed entirely
        assert "DEPRECATED" in content.upper() or "deprecated" in content.lower(), (
            "ultrathink.md should be marked as deprecated"
        )


def test_workflow_009_ultrathink_orchestrator_deprecated():
    """WORKFLOW-009: ultrathink-orchestrator skill should be deprecated."""
    skill_path = PROJECT_ROOT / ".claude" / "skills" / "ultrathink-orchestrator" / "SKILL.md"

    if skill_path.exists():
        content = skill_path.read_text()
        # Should have deprecation notice OR be removed entirely
        assert "DEPRECATED" in content.upper() or "deprecated" in content.lower(), (
            "ultrathink-orchestrator should be marked as deprecated"
        )


def test_workflow_010_default_workflow_skill_deprecated():
    """WORKFLOW-010: default-workflow skill should be deprecated."""
    skill_path = PROJECT_ROOT / ".claude" / "skills" / "default-workflow" / "SKILL.md"

    if skill_path.exists():
        content = skill_path.read_text()
        # Should have deprecation notice OR be removed entirely
        assert "DEPRECATED" in content.upper() or "deprecated" in content.lower(), (
            "default-workflow skill should be marked as deprecated"
        )


# =============================================================================
# Workflow File Existence Tests
# =============================================================================


def test_workflow_011_default_workflow_exists():
    """WORKFLOW-011: DEFAULT_WORKFLOW.md must exist."""
    workflow_path = PROJECT_ROOT / ".claude" / "workflow" / "DEFAULT_WORKFLOW.md"
    assert workflow_path.exists(), "DEFAULT_WORKFLOW.md must exist"


def test_workflow_012_investigation_workflow_exists():
    """WORKFLOW-012: INVESTIGATION_WORKFLOW.md must exist."""
    workflow_path = PROJECT_ROOT / ".claude" / "workflow" / "INVESTIGATION_WORKFLOW.md"
    assert workflow_path.exists(), "INVESTIGATION_WORKFLOW.md must exist"


# =============================================================================
# Integration Sanity Tests
# =============================================================================


def test_workflow_013_no_skill_invocation_required():
    """WORKFLOW-013: CLAUDE.md should not require Skill() invocation for workflow selection."""
    claude_md_path = PROJECT_ROOT / "CLAUDE.md"
    content = claude_md_path.read_text()

    # Classification should work directly, not require skill invocation
    # This test validates that we've eliminated the indirection
    classification_section = content.lower()

    # We don't want mandatory Skill() calls for basic workflow selection
    # If Skill() is mentioned, it should be optional/deprecated
    if 'skill(skill="default-workflow")' in classification_section:
        assert "optional" in classification_section or "deprecated" in classification_section, (
            "Skill invocation for workflow should be optional/deprecated"
        )
