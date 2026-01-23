# Smart Test Selection Skill

Intelligent test selection based on code changes. Optimizes feedback loops by running only the tests affected by your changes.

## Quick Start

```
User: What tests should I run for my changes?

Claude: Analyzing your changes...

Changed: src/amplihack/core/processor.py

Tier 1 (Fast - 30s):
  pytest tests/unit/test_processor.py -v

Tier 2 (Impacted - 2m):
  pytest tests/unit/test_processor.py tests/integration/test_pipeline.py -v

Start with Tier 1 for quick feedback.
```

## Features

- **Import Dependency Analysis**: Maps source files to tests via Python imports
- **Three-Tier Testing**: Fast (< 1 min), Impacted (< 5 min), Full Suite
- **Reliability Tracking**: Excludes flaky tests from fast runs
- **Cache-Based**: Stores mappings in `~/.amplihack/.claude/data/test-mapping/`
- **pytest Integration**: Works with existing markers (slow, integration, e2e)

## Tiers Explained

| Tier | When to Use           | Time Budget | What's Included                     |
| ---- | --------------------- | ----------- | ----------------------------------- |
| 1    | Pre-commit, iteration | < 1 min     | Direct unit tests, high reliability |
| 2    | Pre-push, draft PR    | < 5 min     | All affected tests + integrations   |
| 3    | Ready PR, CI main     | Full        | Complete test suite                 |

## Commands

```bash
# Tier 1: Fast feedback
pytest -m "not slow and not integration" tests/unit/test_changed_module.py

# Tier 2: Thorough check
pytest tests/unit/test_changed_module.py tests/integration/test_related.py

# Tier 3: Full suite
pytest
```

## Data Files

### code_to_tests.yaml

Maps source files to their tests:

```yaml
mappings:
  src/module.py:
    direct_tests: [tests/test_module.py]
    indirect_tests: [tests/test_consumer.py]
```

### reliability.yaml

Tracks test stability:

```yaml
tests:
  tests/test_api.py::test_timeout:
    reliability: 0.75
    flaky_reason: "Network dependent"
```

## Workflow Integration

- **Step 12 (Run Tests)**: Use Tier 1 for pre-commit hooks
- **Step 13 (Local Testing)**: Use Tier 2 before commit
- **CI**: Use Tier 2 for drafts, Tier 3 for ready PRs

## Maintenance

Rebuild cache when:

- New test files added
- Module structure changed
- Cache older than 7 days

```
User: Rebuild test mapping cache
```

## Related Skills

- `test-gap-analyzer`: Find untested code
- `outside-in-testing`: Create E2E tests
- `pre-commit-diagnostic`: Fix hook failures

---

See [SKILL.md](./SKILL.md) for complete documentation.
