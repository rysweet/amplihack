# Type Safety User’s Guide

## Automatic Type Safety Checks

- **On Every Push and Pull Request**
  - The CI workflow runs pyright strict type checks.
  - Any type error blocks the build and merge.

## Manual Type Safety Checks

- **Running Pyright Locally**
  - Command: `pyright .`
  - Ensures your changes are type-safe before committing/pushing.

- **Before Merging or PR Submission**
  - Always run `pyright .` and confirm zero errors.
  - Fix all type issues before opening PRs.

## Standards

- All public functions/classes must be annotated.
- Avoid `Any` types unless documented.

## Common Scenarios

- New feature: run pyright before push/PR.
- Refactor existing code: verify with pyright, CI will also enforce type safety.
- Dependency update: rerun pyright to catch new type issues.

All checks are strict; noncompliance prevents merging.
