# Triage 2026-03-16T02Z

13 open PRs. 2 newly triaged, 11 previously triaged.

## Newly Triaged

### #3179 — Fix external-runtime orchestrator resolution
- **Risk**: MEDIUM
- **Author**: rysweet (human)
- **Draft**: yes
- **Base**: `main` (matches current HEAD c78ca7f)
- **Labels added**: triage:complete, triage:medium-risk, triage:has-tests
- **CI**: GitGuardian ✅ (only check so far — PR opened ~30 min ago)
- **Summary**: Fixes external-runtime orchestrator regression cluster behind #3170, #3158, #3120. Stages full runtime assets into `~/.amplihack` including `amplifier-bundle/`. Resolves smart-orchestrator helper/session-tree/hooks assets from real runtime roots. Injects dev-orchestrator workflow instructions into Copilot context. Adds regression coverage for runtime staging and external resolution.
- **Note**: Separate Rust recipe-runner CLI compatibility outage (#3176-class) still under investigation and explicitly excluded from this PR's scope. Draft — needs more CI validation before review.

### #3175 — fix: unify distributed cognitive memory contracts
- **Risk**: MEDIUM
- **Author**: rysweet (human)
- **Draft**: yes
- **Base**: `fix/update-memory-lib-latest-main` (sha: cf8424ec — not main)
- **Labels added**: triage:complete, triage:medium-risk, triage:has-tests
- **CI**: Validate Code in_progress, Link Validation in_progress; others passed
- **Summary**: Adds cluster-wide `retrieve_by_entity()` and `execute_aggregation()` to distributed memory wrapper. Makes distributed shard queries deterministic and fail-fast instead of silently degrading. Fails fast when Azure distributed topology cannot initialize.
- **Note**: Stacked on `fix/update-memory-lib-latest-main` — cannot merge to main until that base branch lands. Part of the broader hive-mind stack alongside #3157 and #3161.

## Previously Triaged (no action needed)

- #3161 (low, has-tests): criterion2 query text fix — ready for review on base branch
- #3157 (medium, has-tests): distributed-memory deterministic fan-out — stacked on #2876
- #3152 (low, docs/automation, draft, EXPIRES Mar 16): daily docs update
- #3146 (low, draft): security-red-team timeout 60→90min
- #3144 (medium, has-tests, draft): GhAwCompiler YAML `on` boolean fix
- #3143 (low, needs-review): pre-commit guard for CI-incompatible MCP servers (NOT draft)
- #3142 (low, has-tests, draft): CLI subordinate passthrough
- #3141 (medium, draft): drop CWD-traversal from resolve_bundle_asset
- #3140 (medium, has-tests, draft): recipe runner auto-normalise `{{var}}` quoting
- #3127 (low, needs-review, needs-testing): Windows native compat phases 1-3 (NOT draft)
- #2876 (extreme, dirty): hive mind DHT sharding — needs-decomposition, merge-conflicts

## Action Recommended

- **#3143** and **#3127**: non-draft, labeled needs-review — top priority for human review
- **#3161**: non-draft, low-risk — ready for review against its base branch
- **#3152**: expires Mar 16 — merge or let expire today
- **#3179**: draft targeting main — watch CI completion; medium-risk, good candidate once CI green
- **#3175**: draft on non-main base — part of hive-mind stack; needs base to land first
- **#2876**: still blocked on needs-decomposition and merge-conflicts
