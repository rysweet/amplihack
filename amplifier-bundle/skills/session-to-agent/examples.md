# Session-to-Agent: Examples

Worked examples showing how sessions are converted into goal-seeking agents.

## Example 1: Security Analyst Session to Security Audit Agent

### Session Summary

A user spent 90 minutes manually auditing a Python web API for security
issues. They checked dependencies, reviewed authentication middleware, tested
for SQL injection, and verified CORS headers.

### Extracted Context

```json
{
  "primary_goal": "Audit a Python web API for common security vulnerabilities",
  "sub_goals": [
    "Scan dependencies for known CVEs",
    "Review authentication and authorization middleware",
    "Test endpoints for SQL injection and XSS",
    "Verify CORS, CSP, and security headers",
    "Generate a severity-ranked findings report"
  ],
  "constraints": [
    "Must not modify production database",
    "Only test against staging environment",
    "Complete within 2 hours"
  ],
  "tools_used": [
    "pip-audit",
    "bandit",
    "curl",
    "sqlmap (manual equivalent)",
    "Grep for pattern scanning",
    "Read for code review"
  ],
  "patterns_observed": [
    "Scan dependencies first (fastest, highest signal)",
    "Static analysis before dynamic testing",
    "Check authentication before authorization",
    "Verify error responses do not leak stack traces"
  ],
  "domain_knowledge": [
    "FastAPI's Depends() system for middleware injection",
    "SQLAlchemy parameterized queries prevent most SQL injection",
    "CORS misconfiguration is the most common finding in internal APIs"
  ],
  "success_criteria": [
    "All OWASP Top 10 categories checked",
    "Zero critical findings or all critical findings remediated",
    "Report generated with severity levels and remediation steps"
  ],
  "failure_modes": [
    "pip-audit can miss vendored dependencies -- supplement with Snyk or OSV",
    "Dynamic testing requires running server -- add health check first"
  ],
  "estimated_complexity": "moderate",
  "suggested_agent_name": "api-security-auditor"
}
```

### Generated prompt.md

```markdown
# Goal: Audit a Python web API for common security vulnerabilities

## Objective

Audit a Python web API for common security vulnerabilities.

### Sub-Goals

- Scan dependencies for known CVEs
- Review authentication and authorization middleware
- Test endpoints for SQL injection and XSS
- Verify CORS, CSP, and security headers
- Generate a severity-ranked findings report

## Success Criteria

- All OWASP Top 10 categories checked
- Zero critical findings or all critical findings remediated
- Report generated with severity levels and remediation steps

## Constraints

- Must not modify production database
- Only test against staging environment
- Complete within 2 hours

## Domain Knowledge

- FastAPI's Depends() system for middleware injection
- SQLAlchemy parameterized queries prevent most SQL injection
- CORS misconfiguration is the most common finding in internal APIs

## Patterns and Strategies

- Scan dependencies first (fastest, highest signal)
- Static analysis before dynamic testing
- Check authentication before authorization
- Verify error responses do not leak stack traces

## Tools and Capabilities Required

- pip-audit
- bandit
- curl
- sqlmap (manual equivalent)
- Grep for pattern scanning
- Read for code review

## Failure Modes and Recovery

- pip-audit can miss vendored dependencies -- supplement with Snyk or OSV
- Dynamic testing requires running server -- add health check first
```

### Agent Generation Command

```bash
amplihack new \
  --file /tmp/session-agent-prompt.md \
  --name api-security-auditor \
  --sdk copilot \
  --enable-memory \
  --output ./goal_agents/api-security-auditor
```

### Result

A 4-phase agent:

1. **Dependency Audit** -- runs pip-audit and bandit
2. **Code Review** -- static analysis of auth, input validation, error handling
3. **Dynamic Testing** -- tests endpoints with crafted payloads
4. **Reporting** -- generates markdown report with findings and remediation

---

## Example 2: Code Review Session to Code Review Agent

### Session Summary

A user conducted a thorough code review of a PR with 15 changed files. They
checked naming conventions, tested edge cases, verified error handling, and
confirmed test coverage. The session took 45 minutes.

### Extracted Context

```json
{
  "primary_goal": "Review a pull request for code quality, correctness, and test coverage",
  "sub_goals": [
    "Check naming conventions and code style",
    "Verify error handling in all new functions",
    "Identify missing edge case tests",
    "Confirm type annotations are complete",
    "Review for philosophy compliance (ruthless simplicity)"
  ],
  "constraints": [
    "Must not push changes to the PR branch",
    "Review all changed files, not just a sample",
    "Flag issues with severity levels (critical, warning, suggestion)"
  ],
  "tools_used": [
    "gh pr diff",
    "Read for file inspection",
    "Grep for pattern matching",
    "ruff check --select ALL",
    "mypy for type checking"
  ],
  "patterns_observed": [
    "Read the PR description first to understand intent",
    "Diff-first review: scan all changes before deep-diving",
    "Check test files alongside implementation files",
    "Look for missing __all__ exports in module files",
    "Verify docstrings match actual behavior"
  ],
  "domain_knowledge": [
    "Project uses ruff for linting with strict config",
    "All public functions require type annotations per project policy",
    "Test files must mirror src/ structure"
  ],
  "success_criteria": [
    "All critical issues identified and documented",
    "Review comments posted to PR with severity tags",
    "No false positives in critical category"
  ],
  "failure_modes": [
    "Large diffs can exceed context window -- chunk by file",
    "Renamed files appear as delete+add -- check git rename detection"
  ],
  "estimated_complexity": "moderate",
  "suggested_agent_name": "pr-code-reviewer"
}
```

### Agent Generation Command

```bash
amplihack new \
  --file /tmp/session-agent-prompt.md \
  --name pr-code-reviewer \
  --sdk copilot \
  --enable-memory
```

### Result

A 3-phase agent:

1. **PR Context** -- reads PR description, fetches diff, identifies changed files
2. **Deep Review** -- reviews each file for style, correctness, types, tests
3. **Report** -- generates review summary with categorized findings

---

## Example 3: Data Analysis Session to Data Pipeline Agent

### Session Summary

A user spent 2 hours building a data transformation pipeline: fetching data
from three CSV sources, cleaning and merging them, running validation checks,
and exporting the result to a PostgreSQL database. They iterated on data
quality rules until the pipeline produced clean output.

### Extracted Context

```json
{
  "primary_goal": "Build a data pipeline that ingests CSVs, cleans and merges data, validates quality, and loads into PostgreSQL",
  "sub_goals": [
    "Fetch and parse 3 CSV sources with different schemas",
    "Normalize column names and types across sources",
    "Merge records on shared key with deduplication",
    "Apply quality rules (completeness, range checks, format validation)",
    "Load validated records into PostgreSQL staging table",
    "Generate quality report with pass/fail counts"
  ],
  "constraints": [
    "Must handle missing values gracefully (default or skip, never error)",
    "Idempotent: safe to re-run without duplicating data",
    "Must complete within 30 minutes for 500K total records"
  ],
  "tools_used": [
    "pandas for data manipulation",
    "psycopg2 for PostgreSQL connection",
    "Bash for file operations",
    "Python scripts for transformation logic"
  ],
  "patterns_observed": [
    "Validate schema before processing (fail fast on wrong format)",
    "Log rejected records to a separate file for manual review",
    "Use UPSERT (INSERT ON CONFLICT UPDATE) for idempotency",
    "Process sources in parallel since they are independent"
  ],
  "domain_knowledge": [
    "Source A uses ISO dates, Source B uses US format, Source C uses epoch",
    "Customer ID field has leading zeros that must be preserved as strings",
    "PostgreSQL COPY is 10x faster than INSERT for bulk loads"
  ],
  "success_criteria": [
    "All 3 sources successfully ingested",
    "Quality checks pass with >95% completeness",
    "Data loaded into PostgreSQL staging table",
    "Quality report generated with metrics"
  ],
  "failure_modes": [
    "CSV encoding issues (Latin-1 vs UTF-8) -- detect and convert",
    "PostgreSQL connection timeout -- retry with exponential backoff",
    "Memory issues with large CSVs -- use chunked reading"
  ],
  "estimated_complexity": "moderate",
  "suggested_agent_name": "csv-to-postgres-pipeline"
}
```

### Agent Generation Command

```bash
amplihack new \
  --file /tmp/session-agent-prompt.md \
  --name csv-to-postgres-pipeline \
  --sdk copilot \
  --enable-memory \
  --multi-agent
```

### Result

A 4-phase agent with multi-agent architecture:

1. **Ingestion** (parallel sub-agents) -- each source gets its own sub-agent
2. **Transformation** -- normalize schemas, merge, deduplicate
3. **Validation** -- apply quality rules, log rejections
4. **Loading** -- bulk load to PostgreSQL, generate quality report

The `--multi-agent` flag creates a coordinator agent that orchestrates
three ingestion sub-agents in parallel, then sequences through
transformation, validation, and loading.

---

## Example 4: Debugging Session to Diagnostic Agent

### Session Summary

A user spent 60 minutes debugging a flaky integration test. The test
passed locally but failed in CI. The root cause was a race condition in
async database cleanup between tests.

### Extracted Context

```json
{
  "primary_goal": "Diagnose and fix flaky integration tests that pass locally but fail in CI",
  "sub_goals": [
    "Compare local and CI environments (Python version, OS, dependencies)",
    "Identify test isolation issues (shared state between tests)",
    "Check for race conditions in async test fixtures",
    "Verify database cleanup between test cases",
    "Confirm fix by running tests in CI-like conditions locally"
  ],
  "constraints": [
    "Must not change test behavior, only fix flakiness",
    "Fix must work in both local and CI environments",
    "Cannot add sleep-based waits (use proper synchronization)"
  ],
  "tools_used": [
    "pytest --tb=long -x for detailed failure output",
    "pytest -p no:randomly to control test ordering",
    "git bisect to find introducing commit",
    "docker for CI environment reproduction"
  ],
  "patterns_observed": [
    "Run failing test in isolation first to check if it is test interaction",
    "Check pytest fixtures for shared mutable state",
    "Look for missing await in async teardown",
    "Compare environment variables between local and CI"
  ],
  "domain_knowledge": [
    "pytest-asyncio event_loop fixture is session-scoped by default",
    "PostgreSQL connections persist across tests unless explicitly closed",
    "CI runs tests in parallel by default which exposes race conditions"
  ],
  "success_criteria": [
    "Test passes reliably in 10 consecutive CI runs",
    "No new test failures introduced",
    "Root cause documented in test docstring"
  ],
  "failure_modes": [
    "git bisect may point to unrelated commit if flakiness is probabilistic",
    "Docker environment may not perfectly match CI -- check CI config"
  ],
  "estimated_complexity": "moderate",
  "suggested_agent_name": "flaky-test-diagnostician"
}
```

### Agent Generation Command

```bash
amplihack new \
  --file /tmp/session-agent-prompt.md \
  --name flaky-test-diagnostician \
  --sdk copilot \
  --enable-memory
```

### Result

A 5-phase diagnostic agent:

1. **Environment Comparison** -- diff local vs CI config
2. **Isolation Testing** -- run failing test alone vs with neighbors
3. **Root Cause Analysis** -- check fixtures, shared state, async cleanup
4. **Fix Application** -- apply targeted fix based on diagnosis
5. **Verification** -- run test suite multiple times to confirm stability

---

## Usage Pattern Summary

| Session Type          | Agent Type        | Key Flags                         |
| --------------------- | ----------------- | --------------------------------- |
| Security audit        | Audit agent       | `--enable-memory`                 |
| Code review           | Review agent      | `--enable-memory`                 |
| Data pipeline         | Pipeline agent    | `--multi-agent`                   |
| Debugging/diagnostics | Diagnostic agent  | `--enable-memory`                 |
| Infrastructure setup  | Automation agent  | `--multi-agent --enable-spawning` |
| API development       | API builder agent | `--enable-memory`                 |
