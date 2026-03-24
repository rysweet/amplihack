# Dimension 6: Credential Hygiene and OIDC Migration

## Overview

Long-lived credentials (static tokens, API keys, service account keys) in CI/CD are
a persistent supply chain risk. OIDC (OpenID Connect) federated identity eliminates
the need for long-lived secrets entirely for cloud provider access.

---

## Detection: Long-Lived Secrets to Flag

### Detection Commands

```bash
# Dim 6 — scan workflow files for long-lived credential secret names
grep -rn "AWS_ACCESS_KEY_ID\|AWS_SECRET_ACCESS_KEY\|AZURE_CREDENTIALS\|GOOGLE_CREDENTIALS\|GCP_SA_KEY\|AZURE_CLIENT_SECRET" .github/workflows/ 2>/dev/null

# Dim 6 — detect static credentials passed to cloud provider actions
grep -rn "aws-access-key-id\|aws-secret-access-key\|creds:" .github/workflows/ 2>/dev/null

# Dim 6 — check for OIDC-capable actions that are using secret-based auth instead
grep -rn "configure-aws-credentials\|azure/login\|google-github-actions/auth" .github/workflows/ 2>/dev/null
```

### Secrets That Should Migrate to OIDC

```yaml
# REVIEW — candidates for OIDC migration
secrets:
  AWS_ACCESS_KEY_ID         # → use aws-actions/configure-aws-credentials with OIDC
  AWS_SECRET_ACCESS_KEY     # → same
  AZURE_CREDENTIALS         # → use azure/login with OIDC
  GOOGLE_CREDENTIALS        # → use google-github-actions/auth with OIDC
  GCP_SA_KEY                # → same
  AZURE_CLIENT_SECRET       # → use federated identity credential
```

### Secrets That Cannot Migrate (Accept and Document)

```yaml
# ACCEPTABLE — no OIDC alternative exists
secrets:
  DOCKERHUB_TOKEN           # DockerHub has no OIDC support for GitHub Actions
  NPM_TOKEN                 # npm registry has no OIDC push support
  PYPI_TOKEN                # PyPI has OIDC via trusted publishers (migrate if possible)
  SLACK_WEBHOOK             # notification-only, rotate regularly
```

### PyPI Trusted Publishers (OIDC Available)

PyPI supports OIDC via "trusted publishers" — flag `PYPI_TOKEN` as a migration candidate:

```yaml
# VIOLATION — long-lived API token
- name: Publish to PyPI
  uses: pypa/gh-action-pypi-publish@<sha>
  with:
    password: ${{ secrets.PYPI_TOKEN }}

# CORRECT — OIDC trusted publisher (no secret needed)
jobs:
  publish:
    permissions:
      id-token: write  # required for OIDC
    steps:
      - uses: pypa/gh-action-pypi-publish@<sha>
        # no password needed — OIDC authenticates automatically
```

---

## OIDC Migration Patterns

### AWS

```yaml
# CORRECT — OIDC for AWS
jobs:
  deploy:
    permissions:
      id-token: write # required for OIDC token request
      contents: read
    steps:
      - uses: aws-actions/configure-aws-credentials@<sha> # pin SHA
        with:
          role-to-assume: arn:aws:iam::123456789:role/github-actions-deploy
          role-session-name: github-actions-${{ github.run_id }}
          aws-region: us-east-1
```

### Azure

```yaml
# CORRECT — OIDC for Azure
jobs:
  deploy:
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: azure/login@<sha> # pin SHA
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
          # No client-secret — uses OIDC federated identity
```

### GCP

```yaml
# CORRECT — OIDC for GCP
jobs:
  deploy:
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: google-github-actions/auth@<sha> # pin SHA
        with:
          workload_identity_provider: projects/123/locations/global/workloadIdentityPools/github/providers/github
          service_account: deploy@project.iam.gserviceaccount.com
          # No service account key JSON — uses OIDC
```

---

## Subject Constraint Verification

OIDC tokens without subject constraints allow any repository to assume the role.

### AWS Trust Policy (Correct)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::123456789:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          "token.actions.githubusercontent.com:sub": "repo:my-org/my-repo:ref:refs/heads/main"
        }
      }
    }
  ]
}
```

### Subject Constraint Audit Checks

1. AWS: IAM role trust policy has `sub` condition — not just `aud`
2. Azure: Federated credential has `subject` set to specific repo+branch
3. GCP: Workload Identity Pool has attribute condition on repository

Flag as **High** if OIDC is used but subject constraints are missing (any repo can assume the role).

---

## Secret Rotation Assessment

For secrets that cannot migrate to OIDC:

```yaml
# Flag for rotation audit if age > 90 days:
# - Check GitHub secret creation date via API
gh api repos/{owner}/{repo}/actions/secrets/{secret_name} --jq '.updated_at'
```

### Severity

| Finding                                                                     | Severity |
| --------------------------------------------------------------------------- | -------- |
| Long-lived cloud credential (AWS/Azure/GCP) with OIDC alternative available | High     |
| OIDC configured but no subject constraint                                   | High     |
| OIDC `id-token: write` at workflow level (not job level)                    | Medium   |
| Secret older than 90 days with no documented rotation policy                | Medium   |
| `PYPI_TOKEN` when PyPI trusted publishers is available                      | Medium   |

---

## Verification Checklist (Credentials)

- [ ] AWS/Azure/GCP access uses OIDC, not static credentials
- [ ] OIDC subject constraints lock down to specific repo + branch
- [ ] `id-token: write` permission is at job level, not workflow level
- [ ] PyPI publishing uses trusted publishers if possible
- [ ] Remaining long-lived secrets are documented with rotation policy
- [ ] No credentials committed in workflow files or `.env` files
