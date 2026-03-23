# Credentials and OIDC — Dimension 6

## OIDC vs Secret-Based Auth

Detect Azure/AWS/GCP login steps using static credentials:

**Azure** (Critical):

- `AZURE_CREDENTIALS` env var (JSON SP credentials)
- `AZURE_CLIENT_SECRET` env var
- `azure/login@*` with `creds: ${{ secrets.AZURE_CREDENTIALS }}`

**AWS** (Critical):

- `aws-access-key-id` + `aws-secret-access-key` in `aws-actions/configure-aws-credentials`

**GCP** (Critical):

- `credentials_json` in `google-github-actions/auth`

For each, recommend OIDC federated credential migration.

## OIDC Subject Constraint Verification

When OIDC is already in use, verify subject constraints are narrow:

**High**: federated credential subject matches `repo:*` or `refs/heads/*` (too broad).
**Medium**: subject matches specific repo but allows all branches (`refs/heads/*`).
**Compliant**: subject scoped to `refs/heads/main` or specific environment.

Check that the federated credential in Azure AD / AWS IAM / GCP Workload Identity
is scoped to the minimum required branch/environment.

## Fix Templates

Azure OIDC migration:

```yaml
- uses: azure/login@<sha>
  with:
    client-id: ${{ secrets.AZURE_CLIENT_ID }}
    tenant-id: ${{ secrets.AZURE_TENANT_ID }}
    subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
# (no client-secret; uses OIDC federation)
# Required workflow permission: id-token: write
```

AWS OIDC migration:

```yaml
- uses: aws-actions/configure-aws-credentials@<sha>
  with:
    role-to-assume: arn:aws:iam::123456789012:role/GitHubActions
    aws-region: us-east-1
# (no access-key-id / secret-access-key)
```
