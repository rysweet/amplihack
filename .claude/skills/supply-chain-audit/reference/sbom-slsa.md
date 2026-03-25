# SBOM, CVSS Scoring, SLSA Compliance, and Fix-PR Workflow

## Table of Contents

1. [SBOM Generation](#sbom-generation)
2. [CVSS Severity Mapping](#cvss-severity-mapping)
3. [SLSA L1-L4 Compliance](#slsa-l1-l4-compliance)
4. [Fix-PR Generation Workflow](#fix-pr-generation-workflow)
5. [Integration with amplihack Skills](#integration-with-amplihack-skills)

---

## SBOM Generation

A Software Bill of Materials documents all components in a software artifact.
SBOM generation is required for SLSA L1+ and increasingly mandated by
US Executive Order 14028 (2021) and EU CRA (2024).

### Tooling by Artifact Type

| Artifact        | Tool       | Format    | Command                                               |
| --------------- | ---------- | --------- | ----------------------------------------------------- |
| Container image | syft       | SPDX JSON | `syft <image>@<digest> -o spdx-json > sbom.spdx.json` |
| Container image | trivy      | CycloneDX | `trivy image --format cyclonedx <image>@<digest>`     |
| Python project  | syft       | SPDX JSON | `syft dir:. -o spdx-json > sbom.spdx.json`            |
| Node.js project | cdxgen     | CycloneDX | `cdxgen -t nodejs -o bom.json`                        |
| Go project      | syft       | SPDX JSON | `syft dir:. -o spdx-json`                             |
| .NET project    | cdxgen     | CycloneDX | `cdxgen -t dotnet -o bom.json`                        |
| Rust project    | cargo-sbom | SPDX JSON | `cargo sbom --output-format spdx_json_2_3`            |

### SBOM Attestation in CI

Attach SBOM to GitHub release artifacts using cosign:

```yaml
- name: Generate SBOM
  uses: anchore/sbom-action@<sha> # pin to full SHA — see actions.md Dim 1
  with:
    format: spdx-json
    output-file: sbom.spdx.json

- name: Sign SBOM with cosign
  env:
    COSIGN_EXPERIMENTAL: 1
  run: |
    cosign attest --predicate sbom.spdx.json \
      --type spdxjson \
      ${{ env.IMAGE_REF }}
```

### SBOM File Handling (Warn-Before-Write)

Before writing an SBOM file to the repository, warn the user:

```
⚠ SBOM Write Advisory:
Writing sbom.spdx.json to the repository will make your full dependency tree
publicly visible. Consider whether this is intended before committing.

Recommended actions:
  1. Add to .gitignore if not intended for version control:
       echo "sbom.spdx.json" >> .gitignore
       echo "*.cyclonedx.json" >> .gitignore
  2. If storing in the repo is intentional (e.g., for release assets):
       - Add to .github/release-assets/ not to the project root
       - Attach to GitHub Releases rather than committing to main branch
  3. For CI-only SBOM (recommended):
       - Upload as workflow artifact: actions/upload-artifact
       - Attach to release via gh release upload
       - Never commit to version control
```

### Vulnerability Scanning from SBOM

```bash
# grype — scan SBOM for CVEs
grype sbom:./sbom.spdx.json --fail-on high

# osv-scanner — scan against OSV vulnerability database
osv-scanner --sbom=sbom.spdx.json
```

---

## CVSS Severity Mapping

This skill uses CVSS v3.1 base score bands for all severity ratings:

| Label        | CVSS Range | Action Required                               |
| ------------ | ---------- | --------------------------------------------- |
| **Critical** | 9.0-10.0   | Block deployment; fix before merge            |
| **High**     | 7.0-8.9    | Fix before next release; track in sprint      |
| **Medium**   | 4.0-6.9    | Fix within 30 days; track in backlog          |
| **Info**     | 0.1-3.9    | Informational; fix in next maintenance window |

### Supply Chain Risk Scoring (Non-CVE Findings)

When a finding is not associated with a CVE (e.g., mutable action ref, missing
lock file), use the following heuristic to assign severity:

| Risk Factor                       | Score Modifier |
| --------------------------------- | -------------- |
| Third-party code execution        | +3.0           |
| Write permission in same job      | +2.0           |
| Secret access in same job         | +2.0           |
| Production path (deploy workflow) | +1.5           |
| Dev/test only path                | -2.0           |
| Org-internal code                 | -1.5           |

Example: Unpin third-party action (base 6.0) + write permissions (+2.0) + secret access (+2.0) = 10.0 → **Critical**

---

## SLSA L1-L4 Compliance

SLSA (Supply-chain Levels for Software Artifacts) is a framework for measuring
supply chain security maturity. https://slsa.dev

### Compliance Table

| SLSA Level | Build              | Provenance      | Source             | Blockers (Common)                                                            |
| ---------- | ------------------ | --------------- | ------------------ | ---------------------------------------------------------------------------- |
| **L1**     | Scripted           | Exists          | -                  | No provenance generated at all                                               |
| **L2**     | Build service      | Authenticated   | -                  | Build not on hosted CI; provenance not signed                                |
| **L3**     | Hardened           | Non-falsifiable | -                  | Build service can't inject provenance; GitHub Actions without SLSA generator |
| **L4**     | Two-party reviewed | -               | Two-party reviewed | Requires organizational process changes                                      |

### Achieving SLSA L3 with GitHub Actions

SLSA L3 is achievable with GitHub Actions + the SLSA generic generator:

```yaml
# .github/workflows/release.yml
jobs:
  build:
    outputs:
      hashes: ${{ steps.hash.outputs.hashes }}
    steps:
      - name: Build artifact
        run: |
          make build
          sha256sum my-artifact > hashes.txt

      - id: hash
        run: echo "hashes=$(cat hashes.txt | base64 -w0)" >> $GITHUB_OUTPUT

  provenance:
    needs: [build]
    permissions:
      actions: read
      id-token: write
      contents: write
    uses: slsa-framework/slsa-github-generator/.github/workflows/generator_generic_slsa3.yml@1234567890abcdef1234567890abcdef12345678 # v2.0.0 — replace with SHA from https://github.com/slsa-framework/slsa-github-generator/releases
    # IMPORTANT: Pin to full SHA — look up current SHA at:
    # https://github.com/slsa-framework/slsa-github-generator/releases
    with:
      base64-subjects: "${{ needs.build.outputs.hashes }}"
      upload-assets: true
```

**Note on SHA pinning for the SLSA generator itself**: The SLSA generator workflow
(`slsa-framework/slsa-github-generator`) must itself be pinned to a full commit SHA
(not a semver tag), per Dimension 1 of this skill. Using a semver tag here would be
a High finding — an ironic violation in a provenance workflow.

### Verification of SLSA Provenance

```bash
# Install slsa-verifier
go install github.com/slsa-framework/slsa-verifier/v2/cli/slsa-verifier@latest

# Verify provenance for a release artifact
slsa-verifier verify-artifact \
  --provenance-path my-artifact.intoto.jsonl \
  --source-uri github.com/myorg/myrepo \
  --source-tag v1.2.3 \
  my-artifact
```

### SLSA Readiness Assessment Template

Include this in audit reports:

```markdown
### SLSA Readiness

| Requirement                              | Status  | Gap                         |
| ---------------------------------------- | ------- | --------------------------- |
| Build is scripted (not manual)           | ✅ / ❌ |                             |
| Build runs on hosted CI (GitHub Actions) | ✅ / ❌ |                             |
| Provenance is generated per build        | ✅ / ❌ | Add SLSA generator workflow |
| Provenance is signed (OIDC-based)        | ✅ / ❌ | Requires id-token: write    |
| All action refs pinned to SHA            | ✅ / ❌ | See Dim 1 findings          |
| SLSA generator itself is SHA-pinned      | ✅ / ❌ |                             |

**Current SLSA Level**: L0 / L1 / L2 / L3
**Blockers to next level**: [list]
```

---

## Fix-PR Generation Workflow

When audit produces actionable findings, generate a fix PR using this checklist:

### Priority Ordering for Fix PR

1. **Critical findings** — block all other PRs until resolved
2. **High findings in production deploy workflows** — fix before next release
3. **High findings in all other workflows** — fix within sprint
4. **Medium findings** — batch into single "supply chain hygiene" PR
5. **Info findings** — batch or close as accepted risk

### Fix PR Safety Checklist

Before opening a fix PR:

- [ ] Verify each new SHA corresponds to the expected version tag
- [ ] For actions: `gh api repos/{owner}/{action}/git/ref/tags/{tag}` confirms SHA
- [ ] For containers: `crane digest {image}:{tag}` confirms digest
- [ ] Add version comment after each pinned SHA
- [ ] Run CI on fix branch before requesting review
- [ ] For lock file additions: regenerate with `npm ci`, `cargo update`, etc.
- [ ] Document any accepted-risk findings in `.supply-chain-accepted-risks.yml`

### Accepted Risk Documentation Template

`.supply-chain-accepted-risks.yml` uses YAML format matching the schema in `contracts.md`:

```yaml
# .supply-chain-accepted-risks.yml
- id: HIGH-001
  file: .github/workflows/ci.yml
  line: 0
  dimension: 6
  rationale: "DockerHub does not support OIDC for GitHub Actions; token scoped to single repository, rotated quarterly."
  review_date: "2026-06-01"

- id: INFO-002
  file: .github/workflows/internal.yml
  line: 8
  dimension: 1
  rationale: "Internal action maintained by Platform team; monitored via internal security review process."
  review_date: "2026-09-01"
```

**Constraints** (enforced by `contracts.md` error handling):

- File size ≤ 64KB (`ACCEPTED_RISKS_OVERFLOW` if exceeded)
- No wildcards in `id` field
- `review_date` must be a future date — past dates restore original severity
- Critical findings cannot be suppressed regardless of matching entry

---

## Integration with amplihack Skills

### Delegate to dependency-resolver

After finding lock file issues (Dims 7, 8, 9, 10, 11), delegate:

```
"I found missing/outdated lock files in this audit. Delegating to dependency-resolver
for conflict resolution and lock file regeneration."
```

Handoff context to pass:

- Which ecosystems have lock file issues
- Whether conflicts exist between transitive deps
- CI command to validate after fix (`npm ci`, `cargo build`, `go mod verify`)

### Delegate to pre-commit-manager

After audit completes, offer to install enforcement hooks:

```
"Supply chain audit complete. To prevent regressions, I recommend installing
pre-commit hooks via pre-commit-manager for:
- SHA pinning validation (actions-security via zizmor or actionlint)
- npm ci enforcement (lock file check hook)
- go mod verify hook
- detect-secrets for credential scanning"
```
