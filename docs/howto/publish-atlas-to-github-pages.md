---
type: howto
skill: code-atlas
updated: 2026-03-16
---

# How to Publish Code Atlas to GitHub Pages

Publish your atlas as a browsable documentation site at `https://<org>.github.io/<repo>/atlas/`.

---

## Prerequisites

- Atlas already built (`docs/atlas/` exists with content)
- GitHub repository with GitHub Pages enabled
- mkdocs installed: `pip install mkdocs mkdocs-material mkdocs-mermaid2-plugin`

---

## Step 1: Add atlas to mkdocs.yml

Add these entries to your `mkdocs.yml`:

```yaml
nav:
  - Code Atlas:
      - Overview: atlas/index.md
      - Layer 1 — Runtime Topology: atlas/layer1-runtime/README.md
      - Layer 2 — Dependencies: atlas/layer2-dependencies/README.md
      - Layer 3 — HTTP Routing: atlas/layer3-routing/README.md
      - Layer 4 — Data Flow: atlas/layer4-dataflow/README.md
      - Layer 5 — User Journeys: atlas/layer5-journeys/README.md
      - Layer 6 — Inventory: atlas/layer6-inventory/services.md
      - Bug Reports: atlas/bug-reports/

plugins:
  - search
  - mermaid2
```

---

## Step 2: Enable GitHub Pages

In your repository settings:

1. Go to **Settings → Pages**
2. Source: **GitHub Actions**

---

## Step 3: Add the deployment workflow

Create `.github/workflows/docs.yml`:

```yaml
name: Deploy Documentation

on:
  push:
    branches: [main]
    paths:
      - "docs/**"
      - "mkdocs.yml"

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install mkdocs
        run: pip install mkdocs mkdocs-material mkdocs-mermaid2-plugin

      - name: Build docs
        run: mkdocs build

      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./site
```

---

## Step 4: Trigger a publish

Commit any change to `docs/` or run:

```
/code-atlas publish=true
```

---

## Step 5: Verify publication

After the workflow completes:

```bash
# Check atlas index is reachable
curl -sf "https://<org>.github.io/<repo>/atlas/" | grep "Code Atlas" && \
    echo "Atlas published successfully" || \
    echo "WARNING: Atlas index page not found"

# Check specific layer
curl -sf "https://<org>.github.io/<repo>/atlas/layer1-runtime/" | grep -q "Runtime" && \
    echo "Layer 1 published" || \
    echo "WARNING: Layer 1 not found"
```

---

## Troubleshooting

**SVGs not rendering in GitHub Pages**
SVG files must be committed to `docs/atlas/`. Run the SVG generation commands from `SKILL.md` before pushing. See [use-code-atlas.md](./use-code-atlas.md#render-svg-files-for-all-layers).

**Mermaid diagrams not rendering**
Ensure `mkdocs-mermaid2-plugin` is installed and listed in `mkdocs.yml` plugins. The plugin adds Mermaid.js to the site automatically.

**404 on atlas pages**
Verify `docs/atlas/` exists and the mkdocs.yml nav entries match the actual file paths. Run `mkdocs build` locally to see any warnings.
