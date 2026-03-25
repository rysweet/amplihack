"""TDD tests for supply_chain_audit.models — dataclass contracts.

These tests define the expected behavior of all data models:
Advisory, IOCSet, WorkflowRun, RunAnalysis, IOCMatch, RepoVerdict,
Evidence, and AuditReport.

Tests are written FIRST (TDD Red phase) and will fail until
implementation is complete.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

# ---------------------------------------------------------------------------
# Imports — will fail until models.py is created
# ---------------------------------------------------------------------------
from amplihack.tools.supply_chain_audit.models import (
    Advisory,
    AuditReport,
    Evidence,
    IOCMatch,
    IOCSet,
    RepoVerdict,
    RunAnalysis,
    WorkflowRun,
)

# ===========================================================================
# IOCSet
# ===========================================================================


class TestIOCSet:
    """IOCSet holds indicator-of-compromise patterns."""

    def test_empty_defaults(self):
        """IOCSet with no args has empty lists."""
        ioc = IOCSet()
        assert ioc.domains == []
        assert ioc.ips == []
        assert ioc.file_patterns == []

    def test_with_values(self):
        """IOCSet stores provided values."""
        ioc = IOCSet(
            domains=["evil.example.com"],
            ips=["198.51.100.42"],
            file_patterns=["*.pth"],
        )
        assert "evil.example.com" in ioc.domains
        assert "198.51.100.42" in ioc.ips
        assert "*.pth" in ioc.file_patterns

    def test_is_empty_true(self):
        """is_empty returns True when all lists are empty."""
        ioc = IOCSet()
        assert ioc.is_empty() is True

    def test_is_empty_false(self):
        """is_empty returns False when any list is populated."""
        ioc = IOCSet(domains=["evil.example.com"])
        assert ioc.is_empty() is False


# ===========================================================================
# Advisory
# ===========================================================================


class TestAdvisory:
    """Advisory represents a known supply chain incident."""

    @pytest.fixture
    def trivy_advisory(self):
        return Advisory(
            id="GHSA-69fq-xp46-6x23",
            title="Trivy Action Compromise",
            description="Compromised GitHub Action",
            attack_vector="actions",
            exposure_window_start=datetime(2025, 1, 13, tzinfo=UTC),
            exposure_window_end=datetime(2025, 1, 14, 23, 59, 59, tzinfo=UTC),
            compromised_versions=["v0.18.0", "v0.19.0", "v0.20.0"],
            package_name="aquasecurity/trivy-action",
            safe_versions=[],
            safe_shas=[],
            iocs=IOCSet(domains=["tpcp-docs.github.io"]),
        )

    @pytest.fixture
    def litellm_advisory(self):
        return Advisory(
            id="PYPI-LITELLM-2025",
            title="LiteLLM Malicious PyPI Release",
            description="Malicious PyPI package release",
            attack_vector="pypi",
            exposure_window_start=datetime(2025, 3, 17, tzinfo=UTC),
            exposure_window_end=datetime(2025, 3, 19, 23, 59, 59, tzinfo=UTC),
            compromised_versions=["1.82.7", "1.82.8"],
            package_name="litellm",
            safe_versions=["1.82.6", "1.82.9"],
            safe_shas=[],
            iocs=IOCSet(file_patterns=["*.pth"]),
        )

    def test_basic_creation(self, trivy_advisory):
        """Advisory can be created with all required fields."""
        assert trivy_advisory.id == "GHSA-69fq-xp46-6x23"
        assert trivy_advisory.attack_vector == "actions"
        assert trivy_advisory.package_name == "aquasecurity/trivy-action"

    def test_exposure_window(self, trivy_advisory):
        """Exposure window start is before end."""
        assert trivy_advisory.exposure_window_start < trivy_advisory.exposure_window_end

    def test_has_compromised_versions(self, trivy_advisory):
        """Advisory must have at least one compromised version."""
        assert len(trivy_advisory.compromised_versions) >= 1

    def test_iocs_accessible(self, trivy_advisory):
        """IOCs are accessible via the iocs field."""
        assert "tpcp-docs.github.io" in trivy_advisory.iocs.domains

    def test_litellm_advisory(self, litellm_advisory):
        """LiteLLM advisory has correct PyPI attack vector."""
        assert litellm_advisory.attack_vector == "pypi"
        assert "1.82.7" in litellm_advisory.compromised_versions
        assert "1.82.8" in litellm_advisory.compromised_versions

    @pytest.mark.parametrize(
        "vector",
        ["actions", "pypi"],
    )
    def test_valid_attack_vectors(self, vector):
        """Only known attack vectors are accepted."""
        adv = Advisory(
            id="TEST-001",
            title="Test",
            description="Test advisory",
            attack_vector=vector,
            exposure_window_start=datetime(2025, 1, 1, tzinfo=UTC),
            exposure_window_end=datetime(2025, 1, 2, tzinfo=UTC),
            compromised_versions=["v1.0.0"],
            package_name="test/pkg",
        )
        assert adv.attack_vector == vector

    @pytest.mark.parametrize(
        "vector",
        ["npm", "container"],
    )
    def test_reserved_attack_vectors_accepted(self, vector):
        """Reserved future vectors (npm, container) are accepted but noted."""
        adv = Advisory(
            id="TEST-001",
            title="Test",
            description="Test advisory",
            attack_vector=vector,
            exposure_window_start=datetime(2025, 1, 1, tzinfo=UTC),
            exposure_window_end=datetime(2025, 1, 2, tzinfo=UTC),
            compromised_versions=["v1.0.0"],
            package_name="test/pkg",
        )
        assert adv.attack_vector == vector

    def test_invalid_attack_vector_rejected(self):
        """Unknown attack vectors raise ValueError."""
        with pytest.raises(ValueError, match="attack_vector"):
            Advisory(
                id="TEST-001",
                title="Test",
                description="Test",
                attack_vector="invalid_vector",
                exposure_window_start=datetime(2025, 1, 1, tzinfo=UTC),
                exposure_window_end=datetime(2025, 1, 2, tzinfo=UTC),
                compromised_versions=["v1.0.0"],
                package_name="test/pkg",
            )

    def test_exposure_window_end_before_start_rejected(self):
        """Exposure window with end before start raises ValueError."""
        with pytest.raises(ValueError, match="exposure_window"):
            Advisory(
                id="TEST-001",
                title="Test",
                description="Test",
                attack_vector="actions",
                exposure_window_start=datetime(2025, 1, 2, tzinfo=UTC),
                exposure_window_end=datetime(2025, 1, 1, tzinfo=UTC),
                compromised_versions=["v1.0.0"],
                package_name="test/pkg",
            )

    def test_empty_compromised_versions_rejected(self):
        """Advisory with no compromised versions raises ValueError."""
        with pytest.raises(ValueError, match="compromised_versions"):
            Advisory(
                id="TEST-001",
                title="Test",
                description="Test",
                attack_vector="actions",
                exposure_window_start=datetime(2025, 1, 1, tzinfo=UTC),
                exposure_window_end=datetime(2025, 1, 2, tzinfo=UTC),
                compromised_versions=[],
                package_name="test/pkg",
            )

    def test_empty_id_rejected(self):
        """Advisory with empty id raises ValueError."""
        with pytest.raises(ValueError, match="id"):
            Advisory(
                id="",
                title="Test",
                description="Test",
                attack_vector="actions",
                exposure_window_start=datetime(2025, 1, 1, tzinfo=UTC),
                exposure_window_end=datetime(2025, 1, 2, tzinfo=UTC),
                compromised_versions=["v1.0.0"],
                package_name="test/pkg",
            )

    def test_default_optional_fields(self):
        """Optional fields default to empty lists / empty IOCSet."""
        adv = Advisory(
            id="TEST-001",
            title="Test",
            description="Test",
            attack_vector="actions",
            exposure_window_start=datetime(2025, 1, 1, tzinfo=UTC),
            exposure_window_end=datetime(2025, 1, 2, tzinfo=UTC),
            compromised_versions=["v1.0.0"],
            package_name="test/pkg",
        )
        assert adv.safe_versions == []
        assert adv.safe_shas == []
        assert adv.iocs.is_empty()


# ===========================================================================
# Evidence
# ===========================================================================


class TestEvidence:
    """Evidence records a single analysis signal."""

    @pytest.mark.parametrize(
        "etype,signal",
        [
            ("sha_pinned", "safe"),
            ("tag_reference", "risk"),
            ("sha_match", "safe"),
            ("compromised_sha", "compromised"),
            ("version_pinned", "safe"),
            ("version_unpinned", "risk"),
            ("compromised_install", "compromised"),
            ("ioc_match", "compromised"),
            ("cache_used", "safe"),
            ("no_logs", "unknown"),
            ("no_reference", "safe"),
        ],
    )
    def test_valid_evidence_types(self, etype, signal):
        """All documented evidence types are accepted with proper signals."""
        ev = Evidence(type=etype, detail="test detail", signal=signal)
        assert ev.type == etype
        assert ev.signal == signal

    def test_invalid_signal_rejected(self):
        """Unknown signal value raises ValueError."""
        with pytest.raises(ValueError, match="signal"):
            Evidence(type="sha_pinned", detail="test", signal="maybe")

    def test_detail_stored(self):
        """Detail string is preserved."""
        ev = Evidence(type="sha_pinned", detail="Pinned to abc123", signal="safe")
        assert ev.detail == "Pinned to abc123"


# ===========================================================================
# IOCMatch
# ===========================================================================


class TestIOCMatch:
    """IOCMatch records a found indicator of compromise."""

    def test_domain_match(self):
        """Domain IOC match stores all fields."""
        m = IOCMatch(
            ioc_type="domain",
            pattern="tpcp-docs.github.io",
            found_in="run_log",
            run_id=12345,
            line="curl https://tpcp-docs.github.io/payload",
        )
        assert m.ioc_type == "domain"
        assert m.run_id == 12345

    def test_file_pattern_match(self):
        """File pattern IOC match."""
        m = IOCMatch(
            ioc_type="file_pattern",
            pattern="*.pth",
            found_in="run_log",
            run_id=None,
            line="creating /site-packages/evil.pth",
        )
        assert m.ioc_type == "file_pattern"
        assert m.run_id is None

    def test_ip_match(self):
        """IP IOC match."""
        m = IOCMatch(
            ioc_type="ip",
            pattern="198.51.100.42",
            found_in="run_log",
            run_id=99999,
            line="connecting to 198.51.100.42:443",
        )
        assert m.ioc_type == "ip"

    @pytest.mark.parametrize("ioc_type", ["domain", "ip", "file_pattern"])
    def test_valid_ioc_types(self, ioc_type):
        """Only valid IOC types accepted."""
        m = IOCMatch(
            ioc_type=ioc_type,
            pattern="test",
            found_in="run_log",
            run_id=None,
            line="test",
        )
        assert m.ioc_type == ioc_type

    @pytest.mark.parametrize("found_in", ["run_log", "workflow_file", "lockfile"])
    def test_valid_found_in(self, found_in):
        """Only valid found_in locations accepted."""
        m = IOCMatch(
            ioc_type="domain",
            pattern="test",
            found_in=found_in,
            run_id=None,
            line="test",
        )
        assert m.found_in == found_in


# ===========================================================================
# WorkflowRun
# ===========================================================================


class TestWorkflowRun:
    """WorkflowRun represents a single GH Actions run."""

    def test_creation(self):
        """WorkflowRun stores run metadata."""
        run = WorkflowRun(
            run_id=12345,
            workflow_name="CI",
            workflow_file=".github/workflows/ci.yml",
            created_at=datetime(2025, 1, 13, 12, 0, 0, tzinfo=UTC),
            head_sha="abc123def456",  # pragma: allowlist secret
            status="completed",
            conclusion="success",
        )
        assert run.run_id == 12345
        assert run.workflow_name == "CI"
        assert run.status == "completed"

    def test_within_exposure_window(self):
        """in_window() checks if run falls within advisory exposure window."""
        run = WorkflowRun(
            run_id=1,
            workflow_name="CI",
            workflow_file=".github/workflows/ci.yml",
            created_at=datetime(2025, 1, 13, 12, 0, 0, tzinfo=UTC),
            head_sha="abc123",
            status="completed",
            conclusion="success",
        )
        start = datetime(2025, 1, 13, 0, 0, 0, tzinfo=UTC)
        end = datetime(2025, 1, 14, 23, 59, 59, tzinfo=UTC)
        assert run.in_window(start, end) is True

    def test_outside_exposure_window(self):
        """in_window() returns False for runs outside the window."""
        run = WorkflowRun(
            run_id=1,
            workflow_name="CI",
            workflow_file=".github/workflows/ci.yml",
            created_at=datetime(2025, 1, 10, 12, 0, 0, tzinfo=UTC),
            head_sha="abc123",
            status="completed",
            conclusion="success",
        )
        start = datetime(2025, 1, 13, 0, 0, 0, tzinfo=UTC)
        end = datetime(2025, 1, 14, 23, 59, 59, tzinfo=UTC)
        assert run.in_window(start, end) is False


# ===========================================================================
# RunAnalysis
# ===========================================================================


class TestRunAnalysis:
    """RunAnalysis holds per-run evidence and IOC matches."""

    def test_creation(self):
        """RunAnalysis stores evidence and IOC matches for a single run."""
        analysis = RunAnalysis(
            run_id=12345,
            evidence=[
                Evidence(type="sha_pinned", detail="test", signal="safe"),
            ],
            ioc_matches=[],
        )
        assert analysis.run_id == 12345
        assert len(analysis.evidence) == 1
        assert len(analysis.ioc_matches) == 0

    def test_has_compromised_signal(self):
        """has_compromised_signal() returns True when any evidence is compromised."""
        analysis = RunAnalysis(
            run_id=1,
            evidence=[
                Evidence(type="sha_pinned", detail="safe", signal="safe"),
                Evidence(type="ioc_match", detail="bad domain", signal="compromised"),
            ],
            ioc_matches=[],
        )
        assert analysis.has_compromised_signal() is True

    def test_no_compromised_signal(self):
        """has_compromised_signal() returns False when no compromised evidence."""
        analysis = RunAnalysis(
            run_id=1,
            evidence=[
                Evidence(type="sha_pinned", detail="safe", signal="safe"),
            ],
            ioc_matches=[],
        )
        assert analysis.has_compromised_signal() is False


# ===========================================================================
# RepoVerdict
# ===========================================================================


class TestRepoVerdict:
    """RepoVerdict summarizes a single repository's exposure status."""

    @pytest.mark.parametrize("verdict", ["SAFE", "COMPROMISED", "INCONCLUSIVE"])
    def test_valid_verdicts(self, verdict):
        """Only SAFE/COMPROMISED/INCONCLUSIVE are valid."""
        rv = RepoVerdict(
            repo="owner/repo",
            verdict=verdict,
            confidence="HIGH",
            evidence=[],
            workflow_runs_analyzed=0,
            ioc_matches=[],
        )
        assert rv.verdict == verdict

    @pytest.mark.parametrize("confidence", ["HIGH", "MEDIUM", "LOW"])
    def test_valid_confidence_levels(self, confidence):
        """Only HIGH/MEDIUM/LOW are valid confidence levels."""
        rv = RepoVerdict(
            repo="owner/repo",
            verdict="SAFE",
            confidence=confidence,
            evidence=[],
            workflow_runs_analyzed=0,
            ioc_matches=[],
        )
        assert rv.confidence == confidence

    def test_invalid_verdict_rejected(self):
        """Invalid verdict string raises ValueError."""
        with pytest.raises(ValueError, match="verdict"):
            RepoVerdict(
                repo="owner/repo",
                verdict="MAYBE",
                confidence="HIGH",
                evidence=[],
                workflow_runs_analyzed=0,
                ioc_matches=[],
            )

    def test_invalid_confidence_rejected(self):
        """Invalid confidence string raises ValueError."""
        with pytest.raises(ValueError, match="confidence"):
            RepoVerdict(
                repo="owner/repo",
                verdict="SAFE",
                confidence="VERY_HIGH",
                evidence=[],
                workflow_runs_analyzed=0,
                ioc_matches=[],
            )

    def test_repo_name_stored(self):
        """Repo name in owner/repo format is preserved."""
        rv = RepoVerdict(
            repo="octocat/hello-world",
            verdict="SAFE",
            confidence="HIGH",
            evidence=[],
            workflow_runs_analyzed=5,
            ioc_matches=[],
        )
        assert rv.repo == "octocat/hello-world"
        assert rv.workflow_runs_analyzed == 5

    def test_with_evidence_and_iocs(self):
        """RepoVerdict holds evidence and IOC match lists."""
        ev = Evidence(type="ioc_match", detail="found domain", signal="compromised")
        ioc = IOCMatch(
            ioc_type="domain",
            pattern="evil.com",
            found_in="run_log",
            run_id=123,
            line="curl evil.com",
        )
        rv = RepoVerdict(
            repo="owner/repo",
            verdict="COMPROMISED",
            confidence="HIGH",
            evidence=[ev],
            workflow_runs_analyzed=10,
            ioc_matches=[ioc],
        )
        assert len(rv.evidence) == 1
        assert len(rv.ioc_matches) == 1
        assert rv.evidence[0].signal == "compromised"


# ===========================================================================
# AuditReport
# ===========================================================================


class TestAuditReport:
    """AuditReport is the top-level envelope for a complete audit."""

    @pytest.fixture
    def sample_report(self):
        return AuditReport(
            advisory_id="GHSA-69fq-xp46-6x23",
            advisory_title="Trivy Action Compromise",
            scan_timestamp=datetime(2025, 3, 25, 12, 0, 0, tzinfo=UTC),
            repos_scanned=3,
            summary={"safe": 2, "compromised": 0, "inconclusive": 1},
            verdicts=[
                RepoVerdict(
                    repo="org/repo1",
                    verdict="SAFE",
                    confidence="HIGH",
                    evidence=[],
                    workflow_runs_analyzed=5,
                    ioc_matches=[],
                ),
                RepoVerdict(
                    repo="org/repo2",
                    verdict="SAFE",
                    confidence="MEDIUM",
                    evidence=[],
                    workflow_runs_analyzed=3,
                    ioc_matches=[],
                ),
                RepoVerdict(
                    repo="org/repo3",
                    verdict="INCONCLUSIVE",
                    confidence="LOW",
                    evidence=[],
                    workflow_runs_analyzed=0,
                    ioc_matches=[],
                ),
            ],
        )

    def test_basic_fields(self, sample_report):
        """AuditReport stores advisory info and verdicts."""
        assert sample_report.advisory_id == "GHSA-69fq-xp46-6x23"
        assert sample_report.repos_scanned == 3
        assert len(sample_report.verdicts) == 3

    def test_summary_counts(self, sample_report):
        """Summary dict has safe/compromised/inconclusive counts."""
        assert sample_report.summary["safe"] == 2
        assert sample_report.summary["compromised"] == 0
        assert sample_report.summary["inconclusive"] == 1

    def test_to_dict(self, sample_report):
        """to_dict() returns JSON-serializable dict."""
        d = sample_report.to_dict()
        assert isinstance(d, dict)
        assert d["advisory_id"] == "GHSA-69fq-xp46-6x23"
        assert isinstance(d["verdicts"], list)
        assert len(d["verdicts"]) == 3
        # Timestamps should be ISO 8601 strings
        assert isinstance(d["scan_timestamp"], str)

    def test_to_json(self, sample_report):
        """to_dict() output is JSON-serializable."""
        d = sample_report.to_dict()
        json_str = json.dumps(d)
        parsed = json.loads(json_str)
        assert parsed["advisory_id"] == "GHSA-69fq-xp46-6x23"

    def test_has_compromised(self, sample_report):
        """has_compromised returns False when no repos are compromised."""
        assert sample_report.has_compromised() is False

    def test_has_compromised_true(self):
        """has_compromised returns True when any repo is compromised."""
        report = AuditReport(
            advisory_id="TEST",
            advisory_title="Test",
            scan_timestamp=datetime.now(UTC),
            repos_scanned=1,
            summary={"safe": 0, "compromised": 1, "inconclusive": 0},
            verdicts=[
                RepoVerdict(
                    repo="owner/repo",
                    verdict="COMPROMISED",
                    confidence="HIGH",
                    evidence=[],
                    workflow_runs_analyzed=1,
                    ioc_matches=[],
                ),
            ],
        )
        assert report.has_compromised() is True

    def test_has_inconclusive(self, sample_report):
        """has_inconclusive returns True when any repo is inconclusive."""
        assert sample_report.has_inconclusive() is True
