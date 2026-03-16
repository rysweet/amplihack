---
type: howto
skill: code-atlas
updated: 2026-03-16
---

# How to Use Code Atlas

Common tasks and recipes for daily code atlas use.

---

## Build a full atlas

```
Build a complete code atlas for this repository
```

Produces 6 layers + bug reports in `docs/atlas/`. Takes 2–5 minutes.

---

## Rebuild a single layer

When only one area of the code changed:

```
/code-atlas rebuild layer3
```

Or via shell:

```bash
bash scripts/check-atlas-staleness.sh  # find which layers are stale
```

---

## Run bug-hunting passes only

If you already have an atlas and want to re-run bug detection:

```
Run code atlas bug hunting passes on this service
```

This runs both Pass 1 (contradiction hunt) and Pass 2 (journey trace) against the current atlas state.

---

## Check which layers are stale

```bash
# Against last commit
bash scripts/check-atlas-staleness.sh

# Against a PR (compares to origin/main)
bash scripts/check-atlas-staleness.sh --pr

# Between two specific commits
bash scripts/check-atlas-staleness.sh abc1234 def5678
```

Exit codes: `0` = fresh, `1` = stale layers found, `2` = usage error.

---

## Build atlas for a specific service subdirectory

```
/code-atlas codebase_path=services/billing
```

Builds an atlas scoped to `services/billing/` only. Useful for microservices with independent atlas tracking.

---

## Get DOT format instead of Mermaid

```
/code-atlas diagram_formats=dot
```

Produces Graphviz DOT files (`.dot`) instead of Mermaid (`.mmd`). Requires `graphviz` installed for SVG rendering.

---

## Render SVG files for all layers

```bash
# Render all .mmd files to SVG (requires mermaid-cli)
find docs/atlas -name "*.mmd" | while read f; do
    svg="${f%.mmd}.svg"
    mmdc -i "$f" -o "$svg" --backgroundColor transparent
    echo "Rendered: $svg"
done

# Render DOT files to SVG (requires graphviz)
find docs/atlas -name "*.dot" | while read f; do
    svg="${f%.dot}.svg"
    dot -Tsvg "$f" -o "$svg"
    echo "Rendered: $svg"
done
```

---

## Set up CI integration

Copy the pre-built workflow:

```bash
# The workflow file is already at:
cat .github/workflows/atlas-ci.yml
```

The workflow provides:
- **Pattern 1**: Post-merge staleness gate on push to `main`
- **Pattern 2**: PR architecture impact check
- **Pattern 3**: Scheduled weekly full rebuild (every Monday)

---

## Write atlas to a custom output directory

```
/code-atlas output_dir=docs/architecture/atlas
```

Useful if your project uses a different documentation root.

---

## Skip the bug hunt (faster builds)

```
/code-atlas bug_hunt=false
```

Builds all 6 layers but skips Pass 1 and Pass 2. Use for quick documentation updates when bug hunting is not needed.

---

## Preview what would run (dry run)

```bash
bash scripts/rebuild-atlas-all.sh --dry-run
```

Prints what would happen without writing any files.

---

## Review PR architecture impact before merging

```
Show architecture impact of the changes in this PR
```

The skill diffs changed files against the trigger table and reports which atlas layers the PR affects — before it's merged.

---

## Publish to GitHub Pages

```
/code-atlas publish=true
```

Triggers the GitHub Pages publication workflow. See [how to publish to GitHub Pages](./publish-atlas-to-github-pages.md) for full setup.

---

## Troubleshooting

**"Layer 1 LAYER_SOURCE_NOT_FOUND"**
No `docker-compose.yml` or Kubernetes manifests found. Layer 1 is skipped — the build continues. Manually define service topology if needed.

**"DOT_RENDER_FAILED: graphviz not installed"**
Install Graphviz: `brew install graphviz` (macOS) or `apt-get install graphviz` (Ubuntu). Mermaid output is always produced as fallback.

**"JOURNEY_UNDER_MINIMUM"**
Fewer than 3 user journeys could be auto-derived. Add custom journeys: see [how to add custom journeys](./add-custom-journeys.md).

**Atlas seems stale but staleness check says fresh**
The staleness check is heuristic (git diff pattern matching). If you know the atlas is outdated, run `/code-atlas rebuild all` to force a full rebuild.
