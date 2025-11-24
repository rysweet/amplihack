# Azure DevOps CLI Skill

## Purpose

Expert guidance for Azure DevOps CLI (`az devops`) covering automation, pipelines, repositories, boards, and artifacts management. This skill enables Claude Code to provide comprehensive assistance with Azure DevOps workflows and command-line operations.

## Module Contract

### Public Interface (The "Studs")

This skill provides:

1. **Quick Start**: Installation, authentication, and configuration patterns
2. **Essential Commands**: High-value commands across 5 primary groups (DevOps, Pipelines, Boards, Repos, Artifacts)
3. **Common Workflows**: 10+ practical automation patterns for daily DevOps tasks
4. **Troubleshooting**: Solutions for authentication, configuration, and query issues
5. **Advanced Patterns**: REST API access, JMESPath queries, scripting utilities

### Auto-Activation Keywords

The skill automatically activates when conversation mentions:

- azure devops, az devops, ado cli
- pipelines, azure pipelines, yaml pipeline, build pipeline, release pipeline
- boards, azure boards, work items
- repos, azure repos, pull requests, git repos
- artifacts, azure artifacts, artifacts feed

### Explicit Invocation

```
Skill(skill="azure-devops-cli")
```

## Architecture

Progressive disclosure design with core skill (<2000 tokens) and extended reference files:

```
azure-devops-cli/
├── skill.md              # Core: Quick start + 5 commands/group + 10 workflows
├── examples/             # Extended: Complete command references
│   ├── pipelines-reference.md
│   ├── boards-reference.md
│   ├── repos-reference.md
│   └── artifacts-reference.md
└── tests/                # Validation scenarios
```

**Philosophy**: Self-contained module following ruthless simplicity. Every command works, no stubs/TODOs. Regeneratable from Azure DevOps CLI docs

## Dependencies

### Required

- Azure CLI (az): Core command-line tool
- Azure DevOps Extension: `az extension add --name azure-devops`

### Authentication

One of the following:

- Azure account with `az login`
- Personal Access Token (PAT) with `az devops login`

### Configuration

Recommended defaults:

```bash
az devops configure --defaults organization=URL project=NAME
```

## Usage Examples

### Auto-Activation

```
User: "How do I list all Azure DevOps pipelines?"
→ Skill auto-activates on "Azure DevOps pipelines"
→ Provides `az pipelines list` command with examples
```

### Explicit Invocation

```
User: "Show me Azure Artifacts workflows"
Agent: Skill(skill="azure-devops-cli")
→ Loads complete skill context
→ Provides artifacts commands and workflows
```

### Progressive Disclosure

```
User: "I need comprehensive pipeline command reference"
→ Agent reads examples/pipelines-reference.md
→ Provides complete command set with advanced examples
```

## Command Coverage

### DevOps (Organization & Projects)

- Project management: list, create, show, delete
- User and team management
- Organization configuration

### Pipelines (Build & Release)

- Pipeline operations: list, run, create
- Run management: show, list, monitor
- YAML pipeline automation

### Boards (Work Items & Sprints)

- Work item CRUD operations
- WIQL queries for filtering
- Sprint and iteration management

### Repos (Git Repositories)

- Repository management: list, create
- Pull request workflows: create, review, merge
- Git integration and aliases

### Artifacts (Package Management)

- Feed management: list, create
- Package operations: publish, download
- Universal package support

## Common Workflows Covered

1. CI/CD Pipeline Automation
2. Pull Request Review Automation
3. Work Item Batch Creation
4. Pipeline Status Dashboard
5. Repository Clone Automation
6. Sprint Planning Helper
7. Release Gate Checking
8. Artifact Versioning
9. Team Dashboard Data
10. Environment Sync

## Success Criteria

- ✅ Auto-activates on keywords
- ✅ Core <2000 tokens
- ✅ All commands tested
- ✅ 10+ workflows
- ✅ All 5 command groups
- ✅ Philosophy compliant

## Maintenance

**Update triggers**: Azure CLI updates, new command groups, auth changes, user feedback

**Regeneration**: Review official docs → identify high-value commands → update workflows → test → version bump

**Version**: 1.0.0 (2025-11-24) - Initial release with 5 command groups, 10+ workflows

## Testing

See `tests/test-scenarios.md` for:

- Auto-activation test cases
- Command accuracy validation
- Workflow testing examples
- Error handling verification

## References

- [Azure DevOps CLI Documentation](https://learn.microsoft.com/en-us/cli/azure/devops)
- [WIQL Syntax Reference](https://learn.microsoft.com/en-us/azure/devops/boards/queries/wiql-syntax)
- [Azure DevOps REST API](https://learn.microsoft.com/en-us/rest/api/azure/devops)
- [Azure CLI Extensions](https://learn.microsoft.com/en-us/cli/azure/azure-cli-extensions-overview)

## Contributing

Maintain 80/20 in core, add details to examples/, test all commands, follow amplihack philosophy

---

**Brick Philosophy**: Self-contained, regeneratable module with clear interface
