# CI/CD Pipeline Documentation

## Overview

This GitHub Actions CI pipeline ensures code quality by running formatting, linting, and test checks on every pull request.

## Workflow: ci.yml

### Triggers

- **Pull Requests**: Runs on open, synchronize (new commits), and reopen
- **Main Branch**: Runs on pushes to main for post-merge validation

### Jobs

#### 1. Validate Code

Runs all code quality checks:

- **Pre-commit hooks**: Formatting, linting for all languages
- **Python tests**: pytest suite
- **JavaScript/TypeScript tests**: npm test (if applicable)

### Features

- **Fast execution**: Aggressive caching, parallel setup
- **Smart concurrency**: Cancels outdated runs automatically
- **Clear feedback**: Detailed status reporting
- **Graceful degradation**: Continues even if some tools missing

## Local Testing

Before pushing, run the same checks locally:

```bash
# Run all pre-commit hooks
pre-commit run --all-files

# Run Python tests
pytest

# Run JavaScript tests (if applicable)
npm test
```

## Troubleshooting

### Workflow not running?

- Check if Actions are enabled in repository settings
- Verify file is in `.github/workflows/` directory
- Ensure file has `.yml` or `.yaml` extension

### Checks failing?

1. Check the workflow logs for specific errors
2. Run checks locally to reproduce
3. Fix issues and push again

### Too slow?

- Check cache hit rates in logs
- Consider running fewer hooks
- Use `fetch-depth: 1` if full history not needed

## Agentic Workflows (gh-aw)

Several workflows use GitHub's Agentic Workflows framework (`gh-aw`). These are defined as `.md` source files that compile into `.lock.yml` workflow files via `gh aw compile`.

### Lockdown Mode

The GitHub MCP server in gh-aw workflows supports a lockdown mode that restricts the token used for API access:

- **`lockdown: true`** (explicit): Requires `GH_AW_GITHUB_TOKEN` or `GH_AW_GITHUB_MCP_SERVER_TOKEN` as a repository secret with a fine-grained PAT. The workflow will **fail** if neither secret is configured.
- **`lockdown: false`** (automatic): Uses automatic lockdown detection that enables lockdown when a custom PAT is available and gracefully falls back to `GITHUB_TOKEN` when not. This is the **recommended default** for most workflows.

To change lockdown mode, edit the `tools.github.lockdown` field in the `.md` source file and recompile with `gh aw compile`.

### Editing Agentic Workflows

1. Edit the `.md` source file (e.g., `pr-triage-agent.md`)
2. Run `gh aw compile` to regenerate the `.lock.yml`
3. Never edit `.lock.yml` files directly (they are auto-generated)

## Maintenance

### Adding new checks

1. Add tool to pre-commit config first
2. Test locally
3. Push and verify in CI

### Adjusting strictness

- Initially set to `continue-on-error: true` for gradual adoption
- Remove `continue-on-error` once codebase is clean
- Add more checks as team comfort grows
