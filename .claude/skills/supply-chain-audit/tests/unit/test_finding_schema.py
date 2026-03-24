"""
Unit tests — Finding Schema Validation
TDD: Tests define the 11-field finding contract from contracts.md.
All tests FAIL until supply_chain_audit.schema is implemented.
"""

import pytest

# This import WILL FAIL until implementation exists — that is the intent.
from supply_chain_audit.schema import Finding, FindingId, validate_finding


class TestFindingIdFormat:
    """Finding IDs must follow {SEVERITY}-{NNN} format, unique per report."""

    def test_valid_critical_id(self):
        fid = FindingId("CRITICAL-001")
        assert fid.severity == "Critical"
        assert fid.sequence == 1

    def test_valid_high_id(self):
        fid = FindingId("HIGH-042")
        assert fid.severity == "High"
        assert fid.sequence == 42

    def test_valid_medium_id(self):
        fid = FindingId("MEDIUM-007")
        assert fid.severity == "Medium"
        assert fid.sequence == 7

    def test_valid_info_id(self):
        fid = FindingId("INFO-001")
        assert fid.severity == "Info"
        assert fid.sequence == 1

    def test_id_rejects_lowercase_severity(self):
        with pytest.raises(ValueError, match="severity prefix"):
            FindingId("critical-001")

    def test_id_rejects_missing_sequence(self):
        with pytest.raises(ValueError):
            FindingId("HIGH-")

    def test_id_rejects_two_digit_sequence(self):
        """Sequence must be zero-padded to 3 digits."""
        with pytest.raises(ValueError, match="3-digit"):
            FindingId("HIGH-01")

    def test_id_rejects_wildcard(self):
        """Wildcards prohibited — accepted-risks protection."""
        with pytest.raises(ValueError, match="wildcard"):
            FindingId("HIGH-*")

    def test_id_rejects_invalid_severity_prefix(self):
        with pytest.raises(ValueError, match="severity"):
            FindingId("WARNING-001")

    def test_sequence_is_unique_within_report(self):
        """Two findings of same severity must have different sequences."""
        findings = [
            Finding(
                id="HIGH-001",
                dimension=1,
                severity="High",
                file=".github/workflows/ci.yml",
                line=8,
                current_value="actions/checkout@v4",
                expected_value="actions/checkout@<sha>  # v4",
                rationale="Mutable ref.",
                offline_detectable=True,
            ),
            Finding(
                id="HIGH-001",
                dimension=1,
                severity="High",
                file=".github/workflows/ci.yml",
                line=9,
                current_value="actions/setup-python@v5",
                expected_value="actions/setup-python@<sha>  # v5",
                rationale="Mutable ref.",
                offline_detectable=True,
            ),
        ]
        with pytest.raises(ValueError, match="duplicate.*id"):
            validate_finding(findings)


class TestFindingRequiredFields:
    """Every finding must have all required fields populated."""

    def test_minimal_valid_finding(self):
        f = Finding(
            id="HIGH-001",
            dimension=1,
            severity="High",
            file=".github/workflows/ci.yml",
            line=8,
            current_value="uses: actions/checkout@v4",
            expected_value="uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # v4.2.2",
            rationale="Mutable semver tag allows silent code replacement.",
            offline_detectable=True,
        )
        assert f.id == "HIGH-001"
        assert f.dimension == 1

    def test_missing_id_raises(self):
        with pytest.raises((TypeError, ValueError)):
            Finding(
                dimension=1,
                severity="High",
                file=".github/workflows/ci.yml",
                line=8,
                current_value="uses: actions/checkout@v4",
                expected_value="uses: actions/checkout@<sha>",
                rationale="Test.",
                offline_detectable=True,
            )

    def test_missing_rationale_raises(self):
        with pytest.raises((TypeError, ValueError)):
            Finding(
                id="HIGH-001",
                dimension=1,
                severity="High",
                file=".github/workflows/ci.yml",
                line=8,
                current_value="uses: actions/checkout@v4",
                expected_value="uses: actions/checkout@<sha>",
                offline_detectable=True,
            )

    def test_missing_offline_detectable_raises(self):
        with pytest.raises((TypeError, ValueError)):
            Finding(
                id="HIGH-001",
                dimension=1,
                severity="High",
                file=".github/workflows/ci.yml",
                line=8,
                current_value="uses: actions/checkout@v4",
                expected_value="uses: actions/checkout@<sha>",
                rationale="Mutable ref.",
            )


class TestFindingFieldConstraints:
    """Field-level constraint enforcement from contracts.md."""

    def test_dimension_must_be_1_to_12(self):
        with pytest.raises(ValueError, match="dimension"):
            Finding(
                id="HIGH-001",
                dimension=0,
                severity="High",
                file="f.yml",
                line=1,
                current_value="x",
                expected_value="y",
                rationale="r",
                offline_detectable=True,
            )

    def test_dimension_13_rejected(self):
        with pytest.raises(ValueError, match="dimension"):
            Finding(
                id="HIGH-001",
                dimension=13,
                severity="High",
                file="f.yml",
                line=1,
                current_value="x",
                expected_value="y",
                rationale="r",
                offline_detectable=True,
            )

    def test_severity_must_be_valid_enum(self):
        with pytest.raises(ValueError, match="severity"):
            Finding(
                id="WARNING-001",
                dimension=1,
                severity="Warning",
                file="f.yml",
                line=1,
                current_value="x",
                expected_value="y",
                rationale="r",
                offline_detectable=True,
            )

    def test_file_must_be_relative_posix_path(self):
        """Absolute paths are forbidden — must be relative."""
        with pytest.raises(ValueError, match="relative"):
            Finding(
                id="HIGH-001",
                dimension=1,
                severity="High",
                file="/home/user/.github/workflows/ci.yml",
                line=8,
                current_value="x",
                expected_value="y",
                rationale="r",
                offline_detectable=True,
            )

    def test_file_rejects_path_traversal(self):
        """Path traversal in file field must be rejected."""
        with pytest.raises(ValueError, match="traversal"):
            Finding(
                id="HIGH-001",
                dimension=1,
                severity="High",
                file="../../../etc/passwd",
                line=1,
                current_value="x",
                expected_value="y",
                rationale="r",
                offline_detectable=True,
            )

    def test_line_zero_valid_for_file_level_findings(self):
        """Line 0 is valid — indicates a file-level finding."""
        f = Finding(
            id="HIGH-001",
            dimension=10,
            severity="High",
            file="package.json",
            line=0,
            current_value="no package-lock.json",
            expected_value="add package-lock.json",
            rationale="Lock file absent.",
            offline_detectable=True,
        )
        assert f.line == 0

    def test_line_negative_rejected(self):
        with pytest.raises(ValueError, match="line"):
            Finding(
                id="HIGH-001",
                dimension=1,
                severity="High",
                file="f.yml",
                line=-1,
                current_value="x",
                expected_value="y",
                rationale="r",
                offline_detectable=True,
            )

    def test_tool_required_valid_values(self):
        """tool_required must be null or one of the approved tool names."""
        # null is valid
        f = Finding(
            id="HIGH-001",
            dimension=5,
            severity="High",
            file="Dockerfile",
            line=1,
            current_value="FROM alpine:latest",
            expected_value="FROM alpine@sha256:<digest>",
            rationale="Mutable tag.",
            offline_detectable=False,
            tool_required=None,
        )
        assert f.tool_required is None

    def test_tool_required_crane_valid(self):
        f = Finding(
            id="HIGH-001",
            dimension=5,
            severity="High",
            file="Dockerfile",
            line=1,
            current_value="FROM alpine:latest",
            expected_value="FROM alpine@sha256:<digest>",
            rationale="Mutable tag.",
            offline_detectable=False,
            tool_required="crane",
        )
        assert f.tool_required == "crane"

    def test_tool_required_invalid_name_rejected(self):
        with pytest.raises(ValueError, match="tool_required"):
            Finding(
                id="HIGH-001",
                dimension=5,
                severity="High",
                file="Dockerfile",
                line=1,
                current_value="x",
                expected_value="y",
                rationale="r",
                offline_detectable=False,
                tool_required="docker",
            )  # "docker" not in approved list


class TestSecretRedaction:
    """Secrets must never appear in finding output — replaced with <REDACTED>."""

    def test_current_value_with_secret_is_redacted(self):
        f = Finding(
            id="CRITICAL-001",
            dimension=3,
            severity="Critical",
            file=".github/workflows/ci.yml",
            line=12,
            current_value="echo 'mysecretvalue123'",
            expected_value="Remove secret echo",
            rationale="Secret echoed to log.",
            offline_detectable=True,
            contains_secret=True,
        )
        rendered = f.render()
        assert "mysecretvalue123" not in rendered
        assert "<REDACTED>" in rendered

    def test_expected_value_with_secret_is_redacted(self):
        f = Finding(
            id="CRITICAL-001",
            dimension=6,
            severity="Critical",
            file=".github/workflows/ci.yml",
            line=5,
            current_value="aws-secret-access-key: ${{ secrets.AWS_SECRET }}",
            expected_value="Use OIDC: id-token: write",
            rationale="Static credential.",
            offline_detectable=True,
            contains_secret=True,
        )
        rendered = f.render()
        assert "<REDACTED>" in rendered
