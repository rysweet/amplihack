"""Validation tests for the markitdown skill following TDD methodology.

Tests validate skill file structure, YAML frontmatter, progressive disclosure,
security requirements, and completeness. These tests ensure the markitdown skill
follows amplihack philosophy and Claude Code best practices.

Philosophy:
- Skills are markdown files, not executable code
- Validation focuses on structure, content quality, and completeness
- Token efficiency is critical (SKILL.md target: <500 lines, 2000 tokens)
- Progressive disclosure: SKILL.md references supporting files
- Security: Must include security warnings for API keys
"""

import re
from pathlib import Path

import pytest
import tiktoken

# Path constants
AMPLIHACK_ROOT = Path("/home/azureuser/src/amplihack")
SKILL_DIR = AMPLIHACK_ROOT / ".claude" / "skills" / "markitdown"
SKILL_FILE = SKILL_DIR / "SKILL.md"

# Expected files in skill directory
REQUIRED_FILES = [
    "SKILL.md",
    "reference.md",
    "examples.md",
    "patterns.md",
]

# Token and line budget constants
MAX_SKILL_TOKENS = 2000
MAX_SKILL_LINES = 500
MIN_AUTO_ACTIVATES = 6


def count_tokens(text: str) -> int:
    """Count tokens using tiktoken for claude-sonnet-4-5."""
    # Use cl100k_base encoding (closest to Claude's tokenizer)
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))


def count_lines(text: str) -> int:
    """Count non-empty lines in text."""
    return len([line for line in text.split("\n") if line.strip()])


def extract_yaml_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter from markdown file."""
    # Match YAML frontmatter between --- delimiters
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}

    yaml_text = match.group(1)
    result = {}

    # Parse simple YAML (key: value or key: [list])
    current_key = None
    for line in yaml_text.split("\n"):
        line = line.strip()
        if not line:
            continue

        if line.startswith("- "):
            # List item
            if current_key and isinstance(result.get(current_key), list):
                result[current_key].append(line[2:].strip())
        elif ":" in line:
            # Key: value
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()

            if not value:
                # Empty value, might be start of list
                result[key] = []
                current_key = key
            else:
                result[key] = value
                current_key = None

    return result


class TestFileStructure:
    """Test that all required files exist in correct location."""

    def test_skill_directory_exists(self):
        """Test that markitdown skill directory exists."""
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

    def test_skill_file_is_readable(self):
        """Test that SKILL.md can be read."""
        assert SKILL_FILE.exists()
        content = SKILL_FILE.read_text()
        assert len(content) > 0, "SKILL.md is empty"


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
        assert frontmatter["name"] == "markitdown", (
            f"Expected name='markitdown', got '{frontmatter['name']}'"
        )

    def test_frontmatter_has_version(self, frontmatter):
        """Test that frontmatter includes 'version' field."""
        assert "version" in frontmatter, "YAML frontmatter missing 'version' field"
        # Check semantic versioning format
        version_pattern = r"^\d+\.\d+\.\d+$"
        assert re.match(version_pattern, frontmatter["version"]), (
            f"Version must be semantic (X.Y.Z), got '{frontmatter['version']}'"
        )

    def test_frontmatter_has_description(self, frontmatter):
        """Test that frontmatter includes 'description' field."""
        assert "description" in frontmatter, "YAML frontmatter missing 'description' field"
        desc = frontmatter["description"]
        assert len(desc) > 20, f"Description too short ({len(desc)} chars), should be >20 chars"
        assert len(desc) < 500, f"Description too long ({len(desc)} chars), should be <500 chars"

    def test_frontmatter_has_auto_activates(self, frontmatter):
        """Test that frontmatter includes 'auto_activates' list."""
        assert "auto_activates" in frontmatter, "YAML frontmatter missing 'auto_activates' field"
        auto_activates = frontmatter["auto_activates"]
        assert isinstance(auto_activates, list), "auto_activates must be a list"
        assert len(auto_activates) >= MIN_AUTO_ACTIVATES, (
            f"auto_activates should have >= {MIN_AUTO_ACTIVATES} triggers, "
            f"got {len(auto_activates)}"
        )

    def test_frontmatter_has_source_urls(self, frontmatter):
        """Test that frontmatter includes 'source_urls' field."""
        assert "source_urls" in frontmatter, "YAML frontmatter missing 'source_urls' field"
        source_urls = frontmatter["source_urls"]
        assert isinstance(source_urls, list), "source_urls must be a list"
        assert len(source_urls) > 0, "source_urls list is empty"
        # Check that URLs are valid format
        for url in source_urls:
            assert url.startswith("http"), f"Invalid URL in source_urls: {url}"

    def test_frontmatter_has_priority_score(self, frontmatter):
        """Test that frontmatter includes 'priority_score' field."""
        assert "priority_score" in frontmatter, "YAML frontmatter missing 'priority_score' field"
        priority = frontmatter["priority_score"]
        # Should be numeric
        try:
            float(priority)
        except (ValueError, TypeError):
            pytest.fail(f"priority_score must be numeric, got '{priority}'")


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


class TestProgressiveDisclosure:
    """Test progressive disclosure pattern implementation."""

    @pytest.fixture
    def skill_content(self):
        """Load SKILL.md content."""
        return SKILL_FILE.read_text()

    def test_has_navigation_guide(self, skill_content):
        """Test that SKILL.md includes navigation guide to supporting files."""
        # Check for navigation section
        assert "When to Read Supporting Files" in skill_content or (
            "Supporting Files" in skill_content
        ), (
            "SKILL.md must include navigation guide: "
            "'When to Read Supporting Files' or 'Supporting Files' section"
        )

    def test_references_all_supporting_files(self, skill_content):
        """Test that SKILL.md references all supporting files."""
        supporting_files = ["reference.md", "examples.md", "patterns.md"]
        for filename in supporting_files:
            # Check for markdown link syntax
            pattern = rf"\[.*?\]\({filename}\)"
            assert re.search(pattern, skill_content), (
                f"SKILL.md must reference supporting file: {filename}"
            )

    def test_navigation_guide_format(self, skill_content):
        """Test that navigation guide uses proper format."""
        # Should have bullet points or structured links to supporting files
        supporting_files = ["reference.md", "examples.md", "patterns.md"]
        for filename in supporting_files:
            # Check for link with description pattern
            pattern = rf"-\s+\*\*\[.*?\]\({filename}\)\*\*\s+-\s+Read when"
            if not re.search(pattern, skill_content):
                # Alternative format: just link with text
                pattern = rf"\[.*?\]\({filename}\).*?when"
                assert re.search(pattern, skill_content, re.IGNORECASE), (
                    f"Navigation guide should explain WHEN to read {filename}"
                )


class TestSecurityRequirements:
    """Test that security warnings and best practices are included."""

    @pytest.fixture
    def skill_content(self):
        """Load SKILL.md content."""
        return SKILL_FILE.read_text()

    def test_has_security_section(self, skill_content):
        """Test that SKILL.md includes security section."""
        security_indicators = [
            "Security",
            "security",
            "🔒",
            "API Key",
        ]
        found = any(indicator in skill_content for indicator in security_indicators)
        assert found, "SKILL.md must include security section or security warnings"

    def test_api_key_security_warnings(self, skill_content):
        """Test that API key security warnings are present."""
        # Should warn against hardcoding
        assert "NEVER" in skill_content or "❌" in skill_content, (
            "SKILL.md should include warnings about what NOT to do"
        )
        # Should mention environment variables
        assert "environment variable" in skill_content.lower() or (
            "OPENAI_API_KEY" in skill_content
        ), "SKILL.md should mention using environment variables for API keys"

    def test_secure_examples_present(self, skill_content):
        """Test that secure code examples are included."""
        # Check for secure pattern examples
        assert "os.getenv" in skill_content or "os.environ" in skill_content, (
            "SKILL.md should include secure examples using os.getenv()"
        )


class TestContentQuality:
    """Test content quality and completeness."""

    @pytest.fixture
    def skill_content(self):
        """Load SKILL.md content."""
        return SKILL_FILE.read_text()

    def test_has_overview_section(self, skill_content):
        """Test that SKILL.md has overview section."""
        assert "## Overview" in skill_content or "# Overview" in skill_content, (
            "SKILL.md should have an Overview section"
        )

    def test_has_usage_examples(self, skill_content):
        """Test that SKILL.md includes usage examples."""
        # Should have code blocks
        assert "```python" in skill_content or "```bash" in skill_content, (
            "SKILL.md should include code examples"
        )

    def test_has_quick_start(self, skill_content):
        """Test that SKILL.md includes quick start section."""
        quick_start_indicators = [
            "Quick Start",
            "Getting Started",
            "Basic Usage",
        ]
        found = any(indicator in skill_content for indicator in quick_start_indicators)
        assert found, "SKILL.md should have Quick Start or Getting Started section"

    def test_has_common_mistakes_section(self, skill_content):
        """Test that SKILL.md includes common mistakes/anti-patterns."""
        mistakes_indicators = [
            "Common Mistake",
            "Anti-Pattern",
            "⚠️",
            "Common Issues",
        ]
        found = any(indicator in skill_content for indicator in mistakes_indicators)
        assert found, "SKILL.md should include Common Mistakes or Anti-Patterns section"

    def test_supported_formats_documented(self, skill_content):
        """Test that supported file formats are documented."""
        # For markitdown specifically, should mention key formats
        formats = ["PDF", "Word", "Excel", "PowerPoint", "Image"]
        missing = [fmt for fmt in formats if fmt not in skill_content]
        assert not missing, (
            f"SKILL.md should document supported formats. Missing: {', '.join(missing)}"
        )


class TestSupportingFiles:
    """Test that supporting files meet quality standards."""

    def test_reference_file_exists(self):
        """Test that reference.md exists and is substantial."""
        ref_file = SKILL_DIR / "reference.md"
        assert ref_file.exists(), "reference.md is missing"
        content = ref_file.read_text()
        assert len(content) > 1000, (
            f"reference.md too short ({len(content)} chars), "
            "should contain comprehensive API documentation"
        )

    def test_examples_file_exists(self):
        """Test that examples.md exists and has examples."""
        ex_file = SKILL_DIR / "examples.md"
        assert ex_file.exists(), "examples.md is missing"
        content = ex_file.read_text()
        # Should have multiple code blocks
        code_blocks = content.count("```")
        assert code_blocks >= 4, (
            f"examples.md should have multiple code examples (found {code_blocks // 2} blocks)"
        )

    def test_patterns_file_exists(self):
        """Test that patterns.md exists and covers patterns."""
        patterns_file = SKILL_DIR / "patterns.md"
        assert patterns_file.exists(), "patterns.md is missing"
        content = patterns_file.read_text()
        # Should discuss patterns and security
        assert "pattern" in content.lower(), "patterns.md should discuss usage patterns"


class TestZeroBSCompliance:
    """Test Zero-BS implementation - no stubs, all examples complete."""

    @pytest.fixture
    def all_content(self):
        """Load all skill file contents."""
        content = {}
        for filename in REQUIRED_FILES:
            file_path = SKILL_DIR / filename
            if file_path.exists():
                content[filename] = file_path.read_text()
        return content

    def test_no_placeholder_code(self, all_content):
        """Test that there are no placeholder or stub code examples."""
        stub_indicators = [
            "# TODO",
            "# FIXME",
            "pass  # implementation",
            "# placeholder",
            "# stub",
        ]

        for filename, content in all_content.items():
            for indicator in stub_indicators:
                assert indicator not in content, (
                    f"{filename} contains stub/placeholder code: '{indicator}'"
                )

            # Check for ellipsis placeholders, but allow them in:
            # 1. String values like "sk-..." (API key examples)
            # 2. Comments
            # 3. URLs ending with ...
            if "..." in content:
                # Extract lines with ellipsis
                lines_with_ellipsis = [line for line in content.split("\n") if "..." in line]
                for line in lines_with_ellipsis:
                    # OK: In string literals (API keys, endpoints)
                    if '"..."' in line or "'...'" in line:
                        continue
                    # OK: In code strings like "sk-..." or "<endpoint...>"
                    if '"' in line and "..." in line:
                        continue
                    # OK: In comments
                    if line.strip().startswith("#"):
                        continue
                    # OK: In markdown headers or bullets
                    if line.strip().startswith(("-", "*", "#")):
                        continue
                    # NOT OK: Ellipsis as code placeholder
                    if "pass" in line or "return" in line:
                        pytest.fail(f"{filename} contains ellipsis placeholder in code:\n{line}")

    def test_examples_are_runnable(self, all_content):
        """Test that code examples appear complete and runnable."""
        examples_content = all_content.get("examples.md", "")
        skill_content = all_content.get("SKILL.md", "")

        # Extract Python code blocks
        python_blocks = re.findall(
            r"```python\n(.*?)\n```", examples_content + skill_content, re.DOTALL
        )

        assert len(python_blocks) > 0, "Should have Python code examples"

        for block in python_blocks:
            # Skip if it's explicitly marked as partial
            if "..." in block and "# partial example" not in block.lower():
                pytest.fail(f"Code example appears incomplete (contains '...'):\n{block[:100]}")
