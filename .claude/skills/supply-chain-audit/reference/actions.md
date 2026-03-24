# Dimensions 1-4: GitHub Actions Supply Chain

## Dimension 1: Action SHA Pinning

Every `uses:` step in `.github/workflows/*.yml` must reference a full 40-character commit SHA.

### Pattern to Detect (High/Critical)

```yaml
# VIOLATION — mutable semver tag
uses: actions/checkout@v4

# VIOLATION — mutable branch
uses: my-org/my-action@main

# CORRECT — immutable SHA with version comment
uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # v4.2.2
```

### Severity Rules

| Condition                                              | Severity |
| ------------------------------------------------------ | -------- |
| Third-party action + write permissions + secret access | Critical |
| Third-party action + semver/branch ref                 | High     |
| First-party org action + semver ref                    | Medium   |
| `@v1` major-only ref (any)                             | High     |

### SHA Lookup

```bash
# Look up SHA for a specific tag
gh api repos/actions/checkout/git/ref/tags/v4.2.2 --jq '.object.sha'

# If tag points to a tag object (not commit), dereference it
gh api repos/actions/checkout/git/tags/<tag-object-sha> --jq '.object.sha'
```

### Fix Template

```yaml
# Replace:
uses: actions/checkout@v4
# With:
uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # v4.2.2
```

### Common Actions SHA Reference (verify at time of audit — these change with releases)

| Action                     | Look up SHA via                                      |
| -------------------------- | ---------------------------------------------------- |
| `actions/checkout`         | https://github.com/actions/checkout/releases         |
| `actions/setup-python`     | https://github.com/actions/setup-python/releases     |
| `actions/setup-node`       | https://github.com/actions/setup-node/releases       |
| `actions/setup-go`         | https://github.com/actions/setup-go/releases         |
| `docker/build-push-action` | https://github.com/docker/build-push-action/releases |

---

## Dimension 2: Workflow Permissions

Overly broad permissions expose the GITHUB_TOKEN to compromise.

### Pattern to Detect

```yaml
# VIOLATION — implicit all permissions (default behavior pre-2023)
# No permissions key at all in workflow

# VIOLATION — explicit write-all
permissions: write-all

# CORRECT — read-all at top, minimal write at job level
permissions: read-all

jobs:
  build:
    permissions:
      contents: read
      packages: write  # only what this job needs
```

### Checks

1. Top-level `permissions:` key exists and is not `write-all`
2. Each job that writes (`contents: write`, `packages: write`, `id-token: write`, etc.) has a comment explaining why
3. `pull_request_target` trigger without explicit permissions restriction — flag Critical (privilege escalation risk)

### Severity

| Finding                                                     | Severity |
| ----------------------------------------------------------- | -------- |
| `pull_request_target` + no explicit `permissions: read-all` | Critical |
| No `permissions` key at workflow level (implicit all)       | High     |
| `permissions: write-all`                                    | High     |
| Job with `contents: write` but no justification comment     | Medium   |

---

## Dimension 3: Secret Exposure

### Pattern to Detect

```yaml
# VIOLATION — secret echoed to log
- run: echo "${{ secrets.MY_SECRET }}"

# VIOLATION — secret exported to env then used in shell
- run: export TOKEN=$TOKEN && curl -H "Auth: $TOKEN" ...
  env:
    TOKEN: ${{ secrets.API_TOKEN }}
# (not a violation by itself but flag for review if token is printed anywhere)

# VIOLATION — ACTIONS_STEP_DEBUG unguarded
- run: |
    echo "Debug: ${{ secrets.AWS_KEY }}"
  if: ${{ runner.debug == '1' }}
```

### Checks

1. Grep for `echo.*secrets\.` — flag Critical
2. Grep for `print.*secrets\.` — flag Critical
3. Check `ACTIONS_RUNNER_DEBUG` / `ACTIONS_STEP_DEBUG` handling
4. Check for secrets in `actions/cache` keys — flag High (cache key logged)
5. Check that `${{ github.event.pull_request.head.sha }}` is not used to check out untrusted code in `pull_request_target`

### Severity

| Finding                                         | Severity |
| ----------------------------------------------- | -------- |
| Secret echoed to log                            | Critical |
| Secret in cache key                             | High     |
| Untrusted ref checkout in `pull_request_target` | Critical |

---

## Dimension 4: Cache Poisoning

### Pattern to Detect

```yaml
# RISK — broad restore-keys may restore cache from untrusted branch
- uses: actions/cache@<sha> # verify this is pinned
  with:
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-node-    # broad fallback — may restore attacker-poisoned cache
```

### Checks

1. `restore-keys:` breadth — single broad fallback matches too many keys
2. Cache key includes content hash (`hashFiles(...)`) — required
3. `actions/cache` action itself is SHA-pinned (Dimension 1 catch)
4. Workflow uses `cache: 'npm'` shorthand in `setup-node` — verify the version is pinned

### Severity

| Finding                                           | Severity |
| ------------------------------------------------- | -------- |
| No `hashFiles` in cache key                       | High     |
| Very broad `restore-keys` (single OS prefix only) | Medium   |
| `actions/cache` unpinned (also caught by Dim 1)   | High     |

---

## Verification Checklist (GitHub Actions)

- [ ] Every `uses:` step has a full 40-char SHA
- [ ] SHA comment matches the version tag
- [ ] Top-level `permissions: read-all` present
- [ ] No `pull_request_target` without explicit permissions restriction
- [ ] No `echo "${{ secrets.* }}"` patterns
- [ ] Cache keys include `hashFiles`
- [ ] No broad single-token `restore-keys`
