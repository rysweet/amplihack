"""
Integration tests — 5-Step Audit Workflow
TDD: Tests define end-to-end workflow behavior from SKILL.md §5-Step Audit Workflow.
All tests FAIL until supply_chain_audit.audit is implemented.
"""

from supply_chain_audit.audit import run_audit


class TestStep1ScopeDetection:
    """Step 1: detect active ecosystems; annotate skipped ones."""

    def test_scope_detection_result_in_report_header(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("requests==2.31.0\n")
        result = run_audit(str(tmp_path), scope="all")
        report = result.render_report()
        assert "Python" in report or "python" in report
        # Skipped dimensions must be listed
        assert "Skipped" in report or "skipped" in report

    def test_gha_not_detected_when_no_workflows(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("requests==2.31.0\n")
        result = run_audit(str(tmp_path), scope="all")
        assert 1 not in result.active_dimensions
        assert 1 in result.skipped_dimensions

    def test_active_and_skipped_dimensions_partition_1_to_12(self, tmp_path):
        """active + skipped must together equal dimensions 1-12."""
        result = run_audit(str(tmp_path), scope="all")
        all_dims = set(result.active_dimensions) | set(result.skipped_dimensions)
        assert all_dims == set(range(1, 13))


class TestStep2StaticAnalysis:
    """Step 2: run dimension-specific checks and collect findings with file:line."""

    def test_every_finding_has_file_and_line(self, tmp_path):
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - uses: actions/checkout@v4\n"
        )
        result = run_audit(str(tmp_path), scope="gha")
        for finding in result.findings:
            assert finding.file is not None and finding.file != ""
            assert isinstance(finding.line, int)
            assert finding.line >= 0

    def test_file_paths_are_relative_posix(self, tmp_path):
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - uses: actions/checkout@v4\n"
        )
        result = run_audit(str(tmp_path), scope="gha")
        for finding in result.findings:
            # Must be relative (not start with /)
            assert not finding.file.startswith("/"), f"Absolute path in finding: {finding.file}"
            # Must use forward slashes
            assert "\\" not in finding.file, f"Windows path separator in finding: {finding.file}"

    def test_every_finding_has_current_value_and_expected_value(self, tmp_path):
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - uses: actions/checkout@v4\n"
        )
        result = run_audit(str(tmp_path), scope="gha")
        for finding in result.findings:
            assert finding.current_value and len(finding.current_value) > 0
            assert finding.expected_value and len(finding.expected_value) > 0


class TestStep3SeverityScoring:
    """Step 3: map findings to CVSS-aligned severity bands."""

    def test_severity_ordering_critical_high_medium_info(self, tmp_path):
        """All findings have valid severity values."""
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push, pull_request_target]\njobs:\n  test:\n"
            "    runs-on: ubuntu-latest\n    steps:\n"
            "      - uses: actions/checkout@v4\n"
            '      - run: echo "${{ secrets.TOKEN }}"\n'
        )
        result = run_audit(str(tmp_path), scope="gha")
        valid_severities = {"Critical", "High", "Medium", "Info"}
        for finding in result.findings:
            assert finding.severity in valid_severities

    def test_pull_request_target_elevates_to_critical(self, tmp_path):
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push, pull_request_target]\njobs:\n  test:\n"
            "    runs-on: ubuntu-latest\n    steps:\n"
            "      - uses: actions/checkout@v4\n"
        )
        result = run_audit(str(tmp_path), scope="gha")
        assert any(f.severity == "Critical" for f in result.findings)

    def test_min_severity_filter_suppresses_lower_findings(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("requests==2.31.0\n")
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - uses: actions/checkout@v4\n"
        )
        result = run_audit(str(tmp_path), scope="all", min_severity="High")
        # No Medium or Info findings should appear
        for finding in result.findings:
            assert finding.severity in ("Critical", "High")


class TestStep4ReportGeneration:
    """Step 4: produce structured markdown report per report schema."""

    def test_report_has_required_header_fields(self, tmp_path):
        result = run_audit(str(tmp_path), scope="all")
        report = result.render_report()
        assert "Supply Chain Audit Report" in report
        assert "Date" in report
        assert "Scope" in report
        assert "Skipped" in report

    def test_report_has_summary_table(self, tmp_path):
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - uses: actions/checkout@v4\n"
        )
        result = run_audit(str(tmp_path), scope="gha")
        report = result.render_report()
        # Summary table must show severity counts
        assert "Critical" in report
        assert "High" in report
        assert "Medium" in report
        assert "Info" in report

    def test_findings_ordered_critical_first(self, tmp_path):
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push, pull_request_target]\njobs:\n  test:\n"
            "    runs-on: ubuntu-latest\n    steps:\n"
            "      - uses: actions/checkout@v4\n"
        )
        (tmp_path / "requirements.txt").write_text("requests==2.31.0\n")
        result = run_audit(str(tmp_path), scope="all")
        report = result.render_report()
        # Critical must appear before High in report
        if "CRITICAL" in report and "HIGH" in report:
            assert report.index("CRITICAL") < report.index("HIGH")

    def test_report_includes_slsa_readiness_section(self, tmp_path):
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo hello\n"
        )
        result = run_audit(str(tmp_path), scope="gha")
        report = result.render_report()
        assert "SLSA" in report

    def test_report_includes_next_steps_section(self, tmp_path):
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - uses: actions/checkout@v4\n"
        )
        result = run_audit(str(tmp_path), scope="gha")
        report = result.render_report()
        assert "Next Steps" in report or "Recommended" in report

    def test_empty_report_lists_all_checked_and_skipped_dimensions(self, tmp_path):
        """Empty report (no findings) must show dimensions checked vs skipped."""
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        # Clean workflow — pinned SHA, permissions set
        wf.write_text(
            "name: CI\non: [push]\npermissions: read-all\njobs:\n  build:\n"
            "    runs-on: ubuntu-latest\n    steps:\n"
            "      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # v4.2.2\n"
        )
        result = run_audit(str(tmp_path), scope="gha")
        report = result.render_report()
        # Empty report must still show dimension status table
        assert "Checked" in report or "checked" in report
        assert "Skipped" in report or "skipped" in report

    def test_finding_ids_follow_severity_nnn_format(self, tmp_path):
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push, pull_request_target]\njobs:\n  test:\n"
            "    runs-on: ubuntu-latest\n    steps:\n"
            "      - uses: actions/checkout@v4\n"
        )
        result = run_audit(str(tmp_path), scope="gha")
        import re

        for finding in result.findings:
            assert re.match(r"^(CRITICAL|HIGH|MEDIUM|INFO)-\d{3}$", finding.id), (
                f"Finding ID does not match {{SEVERITY}}-{{NNN}}: {finding.id}"
            )

    def test_finding_ids_unique_within_report(self, tmp_path):
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - uses: actions/checkout@v4\n"
            "      - uses: actions/setup-python@v5\n"
            "      - uses: actions/setup-node@v4\n"
        )
        result = run_audit(str(tmp_path), scope="gha")
        ids = [f.id for f in result.findings]
        assert len(ids) == len(set(ids)), f"Duplicate finding IDs: {ids}"


class TestStep5RemediationPrioritization:
    """Step 5: remediation order — Critical first, then High, then delegate."""

    def test_next_steps_delegates_lock_files_to_dependency_resolver(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("requests==2.31.0\n")
        result = run_audit(str(tmp_path), scope="python")
        report = result.render_report()
        assert "dependency-resolver" in report

    def test_next_steps_recommends_pre_commit_hooks(self, tmp_path):
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - uses: actions/checkout@v4\n"
        )
        result = run_audit(str(tmp_path), scope="gha")
        report = result.render_report()
        assert "pre-commit" in report or "pre_commit" in report


class TestInterSkillHandoffs:
    """Handoff messages must use verbatim templates from contracts.md."""

    def test_dependency_resolver_handoff_template_fields(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("requests==2.31.0\n")
        result = run_audit(str(tmp_path), scope="python")
        handoff = result.get_handoff("dependency-resolver")
        assert handoff is not None
        assert "Ecosystems with lock file issues" in handoff
        assert "CI validation commands" in handoff

    def test_pre_commit_manager_handoff_template_fields(self, tmp_path):
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - uses: actions/checkout@v4\n"
        )
        result = run_audit(str(tmp_path), scope="gha")
        handoff = result.get_handoff("pre-commit-manager")
        assert handoff is not None
        assert "Hooks to install" in handoff
        assert "Findings this would have prevented" in handoff

    def test_cybersecurity_analyst_handoff_includes_posture_summary(self, tmp_path):
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push, pull_request_target]\njobs:\n  test:\n"
            "    runs-on: ubuntu-latest\n    steps:\n"
            "      - uses: actions/checkout@v4\n"
        )
        result = run_audit(str(tmp_path), scope="gha")
        handoff = result.get_handoff("cybersecurity-analyst")
        # Only generated when runtime concerns are detected
        if handoff:
            assert "Critical:" in handoff
            assert "High:" in handoff

    def test_silent_degradation_handoff_for_continue_on_error(self, tmp_path):
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\npermissions: read-all\njobs:\n  build:\n"
            "    runs-on: ubuntu-latest\n    steps:\n"
            "      - uses: some/security-scan@<sha>  # v1\n"
            "        continue-on-error: true\n"
        )
        result = run_audit(str(tmp_path), scope="gha")
        handoff = result.get_handoff("silent-degradation-audit")
        if handoff:  # Only if silent degradation detected
            assert "continue-on-error" in handoff
            assert "security gates" in handoff.lower() or "enforcing" in handoff.lower()
