# Triage 2026-03-15T17Z

13 open PRs. 2 newly triaged, 11 previously triaged.

## Newly Triaged

### #3157 — fix(distributed-memory): deterministic fan-out, no silent fallbacks, no hardcoded constants
- **Risk**: MEDIUM
- **Author**: rysweet (human)
- **Draft**: yes
- **Base**: `feat/distributed-hive-mind` (stacked on PR #2876 — extreme-risk)
- **Labels added**: triage:complete, triage:medium-risk, triage:has-tests
- **Summary**: Removes `try/except Exception: logger.debug(...)` silent fallbacks in `_query_hive()` and `_get_all_hive_facts()` — errors now propagate. Deterministic `_merge_fact_lists()` sort key. Adds `CONFIDENCE_SORT_WEIGHT` constant to `retrieval_constants.py`. New tests: `test_distributed_fanout_determinism.py` and `test_criterion2_query_text.py`.
- **Note**: Must not merge to main until base PR #2876 (extreme-risk, has merge-conflicts) is resolved and merged first.

### #3161 — fix(criterion2): ensure original user question reaches search_facts / distributed hive
- **Risk**: LOW (additive change, good tests)
- **Author**: rysweet (human)
- **Draft**: no (ready for review)
- **Base**: `feat/eh-transport-replace-all-service-bus` (no open PR visible — likely a downstream feature branch)
- **Labels added**: triage:complete, triage:low-risk, triage:has-tests
- **Summary**: Adds `answer_question(question, limit)` to `CognitiveAdapter` (delegates to `search()`). In `LearningAgent.answer_question()`, calls `memory.answer_question(question)` after all local strategies to guarantee original question text flows through to hive. 7 tests in `test_criterion2_query_text.py`.
- **Note**: Base branch is not main — stacked on `feat/eh-transport-replace-all-service-bus`. Cannot merge to main until base lands. Not a draft, so ready for code review against base branch.

## Previously Triaged (no action needed)

- #3152 (low, docs/automation, draft, expires Mar 16): daily docs update — potential conflict with #3141 if #3141 merges
- #3146 (low): security-red-team timeout 60→90min
- #3145 (low, has-tests): session_tracker FileNotFoundError crash fix
- #3144 (medium, has-tests): GhAwCompiler YAML `on` boolean fix
- #3143 (low, needs-review): pre-commit guard for CI-incompatible MCP servers (not draft)
- #3142 (low, has-tests): CLI subordinate passthrough
- #3141 (medium): drop CWD-traversal from resolve_bundle_asset
- #3140 (medium, has-tests): recipe runner auto-normalise `{{var}}` quoting
- #3127 (low, needs-review, needs-testing): Windows native compat phases 1-3 (not draft)
- #2876 (extreme, dirty): hive mind DHT sharding — needs-decomposition, merge-conflicts, long-standing

## Action Recommended

- **#3143** and **#3127**: non-draft, labeled needs-review — top priority for human review
- **#3161**: non-draft, newly triaged low-risk — ready for review against its base branch
- **#3152**: expires Mar 16 — merge or let expire
- **#2876**: still blocked on needs-decomposition; #3157 and #3161 are stacked on it
