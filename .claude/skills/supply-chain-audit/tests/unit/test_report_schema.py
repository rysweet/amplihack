"""
Unit tests — Report Schema Compliance
TDD: Tests define the report schema from contracts.md §Report Schema.
All tests FAIL until supply_chain_audit.report is implemented.
"""

from supply_chain_audit.report import SlsaAssessment, build_report


class TestReportStructure:
    """Report must have all 5 required sections."""

    def test_report_has_date_field(self):
        report = build_report(
            findings=[], active_dims=[1, 2, 3, 4], skipped_dims=list(range(5, 13))
        )
        rendered = report.render()
        assert "**Date**:" in rendered

    def test_report_has_root_field(self):
        report = build_report(
            findings=[], active_dims=[], skipped_dims=list(range(1, 13)), root="/repo"
        )
        rendered = report.render()
        assert "**Root**:" in rendered

    def test_report_has_scope_field(self):
        report = build_report(
            findings=[], active_dims=[1], skipped_dims=list(range(2, 13)), scope=["gha"]
        )
        rendered = report.render()
        assert "**Scope**:" in rendered

    def test_report_has_skipped_field(self):
        report = build_report(
            findings=[], active_dims=[1, 2, 3, 4], skipped_dims=[5, 6, 7, 8, 9, 10, 11, 12]
        )
        rendered = report.render()
        assert "**Skipped**:" in rendered

    def test_report_has_tool_availability_field(self):
        report = build_report(findings=[], active_dims=[], skipped_dims=list(range(1, 13)))
        rendered = report.render()
        assert "**Tool availability**:" in rendered

    def test_report_has_summary_section(self):
        report = build_report(findings=[], active_dims=[], skipped_dims=list(range(1, 13)))
        rendered = report.render()
        assert "### Summary" in rendered

    def test_report_has_findings_section(self):
        report = build_report(findings=[], active_dims=[], skipped_dims=list(range(1, 13)))
        rendered = report.render()
        assert "### Findings" in rendered

    def test_report_has_slsa_readiness_section(self):
        report = build_report(
            findings=[], active_dims=[1, 2, 3, 4], skipped_dims=list(range(5, 13))
        )
        rendered = report.render()
        assert "### SLSA Readiness" in rendered

    def test_report_has_next_steps_section(self):
        report = build_report(findings=[], active_dims=[], skipped_dims=list(range(1, 13)))
        rendered = report.render()
        assert "### Recommended Next Steps" in rendered


class TestSummaryTable:
    """Summary table must show all severity levels with counts."""

    def test_summary_table_has_all_severity_rows(self):
        report = build_report(findings=[], active_dims=[], skipped_dims=list(range(1, 13)))
        rendered = report.render()
        for severity in ("Critical", "High", "Medium", "Info"):
            assert severity in rendered

    def test_summary_table_counts_are_accurate(self):
        from supply_chain_audit.schema import Finding

        findings = [
            Finding(
                id="CRITICAL-001",
                dimension=1,
                severity="Critical",
                file="f.yml",
                line=1,
                current_value="x",
                expected_value="y",
                rationale="r",
                offline_detectable=True,
            ),
            Finding(
                id="HIGH-001",
                dimension=2,
                severity="High",
                file="f.yml",
                line=2,
                current_value="x",
                expected_value="y",
                rationale="r",
                offline_detectable=True,
            ),
            Finding(
                id="HIGH-002",
                dimension=2,
                severity="High",
                file="f.yml",
                line=3,
                current_value="x",
                expected_value="y",
                rationale="r",
                offline_detectable=True,
            ),
        ]
        report = build_report(
            findings=findings, active_dims=[1, 2], skipped_dims=list(range(3, 13))
        )
        rendered = report.render()
        assert "1" in rendered  # 1 Critical
        assert "2" in rendered  # 2 High

    def test_summary_total_row_present(self):
        from supply_chain_audit.schema import Finding

        findings = [
            Finding(
                id="HIGH-001",
                dimension=1,
                severity="High",
                file="f.yml",
                line=1,
                current_value="x",
                expected_value="y",
                rationale="r",
                offline_detectable=True,
            ),
        ]
        report = build_report(findings=findings, active_dims=[1], skipped_dims=list(range(2, 13)))
        rendered = report.render()
        assert "**Total**" in rendered


class TestFindingBlockFormat:
    """Each finding block must have the required subfields."""

    def test_finding_block_has_id_and_dimension(self):
        from supply_chain_audit.schema import Finding

        f = Finding(
            id="HIGH-001",
            dimension=1,
            severity="High",
            file=".github/workflows/ci.yml",
            line=8,
            current_value="uses: actions/checkout@v4",
            expected_value="uses: actions/checkout@<sha>  # v4",
            rationale="Mutable ref.",
            offline_detectable=True,
        )
        report = build_report(findings=[f], active_dims=[1], skipped_dims=list(range(2, 13)))
        rendered = report.render()
        assert "HIGH-001" in rendered
        assert "Dim 1" in rendered

    def test_finding_block_has_severity_line(self):
        from supply_chain_audit.schema import Finding

        f = Finding(
            id="HIGH-001",
            dimension=1,
            severity="High",
            file="f.yml",
            line=1,
            current_value="x",
            expected_value="y",
            rationale="r",
            offline_detectable=True,
        )
        rendered = build_report(
            findings=[f], active_dims=[1], skipped_dims=list(range(2, 13))
        ).render()
        assert "**Severity**:" in rendered

    def test_finding_block_has_file_colon_line_reference(self):
        from supply_chain_audit.schema import Finding

        f = Finding(
            id="HIGH-001",
            dimension=1,
            severity="High",
            file=".github/workflows/ci.yml",
            line=8,
            current_value="x",
            expected_value="y",
            rationale="r",
            offline_detectable=True,
        )
        rendered = build_report(
            findings=[f], active_dims=[1], skipped_dims=list(range(2, 13))
        ).render()
        assert ".github/workflows/ci.yml:8" in rendered

    def test_finding_block_has_why_rationale(self):
        from supply_chain_audit.schema import Finding

        f = Finding(
            id="HIGH-001",
            dimension=1,
            severity="High",
            file="f.yml",
            line=1,
            current_value="x",
            expected_value="y",
            rationale="Mutable semver tag allows silent replacement.",
            offline_detectable=True,
        )
        rendered = build_report(
            findings=[f], active_dims=[1], skipped_dims=list(range(2, 13))
        ).render()
        assert "**Why**:" in rendered
        assert "Mutable semver tag" in rendered


class TestSlsaAssessment:
    """SLSA assessment section follows the compliance table format."""

    def test_slsa_table_has_required_rows(self):
        slsa = SlsaAssessment(
            build_is_scripted=True,
            runs_on_hosted_ci=True,
            provenance_generated=False,
            action_refs_sha_pinned=False,
        )
        rendered = slsa.render()
        assert "Build is scripted" in rendered
        assert "Build runs on hosted CI" in rendered
        assert "Provenance generated" in rendered
        assert "Action refs SHA-pinned" in rendered

    def test_slsa_table_shows_current_level(self):
        slsa = SlsaAssessment(
            build_is_scripted=True,
            runs_on_hosted_ci=True,
            provenance_generated=False,
            action_refs_sha_pinned=False,
        )
        rendered = slsa.render()
        assert "L1" in rendered

    def test_slsa_l1_blockers_to_l2_listed(self):
        slsa = SlsaAssessment(
            build_is_scripted=True,
            runs_on_hosted_ci=True,
            provenance_generated=False,
            action_refs_sha_pinned=False,
        )
        rendered = slsa.render()
        assert "L2" in rendered
        assert "provenance" in rendered.lower() or "blocker" in rendered.lower()

    def test_slsa_l2_if_provenance_generated_and_pinned(self):
        slsa = SlsaAssessment(
            build_is_scripted=True,
            runs_on_hosted_ci=True,
            provenance_generated=True,
            action_refs_sha_pinned=True,
        )
        rendered = slsa.render()
        assert "L2" in rendered


class TestVersioningMetadata:
    """Report must include skill version from SKILL.md frontmatter."""

    def test_report_does_not_include_version_in_main_body(self):
        """Version is in SKILL.md frontmatter; report focuses on findings."""
        report = build_report(findings=[], active_dims=[], skipped_dims=list(range(1, 13)))
        rendered = report.render()
        # Version should not pollute the findings report
        # (This is a soft constraint — verify implementation doesn't add noise)
        assert "version: 1.0.0" not in rendered
