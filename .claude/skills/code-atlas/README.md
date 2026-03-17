# Code Atlas

Builds comprehensive, living architecture atlases as multi-layer documents derived from code-first truth. Language-agnostic (Go, TypeScript, Python, .NET, Rust, Java). Version 1.1.0 adds per-service component architecture (Layer 7), cross-file AST+LSP symbol bindings with dead code detection (Layer 8), a three-pass bug hunt, and a strict no-silent-degradation density guard.

## Quick Start

Simply describe what you want:

```
Build a code atlas for this repository
```

```
Check if the atlas is stale after my last commit
```

```
Hunt for structural bugs using the atlas
```

```
Publish the atlas to GitHub Pages
```

## What It Produces

A complete atlas is eight layers plus a bug report:

| Layer                                    | Content                                                            |
| ---------------------------------------- | ------------------------------------------------------------------ |
| Layer 1 — Runtime Topology               | Service graph: containers, ports, external dependencies            |
| Layer 2 — Compile-time Dependencies      | Package graphs, version constraints, circular dependency detection |
| Layer 3 — API Contracts                   | Route inventory, request/response contracts, middleware chain      |
| Layer 4 — Data Flows                     | DTO/schema chain from HTTP boundary to storage                     |
| Layer 5 — User Journey Scenarios         | Entry-point to outcome scenario graphs                             |
| Layer 6 — Exhaustive Inventory           | All services, env vars, data stores, external deps in tables       |
| Layer 7 — Service Component Architecture | Per-service module/package diagrams; internal coupling mapping     |
| Layer 8 — AST+LSP Symbol Bindings        | Cross-file references, dead code detection, interface mismatches   |

Every layer is committed to `docs/atlas/` as `.mmd`, `.dot`, `.svg`, and a `README.md` narrative. The atlas is regeneratable at any time from code alone.

## Features

### Code-First Truth

All diagrams derive from real code: parsed imports, route definitions, env var references, Docker Compose ports, OpenAPI specs. No invented topology, no stale docs carried forward.

### Three-Pass Bug Hunting

**Pass 1 — Comprehensive Build + Hunt**: Build all 8 layers. Structural anomalies surface while mapping graphs. Reviewer agent cross-checks every layer for route/DTO mismatches, orphaned env vars, dead code paths, and schema drift.

**Pass 2 — Fresh-Eyes Cross-Check**: A new context window re-examines the atlas independently, without access to Pass 1 conclusions. Confirms, overturns, or escalates Pass 1 findings. Prevents anchoring bias.

**Pass 3 — Scenario Deep-Dive**: Every Layer 5 user journey is traced end-to-end through Layers 3, 4, 1, 7, and 8. Each journey receives a formal verdict: `PASS`, `FAIL`, or `NEEDS_ATTENTION`, with an evidence table and rationale paragraph.

Every filed bug includes code evidence extracted from the atlas — no speculation. All evidence uses relative file paths (never absolute).

### Staleness Detection

Watches 11 file-pattern triggers against `git diff`. Reports exactly which layers are stale and which rebuild command to run. Fast — no rebuild, just a diff read.

```
Layer 1 STALE: docker-compose.yml (changed in abc1234)
Layer 3 STALE: src/api/routes/user-routes.ts (changed in abc1234)
Run: /code-atlas rebuild layer1 layer3
```

### CI Integration

Three ready-to-use GitHub Actions patterns:

- **Pattern 1**: Post-merge staleness gate with auto-commit of refreshed diagrams
- **Pattern 2**: PR impact check — annotates which atlas layers a PR touches
- **Pattern 3**: Scheduled weekly full rebuild with issue creation on failure

See `SKILL.md` for full workflow YAML.

### Publication

Outputs GitHub Pages-ready `docs/atlas/` structure. Compatible with mkdocs-material and plain GitHub Pages. SVGs are committed so no render step is needed at read time.

### Diagram Density Guard

When any diagram has >50 nodes or >100 edges, the skill pauses and asks:

```
This diagram has {N} nodes and {M} edges, which may render poorly.
Please choose:
  (a) Full diagram anyway
  (b) Simplified/clustered diagram
  (c) Table representation
```

A table is only produced if the user explicitly chooses option `(c)`. The skill **never** silently substitutes a table for a diagram (FORBIDDEN_PATTERNS.md §2 compliance). Thresholds are configurable per-invocation via `--density-threshold nodes=N,edges=M`.

## How It Works

```
code-atlas (orchestrator)
├── Explores code (language-agnostic grep, AST, config parsing)
├── Builds 8 atlas layers
├── Density guard: prompts user when node/edge count is high (all layers)
├── Runs 3-pass bug hunt
├── Checks staleness via git diff
└── Delegates to:
    ├── code-visualizer       — Python AST module analysis (Layer 2, Layer 7)
    ├── lsp-setup             — Symbol queries, dead code, interface mismatches (Layer 8)
    ├── mermaid-diagram-generator — Mermaid syntax and formatting
    ├── visualization-architect   — Complex DOT layouts
    ├── analyzer              — Deep dependency mapping
    └── reviewer              — Contradiction hunting (Passes 1, 2, 3)
```

## Skill Architecture

```
skills/code-atlas/
├── SKILL.md          # Full protocol: 8 layers, 3-pass bug hunt, density guard, Appendix A
├── API-CONTRACTS.md  # v1.1.0: typed contracts for all 6 delegations + filesystem layout
├── SECURITY.md       # Security controls (SEC-01–SEC-19): required before implementing
├── tests/
│   ├── run_all_tests.sh             # 10-suite test runner
│   ├── test_staleness_triggers.sh   # 30+ assertions verifying trigger patterns
│   ├── test_rebuild_script.sh       # rebuild-atlas-all.sh behavior assertions
│   ├── test_security_controls.sh    # SEC-01–SEC-10 automated test plans
│   ├── test_security_controls.md    # SEC-01–SEC-19 manual test plans
│   ├── test_atlas_output_structure.sh # docs/atlas/ directory contract assertions
│   ├── test_layer_contracts.sh      # Per-layer output contracts (Layers 1–8)
│   ├── test_bug_hunt_workflow.sh    # Three-pass bug hunt report format
│   ├── test_ci_workflow.sh          # CI YAML structure and script path checks
│   ├── test_publication_workflow.sh # SVG generation and GitHub Pages readiness
│   ├── test_layer7_8.sh             # Layer 7/8 output structure + security assertions
│   ├── test_no_silent_degradation.sh # Density guard compliance assertions
│   └── test_scenarios.md            # 8 end-to-end acceptance scenarios
└── README.md         # This file
```

## CI Integration

Three GitHub Actions patterns in `.github/workflows/atlas-ci.yml`:

- **Pattern 1** (`atlas-staleness-gate`): Post-merge staleness detection on push to `main`
- **Pattern 2** (`atlas-pr-impact`): PR architecture impact check with artifact upload
- **Pattern 3** (`atlas-scheduled-rebuild`): Weekly full rebuild, creates issue on failure

## User Documentation

Full documentation in `docs/`:

- [Getting Started](../../../docs/tutorials/code-atlas-getting-started.md) — 30-minute tutorial
- [Daily Use Recipes](../../../docs/howto/use-code-atlas.md) — 15 practical how-tos
- [Add Custom Journeys](../../../docs/howto/add-custom-journeys.md)
- [Publish to GitHub Pages](../../../docs/howto/publish-atlas-to-github-pages.md)
- [Configure Staleness Triggers](../../../docs/howto/configure-staleness-triggers.md)
- [Full Reference](../../../docs/reference/code-atlas-reference.md) — All flags, error codes, schemas
- [Layers Explained](../../../docs/reference/atlas-layers-explained.md) — Per-layer bug detection guide

## Limitations (Important)

- **Not a static analysis tool**: Uses grep, AST, and config parsing — not a compiler. Dynamic dispatch is not traced.
- **Staleness is heuristic**: Git diff pattern matching, not semantic analysis. False positives are possible on rename-only changes.
- **Python AST delegation**: For Python module graphs, delegates to `code-visualizer` which is Python-only.
- **SVG rendering requires Graphviz/Mermaid CLI**: CI environments need these installed to render committed SVGs.
- **Bug hunting is probabilistic**: Pass 2 surfaces high-probability structural bugs. Human review is still required before filing.

See `SKILL.md` for complete limitations and accuracy expectations.

## Philosophy Alignment

| Principle               | How This Skill Follows It                                                    |
| ----------------------- | ---------------------------------------------------------------------------- |
| **Ruthless Simplicity** | Code is truth; every diagram regeneratable from one command                  |
| **Zero-BS**             | Real parsing, no invented topology, honest about heuristic limits            |
| **Modular Design**      | One brick (atlas orchestration), delegates diagram work to specialist bricks |

## Security Controls

- Secret values are never emitted: `.env` files and K8s Secrets are parsed for key names only
- Path traversal prevented via `realpath()` boundary validation
- Mermaid/DOT/SVG labels are sanitized before rendering (XSS prevention)
- Bug report `code_quote` fields are redacted of any credential patterns

See `SECURITY.md` for the full control list.

## Integration

Works with:

- `code-visualizer` skill for Python module graphs
- `mermaid-diagram-generator` skill for diagram syntax
- `visualization-architect` agent for complex DOT diagrams
- `analyzer` agent for deep dependency investigation
- `reviewer` agent for contradiction hunting
- GitHub Actions for CI staleness gates and scheduled rebuilds

## Dependencies

- **Required**: mermaid-diagram-generator skill
- **Recommended**: Graphviz (`dot` CLI) for DOT rendering, Mermaid CLI for SVG export
- **CI**: GitHub Actions (or equivalent) for automated staleness detection
- **Optional**: mkdocs-material for documentation site publication
