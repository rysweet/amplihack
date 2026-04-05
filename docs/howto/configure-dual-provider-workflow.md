# How to Configure Dual-Provider Workflow

> [Home](../index.md) > How-To > Configure Dual-Provider Workflow

This guide shows how to set up and run the `default-workflow` recipe against an Azure DevOps repository.

---

## Before You Start

You need:

- Azure CLI installed (`az --version`)
- `azure-devops` extension installed (`az extension list --query "[?name=='azure-devops']"`)
- Authenticated Azure session (`az account show`)
- ADO organization and project defaults configured (`az devops configure --defaults ...`)
- A git repository whose `origin` remote points to `dev.azure.com` or `visualstudio.com`

The workflow detects the provider automatically from the git remote URL. No additional recipe flags are needed.

---

## 1. Install and Configure the Azure CLI

```bash
# macOS
brew install azure-cli

# Linux (Debian/Ubuntu)
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Windows
winget install Microsoft.AzureCLI
```

Install the DevOps extension:

```bash
az extension add --name azure-devops
```

---

## 2. Authenticate

```bash
az login
# or for service principal / CI:
az login --service-principal \
  --username "$ARM_CLIENT_ID" \
  --password "$ARM_CLIENT_SECRET" \
  --tenant "$ARM_TENANT_ID"
```

Verify the session:

```bash
az account show --query "{subscription:name, tenant:tenantId}"
```

---

## 3. Set ADO Defaults

The `az boards` and `az repos` commands used by the workflow read organization and project from the CLI defaults. Set them once per shell or in your environment:

```bash
az devops configure --defaults \
  organization=https://dev.azure.com/YOUR_ORG \
  project=YOUR_PROJECT
```

Verify:

```bash
az devops configure --list
```

Expected output:

```
organization=https://dev.azure.com/YOUR_ORG
project=YOUR_PROJECT
```

If these are not set, `az boards work-item create` and `az repos pr create` will fail with a "no organization/project" error.

---

## 4. Verify the git Remote

The workflow reads the `origin` remote URL to determine the provider:

```bash
cd /path/to/your/ado-repo
git remote get-url origin
# Expected: https://dev.azure.com/org/project/_git/repo
#       or: git@ssh.dev.azure.com:v3/org/project/repo
```

Both HTTPS and SSH ADO remote formats are detected correctly (the detection checks for `dev.azure.com` or `visualstudio.com` anywhere in the URL).

---

## 5. Run the Workflow

No provider-specific flags are needed. Run exactly as you would for a GitHub repository:

```bash
amplihack recipe run default-workflow \
  -c "task_description=Fix the authentication timeout bug" \
  -c "repo_path=/home/user/src/my-ado-repo"
```

Or with `smart-orchestrator` (recommended for most tasks):

```bash
amplihack recipe run smart-orchestrator \
  -c "task_description=Fix the authentication timeout bug" \
  -c "repo_path=/home/user/src/my-ado-repo"
```

The workflow will:

1. Detect `GIT_PROVIDER=ado`
2. Create an ADO Task work item (`az boards work-item create`)
3. Continue through implementation, testing, commit, and push steps
4. Create a draft ADO pull request (`az repos pr create --draft`)

---

## 6. Verify the Work Item Was Created

After step-03 completes, the recipe context will contain `issue_number`. You can verify the work item independently:

```bash
az boards work-item show --id <issue_number>
```

And verify the draft PR after step-16:

```bash
az repos pr list --source-branch <branch-name>
```

---

## Troubleshooting

### `az boards work-item create` fails with exit 1

- Check `az account show` — session may have expired. Re-run `az login`.
- Check `az devops configure --list` — organization and project must be set.
- Check that the authenticated identity has permission to create work items in the project.

### `step-03b-extract-issue-number` fails to extract a number

- Verify that step-03 completed successfully and emitted a line matching `_workitems/edit/NNNN`.
- The regex matches `_workitems/edit/` followed by one or more digits. Unusual ADO URLs or partial output from `az` may not match.

### `az repos pr create` fails with "no commits between main and \<branch\>"

This is not ADO-specific. It means step-15 (commit and push) produced no commits on the branch. Check the step-15 output in the recipe run log.

### Work item is created with wrong type

The workflow uses `--type Task`. If your ADO project uses a custom process model (e.g., CMMI), `Task` may map to a different work item type or be unavailable. Adapt the `--type` value in `step-03-create-issue` to match your process template.
