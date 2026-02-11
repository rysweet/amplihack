"""
Test suite for Amplihack bundle integration.

TDD: These tests SHOULD FAIL initially - implementation doesn't exist yet.
They define the expected behavior for:
- Behavior YAML files (dev-tools, lsp-rust, community, notifications)
- Bundle.md integration
- Documentation updates
- Security requirements
"""

import re
from pathlib import Path

import pytest
import yaml

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def behaviors_dir(project_root: Path) -> Path:
    """Get the behaviors directory path."""
    return project_root / "amplifier-bundle" / "behaviors"


@pytest.fixture
def bundle_md(project_root: Path) -> Path:
    """Get the main bundle.md file path."""
    return project_root / "amplifier-bundle" / "bundle.md"


@pytest.fixture
def docs_dir(project_root: Path) -> Path:
    """Get the docs directory path."""
    return project_root / "docs"


@pytest.fixture
def gitignore(project_root: Path) -> Path:
    """Get the .gitignore file path."""
    return project_root / ".gitignore"


# ============================================================================
# TEST: Behavior YAML Files Exist
# ============================================================================


class TestBehaviorFilesExist:
    """Test that all behavior YAML files are created."""

    def test_dev_tools_yaml_exists(self, behaviors_dir: Path):
        """Test that dev-tools.yaml exists."""
        dev_tools_yaml = behaviors_dir / "dev-tools.yaml"
        assert dev_tools_yaml.exists(), (
            f"Expected {dev_tools_yaml} to exist. "
            "This file should integrate python-dev and ts-dev bundles."
        )

    def test_lsp_rust_yaml_exists(self, behaviors_dir: Path):
        """Test that lsp-rust.yaml exists."""
        lsp_rust_yaml = behaviors_dir / "lsp-rust.yaml"
        assert lsp_rust_yaml.exists(), (
            f"Expected {lsp_rust_yaml} to exist. "
            "This file should integrate standalone lsp-rust bundle."
        )

    def test_community_yaml_exists(self, behaviors_dir: Path):
        """Test that community.yaml exists."""
        community_yaml = behaviors_dir / "community.yaml"
        assert community_yaml.exists(), (
            f"Expected {community_yaml} to exist. "
            "This file should integrate memory and perplexity bundles."
        )

    def test_notifications_yaml_exists(self, behaviors_dir: Path):
        """Test that notifications.yaml exists."""
        notifications_yaml = behaviors_dir / "notifications.yaml"
        assert notifications_yaml.exists(), (
            f"Expected {notifications_yaml} to exist. "
            "This file should integrate notify bundle (optional)."
        )


# ============================================================================
# TEST: YAML Syntax Validity
# ============================================================================


class TestYAMLSyntax:
    """Test that all YAML files have valid syntax."""

    @pytest.mark.parametrize(
        "filename",
        [
            "dev-tools.yaml",
            "lsp-rust.yaml",
            "community.yaml",
            "notifications.yaml",
        ],
    )
    def test_yaml_parses_without_errors(self, behaviors_dir: Path, filename: str):
        """Test that YAML file parses without syntax errors."""
        yaml_file = behaviors_dir / filename

        with open(yaml_file) as f:
            try:
                data = yaml.safe_load(f)
                assert data is not None, f"{filename} parsed to None - check for empty file"
            except yaml.YAMLError as e:
                pytest.fail(f"{filename} has invalid YAML syntax: {e}")


# ============================================================================
# TEST: Bundle Structure and Naming
# ============================================================================


class TestBundleStructure:
    """Test bundle naming conventions and structure."""

    def test_dev_tools_has_correct_name(self, behaviors_dir: Path):
        """Test that dev-tools.yaml follows amplihack-* naming convention."""
        yaml_file = behaviors_dir / "dev-tools.yaml"
        with open(yaml_file) as f:
            data = yaml.safe_load(f)

        assert "name" in data, "Bundle must have a 'name' field"
        assert data["name"].startswith("amplihack-"), (
            f"Bundle name must start with 'amplihack-', got: {data['name']}"
        )

    def test_lsp_rust_has_correct_name(self, behaviors_dir: Path):
        """Test that lsp-rust.yaml follows amplihack-* naming convention."""
        yaml_file = behaviors_dir / "lsp-rust.yaml"
        with open(yaml_file) as f:
            data = yaml.safe_load(f)

        assert "name" in data, "Bundle must have a 'name' field"
        assert data["name"].startswith("amplihack-"), (
            f"Bundle name must start with 'amplihack-', got: {data['name']}"
        )

    def test_community_has_correct_name(self, behaviors_dir: Path):
        """Test that community.yaml follows amplihack-* naming convention."""
        yaml_file = behaviors_dir / "community.yaml"
        with open(yaml_file) as f:
            data = yaml.safe_load(f)

        assert "name" in data, "Bundle must have a 'name' field"
        assert data["name"].startswith("amplihack-"), (
            f"Bundle name must start with 'amplihack-', got: {data['name']}"
        )


# ============================================================================
# TEST: Bundle References (Git URLs)
# ============================================================================


class TestBundleReferences:
    """Test that bundles reference correct Git URLs."""

    def test_dev_tools_includes_python_dev(self, behaviors_dir: Path):
        """Test that dev-tools.yaml includes python-dev bundle."""
        yaml_file = behaviors_dir / "dev-tools.yaml"
        with open(yaml_file) as f:
            data = yaml.safe_load(f)

        includes = data.get("includes", [])
        python_dev_url = "git+https://github.com/microsoft/amplifier-bundle-python-dev@main"

        # Check if python-dev is included
        python_dev_found = False
        for include in includes:
            if (isinstance(include, dict) and include.get("bundle") == python_dev_url) or (
                isinstance(include, str) and include == python_dev_url
            ):
                python_dev_found = True
                break

        assert python_dev_found, (
            f"Expected python-dev bundle ({python_dev_url}) in includes section"
        )

    def test_dev_tools_includes_ts_dev(self, behaviors_dir: Path):
        """Test that dev-tools.yaml includes ts-dev bundle."""
        yaml_file = behaviors_dir / "dev-tools.yaml"
        with open(yaml_file) as f:
            data = yaml.safe_load(f)

        includes = data.get("includes", [])
        ts_dev_url = "git+https://github.com/microsoft/amplifier-bundle-ts-dev@main"

        # Check if ts-dev is included
        ts_dev_found = False
        for include in includes:
            if (isinstance(include, dict) and include.get("bundle") == ts_dev_url) or (
                isinstance(include, str) and include == ts_dev_url
            ):
                ts_dev_found = True
                break

        assert ts_dev_found, f"Expected ts-dev bundle ({ts_dev_url}) in includes section"

    def test_lsp_rust_includes_lsp_rust_bundle(self, behaviors_dir: Path):
        """Test that lsp-rust.yaml includes lsp-rust bundle."""
        yaml_file = behaviors_dir / "lsp-rust.yaml"
        with open(yaml_file) as f:
            data = yaml.safe_load(f)

        includes = data.get("includes", [])
        lsp_rust_url = "git+https://github.com/microsoft/amplifier-bundle-lsp-rust@main"

        # Check if lsp-rust is included
        lsp_rust_found = False
        for include in includes:
            if (isinstance(include, dict) and include.get("bundle") == lsp_rust_url) or (
                isinstance(include, str) and include == lsp_rust_url
            ):
                lsp_rust_found = True
                break

        assert lsp_rust_found, f"Expected lsp-rust bundle ({lsp_rust_url}) in includes section"

    def test_community_includes_memory(self, behaviors_dir: Path):
        """Test that community.yaml includes memory bundle."""
        yaml_file = behaviors_dir / "community.yaml"
        with open(yaml_file) as f:
            data = yaml.safe_load(f)

        includes = data.get("includes", [])
        memory_url = "git+https://github.com/michaeljabbour/amplifier-bundle-memory@main"

        # Check if memory is included
        memory_found = False
        for include in includes:
            if (isinstance(include, dict) and include.get("bundle") == memory_url) or (
                isinstance(include, str) and include == memory_url
            ):
                memory_found = True
                break

        assert memory_found, f"Expected memory bundle ({memory_url}) in includes section"

    def test_community_includes_perplexity(self, behaviors_dir: Path):
        """Test that community.yaml includes perplexity bundle."""
        yaml_file = behaviors_dir / "community.yaml"
        with open(yaml_file) as f:
            data = yaml.safe_load(f)

        includes = data.get("includes", [])
        perplexity_url = "git+https://github.com/colombod/amplifier-bundle-perplexity@main"

        # Check if perplexity is included
        perplexity_found = False
        for include in includes:
            if (isinstance(include, dict) and include.get("bundle") == perplexity_url) or (
                isinstance(include, str) and include == perplexity_url
            ):
                perplexity_found = True
                break

        assert perplexity_found, (
            f"Expected perplexity bundle ({perplexity_url}) in includes section"
        )

    def test_notifications_includes_notify(self, behaviors_dir: Path):
        """Test that notifications.yaml includes notify bundle."""
        yaml_file = behaviors_dir / "notifications.yaml"
        with open(yaml_file) as f:
            data = yaml.safe_load(f)

        includes = data.get("includes", [])
        notify_url = "git+https://github.com/microsoft/amplifier-bundle-notify@main"

        # Check if notify is included
        notify_found = False
        for include in includes:
            if (isinstance(include, dict) and include.get("bundle") == notify_url) or (
                isinstance(include, str) and include == notify_url
            ):
                notify_found = True
                break

        assert notify_found, f"Expected notify bundle ({notify_url}) in includes section"


# ============================================================================
# TEST: Git URLs Use HTTPS and @main Branch
# ============================================================================


class TestGitURLFormat:
    """Test that Git URLs follow security best practices."""

    @pytest.mark.parametrize(
        "filename",
        [
            "dev-tools.yaml",
            "lsp-rust.yaml",
            "community.yaml",
            "notifications.yaml",
        ],
    )
    def test_git_urls_use_https(self, behaviors_dir: Path, filename: str):
        """Test that all Git URLs use HTTPS protocol."""
        yaml_file = behaviors_dir / filename
        with open(yaml_file) as f:
            content = f.read()

        # Find all Git URLs
        git_urls = re.findall(r"git\+[^\s]+", content)

        for url in git_urls:
            assert url.startswith("git+https://"), f"Git URL must use HTTPS protocol, got: {url}"

    @pytest.mark.parametrize(
        "filename",
        [
            "dev-tools.yaml",
            "lsp-rust.yaml",
            "community.yaml",
            "notifications.yaml",
        ],
    )
    def test_git_urls_use_main_branch(self, behaviors_dir: Path, filename: str):
        """Test that all Git URLs reference @main branch."""
        yaml_file = behaviors_dir / filename
        with open(yaml_file) as f:
            content = f.read()

        # Find all Git URLs
        git_urls = re.findall(r"git\+https://[^\s]+", content)

        for url in git_urls:
            assert url.endswith("@main"), f"Git URL must reference @main branch, got: {url}"


# ============================================================================
# TEST: Security Requirements
# ============================================================================


class TestSecurityRequirements:
    """Test security-related requirements."""

    def test_no_hardcoded_api_keys(self, behaviors_dir: Path):
        """Test that no API keys are hardcoded in YAML files."""
        yaml_files = [
            "dev-tools.yaml",
            "lsp-rust.yaml",
            "community.yaml",
            "notifications.yaml",
        ]

        # Patterns that indicate hardcoded secrets
        secret_patterns = [
            r'api[_-]?key:\s*["\']?[a-zA-Z0-9]{20,}',
            r'token:\s*["\']?[a-zA-Z0-9]{20,}',
            r'password:\s*["\']?[a-zA-Z0-9]+',
            r'secret:\s*["\']?[a-zA-Z0-9]{20,}',
        ]

        for filename in yaml_files:
            yaml_file = behaviors_dir / filename
            with open(yaml_file) as f:
                content = f.read()

            for pattern in secret_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                assert len(matches) == 0, (
                    f"Potential hardcoded secret found in {filename}: {matches}"
                )

    def test_community_yaml_has_security_comments(self, behaviors_dir: Path):
        """Test that community.yaml has security warnings."""
        yaml_file = behaviors_dir / "community.yaml"
        with open(yaml_file) as f:
            content = f.read()

        # Check for security-related comments
        assert "security" in content.lower() or "warning" in content.lower(), (
            "community.yaml should have security warnings in comments"
        )

    def test_gitignore_includes_secret_patterns(self, gitignore: Path):
        """Test that .gitignore includes secret file patterns."""
        with open(gitignore) as f:
            content = f.read()

        required_patterns = [".env", "*.key", "*secret*", "*token*"]

        for pattern in required_patterns:
            assert pattern in content, f".gitignore must include pattern: {pattern}"


# ============================================================================
# TEST: Bundle.md Integration
# ============================================================================


class TestBundleMdIntegration:
    """Test that bundle.md is updated correctly."""

    def test_bundle_md_includes_dev_tools(self, bundle_md: Path):
        """Test that bundle.md includes dev-tools behavior."""
        with open(bundle_md) as f:
            content = f.read()

        # Look for the behavior include
        assert "behaviors/dev-tools.yaml" in content, (
            "bundle.md should include behaviors/dev-tools.yaml"
        )

    def test_bundle_md_includes_lsp_rust(self, bundle_md: Path):
        """Test that bundle.md includes lsp-rust behavior."""
        with open(bundle_md) as f:
            content = f.read()

        # Look for the behavior include
        assert "behaviors/lsp-rust.yaml" in content, (
            "bundle.md should include behaviors/lsp-rust.yaml"
        )

    def test_bundle_md_includes_community(self, bundle_md: Path):
        """Test that bundle.md includes community behavior."""
        with open(bundle_md) as f:
            content = f.read()

        # Look for the behavior include
        assert "behaviors/community.yaml" in content, (
            "bundle.md should include behaviors/community.yaml"
        )

    def test_bundle_md_version_unchanged(self, bundle_md: Path):
        """Test that bundle.md version remains 1.0.0."""
        with open(bundle_md) as f:
            content = f.read()

        # Look for version field
        version_match = re.search(r'version:\s*["\']?(\d+\.\d+\.\d+)', content)
        assert version_match, "Could not find version field in bundle.md"

        version = version_match.group(1)
        assert version == "0.8.0", f"Version should remain 0.8.0, got: {version}"


# ============================================================================
# TEST: Documentation Updates
# ============================================================================


class TestDocumentationUpdates:
    """Test that documentation is updated for multi-language support."""

    def test_readme_mentions_multiple_languages(self, project_root: Path):
        """Test that README.md mentions Python, TypeScript, JavaScript, Rust."""
        readme = project_root / "README.md"
        with open(readme) as f:
            content = f.read()

        languages = ["Python", "TypeScript", "JavaScript", "Rust"]

        for lang in languages:
            assert lang in content, f"README.md should mention {lang} support"

    def test_readme_no_python_only_language(self, project_root: Path):
        """Test that README.md doesn't refer to Python-only."""
        readme = project_root / "README.md"
        with open(readme) as f:
            content = f.read()

        problematic_phrases = [
            "Python-only",
            "Python-specific",
            "for Python projects only",
            "Python projects only",
        ]

        for phrase in problematic_phrases:
            assert phrase not in content, f"README.md should not contain '{phrase}'"

    def test_docs_index_mentions_multiple_languages(self, docs_dir: Path):
        """Test that docs/index.md mentions multiple languages."""
        index = docs_dir / "index.md"
        with open(index) as f:
            content = f.read()

        languages = ["Python", "TypeScript", "Rust"]

        for lang in languages:
            assert lang in content, f"docs/index.md should mention {lang} support"

    def test_security_md_exists(self, docs_dir: Path):
        """Test that SECURITY.md exists."""
        security_md = docs_dir / "SECURITY.md"
        assert security_md.exists(), "docs/SECURITY.md should exist with security documentation"

    def test_privacy_md_exists(self, docs_dir: Path):
        """Test that PRIVACY.md exists."""
        privacy_md = docs_dir / "PRIVACY.md"
        assert privacy_md.exists(), "docs/PRIVACY.md should exist with privacy disclosure"

    def test_prerequisites_mentions_lsp_setup(self, docs_dir: Path):
        """Test that PREREQUISITES.md mentions LSP setup."""
        prerequisites = docs_dir / "PREREQUISITES.md"
        with open(prerequisites) as f:
            content = f.read()

        assert "LSP" in content or "Language Server" in content, (
            "PREREQUISITES.md should mention LSP/Language Server setup"
        )


# ============================================================================
# TEST: Behavior Comments and Documentation
# ============================================================================


class TestBehaviorComments:
    """Test that behavior files have proper comments."""

    @pytest.mark.parametrize(
        "filename,expected_comment",
        [
            ("dev-tools.yaml", "quality"),
            ("lsp-rust.yaml", "Rust"),
            ("community.yaml", "community"),
            ("notifications.yaml", "notification"),
        ],
    )
    def test_behavior_has_explanatory_comments(
        self, behaviors_dir: Path, filename: str, expected_comment: str
    ):
        """Test that behavior YAML has comments explaining purpose."""
        yaml_file = behaviors_dir / filename
        with open(yaml_file) as f:
            content = f.read()

        # Check for comments (lines starting with #)
        comments = [line for line in content.split("\n") if line.strip().startswith("#")]

        assert len(comments) > 0, f"{filename} should have explanatory comments"

        # Check that at least one comment mentions the expected topic
        comment_text = " ".join(comments).lower()
        assert expected_comment.lower() in comment_text, (
            f"{filename} comments should mention '{expected_comment}'"
        )


# ============================================================================
# TEST: Integration - No Circular Dependencies
# ============================================================================


class TestNCircularDependencies:
    """Test that no circular dependencies are introduced."""

    def test_no_self_includes(self, behaviors_dir: Path):
        """Test that behavior bundles don't include themselves."""
        yaml_files = [
            "dev-tools.yaml",
            "lsp-rust.yaml",
            "community.yaml",
            "notifications.yaml",
        ]

        for filename in yaml_files:
            yaml_file = behaviors_dir / filename
            with open(yaml_file) as f:
                data = yaml.safe_load(f)

            bundle_name = data.get("name", "")
            includes = data.get("includes", [])

            for include in includes:
                include_str = str(include)
                assert bundle_name not in include_str, (
                    f"{filename} appears to include itself: {bundle_name} in {include_str}"
                )


# ============================================================================
# TEST: Edge Cases
# ============================================================================


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_includes_not_allowed(self, behaviors_dir: Path):
        """Test that behavior bundles have at least one include."""
        yaml_files = [
            "dev-tools.yaml",
            "lsp-rust.yaml",
            "community.yaml",
            "notifications.yaml",
        ]

        for filename in yaml_files:
            yaml_file = behaviors_dir / filename
            with open(yaml_file) as f:
                data = yaml.safe_load(f)

            includes = data.get("includes", [])
            assert len(includes) > 0, (
                f"{filename} must have at least one bundle in includes section"
            )

    def test_yaml_files_not_empty(self, behaviors_dir: Path):
        """Test that YAML files are not empty."""
        yaml_files = [
            "dev-tools.yaml",
            "lsp-rust.yaml",
            "community.yaml",
            "notifications.yaml",
        ]

        for filename in yaml_files:
            yaml_file = behaviors_dir / filename
            with open(yaml_file) as f:
                content = f.read().strip()

            assert len(content) > 0, f"{filename} should not be empty"

    def test_no_duplicate_includes(self, behaviors_dir: Path):
        """Test that behavior bundles don't have duplicate includes."""
        yaml_files = [
            "dev-tools.yaml",
            "lsp-rust.yaml",
            "community.yaml",
            "notifications.yaml",
        ]

        for filename in yaml_files:
            yaml_file = behaviors_dir / filename
            with open(yaml_file) as f:
                data = yaml.safe_load(f)

            includes = data.get("includes", [])

            # Convert to strings for comparison
            include_strs = []
            for include in includes:
                if isinstance(include, dict):
                    include_strs.append(include.get("bundle", ""))
                else:
                    include_strs.append(str(include))

            # Check for duplicates
            unique_includes = set(include_strs)
            assert len(unique_includes) == len(include_strs), (
                f"{filename} has duplicate includes: {include_strs}"
            )
