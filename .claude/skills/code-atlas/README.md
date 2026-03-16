# Code Atlas

Builds comprehensive, living architecture atlases as multi-layer documents derived from code-first truth. Language-agnostic (Go, TypeScript, Python, .NET, Rust, Java).

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

A complete atlas is six layers plus a bug report:

| Layer | Content |
|-------|---------|
| Layer 1 — Runtime Topology | Service graph: containers, ports, external dependencies |
| Layer 2 — Compile-time Dependencies | Package graphs, version constraints, circular dependency detection |
| Layer 3 — HTTP Routing | Route inventory, request/response contracts, middleware chain |
| Layer 4 — Data Flows | DTO/schema chain from HTTP boundary to storage |
| Layer 5 — User Journey Scenarios | Entry-point to outcome scenario graphs |
| Layer 6 — Exhaustive Inventory | All services, env vars, data stores, external deps in tables |

Every layer is committed to `docs/atlas/` as `.mmd`, `.dot`, `.svg`, and a `README.md` narrative. The atlas is regeneratable at any time from code alone.

## Features

### Code-First Truth

All diagrams derive from real code: parsed imports, route definitions, env var references, Docker Compose ports, OpenAPI specs. No invented topology, no stale docs carried forward.

### Two-Pass Bug Hunting

**Pass 1 — Build the atlas**: Structural anomalies surface naturally while mapping graphs.

**Pass 2 — Contradiction hunt**: Reviewer agent cross-checks every layer for route/DTO mismatches, orphaned env vars, dead code paths, and schema drift.

Every filed bug includes code evidence extracted from the atlas — no speculation.

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

## How It Works

```
code-atlas (orchestrator)
├── Explores code (language-agnostic grep, AST, config parsing)
├── Builds 6 atlas layers
├── Runs 2-pass bug hunt
├── Checks staleness via git diff
└── Delegates to:
    ├── code-visualizer       — Python AST module analysis
    ├── mermaid-diagram-generator — Mermaid syntax and formatting
    ├── visualization-architect   — Complex DOT layouts
    ├── analyzer              — Deep dependency mapping
    └── reviewer              — Contradiction hunting
```

## Skill Architecture

```
skills/code-atlas/
├── SKILL.md          # Full protocol: 6 layers, bug-hunt workflow, CI patterns
├── API-CONTRACTS.md  # Typed contracts for all 5 delegations + filesystem layout
├── SECURITY.md       # Security controls (SEC-01–SEC-10): required before implementing
├── tests/
│   ├── test_staleness_triggers.sh   # 30+ assertions verifying trigger patterns
│   ├── test_security_controls.md    # SEC-01–SEC-10 manual/automated test plans
│   └── test_scenarios.md            # 6 end-to-end acceptance scenarios
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

| Principle | How This Skill Follows It |
|-----------|--------------------------|
| **Ruthless Simplicity** | Code is truth; every diagram regeneratable from one command |
| **Zero-BS** | Real parsing, no invented topology, honest about heuristic limits |
| **Modular Design** | One brick (atlas orchestration), delegates diagram work to specialist bricks |

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
