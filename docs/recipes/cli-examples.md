# Recipe CLI Examples

Real-world examples showing how to use the `amplihack recipe` CLI commands in different development scenarios.

## Contents

- [Development Scenarios](#development-scenarios)
- [Testing Scenarios](#testing-scenarios)
- [CI/CD Integration](#cicd-integration)
- [Team Workflows](#team-workflows)
- [Custom Recipe Development](#custom-recipe-development)

## Development Scenarios

### Implement a New Feature

**Scenario**: Add JWT authentication to an API using the full 22-step workflow.

```bash
# Create feature branch and run complete workflow
amplihack recipe run default-workflow \
  --context '{
    "task_description": "Add JWT authentication to REST API with token refresh",
    "repo_path": "/home/user/api-server",
    "branch_name": "feat/jwt-auth"
  }'
```

**What happens**:

1. Creates branch `feat/jwt-auth`
2. Clarifies requirements (prompt-writer agent)
3. Designs architecture (architect agent)
4. Writes failing tests (tester agent)
5. Implements code (builder agent)
6. Reviews code (reviewer agent)
7. Runs tests and CI
8. Creates pull request
9. Merges to main (after CI passes)

**Expected duration**: 15-25 minutes

### Quick Bug Fix

**Scenario**: Fix a null pointer exception in production code.

```bash
# Use lightweight quick-fix recipe (4 steps only)
amplihack recipe run quick-fix \
  --context '{
    "task_description": "Fix NullPointerException in UserProfileHandler.getAvatar() when user has no avatar set",
    "repo_path": ".",
    "branch_name": "fix/avatar-null-check"
  }'
```

**What happens**:

1. Analyzes the bug location and root cause
2. Generates and applies fix
3. Runs existing tests
4. Commits changes with descriptive message

**Expected duration**: 2-5 minutes

### Investigate Unknown Codebase

**Scenario**: Understand how authentication works in a legacy system.

```bash
# Run investigation workflow
amplihack recipe run investigation \
  --context '{
    "task_description": "How does the authentication and session management system work? Document the flow from login to logout.",
    "repo_path": "/home/user/legacy-app",
    "focus_area": "src/auth/"
  }'
```

**What happens**:

1. Maps code structure in `src/auth/`
2. Traces data flow through authentication
3. Identifies session storage mechanism
4. Documents findings in markdown
5. Generates architecture diagram

**Output files**:

- `docs/INVESTIGATION_auth-system-<timestamp>.md`
- `docs/diagrams/auth-flow.mermaid`

**Expected duration**: 10-15 minutes

### Refactor Legacy Code

**Scenario**: Refactor a monolithic function into smaller, testable units.

```bash
# Run refactoring workflow with safety checks
amplihack recipe run refactor \
  --context '{
    "task_description": "Refactor processOrder() function in OrderService.java - split into smaller functions with single responsibilities",
    "repo_path": ".",
    "target_file": "src/service/OrderService.java",
    "branch_name": "refactor/order-service"
  }'
```

**What happens**:

1. Analyzes current code structure
2. Proposes refactoring plan (shows before/after)
3. Writes tests for existing behavior
4. Applies refactoring incrementally
5. Verifies tests still pass after each step
6. Reviews for regressions

**Expected duration**: 8-12 minutes

## Testing Scenarios

### Run Only Verification Steps

**Scenario**: Code is already implemented, just need to verify tests and CI.

```bash
# Run post-implementation verification workflow
amplihack recipe run verification-workflow \
  --context '{
    "repo_path": "."
  }'
```

**What happens**:

1. Runs test suite
2. Checks code coverage
3. Runs linting/formatting
4. Builds project
5. Generates verification report

**Expected duration**: 3-6 minutes

### Validate Recipe Before Running

**Scenario**: Created a custom recipe, want to verify it's correct.

```bash
# First validate the YAML
amplihack recipe validate ~/.amplihack/.claude/recipes/my-api-workflow.yaml
```

**Expected output**:

```
Validating my-api-workflow.yaml...
  [OK] Valid YAML syntax
  [OK] Required fields present (name, steps)
  [OK] All step IDs unique
  [OK] Template variables resolve against context
  [OK] Agent references valid (api-designer, builder, tester)
  [OK] No circular dependencies

Recipe "my-api-workflow" is valid (7 steps)
```

**Then dry-run**:

```bash
# Preview execution without making changes
amplihack recipe run my-api-workflow --dry-run \
  --context '{"endpoint": "/api/users", "repo_path": "."}'
```

**Expected output**:

```
[DRY RUN] my-api-workflow (7 steps)
[Step 1/7] design-api (agent: api-designer)
  Would run agent: amplihack:api-designer
  Prompt: Design REST endpoint for /api/users...
[Step 2/7] generate-openapi (type: bash)
  Would execute: python scripts/generate_openapi.py
...

No changes made (dry run mode)
```

**Finally execute**:

```bash
# Actually run it
amplihack recipe run my-api-workflow \
  --context '{"endpoint": "/api/users", "repo_path": "."}'
```

## CI/CD Integration

### GitHub Actions Workflow

**Scenario**: Automatically run recipes in CI when PRs are created.

```yaml
# .github/workflows/recipe-validation.yml
name: Recipe Validation

on:
  pull_request:
    branches: [main]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Install amplihack
        run: pip install amplihack

      - name: Run verification workflow
        run: |
          amplihack recipe run verification-workflow \
            --context '{"repo_path": "."}' \
            --output verification-log.json

      - name: Upload verification log
        uses: actions/upload-artifact@v3
        with:
          name: verification-log
          path: verification-log.json

      - name: Check exit code
        run: |
          if [ $? -ne 0 ]; then
            echo "Verification failed"
            exit 1
          fi
```

### Run Recipe in CI Only on Failures

**Scenario**: Automatically diagnose and fix CI failures.

```yaml
# .github/workflows/auto-fix.yml
name: Auto-Fix CI Failures

on:
  workflow_run:
    workflows: ["CI"]
    types: [completed]
    branches: [main]

jobs:
  auto-fix:
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.conclusion == 'failure' }}
    steps:
      - uses: actions/checkout@v3

      - name: Install amplihack
        run: pip install amplihack

      - name: Run CI diagnostic workflow
        run: |
          amplihack recipe run ci-diagnostic \
            --context '{
              "pr_number": "${{ github.event.pull_request.number }}",
              "repo_path": ".",
              "ci_log_url": "${{ github.event.workflow_run.html_url }}"
            }'

      - name: Notify on Slack
        if: success()
        run: |
          curl -X POST "${{ secrets.SLACK_WEBHOOK }}" \
            -H 'Content-Type: application/json' \
            -d '{"text":"CI failure auto-fixed by recipe workflow"}'
```

### Pre-commit Hook

**Scenario**: Validate custom recipes before committing them.

```bash
# .git/hooks/pre-commit
#!/bin/bash
set -e

# Find all recipe YAML files staged for commit
RECIPES=$(git diff --cached --name-only --diff-filter=ACM | grep '.yaml$' | grep 'recipes/' || true)

if [ -n "$RECIPES" ]; then
  echo "Validating recipe files..."
  for recipe in $RECIPES; do
    echo "  Checking $recipe..."
    amplihack recipe validate "$recipe"
  done
  echo "All recipes valid"
fi
```

## Team Workflows

### Share Context Files

**Scenario**: Team members use standardized context for common tasks.

```bash
# Create team context file
mkdir -p .amplihack/contexts

cat > .amplihack/contexts/new-api-endpoint.json <<EOF
{
  "task_description": "Add new REST endpoint",
  "repo_path": ".",
  "api_version": "v2",
  "auth_required": true,
  "rate_limit": 100
}
EOF
```

**Team members run with shared context**:

```bash
# Developer A adds user search endpoint
amplihack recipe run my-api-workflow \
  --context-file .amplihack/contexts/new-api-endpoint.json \
  --context '{"endpoint": "/api/v2/users/search"}'

# Developer B adds order lookup endpoint
amplihack recipe run my-api-workflow \
  --context-file .amplihack/contexts/new-api-endpoint.json \
  --context '{"endpoint": "/api/v2/orders/lookup"}'
```

**Context Merging**: The `--context` CLI argument merges with `--context-file`. CLI values override file values for matching keys (last-wins strategy). In the examples above, the `endpoint` value from `--context` overrides any `endpoint` defined in the context file, while other keys like `api_version`, `auth_required`, and `rate_limit` are preserved from the file.

### Code Review Recipe

**Scenario**: Standardized code review before merging PRs.

```bash
# Run multi-perspective code review
amplihack recipe run code-review \
  --context '{
    "pr_number": "123",
    "repo_path": ".",
    "focus_areas": ["security", "performance", "maintainability"]
  }'
```

**What happens**:

1. Security agent checks for vulnerabilities
2. Performance agent identifies bottlenecks
3. Reviewer agent checks code style
4. Generates combined review report

**Output**: `code-review-pr123-<timestamp>.md`

### Security Audit Schedule

**Scenario**: Weekly automated security audit on main branch.

```bash
# Run as cron job
# crontab entry: 0 2 * * 1 /usr/local/bin/audit-security.sh
#!/bin/bash
cd /home/user/myproject

amplihack recipe run security-audit \
  --context '{
    "repo_path": ".",
    "focus_modules": "auth,api,database",
    "output_format": "json"
  }' \
  --output /var/log/security-audits/audit-$(date +%Y%m%d).json

# Email report to security team
if [ $? -eq 0 ]; then
  mail -s "Weekly Security Audit - PASSED" security@company.com < /var/log/security-audits/audit-$(date +%Y%m%d).json
else
  mail -s "Weekly Security Audit - FAILED" security@company.com < /var/log/security-audits/audit-$(date +%Y%m%d).json
fi
```

## Custom Recipe Development

### Build Recipe Iteratively

**Scenario**: Create a recipe for adding React components.

**Step 1: Start with minimal recipe**

```bash
cat > ~/.amplihack/.claude/recipes/react-component.yaml <<EOF
name: react-component
description: "Scaffold new React component"
version: "1.0"

context:
  component_name: ""
  repo_path: "."

steps:
  - id: scaffold-files
    type: bash
    command: "mkdir -p {{repo_path}}/src/components/{{component_name}}"
EOF
```

**Step 2: Validate**

```bash
amplihack recipe validate react-component.yaml
```

**Step 3: Dry-run**

```bash
amplihack recipe run react-component --dry-run \
  --context '{"component_name": "UserAvatar", "repo_path": "."}'
```

**Step 4: Add more steps**

```bash
cat >> ~/.amplihack/.claude/recipes/react-component.yaml <<EOF

  - id: design-api
    agent: amplihack:api-designer
    prompt: |
      Design the props interface for React component: {{component_name}}
      Follow TypeScript best practices.
    output: component_api

  - id: implement
    agent: amplihack:builder
    prompt: |
      Implement React component {{component_name}} with this API:
      {{component_api}}

      Use functional components with hooks.
    output: component_code

  - id: write-tests
    agent: amplihack:tester
    prompt: |
      Write React Testing Library tests for {{component_name}}.
      Cover rendering, props, and user interactions.

  - id: run-tests
    type: bash
    command: "cd {{repo_path}} && npm test -- --testPathPattern={{component_name}}"
EOF
```

**Step 5: Test full recipe**

```bash
amplihack recipe run react-component \
  --context '{"component_name": "UserAvatar", "repo_path": "."}'
```

### Debug Recipe Execution

**Scenario**: Recipe step fails, need to understand why.

**Run with verbose output**:

```bash
amplihack recipe --verbose run my-recipe \
  --context '{"task": "..."}' \
  --output debug-log.json
```

**Expected output**:

```
[Recipe] my-recipe (5 steps)
[DEBUG] Loading recipe from: /home/user/.amplihack/.claude/recipes/my-recipe.yaml
[DEBUG] Context variables: task_description, repo_path
[DEBUG] Selected adapter: claude (auto-detected)

[Step 1/5] design (agent: architect)
[DEBUG] Expanding template variables in prompt...
[DEBUG] Resolved: {{task_description}} -> "Add webhooks"
[DEBUG] Calling adapter.execute_agent_step(agent='amplihack:architect', prompt='...')
  ✓ Completed in 8.2s
[DEBUG] Stored output in context.design_spec (1234 chars)

[Step 2/5] implement (agent: builder)
[DEBUG] Expanding template variables in prompt...
[DEBUG] Resolved: {{design_spec}} -> "System Design: Webhook ..."
[DEBUG] Calling adapter.execute_agent_step(agent='amplihack:builder', prompt='...')
  ✗ Failed in 3.1s
[ERROR] Agent execution failed: amplihack:builder returned non-zero exit code 1

Recipe failed at step 2/5: implement
```

**Resume from failed step after fixing**:

```bash
# Fix the issue (maybe adjust prompt or context)
# Then resume from the failed step
amplihack recipe run my-recipe \
  --context '{"task": "..."}' \
  --resume-from implement
```

### Share Recipe with Team

**Scenario**: Package custom recipe for team distribution.

```bash
# 1. Create team recipes repository
mkdir -p team-recipes
cd team-recipes
git init

# 2. Copy recipe
cp ~/.amplihack/.claude/recipes/react-component.yaml .

# 3. Add documentation
cat > README.md <<EOF
# React Component Recipe

Scaffolds a new React component with:
- TypeScript props interface
- Functional component implementation
- React Testing Library tests

## Usage

\`\`\`bash
amplihack recipe run react-component \\
  --context '{"component_name": "ButtonGroup", "repo_path": "."}'
\`\`\`
EOF

# 4. Commit and push
git add react-component.yaml README.md
git commit -m "Add React component scaffolding recipe"
git push origin main
```

**Team members install**:

```bash
# Clone team recipes
git clone https://github.com/company/team-recipes ~/.amplihack-team-recipes

# Add to recipe path
export AMPLIHACK_RECIPE_PATH="$HOME/.amplihack-team-recipes"

# List now includes team recipes
amplihack recipe list | grep react-component
```

### Conditional Step Execution

**Scenario**: Skip steps based on previous results.

```yaml
name: smart-deploy
description: "Deploy to staging or prod based on test results"
version: "1.0"

context:
  repo_path: "."
  environment: "staging"

steps:
  - id: run-tests
    type: bash
    command: "cd {{repo_path}} && npm test"
    output: test_output

  - id: check-coverage
    type: bash
    command: "cd {{repo_path}} && npm run coverage -- --json"
    parse_json: true
    output: coverage_results

  # Only deploy if coverage > 80%
  - id: deploy-staging
    type: bash
    command: "cd {{repo_path}} && ./deploy.sh staging"
    condition: "coverage_results.total.coverage > 80"
    output: deploy_result

  # Only deploy prod if staging succeeded AND environment is prod
  - id: deploy-prod
    type: bash
    command: "cd {{repo_path}} && ./deploy.sh production"
    condition: "deploy_result and environment == 'production'"
```

**Run with different environments**:

```bash
# Deploy to staging (coverage check applies)
amplihack recipe run smart-deploy \
  --context '{"environment": "staging"}'

# Deploy to prod (both checks apply)
amplihack recipe run smart-deploy \
  --context '{"environment": "production"}'
```

---

**See also**:

- [Recipe Runner Overview](README.md) - Architecture and YAML format
- [Recipe CLI How-To](../howto/recipe-cli-commands.md) - Command usage guide
- [Recipe CLI Reference](../reference/recipe-cli-reference.md) - Complete command documentation
