# Code Atlas

Builds comprehensive, living architecture atlases as multi-layer documents derived from
code-first truth. Language-agnostic (Go, TypeScript, Python, .NET, Rust, Java).

## Quick Start

```
Build a code atlas for this repository
```

```
Run code atlas bug hunting passes on this service
```

```
Check if the atlas is stale after my last commit
```

```
Publish the atlas to GitHub Pages
```

## What It Produces

A complete atlas has eight layers plus a bug report. Layer definitions are in
[LAYERS.yaml](./LAYERS.yaml).

| Slug                 | Name                           | Description                                                   |
| -------------------- | ------------------------------ | ------------------------------------------------------------- |
| `repo-surface`       | Repository Surface             | All source files, project structure, build systems            |
| `ast-lsp-bindings`   | AST+LSP Symbol Bindings        | Cross-file symbol references, dead code, interface mismatches |
| `compile-deps`       | Compile-time Dependencies      | Package imports, dependency trees, circular deps              |
| `runtime-topology`   | Runtime Topology               | Services, containers, ports, inter-service connections        |
| `api-contracts`      | API Contracts                  | HTTP routes, gRPC, GraphQL, middleware chains                 |
| `data-flow`          | Data Flow                      | DTO-to-storage chains, transformation steps                   |
| `service-components` | Service Component Architecture | Per-service internal module/package structure                 |
| `user-journeys`      | User Journey Scenarios         | End-to-end paths from entry to outcome                        |

Every layer is committed to `docs/atlas/{slug}/` with `.mmd`, `.dot`, `.svg`, and a
`README.md` narrative. The atlas is regeneratable at any time from code alone.

Defaults to both Graphviz DOT and Mermaid formats. User can override to single format.

## Features

- **Code-First Truth**: All diagrams derive from real code -- parsed imports, route
  definitions, env var references, Docker Compose ports, OpenAPI specs
- **Three-Pass Bug Hunting**: Pass 1 (build + hunt), Pass 2 (fresh-eyes cross-check),
  Pass 3 (per-journey verdicts)
- **Staleness Detection**: Git diff pattern matching against layer triggers
- **CI Integration**: Three GitHub Actions patterns (post-merge, PR impact, scheduled rebuild)
- **Publication**: GitHub Pages-ready structure, mkdocs compatible
- **Density Management**: Auto-splits dense diagrams by package/service boundary

## File Structure

```
skills/code-atlas/
  SKILL.md              # Core instructions (under 500 lines)
  LAYERS.yaml           # Layer definitions (single source of truth)
  SECURITY.md           # Security controls (SEC-01 through SEC-19)
  API-CONTRACTS.md      # Typed contracts for all delegations + filesystem layout
  bug-hunt-guide.md     # Three-pass bug hunt checklists and templates
  publication-guide.md  # CI, GitHub Pages, mkdocs, SVG rendering
  examples.md           # Per-layer Mermaid/DOT examples and diagram type guidance
  reference.md          # Staleness triggers, error codes, Kuzu schema, language coverage
  README.md             # This file
  tests/                # Test suites
```

## Delegation Architecture

```
code-atlas (orchestrator)
  code-visualizer       Python AST module analysis
  mermaid-diagram-generator   Mermaid syntax and formatting
  lsp-setup             Symbol queries, dead code (ast-lsp-bindings layer)
  visualization-architect     Complex DOT layouts
  analyzer              Deep dependency mapping
  reviewer              Contradiction hunting (all 3 passes)
```

## Limitations

- **Not a static analysis tool**: Uses grep, AST, config parsing -- not a compiler
- **Staleness is heuristic**: Git diff patterns, not semantic analysis
- **Bug hunting is probabilistic**: Human review required before filing
- **Single-repository focus**: Cross-repo deps require manual configuration

See [SKILL.md](./SKILL.md) for complete details.

## Philosophy Alignment

| Principle               | How This Skill Follows It                                       |
| ----------------------- | --------------------------------------------------------------- |
| **Ruthless Simplicity** | Code is truth; every diagram regeneratable from one command     |
| **Zero-BS**             | Real parsing, no invented topology, honest about limits         |
| **Modular Design**      | One brick (atlas orchestration), delegates to specialist bricks |
