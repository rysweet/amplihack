# Triage 2026-03-15T07Z

11 open PRs. 1 newly triaged, 10 previously triaged.

## Newly Triaged

- #3152 (low, docs/automation, 0d, draft): Automated daily docs for 2026-03-15 — 3 docs files updated (staging-api.md, cli.md, recipe-cli-reference.md) based on PRs #3151, #3139, #3138. Documentation-only, no code. Expires Mar 16. **Note**: recipe-cli-reference.md documents CWD-traversal resolution (step 2) which open PR #3141 is set to remove — potential doc conflict if #3141 merges before #3152. Labels added: triage:complete, triage:low-risk.

## Previously Triaged (no action needed)

- #3146 (low): security-red-team timeout 60→90min — transient API flakiness fix
- #3145 (low, has-tests): session_tracker FileNotFoundError crash fix + tests
- #3144 (medium, has-tests): GhAwCompiler — YAML `on` boolean fix, line:col, typo→error escalation
- #3143 (low, needs-review): pre-commit guard for CI-incompatible MCP servers (not draft, ready to review)
- #3142 (low, has-tests): CLI subordinate passthrough without `--` separator
- #3141 (medium): drop CWD-traversal from resolve_bundle_asset
- #3140 (medium, has-tests): recipe runner auto-normalise `{{var}}` quoting
- #3127 (low, needs-review, needs-testing): Windows native compat phases 1-3 (not draft, ready to review)
- #3124 (low): docs/recipe-variable-expansion-reference — expires Mar 15
- #2876 (extreme, dirty): hive mind DHT sharding — needs-decomposition, merge-conflicts, long-standing

## Action Recommended

- **#3143** and **#3127** are non-draft and labeled `triage:needs-review` — top priority for human review.
- #2876 still needs decomposition before it can proceed.
- #3124 expires today (Mar 15) — if not merged, will close automatically.
