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

#### 2. Security Scan (Optional)
Placeholder for security scanning tools (non-blocking)

### Features
- **Fast execution**: Aggressive caching, parallel setup
- **Smart concurrency**: Cancels outdated runs automatically
- **Clear feedback**: Detailed status reporting
- **Graceful degradation**: Continues even if some tools missing

## Setup Instructions

### 1. Enable GitHub Actions
The workflow will automatically run once merged to main.

### 2. Configure Branch Protection (Recommended)

1. Go to Settings → Branches
2. Add rule for `main` branch
3. Enable these options:
   - ✅ Require status checks to pass before merging
   - ✅ Require branches to be up to date before merging
   - Select "CI / Validate Code" as required status check
   - ✅ Include administrators (optional but recommended)

### 3. Add Status Badge to README

Add this line to your main README.md:

```markdown
![CI](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/workflows/CI/badge.svg)
```

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

## Maintenance

### Adding new checks
1. Add tool to pre-commit config first
2. Test locally
3. Push and verify in CI

### Adjusting strictness
- Initially set to `continue-on-error: true` for gradual adoption
- Remove `continue-on-error` once codebase is clean
- Add more checks as team comfort grows