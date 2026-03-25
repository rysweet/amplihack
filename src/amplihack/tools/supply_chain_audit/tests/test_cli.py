"""TDD tests for supply_chain_audit.cli — Click CLI command contracts.

Tests the Click CLI using CliRunner: audit, list-advisories, and
validate-config commands with exit codes and output format.

Tests are written FIRST (TDD Red phase) and will fail until
implementation is complete.
"""

from __future__ import annotations

import json
import textwrap
from datetime import UTC
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from amplihack.tools.supply_chain_audit.cli import supply_chain_audit

# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def runner():
    return CliRunner()


# ===========================================================================
# Help & Basic CLI
# ===========================================================================


class TestCLIHelp:
    """CLI help text and basic invocation."""

    def test_help_exit_code(self, runner):
        """--help exits with code 0."""
        result = runner.invoke(supply_chain_audit, ["--help"])
        assert result.exit_code == 0

    def test_help_lists_commands(self, runner):
        """--help shows all three commands."""
        result = runner.invoke(supply_chain_audit, ["--help"])
        assert "audit" in result.output
        assert "list-advisories" in result.output
        assert "validate-config" in result.output

    def test_audit_help(self, runner):
        """audit --help shows options."""
        result = runner.invoke(supply_chain_audit, ["audit", "--help"])
        assert result.exit_code == 0
        assert "--repos" in result.output
        assert "--org" in result.output
        assert "--format" in result.output

    def test_no_args_shows_help(self, runner):
        """No arguments shows help text."""
        result = runner.invoke(supply_chain_audit, [])
        assert result.exit_code == 0
        assert "audit" in result.output


# ===========================================================================
# audit command
# ===========================================================================


class TestAuditCommand:
    """Tests for the audit subcommand."""

    def test_audit_requires_advisory_id(self, runner):
        """audit without advisory ID fails."""
        result = runner.invoke(supply_chain_audit, ["audit"])
        assert result.exit_code != 0

    def test_audit_requires_repos_or_org(self, runner):
        """audit with advisory but no --repos or --org fails."""
        result = runner.invoke(supply_chain_audit, ["audit", "GHSA-69fq-xp46-6x23"])
        assert result.exit_code != 0
        assert "repos" in result.output.lower() or "org" in result.output.lower()

    def test_audit_rejects_both_repos_and_org(self, runner):
        """audit with both --repos and --org fails."""
        result = runner.invoke(
            supply_chain_audit,
            ["audit", "GHSA-69fq-xp46-6x23", "--repos", "o/r", "--org", "my-org"],
        )
        assert result.exit_code != 0

    @patch("amplihack.tools.supply_chain_audit.cli.Analyzer")
    @patch("amplihack.tools.supply_chain_audit.cli.get_advisory")
    def test_audit_unknown_advisory_fails(self, mock_get, mock_analyzer, runner):
        """audit with unknown advisory ID exits with error."""
        mock_get.return_value = None
        result = runner.invoke(
            supply_chain_audit,
            ["audit", "NONEXISTENT-999", "--repos", "owner/repo"],
        )
        assert result.exit_code != 0

    @patch("amplihack.tools.supply_chain_audit.cli.Analyzer")
    @patch("amplihack.tools.supply_chain_audit.cli.get_advisory")
    def test_audit_known_advisory_with_repos(self, mock_get, mock_analyzer_cls, runner):
        """audit with known advisory and --repos runs successfully."""
        from datetime import datetime

        from amplihack.tools.supply_chain_audit.models import (
            Advisory,
            AuditReport,
            IOCSet,
            RepoVerdict,
        )

        mock_advisory = Advisory(
            id="GHSA-69fq-xp46-6x23",
            title="Trivy Action Compromise",
            description="Test",
            attack_vector="actions",
            exposure_window_start=datetime(2025, 1, 13, tzinfo=UTC),
            exposure_window_end=datetime(2025, 1, 14, 23, 59, 59, tzinfo=UTC),
            compromised_versions=["v0.18.0"],
            package_name="aquasecurity/trivy-action",
            iocs=IOCSet(domains=["tpcp-docs.github.io"]),
        )
        mock_get.return_value = mock_advisory

        mock_report = AuditReport(
            advisory_id="GHSA-69fq-xp46-6x23",
            advisory_title="Trivy Action Compromise",
            scan_timestamp=datetime.now(UTC),
            repos_scanned=1,
            summary={"safe": 1, "compromised": 0, "inconclusive": 0},
            verdicts=[
                RepoVerdict(
                    repo="owner/repo",
                    verdict="SAFE",
                    confidence="HIGH",
                    evidence=[],
                    workflow_runs_analyzed=5,
                    ioc_matches=[],
                ),
            ],
        )
        mock_analyzer_instance = MagicMock()
        mock_analyzer_instance.audit.return_value = mock_report
        mock_analyzer_cls.return_value = mock_analyzer_instance

        result = runner.invoke(
            supply_chain_audit,
            ["audit", "GHSA-69fq-xp46-6x23", "--repos", "owner/repo"],
        )
        assert result.exit_code == 0

    @patch("amplihack.tools.supply_chain_audit.cli.Analyzer")
    @patch("amplihack.tools.supply_chain_audit.cli.get_advisory")
    def test_audit_json_output(self, mock_get, mock_analyzer_cls, runner):
        """--format json produces valid JSON output."""
        from datetime import datetime

        from amplihack.tools.supply_chain_audit.models import (
            Advisory,
            AuditReport,
            IOCSet,
            RepoVerdict,
        )

        mock_advisory = Advisory(
            id="GHSA-69fq-xp46-6x23",
            title="Trivy",
            description="Test",
            attack_vector="actions",
            exposure_window_start=datetime(2025, 1, 13, tzinfo=UTC),
            exposure_window_end=datetime(2025, 1, 14, 23, 59, 59, tzinfo=UTC),
            compromised_versions=["v0.18.0"],
            package_name="aquasecurity/trivy-action",
            iocs=IOCSet(domains=["tpcp-docs.github.io"]),
        )
        mock_get.return_value = mock_advisory

        mock_report = AuditReport(
            advisory_id="GHSA-69fq-xp46-6x23",
            advisory_title="Trivy",
            scan_timestamp=datetime.now(UTC),
            repos_scanned=1,
            summary={"safe": 1, "compromised": 0, "inconclusive": 0},
            verdicts=[
                RepoVerdict(
                    repo="owner/repo",
                    verdict="SAFE",
                    confidence="HIGH",
                    evidence=[],
                    workflow_runs_analyzed=5,
                    ioc_matches=[],
                ),
            ],
        )
        mock_analyzer_instance = MagicMock()
        mock_analyzer_instance.audit.return_value = mock_report
        mock_analyzer_cls.return_value = mock_analyzer_instance

        result = runner.invoke(
            supply_chain_audit,
            [
                "audit",
                "GHSA-69fq-xp46-6x23",
                "--repos",
                "owner/repo",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["advisory_id"] == "GHSA-69fq-xp46-6x23"

    # -----------------------------------------------------------------------
    # Exit codes
    # -----------------------------------------------------------------------

    @patch("amplihack.tools.supply_chain_audit.cli.Analyzer")
    @patch("amplihack.tools.supply_chain_audit.cli.get_advisory")
    def test_exit_code_0_all_safe(self, mock_get, mock_analyzer_cls, runner):
        """Exit code 0 when all repos are SAFE."""
        from datetime import datetime

        from amplihack.tools.supply_chain_audit.models import (
            Advisory,
            AuditReport,
            RepoVerdict,
        )

        mock_get.return_value = Advisory(
            id="TEST",
            title="Test",
            description="Test",
            attack_vector="actions",
            exposure_window_start=datetime(2025, 1, 1, tzinfo=UTC),
            exposure_window_end=datetime(2025, 1, 2, tzinfo=UTC),
            compromised_versions=["v1.0"],
            package_name="test/pkg",
        )
        mock_report = AuditReport(
            advisory_id="TEST",
            advisory_title="Test",
            scan_timestamp=datetime.now(UTC),
            repos_scanned=1,
            summary={"safe": 1, "compromised": 0, "inconclusive": 0},
            verdicts=[
                RepoVerdict(
                    repo="o/r",
                    verdict="SAFE",
                    confidence="HIGH",
                    evidence=[],
                    workflow_runs_analyzed=1,
                    ioc_matches=[],
                ),
            ],
        )
        mock_inst = MagicMock()
        mock_inst.audit.return_value = mock_report
        mock_analyzer_cls.return_value = mock_inst

        result = runner.invoke(supply_chain_audit, ["audit", "TEST", "--repos", "o/r"])
        assert result.exit_code == 0

    @patch("amplihack.tools.supply_chain_audit.cli.Analyzer")
    @patch("amplihack.tools.supply_chain_audit.cli.get_advisory")
    def test_exit_code_1_compromised(self, mock_get, mock_analyzer_cls, runner):
        """Exit code 1 when any repo is COMPROMISED."""
        from datetime import datetime

        from amplihack.tools.supply_chain_audit.models import (
            Advisory,
            AuditReport,
            RepoVerdict,
        )

        mock_get.return_value = Advisory(
            id="TEST",
            title="Test",
            description="Test",
            attack_vector="actions",
            exposure_window_start=datetime(2025, 1, 1, tzinfo=UTC),
            exposure_window_end=datetime(2025, 1, 2, tzinfo=UTC),
            compromised_versions=["v1.0"],
            package_name="test/pkg",
        )
        mock_report = AuditReport(
            advisory_id="TEST",
            advisory_title="Test",
            scan_timestamp=datetime.now(UTC),
            repos_scanned=1,
            summary={"safe": 0, "compromised": 1, "inconclusive": 0},
            verdicts=[
                RepoVerdict(
                    repo="o/r",
                    verdict="COMPROMISED",
                    confidence="HIGH",
                    evidence=[],
                    workflow_runs_analyzed=1,
                    ioc_matches=[],
                ),
            ],
        )
        mock_inst = MagicMock()
        mock_inst.audit.return_value = mock_report
        mock_analyzer_cls.return_value = mock_inst

        result = runner.invoke(supply_chain_audit, ["audit", "TEST", "--repos", "o/r"])
        assert result.exit_code == 1

    @patch("amplihack.tools.supply_chain_audit.cli.Analyzer")
    @patch("amplihack.tools.supply_chain_audit.cli.get_advisory")
    def test_exit_code_2_inconclusive(self, mock_get, mock_analyzer_cls, runner):
        """Exit code 2 when inconclusive (no compromised)."""
        from datetime import datetime

        from amplihack.tools.supply_chain_audit.models import (
            Advisory,
            AuditReport,
            RepoVerdict,
        )

        mock_get.return_value = Advisory(
            id="TEST",
            title="Test",
            description="Test",
            attack_vector="actions",
            exposure_window_start=datetime(2025, 1, 1, tzinfo=UTC),
            exposure_window_end=datetime(2025, 1, 2, tzinfo=UTC),
            compromised_versions=["v1.0"],
            package_name="test/pkg",
        )
        mock_report = AuditReport(
            advisory_id="TEST",
            advisory_title="Test",
            scan_timestamp=datetime.now(UTC),
            repos_scanned=1,
            summary={"safe": 0, "compromised": 0, "inconclusive": 1},
            verdicts=[
                RepoVerdict(
                    repo="o/r",
                    verdict="INCONCLUSIVE",
                    confidence="LOW",
                    evidence=[],
                    workflow_runs_analyzed=0,
                    ioc_matches=[],
                ),
            ],
        )
        mock_inst = MagicMock()
        mock_inst.audit.return_value = mock_report
        mock_analyzer_cls.return_value = mock_inst

        result = runner.invoke(supply_chain_audit, ["audit", "TEST", "--repos", "o/r"])
        assert result.exit_code == 2


# ===========================================================================
# list-advisories command
# ===========================================================================


class TestListAdvisoriesCommand:
    """Tests for the list-advisories subcommand."""

    def test_list_advisories_text(self, runner):
        """list-advisories shows advisory info in text format."""
        result = runner.invoke(supply_chain_audit, ["list-advisories"])
        assert result.exit_code == 0
        assert "GHSA-69fq-xp46-6x23" in result.output
        assert "PYPI-LITELLM-2025" in result.output

    def test_list_advisories_json(self, runner):
        """list-advisories --format json produces valid JSON."""
        result = runner.invoke(supply_chain_audit, ["list-advisories", "--format", "json"])
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert isinstance(parsed, list)
        ids = {a["id"] for a in parsed}
        assert "GHSA-69fq-xp46-6x23" in ids

    def test_list_advisories_with_config(self, runner, tmp_path):
        """list-advisories --config includes custom advisories."""
        config = tmp_path / "custom.yaml"
        config.write_text(
            textwrap.dedent("""\
            id: "CUSTOM-001"
            title: "Custom Advisory"
            description: "Test"
            attack_vector: "actions"
            exposure_window:
              start: "2026-01-01T00:00:00Z"
              end: "2026-01-02T00:00:00Z"
            compromised_versions:
              - "v1.0.0"
            package_name: "owner/action"
        """)
        )
        result = runner.invoke(supply_chain_audit, ["list-advisories", "--config", str(config)])
        assert result.exit_code == 0
        assert "CUSTOM-001" in result.output


# ===========================================================================
# validate-config command
# ===========================================================================


class TestValidateConfigCommand:
    """Tests for the validate-config subcommand."""

    def test_validate_valid_config(self, runner, tmp_path):
        """Valid config exits 0."""
        config = tmp_path / "valid.yaml"
        config.write_text(
            textwrap.dedent("""\
            id: "VALID-001"
            title: "Valid"
            description: "Test"
            attack_vector: "actions"
            exposure_window:
              start: "2026-01-01T00:00:00Z"
              end: "2026-01-02T00:00:00Z"
            compromised_versions:
              - "v1.0.0"
            package_name: "owner/action"
        """)
        )
        result = runner.invoke(supply_chain_audit, ["validate-config", str(config)])
        assert result.exit_code == 0

    def test_validate_invalid_config(self, runner, tmp_path):
        """Invalid config exits 1 with errors."""
        config = tmp_path / "invalid.yaml"
        config.write_text(
            textwrap.dedent("""\
            id: "BAD"
            title: "Bad"
        """)
        )
        result = runner.invoke(supply_chain_audit, ["validate-config", str(config)])
        assert result.exit_code == 1

    def test_validate_nonexistent_config(self, runner):
        """Nonexistent config path exits with error."""
        result = runner.invoke(
            supply_chain_audit,
            ["validate-config", "/nonexistent/file.yaml"],
        )
        assert result.exit_code != 0

    def test_validate_requires_path(self, runner):
        """validate-config without path fails."""
        result = runner.invoke(supply_chain_audit, ["validate-config"])
        assert result.exit_code != 0


# ===========================================================================
# Output File Writing
# ===========================================================================


class TestOutputFile:
    """Tests for --output file writing."""

    @patch("amplihack.tools.supply_chain_audit.cli.Analyzer")
    @patch("amplihack.tools.supply_chain_audit.cli.get_advisory")
    def test_output_writes_file(self, mock_get, mock_analyzer_cls, runner, tmp_path):
        """--output writes report to file."""
        from datetime import datetime

        from amplihack.tools.supply_chain_audit.models import (
            Advisory,
            AuditReport,
            RepoVerdict,
        )

        mock_get.return_value = Advisory(
            id="TEST",
            title="Test",
            description="Test",
            attack_vector="actions",
            exposure_window_start=datetime(2025, 1, 1, tzinfo=UTC),
            exposure_window_end=datetime(2025, 1, 2, tzinfo=UTC),
            compromised_versions=["v1.0"],
            package_name="test/pkg",
        )
        mock_report = AuditReport(
            advisory_id="TEST",
            advisory_title="Test",
            scan_timestamp=datetime.now(UTC),
            repos_scanned=1,
            summary={"safe": 1, "compromised": 0, "inconclusive": 0},
            verdicts=[
                RepoVerdict(
                    repo="o/r",
                    verdict="SAFE",
                    confidence="HIGH",
                    evidence=[],
                    workflow_runs_analyzed=1,
                    ioc_matches=[],
                ),
            ],
        )
        mock_inst = MagicMock()
        mock_inst.audit.return_value = mock_report
        mock_analyzer_cls.return_value = mock_inst

        out_file = tmp_path / "report.json"
        result = runner.invoke(
            supply_chain_audit,
            [
                "audit",
                "TEST",
                "--repos",
                "o/r",
                "--format",
                "json",
                "--output",
                str(out_file),
            ],
        )
        assert result.exit_code == 0
        assert out_file.exists()
        parsed = json.loads(out_file.read_text())
        assert parsed["advisory_id"] == "TEST"
