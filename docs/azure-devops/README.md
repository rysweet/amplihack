# Azure DevOps Integration

Complete Azure DevOps automation tools for boards, repositories, pipelines, and artifacts.

## What It Does

Provides CLI tools and AI guidance for:

- **Work Items (Boards)** - Create, update, query, and manage work items
- **Repositories** - List repos and create pull requests
- **Pipelines** - Trigger builds and monitor execution (via az CLI)
- **Artifacts** - Manage package feeds and versions (via az CLI)

## For AI Agents

See `~/.amplihack/.claude/skills/azure-devops/SKILL.md` for complete skill definition with progressive loading references.

## For Humans

### Quick Setup

1. **Install Azure CLI**

   ```bash
   # macOS
   brew install azure-cli

   # Windows
   winget install Microsoft.AzureCLI

   # Linux
   curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
   ```

2. **Install DevOps Extension**

   ```bash
   az extension add --name azure-devops
   ```

3. **Login and Configure**

   ```bash
   az login
   az devops configure --defaults \
     organization=https://dev.azure.com/YOUR_ORG \
     project=YOUR_PROJECT
   ```

4. **Verify Setup**
   ```bash
   python .claude/scenarios/az-devops-tools/auth_check.py --auto-fix
   ```

### Available Tools

All tools are in `~/.amplihack/.claude/scenarios/az-devops-tools/`. Run any tool with `--help` for usage.

#### Work Item Tools

- `list_work_items.py` - Query and filter work items
- `get_work_item.py` - Get single work item details
- `create_work_item.py` - Create new work items
- `update_work_item.py` - Update work item fields/state
- `delete_work_item.py` - Delete work items (with confirmation)
- `link_parent.py` - Link parent-child relationships
- `query_wiql.py` - Execute custom WIQL queries
- `list_types.py` - Discover work item types and fields

#### Utility Tools

- `auth_check.py` - Verify authentication and configuration
- `format_html.py` - Convert markdown to HTML

#### Repository Tools

- `list_repos.py` - List repositories in project
- `create_pr.py` - Create pull requests

### Quick Examples

#### Create Work Item

```bash
python .claude/scenarios/az-devops-tools/create_work_item.py \
  --type "User Story" \
  --title "Implement login" \
  --description "Add user authentication"
```

#### List My Work Items

```bash
python .claude/scenarios/az-devops-tools/list_work_items.py --query mine
```

#### Create Pull Request

```bash
python .claude/scenarios/az-devops-tools/create_pr.py \
  --source feature/auth \
  --target main \
  --title "Add authentication"
```

## Philosophy

These tools follow clean architecture principles:

- **Standard library + Azure CLI** - Minimal dependencies
- **Self-contained** - Each tool is independent and regeneratable
- **Clear error messages** - Actionable guidance when things fail
- **Fail-fast validation** - Check prerequisites before operations

## Common Workflows

### 1. Create Epic → Feature → Story Hierarchy

```bash
# Create Epic
python .claude/scenarios/az-devops-tools/create_work_item.py \
  --type Epic \
  --title "Authentication System"

# Output shows: Created work item #100

# Create Feature under Epic
python .claude/scenarios/az-devops-tools/create_work_item.py \
  --type Feature \
  --title "OAuth Integration" \
  --parent-id 100

# Output shows: Created work item #101
```

### 2. Query and Update Workflow

```bash
# Find my active work items
python .claude/scenarios/az-devops-tools/list_work_items.py \
  --state Active \
  --assigned-to @me

# Update work item
python .claude/scenarios/az-devops-tools/update_work_item.py \
  --id 101 \
  --state "In Progress" \
  --comment "Starting work"
```

### 3. Feature Branch to Pull Request

```bash
# Create feature branch
git checkout -b feature/oauth main

# ... make changes, commit ...

# Push branch
git push -u origin feature/oauth

# Create PR
python .claude/scenarios/az-devops-tools/create_pr.py \
  --source feature/oauth \
  --target main \
  --title "Add OAuth integration" \
  --work-items "101"
```

## Troubleshooting

### "az: command not found"

Install Azure CLI. See Quick Setup above.

### "DevOps extension not installed"

```bash
az extension add --name azure-devops
```

### "Authentication failed"

```bash
az logout
az login
python .claude/scenarios/az-devops-tools/auth_check.py --auto-fix
```

### "Invalid work item type"

```bash
python .claude/scenarios/az-devops-tools/list_types.py
```

## Documentation

For detailed AI-facing documentation, see:

- `~/.amplihack/.claude/skills/azure-devops/authentication.md` - Auth setup
- `~/.amplihack/.claude/skills/azure-devops/work-items.md` - Work item operations
- `~/.amplihack/.claude/skills/azure-devops/queries.md` - WIQL query patterns
- `~/.amplihack/.claude/skills/azure-devops/html-formatting.md` - HTML formatting
- `~/.amplihack/.claude/skills/azure-devops/repos.md` - Repository operations
- `~/.amplihack/.claude/skills/azure-devops/pipelines.md` - Pipeline operations
- `~/.amplihack/.claude/skills/azure-devops/artifacts.md` - Artifact management

## References

- [Azure DevOps CLI Docs](https://learn.microsoft.com/en-us/cli/azure/devops)
- [Work Items API](https://learn.microsoft.com/en-us/rest/api/azure/devops/wit/work-items)
- [WIQL Syntax](https://learn.microsoft.com/en-us/azure/devops/boards/queries/wiql-syntax)
