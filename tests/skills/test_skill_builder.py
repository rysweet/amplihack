"""Validation tests for skill-builder enhancements following TDD methodology.

Tests validate that skill-builder now includes:
- Validation checklist for skill quality
- Simplified workflow (< 15 lines)
- Complete examples (agent + scenario)
- No stubs or incomplete implementations

Philosophy:
- Validates documentation quality, not code behavior
- Ensures best practices are documented and enforced
- Checks for completeness and usability
"""

import re
from pathlib import Path

import pytest
import tiktoken

# Path constants
AMPLIHACK_ROOT = Path("/home/azureuser/src/amplihack")
SKILL_DIR = AMPLIHACK_ROOT / ".claude" / "skills" / "skill-builder"
SKILL_FILE = SKILL_DIR / "SKILL.md"
REFERENCE_FILE = SKILL_DIR / "reference.md"
EXAMPLES_FILE = SKILL_DIR / "examples.md"

# Expected files
REQUIRED_FILES = [
    "SKILL.md",
    "reference.md",
    "examples.md",
]

# Quality thresholds
MAX_SKILL_TOKENS = 5000  # skill-builder is more complex
MAX_SKILL_LINES = 500
MAX_WORKFLOW_LINES = 15  # Simplified workflow requirement


def count_tokens(text: str) -> int:
    """Count tokens using tiktoken for claude-sonnet-4-5."""
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))


def count_lines(text: str) -> int:
    """Count non-empty lines in text."""
    return len([line for line in text.split("\n") if line.strip()])


def extract_yaml_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter from markdown file."""
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}

    yaml_text = match.group(1)
    result = {}

    current_key = None
    for line in yaml_text.split("\n"):
        line = line.strip()
        if not line:
            continue

        if line.startswith("- "):
            if current_key and isinstance(result.get(current_key), list):
                result[current_key].append(line[2:].strip())
        elif ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()

            if not value:
                result[key] = []
                current_key = key
            else:
                result[key] = value
                current_key = None

    return result


class TestFileStructure:
    """Test that all required files exist in correct location."""

    def test_skill_directory_exists(self):
        """Test that skill-builder skill directory exists."""
        assert SKILL_DIR.exists(), f"Skill directory does not exist: {SKILL_DIR}"
        assert SKILL_DIR.is_dir(), f"Skill path is not a directory: {SKILL_DIR}"

    def test_all_required_files_exist(self):
        """Test that all required skill files exist."""
        missing_files = []
        for filename in REQUIRED_FILES:
            file_path = SKILL_DIR / filename
            if not file_path.exists():
                missing_files.append(filename)

        assert not missing_files, (
            f"Missing required files in {SKILL_DIR}: {', '.join(missing_files)}"
        )


class TestYAMLFrontmatter:
    """Test YAML frontmatter structure and required fields."""

    @pytest.fixture
    def skill_content(self):
        """Load SKILL.md content."""
        return SKILL_FILE.read_text()

    @pytest.fixture
    def frontmatter(self, skill_content):
        """Extract and return YAML frontmatter."""
        return extract_yaml_frontmatter(skill_content)

    def test_has_yaml_frontmatter(self, skill_content):
        """Test that SKILL.md has YAML frontmatter."""
        assert skill_content.startswith("---\n"), "SKILL.md must start with YAML frontmatter (---)"

    def test_frontmatter_has_name(self, frontmatter):
        """Test that frontmatter includes 'name' field."""
        assert "name" in frontmatter, "YAML frontmatter missing 'name' field"
        assert frontmatter["name"] == "skill-builder", (
            f"Expected name='skill-builder', got '{frontmatter['name']}'"
        )

    def test_frontmatter_has_version(self, frontmatter):
        """Test that frontmatter includes 'version' field."""
        assert "version" in frontmatter, "YAML frontmatter missing 'version' field"
        version_pattern = r"^\d+\.\d+\.\d+$"
        assert re.match(version_pattern, frontmatter["version"]), (
            f"Version must be semantic (X.Y.Z), got '{frontmatter['version']}'"
        )

    def test_frontmatter_has_description(self, frontmatter):
        """Test that frontmatter includes 'description' field."""
        assert "description" in frontmatter, "YAML frontmatter missing 'description' field"
        desc = frontmatter["description"]
        assert len(desc) > 20, f"Description too short ({len(desc)} chars), should be >20 chars"


class TestTokenBudget:
    """Test that SKILL.md stays within token budget."""

    @pytest.fixture
    def skill_content(self):
        """Load SKILL.md content."""
        return SKILL_FILE.read_text()

    def test_token_count_within_budget(self, skill_content):
        """Test that SKILL.md token count is within budget."""
        token_count = count_tokens(skill_content)
        assert token_count <= MAX_SKILL_TOKENS, (
            f"SKILL.md exceeds token budget: {token_count} tokens (max: {MAX_SKILL_TOKENS})"
        )

    def test_line_count_within_budget(self, skill_content):
        """Test that SKILL.md line count is within budget."""
        line_count = count_lines(skill_content)
        assert line_count <= MAX_SKILL_LINES, (
            f"SKILL.md exceeds line budget: {line_count} lines (max: {MAX_SKILL_LINES})"
        )


class TestValidationChecklist:
    """Test that validation checklist exists and is comprehensive."""

    @pytest.fixture
    def reference_content(self):
        """Load reference.md content."""
        return REFERENCE_FILE.read_text()

    @pytest.fixture
    def skill_content(self):
        """Load SKILL.md content."""
        return SKILL_FILE.read_text()

    def test_validation_checklist_exists(self, skill_content, reference_content):
        """Test that validation checklist is documented."""
        # Check in both SKILL.md and reference.md
        all_content = skill_content + reference_content
        validation_indicators = [
            "validation",
            "checklist",
            "quality",
            "Validate",
        ]
        found = any(indicator in all_content for indicator in validation_indicators)
        assert found, "Should document validation checklist for skill quality"

    def test_validation_covers_yaml_frontmatter(self, reference_content, skill_content):
        """Test that validation checklist covers YAML frontmatter."""
        all_content = skill_content + reference_content
        yaml_checks = [
            "frontmatter",
            "YAML",
            "name:",
            "description:",
        ]
        found = sum(1 for check in yaml_checks if check in all_content)
        assert found >= 2, "Validation should cover YAML frontmatter requirements"

    def test_validation_covers_token_budget(self, reference_content, skill_content):
        """Test that validation mentions token budget."""
        all_content = skill_content + reference_content
        assert "token" in all_content.lower(), (
            "Validation should mention token budget considerations"
        )

    def test_validation_covers_philosophy_compliance(self, reference_content, skill_content):
        """Test that validation mentions philosophy compliance."""
        all_content = skill_content + reference_content
        philosophy_indicators = [
            "philosophy",
            "compliance",
            "simplicity",
            "reviewer",
        ]
        found = any(indicator in all_content.lower() for indicator in philosophy_indicators)
        assert found, "Validation should mention philosophy compliance checks"


class TestSimplifiedWorkflow:
    """Test that workflow is simplified to < 15 lines."""

    @pytest.fixture
    def skill_content(self):
        """Load SKILL.md content."""
        return SKILL_FILE.read_text()

    def test_workflow_exists(self, skill_content):
        """Test that workflow section exists."""
        workflow_indicators = [
            "What I Do",
            "Process",
            "Workflow",
            "Steps",
        ]
        found = any(indicator in skill_content for indicator in workflow_indicators)
        assert found, "SKILL.md should have workflow/process section"

    def test_workflow_is_simplified(self, skill_content):
        """Test that workflow is simplified (numbered list < 15 lines)."""
        # Extract workflow section
        # Look for numbered list pattern
        workflow_pattern = r"(?:What I Do|Process|Workflow|Steps).*?\n\n((?:\d+\..*?\n)+)"
        match = re.search(workflow_pattern, skill_content, re.DOTALL)

        if match:
            workflow_text = match.group(1)
            workflow_lines = [
                line
                for line in workflow_text.split("\n")
                if line.strip() and re.match(r"^\d+\.", line.strip())
            ]
            line_count = len(workflow_lines)
            assert line_count <= MAX_WORKFLOW_LINES, (
                f"Workflow should be simplified to <= {MAX_WORKFLOW_LINES} steps, "
                f"found {line_count}"
            )

    def test_workflow_references_agents(self, skill_content):
        """Test that workflow references specialized agents."""
        # Simplified workflow should delegate to agents
        agent_indicators = [
            "agent",
            "architect",
            "builder",
            "reviewer",
            "tester",
        ]
        found = sum(1 for indicator in agent_indicators if indicator in skill_content.lower())
        assert found >= 3, "Workflow should reference delegation to specialized agents"


class TestCompleteExamples:
    """Test that examples.md has complete implementations."""

    @pytest.fixture
    def examples_content(self):
        """Load examples.md content."""
        return EXAMPLES_FILE.read_text()

    def test_examples_file_substantial(self, examples_content):
        """Test that examples.md is substantial."""
        assert len(examples_content) > 2000, (
            f"examples.md too short ({len(examples_content)} chars), "
            "should contain comprehensive examples"
        )

    def test_has_agent_example(self, examples_content):
        """Test that examples include agent creation."""
        # Should show how to create an agent
        agent_indicators = [
            "agent",
            "Agent",
            ".claude/agents",
            "specialized",
        ]
        found = sum(1 for indicator in agent_indicators if indicator in examples_content)
        assert found >= 2, "examples.md should include agent creation example"

    def test_has_scenario_example(self, examples_content):
        """Test that examples include scenario/tool creation."""
        scenario_indicators = [
            "scenario",
            "Scenario",
            ".claude/scenarios",
            "tool",
        ]
        found = sum(1 for indicator in scenario_indicators if indicator in examples_content)
        assert found >= 2, "examples.md should include scenario creation example"

    def test_examples_have_code_blocks(self, examples_content):
        """Test that examples include code blocks."""
        # Count markdown code blocks
        code_block_count = examples_content.count("```")
        assert code_block_count >= 10, (
            f"examples.md should have multiple code examples "
            f"(found {code_block_count // 2} blocks, expected >= 5)"
        )

    def test_examples_show_frontmatter(self, examples_content):
        """Test that examples show YAML frontmatter format."""
        # Should have examples of frontmatter structure
        frontmatter_indicators = [
            "---",
            "name:",
            "description:",
            "version:",
        ]
        found = sum(1 for indicator in frontmatter_indicators if indicator in examples_content)
        assert found >= 3, "examples.md should show YAML frontmatter examples"


class TestZeroBSCompliance:
    """Test Zero-BS implementation - no stubs in examples."""

    @pytest.fixture
    def examples_content(self):
        """Load examples.md content."""
        return EXAMPLES_FILE.read_text()

    def test_no_stub_implementations(self, examples_content):
        """Test that examples don't contain stub implementations."""
        stub_indicators = [
            "# TODO",
            "# FIXME",
            "# placeholder",
            "# stub",
            "pass  # implementation",
        ]

        for indicator in stub_indicators:
            assert indicator not in examples_content, (
                f"examples.md contains stub code: '{indicator}'"
            )

    def test_no_ellipsis_placeholders(self, examples_content):
        """Test that examples don't use ellipsis as placeholders."""
        # Extract code blocks
        code_blocks = re.findall(
            r"```(?:markdown|yaml|python|bash)\n(.*?)\n```", examples_content, re.DOTALL
        )

        for block in code_blocks:
            # Ellipsis is OK in:
            # 1. Comments explaining more could go here
            # 2. Workflow step descriptions like "[Step-by-step workflow...]"
            # 3. EXECUTION INSTRUCTIONS sections (standard pattern)
            # 4. In string literals or documentation examples
            lines = block.split("\n")
            for line in lines:
                if "..." in line and not line.strip().startswith("#"):
                    # OK: Workflow placeholders in square brackets
                    if "[" in line and "..." in line and "]" in line:
                        continue
                    # OK: EXECUTION INSTRUCTIONS marker
                    if "EXECUTION INSTRUCTIONS" in line or "Core workflow" in line:
                        continue
                    # OK: Documentation references
                    if "Examples in" in line or "See" in line:
                        continue
                    # NOT OK: Code placeholder like "pass..." or "return..."
                    if any(keyword in line for keyword in ["pass", "return", "def ", "class "]):
                        pytest.fail(f"Code example contains ellipsis placeholder:\n{line}")

    def test_examples_are_complete(self, examples_content):
        """Test that example skill files appear complete."""
        # Examples should show complete SKILL.md structure
        complete_indicators = [
            "## Purpose",
            "## When I Activate",
            "## What I Do",
            "## Usage",
        ]

        # At least some examples should show complete structure
        found = sum(1 for indicator in complete_indicators if indicator in examples_content)
        assert found >= 3, (
            f"examples.md should show complete skill structure (found {found}/4 section headers)"
        )


class TestBestPracticesDocumentation:
    """Test that official best practices are documented."""

    @pytest.fixture
    def reference_content(self):
        """Load reference.md content."""
        return REFERENCE_FILE.read_text()

    @pytest.fixture
    def skill_content(self):
        """Load SKILL.md content."""
        return SKILL_FILE.read_text()

    def test_references_official_docs(self, skill_content, reference_content):
        """Test that official documentation sources are referenced."""
        all_content = skill_content + reference_content
        # Should reference official Claude Code docs
        official_indicators = [
            "claude.com",
            "anthropic.com",
            "code.claude.com",
            "Official",
            "official",
        ]
        found = sum(1 for indicator in official_indicators if indicator in all_content)
        assert found >= 2, "Should reference official Claude Code/Anthropic documentation"

    def test_documents_progressive_disclosure(self, reference_content, skill_content):
        """Test that progressive disclosure pattern is documented."""
        all_content = skill_content + reference_content
        disclosure_indicators = [
            "progressive disclosure",
            "supporting files",
            "reference.md",
            "examples.md",
        ]
        all_content_lower = all_content.lower()
        found = sum(
            1 for indicator in disclosure_indicators if indicator.lower() in all_content_lower
        )
        assert found >= 2, "Should document progressive disclosure pattern"

    def test_documents_skill_types(self, skill_content):
        """Test that different skill types are documented."""
        # Should explain different types: skill, agent, command, scenario
        skill_types = ["skill", "agent", "command", "scenario"]
        found = sum(1 for stype in skill_types if stype in skill_content.lower())
        assert found >= 3, (
            f"Should document different skill types "
            f"(found {found}/4: skill, agent, command, scenario)"
        )

    def test_documents_auto_activation(self, skill_content, reference_content):
        """Test that auto-activation mechanism is explained."""
        all_content = skill_content + reference_content
        activation_indicators = [
            "auto_activates",
            "automatically",
            "auto-discovery",
            "When I Activate",
        ]
        found = sum(1 for indicator in activation_indicators if indicator in all_content)
        assert found >= 2, "Should explain auto-activation mechanism"


class TestCommonMistakes:
    """Test that common mistakes are documented."""

    @pytest.fixture
    def reference_content(self):
        """Load reference.md content."""
        return REFERENCE_FILE.read_text()

    @pytest.fixture
    def skill_content(self):
        """Load SKILL.md content."""
        return SKILL_FILE.read_text()

    def test_documents_common_mistakes(self, skill_content, reference_content):
        """Test that common mistakes are documented."""
        all_content = skill_content + reference_content
        mistake_indicators = [
            "Common Mistake",
            "Anti-Pattern",
            "Avoid",
            "Don't",
            "⚠️",
            "❌",
        ]
        found = any(indicator in all_content for indicator in mistake_indicators)
        assert found, "Should document common mistakes or anti-patterns"

    def test_documents_troubleshooting(self, reference_content):
        """Test that troubleshooting guidance is provided."""
        troubleshooting_indicators = [
            "troubleshoot",
            "Troubleshoot",
            "Common Issues",
            "Problems",
            "Error",
        ]
        found = any(indicator in reference_content for indicator in troubleshooting_indicators)
        assert found, "reference.md should include troubleshooting guidance"


class TestAgentOrchestration:
    """Test that agent orchestration is properly documented."""

    @pytest.fixture
    def skill_content(self):
        """Load SKILL.md content."""
        return SKILL_FILE.read_text()

    def test_documents_agent_delegation(self, skill_content):
        """Test that agent delegation strategy is documented."""
        # Should mention specific agents: architect, builder, reviewer, tester
        agents = [
            "architect",
            "builder",
            "reviewer",
            "tester",
            "prompt-writer",
        ]
        found = sum(1 for agent in agents if agent in skill_content.lower())
        assert found >= 4, (
            f"Should document agent delegation strategy (found {found}/5 agents mentioned)"
        )

    def test_workflow_shows_agent_handoffs(self, skill_content):
        """Test that workflow shows which agent handles each step."""
        # Look for mentions of specific agents in workflow context
        # Can be in format: "architect agent", "using architect", etc.
        workflow_section = ""
        lines = skill_content.split("\n")
        in_workflow = False
        for line in lines:
            if "What I Do" in line or "I create" in line or "Process" in line:
                in_workflow = True
            if in_workflow:
                workflow_section += line + "\n"
                # Stop at next major section
                if line.startswith("##") and "What I Do" not in line and "Process" not in line:
                    break

        # Count mentions of specific agent types
        agent_names = [
            "architect",
            "builder",
            "reviewer",
            "tester",
            "prompt-writer",
        ]
        agent_mentions = sum(1 for agent in agent_names if agent in workflow_section.lower())

        assert agent_mentions >= 3, (
            f"Workflow should mention which agents handle each step "
            f"(found {agent_mentions} agent references)"
        )
