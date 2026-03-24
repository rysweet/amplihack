# File: supply_chain_audit/report.py
"""Report generation — AuditReport, SlsaAssessment, build_report."""

from datetime import date

from .schema import Finding, _sanitize_for_display

_SEVERITY_ORDER = ["Critical", "High", "Medium", "Info"]


class SlsaAssessment:
    """SLSA compliance assessment table."""

    def __init__(
        self,
        build_is_scripted: bool,
        runs_on_hosted_ci: bool,
        provenance_generated: bool,
        action_refs_sha_pinned: bool,
    ):
        self.build_is_scripted = build_is_scripted
        self.runs_on_hosted_ci = runs_on_hosted_ci
        self.provenance_generated = provenance_generated
        self.action_refs_sha_pinned = action_refs_sha_pinned

    @property
    def current_level(self) -> str:
        """Determine current SLSA level based on criteria."""
        if not self.build_is_scripted:
            return "L0"
        if self.runs_on_hosted_ci and self.provenance_generated and self.action_refs_sha_pinned:
            return "L2"
        return "L1"

    def render(self) -> str:
        """Render SLSA compliance table as markdown."""

        def check(b: bool) -> str:
            return "✅" if b else "❌"

        level = self.current_level

        lines = [
            "| Requirement | Status |",
            "|-------------|--------|",
            f"| Build is scripted | {check(self.build_is_scripted)} |",
            f"| Build runs on hosted CI | {check(self.runs_on_hosted_ci)} |",
            f"| Provenance generated | {check(self.provenance_generated)} |",
            f"| Action refs SHA-pinned | {check(self.action_refs_sha_pinned)} |",
            "",
            f"**Current SLSA Level: {level}**",
        ]

        # Add blockers to next level
        if level == "L0":
            lines.append("\n**Blockers to L1:** Implement scripted build in CI.")
        elif level == "L1":
            blockers = []
            if not self.runs_on_hosted_ci:
                blockers.append("Move to hosted CI runner (e.g., ubuntu-latest)")
            if not self.provenance_generated:
                blockers.append(
                    "Add SLSA provenance generation (slsa-framework/slsa-github-generator)"
                )
            if not self.action_refs_sha_pinned:
                blockers.append("Pin all action refs to full SHA (Dim 1 findings)")
            if blockers:
                lines.append("\n**Blockers to L2:** " + "; ".join(blockers))
            lines.append(
                "\n**Blockers to L3:** Add SLSA generator action with OIDC provenance signing."
            )

        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "build_is_scripted": self.build_is_scripted,
            "runs_on_hosted_ci": self.runs_on_hosted_ci,
            "provenance_generated": self.provenance_generated,
            "action_refs_sha_pinned": self.action_refs_sha_pinned,
            "current_level": self.current_level,
        }


class AuditReport:
    """Complete supply chain audit report with all 5 required sections."""

    def __init__(
        self,
        findings: list[Finding],
        active_dims: list[int],
        skipped_dims: list[int],
        skip_reasons: dict[int, str],
        root: str = "",
        scope: list[str] | None = None,
        min_severity: str = "Info",
        slsa: SlsaAssessment | None = None,
        tool_status: dict[str, str] | None = None,
        advisory_messages: list[str] | None = None,
        generate_sbom: bool = False,
        handoffs: dict[str, str] | None = None,
    ):
        self.findings = findings
        self.active_dims = active_dims
        self.skipped_dims = skipped_dims
        self._skip_reasons = skip_reasons
        self.root = root
        self.scope = scope or ["all"]
        self.min_severity = min_severity
        self.slsa = slsa
        self.tool_status = tool_status or {}
        self._advisory_messages: list[str] = advisory_messages or []
        self.generate_sbom = generate_sbom
        self._handoffs: dict[str, str] = handoffs or {}

        if generate_sbom:
            self._advisory_messages.append(
                "SBOM Advisory: Writing sbom.spdx.json to the repository exposes your full "
                "dependency tree publicly. Add to .gitignore if not intended for version control. "
                "Prefer uploading as a workflow artifact instead of committing."
            )

    def _render_summary_table(self) -> list[str]:
        """Render the summary section including dimension status."""
        # Count by severity
        counts = dict.fromkeys(_SEVERITY_ORDER, 0)
        for f in self.findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1
        total = sum(counts.values())

        lines = [
            "### Summary",
            "",
            "| Severity | Count |",
            "|----------|-------|",
        ]
        for sev in _SEVERITY_ORDER:
            lines.append(f"| {sev} | {counts[sev]} |")
        lines.append(f"| **Total** | **{total}** |")
        lines.append("")

        # Overall posture
        if counts["Critical"] == 0 and counts["High"] == 0:
            if total == 0:
                lines.append("**Supply Chain Posture: Passing ✅** — No findings detected.")
            else:
                lines.append("**Supply Chain Posture: Passing ✅** — No Critical or High findings.")
        else:
            lines.append(
                f"**Supply Chain Posture: ⚠ Action Required** — {counts['Critical']} Critical, {counts['High']} High findings."
            )
        lines.append("")

        # Dimension status table
        lines += [
            "#### Dimension Status",
            "",
            "| Dim | Name | Status | Reason |",
            "|-----|------|--------|--------|",
        ]
        dim_names = {
            1: "Action SHA Pinning",
            2: "Workflow Permissions",
            3: "Secret Exposure",
            4: "Cache Poisoning",
            5: "Container Image Pinning",
            6: "Credential Hygiene",
            7: "NuGet Lock",
            8: "Python Integrity",
            9: "Cargo Supply Chain",
            10: "Node Integrity",
            11: "Go Module Integrity",
            12: "Docker Build Chain",
        }
        for dim in range(1, 13):
            name = dim_names.get(dim, f"Dimension {dim}")
            if dim in self.active_dims:
                dim_findings = [f for f in self.findings if f.dimension == dim]
                if dim_findings:
                    status = f"⚠ {len(dim_findings)} finding(s)"
                else:
                    status = "✅ Checked"
                reason = ""
            else:
                status = "⏭ Skipped"
                reason = self._skip_reasons.get(dim, "")
            lines.append(f"| {dim} | {name} | {status} | {reason} |")
        lines.append("")

        return lines

    def _render_findings_section(self) -> list[str]:
        """Render the findings list section."""
        lines = ["### Findings", ""]

        if not self.findings:
            lines.append("_No findings detected for audited dimensions._")
            lines.append("")
        else:
            # Sort: Critical first, then High, Medium, Info; within severity by dim/file/line
            severity_rank = {s: i for i, s in enumerate(_SEVERITY_ORDER)}
            sorted_findings = sorted(
                self.findings,
                key=lambda f: (severity_rank.get(f.severity, 99), f.dimension, f.file, f.line),
            )
            for f in sorted_findings:
                lines.append(f"#### {f.id} — Dim {f.dimension} — {f.severity}")
                lines.append("")
                lines.append(f"**Severity**: {f.severity}")
                lines.append(f"**File**: `{f.file}:{f.line}`")
                current_display = (
                    "<REDACTED>" if f.contains_secret else _sanitize_for_display(f.current_value)
                )
                lines.append(f"**Current**: `{current_display}`")
                expected_display = (
                    "<REDACTED>" if f.contains_secret else _sanitize_for_display(f.expected_value)
                )
                lines.append(f"**Expected**: `{expected_display}`")
                lines.append(f"**Why**: {f.rationale}")
                if f.accepted_risk:
                    lines.append("_[ACCEPTED RISK — review date applies]_")
                if f.fix_url:
                    lines.append(f"**Fix**: {f.fix_url}")
                if f.tool_required:
                    lines.append(f"**Tool required**: {f.tool_required}")
                lines.append("")

        return lines

    def _render_slsa_section(self) -> list[str]:
        """Render the SLSA readiness section."""
        lines = ["### SLSA Readiness", ""]
        if self.slsa:
            lines.append(self.slsa.render())
        else:
            lines.append(
                "_SLSA assessment requires GHA scope. Run with --scope gha or --scope all._"
            )
        lines.append("")
        return lines

    def render(self) -> str:
        """Render the full markdown report."""
        today = date.today().isoformat()
        scope_str = ", ".join(self.scope)

        # Build tool availability string
        if self.tool_status:
            tool_parts = []
            for tool, status in sorted(self.tool_status.items()):
                tool_parts.append(f"{tool}: {status}")
            tool_avail = "; ".join(tool_parts)
        else:
            tool_avail = (
                "gh: not checked, crane: not checked, syft: not checked, grype: not checked"
            )

        # Degraded mode notice
        degraded_tools = [
            t
            for t, s in self.tool_status.items()
            if "unavailable" in s.lower() or "timeout" in s.lower()
        ]

        lines = [
            "## Supply Chain Audit Report",
            "",
            f"**Date**: {today}",
            f"**Root**: {self.root or '.'}",
            f"**Scope**: {scope_str}",
            f"**Skipped**: Dims {', '.join(str(d) for d in sorted(self.skipped_dims)) if self.skipped_dims else 'none'}",
            f"**Tool availability**: {tool_avail}",
        ]

        if degraded_tools:
            lines.append(
                f"**⚠ Degraded mode**: {', '.join(degraded_tools)} unavailable — TOOL_TIMEOUT or not installed"
            )

        lines.append("")

        # Delegate to section renderers
        lines += self._render_summary_table()
        lines += self._render_findings_section()
        lines += self._render_slsa_section()

        # ── Recommended Next Steps section ────────────────────────────────────
        lines += ["### Recommended Next Steps", ""]

        # Count by severity for next steps
        counts = dict.fromkeys(_SEVERITY_ORDER, 0)
        for f in self.findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1

        if counts["Critical"] > 0 or counts["High"] > 0:
            lines.append("**Priority 1 — Fix Critical and High findings immediately:**")
            critical_high = [f for f in self.findings if f.severity in ("Critical", "High")]
            for f in critical_high[:3]:
                lines.append(f"- [ ] Fix `{f.id}`: {f.rationale[:80]}...")
            lines.append("")

        # Lock file issues → dependency-resolver
        lock_dims = [7, 8, 9, 10, 11]
        lock_findings = [f for f in self.findings if f.dimension in lock_dims]
        if lock_findings:
            lines.append("**Delegate lock file remediation to `dependency-resolver` skill:**")
            lines.append(
                f"- Affected ecosystems: {', '.join(sorted({_dim_to_eco(f.dimension) for f in lock_findings}))}"
            )
            lines.append("- Run `/dependency-resolver` with the finding IDs above")
            lines.append("")

        # Pre-commit hooks
        lines.append("**Install pre-commit hooks to prevent regressions:**")
        lines.append("- Run `/pre-commit-manager` to install hooks for detected ecosystems")
        if any(f.dimension in (1, 2, 3) for f in self.findings):
            lines.append("  - zizmor / actionlint: GitHub Actions security linting (Dims 1-3)")
        if any(f.dimension == 3 for f in self.findings):
            lines.append("  - detect-secrets: Prevent secret commits (Dim 3+6)")
        lines.append("")

        # Advisory messages
        if self._advisory_messages:
            lines.append("**Advisories:**")
            for msg in self._advisory_messages:
                lines.append(f"- {msg}")
            lines.append("")

        return "\n".join(lines)

    def get_handoff(self, skill: str) -> str | None:
        """Get pre-built inter-skill handoff message, or None if not applicable."""
        return self._handoffs.get(skill)

    def get_advisory_messages(self) -> list[str]:
        """Return list of advisory messages (SBOM warnings, tool notes)."""
        return list(self._advisory_messages)


def _dim_to_eco(dim: int) -> str:
    return {7: "dotnet", 8: "python", 9: "rust", 10: "node", 11: "go"}.get(dim, f"dim{dim}")


def build_report(
    findings: list[Finding],
    active_dims: list[int],
    skipped_dims: list[int],
    skip_reasons: dict[int, str] | None = None,
    root: str = "",
    scope: list[str] | None = None,
    slsa: SlsaAssessment | None = None,
    tool_status: dict[str, str] | None = None,
    advisory_messages: list[str] | None = None,
    generate_sbom: bool = False,
    handoffs: dict[str, str] | None = None,
) -> AuditReport:
    """Construct an AuditReport from findings and metadata."""
    return AuditReport(
        findings=findings,
        active_dims=active_dims,
        skipped_dims=skipped_dims,
        skip_reasons=skip_reasons or {},
        root=root,
        scope=scope,
        slsa=slsa,
        tool_status=tool_status or {},
        advisory_messages=advisory_messages or [],
        generate_sbom=generate_sbom,
        handoffs=handoffs or {},
    )
