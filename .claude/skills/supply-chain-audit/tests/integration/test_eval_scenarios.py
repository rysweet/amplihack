"""
Integration tests — Evaluation Scenarios (from eval-scenarios.md)
TDD: Tests define the 3 graded validation scenarios. FAIL until implemented.

Scenario A: GitHub Actions Monorepo (GHA + Python + Node) — 7 planted findings
Scenario B: Containerized Go Service (Containers + Go + Credentials) — 5 findings
Scenario C: .NET + Rust Mixed Repo (.NET + Rust + SLSA) — 6 findings
"""

import shutil
from pathlib import Path

import pytest
from supply_chain_audit.audit import run_audit

FIXTURES_ROOT = Path(__file__).parent.parent / "fixtures"


def copy_fixture_as_repo(src_fixture_name: str, tmp_path: Path) -> Path:
    """Copy a fixture directory into a temp path that simulates a repo root."""
    src = FIXTURES_ROOT / src_fixture_name
    dst = tmp_path / src_fixture_name
    shutil.copytree(src, dst)
    # Rename 'workflows' -> '.github/workflows' to simulate real repo layout
    wf_src = dst / "workflows"
    if wf_src.exists():
        gha_dir = dst / ".github" / "workflows"
        gha_dir.parent.mkdir(parents=True, exist_ok=True)
        wf_src.rename(gha_dir)
    return dst


# ─── Scenario A ─────────────────────────────────────────────────────────────


class TestScenarioA_GHAPythonNode:
    """
    Scenario A: GitHub Actions Monorepo
    Expected: 2 Critical, 3 High, 2 Medium (7 total)
    FAIL criteria: missing F1, F2, F3 (Critical) or F4 (High in requirements.txt)
    """

    @pytest.fixture
    def scenario_a(self, tmp_path):
        return copy_fixture_as_repo("scenario_a", tmp_path)

    def test_scenario_a_detects_f1_unpinned_action_critical(self, scenario_a):
        """F1: pull_request_target + unpinned action = Critical (Dim 1)."""
        result = run_audit(str(scenario_a), scope="all")
        critical = [f for f in result.findings if f.severity == "Critical"]
        f1 = [f for f in critical if f.dimension == 1 and "checkout@v4" in f.current_value]
        assert len(f1) >= 1, "F1 not detected: unpinned action with pull_request_target"

    def test_scenario_a_detects_f2_pull_request_target_no_permissions(self, scenario_a):
        """F2: pull_request_target without permissions:read-all = Critical (Dim 2)."""
        result = run_audit(str(scenario_a), scope="all")
        critical = [f for f in result.findings if f.severity == "Critical"]
        f2 = [f for f in critical if f.dimension == 2 and "pull_request_target" in f.current_value]
        assert len(f2) >= 1, "F2 not detected: pull_request_target without permissions"

    def test_scenario_a_detects_f3_secret_echoed_to_log(self, scenario_a):
        """F3: echo "${{ secrets.API_TOKEN }}" = Critical (Dim 3)."""
        result = run_audit(str(scenario_a), scope="all")
        critical = [f for f in result.findings if f.severity == "Critical"]
        f3 = [f for f in critical if f.dimension == 3 and "secret" in f.rationale.lower()]
        assert len(f3) >= 1, "F3 not detected: secret echoed to log"

    def test_scenario_a_detects_f4_no_hash_pinning_requirements(self, scenario_a):
        """F4: requirements.txt without --require-hashes = High (Dim 8)."""
        result = run_audit(str(scenario_a), scope="all")
        high = [f for f in result.findings if f.severity == "High"]
        f4 = [f for f in high if f.dimension == 8 and "requirements.txt" in f.file]
        assert len(f4) >= 1, "F4 not detected: missing hash pinning in requirements.txt"

    def test_scenario_a_detects_f5_no_lock_file(self, scenario_a):
        """F5: No package-lock.json detected = High (Dim 10, file-level)."""
        result = run_audit(str(scenario_a), scope="all")
        high = [f for f in result.findings if f.severity == "High"]
        f5 = [f for f in high if f.dimension == 10 and f.line == 0]
        assert len(f5) >= 1, "F5 not detected: missing package-lock.json"

    def test_scenario_a_detects_f6_unversioned_npx(self, scenario_a):
        """F6: npx webpack without version pin = High (Dim 10)."""
        result = run_audit(str(scenario_a), scope="all")
        high = [f for f in result.findings if f.severity == "High"]
        f6 = [f for f in high if f.dimension == 10 and "npx" in f.current_value.lower()]
        assert len(f6) >= 1, "F6 not detected: unversioned npx"

    def test_scenario_a_detects_f7_pip_install_without_require_hashes(self, scenario_a):
        """F7: pip install -r requirements.txt without --require-hashes = Medium (Dim 8)."""
        result = run_audit(str(scenario_a), scope="all")
        medium = [f for f in result.findings if f.severity == "Medium"]
        f7 = [
            f for f in medium if f.dimension == 8 and "require-hashes" in (f.expected_value or "")
        ]
        assert len(f7) >= 1, "F7 not detected: pip install without --require-hashes"

    def test_scenario_a_severity_distribution(self, scenario_a):
        """Expected: 2 Critical, 3 High, 2 Medium (pass if ≥ 5 of 7 found)."""
        result = run_audit(str(scenario_a), scope="all")
        counts = dict.fromkeys(("Critical", "High", "Medium", "Info"), 0)
        for f in result.findings:
            counts[f.severity] += 1
        # Must find all Critical findings (F1, F2, F3)
        assert counts["Critical"] >= 2, f"Expected ≥2 Critical, got {counts['Critical']}"
        # Must find High findings (F4, F5, F6)
        assert counts["High"] >= 2, f"Expected ≥2 High, got {counts['High']}"

    def test_scenario_a_total_findings_at_least_5(self, scenario_a):
        """PARTIAL PASS threshold: ≥5 findings."""
        result = run_audit(str(scenario_a), scope="all")
        assert len(result.findings) >= 5, f"Expected ≥5 findings, got {len(result.findings)}"

    def test_scenario_a_all_findings_offline_detectable(self, scenario_a):
        """All 7 Scenario A findings are pattern-detectable without network tools."""
        result = run_audit(str(scenario_a), scope="all")
        non_offline = [
            f
            for f in result.findings
            if not f.offline_detectable and f.severity in ("Critical", "High", "Medium")
        ]
        assert non_offline == [], f"Non-offline findings in Scenario A: {non_offline}"


# ─── Scenario B ─────────────────────────────────────────────────────────────


class TestScenarioB_ContainerGoCredentials:
    """
    Scenario B: Containerized Go Service
    Expected: 1 Critical, 3 High, 1 Medium (5 total)
    FAIL criteria: missing F3 (Critical: :latest) or F4 (High: static AWS creds)
    """

    @pytest.fixture
    def scenario_b(self, tmp_path):
        return copy_fixture_as_repo("scenario_b", tmp_path)

    def test_scenario_b_detects_f1_semver_golang_base(self, scenario_b):
        """F1: golang:1.22-alpine uses semver tag = High (Dim 5)."""
        result = run_audit(str(scenario_b), scope="all")
        high = [f for f in result.findings if f.severity == "High"]
        f1 = [f for f in high if f.dimension == 5 and "golang:1.22-alpine" in f.current_value]
        assert len(f1) >= 1, "F1 not detected: golang semver tag"

    def test_scenario_b_detects_f2_no_user_instruction(self, scenario_b):
        """F2: Final stage runs as root; no USER instruction = High (Dim 12)."""
        result = run_audit(str(scenario_b), scope="all")
        high = [f for f in result.findings if f.severity == "High"]
        f2 = [f for f in high if f.dimension == 12]
        assert len(f2) >= 1, "F2 not detected: runs as root, no USER instruction"

    def test_scenario_b_detects_f3_latest_tag_critical(self, scenario_b):
        """F3: alpine:latest = Critical (Dim 5). FAIL if missed."""
        result = run_audit(str(scenario_b), scope="all")
        critical = [f for f in result.findings if f.severity == "Critical"]
        f3 = [f for f in critical if f.dimension == 5 and ":latest" in f.current_value]
        assert len(f3) >= 1, "F3 MUST be detected: alpine:latest is Critical"

    def test_scenario_b_detects_f4_static_aws_credentials(self, scenario_b):
        """F4: Static AWS credentials; OIDC available = High (Dim 6). FAIL if missed."""
        result = run_audit(str(scenario_b), scope="all")
        high = [f for f in result.findings if f.severity == "High"]
        f4 = [f for f in high if f.dimension == 6 and "AWS" in f.current_value.upper()]
        assert len(f4) >= 1, "F4 MUST be detected: static AWS credentials"

    def test_scenario_b_detects_f5_mutable_replace_directive(self, scenario_b):
        """F5: replace directive using mutable branch 'main' = Medium (Dim 11)."""
        result = run_audit(str(scenario_b), scope="all")
        medium = [f for f in result.findings if f.severity == "Medium"]
        f5 = [f for f in medium if f.dimension == 11 and "replace" in f.current_value.lower()]
        assert len(f5) >= 1, "F5 not detected: mutable replace directive"

    def test_scenario_b_severity_distribution(self, scenario_b):
        """Expected: 1 Critical, 3 High, 1 Medium."""
        result = run_audit(str(scenario_b), scope="all")
        counts = dict.fromkeys(("Critical", "High", "Medium", "Info"), 0)
        for f in result.findings:
            counts[f.severity] += 1
        assert counts["Critical"] >= 1
        assert counts["High"] >= 2

    def test_scenario_b_total_findings_at_least_3(self, scenario_b):
        """PARTIAL PASS threshold: F1, F3, F4 detected (minimum 3)."""
        result = run_audit(str(scenario_b), scope="all")
        # At minimum, F3 (Critical) and F4 (High) must be found
        critical = [f for f in result.findings if f.severity == "Critical"]
        high = [f for f in result.findings if f.severity == "High"]
        assert len(critical) >= 1 and len(high) >= 1, (
            "Must find at least 1 Critical and 1 High finding"
        )


# ─── Scenario C ─────────────────────────────────────────────────────────────


class TestScenarioC_DotNetRustSLSA:
    """
    Scenario C: .NET + Rust Mixed Repo
    Expected: 0 Critical, 4 High, 2 Medium (6 total)
    FAIL criteria: missing F2 (NuGet dependency confusion) or no SLSA assessment
    """

    @pytest.fixture
    def scenario_c(self, tmp_path):
        return copy_fixture_as_repo("scenario_c", tmp_path)

    def test_scenario_c_detects_f1_no_nuget_lock_file(self, scenario_c):
        """F1: No packages.lock.json; no RestoreLockedMode = High (Dim 7)."""
        result = run_audit(str(scenario_c), scope="all")
        high = [f for f in result.findings if f.severity == "High"]
        f1 = [f for f in high if f.dimension == 7 and f.line == 0]
        assert len(f1) >= 1, "F1 not detected: missing NuGet lock file"

    def test_scenario_c_detects_f2_dependency_confusion_risk(self, scenario_c):
        """F2: Internal + public sources without packageSourceMapping = High (Dim 7). FAIL if missed."""
        result = run_audit(str(scenario_c), scope="all")
        high = [f for f in result.findings if f.severity == "High"]
        f2 = [f for f in high if f.dimension == 7 and "NuGet.Config" in f.file]
        assert len(f2) >= 1, "F2 MUST be detected: dependency confusion risk in NuGet.Config"

    def test_scenario_c_detects_f3_cargo_lock_in_gitignore(self, scenario_c):
        """F3: Cargo.lock excluded for binary crate = Medium (Dim 9)."""
        result = run_audit(str(scenario_c), scope="all")
        medium = [f for f in result.findings if f.severity == "Medium"]
        f3 = [f for f in medium if f.dimension == 9 and "Cargo.lock" in (f.current_value or "")]
        assert len(f3) >= 1, "F3 not detected: Cargo.lock in .gitignore for binary"

    def test_scenario_c_detects_f4_checkout_unpinned(self, scenario_c):
        """F4: actions/checkout@v4 — unpinned semver ref = High (Dim 1)."""
        result = run_audit(str(scenario_c), scope="all")
        high = [f for f in result.findings if f.severity == "High"]
        f4 = [f for f in high if f.dimension == 1 and "checkout@v4" in f.current_value]
        assert len(f4) >= 1, "F4 not detected: actions/checkout@v4 unpinned"

    def test_scenario_c_detects_f5_no_permissions_key(self, scenario_c):
        """F5: No permissions key (implicit all) = Medium (Dim 2)."""
        result = run_audit(str(scenario_c), scope="all")
        medium = [f for f in result.findings if f.severity == "Medium"]
        f5 = [f for f in medium if f.dimension == 2]
        assert len(f5) >= 1, "F5 not detected: no permissions key"

    def test_scenario_c_detects_f6_rust_toolchain_mutable_ref(self, scenario_c):
        """F6: dtolnay/rust-toolchain@stable — mutable branch ref = High (Dim 1)."""
        result = run_audit(str(scenario_c), scope="all")
        high = [f for f in result.findings if f.severity == "High"]
        f6 = [f for f in high if f.dimension == 1 and "rust-toolchain@stable" in f.current_value]
        assert len(f6) >= 1, "F6 not detected: dtolnay/rust-toolchain@stable mutable ref"

    def test_scenario_c_no_critical_findings(self, scenario_c):
        """Scenario C has 0 Critical findings by design."""
        result = run_audit(str(scenario_c), scope="all")
        critical = [f for f in result.findings if f.severity == "Critical"]
        assert critical == [], f"Unexpected Critical findings in Scenario C: {critical}"

    def test_scenario_c_slsa_assessment_present(self, scenario_c):
        """SLSA readiness assessment MUST be in the report. FAIL if absent."""
        result = run_audit(str(scenario_c), scope="all")
        report = result.render_report()
        assert "SLSA" in report, "SLSA assessment is mandatory in Scenario C"

    def test_scenario_c_slsa_reports_l1_with_blockers(self, scenario_c):
        """SLSA level should be L1 (scripted build, no provenance)."""
        result = run_audit(str(scenario_c), scope="all")
        report = result.render_report()
        assert "L1" in report, "Expected SLSA L1 assessment"
        # Must identify blockers to L2
        assert "L2" in report or "provenance" in report.lower()

    def test_scenario_c_slsa_flags_unpinned_action_refs(self, scenario_c):
        """SLSA table must report unpinned action refs as a blocker."""
        result = run_audit(str(scenario_c), scope="all")
        slsa = result.get_slsa_assessment()
        assert slsa is not None
        assert not slsa["action_refs_sha_pinned"], "SLSA should detect unpinned action refs"

    def test_scenario_c_severity_distribution(self, scenario_c):
        """Expected: 0 Critical, 4 High, 2 Medium."""
        result = run_audit(str(scenario_c), scope="all")
        counts = dict.fromkeys(("Critical", "High", "Medium", "Info"), 0)
        for f in result.findings:
            counts[f.severity] += 1
        assert counts["Critical"] == 0
        assert counts["High"] >= 3
        assert counts["Medium"] >= 1

    def test_scenario_c_total_findings_at_least_4(self, scenario_c):
        """PARTIAL PASS threshold: 4-5 findings with SLSA present."""
        result = run_audit(str(scenario_c), scope="all")
        assert len(result.findings) >= 4, f"Expected ≥4 findings, got {len(result.findings)}"
