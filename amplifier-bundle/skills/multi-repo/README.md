# Multi-Repository Orchestration Skill

Coordinate atomic changes across multiple repositories when features span repo boundaries.

## Quick Start

1. **Initialize the dependency graph:**

   ```
   "Initialize multi-repo dependencies for this project"
   ```

2. **Add a dependency:**

   ```
   "Add dependency: my-org/web-client depends on my-org/api-server"
   ```

3. **Check for breaking changes:**

   ```
   "Check if my current changes break any dependent repositories"
   ```

4. **Create linked PRs:**
   ```
   "Create linked PRs for this feature across api-server and web-client"
   ```

## Directory Structure

```
.claude/
  skills/multi-repo/
    SKILL.md     # Skill definition
    README.md    # This file
  data/multi-repo/
    dependencies.yaml   # Repository dependency graph
    linked-prs.yaml     # Active linked PR sets
```

## Dependency Graph Example

```yaml
# .claude/data/multi-repo/dependencies.yaml
version: "1.0"
repositories:
  my-org/api-server:
    depends_on: []
    exposes:
      - type: api
        name: REST API v2
        contract: openapi.yaml

  my-org/web-client:
    depends_on:
      - repo: my-org/api-server
        type: api
        version: ">=2.0"
    exposes: []
```

## Common Use Cases

### Detecting Breaking Changes

Before modifying a public interface:

```
"I'm about to change the User schema in api-server.
What repos will be affected?"
```

The skill will:

1. Identify dependents from the graph
2. Check if they use the changed interface
3. Report impact and recommendations

### Coordinated Feature Release

For features spanning multiple repos:

```
"Implement feature X across api-server, web-client, and docs"
```

The skill will:

1. Create feature branches in each repo
2. Create PRs with cross-references
3. Track them as a linked set
4. Guide merge order based on dependencies

### Merge Coordination

When ready to merge a linked set:

```
"Merge the oauth2-implementation linked PRs"
```

The skill will:

1. Verify all PRs are approved
2. Merge in dependency order (upstream first)
3. Wait for CI between merges
4. Report completion status

## Integration

### With Worktree Manager

Uses worktree-manager for local multi-repo operations:

- Creates worktrees for each local repo
- Manages parallel development
- Cleans up after completion

### With PM Architect

For project management integration:

- Linked PRs map to workstream items
- Breaking changes feed into roadmap
- Cross-repo work tracked in backlog

## Limitations

- Dependency graph is workspace-local (not centralized)
- Requires `gh` CLI authentication for PR operations
- Breaking change detection is heuristic-based
- Circular dependencies not supported

## Philosophy

- **Ruthless Simplicity**: YAML files, no database
- **Zero-BS**: All operations work today
- **Modular**: Self-contained, optional PM integration
