# Tutorial: Running the Default Workflow on an Azure DevOps Repository

**Time to Complete**: 20 minutes
**Skill Level**: Intermediate
**Prerequisites**: An ADO repository clone, `az` CLI installed and authenticated, ADO organization and project defaults configured.

This tutorial walks through a complete `default-workflow` run on an Azure DevOps repository, from the first `detect_git_provider()` call through a committed draft pull request.

---

## What You'll Learn

By the end of this tutorial you will:

1. Verify your ADO environment is ready for the workflow
2. Observe how `detect_git_provider()` routes execution at runtime
3. See an ADO work item created via `az boards work-item create`
4. Understand the `_workitems/edit/NNN` URL format and why `step-03b` can parse it
5. See a draft ADO PR created via `az repos pr create --draft`
6. Diagnose the two most common ADO-specific failure modes

---

## Step 1: Verify the Environment

Confirm all prerequisites are in place before launching the workflow.

```bash
# 1. az CLI is present
az --version | head -1

# 2. DevOps extension is installed
az extension list --query "[?name=='azure-devops'].version" -o tsv

# 3. Authenticated session exists
az account show --query "{sub:name, tenant:tenantId}" -o json

# 4. ADO defaults are configured
az devops configure --list

# 5. The repository remote is ADO
cd /path/to/your/ado-repo
git remote get-url origin
```

Expected output for the remote:

```
https://dev.azure.com/myorg/myproject/_git/myrepo
```

---

## Step 2: Understand What detect_git_provider() Does

Before running the workflow, read the function in `step-03-create-issue`:

```bash
grep -A8 "detect_git_provider" \
  amplifier-bundle/recipes/default-workflow.yaml | head -12
```

You will see:

```bash
detect_git_provider() {
  local remote_url
  remote_url=$(git remote get-url origin 2>/dev/null || echo '')
  if [[ "$remote_url" == *"dev.azure.com"* ]] || \
     [[ "$remote_url" == *"visualstudio.com"* ]]; then
    echo "ado"
  else
    echo "github"
  fi
}
```

This function runs once per provider-aware step, right after `set -euo pipefail`. The result is stored in `GIT_PROVIDER` and used to choose the ADO or GitHub command branch.

---

## Step 3: Run the Workflow

Launch with your ADO repository:

```bash
amplihack recipe run default-workflow \
  -c "task_description=Fix the session timeout bug reported in #12345" \
  -c "repo_path=/path/to/your/ado-repo"
```

Watch the step-03 output. You will see:

```
=== Step 3: Creating Issue/Work Item (provider: ado) ===
INFO: task_description references work item #12345 — verifying it exists
INFO: Reusing existing work item #12345 — skipping creation
```

or, if no existing work item is referenced:

```
=== Step 3: Creating Issue/Work Item (provider: ado) ===
INFO: Searching open ADO work items for similar title
INFO: No matching open work item found — proceeding to create
INFO: Created ADO work item #98
_workitems/edit/98
```

The line `_workitems/edit/98` is what step-03b reads to extract `issue_number=98`.

---

## Step 4: Verify the Work Item

After step-03 completes, confirm the work item exists in ADO:

```bash
az boards work-item show --id 98 \
  --query "{id:id, title:fields.\"System.Title\", state:fields.\"System.State\", type:fields.\"System.WorkItemType\"}" \
  -o json
```

Expected output:

```json
{
  "id": 98,
  "title": "Fix the session timeout bug reported in #12345",
  "state": "Active",
  "type": "Task"
}
```

---

## Step 5: Watch the Workflow Continue

Steps 04 through 15 run identically on ADO repos — they operate on the local git clone and do not call any provider-specific API. The workflow:

- Sets up a worktree (step-04)
- Runs investigation agents (steps 05–07)
- Generates a design (step-08)
- Implements changes (steps 09–13)
- Runs tests (step-14)
- Commits and pushes the branch (step-15)

The branch pushed is a normal `git push origin <branch>` call. ADO accepts standard git pushes.

---

## Step 6: Verify the Draft PR

When step-16 runs, you will see:

```
=== Step 16: Creating Draft PR ===
```

followed by the ADO PR URL:

```
https://dev.azure.com/myorg/myproject/_git/myrepo/pullrequest/7
```

Verify it:

```bash
az repos pr show \
  --id 7 \
  --query "{id:pullRequestId, title:title, status:status, isDraft:isDraft}" \
  -o json
```

Expected output:

```json
{
  "id": 7,
  "title": "Fix the session timeout bug reported in #12345",
  "status": "active",
  "isDraft": true
}
```

The PR is in draft status, targeting `main`, and contains the task description and design spec in the description body.

---

## Step 7: Diagnose Common Failure Modes

### Failure Mode 1: ADO defaults not set

**Symptom**: step-03 exits 1 with a message from `az` about missing organization or project.

**Diagnosis**:

```bash
az devops configure --list
# If empty or missing, set them:
az devops configure --defaults \
  organization=https://dev.azure.com/myorg \
  project=myproject
```

### Failure Mode 2: Authentication expired

**Symptom**: step-03 or step-16 exits 1 with a 401/403 error from the Azure REST API.

**Diagnosis**:

```bash
az account show
# If this fails, re-authenticate:
az login
```

For CI/CD environments, use a service principal:

```bash
az login --service-principal \
  -u "$ARM_CLIENT_ID" \
  -p "$ARM_CLIENT_SECRET" \
  --tenant "$ARM_TENANT_ID"
```

---

## Summary

You have seen the complete ADO workflow path:

| Step        | What happened                                                                       |
| ----------- | ----------------------------------------------------------------------------------- |
| Pre-flight  | `az account show` and `az devops configure --list` confirmed                        |
| step-03     | `detect_git_provider()` returned `ado`; `az boards work-item create` created a Task |
| step-03b    | `_workitems/edit/98` parsed to `issue_number=98`                                    |
| steps 04–15 | Normal git/implementation flow, provider-agnostic                                   |
| step-16     | `detect_git_provider()` returned `ado`; `az repos pr create --draft` created the PR |

The workflow is functionally identical on GitHub and ADO. Provider detection is the only branching point.
