---
name: gh-aw-setup
version: 1.0.0
description: Configure and set up GitHub Agentic Workflows (gh-aw) in a repository, including the Repo Guardian workflow that blocks PRs containing ephemeral content (meeting notes, temp scripts, point-in-time documents). Auto-activates for repo guardian setup, gh-aw configuration, or agentic workflow bootstrapping requests.
source_urls:
  - https://github.com/github/gh-aw
  - https://github.com/github/gh-aw/blob/main/.github/aw/github-agentic-workflows.md
auto_activates:
  - "set up repo guardian"
  - "configure gh-aw"
  - "add repo guardian"
  - "setup github agentic workflows"
  - "bootstrap gh-aw"
  - "install repo guardian"
token_budget: 2000
---

# GitHub Agentic Workflows Setup Skill

## Purpose

This skill guides you through setting up GitHub Agentic Workflows (gh-aw) in a
repository, with a focus on the **Repo Guardian** workflow — a production-ready
agentic workflow that reviews every PR for ephemeral content that doesn't belong
in the repository.

## What Is Repo Guardian?

Repo Guardian is an AI-powered PR reviewer that automatically detects and flags:

- **Meeting notes** and sprint retrospectives committed to the repo
- **Temporary scripts** (`fix-thing.sh`, `one-off-migration.py`)
- **Point-in-time documents** that will become stale (status updates, diaries)
- **Snapshot files** with date prefixes (`2024-01-15-deployment-notes.md`)

It posts a PR comment with findings and an override mechanism for legitimate exceptions.

### Two-Workflow Architecture

Repo Guardian uses two complementary workflows:

1. **`repo-guardian.md`** — The gh-aw agentic workflow (AI agent that reviews the PR)
2. **`repo-guardian-gate.yml`** — A standard GitHub Actions workflow that enforces
   the agent's findings as a blocking CI check

## Prerequisites

```bash
# 1. Install gh CLI
gh --version

# 2. Install gh-aw extension
gh extension install github/gh-aw
gh aw --version

# 3. Verify repository access
gh auth status
```

## Quick Setup (3 Steps)

### Step 1: Copy Workflow Files

Copy the template files from this skill into your repository:

```bash
# From the skill directory, copy templates:
mkdir -p .github/workflows

# Copy the agentic workflow prompt
cp repo-guardian.md .github/workflows/repo-guardian.md

# Copy the enforcement gate
cp repo-guardian-gate.yml .github/workflows/repo-guardian-gate.yml
```

> **Or use the templates in this skill directory** — see `repo-guardian.md` and
> `repo-guardian-gate.yml` alongside this file.

### Step 2: Compile the Agentic Workflow

The `.md` file must be compiled to a `.lock.yml` before GitHub Actions can run it:

```bash
cd .github/workflows
gh aw compile repo-guardian

# Verify the lock file was created
ls repo-guardian.lock.yml
```

### Step 3: Configure Required Secrets

The gh-aw agent requires a GitHub Copilot token:

1. Go to **Repository Settings → Secrets and variables → Actions**
2. Add secret: `COPILOT_GITHUB_TOKEN`
   - Value: A GitHub personal access token with Copilot access
   - Required scopes: `read:org`, `repo`

```bash
# Or via CLI:
gh secret set COPILOT_GITHUB_TOKEN --body "<your-token>"
```

## Commit and Push

```bash
git add .github/workflows/repo-guardian.md \
        .github/workflows/repo-guardian.lock.yml \
        .github/workflows/repo-guardian-gate.yml

git commit -m "feat: Add Repo Guardian agentic workflow

Adds AI-powered PR review that detects and blocks ephemeral content:
- Meeting notes, sprint retrospectives, status updates
- Temporary/one-off scripts
- Point-in-time documents that will become stale

Uses gh-aw (GitHub Agentic Workflows) with GitHub Copilot CLI engine.
Requires COPILOT_GITHUB_TOKEN secret to be configured.

Two-workflow setup:
- repo-guardian.md: AI agent prompt (compiled to repo-guardian.lock.yml)
- repo-guardian-gate.yml: CI enforcement gate

Co-Authored-By: Claude Sonnet 4.6 (1M context) <noreply@anthropic.com>"

git push
```

## Optional: Branch Protection

For maximum enforcement, require the Repo Guardian Gate check to pass:

1. Go to **Repository Settings → Branches → Branch protection rules**
2. Edit the rule for `main` (or your default branch)
3. Under **Require status checks to pass before merging**, add:
   - `Repo Guardian Gate`
4. Save the rule

## Override Mechanism

When a legitimate file gets flagged, any collaborator can add a PR comment:

```
repo-guardian:override This is a durable ADR, not a meeting note
```

The reason after `override` is **required** for auditability. The gate will then
pass, and the agent will post an acknowledgment comment.

## Optional: Custom Configuration

Create `repo-guardian.config.json` in the repo root to customize behavior:

```json
{
  "allowlist": [
    "docs/decisions/**",
    "CHANGELOG.md"
  ],
  "extraRules": "Also flag files in the /scratch directory unconditionally."
}
```

> The config file itself is explicitly excluded from Repo Guardian's checks.

## How It Works

### Trigger

Both workflows trigger on `pull_request` events (opened, synchronize, reopened).

### Agentic Workflow Flow

```
PR opened
  → repo-guardian.lock.yml activates
  → gh-aw spawns Copilot agent in sandboxed container
  → Agent reads changed files via GitHub MCP server (read-only)
  → Agent analyzes each file for ephemeral content
  → Agent posts ONE comment: "Repo Guardian - Passed" or "Repo Guardian - Action Required"
  → safe-outputs enforces max 1 comment
```

### Gate Flow

```
PR opened / comment posted
  → repo-guardian-gate.yml activates
  → Waits 60s for agent comment (on PR events)
  → Reads all PR comments
  → If "Action Required" exists AND no override → fails CI
  → If "Passed" or override present → passes CI
```

### Security Model

- Agent has **read-only** GitHub access (no write permissions in the agent job)
- All mutations (comments) go through **safe-outputs** with a max of 1
- Override requires a **non-empty reason** (prevents trivial bypasses)
- Gate enforces findings **independently** from the agent (defense in depth)

## Troubleshooting

**Agent not triggering:**

- Verify `COPILOT_GITHUB_TOKEN` secret exists
- Check that `repo-guardian.lock.yml` was committed (not just the `.md`)
- Ensure the PR is from the same repository (fork PRs are excluded for security)

**Gate passing even with violations:**

- Check that `repo-guardian-gate.yml` is on the default branch
- Verify the gate is required in branch protection rules

**False positives:**

- Add an override comment: `repo-guardian:override <reason>`
- Or add the path to `repo-guardian.config.json` allowlist

**Recompiling after edits:**

```bash
cd .github/workflows
gh aw compile repo-guardian
git add repo-guardian.lock.yml
git commit -m "chore: Recompile repo-guardian workflow"
```

## Relationship to gh-aw-adoption Skill

This skill is **focused setup** for a specific, high-value workflow (Repo
Guardian). For **full gh-aw adoption** across an entire repository (15-20
workflows covering security, automation, quality), use the `gh-aw-adoption`
skill instead.

| Skill | Use When |
|-------|----------|
| `gh-aw-setup` | You want Repo Guardian specifically, or are bootstrapping gh-aw |
| `gh-aw-adoption` | You want comprehensive workflow automation (15-20 workflows) |
