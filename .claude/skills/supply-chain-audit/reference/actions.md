# GitHub Actions Supply Chain — Dimensions 1-4

## Dimension 1: Action Pinning

Scan all `.github/workflows/*.yml` and `.github/aw/*.yml` for `uses:` directives.

**Critical**: any `uses:` not pinned to a full 40-character commit SHA.
Examples of non-compliant values:

- `uses: actions/checkout@v4` (semver tag — mutable)
- `uses: aquasecurity/trivy-action@master` (branch — maximally dangerous)
- `uses: some-org/some-action@latest`

Compliant form: `uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683`

Check reusable workflows (`workflow_call`) for the same requirement.

Check composite actions: if a pinned action internally references another action
by tag (in its `action.yml`), flag as a transitive pinning gap.

**Fix template:**

```
# Replace tag/branch with SHA. Verify SHA from upstream git tag resolution.
# uses: <owner>/<repo>@<tag>
# becomes:
# uses: <owner>/<repo>@<full-40-char-sha>  # <tag>
```

## Dimension 2: Action Permission Scope

Parse `permissions:` blocks at workflow and job level.

Flag `contents: write`, `id-token: write`, `security-events: write`, or
`packages: write` when granted in a job that also uses non-first-party actions
(anything not `actions/*` or `github/*`).

**High**: overly broad permissions granted at workflow level applying to third-party steps.
**Medium**: broad permissions at job level where only a subset of steps need them.

Recommend: scope permissions to the minimum required per step. Use
`permissions: {}` at workflow level and explicit grants per job.

## Dimension 3: Secret Exposure Patterns

Detect secrets passed to third-party steps:

- `${{ secrets.* }}` in `env:` blocks of non-first-party action steps — **High**
- `${{ secrets.* }}` in `with:` parameters to non-first-party actions — **High**
- `${{ secrets.* }}` piped through `base64`, `jq`, `sed`, `echo` in `run:` steps — **Critical**
- `${{ github.token }}` passed explicitly to third-party action `with:` — **High**

Client-secret SP auth patterns (Azure):

- `AZURE_CLIENT_SECRET` or `AZURE_CREDENTIALS` env vars in steps — **Critical** (recommend OIDC)
- `aws-access-key-id` / `aws-secret-access-key` in `with:` — **Critical** (recommend OIDC)

## Dimension 4: Cache Poisoning Vectors

Identify `actions/cache` and `actions/cache/restore` usage.

**High**: cache stores executable binaries (tool installations, compilers, interpreters)
with a key that includes attacker-controllable input:

- `${{ github.head_ref }}` — PR branch name
- `${{ github.event.pull_request.title }}`
- Any value from `github.event` on `pull_request` trigger

**Medium**: binary cache with predictable-but-static key (no attacker influence,
but cache poisoning still possible via compromised upstream step in same job).

**Fix**: scope binary caches to protected branches only, or use content-addressed
keys (hash of lock files: `${{ hashFiles('**/package-lock.json') }}`).

## Dimension 13: Dangerous Trigger Patterns

### pull_request_target Misuse (Critical)

`pull_request_target` runs with write access and full secrets in the base repo
context — including for PRs from forks. If the workflow checks out and executes
PR code, it is arbitrary code execution with full secret access.

**Critical**: `pull_request_target` trigger combined with any of:

- `actions/checkout` with `ref: ${{ github.event.pull_request.head.sha }}` or `ref: ${{ github.head_ref }}`
- `run:` steps that interpolate `${{ github.event.pull_request.* }}` into shell commands
- `env:` values derived from PR event payload passed to `run:` steps

Safe use of `pull_request_target`: workflows that only label, comment, or
read base repo data — never check out fork code.

**Fix**: replace `pull_request_target` with `pull_request` for workflows that
build or test PR code. Reserve `pull_request_target` for bot-only workflows
(labeling, commenting) that do not check out the PR branch.

### workflow_run Privilege Escalation (High)

`workflow_run` triggers with write permissions when the triggering workflow
ran on a fork. Untrusted artifact content from fork workflows can reach the
privileged context.

**High**: `workflow_run` trigger that downloads artifacts from the triggering
run and uses the content in `run:` steps without sanitization.

**Fix**: validate all downloaded artifact content before use; never execute
downloaded artifacts as code.

### Self-Hosted Runner on PR Workflows (High)

Self-hosted runners may retain state between jobs. Fork PRs can access the
runner environment if the workflow trigger allows fork PRs.

**High**: `runs-on: self-hosted` (or custom runner label) in workflows
triggered by `pull_request` with `branches` allowing fork PRs.

**Fix**: use GitHub-hosted ephemeral runners for PR workflows from forks.
