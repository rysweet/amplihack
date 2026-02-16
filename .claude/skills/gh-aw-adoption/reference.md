# GitHub Agentic Workflows (gh-aw) - Complete Reference

This file contains comprehensive technical documentation for gh-aw adoption, including CLI commands, workflow schema, security patterns, and architecture details.

**Last Updated**: 2026-02-15
**gh-aw Version**: v0.42.17+
**Source**: https://github.com/github/gh-aw

---

## Table of Contents

1. [CLI Command Reference](#cli-command-reference)
2. [Workflow Schema](#workflow-schema)
3. [Tool Configuration](#tool-configuration)
4. [Safe-Outputs Specification](#safe-outputs-specification)
5. [Network and Security](#network-and-security)
6. [Repo-Memory System](#repo-memory-system)
7. [MCP Server Integration](#mcp-server-integration)
8. [Error Resilience Architecture](#error-resilience-architecture)
9. [Investigation Methodology](#investigation-methodology)
10. [Parallel Agent Orchestration](#parallel-agent-orchestration)

---

## CLI Command Reference

### Installation

```bash
# Install gh CLI (if not present)
brew install gh  # macOS
# or
apt install gh   # Ubuntu/Debian

# Install gh-aw extension
gh extension install github/gh-aw

# Verify installation
gh aw --version
```

### Repository Initialization

```bash
# Initialize repository for agentic workflows
gh aw init

# What this does:
# - Creates .github/workflows/ directory
# - Sets up configuration files
# - Initializes repo-memory branches
# - Configures default engine (copilot/claude)
```

### Workflow Compilation

```bash
# Compile all workflows in repository
gh aw compile

# Compile specific workflow
gh aw compile workflow-name

# Validate without writing lock files
gh aw compile --validate

# Compile with verbose output
gh aw compile --verbose

# Auto-fix common issues
gh aw fix --write
```

**What compilation does**:

- Parses markdown workflow files (`.github/workflows/*.md`)
- Validates YAML frontmatter syntax
- Generates GitHub Actions YAML (`.github/workflows/*.lock.yml`)
- Checks permissions, tools, safe-outputs configuration
- Verifies network firewall rules
- Validates trigger events

### Workflow Debugging

```bash
# View workflow logs
gh aw logs workflow-name

# Audit specific workflow run
gh aw audit <run-id>

# Show recent workflow executions
gh aw list-runs

# Debug compilation issues
gh aw compile workflow-name --verbose
```

### Workflow Execution

```bash
# Trigger workflow manually
gh workflow run workflow-name.lock.yml

# Trigger with inputs
gh workflow run workflow-name.lock.yml \
  -f input_name=value

# View workflow status
gh run list --workflow=workflow-name.lock.yml

# View specific run details
gh run view <run-id>
```

### Version Management

```bash
# Check for gh-aw updates
gh extension upgrade gh-aw

# List installed version
gh extension list | grep gh-aw

# Upgrade to specific version
gh extension remove gh-aw
gh extension install github/gh-aw@v0.42.17
```

---

## Workflow Schema

### Complete Frontmatter Schema

```yaml
---
# REQUIRED: Trigger configuration (GitHub Actions events)
on:
  schedule:
    - cron: "0 */2 * * *" # Cron schedule
  workflow_dispatch: # Manual trigger
  issues:
    types: [opened, labeled]
  pull_request:
    types: [opened, synchronize]

# REQUIRED: Permissions (least-privilege principle)
permissions:
  contents: read # Read repository contents
  issues: write # Create/modify issues
  pull-requests: write # Create/modify PRs
  discussions: write # Create/modify discussions
  checks: write # Create check runs
  statuses: write # Create commit statuses

# REQUIRED: AI engine selection
engine: copilot | claude-code | claude-sonnet-4-5 | codex

# OPTIONAL: Tool configuration
tools:
  github:
    toolsets: [issues, pull_requests, repos, discussions]
    mode: remote | local
    read-only: false
  repo-memory:
    branch-name: memory/workflow-name
    retention-days: 30
  bash:
    enabled: true # Enabled by default in AWF sandbox
  edit:
    enabled: true # Enabled by default in AWF sandbox
  web-fetch:
    enabled: false

# OPTIONAL: Safe-outputs (GitHub API mutation limits)
safe-outputs:
  add-comment:
    max: 10
    expiration: 1d
  close-issue:
    max: 5
  create-issue:
    max: 2
  update-issue:
    max: 10
  label-issue:
    max: 20
  close-pull-request:
    max: 3

# OPTIONAL: Network firewall configuration
network:
  firewall: true
  allowed:
    - defaults # GitHub API, npm, PyPI, etc.
    - github # GitHub.com domains
    - https://api.example.com

# OPTIONAL: Workflow metadata
name: Human-Readable Workflow Name
description: Brief description of workflow purpose
---
```

### Field Specifications

#### `on:` (Trigger Events)

**Supported events**:

- `schedule`: Cron-based triggers
- `workflow_dispatch`: Manual execution
- `issues`: Issue events (opened, closed, labeled, etc.)
- `pull_request`: PR events (opened, synchronize, review_requested, etc.)
- `push`: Push to branches
- `pull_request_target`: PR from forks (security-sensitive)
- `discussion`: Discussion events
- `issue_comment`: Comments on issues/PRs

**Example: Multiple triggers**

```yaml
on:
  schedule:
    - cron: "0 9 * * 1" # Every Monday at 9 AM UTC
  workflow_dispatch:
  issues:
    types: [opened, labeled]
```

#### `permissions:`

**Available permissions**:

- `contents`: Repository contents (read/write)
- `issues`: Issue management
- `pull-requests`: PR management
- `discussions`: Discussion management
- `checks`: Check runs
- `statuses`: Commit statuses
- `actions`: GitHub Actions workflows
- `packages`: GitHub Packages
- `deployments`: Deployments

**Principle**: Grant minimum necessary permissions

```yaml
# Good: Minimal permissions
permissions:
  contents: read
  issues: write

# Bad: Overly broad
permissions:
  contents: write
  issues: write
  pull-requests: write
  discussions: write
```

#### `engine:`

**Supported engines**:

- `copilot`: GitHub Copilot (default, fastest)
- `claude-code`: Claude Code (more stable for complex tasks)
- `claude-sonnet-4-5`: Claude Sonnet 4.5 (highest quality)
- `codex`: OpenAI Codex

**Selection criteria**:

- `copilot`: Fast iteration, simple tasks, GitHub-native
- `claude-code`: Complex logic, multi-step workflows, better reasoning
- `claude-sonnet-4-5`: Maximum quality, critical workflows
- `codex`: OpenAI integration, specific model requirements

---

## Tool Configuration

### GitHub Toolsets

**Available toolsets**:

- `issues`: Issue CRUD operations, labels, assignees
- `pull_requests`: PR CRUD, reviews, merges, checks
- `repos`: Repository metadata, branches, tags
- `discussions`: Discussion CRUD, comments, categories
- `projects`: GitHub Projects v2 integration
- `search`: Code search, issue search
- `teams`: Team management (requires org permissions)

**Configuration**:

```yaml
tools:
  github:
    toolsets: [issues, pull_requests, repos]
    mode: remote # Use GitHub API
    read-only: false # Allow mutations
```

**Read-only mode** (for analysis workflows):

```yaml
tools:
  github:
    toolsets: [issues, pull_requests, repos]
    mode: remote
    read-only: true # Prevent all mutations
```

### Bash Tools

**Default**: Enabled in Agent Workflow Firewall (AWF) sandbox

**Why it's safe**: AWF provides complete sandboxing, so bash commands are isolated and cannot affect the host system.

**Configuration** (explicit):

```yaml
tools:
  bash:
    enabled: true
    timeout: 300000 # 5 minutes (milliseconds)
```

**Common uses**:

- Running CLI tools (gh, jq, yq, etc.)
- Processing data with standard Unix utilities
- Executing test suites
- Calling external APIs with curl

### Edit Tools

**Default**: Enabled in AWF sandbox

**Use cases**:

- Modifying workflow files programmatically
- Updating configuration files
- Fixing code issues found by analysis

**Configuration**:

```yaml
tools:
  edit:
    enabled: true
```

### Web-Fetch Tools

**Default**: Disabled (explicit opt-in required)

**Use cases**:

- Fetching external documentation
- Retrieving API data from external services
- Downloading resources for analysis

**Configuration**:

```yaml
tools:
  web-fetch:
    enabled: true
    timeout: 30000 # 30 seconds

network:
  firewall: true
  allowed:
    - defaults
    - https://api.example.com
```

---

## Safe-Outputs Specification

### Purpose

Safe-outputs limit the number of GitHub API mutations a workflow can perform, preventing runaway automation and API abuse.

### Available Safe-Output Types

**Issue operations**:

- `create-issue`: Create new issues
- `update-issue`: Modify existing issues
- `close-issue`: Close issues
- `reopen-issue`: Reopen closed issues
- `label-issue`: Add/remove labels
- `assign-issue`: Assign users

**Pull request operations**:

- `create-pull-request`: Create PRs
- `update-pull-request`: Modify PRs
- `close-pull-request`: Close PRs
- `merge-pull-request`: Merge PRs
- `request-review`: Request PR reviews

**Comment operations**:

- `add-comment`: Post comments on issues/PRs
- `update-comment`: Edit existing comments
- `delete-comment`: Remove comments

**Discussion operations**:

- `create-discussion`: Create discussions
- `close-discussion`: Close discussions
- `add-discussion-comment`: Post discussion comments

**Repository operations**:

- `create-branch`: Create branches
- `delete-branch`: Delete branches
- `create-tag`: Create tags

### Configuration Syntax

```yaml
safe-outputs:
  <operation-name>:
    max: <integer> # Maximum operations per run
    expiration: <duration> # Optional: Time window (1h, 1d, 1w)
```

**Examples**:

**High-frequency commenting** (chatbot):

```yaml
safe-outputs:
  add-comment:
    max: 50
    expiration: 1h
```

**Conservative issue management**:

```yaml
safe-outputs:
  create-issue:
    max: 2
    expiration: 1d
  close-issue:
    max: 5
    expiration: 1d
```

**No safe-outputs** (read-only workflow):

```yaml
# Omit safe-outputs entirely
# Workflow can only read, never mutate
```

### Best Practices

1. **Start conservative**: Begin with low limits, increase based on actual needs
2. **Add expiration windows**: Prevent accumulated quota abuse over time
3. **Prioritize operations**: Critical actions first (e.g., security issues before cosmetic labels)
4. **Log limit hits**: Track when workflows hit limits for tuning
5. **Separate concerns**: Don't bundle high-limit and low-limit operations in same workflow

---

## Network and Security

### Firewall Configuration

**Purpose**: Restrict network access to prevent data exfiltration and unauthorized API calls.

**Default**: Firewall enabled, only approved domains allowed

**Configuration**:

```yaml
network:
  firewall: true
  allowed:
    - defaults # npm, PyPI, GitHub API, common registries
    - github # All GitHub.com domains
    - https://api.example.com # Explicit domain
    - https://*.trusted-domain.com # Wildcard subdomain
```

**Special keywords**:

- `defaults`: Common package registries (npm, PyPI, RubyGems, crates.io, etc.)
- `github`: All GitHub-related domains (api.github.com, github.com, etc.)

### Security Best Practices

#### 1. Least-Privilege Permissions

```yaml
# Good: Minimal permissions
permissions:
  contents: read
  issues: write

# Bad: Overly broad
permissions: write-all  # DON'T DO THIS
```

#### 2. Explicit Network Rules

```yaml
# Good: Explicit allowlist
network:
  firewall: true
  allowed:
    - defaults
    - https://api.trusted-service.com

# Bad: Firewall disabled
network:
  firewall: false  # DON'T DO THIS
```

#### 3. Safe-Output Limits

```yaml
# Good: Reasonable limits
safe-outputs:
  add-comment:
    max: 10
    expiration: 1d

# Bad: Unlimited mutations
# (omitting safe-outputs when mutations are possible)
```

#### 4. Input Validation

**Always validate external inputs**:

- Issue body content
- PR descriptions
- Comments
- Webhook payloads

**Template injection prevention**:

```yaml
# Bad: Direct interpolation
${{ github.event.issue.body }}
# Good: Pass through safe-output with validation
# Let gh-aw validate and sanitize before use
```

#### 5. Secret Management

**Use GitHub secrets for sensitive data**:

```yaml
# Workflow accesses secrets via context
${{ secrets.API_KEY }}
```

**Never**:

- Hardcode credentials in workflows
- Log secrets to console
- Include secrets in comments or issues
- Commit secrets to repo-memory

---

## Repo-Memory System

### Purpose

Persistent git-backed storage for agent state, enabling stateful workflows.

### Configuration

```yaml
tools:
  repo-memory:
    branch-name: memory/workflow-name
    retention-days: 30 # Auto-cleanup old data
```

### Branch Structure

```
memory/
├── workflow-name/
│   ├── state.json           # Current workflow state
│   ├── audit-log.jsonl      # Audit trail (append-only)
│   ├── cache/               # Cached data
│   └── artifacts/           # Workflow outputs
```

### Usage Patterns

#### State Tracking

```yaml
# Store state
echo '{"last_run": "2026-02-15T10:00:00Z"}' > state.json
git add state.json
git commit -m "Update state"
git push origin memory/workflow-name

# Read state on next run
cat state.json
```

#### Audit Logging

```jsonl
{"timestamp": "2026-02-15T10:00:00Z", "action": "closed-issue", "issue": 123}
{"timestamp": "2026-02-15T10:05:00Z", "action": "added-label", "issue": 124}
```

**Append-only for auditability**:

```bash
echo "$log_entry" >> audit-log.jsonl
```

#### Cache Management

```bash
# Cache external data to avoid repeated API calls
curl https://api.example.com/data > cache/api-data.json
git add cache/api-data.json
git commit -m "Cache API data"
```

### Retention and Cleanup

**Automatic cleanup** (if configured):

```yaml
tools:
  repo-memory:
    branch-name: memory/workflow-name
    retention-days: 30
```

**Manual cleanup**:

```bash
# In workflow
find cache/ -mtime +30 -delete
git add cache/
git commit -m "Clean old cache"
```

---

## MCP Server Integration

### What is MCP?

Model Context Protocol (MCP) provides standardized tool interfaces for AI agents.

### Supported MCP Servers

**Common MCP servers for gh-aw**:

- `@modelcontextprotocol/server-github`: Enhanced GitHub API access
- `@modelcontextprotocol/server-filesystem`: File operations
- `@modelcontextprotocol/server-postgres`: Database queries
- `@modelcontextprotocol/server-slack`: Slack integration
- Custom MCP servers for proprietary systems

### Configuration

```yaml
tools:
  mcp:
    servers:
      - name: github-advanced
        package: "@modelcontextprotocol/server-github"
        config:
          token: ${{ secrets.GITHUB_TOKEN }}
      - name: postgres
        package: "@modelcontextprotocol/server-postgres"
        config:
          connection_string: ${{ secrets.DATABASE_URL }}
```

### Creating Shared Workflow Components

**Wrap MCP servers as reusable workflow components**:

File: `.github/workflows/shared/notion-integration.md`

```yaml
---
# Shared component configuration
shared: true
engine: copilot
tools:
  mcp:
    servers:
      - name: notion
        package: "@notionhq/mcp-server-notion"
        config:
          auth_token: ${{ secrets.NOTION_TOKEN }}
---

# Notion Integration Component

Provides Notion database access for workflows.

Available operations:
- Query databases
- Create/update pages
- Search content
```

**Use in workflows**:

```yaml
tools:
  shared:
    - notion-integration
```

---

## Error Resilience Architecture

### Patterns Every Workflow Should Implement

#### 1. API Rate Limit Handling

```markdown
## Rate Limit Strategy

Before each GitHub API call:

1. Check remaining rate limit: `gh api rate_limit`
2. If < 100 requests remaining, wait for reset
3. Implement exponential backoff on 429 responses

**Backoff schedule**:

- Attempt 1: Immediate
- Attempt 2: Wait 1 second
- Attempt 3: Wait 2 seconds
- Attempt 4: Wait 4 seconds
- Attempt 5: Wait 8 seconds (max 5 attempts)
```

#### 2. Network Failure Retries

````markdown
## Network Resilience

For all external API calls (non-GitHub):

1. Set timeout: 30 seconds
2. Retry on timeout or connection failure
3. Maximum 3 attempts
4. Exponential backoff: 2s, 4s, 8s

**Retry logic**:

```bash
for attempt in 1 2 3; do
  if curl --max-time 30 https://api.example.com; then
    break
  fi
  sleep $((2 ** attempt))
done
```
````

````

#### 3. Partial Failure Recovery

```markdown
## Continue on Error Strategy

When processing multiple items (issues, PRs, files):
1. Process each item independently
2. Log failures but continue to next item
3. At end, report success count and failure count
4. Save failed items to repo-memory for retry

**Example**: Closing 10 expired issues
- Don't stop on first failure
- Close remaining 9 issues
- Report: "Closed 9/10 issues, 1 failure (see audit log)"
````

#### 4. Comprehensive Audit Trails

````markdown
## Audit Logging Requirements

Log every action to repo-memory in JSON Lines format:

**Schema**:

```jsonl
{
  "timestamp": "ISO8601",
  "action": "string",
  "target": "string",
  "result": "success|failure",
  "error": "string|null"
}
```
````

**Actions to log**:

- API calls (GitHub and external)
- Safe-output operations (comments, labels, closures)
- State changes
- Errors and exceptions

**Location**: `memory/<workflow>/audit-log.jsonl`

````

#### 5. Safe-Output Limit Awareness

```markdown
## Prioritization Strategy

When approaching safe-output limits:
1. Prioritize critical operations (security issues > cosmetic labels)
2. Track operations completed vs. limit
3. If limit reached, save remaining work to repo-memory
4. Log warning: "Hit safe-output limit, deferred N items"
5. Next run processes deferred items first
````

### Error Handling Template

```markdown
## Error Handling Protocol

For every workflow operation:

**Pre-operation**:

- Validate inputs
- Check prerequisites (permissions, rate limits)
- Log operation start

**During operation**:

- Set timeouts
- Implement retries
- Handle exceptions gracefully

**Post-operation**:

- Verify success
- Log outcome (success/failure)
- Clean up resources

**On failure**:

- Log detailed error to repo-memory
- Post comment to issue/PR if appropriate
- Create monitoring issue if critical failure
- Never silently fail
```

---

## Investigation Methodology

### Goal

Discover what agentic workflows exist in the gh-aw repository and identify gaps in target repository.

### Step-by-Step Process

#### Step 1: Enumerate All Workflows

```bash
# List all workflow files in gh-aw repository
gh api repos/github/gh-aw/contents/.github/workflows \
  --jq '.[] | select(.name | endswith(".md")) | .name'

# Output: List of 100+ workflow filenames
```

#### Step 2: Sample Diverse Workflows

**Selection strategy**:

- Pick 10-15 workflows spanning different categories
- Prioritize workflows with recent updates
- Include variety: security, automation, maintenance, reporting

**Categories to cover**:

- Security scanning
- Issue/PR automation
- CI/CD integration
- Maintenance and housekeeping
- Reporting and analytics
- Team communication

**Example sample**:

```
1. issue-classifier.md (triage automation)
2. pr-labeler.md (PR automation)
3. secret-validation.md (security)
4. container-scanning.md (security)
5. agentics-maintenance.md (maintenance hub)
6. weekly-issue-summary.md (reporting)
7. stale-pr-manager.md (housekeeping)
8. test-coverage-enforcer.md (quality gates)
9. changelog-generator.md (release automation)
10. performance-testing.md (CI/CD)
```

#### Step 3: Analyze Workflow Patterns

For each sampled workflow, document:

**Structure**:

- Trigger events (schedule, webhook, manual)
- Permissions required
- Tools used
- Safe-outputs configuration
- Network requirements

**Purpose**:

- What problem does it solve?
- What tasks does it automate?
- Who benefits (developers, maintainers, security team)?

**Complexity**:

- Simple (single-step)
- Medium (multi-step with branching)
- Complex (stateful, orchestration)

**Dependencies**:

- External services (MCP servers)
- Repo-memory usage
- Other workflows

#### Step 4: Categorize All Workflows

**Create taxonomy**:

```
Security & Compliance
├── Vulnerability scanning
├── Secret management
├── License compliance
└── SBOM generation

Development Automation
├── Issue triage
├── PR automation
├── Code review assistance
└── Merge automation

Quality Assurance
├── Test coverage enforcement
├── Mutation testing
├── Performance testing
└── Code quality checks

Maintenance & Operations
├── Workflow health monitoring
├── Stale resource cleanup
├── Dependency updates
└── Repository housekeeping

Reporting & Analytics
├── Weekly summaries
├── Team dashboards
├── Metrics collection
└── Trend analysis

Team Communication
├── Status reports
├── Review reminders
├── Announcement distribution
└── Onboarding automation
```

#### Step 5: Gap Analysis

**Compare against target repository**:

For each category, ask:

1. Does target repository have existing automation in this area?
2. What workflows would provide immediate value?
3. What workflows are nice-to-have but lower priority?
4. Are there any repository-specific needs not covered by gh-aw workflows?

**Output**: Prioritized list with reasoning

**Example output**:

```markdown
## High Priority (Immediate Value)

1. **secret-validation.md** - NO current secret monitoring
   - Impact: Prevent expired credentials causing outages
   - Effort: Low (1 hour)

2. **pr-labeler.md** - Manual labeling currently
   - Impact: Save 2 hours/week developer time
   - Effort: Low (1 hour)

3. **agentics-maintenance.md** - No workflow health monitoring
   - Impact: Catch failing workflows early
   - Effort: Medium (2 hours)

## Medium Priority (Valuable But Not Urgent)

4. **stale-pr-manager.md** - 26 open PRs need cleanup
   - Impact: Reduce noise in PR list
   - Effort: Low (1 hour)

...
```

#### Step 6: Create Implementation Plan

**Prioritize by**:

- Value / Effort ratio (high value, low effort first)
- Dependencies (foundational workflows before dependent ones)
- Risk (low-risk before experimental)

**Example plan**:

```markdown
## Phase 1: Foundation (Week 1)

- agentics-maintenance.md (workflow health)
- secret-validation.md (security)
- pr-labeler.md (quick win)

## Phase 2: Security & Compliance (Week 2)

- container-scanning.md
- license-compliance.md
- sbom-generation.md

## Phase 3: Quality Automation (Week 3)

- test-coverage-enforcer.md
- mutation-testing.md
- performance-testing.md

## Phase 4: Maintenance (Week 4)

- stale-pr-manager.md
- dependency-updates.md
- changelog-generator.md

## Phase 5: Reporting (Week 5)

- weekly-issue-summary.md
- workflow-health-dashboard.md
- team-status-reports.md
```

---

## Parallel Agent Orchestration

### Architecture

**Goal**: Create multiple workflows simultaneously using parallel agents.

### Coordinator Agent Responsibilities

1. **Task distribution**: Assign workflows to worker agents
2. **Progress tracking**: Monitor worker agent completion
3. **Conflict resolution**: Handle merge conflicts between workers
4. **CI orchestration**: Ensure all workflows pass CI before merge
5. **Error aggregation**: Collect and report failures

### Worker Agent Responsibilities

1. **Workflow creation**: Read reference, adapt, create workflow file
2. **Error resilience**: Add comprehensive error handling
3. **Testing**: Validate workflow compiles correctly
4. **Documentation**: Create clear purpose and usage docs
5. **Branch management**: Create feature branch, commit, push

### Orchestration Pattern

```markdown
## Parallel Workflow Creation

**Coordinator**: Main agent thread

**Workers**: N agent threads (one per workflow)

### Phase 1: Distribute Work (Coordinator)

For each workflow in priority list:

1. Spawn new agent thread
2. Assign workflow name and reference URL
3. Track thread ID and workflow name

Wait for all agents to report completion or failure.

### Phase 2: Create Workflow (Worker)

Each worker agent:

1. Read reference workflow from gh-aw repository
2. Analyze structure, purpose, tools, permissions
3. Adapt to target repository context
4. Create workflow file in feature branch
5. Add error resilience patterns
6. Commit and push
7. Report success/failure to coordinator

### Phase 3: Integrate (Coordinator)

After all workers complete:

1. Collect list of created branches
2. For each branch:
   - Compile workflow: `gh aw compile`
   - Check CI status
   - Merge if passing
3. Create integration PR if applicable
4. Report summary to user

### Phase 4: Resolve Conflicts (Coordinator)

If merge conflicts occur:

1. Identify conflicting files
2. Rebase branches in sequence
3. Re-run CI checks
4. Retry merge

If CI failures occur:

1. Analyze logs
2. Spawn repair agent for failing workflow
3. Wait for fix
4. Retry CI

### Phase 5: Validate (Coordinator)

After all workflows merged:

1. Compile all workflows: `gh aw compile --validate`
2. Check for any compilation errors
3. Trigger test runs with `workflow_dispatch`
4. Monitor first executions
5. Report final status
```

### Error Handling in Orchestration

**Worker agent failures**:

- Log error to coordinator
- Continue with remaining workflows
- Report failed workflows in summary

**CI failures**:

- Don't block other workflows
- Spawn repair agents for failures
- Retry after fixes applied

**Merge conflicts**:

- Rebase automatically if possible
- Escalate complex conflicts to user
- Provide conflict resolution guidance

### Communication Protocol

**Worker → Coordinator**:

```json
{
  "thread_id": "agent-1",
  "workflow": "pr-labeler",
  "status": "success",
  "branch": "feat/pr-labeler-workflow",
  "commit": "a1b2c3d",
  "message": "Created PR labeler workflow"
}
```

**Coordinator → User**:

```markdown
## Workflow Creation Progress

✅ pr-labeler (agent-1) - Created in feat/pr-labeler-workflow
✅ issue-classifier (agent-2) - Created in feat/issue-classifier-workflow
⚠️ security-scanner (agent-3) - CI failed, spawning repair agent
✅ stale-pr-manager (agent-4) - Created in feat/stale-pr-manager-workflow
❌ performance-testing (agent-5) - Failed: Missing Azure credentials

**Summary**: 3 successful, 1 in repair, 1 failed

Next: Merging successful workflows to integration branch...
```

---

## Advanced Topics

### Workflow Composition

**Reuse patterns across workflows**:

Create shared prompt components:

```markdown
<!-- shared-error-handling.md -->

## Error Handling Protocol

For every operation:

1. Validate inputs
2. Set timeouts and retries
3. Log all actions
4. Handle failures gracefully
```

Import in workflows:

```markdown
---
# Workflow frontmatter
---

# My Workflow

@import "shared-error-handling.md"

## Workflow-Specific Logic

...
```

### Conditional Execution

**Execute workflow based on conditions**:

```markdown
## Conditional Logic

Before proceeding, check:

1. Is this a weekday? (Don't run on weekends)
2. Are there open issues with `urgent` label?
3. Is CI passing on main branch?

If ANY condition fails, exit gracefully with message.
```

### Multi-Repository Workflows

**Operate across multiple repositories**:

```yaml
tools:
  github:
    toolsets: [repos]
    repositories:
      - owner/repo1
      - owner/repo2
      - owner/repo3
```

**Use case**: Organization-wide maintenance

- Update dependencies across all repos
- Enforce security policies
- Collect metrics from multiple projects

### Workflow Metrics

**Track workflow performance**:

````markdown
## Metrics Collection

After each run, save to repo-memory:

**Schema**:

```json
{
  "timestamp": "2026-02-15T10:00:00Z",
  "duration_ms": 12500,
  "operations": {
    "issues_closed": 3,
    "comments_added": 5
  },
  "errors": 0
}
```
````

**Aggregation**: Weekly summary workflow reads metrics and generates dashboard

````

---

## Troubleshooting Guide

### Compilation Errors

**Error: "Missing required field: on"**
```yaml
# Fix: Add trigger configuration
on:
  workflow_dispatch:
````

**Error: "Invalid tool name: xyz"**

```yaml
# Fix: Check tool name spelling
tools:
  github: # Not "github-api"
    toolsets: [issues]
```

**Error: "Permission denied: contents"**

```yaml
# Fix: Add required permission
permissions:
  contents: read
```

### Runtime Errors

**Error: "API rate limit exceeded"**

- Implement rate limit checking before API calls
- Add exponential backoff on 429 responses
- Consider increasing schedule interval

**Error: "Safe-output limit reached"**

- Increase limit if appropriate
- Add prioritization logic
- Split workflow into multiple runs

**Error: "Network request blocked by firewall"**

```yaml
# Fix: Add domain to allowlist
network:
  firewall: true
  allowed:
    - defaults
    - https://api.external-service.com
```

### Debugging Techniques

**View raw logs**:

```bash
gh run view <run-id> --log
```

**Audit specific run**:

```bash
gh aw audit <run-id>
```

**Local testing** (simulate workflow):

```bash
# Run workflow prompt locally with Claude Code
cat .github/workflows/my-workflow.md | claude-code --stdin
```

**Verbose compilation**:

```bash
gh aw compile my-workflow --verbose
```

---

## Migration and Upgrades

### Upgrading gh-aw Extension

```bash
# Check current version
gh extension list | grep gh-aw

# Upgrade to latest
gh extension upgrade gh-aw

# Verify upgrade
gh aw --version
```

### Applying Version Migrations

**When new gh-aw version releases**:

1. Read release notes for breaking changes
2. Run automated migration: `gh aw fix --write`
3. Manually review fixes applied
4. Test workflows: `gh aw compile --validate`
5. Run sample workflow executions
6. Commit migrations

**Common migrations**:

- Field renames in YAML frontmatter
- Deprecated tool name updates
- Permission model changes
- Safe-output syntax updates

### Backward Compatibility

**gh-aw follows semantic versioning**:

- Major version: Breaking changes
- Minor version: New features (backward compatible)
- Patch version: Bug fixes

**Recommendation**: Pin to minor version in CI

```yaml
# .github/workflows/compile-workflows.yml
- name: Install gh-aw
  run: gh extension install github/gh-aw@v0.42
```

---

**Last Updated**: 2026-02-15
**Maintainer**: amplihack framework
**Sources**: GitHub gh-aw repository, documentation, and production usage
