"""Render atlas JSON data into beautiful mkdocs-material pages.

Transforms extraction layer JSONs into atlas pages with:
- Grid card dashboard (index)
- Diagram-first layer pages with content tabs (Mermaid / Graphviz / Table)
- Health check dashboard
- Glossary
- Generated .mmd source files

Public API:
    AtlasRenderer: Main renderer class
    main: CLI entry point
"""

import argparse
import json
import textwrap
from datetime import datetime, timezone
from pathlib import Path

__all__ = ["AtlasRenderer", "main"]

# Layer definitions: slug, display name, icon, category, description
LAYER_DEFS = [
    {
        "num": 1,
        "slug": "repo-surface",
        "json_key": "layer1_repo_surface",
        "name": "Repository Surface",
        "icon": ":material-folder-outline:",
        "category": "structural",
        "description": "Directory tree, file counts, project structure",
    },
    {
        "num": 2,
        "slug": "ast-lsp-bindings",
        "json_key": "layer2_ast_bindings",
        "name": "AST + LSP Bindings",
        "icon": ":material-code-braces:",
        "category": "structural",
        "description": "Cross-file imports, symbol references, dead code",
    },
    {
        "num": 3,
        "slug": "compile-deps",
        "json_key": "layer3_compile_deps",
        "name": "Compile-time Dependencies",
        "icon": ":material-package-variant:",
        "category": "structural",
        "description": "External deps, internal import graph, circular deps",
    },
    {
        "num": 4,
        "slug": "runtime-topology",
        "json_key": "layer4_runtime_topology",
        "name": "Runtime Topology",
        "icon": ":material-server-network:",
        "category": "structural",
        "description": "Processes, ports, subprocess calls, env vars",
    },
    {
        "num": 5,
        "slug": "api-contracts",
        "json_key": "layer5_api_contracts",
        "name": "API Contracts",
        "icon": ":material-api:",
        "category": "behavioral",
        "description": "CLI commands, HTTP routes, hooks, recipes",
    },
    {
        "num": 6,
        "slug": "data-flow",
        "json_key": "layer6_data_flow",
        "name": "Data Flow",
        "icon": ":material-transit-connection-variant:",
        "category": "behavioral",
        "description": "File I/O, database ops, network I/O, data paths",
    },
    {
        "num": 7,
        "slug": "service-components",
        "json_key": "layer7_service_components",
        "name": "Service Components",
        "icon": ":material-view-module:",
        "category": "structural",
        "description": "Package boundaries, coupling metrics, architecture",
    },
    {
        "num": 8,
        "slug": "user-journeys",
        "json_key": "layer8_user_journeys",
        "name": "User Journeys",
        "icon": ":material-routes:",
        "category": "behavioral",
        "description": "Entry-to-outcome traces for CLI, HTTP, hooks",
    },
]


def _mermaid_escape(text: str) -> str:
    """Sanitize text for use inside Mermaid node labels and messages.

    Escapes characters that break Mermaid syntax: double quotes, angle brackets,
    and newlines.
    """
    return (text
            .replace('"', '#quot;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('\n', ' '))


class AtlasRenderer:
    """Renders atlas JSON data into mkdocs-material pages.

    Args:
        data_dir: Directory containing layer JSON files (e.g. atlas_output/).
        output_dir: Directory to write rendered pages (e.g. docs/atlas/).
    """

    def __init__(self, data_dir: Path, output_dir: Path):
        self.data_dir = data_dir
        self.output_dir = output_dir
        self.layers: dict[str, dict] = {}
        self.generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    def load_all_layers(self) -> dict[str, dict]:
        """Load all available layer JSONs from data_dir.

        Returns:
            Dict mapping json_key to parsed data. Missing files are skipped
            with a warning printed to stderr.
        """
        import sys

        for layer_def in LAYER_DEFS:
            json_key = layer_def["json_key"]
            json_path = self.data_dir / f"{json_key}.json"
            if json_path.exists():
                self.layers[json_key] = json.loads(json_path.read_text())
            else:
                print(f"Warning: {json_path} not found, skipping", file=sys.stderr)

        # Also try cross-layer report
        report_path = self.data_dir / "cross_layer_report.json"
        if report_path.exists():
            self.layers["cross_layer_report"] = json.loads(report_path.read_text())

        return self.layers

    def render_all(self):
        """Render all atlas pages."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.render_index()
        self.render_layer_pages()
        self.render_health()
        self.render_glossary()
        self.render_mermaid_sources()

    def render_index(self):
        """Render atlas/index.md -- grid card dashboard with coverage bars."""
        lines = [
            "---",
            "title: Code Atlas",
            "---",
            "",
            "# Code Atlas",
            "",
            f'<div class="atlas-metadata">Generated: {self.generated_at}</div>',
            "",
            "## Layer Overview",
            "",
            '<div class="grid cards atlas-grid" markdown>',
            "",
        ]

        for layer_def in LAYER_DEFS:
            json_key = layer_def["json_key"]
            data = self.layers.get(json_key, {})
            summary = data.get("summary", {})
            coverage = self._compute_coverage(layer_def, data)
            icon_class = f"atlas-icon--{layer_def['category']}"

            lines.append(f"-   <span class=\"{icon_class}\">{layer_def['icon']}</span>"
                         f" **[Layer {layer_def['num']}: {layer_def['name']}]"
                         f"({layer_def['slug']}/)**")
            lines.append("")
            lines.append(f"    ---")
            lines.append("")
            lines.append(f"    {layer_def['description']}")
            lines.append("")

            if coverage is not None:
                pct = min(100, max(0, int(coverage)))
                lines.append(f'    <div class="atlas-coverage">')
                lines.append(f'    <div class="atlas-coverage__bar" '
                             f'style="width:{pct}%"></div>')
                lines.append(f"    </div>")
                coverage_label = self._coverage_label(layer_def, data, pct)
                lines.append(f"    <small>{coverage_label}</small>")
                lines.append("")

            # Summary stats
            if summary:
                stat_items = self._format_summary_stats(layer_def, summary)
                if stat_items:
                    lines.append(f'    <div class="atlas-scale">')
                    lines.append(f"    {' | '.join(stat_items)}")
                    lines.append(f"    </div>")
                    lines.append("")

        lines.append("</div>")
        lines.append("")

        # Language detection section (from layer 1)
        layer1 = self.layers.get("layer1_repo_surface", {})
        languages = layer1.get("languages", {})
        if languages:
            primary = layer1.get("primary_language", "unknown")
            total_code = layer1.get("total_code_lines", 0)
            tools_used = layer1.get("tools_used", [])
            tool_label = ", ".join(tools_used) if tools_used else "extension counting"

            lines.extend([
                "## Languages",
                "",
                f"Primary language: **{primary.title()}**"
                f" | Total code: **{total_code:,}** lines"
                f" | Detected via: *{tool_label}*",
                "",
                "| Language | Files | Code Lines | % | Analysis Available |",
                "|----------|------:|-----------:|--:|-------------------|",
            ])

            # Analysis availability per language
            analysis_levels = {
                "python": "Full (AST, imports, dead code, journeys)",
                "rust": "Dependencies (Cargo.toml)",
                "typescript": "Dependencies (package.json)",
                "javascript": "Dependencies (package.json)",
                "go": "Dependencies (go.mod)",
                "csharp": "Dependencies (*.csproj)",
                "java": "Dependencies (build manifest)",
            }

            # Filter out non-code languages for the main table
            _code_languages = {
                "python", "rust", "typescript", "javascript", "go",
                "csharp", "java", "ruby", "swift", "kotlin", "c", "cpp",
                "zig", "lua",
            }

            for lang, info in languages.items():
                analysis = analysis_levels.get(lang, "File-level only")
                code = info.get("code", info.get("line_count", 0))
                pct = info.get("percentage", 0)
                # Show all languages with code, but highlight programming ones
                if lang in _code_languages or code > 0:
                    lines.append(
                        f"| {lang.title()} | {info['file_count']:,} "
                        f"| {code:,} | {pct}% | {analysis} |"
                    )

            lines.append("")

            # Show coverage note if primary language is not Python
            if primary != "python":
                pct_primary = languages.get(primary, {}).get("percentage", 0)
                lines.extend([
                    f"> **Analysis Coverage**: This codebase is primarily "
                    f"**{primary.title()}** ({pct_primary}% of code). "
                    f"Full AST analysis is available for Python files. "
                    f"{primary.title()} analysis covers dependencies and "
                    f"file structure. See [issue #3310]"
                    f"(https://github.com/user/repo/issues/3310) for "
                    f"expanded language support.",
                    "",
                ])
            else:
                non_python = [l for l in languages if l != "python"]
                if non_python:
                    lines.extend([
                        "> **Note**: Full AST analysis is currently available "
                        "for Python only. Other languages have dependency and "
                        "file-level analysis.",
                        "",
                    ])

        # Legend
        lines.extend([
            "## Legend",
            "",
            '<div class="atlas-legend" markdown>',
            "",
            "| Category | Layers | Color |",
            "|----------|--------|-------|",
            "| Structural | 1, 2, 3, 4, 7 | Blue |",
            "| Behavioral | 5, 6, 8 | Orange |",
            "",
            "</div>",
            "",
        ])

        # Cross-references to inventory & health
        lines.extend([
            "## Quick Links",
            "",
            "- [Health Dashboard](health.md) -- cross-layer check results",
            "- [Glossary](glossary.md) -- atlas terminology",
            "",
        ])

        self._write_page("index.md", "\n".join(lines))

    def render_layer_pages(self):
        """Render individual layer pages."""
        for layer_def in LAYER_DEFS:
            json_key = layer_def["json_key"]
            data = self.layers.get(json_key, {})
            self._render_layer_page(layer_def, data)

    def _render_layer_page(self, layer_def: dict, data: dict):
        """Render a single layer page with diagram-first layout.

        Template: breadcrumb > metadata > Map (tabs) > Legend > Key Findings >
        Detail (collapsed) > Cross-refs > Footer
        """
        slug = layer_def["slug"]
        layer_dir = self.output_dir / slug
        layer_dir.mkdir(parents=True, exist_ok=True)

        summary = data.get("summary", {})
        meta = data.get("meta", {})
        gen_time = meta.get("generated_at", self.generated_at)

        lines = [
            "---",
            f"title: \"Layer {layer_def['num']}: {layer_def['name']}\"",
            "---",
            "",
            # Breadcrumb
            f'<nav class="atlas-breadcrumb">',
            f'<a href="../">Atlas</a> &raquo; Layer {layer_def["num"]}: {layer_def["name"]}',
            f"</nav>",
            "",
            f"# Layer {layer_def['num']}: {layer_def['name']}",
            "",
            # Metadata strip
            f'<div class="atlas-metadata">',
            f'Category: <strong>{layer_def["category"].title()}</strong> | '
            f"Generated: {gen_time}",
            f"</div>",
            "",
        ]

        # Map section with content tabs
        mermaid_src = self._generate_mermaid_for_layer(layer_def, data)
        lines.extend([
            "## Map",
            "",
            '=== "Interactive (Mermaid)"',
            "",
            "    ```mermaid",
        ])
        for mermaid_line in mermaid_src.splitlines():
            lines.append(f"    {mermaid_line}")
        lines.extend([
            "    ```",
            "",
            '=== "High-Fidelity (Graphviz)"',
            "",
            f'    <div class="atlas-diagram-container">',
            f'    <img src="{slug}-dot.svg" alt="{layer_def["name"]} - Graphviz">',
            f"    </div>",
            "",
            '=== "Data Table"',
            "",
        ])
        table_lines = self._generate_data_table(layer_def, data)
        for tl in table_lines:
            lines.append(f"    {tl}")
        lines.append("")

        # Legend
        lines.extend([
            "## Legend",
            "",
            '<div class="atlas-legend" markdown>',
            "",
        ])
        lines.extend(self._generate_legend(layer_def))
        lines.extend([
            "",
            "</div>",
            "",
        ])

        # Key Findings
        lines.extend([
            "## Key Findings",
            "",
        ])
        findings = self._generate_findings(layer_def, data)
        for finding in findings:
            lines.append(f"- {finding}")
        if not findings:
            lines.append("- No data available for analysis.")
        lines.append("")

        # Detail (collapsed)
        lines.extend([
            "## Detail",
            "",
            "??? info \"Full data (click to expand)\"",
            "",
        ])
        detail_lines = self._generate_detail_section(layer_def, data)
        for dl in detail_lines:
            lines.append(f"    {dl}")
        lines.append("")

        # Cross-references
        lines.extend([
            "## Cross-References",
            "",
            '<div class="atlas-crossref" markdown>',
            "",
        ])
        xrefs = self._generate_crossrefs(layer_def)
        for xref in xrefs:
            lines.append(f"- {xref}")
        lines.extend([
            "",
            "</div>",
            "",
        ])

        # Footer
        lines.extend([
            '<div class="atlas-footer">',
            "",
            f"Source: `{layer_def['json_key']}.json`"
            f" | [Mermaid source]({slug}.mmd)",
            "",
            "</div>",
            "",
        ])

        self._write_page(f"{slug}/index.md", "\n".join(lines))

    def render_health(self):
        """Render atlas/health.md -- cross-layer check dashboard."""
        report = self.layers.get("cross_layer_report", {})
        checks = report.get("checks", [])
        overall = report.get("overall", "UNKNOWN")
        warning_count = report.get("warning_count", 0)
        failure_count = report.get("failure_count", 0)

        status_icon = {
            "PASS": ":material-check-circle:{ .atlas-health--pass }",
            "PASS_WITH_WARNINGS": ":material-alert-circle:{ .atlas-health--warn }",
            "FAIL": ":material-close-circle:{ .atlas-health--fail }",
        }.get(overall, ":material-help-circle:")

        lines = [
            "---",
            "title: Health Dashboard",
            "---",
            "",
            '<nav class="atlas-breadcrumb">',
            '<a href="../">Atlas</a> &raquo; Health Dashboard',
            "</nav>",
            "",
            "# Health Dashboard",
            "",
            f'<div class="atlas-metadata">',
            f"Overall: {status_icon} **{overall}** | "
            f"Warnings: {warning_count} | Failures: {failure_count}",
            f"</div>",
            "",
        ]

        if checks:
            lines.extend([
                "## Check Results",
                "",
                "| Check | Status | Details |",
                "|-------|--------|---------|",
            ])
            for check in checks:
                name = check.get("name", "unknown")
                status = check.get("status", "UNKNOWN")
                details = check.get("details", "")
                status_badge = {
                    "PASS": ":material-check-circle:{ .atlas-health--pass }",
                    "WARN": ":material-alert-circle:{ .atlas-health--warn }",
                    "FAIL": ":material-close-circle:{ .atlas-health--fail }",
                }.get(status, status)
                lines.append(f"| {name} | {status_badge} | {details} |")
            lines.append("")
        else:
            lines.extend([
                "!!! warning \"No cross-layer report available\"",
                "    Run the extraction pipeline to generate health data:",
                "    ```",
                "    python -m scripts.atlas.run_all",
                "    ```",
                "",
            ])

        # Warnings detail
        if checks:
            warn_checks = [c for c in checks if c.get("status") == "WARN"]
            if warn_checks:
                lines.extend([
                    "## Warnings",
                    "",
                ])
                for check in warn_checks:
                    name = check.get("name", "unknown")
                    details = check.get("details", "")
                    missing = check.get("missing", [])
                    lines.append(f"### {name}")
                    lines.append("")
                    lines.append(details)
                    if missing:
                        lines.append("")
                        lines.append("Missing items:")
                        lines.append("")
                        for item in missing:
                            lines.append(f"- `{item}`")
                    lines.append("")

        self._write_page("health.md", "\n".join(lines))

    def render_glossary(self):
        """Render atlas/glossary.md -- atlas terminology."""
        lines = [
            "---",
            "title: Glossary",
            "---",
            "",
            '<nav class="atlas-breadcrumb">',
            '<a href="../">Atlas</a> &raquo; Glossary',
            "</nav>",
            "",
            "# Atlas Glossary",
            "",
            "| Term | Definition |",
            "|------|-----------|",
            "| **Layer** | A distinct analytical view of the codebase (8 total) |",
            "| **Structural layer** | Layers analyzing static code structure "
            "(1, 2, 3, 4, 7) |",
            "| **Behavioral layer** | Layers analyzing runtime behavior and "
            "data flow (5, 6, 8) |",
            "| **Manifest** | Canonical file list built from `git ls-files` "
            "(Layer 0 foundation) |",
            "| **Coverage** | Percentage of manifest files analyzed by a layer |",
            "| **Afferent coupling (Ca)** | Number of packages that depend on "
            "this package |",
            "| **Efferent coupling (Ce)** | Number of packages this package "
            "depends on |",
            "| **Instability** | Ce / (Ca + Ce). 0 = maximally stable, "
            "1 = maximally unstable |",
            "| **Dead code** | Definitions not exported, not imported, not called "
            "internally (conservative) |",
            "| **Entry point** | CLI command, HTTP route, or hook that starts "
            "a user journey |",
            "| **Journey** | Trace from entry point through call graph to "
            "outcome (depth-limited) |",
            "| **Outcome** | Terminal action: file I/O, database op, subprocess, "
            "network call, or return |",
            "| **Cross-layer check** | Validation that data is consistent across "
            "multiple layers |",
            "| **Transformation point** | Function that both reads and writes "
            "data (data flow bridge) |",
            "",
        ]

        self._write_page("glossary.md", "\n".join(lines))

    def render_mermaid_sources(self):
        """Generate .mmd files from layer JSON data."""
        for layer_def in LAYER_DEFS:
            json_key = layer_def["json_key"]
            data = self.layers.get(json_key, {})
            slug = layer_def["slug"]
            mermaid_src = self._generate_mermaid_for_layer(layer_def, data)

            mmd_path = self.output_dir / slug / f"{slug}.mmd"
            mmd_path.parent.mkdir(parents=True, exist_ok=True)
            mmd_path.write_text(mermaid_src)

    # -----------------------------------------------------------------------
    # Mermaid generation per layer
    # -----------------------------------------------------------------------

    def _generate_mermaid_for_layer(self, layer_def: dict, data: dict) -> str:
        """Generate Mermaid source for a layer.

        Dispatches to layer-specific generator based on layer number.
        Returns a fallback diagram if no data is available.
        """
        generators = {
            1: self._mermaid_repo_surface,
            2: self._mermaid_ast_bindings,
            3: self._mermaid_compile_deps,
            4: self._mermaid_runtime_topology,
            5: self._mermaid_api_contracts,
            6: self._mermaid_data_flow,
            7: self._mermaid_service_components,
            8: self._mermaid_user_journeys,
        }
        generator = generators.get(layer_def["num"])
        if generator is None:
            return self._mermaid_placeholder(layer_def)
        return generator(layer_def, data)

    def _mermaid_placeholder(self, layer_def: dict) -> str:
        return (
            f"graph TD\n"
            f"    A[\"{layer_def['name']}\"] --> B[\"No data available\"]\n"
        )

    def _mermaid_repo_surface(self, layer_def: dict, data: dict) -> str:
        """Layer 1: graph TD showing directory tree with file counts."""
        directories = data.get("directories", [])
        if not directories:
            return self._mermaid_placeholder(layer_def)

        lines = ["graph TD"]

        # Group by depth and limit to top 2 levels for readability
        top_dirs = [d for d in directories if d.get("depth", 0) <= 2]
        top_dirs.sort(key=lambda d: d.get("path", ""))

        node_ids: dict[str, str] = {}
        counter = 0

        for d in top_dirs[:40]:  # Limit nodes for readability
            path = d.get("path", "unknown")
            role = d.get("role", "dir")
            counts = d.get("file_counts", {})
            total = counts.get("total", 0)
            py_count = counts.get("python", 0)

            node_id = f"D{counter}"
            counter += 1
            node_ids[path] = node_id

            short_name = Path(path).name or path
            label = _mermaid_escape(f"{short_name}<br/>{py_count} py / {total} total")
            lines.append(f'    {node_id}["{label}"]')

        # Edges from parent to child
        for d in top_dirs[:40]:
            path = d.get("path", "")
            parent = d.get("parent", "")
            if path in node_ids and parent in node_ids:
                lines.append(f"    {node_ids[parent]} --> {node_ids[path]}")

        # Click events for cross-layer nav
        lines.append("")
        lines.append(f'    click D0 "../" "Back to Atlas index"')

        return "\n".join(lines)

    def _mermaid_ast_bindings(self, layer_def: dict, data: dict) -> str:
        """Layer 2: graph LR showing cross-file imports (top 30 by ref count)."""
        definitions = data.get("definitions", [])
        if not definitions:
            return self._mermaid_placeholder(layer_def)

        # Build reference counts per file
        file_refs: dict[str, int] = {}
        for defn in definitions:
            ref_count = defn.get("reference_count", 0)
            f = defn.get("file", "")
            if f:
                file_refs[f] = file_refs.get(f, 0) + ref_count

        # Top 30 files by total reference count
        top_files = sorted(file_refs.items(), key=lambda x: x[1], reverse=True)[:30]

        lines = ["graph LR"]
        node_ids: dict[str, str] = {}

        for i, (filepath, count) in enumerate(top_files):
            nid = f"F{i}"
            node_ids[filepath] = nid
            short = _mermaid_escape(Path(filepath).stem)
            lines.append(f'    {nid}["{short}<br/>refs: {count}"]')

        # Build edges from imports
        imports = data.get("imports", [])
        seen_edges: set[tuple[str, str]] = set()
        for imp in imports:
            src = imp.get("file", "")
            target = imp.get("resolved_target", "")
            if src in node_ids and target in node_ids and src != target:
                edge = (node_ids[src], node_ids[target])
                if edge not in seen_edges:
                    seen_edges.add(edge)
                    lines.append(f"    {edge[0]} --> {edge[1]}")

        if not seen_edges:
            # Fallback: just show the top files without edges
            pass

        lines.append("")
        lines.append(f'    click F0 "../ast-lsp-bindings/" "View AST bindings"')

        return "\n".join(lines)

    def _mermaid_compile_deps(self, layer_def: dict, data: dict) -> str:
        """Layer 3: Two diagrams -- external deps grouped + internal package graph."""
        ext_deps = data.get("external_dependencies", [])
        int_graph = data.get("internal_import_graph", {})

        lines = ["graph LR"]

        if ext_deps:
            # Group external deps by import count (top 20)
            top_ext = sorted(ext_deps, key=lambda d: d.get("import_count", 0),
                             reverse=True)[:20]
            lines.append('    subgraph ext["External Dependencies"]')
            for i, dep in enumerate(top_ext):
                name = _mermaid_escape(dep.get("name", f"dep{i}"))
                count = dep.get("import_count", 0)
                nid = f"E{i}"
                lines.append(f'        {nid}["{name}<br/>imports: {count}"]')
            lines.append("    end")
            lines.append("")

        nodes = int_graph.get("nodes", [])
        edges = int_graph.get("edges", [])
        if nodes:
            lines.append('    subgraph int["Internal Packages"]')
            pkg_ids: dict[str, str] = {}
            for i, pkg in enumerate(nodes[:30]):
                nid = f"P{i}"
                pkg_ids[pkg] = nid
                short = _mermaid_escape(pkg.split(".")[-1] if "." in pkg else pkg)
                lines.append(f'        {nid}["{short}"]')
            lines.append("    end")

            # Edges with weight > 1
            for edge in edges:
                src = edge.get("from", "")
                dst = edge.get("to", "")
                count = edge.get("import_count", 1)
                if count > 1 and src in pkg_ids and dst in pkg_ids:
                    lines.append(
                        f"    {pkg_ids[src]} -->|{count}| {pkg_ids[dst]}"
                    )

        lines.append("")
        lines.append('    click P0 "../compile-deps/" "View compile deps"')

        return "\n".join(lines)

    def _mermaid_runtime_topology(self, layer_def: dict, data: dict) -> str:
        """Layer 4: graph LR showing processes and connections."""
        subprocess_calls = data.get("subprocess_calls", [])
        port_bindings = data.get("port_bindings", [])
        env_vars = data.get("env_var_reads", [])

        if not subprocess_calls and not port_bindings:
            return self._mermaid_placeholder(layer_def)

        lines = ["graph LR"]

        # Unique subprocess targets
        seen_cmds: dict[str, str] = {}
        counter = 0
        for call in subprocess_calls[:30]:
            cmd = call.get("command_literal")
            if isinstance(cmd, list) and cmd:
                cmd_name = cmd[0]
            elif isinstance(cmd, str):
                cmd_name = cmd.split()[0] if cmd else "unknown"
            else:
                cmd_name = call.get("call_type", "subprocess")

            if cmd_name not in seen_cmds:
                nid = f"S{counter}"
                counter += 1
                seen_cmds[cmd_name] = nid
                lines.append(f'    {nid}(["{_mermaid_escape(cmd_name)}"])')

        # Port bindings as hexagons
        for i, pb in enumerate(port_bindings[:10]):
            port = pb.get("port", "?")
            proto = pb.get("protocol", "tcp")
            framework = pb.get("framework", "")
            label = f":{port} ({proto})"
            if framework:
                label = f"{framework} {label}"
            nid = f"B{i}"
            hex_label = "{{" + f'"{label}"' + "}}"
            lines.append(f"    {nid}{hex_label}")

        # Connect files to their subprocess calls
        file_nodes: dict[str, str] = {}
        fcounter = 0
        for call in subprocess_calls[:30]:
            src_file = call.get("file", "")
            short_src = Path(src_file).stem if src_file else "unknown"
            if short_src not in file_nodes:
                fnid = f"FN{fcounter}"
                fcounter += 1
                file_nodes[short_src] = fnid
                lines.append(f'    {fnid}["{_mermaid_escape(short_src)}"]')

            cmd = call.get("command_literal")
            if isinstance(cmd, list) and cmd:
                cmd_name = cmd[0]
            elif isinstance(cmd, str):
                cmd_name = cmd.split()[0] if cmd else "unknown"
            else:
                cmd_name = call.get("call_type", "subprocess")

            if cmd_name in seen_cmds and short_src in file_nodes:
                lines.append(f"    {file_nodes[short_src]} --> {seen_cmds[cmd_name]}")

        return "\n".join(lines)

    def _mermaid_api_contracts(self, layer_def: dict, data: dict) -> str:
        """Layer 5: graph TD showing CLI command tree."""
        cli_commands = data.get("cli_commands", [])
        if not cli_commands:
            return self._mermaid_placeholder(layer_def)

        lines = ["graph TD"]
        lines.append('    ROOT["amplihack"]')

        node_ids: dict[str, str] = {}
        node_ids["amplihack"] = "ROOT"
        counter = 0

        for cmd in cli_commands:
            command = cmd.get("command", "")
            parent = cmd.get("parent", "amplihack")
            parser_name = cmd.get("parser_name", command.split()[-1] if command else "")

            nid = f"C{counter}"
            counter += 1
            node_ids[command] = nid

            arg_count = len(cmd.get("arguments", []))
            label = _mermaid_escape(parser_name)
            if arg_count:
                label = f"{_mermaid_escape(parser_name)}<br/>{arg_count} args"
            lines.append(f'    {nid}["{label}"]')

            parent_nid = node_ids.get(parent, "ROOT")
            lines.append(f"    {parent_nid} --> {nid}")

        lines.append("")
        lines.append('    click ROOT "../" "Back to Atlas"')

        return "\n".join(lines)

    def _mermaid_data_flow(self, layer_def: dict, data: dict) -> str:
        """Layer 6: flowchart TD showing data paths from entry to storage."""
        file_io = data.get("file_io", [])
        db_ops = data.get("database_ops", [])
        net_io = data.get("network_io", [])
        transforms = data.get("transformation_points", [])

        if not file_io and not db_ops:
            return self._mermaid_placeholder(layer_def)

        lines = ["flowchart TD"]

        # Group I/O by format
        formats: dict[str, int] = {}
        for op in file_io:
            fmt = op.get("format", "unknown")
            operation = op.get("operation", "unknown")
            key = f"{operation}:{fmt}"
            formats[key] = formats.get(key, 0) + 1

        # Storage nodes
        counter = 0
        for key, count in sorted(formats.items(), key=lambda x: x[1], reverse=True)[:15]:
            op, fmt = key.split(":", 1)
            nid = f"IO{counter}"
            counter += 1
            shape = f'[("{fmt} {op}<br/>n={count}")]' if op == "read" else \
                    f'[/"{fmt} {op}<br/>n={count}"/]'
            lines.append(f"    {nid}{shape}")

        # Database ops
        db_types: dict[str, int] = {}
        for op in db_ops:
            db_type = op.get("db_type", "unknown")
            db_types[db_type] = db_types.get(db_type, 0) + 1

        for db_type, count in db_types.items():
            nid = f"DB{counter}"
            counter += 1
            lines.append(f'    {nid}[("{db_type}<br/>ops: {count}")]')

        # Network I/O
        if net_io:
            net_count = len(net_io)
            nid = f"NET{counter}"
            counter += 1
            lines.append(f'    {nid}("Network I/O<br/>n={net_count}")')

        # Transformation points as connectors between I/O nodes
        # Build a lookup from format key to node ID for linking
        io_node_ids: dict[str, str] = {}
        io_counter = 0
        for key in sorted(formats.items(), key=lambda x: x[1], reverse=True)[:15]:
            io_node_ids[key[0]] = f"IO{io_counter}"
            io_counter += 1

        for i, tp in enumerate(transforms[:10]):
            func = _mermaid_escape(tp.get("function", "transform"))
            tnid = f"T{i}"
            lines.append(f'    {tnid}{{{{"{func}"}}}}')
            reads = tp.get("reads", [])
            writes = tp.get("writes", [])
            # Connect to actual I/O nodes based on format matches
            for r in reads[:3]:
                fmt = r if isinstance(r, str) else str(r)
                for key, nid in io_node_ids.items():
                    if fmt in key:
                        lines.append(f"    {nid} -.->|reads| {tnid}")
                        break
            for w in writes[:3]:
                fmt = w if isinstance(w, str) else str(w)
                for key, nid in io_node_ids.items():
                    if fmt in key:
                        lines.append(f"    {tnid} -.->|writes| {nid}")
                        break

        return "\n".join(lines)

    def _mermaid_service_components(self, layer_def: dict, data: dict) -> str:
        """Layer 7: graph TB with subgraph clusters per classification."""
        packages = data.get("packages", [])
        if not packages:
            return self._mermaid_placeholder(layer_def)

        lines = ["graph TB"]

        # Group packages by classification
        by_class: dict[str, list[dict]] = {}
        for pkg in packages:
            cls = pkg.get("classification", "feature")
            by_class.setdefault(cls, []).append(pkg)

        node_ids: dict[str, str] = {}
        counter = 0

        for cls_name in ["core", "utility", "feature", "leaf"]:
            pkgs = by_class.get(cls_name, [])
            if not pkgs:
                continue

            lines.append(f'    subgraph {cls_name}["{cls_name.title()} Packages"]')
            for pkg in pkgs:
                name = pkg.get("name", "")
                short = name.split(".")[-1] if "." in name else name
                instability = pkg.get("instability", 0)
                file_count = pkg.get("file_count", 0)
                nid = f"P{counter}"
                counter += 1
                node_ids[name] = nid
                lines.append(
                    f'        {nid}["{_mermaid_escape(short)}<br/>'
                    f'{file_count} files<br/>'
                    f'I={instability:.2f}"]'
                )
            lines.append("    end")
            lines.append("")

        # Cross-package edges (top imports)
        coupling = data.get("coupling_matrix", {})
        edge_count = 0
        for src, targets in coupling.items():
            if src not in node_ids:
                continue
            for dst, count in sorted(targets.items(), key=lambda x: x[1],
                                     reverse=True)[:3]:
                if dst in node_ids and edge_count < 40:
                    lines.append(
                        f"    {node_ids[src]} -->|{count}| {node_ids[dst]}"
                    )
                    edge_count += 1

        lines.append("")
        lines.append('    click P0 "../service-components/" "View details"')

        return "\n".join(lines)

    def _mermaid_user_journeys(self, layer_def: dict, data: dict) -> str:
        """Layer 8: sequenceDiagram for top 5 CLI commands by trace depth."""
        journeys = data.get("journeys", [])
        if not journeys:
            return self._mermaid_placeholder(layer_def)

        # Top 5 by trace depth
        cli_journeys = [j for j in journeys if j.get("entry_type") == "cli"]
        top = sorted(cli_journeys, key=lambda j: j.get("trace_depth", 0),
                     reverse=True)[:5]
        if not top:
            top = journeys[:5]

        lines = ["sequenceDiagram"]
        declared_participants: set[str] = set()

        for journey in top:
            command = journey.get("command", "unknown")
            handler = journey.get("handler", {})
            handler_func = handler.get("function", "handler")
            handler_file = Path(handler.get("file", "")).stem if handler.get("file") else "module"
            outcomes = journey.get("outcomes", [])
            packages = journey.get("packages_touched", [])

            if "User" not in declared_participants:
                lines.append(f"    participant User")
                declared_participants.add("User")
            if "CLI" not in declared_participants:
                lines.append(f"    participant CLI as cli.py")
                declared_participants.add("CLI")
            if handler_file not in declared_participants:
                lines.append(f"    participant {handler_file}")
                declared_participants.add(handler_file)

            lines.append(f"    User->>CLI: {_mermaid_escape(command)}")
            lines.append(f"    CLI->>{handler_file}: {_mermaid_escape(handler_func)}()")

            for outcome in outcomes[:3]:
                otype = outcome.get("type", "return")
                detail = _mermaid_escape(outcome.get("detail", ""))
                ofile = Path(outcome.get("file", "")).stem if outcome.get("file") else "system"
                if ofile not in declared_participants:
                    lines.append(f"    participant {ofile}")
                    declared_participants.add(ofile)
                lines.append(f"    {handler_file}->>{ofile}: {otype}: {detail}")

            lines.append(f"    {handler_file}-->>CLI: result")
            lines.append(f"    CLI-->>User: exit code")
            lines.append("")

        return "\n".join(lines)

    # -----------------------------------------------------------------------
    # Data table generation
    # -----------------------------------------------------------------------

    def _generate_data_table(self, layer_def: dict, data: dict) -> list[str]:
        """Generate markdown table rows for the Data Table tab."""
        num = layer_def["num"]
        summary = data.get("summary", {})

        if not summary and not data:
            return ["*No data available.*"]

        if num == 1:
            return self._table_repo_surface(data)
        elif num == 2:
            return self._table_ast_bindings(data)
        elif num == 3:
            return self._table_compile_deps(data)
        elif num == 4:
            return self._table_runtime_topology(data)
        elif num == 5:
            return self._table_api_contracts(data)
        elif num == 6:
            return self._table_data_flow(data)
        elif num == 7:
            return self._table_service_components(data)
        elif num == 8:
            return self._table_user_journeys(data)
        return ["*No table generator for this layer.*"]

    def _table_repo_surface(self, data: dict) -> list[str]:
        dirs = data.get("directories", [])
        lines = [
            "| Directory | Role | Python | Total |",
            "|-----------|------|--------|-------|",
        ]
        for d in dirs[:50]:
            path = d.get("path", "")
            role = d.get("role", "")
            counts = d.get("file_counts", {})
            lines.append(
                f"| `{path}` | {role} | {counts.get('python', 0)} "
                f"| {counts.get('total', 0)} |"
            )
        return lines

    def _table_ast_bindings(self, data: dict) -> list[str]:
        summary = data.get("summary", {})
        lines = [
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total definitions | {summary.get('total_definitions', 'N/A')} |",
            f"| Total exports | {summary.get('total_exports', 'N/A')} |",
            f"| Total imports | {summary.get('total_imports', 'N/A')} |",
            f"| Potentially dead | {summary.get('potentially_dead_count', 'N/A')} |",
            f"| Files with `__all__` | {summary.get('files_with_all', 'N/A')} |",
        ]
        return lines

    def _table_compile_deps(self, data: dict) -> list[str]:
        ext_deps = data.get("external_dependencies", [])
        lines = [
            "| Package | Version | Group | Import Count |",
            "|---------|---------|-------|-------------|",
        ]
        for dep in sorted(ext_deps, key=lambda d: d.get("import_count", 0),
                          reverse=True)[:30]:
            lines.append(
                f"| {dep.get('name', '')} | {dep.get('version_constraint', '')} "
                f"| {dep.get('group', '')} | {dep.get('import_count', 0)} |"
            )
        return lines

    def _table_runtime_topology(self, data: dict) -> list[str]:
        summary = data.get("summary", {})
        lines = [
            "| Metric | Value |",
            "|--------|-------|",
            f"| Subprocess calls | {summary.get('subprocess_call_count', 'N/A')} |",
            f"| Unique files with subprocesses | "
            f"{summary.get('unique_subprocess_files', 'N/A')} |",
            f"| Port bindings | {summary.get('port_binding_count', 'N/A')} |",
            f"| Docker services | {summary.get('docker_service_count', 'N/A')} |",
            f"| Environment variables | {summary.get('env_var_count', 'N/A')} |",
        ]
        return lines

    def _table_api_contracts(self, data: dict) -> list[str]:
        cli_cmds = data.get("cli_commands", [])
        lines = [
            "| Command | Args | Help |",
            "|---------|------|------|",
        ]
        for cmd in cli_cmds[:40]:
            command = cmd.get("command", "")
            arg_count = len(cmd.get("arguments", []))
            help_text = cmd.get("help", "")[:60]
            lines.append(f"| `{command}` | {arg_count} | {help_text} |")
        return lines

    def _table_data_flow(self, data: dict) -> list[str]:
        summary = data.get("summary", {})
        lines = [
            "| Metric | Value |",
            "|--------|-------|",
            f"| File I/O operations | {summary.get('file_io_count', 'N/A')} |",
            f"| Database operations | {summary.get('database_op_count', 'N/A')} |",
            f"| Network I/O | {summary.get('network_io_count', 'N/A')} |",
            f"| Transformation points | "
            f"{summary.get('transformation_point_count', 'N/A')} |",
            f"| Files with I/O | {summary.get('files_with_io', 'N/A')} |",
        ]
        return lines

    def _table_service_components(self, data: dict) -> list[str]:
        packages = data.get("packages", [])
        lines = [
            "| Package | Files | Ca | Ce | Instability | Class |",
            "|---------|-------|----|----|-------------|-------|",
        ]
        for pkg in sorted(packages, key=lambda p: p.get("file_count", 0),
                          reverse=True)[:30]:
            name = pkg.get("name", "")
            lines.append(
                f"| `{name}` | {pkg.get('file_count', 0)} "
                f"| {pkg.get('afferent_coupling', 0)} "
                f"| {pkg.get('efferent_coupling', 0)} "
                f"| {pkg.get('instability', 0):.2f} "
                f"| {pkg.get('classification', '')} |"
            )
        return lines

    def _table_user_journeys(self, data: dict) -> list[str]:
        journeys = data.get("journeys", [])
        lines = [
            "| Entry | Type | Depth | Functions | Outcomes |",
            "|-------|------|-------|-----------|----------|",
        ]
        for j in journeys[:30]:
            command = j.get("command", j.get("entry_type", ""))
            etype = j.get("entry_type", "")
            depth = j.get("trace_depth", 0)
            funcs = j.get("functions_reached", 0)
            outcomes = len(j.get("outcomes", []))
            lines.append(f"| `{command}` | {etype} | {depth} | {funcs} | {outcomes} |")
        return lines

    # -----------------------------------------------------------------------
    # Helper methods
    # -----------------------------------------------------------------------

    def _compute_coverage(self, layer_def: dict, data: dict) -> float | None:
        """Compute coverage percentage for a layer, if data is available."""
        summary = data.get("summary", {})
        meta = data.get("meta", {})

        # Different layers have different coverage metrics
        num = layer_def["num"]
        if num == 1:
            # Directories covered
            return 100.0 if data.get("directories") else None
        elif num == 2:
            # Files analyzed at AST level vs total files in the manifest.
            # For multi-language repos, only Python files get full AST analysis,
            # so coverage reflects what fraction of ALL code files are analyzed.
            analyzed = data.get("files_analyzed", 0)
            if analyzed <= 0:
                return None
            # Use layer 1 total file count if available for accurate coverage
            layer1 = self.layers.get("layer1_repo_surface", {})
            total_files = self._layer1_total_files(layer1)
            if total_files > 0:
                failed = len(data.get("files_failed_parse", []))
                return ((analyzed - failed) / total_files) * 100
            # Last fallback: analyzed/analyzed (Python-only view)
            failed = len(data.get("files_failed_parse", []))
            return ((analyzed - failed) / analyzed) * 100
        elif num == 7:
            packages = data.get("packages", [])
            return 100.0 if packages else None
        elif num == 8:
            journeys = data.get("journeys", [])
            journey_summary = summary.get("total_journeys", 0)
            if journey_summary > 0:
                return 100.0
            return 100.0 if journeys else None

        # Generic: has data = 100%, no data = None
        return 100.0 if data and data != {} else None

    @staticmethod
    def _layer1_total_files(layer1: dict) -> int:
        """Get the total file count from layer 1 data.

        Tries completeness.manifest_total first, falls back to summing
        language file counts.
        """
        completeness = layer1.get("completeness", {})
        total = completeness.get("manifest_total", 0)
        if total > 0:
            return total
        languages = layer1.get("languages", {})
        return sum(info.get("file_count", 0) for info in languages.values())

    def _coverage_label(self, layer_def: dict, data: dict, pct: int) -> str:
        """Build a human-readable coverage label for a layer card.

        For layer 2, shows "N/M files analyzed (X%)" so multi-language repos
        don't misleadingly claim 100% when only Python files are parsed.
        """
        num = layer_def["num"]
        if num == 2:
            analyzed = data.get("files_analyzed", 0)
            failed = len(data.get("files_failed_parse", []))
            effective = analyzed - failed
            layer1 = self.layers.get("layer1_repo_surface", {})
            total_files = self._layer1_total_files(layer1)
            if total_files > 0 and total_files != effective:
                return f"{effective}/{total_files} files analyzed ({pct}%)"
        return f"{pct}% coverage"

    def _format_summary_stats(self, layer_def: dict, summary: dict) -> list[str]:
        """Format summary stats as compact text items."""
        items = []
        for key, value in list(summary.items())[:4]:
            clean_key = key.replace("_", " ").replace("count", "").strip()
            if isinstance(value, (int, float)):
                items.append(f"**{clean_key}**: {value}")
            elif isinstance(value, list):
                items.append(f"**{clean_key}**: {len(value)}")
        return items

    def _generate_legend(self, layer_def: dict) -> list[str]:
        """Generate legend table for a layer page."""
        num = layer_def["num"]
        legends = {
            1: [
                "| Symbol | Meaning |",
                "|--------|---------|",
                "| Rectangle | Directory |",
                "| Arrow | Parent-child relationship |",
                "| Label | `name` / `py count` / `total count` |",
            ],
            2: [
                "| Symbol | Meaning |",
                "|--------|---------|",
                "| Rectangle | Source file |",
                "| Arrow | Import dependency |",
                "| `refs: N` | Total reference count |",
            ],
            3: [
                "| Symbol | Meaning |",
                "|--------|---------|",
                "| `ext` subgraph | External dependencies |",
                "| `int` subgraph | Internal packages |",
                "| Edge label N | Import count between packages |",
            ],
            4: [
                "| Symbol | Meaning |",
                "|--------|---------|",
                "| Rounded rect | External process/command |",
                "| Hexagon | Port binding |",
                "| Rectangle | Source module |",
                "| Arrow | Invocation |",
            ],
            5: [
                "| Symbol | Meaning |",
                "|--------|---------|",
                "| ROOT | `amplihack` CLI entry |",
                "| Rectangle | Subcommand |",
                "| Label | `name` / `arg count` |",
                "| Arrow | Parent-child command |",
            ],
            6: [
                "| Symbol | Meaning |",
                "|--------|---------|",
                "| Stadium | Read operation |",
                "| Parallelogram | Write operation |",
                "| Cylinder | Database operation |",
                "| Diamond | Transformation function |",
            ],
            7: [
                "| Symbol | Meaning |",
                "|--------|---------|",
                "| Subgraph | Package classification |",
                "| Rectangle | Package |",
                "| `I=` | Instability metric (0=stable, 1=unstable) |",
                "| Edge label N | Coupling count |",
            ],
            8: [
                "| Symbol | Meaning |",
                "|--------|---------|",
                "| Actor | User |",
                "| Participant | Module/component |",
                "| Solid arrow | Synchronous call |",
                "| Dashed arrow | Response/return |",
            ],
        }
        return legends.get(num, ["*No legend defined.*"])

    def _generate_findings(self, layer_def: dict, data: dict) -> list[str]:
        """Generate key findings from layer data."""
        summary = data.get("summary", {})
        findings = []

        if not summary and not data:
            return findings

        num = layer_def["num"]

        if num == 1:
            dirs = data.get("directories", [])
            entries = data.get("entry_points", [])
            findings.append(f"{len(dirs)} directories discovered")
            if entries:
                findings.append(f"{len(entries)} entry points identified")

        elif num == 2:
            total_defs = summary.get("total_definitions", 0)
            dead = summary.get("potentially_dead_count", 0)
            if total_defs:
                findings.append(f"{total_defs} total definitions across all files")
            if dead:
                pct = (dead / max(1, total_defs)) * 100
                findings.append(
                    f"{dead} potentially dead definitions ({pct:.1f}% of total)"
                )
            no_all = summary.get("files_without_all", 0)
            if no_all:
                findings.append(f"{no_all} files without `__all__` exports")

        elif num == 3:
            unused = data.get("unused_dependencies", [])
            cycles = data.get("circular_dependencies", [])
            if unused:
                findings.append(
                    f"{len(unused)} unused dependencies: {', '.join(unused[:5])}"
                )
            if cycles:
                findings.append(f"{len(cycles)} circular dependency chains detected")
            else:
                findings.append("No circular dependencies detected")

        elif num == 4:
            sub_count = summary.get("subprocess_call_count", 0)
            env_count = summary.get("env_var_count", 0)
            if sub_count:
                findings.append(f"{sub_count} subprocess calls across "
                                f"{summary.get('unique_subprocess_files', '?')} files")
            if env_count:
                findings.append(f"{env_count} environment variable reads")

        elif num == 5:
            cli_count = summary.get("cli_command_count", 0)
            route_count = summary.get("http_route_count", 0)
            recipe_count = summary.get("recipe_count", 0)
            if cli_count:
                findings.append(f"{cli_count} CLI commands")
            if route_count:
                findings.append(f"{route_count} HTTP routes")
            if recipe_count:
                findings.append(f"{recipe_count} recipes defined")

        elif num == 6:
            io_count = summary.get("file_io_count", 0)
            db_count = summary.get("database_op_count", 0)
            if io_count:
                findings.append(f"{io_count} file I/O operations")
            if db_count:
                findings.append(f"{db_count} database operations")

        elif num == 7:
            pkgs = data.get("packages", [])
            core = [p for p in pkgs if p.get("classification") == "core"]
            leaf = [p for p in pkgs if p.get("classification") == "leaf"]
            if pkgs:
                findings.append(f"{len(pkgs)} packages analyzed")
            if core:
                names = ", ".join(p.get("name", "").split(".")[-1] for p in core[:3])
                findings.append(f"{len(core)} core packages: {names}")
            if leaf:
                findings.append(f"{len(leaf)} leaf packages (no dependents)")

        elif num == 8:
            total = summary.get("total_journeys", 0)
            unreachable = summary.get("unreachable_function_count", 0)
            if total:
                findings.append(f"{total} user journeys traced")
            if unreachable:
                findings.append(
                    f"{unreachable} functions unreachable from any entry point"
                )

        return findings

    def _generate_detail_section(self, layer_def: dict, data: dict) -> list[str]:
        """Generate collapsed detail section for a layer."""
        summary = data.get("summary", {})
        if not summary:
            return ["*No detailed data available.*"]

        lines = ["**Summary metrics:**", ""]
        for key, value in summary.items():
            clean_key = key.replace("_", " ").title()
            if isinstance(value, list):
                lines.append(f"- **{clean_key}**: {len(value)} items")
                for item in value[:10]:
                    lines.append(f"    - `{item}`")
                if len(value) > 10:
                    lines.append(f"    - ... and {len(value) - 10} more")
            elif isinstance(value, dict):
                lines.append(f"- **{clean_key}**:")
                for k, v in list(value.items())[:15]:
                    lines.append(f"    - `{k}`: {v}")
            else:
                lines.append(f"- **{clean_key}**: {value}")

        return lines

    def _generate_crossrefs(self, layer_def: dict) -> list[str]:
        """Generate cross-reference links to related layers."""
        num = layer_def["num"]
        refs: dict[int, list[int]] = {
            1: [2, 7],
            2: [1, 3, 7, 8],
            3: [2, 7],
            4: [6, 8],
            5: [8],
            6: [4, 8],
            7: [2, 3],
            8: [2, 4, 5, 6],
        }
        related = refs.get(num, [])
        links = []
        for r in related:
            for ld in LAYER_DEFS:
                if ld["num"] == r:
                    links.append(
                        f"[Layer {r}: {ld['name']}](../{ld['slug']}/)"
                    )
                    break
        return links

    def _write_page(self, rel_path: str, content: str):
        """Write a page to output_dir / rel_path."""
        full_path = self.output_dir / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
        print(f"  Wrote {full_path}")


def main():
    """CLI entry point for atlas renderer."""
    parser = argparse.ArgumentParser(
        description="Render atlas JSON data into mkdocs-material pages"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("atlas_output"),
        help="Directory containing layer JSON files (default: atlas_output/)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/atlas"),
        help="Directory to write rendered pages (default: docs/atlas/)",
    )
    args = parser.parse_args()

    if not args.data_dir.exists():
        print(f"Error: data directory {args.data_dir} does not exist.")
        print("Run the extraction pipeline first: python -m scripts.atlas.run_all")
        raise SystemExit(1)

    renderer = AtlasRenderer(data_dir=args.data_dir, output_dir=args.output_dir)
    print(f"Loading layer data from {args.data_dir}...")
    layers = renderer.load_all_layers()
    print(f"Loaded {len(layers)} layer(s)")

    print(f"Rendering atlas pages to {args.output_dir}...")
    renderer.render_all()
    print("Done.")


if __name__ == "__main__":
    main()
