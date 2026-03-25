"""TDD tests for supply_chain_audit.advisories — advisory database contracts.

Tests the built-in advisory database (Trivy, LiteLLM), advisory lookup,
custom YAML loading, and schema validation.

Tests are written FIRST (TDD Red phase) and will fail until
implementation is complete.
"""

from __future__ import annotations

import textwrap
from datetime import UTC, datetime

import pytest

from amplihack.tools.supply_chain_audit.advisories import (
    BUILTIN_ADVISORIES,
    get_advisory,
    list_advisories,
    load_custom_advisories,
    validate_advisory_yaml,
)
from amplihack.tools.supply_chain_audit.models import Advisory

# ===========================================================================
# Built-in Advisories
# ===========================================================================


class TestBuiltinAdvisories:
    """Verify the built-in advisory database."""

    def test_builtin_advisories_is_dict(self):
        """BUILTIN_ADVISORIES is a dict mapping ID → Advisory."""
        assert isinstance(BUILTIN_ADVISORIES, dict)

    def test_contains_trivy_advisory(self):
        """Built-in DB includes the Trivy action compromise."""
        assert "GHSA-69fq-xp46-6x23" in BUILTIN_ADVISORIES

    def test_contains_litellm_advisory(self):
        """Built-in DB includes the LiteLLM PyPI compromise."""
        assert "PYPI-LITELLM-2025" in BUILTIN_ADVISORIES

    def test_trivy_advisory_fields(self):
        """Trivy advisory has correct fields."""
        adv = BUILTIN_ADVISORIES["GHSA-69fq-xp46-6x23"]
        assert isinstance(adv, Advisory)
        assert adv.attack_vector == "actions"
        assert adv.package_name == "aquasecurity/trivy-action"
        assert adv.exposure_window_start == datetime(2025, 1, 13, 0, 0, 0, tzinfo=UTC)
        assert adv.exposure_window_end == datetime(2025, 1, 14, 23, 59, 59, tzinfo=UTC)
        assert len(adv.compromised_versions) >= 1
        assert "tpcp-docs.github.io" in adv.iocs.domains

    def test_litellm_advisory_fields(self):
        """LiteLLM advisory has correct fields."""
        adv = BUILTIN_ADVISORIES["PYPI-LITELLM-2025"]
        assert isinstance(adv, Advisory)
        assert adv.attack_vector == "pypi"
        assert adv.package_name == "litellm"
        assert "1.82.7" in adv.compromised_versions
        assert "1.82.8" in adv.compromised_versions
        assert adv.exposure_window_start == datetime(2025, 3, 17, 0, 0, 0, tzinfo=UTC)
        assert "*.pth" in adv.iocs.file_patterns

    def test_litellm_safe_versions(self):
        """LiteLLM advisory lists known safe versions."""
        adv = BUILTIN_ADVISORIES["PYPI-LITELLM-2025"]
        assert "1.82.6" in adv.safe_versions or any("1.82.6" in v for v in adv.safe_versions)

    def test_all_builtins_are_advisory_instances(self):
        """Every entry in BUILTIN_ADVISORIES is an Advisory instance."""
        for advisory_id, adv in BUILTIN_ADVISORIES.items():
            assert isinstance(adv, Advisory), f"{advisory_id} is not an Advisory"
            assert adv.id == advisory_id


# ===========================================================================
# get_advisory()
# ===========================================================================


class TestGetAdvisory:
    """Lookup advisory by ID."""

    def test_get_known_advisory(self):
        """get_advisory returns Advisory for known ID."""
        adv = get_advisory("GHSA-69fq-xp46-6x23")
        assert adv is not None
        assert adv.id == "GHSA-69fq-xp46-6x23"

    def test_get_unknown_advisory(self):
        """get_advisory returns None for unknown ID."""
        adv = get_advisory("NONEXISTENT-2099")
        assert adv is None

    def test_case_sensitive(self):
        """Advisory lookup is case-sensitive."""
        adv = get_advisory("ghsa-69fq-xp46-6x23")
        assert adv is None  # IDs are uppercase

    def test_get_litellm(self):
        """get_advisory returns LiteLLM advisory."""
        adv = get_advisory("PYPI-LITELLM-2025")
        assert adv is not None
        assert adv.attack_vector == "pypi"


# ===========================================================================
# list_advisories()
# ===========================================================================


class TestListAdvisories:
    """List all available advisories."""

    def test_returns_list(self):
        """list_advisories returns a list of Advisory objects."""
        advisories = list_advisories()
        assert isinstance(advisories, list)
        assert all(isinstance(a, Advisory) for a in advisories)

    def test_includes_builtins(self):
        """list_advisories includes all built-in advisories."""
        advisories = list_advisories()
        ids = {a.id for a in advisories}
        assert "GHSA-69fq-xp46-6x23" in ids
        assert "PYPI-LITELLM-2025" in ids

    def test_at_least_two(self):
        """At least 2 built-in advisories exist."""
        advisories = list_advisories()
        assert len(advisories) >= 2


# ===========================================================================
# Custom YAML Loading
# ===========================================================================


class TestLoadCustomAdvisories:
    """Load custom advisories from YAML config files."""

    @pytest.fixture
    def valid_yaml(self, tmp_path):
        """Create a valid custom advisory YAML file."""
        content = textwrap.dedent("""\
            id: "CUSTOM-2026-001"
            title: "Test Custom Advisory"
            description: "A test advisory for validation"
            attack_vector: "actions"
            exposure_window:
              start: "2026-01-01T00:00:00Z"
              end: "2026-01-03T00:00:00Z"
            compromised_versions:
              - "v1.0.0"
              - "v1.0.1"
            package_name: "owner/test-action"
            safe_versions:
              - "v0.9.0"
              - "v1.0.2"
            safe_shas:
              - "abc123def456"  # pragma: allowlist secret
            iocs:
              domains:
                - "evil.example.com"
              ips:
                - "198.51.100.42"
              file_patterns:
                - "*.backdoor.sh"
        """)
        yaml_file = tmp_path / "custom_advisory.yaml"
        yaml_file.write_text(content)
        return yaml_file

    @pytest.fixture
    def minimal_yaml(self, tmp_path):
        """Create a minimal valid custom advisory YAML (required fields only)."""
        content = textwrap.dedent("""\
            id: "CUSTOM-MINIMAL"
            title: "Minimal Advisory"
            description: "Minimal test"
            attack_vector: "pypi"
            exposure_window:
              start: "2026-01-01T00:00:00Z"
              end: "2026-01-02T00:00:00Z"
            compromised_versions:
              - "1.0.0"
            package_name: "bad-package"
        """)
        yaml_file = tmp_path / "minimal.yaml"
        yaml_file.write_text(content)
        return yaml_file

    def test_load_valid_yaml(self, valid_yaml):
        """Valid YAML produces Advisory objects."""
        advisories = load_custom_advisories(str(valid_yaml))
        assert len(advisories) >= 1
        adv = advisories[0]
        assert isinstance(adv, Advisory)
        assert adv.id == "CUSTOM-2026-001"
        assert adv.attack_vector == "actions"
        assert "evil.example.com" in adv.iocs.domains

    def test_load_minimal_yaml(self, minimal_yaml):
        """Minimal YAML with only required fields works."""
        advisories = load_custom_advisories(str(minimal_yaml))
        assert len(advisories) >= 1
        adv = advisories[0]
        assert adv.id == "CUSTOM-MINIMAL"
        assert adv.iocs.is_empty()

    def test_load_nonexistent_file_raises(self):
        """Loading from nonexistent path raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_custom_advisories("/nonexistent/path/advisory.yaml")

    def test_load_oversized_file_raises(self, tmp_path):
        """Files exceeding 64KB raise ValueError."""
        big_file = tmp_path / "big.yaml"
        big_file.write_text("x" * (65 * 1024))
        with pytest.raises(ValueError, match="64"):
            load_custom_advisories(str(big_file))

    def test_load_invalid_yaml_syntax(self, tmp_path):
        """Invalid YAML syntax raises ValueError."""
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text(":::not valid yaml[[[")
        with pytest.raises(ValueError):
            load_custom_advisories(str(bad_file))

    def test_path_traversal_rejected(self, tmp_path):
        """Paths with '..' are rejected."""
        with pytest.raises(ValueError, match="traversal|path"):
            load_custom_advisories(str(tmp_path / ".." / ".." / "etc" / "passwd"))

    def test_custom_advisories_merged_with_list(self, valid_yaml):
        """list_advisories(config=path) includes custom + built-in."""
        all_advisories = list_advisories(config=str(valid_yaml))
        ids = {a.id for a in all_advisories}
        assert "CUSTOM-2026-001" in ids
        assert "GHSA-69fq-xp46-6x23" in ids  # built-in still present


# ===========================================================================
# YAML Schema Validation
# ===========================================================================


class TestValidateAdvisoryYaml:
    """Validate custom advisory YAML schema."""

    def test_valid_schema_passes(self, tmp_path):
        """Valid YAML passes validation with no errors."""
        content = textwrap.dedent("""\
            id: "VALID-001"
            title: "Valid Advisory"
            description: "Test"
            attack_vector: "actions"
            exposure_window:
              start: "2026-01-01T00:00:00Z"
              end: "2026-01-02T00:00:00Z"
            compromised_versions:
              - "v1.0.0"
            package_name: "owner/action"
        """)
        yaml_file = tmp_path / "valid.yaml"
        yaml_file.write_text(content)
        errors = validate_advisory_yaml(str(yaml_file))
        assert errors == []

    @pytest.mark.parametrize(
        "missing_field",
        [
            "id",
            "title",
            "description",
            "attack_vector",
            "exposure_window",
            "compromised_versions",
            "package_name",
        ],
    )
    def test_missing_required_field(self, tmp_path, missing_field):
        """Each missing required field produces a validation error."""
        fields = {
            "id": '"VALID-001"',
            "title": '"Test"',
            "description": '"Test"',
            "attack_vector": '"actions"',
            "exposure_window": '\n  start: "2026-01-01T00:00:00Z"\n  end: "2026-01-02T00:00:00Z"',
            "compromised_versions": '\n  - "v1.0.0"',
            "package_name": '"owner/action"',
        }
        lines = []
        for k, v in fields.items():
            if k != missing_field:
                lines.append(f"{k}: {v}")
        yaml_file = tmp_path / "incomplete.yaml"
        yaml_file.write_text("\n".join(lines))
        errors = validate_advisory_yaml(str(yaml_file))
        assert len(errors) >= 1
        assert any(missing_field in e.lower() for e in errors)

    def test_invalid_attack_vector(self, tmp_path):
        """Invalid attack vector produces validation error."""
        content = textwrap.dedent("""\
            id: "BAD-001"
            title: "Bad"
            description: "Bad"
            attack_vector: "unknown_vector"
            exposure_window:
              start: "2026-01-01T00:00:00Z"
              end: "2026-01-02T00:00:00Z"
            compromised_versions:
              - "v1.0.0"
            package_name: "owner/action"
        """)
        yaml_file = tmp_path / "bad_vector.yaml"
        yaml_file.write_text(content)
        errors = validate_advisory_yaml(str(yaml_file))
        assert len(errors) >= 1
        assert any("attack_vector" in e.lower() for e in errors)

    def test_exposure_window_end_before_start(self, tmp_path):
        """End before start produces validation error."""
        content = textwrap.dedent("""\
            id: "BAD-002"
            title: "Bad"
            description: "Bad"
            attack_vector: "actions"
            exposure_window:
              start: "2026-01-03T00:00:00Z"
              end: "2026-01-01T00:00:00Z"
            compromised_versions:
              - "v1.0.0"
            package_name: "owner/action"
        """)
        yaml_file = tmp_path / "bad_window.yaml"
        yaml_file.write_text(content)
        errors = validate_advisory_yaml(str(yaml_file))
        assert len(errors) >= 1
        assert any("window" in e.lower() or "start" in e.lower() for e in errors)

    def test_empty_compromised_versions(self, tmp_path):
        """Empty compromised_versions list produces error."""
        content = textwrap.dedent("""\
            id: "BAD-003"
            title: "Bad"
            description: "Bad"
            attack_vector: "actions"
            exposure_window:
              start: "2026-01-01T00:00:00Z"
              end: "2026-01-02T00:00:00Z"
            compromised_versions: []
            package_name: "owner/action"
        """)
        yaml_file = tmp_path / "empty_versions.yaml"
        yaml_file.write_text(content)
        errors = validate_advisory_yaml(str(yaml_file))
        assert len(errors) >= 1

    def test_multiple_advisories_yaml(self, tmp_path):
        """YAML list with multiple advisories is valid."""
        content = textwrap.dedent("""\
            - id: "MULTI-001"
              title: "First"
              description: "First advisory"
              attack_vector: "actions"
              exposure_window:
                start: "2026-01-01T00:00:00Z"
                end: "2026-01-02T00:00:00Z"
              compromised_versions:
                - "v1.0.0"
              package_name: "owner/action1"
            - id: "MULTI-002"
              title: "Second"
              description: "Second advisory"
              attack_vector: "pypi"
              exposure_window:
                start: "2026-02-01T00:00:00Z"
                end: "2026-02-02T00:00:00Z"
              compromised_versions:
                - "2.0.0"
              package_name: "bad-package"
        """)
        yaml_file = tmp_path / "multi.yaml"
        yaml_file.write_text(content)
        advisories = load_custom_advisories(str(yaml_file))
        assert len(advisories) == 2
        ids = {a.id for a in advisories}
        assert "MULTI-001" in ids
        assert "MULTI-002" in ids
