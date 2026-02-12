"""
Test suite for github-branch-protection skill structure and content.

TDD Phase: RED - These tests should FAIL initially
- Skill file doesn't exist yet
- Content structure not validated
- Auto-activation not tested

Expected to PASS after:
- Phase 2: Skill Creation complete
- All sections written
- YAML frontmatter correct
"""

from pathlib import Path

import pytest
import yaml


class TestSkillFileStructure:
    """Test the skill file exists and has correct structure."""

    @pytest.fixture
    def skill_path(self) -> Path:
        """Path to the github-branch-protection skill file."""
        return Path("amplifier-bundle/skills/github-branch-protection/SKILL.md")

    def test_skill_file_exists(self, skill_path: Path):
        """Test that the skill file exists at the correct location."""
        assert skill_path.exists(), (
            f"Skill file not found at {skill_path}. "
            "Expected location: amplifier-bundle/skills/github-branch-protection/SKILL.md"
        )

    def test_skill_file_not_empty(self, skill_path: Path):
        """Test that the skill file has content."""
        content = skill_path.read_text()
        assert len(content) > 0, "Skill file exists but is empty"
        assert len(content.splitlines()) >= 350, (
            f"Skill file too short: {len(content.splitlines())} lines. "
            "Expected ~350-450 lines minimum"
        )

    def test_skill_has_yaml_frontmatter(self, skill_path: Path):
        """Test that skill file starts with YAML frontmatter."""
        content = skill_path.read_text()
        assert content.startswith("---\n"), (
            "Skill file must start with YAML frontmatter delimiter '---'"
        )

        # Extract frontmatter
        lines = content.split("\n")
        assert lines[0] == "---", "First line must be '---'"

        # Find closing delimiter
        closing_idx = None
        for idx, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                closing_idx = idx
                break

        assert closing_idx is not None, "YAML frontmatter must have closing '---' delimiter"


class TestSkillYAMLFrontmatter:
    """Test the YAML frontmatter has required fields."""

    @pytest.fixture(scope="class")
    def frontmatter(self) -> dict:
        """Extract and parse YAML frontmatter from skill file."""
        skill_path = Path("amplifier-bundle/skills/github-branch-protection/SKILL.md")
        content = skill_path.read_text()

        # Extract frontmatter between --- delimiters
        lines = content.split("\n")
        frontmatter_lines = []

        for line in lines[1:]:  # Skip first ---
            if line.strip() == "---":
                break
            frontmatter_lines.append(line)

        frontmatter_text = "\n".join(frontmatter_lines)
        return yaml.safe_load(frontmatter_text)

    def test_has_name_field(self, frontmatter: dict):
        """Test frontmatter has 'name' field."""
        assert "name" in frontmatter, "YAML frontmatter must have 'name' field"
        assert frontmatter["name"] == "github-branch-protection", (
            f"Expected name 'github-branch-protection', got '{frontmatter['name']}'"
        )

    def test_has_version_field(self, frontmatter: dict):
        """Test frontmatter has 'version' field."""
        assert "version" in frontmatter, "YAML frontmatter must have 'version' field"

        version = frontmatter["version"]
        # Validate semver format
        parts = str(version).split(".")
        assert len(parts) == 3, f"Version must be semver format (x.y.z), got '{version}'"
        assert all(part.isdigit() for part in parts), (
            f"Version parts must be numeric, got '{version}'"
        )

    def test_has_description_field(self, frontmatter: dict):
        """Test frontmatter has 'description' field."""
        assert "description" in frontmatter, "YAML frontmatter must have 'description' field"
        assert len(frontmatter["description"]) > 20, "Description should be meaningful (>20 chars)"

    def test_has_auto_activate_keywords(self, frontmatter: dict):
        """Test frontmatter has 'auto_activate_keywords' field."""
        assert "auto_activate_keywords" in frontmatter, (
            "YAML frontmatter must have 'auto_activate_keywords' field"
        )

        keywords = frontmatter["auto_activate_keywords"]
        assert isinstance(keywords, list), "auto_activate_keywords must be a list"
        assert len(keywords) >= 3, f"Expected at least 3 keywords, got {len(keywords)}"

        # Check for expected keywords
        expected_keywords = [
            "branch protection",
            "protect branch",
            "github protection",
        ]

        keywords_lower = [k.lower() for k in keywords]
        for expected in expected_keywords:
            assert expected in keywords_lower, (
                f"Expected keyword '{expected}' in auto_activate_keywords"
            )


class TestSkillContentSections:
    """Test that skill file contains all required sections."""

    @pytest.fixture(scope="class")
    def skill_content(self) -> str:
        """Load skill file content."""
        skill_path = Path("amplifier-bundle/skills/github-branch-protection/SKILL.md")
        return skill_path.read_text()

    def test_has_purpose_section(self, skill_content: str):
        """Test skill has Purpose & Auto-Activation section."""
        assert "## Purpose" in skill_content or "# Purpose" in skill_content, (
            "Skill must have Purpose section"
        )
        assert "defense-in-depth" in skill_content.lower(), (
            "Purpose section must explain defense-in-depth positioning"
        )

    def test_has_prerequisites_section(self, skill_content: str):
        """Test skill has Prerequisites section."""
        assert "## Prerequisites" in skill_content or "# Prerequisites" in skill_content, (
            "Skill must have Prerequisites section"
        )
        assert "gh auth status" in skill_content, "Prerequisites must include authentication check"

    def test_has_quick_reference_table(self, skill_content: str):
        """Test skill has Quick Reference table."""
        assert "Quick Reference" in skill_content, "Skill must have Quick Reference section"
        # Check for markdown table
        assert "|" in skill_content and "---" in skill_content, (
            "Quick Reference should contain a markdown table"
        )

    def test_has_gh_cli_method(self, skill_content: str):
        """Test skill has gh CLI method documentation."""
        assert "gh CLI" in skill_content or "Method 1" in skill_content, (
            "Skill must document gh CLI method"
        )
        assert "gh api" in skill_content, "gh CLI method must show gh api commands"

    def test_has_github_ui_method(self, skill_content: str):
        """Test skill has GitHub UI method documentation."""
        assert "GitHub UI" in skill_content or "Method 2" in skill_content, (
            "Skill must document GitHub UI method"
        )
        assert "Settings" in skill_content and "Branches" in skill_content, (
            "GitHub UI method must show navigation steps"
        )

    def test_has_protection_settings_explained(self, skill_content: str):
        """Test skill explains all 5 protection settings."""
        required_settings = [
            "Require pull request",
            "Require reviews",
            "Require status checks",
            "force push",
            "deletion",
        ]

        content_lower = skill_content.lower()
        for setting in required_settings:
            assert setting.lower() in content_lower, (
                f"Skill must explain '{setting}' protection setting"
            )

    def test_has_verification_section(self, skill_content: str):
        """Test skill has verification commands."""
        assert "Verification" in skill_content or "Verify" in skill_content, (
            "Skill must have Verification section"
        )
        assert "gh api" in skill_content, "Verification section must show gh api commands"

    def test_has_working_example(self, skill_content: str):
        """Test skill has working example section."""
        assert "Working Example" in skill_content or "Example" in skill_content, (
            "Skill must have Working Example section"
        )
        assert "amplihack" in skill_content.lower(), (
            "Working Example must reference amplihack repository"
        )

    def test_has_troubleshooting_section(self, skill_content: str):
        """Test skill has troubleshooting section."""
        assert "Troubleshooting" in skill_content, "Skill must have Troubleshooting section"
        assert "403" in skill_content or "permission" in skill_content.lower(), (
            "Troubleshooting must cover permission errors"
        )


class TestSkillCommandValidity:
    """Test that gh CLI commands in skill are syntactically valid."""

    @pytest.fixture(scope="class")
    def skill_content(self) -> str:
        """Load skill file content."""
        skill_path = Path("amplifier-bundle/skills/github-branch-protection/SKILL.md")
        return skill_path.read_text()

    def test_gh_api_commands_have_correct_syntax(self, skill_content: str):
        """Test that gh api commands use correct syntax."""
        # Extract code blocks
        import re

        code_blocks = re.findall(r"```(?:bash|sh)?\n(.*?)```", skill_content, re.DOTALL)

        gh_api_commands = []
        for block in code_blocks:
            lines = block.split("\n")
            gh_api_commands.extend(
                [line.strip() for line in lines if line.strip().startswith("gh api")]
            )

        assert len(gh_api_commands) > 0, "Skill must contain gh api commands in code blocks"

        # Validate command structure for repo-related endpoints only
        for cmd in gh_api_commands:
            # Some gh api commands may target non-repo endpoints (e.g., `gh api user`);
            # this test only enforces structure for repo/branch-protection related calls.
            if "repos/" not in cmd:
                continue

            # Allow prerequisite checks OR protection API commands
            # Prerequisite checks: permissions, branch listing, repo verification
            is_permission_check = cmd.endswith(".permissions") or "| jq '.permissions" in cmd
            is_branch_listing = "/branches" in cmd and "/protection" not in cmd
            is_protection_api = "/protection" in cmd

            assert is_permission_check or is_branch_listing or is_protection_api, (
                f"Command should target branch protection API or be a prerequisite check: {cmd}"
            )

    def test_json_payloads_are_valid(self, skill_content: str):
        """Test that JSON payloads in skill are valid JSON."""
        import json
        import re

        # Find JSON code blocks
        json_blocks = re.findall(r"```json\n(.*?)```", skill_content, re.DOTALL)

        for idx, block in enumerate(json_blocks):
            try:
                parsed = json.loads(block)
                assert isinstance(parsed, dict), f"JSON block {idx} should be a dict/object"
            except json.JSONDecodeError as e:
                pytest.fail(f"JSON block {idx} is invalid: {e}\n{block}")

    def test_required_status_checks_structure(self, skill_content: str):
        """Test that required_status_checks examples have correct structure."""
        import json
        import re

        json_blocks = re.findall(r"```json\n(.*?)```", skill_content, re.DOTALL)

        found_status_checks = False
        for block in json_blocks:
            data = json.loads(block)
            if "required_status_checks" in data:
                found_status_checks = True
                status_checks = data["required_status_checks"]

                # Validate structure
                assert "contexts" in status_checks, (
                    "required_status_checks must have 'contexts' field"
                )
                assert isinstance(status_checks["contexts"], list), "contexts must be a list"
                assert "strict" in status_checks, "required_status_checks must have 'strict' field"
                assert isinstance(status_checks["strict"], bool), "strict must be a boolean"

        assert found_status_checks, "Skill must show required_status_checks configuration example"


class TestSkillPhilosophyAlignment:
    """Test that skill follows amplihack philosophy principles."""

    @pytest.fixture(scope="class")
    def skill_content(self) -> str:
        """Load skill file content."""
        skill_path = Path("amplifier-bundle/skills/github-branch-protection/SKILL.md")
        return skill_path.read_text()

    def test_explains_trade_offs(self, skill_content: str):
        """Test that skill explains trade-offs, not just commands."""
        content_lower = skill_content.lower()

        trade_off_indicators = [
            "trade-off",
            "tradeoff",
            "consider",
            "however",
            "but",
            "caveat",
            "warning",
        ]

        found_count = sum(1 for indicator in trade_off_indicators if indicator in content_lower)
        assert found_count >= 3, (
            f"Skill should explain trade-offs and considerations "
            f"(found {found_count} indicators, expected >= 3)"
        )

    def test_actionable_and_scannable(self, skill_content: str):
        """Test that skill is actionable with scannable structure."""
        # Check for numbered lists or step-by-step structure
        assert "1." in skill_content or "Step 1" in skill_content, (
            "Skill should have numbered steps for actionability"
        )

        # Check for code blocks
        assert "```" in skill_content, "Skill should have code blocks with runnable commands"

        # Check for headings (scannable structure)
        heading_count = skill_content.count("##")
        assert heading_count >= 8, (
            f"Skill should have clear section headings for scannability "
            f"(found {heading_count}, expected >= 8)"
        )

    def test_includes_real_examples(self, skill_content: str):
        """Test that skill includes real examples, not just theory."""
        # Should reference actual repository
        assert "amplihack" in skill_content.lower(), (
            "Skill should include real example from amplihack repository"
        )

        # Should have actual output examples
        assert "```" in skill_content, "Skill should show example command outputs"

    def test_warns_about_risks(self, skill_content: str):
        """Test that skill warns about risks and edge cases."""
        content_lower = skill_content.lower()

        risk_indicators = [
            "warning",
            "caution",
            "careful",
            "note:",
            "⚠️",
            "risk",
            "danger",
        ]

        found = [indicator for indicator in risk_indicators if indicator in content_lower]
        assert len(found) >= 2, (
            f"Skill should warn about risks and edge cases "
            f"(found {found}, expected >= 2 different indicators)"
        )


class TestSkillCrossReferences:
    """Test that skill correctly references other amplihack documentation."""

    @pytest.fixture
    def skill_content(self) -> str:
        """Load skill file content."""
        skill_path = Path("amplifier-bundle/skills/github-branch-protection/SKILL.md")
        return skill_path.read_text()

    def test_references_main_branch_protection_doc(self, skill_content: str):
        """Test that skill references main branch protection documentation."""
        assert "docs/features/main-branch-protection.md" in skill_content, (
            "Skill should reference docs/features/main-branch-protection.md"
        )

    def test_references_related_skills(self, skill_content: str):
        """Test that skill references related skills."""
        # Should reference other GitHub skills
        skill_lower = skill_content.lower()

        # These skills should be mentioned if they exist
        related_skills = ["github-copilot-cli", "creating-pull-requests"]

        # At least one related skill should be referenced
        found = [skill for skill in related_skills if skill in skill_lower]
        assert len(found) >= 1, (
            f"Skill should reference related skills for discoverability. "
            f"Expected at least one of {related_skills}, found {found}"
        )

    def test_links_to_github_documentation(self, skill_content: str):
        """Test that skill links to official GitHub documentation."""
        # Should include reference to GitHub docs
        assert (
            "github.com" in skill_content.lower() or "docs.github.com" in skill_content.lower()
        ), "Skill should link to official GitHub documentation for reference"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
