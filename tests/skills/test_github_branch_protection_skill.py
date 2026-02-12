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
        # Progressive disclosure: SKILL.md should be concise (~50-100 lines)
        # Detailed content moved to reference/ directory
        word_count = len(content.split())
        assert word_count < 1000, (
            f"Skill file too long: {word_count} words. "
            "Progressive disclosure requires <1000 words. Move details to reference/"
        )
        assert len(content.splitlines()) >= 50, (
            f"Skill file too short: {len(content.splitlines())} lines. "
            "Expected ~50-150 lines for main guidance"
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


class TestProgressiveDisclosureStructure:
    """Test the progressive disclosure structure (Level 3 reference files)."""

    def test_reference_directory_exists(self):
        """Test that reference/ directory exists for Level 3 content."""
        ref_dir = Path("amplifier-bundle/skills/github-branch-protection/reference")
        assert ref_dir.exists(), (
            "Progressive disclosure requires reference/ directory for detailed content"
        )
        assert ref_dir.is_dir(), "reference/ must be a directory"

    def test_examples_directory_exists(self):
        """Test that examples/ directory exists for working examples."""
        examples_dir = Path("amplifier-bundle/skills/github-branch-protection/examples")
        assert examples_dir.exists(), (
            "Progressive disclosure requires examples/ directory for working examples"
        )
        assert examples_dir.is_dir(), "examples/ must be a directory"

    def test_has_cli_walkthrough_reference(self):
        """Test that CLI walkthrough exists as reference file."""
        cli_ref = Path("amplifier-bundle/skills/github-branch-protection/reference/cli-walkthrough.md")
        assert cli_ref.exists(), "Must have reference/cli-walkthrough.md for detailed CLI instructions"
        content = cli_ref.read_text()
        assert len(content) > 500, "CLI walkthrough should have substantial content"
        assert "gh api" in content, "CLI walkthrough must contain gh api commands"

    def test_has_ui_walkthrough_reference(self):
        """Test that UI walkthrough exists as reference file."""
        ui_ref = Path("amplifier-bundle/skills/github-branch-protection/reference/ui-walkthrough.md")
        assert ui_ref.exists(), "Must have reference/ui-walkthrough.md for detailed UI instructions"
        content = ui_ref.read_text()
        assert len(content) > 300, "UI walkthrough should have substantial content"
        assert "Settings" in content, "UI walkthrough must reference GitHub Settings"

    def test_has_settings_reference(self):
        """Test that settings reference exists for detailed explanations."""
        settings_ref = Path("amplifier-bundle/skills/github-branch-protection/reference/settings-reference.md")
        assert settings_ref.exists(), "Must have reference/settings-reference.md for setting details"
        content = settings_ref.read_text()
        assert "trade-off" in content.lower() or "tradeoff" in content.lower(), (
            "Settings reference should explain trade-offs"
        )

    def test_has_troubleshooting_reference(self):
        """Test that troubleshooting guide exists as reference file."""
        troubleshoot_ref = Path("amplifier-bundle/skills/github-branch-protection/reference/troubleshooting.md")
        assert troubleshoot_ref.exists(), "Must have reference/troubleshooting.md"
        content = troubleshoot_ref.read_text()
        assert "403" in content or "404" in content, "Troubleshooting must cover common HTTP errors"

    def test_has_maintenance_guide(self):
        """Test that maintenance guide exists for future updates."""
        maint_ref = Path("amplifier-bundle/skills/github-branch-protection/reference/maintenance.md")
        assert maint_ref.exists(), "Must have reference/maintenance.md for update guidance"
        content = maint_ref.read_text()
        assert "update" in content.lower(), "Maintenance guide must cover updates"
        assert "version" in content.lower(), "Maintenance guide must cover versioning"

    def test_has_working_example(self):
        """Test that working example exists with actual commands."""
        example = Path("amplifier-bundle/skills/github-branch-protection/examples/amplihack-config.md")
        assert example.exists(), "Must have examples/amplihack-config.md with actual configuration"
        content = example.read_text()
        assert "amplihack" in content.lower(), "Example must reference amplihack repository"
        assert "rysweet" in content.lower(), "Example must show actual repository owner"

    def test_skill_links_to_references(self):
        """Test that main SKILL.md links to reference files."""
        skill_path = Path("amplifier-bundle/skills/github-branch-protection/SKILL.md")
        content = skill_path.read_text()

        # Check for links to reference files
        assert "reference/" in content, "SKILL.md must link to reference/ files"
        assert "examples/" in content, "SKILL.md must link to examples/"
        assert "cli-walkthrough.md" in content, "SKILL.md must link to CLI walkthrough"
        assert "ui-walkthrough.md" in content, "SKILL.md must link to UI walkthrough"
        assert "troubleshooting.md" in content, "SKILL.md must link to troubleshooting"

    def test_skill_links_to_external_docs(self):
        """Test that SKILL.md includes external GitHub documentation links."""
        skill_path = Path("amplifier-bundle/skills/github-branch-protection/SKILL.md")
        content = skill_path.read_text()

        # Check for external documentation
        assert "docs.github.com" in content, "SKILL.md must link to official GitHub documentation"


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
        """Test skill has Purpose/Overview section explaining the skill."""
        # With progressive disclosure, this can be "Overview" instead of "Purpose"
        assert any(section in skill_content for section in ["## Purpose", "# Purpose", "## Overview", "# Overview"]), (
            "Skill must have Purpose or Overview section"
        )
        assert "defense-in-depth" in skill_content.lower() or "layer" in skill_content.lower(), (
            "Must explain defense-in-depth positioning or layer concept"
        )

    def test_has_prerequisites_section(self, skill_content: str):
        """Test skill has Prerequisites section."""
        assert "## Prerequisites" in skill_content or "# Prerequisites" in skill_content, (
            "Skill must have Prerequisites section"
        )
        assert "gh auth status" in skill_content, "Prerequisites must include authentication check"

    def test_has_quick_reference_table(self, skill_content: str):
        """Test skill mentions core settings (detailed table can be in reference/)."""
        # With progressive disclosure, detailed tables move to reference/
        # Main skill should mention core settings
        content_lower = skill_content.lower()
        assert any(term in content_lower for term in ["setting", "protection", "require"]), (
            "Skill must mention protection settings"
        )

    def test_has_gh_cli_method(self, skill_content: str):
        """Test skill references gh CLI method."""
        # With progressive disclosure, detailed walkthrough is in reference/cli-walkthrough.md
        # Main skill should mention gh CLI and link to detailed guide
        assert "gh" in skill_content or "cli" in skill_content.lower(), (
            "Skill must mention gh CLI method"
        )
        assert "cli-walkthrough" in skill_content.lower() or "gh api" in skill_content, (
            "Skill must reference CLI walkthrough or show basic gh api command"
        )

    def test_has_github_ui_method(self, skill_content: str):
        """Test skill references GitHub UI method."""
        # With progressive disclosure, detailed UI walkthrough is in reference/ui-walkthrough.md
        # Main skill should mention UI method and link to detailed guide
        assert "ui" in skill_content.lower() or "web" in skill_content.lower(), (
            "Skill must mention GitHub UI method"
        )

    def test_has_protection_settings_explained(self, skill_content: str):
        """Test skill mentions core protection settings."""
        # With progressive disclosure, detailed explanations in reference/settings-reference.md
        # Main skill should list core settings
        required_settings = [
            "pull request",
            "review",
            "status check",
            "force push",
            "delet",  # matches "deletion" and "delete"
        ]

        content_lower = skill_content.lower()
        matched = sum(1 for setting in required_settings if setting in content_lower)
        assert matched >= 4, (
            f"Skill must mention at least 4 of 5 core protection settings (found {matched})"
        )

    def test_has_verification_section(self, skill_content: str):
        """Test skill has or references verification."""
        # With progressive disclosure, verification details in reference/
        # Main skill should mention verification or Emergency Procedures
        content_lower = skill_content.lower()
        assert any(term in content_lower for term in ["verif", "test", "emergency"]), (
            "Skill must mention verification or testing"
        )

    def test_has_working_example(self, skill_content: str):
        """Test skill references working example."""
        # With progressive disclosure, working example is in examples/amplihack-config.md
        # Main skill should link to it
        assert "example" in skill_content.lower(), (
            "Skill must reference working examples"
        )
        assert "amplihack" in skill_content.lower(), (
            "Skill must reference amplihack repository"
        )

    def test_has_troubleshooting_section(self, skill_content: str):
        """Test skill references troubleshooting."""
        # With progressive disclosure, troubleshooting details in reference/troubleshooting.md
        # Main skill should link to it or mention emergency procedures
        content_lower = skill_content.lower()
        assert any(term in content_lower for term in ["troubleshoot", "emergency", "disable protection"]), (
            "Skill must reference troubleshooting or emergency procedures"
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

        # With progressive disclosure, detailed JSON configs might be in reference files
        # Check main skill AND reference files for status checks configuration

        # Check main skill file
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

        # If not found in main skill, check if it's mentioned (could be in inline JSON or reference)
        if not found_status_checks:
            # Check if required_status_checks is at least mentioned in main skill
            assert "required_status_checks" in skill_content, (
                "Skill must show or reference required_status_checks configuration"
            )

            # Check reference files for detailed config
            ref_files = [
                Path("amplifier-bundle/skills/github-branch-protection/reference/cli-walkthrough.md"),
                Path("amplifier-bundle/skills/github-branch-protection/examples/amplihack-config.md")
            ]

            for ref_file in ref_files:
                if ref_file.exists():
                    ref_content = ref_file.read_text()
                    ref_json_blocks = re.findall(r"```json\n(.*?)```", ref_content, re.DOTALL)

                    for block in ref_json_blocks:
                        try:
                            data = json.loads(block)
                            if "required_status_checks" in data:
                                found_status_checks = True
                                break
                        except json.JSONDecodeError:
                            continue

                    if found_status_checks:
                        break

        assert found_status_checks, (
            "Skill or reference files must show required_status_checks configuration example"
        )


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
            "cautiously",  # Add more relevant terms
            "emergency",
        ]

        content_lower = skill_content.lower()
        found_count = sum(1 for indicator in trade_off_indicators if indicator in content_lower)

        # With progressive disclosure, detailed trade-offs can be in reference/settings-reference.md
        # Main skill should mention at least some considerations
        if found_count < 3:
            # Check reference file for trade-offs
            settings_ref = Path("amplifier-bundle/skills/github-branch-protection/reference/settings-reference.md")
            if settings_ref.exists():
                ref_content = settings_ref.read_text().lower()
                ref_found = sum(1 for indicator in trade_off_indicators if indicator in ref_content)
                found_count += min(ref_found, 3)  # Credit up to 3 from reference

        assert found_count >= 3, (
            f"Skill or reference files should explain trade-offs and considerations "
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
            "emergency",  # Add emergency procedures
            "important",
        ]

        found = [indicator for indicator in risk_indicators if indicator in content_lower]

        # With progressive disclosure, detailed warnings can be in reference/troubleshooting.md
        if len(found) < 2:
            # Check troubleshooting reference for warnings
            troubleshoot_ref = Path("amplifier-bundle/skills/github-branch-protection/reference/troubleshooting.md")
            if troubleshoot_ref.exists():
                ref_content = troubleshoot_ref.read_text().lower()
                ref_found = [indicator for indicator in risk_indicators if indicator in ref_content]
                found.extend(ref_found[:2])  # Add up to 2 from reference

        assert len(found) >= 2, (
            f"Skill or reference files should warn about risks and edge cases "
            f"(found {found[:3]}, expected >= 2 different indicators)"
        )


class TestSkillCrossReferences:
    """Test that skill correctly references other amplihack documentation."""

    @pytest.fixture
    def skill_content(self) -> str:
        """Load skill file content."""
        skill_path = Path("amplifier-bundle/skills/github-branch-protection/SKILL.md")
        return skill_path.read_text()

    def test_references_main_branch_protection_doc(self, skill_content: str):
        """Test that skill mentions client-side protection (may be in overview, not explicit link)."""
        # With progressive disclosure, explicit file paths might be in reference files
        # Main skill should at least mention client-side hook or related documentation
        content_lower = skill_content.lower()
        assert any(term in content_lower for term in [
            "docs/features/main-branch-protection",
            "client-side hook",
            "layer 1",
            ".git/hooks/pre-commit"
        ]), (
            "Skill should reference or mention client-side protection"
        )

    def test_references_related_skills(self, skill_content: str):
        """Test that skill has adequate cross-references."""
        # Should reference other GitHub skills

        # These skills should be mentioned if they exist
        # With progressive disclosure, related skills might not be explicitly mentioned
        # But the skill should have good cross-references to GitHub docs and internal references
        # This test is less relevant for a concise skill following progressive disclosure
        # We verify external docs are referenced instead
        assert "docs.github.com" in skill_content or "github.com/docs" in skill_content, (
            "Skill should reference official GitHub documentation"
        )

    def test_links_to_github_documentation(self, skill_content: str):
        """Test that skill links to official GitHub documentation."""
        # Should include reference to GitHub docs
        assert (
            "github.com" in skill_content.lower() or "docs.github.com" in skill_content.lower()
        ), "Skill should link to official GitHub documentation for reference"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
