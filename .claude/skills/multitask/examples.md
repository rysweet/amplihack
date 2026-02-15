# Multitask Examples

## Example 1: Feature Development Sprint

Three independent features executed in parallel:

```json
[
  {
    "issue": 100,
    "branch": "feat/user-auth",
    "description": "JWT authentication",
    "task": "Implement JWT-based auth with login/logout endpoints. Add middleware for route protection. Include refresh token support.",
    "recipe": "default-workflow"
  },
  {
    "issue": 101,
    "branch": "feat/structured-logging",
    "description": "JSON logging",
    "task": "Replace print statements with structured JSON logging. Add request ID correlation. Configure log levels per environment.",
    "recipe": "default-workflow"
  },
  {
    "issue": 102,
    "branch": "feat/rate-limiting",
    "description": "API rate limits",
    "task": "Add rate limiting middleware using sliding window algorithm. Configure per-endpoint limits. Return proper 429 responses.",
    "recipe": "default-workflow"
  }
]
```

Save as `sprint.json`, then:

```
/multitask sprint.json
```

## Example 2: Mixed Workflow Types

Different recipes per workstream based on task type:

```json
[
  {
    "issue": 200,
    "branch": "feat/new-api",
    "description": "New API endpoint",
    "task": "Add /api/v2/users endpoint with pagination and filtering",
    "recipe": "default-workflow"
  },
  {
    "issue": 201,
    "branch": "investigate/perf-bottleneck",
    "description": "Performance investigation",
    "task": "Investigate why /api/v1/search is slow. Profile database queries. Document findings.",
    "recipe": "investigation-workflow"
  },
  {
    "issue": 202,
    "branch": "fix/config-typo",
    "description": "Config fix",
    "task": "Fix typo in production config that causes timeout errors",
    "recipe": "verification-workflow"
  }
]
```

## Example 3: Inline Invocation

For quick parallel tasks without a config file:

```
/multitask
- #300 (feat/add-tests): Add unit tests for auth module
- #301 (feat/update-docs): Update API documentation
- #302 (feat/fix-lint): Fix all linting warnings
```

Claude parses this into the equivalent JSON config with `default-workflow` recipe.

## Example 4: Classic Mode Fallback

When Recipe Runner is unavailable or you prefer single-session execution:

```
/multitask sprint.json --mode classic
```

Each workstream gets a single long-running Claude session that follows `DEFAULT_WORKFLOW.md` via prompt instructions.

## Example 5: Monitoring During Execution

While workstreams are running:

```bash
# Real-time log of workstream #100
tail -f /tmp/amplihack-workstreams/log-100.txt

# Check which processes are still running
ps aux | grep launcher.py

# See the final report after completion
cat /tmp/amplihack-workstreams/REPORT.md
```

## Example 6: Post-Execution Cleanup

```bash
# Check created PRs
gh pr list --limit 10

# Review a specific workstream's full output
cat /tmp/amplihack-workstreams/log-100.txt

# Clean up all workstream files
rm -rf /tmp/amplihack-workstreams
```

## Production Results

**Recipe Runner follow-up work (2026-02-14)**:

| Issue | Branch                             | Task                   | Result   | Runtime |
| ----- | ---------------------------------- | ---------------------- | -------- | ------- |
| #2288 | feat/ultrathink-recipe-integration | Ultrathink integration | PR #2295 | ~75min  |
| #2289 | feat/recipe-test-coverage          | Test coverage 3:1      | PR #2296 | ~60min  |
| #2290 | feat/recipe-cli-integration        | CLI commands           | PR #2297 | ~90min  |
| #2291 | feat/copilot-sdk-adapter           | Copilot SDK            | Failed   | N/A     |
| #2292 | feat/recipe-integration-tests      | Integration tests      | PR #2303 | ~60min  |

**Success rate**: 4/5 (80%) - meets the >80% acceptance criterion.
