"""
End-to-end tests — Full Audit Execution
TDD: Tests define complete audit pipeline behavior including report format,
accepted-risks suppression, scope filtering, and multi-ecosystem repos.
All tests FAIL until supply_chain_audit is fully implemented.
"""

import re

from supply_chain_audit.audit import run_audit


class TestMinSeverityFiltering:
    """--min-severity suppresses findings below the threshold."""

    def test_min_severity_high_excludes_medium_info(self, tmp_path):
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - uses: actions/checkout@v4\n"
        )
        result_all = run_audit(str(tmp_path), scope="gha", min_severity="Info")
        result_high = run_audit(str(tmp_path), scope="gha", min_severity="High")

        all_findings = len(result_all.findings)
        high_only = len(result_high.findings)
        assert high_only <= all_findings

        for f in result_high.findings:
            assert f.severity in ("Critical", "High")

    def test_min_severity_critical_shows_only_critical(self, tmp_path):
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push, pull_request_target]\njobs:\n  test:\n"
            "    runs-on: ubuntu-latest\n    steps:\n"
            "      - uses: actions/checkout@v4\n"
        )
        result = run_audit(str(tmp_path), scope="gha", min_severity="Critical")
        for f in result.findings:
            assert f.severity == "Critical"

    def test_min_severity_in_report_header(self, tmp_path):
        result = run_audit(str(tmp_path), scope="all", min_severity="High")
        report = result.render_report()
        assert "High" in report


class TestScopeFiltering:
    """--scope restricts which ecosystems and dimensions are checked."""

    def test_scope_gha_only_checks_dims_1_to_4(self, tmp_path):
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - uses: actions/checkout@v4\n"
        )
        (tmp_path / "requirements.txt").write_text("requests==2.31.0\n")
        result = run_audit(str(tmp_path), scope="gha")
        for f in result.findings:
            assert f.dimension in (1, 2, 3, 4), f"Dim {f.dimension} found outside gha scope"

    def test_scope_python_only_checks_dim_8(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("requests==2.31.0\n")
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - uses: actions/checkout@v4\n"
        )
        result = run_audit(str(tmp_path), scope="python")
        for f in result.findings:
            assert f.dimension == 8, f"Dim {f.dimension} found outside python scope"

    def test_scope_comma_separated_multi_scope(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("requests==2.31.0\n")
        (tmp_path / "package.json").write_text('{"name": "app"}\n')
        result = run_audit(str(tmp_path), scope="python,node")
        for f in result.findings:
            assert f.dimension in (8, 10), f"Dim {f.dimension} found outside python,node scope"


class TestReportFormatCompliance:
    """Report must conform to the markdown schema from contracts.md."""

    def test_report_has_supply_chain_audit_report_heading(self, tmp_path):
        result = run_audit(str(tmp_path), scope="all")
        report = result.render_report()
        assert "## Supply Chain Audit Report" in report

    def test_report_date_format_is_iso_8601(self, tmp_path):
        result = run_audit(str(tmp_path), scope="all")
        report = result.render_report()
        # Expect **Date**: YYYY-MM-DD
        date_match = re.search(r"\*\*Date\*\*:\s*(\d{4}-\d{2}-\d{2})", report)
        assert date_match is not None, "Date field not found or not in YYYY-MM-DD format"

    def test_report_tool_availability_field_present(self, tmp_path):
        result = run_audit(str(tmp_path), scope="all")
        report = result.render_report()
        assert "Tool availability" in report or "tool availability" in report.lower()

    def test_finding_format_contains_severity_file_current_expected(self, tmp_path):
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - uses: actions/checkout@v4\n"
        )
        result = run_audit(str(tmp_path), scope="gha")
        report = result.render_report()
        # Each finding block must have all required fields
        if result.findings:
            assert "**Severity**" in report
            assert "**File**" in report
            assert "**Current**" in report
            assert "**Expected**" in report
            assert "**Why**" in report

    def test_file_line_reference_format(self, tmp_path):
        """Findings must reference file:line in the format path/to/file.yml:N."""
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - uses: actions/checkout@v4\n"
        )
        result = run_audit(str(tmp_path), scope="gha")
        report = result.render_report()
        # File:line pattern must appear in findings section
        file_line_pattern = re.search(r"`.+:\d+`", report)
        assert file_line_pattern is not None, "No file:line reference found in report"


class TestPolyglotRepoAudit:
    """Full polyglot repo with all ecosystems active."""

    def test_all_12_dimensions_run_in_polyglot_repo(self, tmp_path):
        # Set up all ecosystems
        wf_dir = tmp_path / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "ci.yml").write_text(
            "name: CI\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
            "    env:\n      TOKEN: ${{ secrets.MY_TOKEN }}\n"
            "    steps:\n      - uses: actions/checkout@v4\n"
        )
        (tmp_path / "Dockerfile").write_text("FROM ubuntu:22.04\n")
        (tmp_path / "requirements.txt").write_text("requests==2.31.0\n")
        (tmp_path / "package.json").write_text('{"name": "app"}\n')
        (tmp_path / "go.mod").write_text("module github.com/org/app\n\ngo 1.22\n")
        (tmp_path / "Cargo.toml").write_text("[package]\nname = 'tool'\nversion = '0.1.0'\n")
        (tmp_path / "App.csproj").write_text('<Project Sdk="Microsoft.NET.Sdk" />\n')

        result = run_audit(str(tmp_path), scope="all")
        # All 12 dimensions should have been attempted
        all_attempted = set(result.active_dimensions) | set(result.skipped_dimensions)
        assert all_attempted == set(range(1, 13))

    def test_polyglot_repo_produces_findings_across_multiple_dimensions(self, tmp_path):
        wf_dir = tmp_path / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "ci.yml").write_text(
            "name: CI\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - uses: actions/checkout@v4\n"
        )
        (tmp_path / "Dockerfile").write_text("FROM ubuntu:latest\n")
        (tmp_path / "requirements.txt").write_text("requests==2.31.0\n")

        result = run_audit(str(tmp_path), scope="all")
        dims_with_findings = {f.dimension for f in result.findings}
        # Must have findings in at least 3 different dimensions
        assert len(dims_with_findings) >= 3


class TestCleanRepoProducesEmptyReport:
    """A properly secured repo produces no findings."""

    def test_clean_gha_workflow_no_findings(self, gha_only_repo):
        result = run_audit(str(gha_only_repo), scope="gha")
        high_or_critical = [f for f in result.findings if f.severity in ("Critical", "High")]
        assert high_or_critical == []

    def test_empty_report_shows_dimensions_checked(self, gha_only_repo):
        result = run_audit(str(gha_only_repo), scope="gha")
        report = result.render_report()
        # Empty report must list what was checked
        assert "Checked" in report or "✅" in report

    def test_empty_report_shows_dimensions_skipped(self, gha_only_repo):
        result = run_audit(str(gha_only_repo), scope="gha")
        report = result.render_report()
        # GHA-only: dims 5, 7, 8, 9, 10, 11, 12 are skipped
        assert "Skipped" in report or "⏭" in report

    def test_empty_report_supply_chain_posture_passing(self, gha_only_repo):
        result = run_audit(str(gha_only_repo), scope="gha")
        report = result.render_report()
        assert "Passing" in report or "passing" in report or "✅" in report


class TestAcceptedRisksSuppressionFlow:
    """End-to-end test of accepted-risks file suppression."""

    def test_accepted_non_critical_finding_appears_as_info(self, tmp_path):
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - uses: actions/checkout@v4\n"
        )
        risk_file = tmp_path / ".supply-chain-accepted-risks.yml"
        risk_file.write_text(
            "- id: 'HIGH-001'\n"
            "  dimension: 1\n"
            "  file: '.github/workflows/ci.yml'\n"
            "  line: 7\n"
            "  rationale: 'Accepted temporarily'\n"
            "  accepted_by: 'security-team'\n"
            "  review_date: '2099-12-31'\n"
        )
        result = run_audit(str(tmp_path), scope="gha")
        accepted = [f for f in result.findings if hasattr(f, "accepted_risk") and f.accepted_risk]
        for f in accepted:
            assert f.severity == "Info", "Accepted non-Critical findings must appear as Info"

    def test_accepted_finding_still_visible_in_report(self, tmp_path):
        """Accepted risks must remain visible for review-date tracking."""
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - uses: actions/checkout@v4\n"
        )
        risk_file = tmp_path / ".supply-chain-accepted-risks.yml"
        risk_file.write_text(
            "- id: 'HIGH-001'\n"
            "  dimension: 1\n"
            "  file: '.github/workflows/ci.yml'\n"
            "  line: 7\n"
            "  rationale: 'Under migration'\n"
            "  accepted_by: 'security-team'\n"
            "  review_date: '2099-12-31'\n"
        )
        result = run_audit(str(tmp_path), scope="gha")
        report = result.render_report()
        assert "ACCEPTED RISK" in report or "accepted" in report.lower()

    def test_accepted_risks_section_shows_review_date(self, tmp_path):
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - uses: actions/checkout@v4\n"
        )
        risk_file = tmp_path / ".supply-chain-accepted-risks.yml"
        risk_file.write_text(
            "- id: 'HIGH-001'\n"
            "  dimension: 1\n"
            "  file: '.github/workflows/ci.yml'\n"
            "  line: 7\n"
            "  rationale: 'Test'\n"
            "  accepted_by: 'team'\n"
            "  review_date: '2099-12-31'\n"
        )
        result = run_audit(str(tmp_path), scope="gha")
        report = result.render_report()
        assert "2099-12-31" in report


class TestSBOMAdvisory:
    """SBOM write advisory must appear before any write to repo."""

    def test_sbom_write_advisory_shown_when_sbom_requested(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("requests==2.31.0\n")
        result = run_audit(str(tmp_path), scope="python", generate_sbom=True)
        messages = result.get_advisory_messages()
        sbom_advisory = [m for m in messages if "SBOM" in m and "advisory" in m.lower()]
        assert len(sbom_advisory) >= 1, "SBOM write advisory must be shown"

    def test_sbom_advisory_mentions_gitignore_recommendation(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("requests==2.31.0\n")
        result = run_audit(str(tmp_path), scope="python", generate_sbom=True)
        messages = result.get_advisory_messages()
        advisory_text = " ".join(messages)
        assert ".gitignore" in advisory_text or "gitignore" in advisory_text.lower()
