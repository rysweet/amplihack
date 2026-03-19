#!/usr/bin/env python3
"""
Outside-in behavioral tests for skill frontmatter loading.

Verifies that ALL skills in .claude/skills/ have valid YAML frontmatter
that Copilot CLI can parse without error. Tests the PUBLIC CONTRACT:
- Frontmatter must match ^---\\s*\n ... \n---
- Must contain 'name' and 'description' fields
- No duplicate skill directories via symlinks

Covers PR fixes:
1. azure-admin: metadata was in code block, not frontmatter
2. azure-devops-cli: title before frontmatter, HTML comments in YAML
3. github: same as azure-devops-cli
4. silent-degradation-audit: no frontmatter at all
5. .github/skills symlink removed to prevent triple-loading
"""

import re
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.e2e

# The regex Copilot CLI uses to extract frontmatter
# Source: ~/.copilot/pkg/linux-x64/*/index.js
FRONTMATTER_RE = re.compile(r"^---\s*\n([\s\S]*?)\n?---\s*(?:\n([\s\S]*))?$")

REPO_ROOT = Path(__file__).parent.parent.parent
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"

# Skills that were broken before the fix
PREVIOUSLY_BROKEN_SKILLS = [
    "azure-admin",
    "azure-devops-cli",
    "github",
    "silent-degradation-audit",
]


def _parse_frontmatter(content: str) -> dict | None:
    """Parse YAML frontmatter using the same regex as Copilot CLI."""
    match = FRONTMATTER_RE.match(content)
    if not match:
        return None
    try:
        return yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return None


def _all_skill_dirs() -> list[Path]:
    """Return all skill directories that contain a SKILL.md."""
    if not SKILLS_DIR.exists():
        return []
    return sorted(d for d in SKILLS_DIR.iterdir() if d.is_dir() and (d / "SKILL.md").exists())


class TestAllSkillsFrontmatterValid:
    """Every skill in .claude/skills/ must have parseable YAML frontmatter."""

    @pytest.fixture(params=_all_skill_dirs(), ids=lambda d: d.name)
    def skill_dir(self, request):
        return request.param

    def test_skill_has_valid_frontmatter(self, skill_dir):
        """SKILL.md must start with --- delimited YAML frontmatter."""
        content = (skill_dir / "SKILL.md").read_text()
        fm = _parse_frontmatter(content)
        assert fm is not None, (
            f"{skill_dir.name}/SKILL.md: missing or malformed YAML frontmatter. "
            f"File must start with ---\\n<yaml>\\n---"
        )

    def test_skill_has_required_fields(self, skill_dir):
        """Frontmatter must contain 'name' and 'description'."""
        content = (skill_dir / "SKILL.md").read_text()
        fm = _parse_frontmatter(content)
        if fm is None:
            pytest.skip("frontmatter invalid — covered by other test")

        assert "name" in fm, f"{skill_dir.name}: missing 'name' field in frontmatter"
        assert "description" in fm, f"{skill_dir.name}: missing 'description' field in frontmatter"

    def test_skill_name_matches_directory(self, skill_dir):
        """Frontmatter 'name' should match the directory name."""
        content = (skill_dir / "SKILL.md").read_text()
        fm = _parse_frontmatter(content)
        if fm is None:
            pytest.skip("frontmatter invalid — covered by other test")

        assert fm.get("name") == skill_dir.name, (
            f"Frontmatter name '{fm.get('name')}' doesn't match directory name '{skill_dir.name}'"
        )


class TestPreviouslyBrokenSkills:
    """Regression tests for the 4 skills that had broken frontmatter."""

    @pytest.mark.parametrize("skill_name", PREVIOUSLY_BROKEN_SKILLS)
    def test_skill_loads_without_error(self, skill_name):
        """Previously broken skills must now have valid frontmatter."""
        skill_file = SKILLS_DIR / skill_name / "SKILL.md"
        assert skill_file.exists(), f"{skill_name}/SKILL.md not found"

        content = skill_file.read_text()
        fm = _parse_frontmatter(content)
        assert fm is not None, f"{skill_name}: still has malformed frontmatter"
        assert fm["name"] == skill_name
        assert "description" in fm and len(fm["description"]) > 10

    @pytest.mark.parametrize("skill_name", PREVIOUSLY_BROKEN_SKILLS)
    def test_no_html_comments_in_frontmatter(self, skill_name):
        """Frontmatter YAML must not contain HTML comments (invalid YAML)."""
        content = (SKILLS_DIR / skill_name / "SKILL.md").read_text()
        match = FRONTMATTER_RE.match(content)
        if not match:
            pytest.skip("frontmatter invalid — covered by other test")

        yaml_block = match.group(1)
        assert "<!--" not in yaml_block, (
            f"{skill_name}: frontmatter contains HTML comments which break YAML parsing"
        )

    @pytest.mark.parametrize("skill_name", PREVIOUSLY_BROKEN_SKILLS)
    def test_frontmatter_is_at_file_start(self, skill_name):
        """Frontmatter --- must be the very first line of the file."""
        content = (SKILLS_DIR / skill_name / "SKILL.md").read_text()
        assert content.startswith("---"), (
            f"{skill_name}: file doesn't start with '---' — "
            f"frontmatter must be at the very beginning"
        )


class TestNoDuplicateSkillPaths:
    """Verify no symlinks cause skills to be loaded multiple times."""

    def test_no_github_skills_symlink(self):
        """.github/skills should not exist (was a symlink to .claude/skills)."""
        github_skills = REPO_ROOT / ".github" / "skills"
        assert not github_skills.exists(), (
            ".github/skills still exists — this causes Copilot CLI to load "
            "every skill twice at the project level. Remove the symlink."
        )

    def test_no_symlinks_in_skills_dir(self):
        """No skill directory should be a symlink (prevents duplicate loading)."""
        for d in SKILLS_DIR.iterdir():
            if d.is_dir():
                assert not d.is_symlink(), (
                    f".claude/skills/{d.name} is a symlink — this may cause duplicate skill loading"
                )
