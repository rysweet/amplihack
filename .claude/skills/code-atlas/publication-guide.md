# Publication Guide

CI integration, GitHub Pages deployment, mkdocs configuration, and SVG rendering for code-atlas.

## Output Directory Structure

```
docs/
  atlas/
    index.md                         # Atlas landing page with layer overview
    repo-surface/
      *.dot, *.mmd, *.svg, README.md
    ast-lsp-bindings/
      README.md                      # Line 1: **Mode:** lsp-assisted|static-approximation
      symbol-references.mmd
      dead-code.md
      mismatched-interfaces.md
    compile-deps/
      dependencies.mmd, dependencies.svg
      inventory.md
      README.md
    runtime-topology/
      topology.dot, topology.mmd, topology.svg
      README.md
    api-contracts/
      routing.mmd, routing.svg
      route-inventory.md
      README.md
    data-flow/
      dataflow.mmd, dataflow.svg
      README.md
    user-journeys/
      journey-{name}.mmd, *.svg
      README.md
    service-components/
      README.md
      {service-name}.mmd             # One per service (SEC-11: name sanitised)
      {service-name}.svg
    bug-reports/
      {YYYY-MM-DD}-pass{N}-{slug}.md
```

## SVG Generation Commands

### Graphviz DOT to SVG

```bash
dot -Tsvg docs/atlas/runtime-topology/topology.dot \
  -o docs/atlas/runtime-topology/topology.svg
```

### Mermaid to SVG

Requires `mmdc` from `@mermaid-js/mermaid-cli`:

```bash
mmdc -i docs/atlas/compile-deps/dependencies.mmd \
     -o docs/atlas/compile-deps/dependencies.svg \
     --backgroundColor transparent
```

### Batch Render All Diagrams

```bash
# Mermaid files
find docs/atlas -name "*.mmd" | while read f; do
  svg="${f%.mmd}.svg"
  mmdc -i "$f" -o "$svg" --backgroundColor transparent
  echo "Rendered: $svg"
done

# DOT files
find docs/atlas -name "*.dot" | while read f; do
  svg="${f%.dot}.svg"
  dot -Tsvg "$f" -o "$svg"
  echo "Rendered: $svg"
done
```

## CI Integration Patterns

### Pattern 1: Post-Merge Atlas Refresh Gate

Runs on push to main. Detects stale layers and rebuilds them.

```yaml
# .github/workflows/atlas-refresh.yml
name: Refresh Code Atlas

on:
  push:
    branches: [main]
    paths:
      - "src/**"
      - "services/**"
      - "docker-compose*.yml"
      - "**/package.json"
      - "**/go.mod"
      - "**/*.csproj"

jobs:
  refresh-atlas:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Detect stale atlas layers
        id: stale
        run: |
          bash scripts/check-atlas-staleness.sh --strict > stale-report.txt
          cat stale-report.txt
          echo "stale=$(wc -l < stale-report.txt)" >> $GITHUB_OUTPUT

      - name: Rebuild stale layers
        if: steps.stale.outputs.stale != '0'
        run: |
          echo "Atlas rebuild triggered -- stale layers detected"
          git config user.name "atlas-bot"
          git config user.email "atlas@ci"
          git add docs/atlas/
          git commit -m "chore: refresh code atlas [skip ci]" || echo "No changes"
          git push
```

### Pattern 2: PR Architecture Impact Check

Runs on PRs. Annotates which atlas layers the PR touches.

```yaml
# .github/workflows/pr-atlas-impact.yml
name: PR Atlas Impact

on:
  pull_request:
    branches: [main]

jobs:
  atlas-impact:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - name: Detect atlas impact
        run: |
          git diff --name-only origin/main...HEAD | while read f; do
            case "$f" in
              *route*|*controller*) echo "api-contracts layer may need update" ;;
              *docker-compose*) echo "runtime-topology layer may need update" ;;
              *dto*|*schema*) echo "data-flow layer may need update" ;;
            esac
          done
```

### Pattern 3: Scheduled Full Rebuild

Runs weekly. Creates an issue on failure.

```yaml
# .github/workflows/scheduled-atlas.yml
name: Scheduled Atlas Rebuild

on:
  schedule:
    - cron: "0 6 * * 1" # Every Monday 6am UTC
  workflow_dispatch:

jobs:
  full-atlas-rebuild:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Full atlas rebuild
        run: bash scripts/rebuild-atlas-all.sh
      - name: Open issue if stale
        if: failure()
        run: gh issue create --title "Code atlas rebuild failed" --body "See workflow run"
```

## mkdocs Integration

Add to your `mkdocs.yml`:

```yaml
nav:
  - Code Atlas:
      - Overview: atlas/index.md
      - Repository Surface: atlas/repo-surface/README.md
      - AST+LSP Bindings: atlas/ast-lsp-bindings/README.md
      - Compile-time Deps: atlas/compile-deps/README.md
      - Runtime Topology: atlas/runtime-topology/README.md
      - API Contracts: atlas/api-contracts/README.md
      - Data Flow: atlas/data-flow/README.md
      - Service Components: atlas/service-components/README.md
      - User Journeys: atlas/user-journeys/README.md
      - Bug Reports: atlas/bug-reports/

plugins:
  - search
  - mermaid2 # pip install mkdocs-mermaid2-plugin
```

## GitHub Pages Deployment

```yaml
# .github/workflows/docs.yml
- name: Deploy docs with atlas
  uses: peaceiris/actions-gh-pages@v3
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    publish_dir: ./site # mkdocs build output

- name: Verify atlas pages
  run: |
    curl -sf "https://<org>.github.io/<repo>/atlas/" | grep "Code Atlas" || \
      echo "WARNING: Atlas index page not found"
```

## Prerequisites for CI

- **Graphviz**: `apt-get install graphviz` (for DOT rendering)
- **Mermaid CLI**: `npm install -g @mermaid-js/mermaid-cli` (for Mermaid SVG export)
- **mkdocs**: `pip install mkdocs mkdocs-material mkdocs-mermaid2-plugin` (for docs site)
