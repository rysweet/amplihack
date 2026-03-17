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

Produces 8 layers + bug reports in `docs/atlas/`. Takes 3–8 minutes (Layers 7 and 8 add analysis time).

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

This runs all three passes against the current atlas state:

- **Pass 1**: Contradiction hunt across Layers 1–8
- **Pass 2**: Fresh-eyes cross-check (new context window, no anchoring bias)
- **Pass 3**: Scenario deep-dive with PASS/FAIL/NEEDS_ATTENTION verdict per journey

## Map internal service structure (Layer 7)

To see the internal module/package structure of each service:

```
/code-atlas layers=7
```

Produces one Mermaid `graph TD` diagram per service under `docs/atlas/layer7-service-components/`. Useful when a service has grown complex and you need to understand its internal coupling.

## Find dead code and interface mismatches (Layer 8)

```
/code-atlas layers=8
```

Runs in `lsp-assisted` mode if an LSP server is active, or `static-approximation` mode otherwise. Always labels which mode was used on line 1 of `docs/atlas/layer8-ast-lsp-bindings/README.md`.

**Check which mode was used:**

```bash
head -1 docs/atlas/layer8-ast-lsp-bindings/README.md
# Output: **Mode:** lsp-assisted
# OR:     **Mode:** static-approximation
```

## Handle a high-density diagram

When a diagram has >50 nodes or >100 edges, the skill pauses and asks:

```
This diagram has 73 nodes and 118 edges, which may render poorly.
Please choose:
  (a) Full diagram anyway
  (b) Simplified/clustered diagram
  (c) Table representation
```

Choose `(b)` for clustered layout (recommended for most cases). Choose `(a)` only for DOT format, which handles density better than Mermaid. Never choose `(c)` unless you genuinely prefer a table — it cannot be rendered back to a diagram.

**Raise the threshold** for a codebase you know has large service graphs:

```
/code-atlas --density-threshold nodes=100,edges=200
```

**Lower the threshold** for presentation-quality output:

```
/code-atlas --density-threshold nodes=30,edges=60
```

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

Builds all 8 layers but skips Passes 1, 2, and 3. Use for quick documentation updates when bug hunting is not needed.

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

## Run a Mermaid-vs-Graphviz experiment (Appendix A)

To compare renderers on a specific layer:

```
/code-atlas layers=1 diagram_formats=mermaid output_dir=docs/atlas/experiment/mermaid
/code-atlas layers=1 diagram_formats=dot output_dir=docs/atlas/experiment/dot
```

Then review both outputs and record your findings in `docs/atlas/experiments/`. See `SKILL.md` Appendix A for the full experiment template and metrics to capture.

## Troubleshooting

**"Layer 1 LAYER_SOURCE_NOT_FOUND"**
No `docker-compose.yml` or Kubernetes manifests found. Layer 1 is skipped — the build continues. Manually define service topology if needed.

**"DOT_RENDER_FAILED: graphviz not installed"**
Install Graphviz: `brew install graphviz` (macOS) or `apt-get install graphviz` (Ubuntu). Mermaid output is always produced as fallback.

**"JOURNEY_UNDER_MINIMUM"**
Fewer than 3 user journeys could be auto-derived. Add custom journeys: see [how to add custom journeys](./add-custom-journeys.md).

**"LAYER7_SOURCE_NOT_FOUND"**
No package/module structure found for one or more services. Layer 7 is skipped for that service. Common causes: service is a single-file script, or uses a language pattern not yet supported. Add package declarations or run with `layers=1,2,3,4,5,6` to skip Layer 7.

**"LAYER8_LSP_UNAVAILABLE"**
No LSP server found for the detected language. Layer 8 runs in `static-approximation` mode — results are labeled accordingly. To get LSP-verified results: run `/lsp-setup` first, then rebuild Layer 8.

**Pass 3 verdict says FAIL but I can't find the bug**
Check `docs/atlas/bug-reports/{date}-pass3-{journey}.md` for the evidence table. The `Evidence` column contains `file:line` references. If they appear truncated, check that `codebase_path` was set correctly.

**Atlas seems stale but staleness check says fresh**
The staleness check is heuristic (git diff pattern matching). If you know the atlas is outdated, run `/code-atlas rebuild all` to force a full rebuild.
