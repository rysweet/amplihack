# SBOM Generation, SLSA Mapping, and Fix-PR Workflow

## SBOM Generation Guidance

A Software Bill of Materials documents all dependencies and their provenance.
Generate SBOMs during or after this audit to capture the current state.

### Recommended Tools by Ecosystem

| Ecosystem      | Tool                                             | Output Format   |
| -------------- | ------------------------------------------------ | --------------- |
| GitHub Actions | `anchore/sbom-action`                            | SPDX, CycloneDX |
| .NET / NuGet   | `dotnet sbom-tool` or `CycloneDX.Tool`           | CycloneDX JSON  |
| Python         | `syft`, `pip-audit --format cyclonedx`           | CycloneDX, SPDX |
| Rust           | `cargo-cyclonedx`                                | CycloneDX       |
| Node.js        | `syft`, `@cyclonedx/cyclonedx-npm`               | CycloneDX       |
| Go             | `syft`, `go-cyclonedx`                           | CycloneDX, SPDX |
| Containers     | `syft <image>`, `trivy image --format cyclonedx` | CycloneDX, SPDX |

SBOM artifacts should be:

1. Signed with Sigstore/cosign for attestation
2. Attached to GitHub releases as workflow artifacts
3. Submitted to a dependency tracking tool (e.g., Dependency-Track)

### Generating SBOM in GitHub Actions

```yaml
- uses: anchore/sbom-action@<sha>
  with:
    format: spdx-json
    artifact-name: sbom.spdx.json
```

## SLSA Level Mapping

The Supply-chain Levels for Software Artifacts (SLSA) framework defines four levels:

| SLSA Level      | Key Requirements                                         | Common Blockers Found by This Audit                    |
| --------------- | -------------------------------------------------------- | ------------------------------------------------------ |
| L1 — Provenance | Build produces signed provenance                         | No `slsa-framework/slsa-github-generator` in workflows |
| L2 — Hosted     | Build runs on hosted platform; source version controlled | Usually satisfied on GitHub-hosted runners             |
| L3 — Hardened   | Ephemeral, isolated build; verified dependencies         | Unpinned actions; mutable tags; broad permissions      |
| L4 — Paranoid   | Two-party review; hermetic builds                        | Requires significant process changes beyond CI config  |

### Generating SLSA Provenance

Add to release workflow:

```yaml
jobs:
  build:
    outputs:
      hashes: ${{ steps.hash.outputs.hashes }}
    steps:
      - name: Build
        run: make build
      - name: Generate hashes
        id: hash
        run: |
          sha256sum ./dist/* | base64 -w0

  provenance:
    needs: [build]
    uses: slsa-framework/slsa-github-generator/.github/workflows/generator_generic_slsa3.yml@v1.10.0
    with:
      base64-subjects: ${{ needs.build.outputs.hashes }}
    permissions:
      actions: read
      id-token: write
      contents: write
```

## Fix-PR Generation Workflow

After completing the audit, optionally generate fix PRs for Critical and High findings.

### Priority Order for Fix PRs

1. **Critical**: secret exposure / OIDC migration (highest risk)
2. **Critical**: mutable action references on main/protected branches
3. **High**: lock file missing or not enforced in CI
4. **High**: container base images using mutable tags
5. **Medium**: missing NuGet audit / cache key improvements

### Fix-PR Checklist

For each Critical/High finding, a fix PR should:

- [ ] Make only one logical change (one finding per PR for reviewability)
- [ ] Include test/verification step showing the fix works (e.g., CI passes with `--locked-mode`)
- [ ] Reference this audit report and the specific finding ID
- [ ] Not introduce new supply chain risks in the fix itself (e.g., adding a new unpinned action)

### Integration with amplihack Dependency Resolver

After generating fix PRs for CI workflow changes, run `dependency-resolver` to:

- Verify local tool versions match what the updated CI expects
- Detect any new version drift introduced by the fixes

### Integration with amplihack Pre-Commit Manager

After audit, run `pre-commit-manager` to install hooks enforcing:

- Action SHA pinning check on `.github/workflows/*.yml` changes
- `npm ci` enforcement (hook rejects `npm install` in CI workflow files)
- detect-secrets scan to catch new secret patterns before commit
