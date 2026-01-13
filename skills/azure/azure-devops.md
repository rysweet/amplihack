---
skill:
  name: azure-devops
  description: Azure DevOps - pipelines, repos, boards
---

# Azure DevOps

## Services
- **Repos**: Git repositories
- **Pipelines**: CI/CD automation
- **Boards**: Work item tracking
- **Artifacts**: Package management
- **Test Plans**: Testing management

## Pipeline YAML
```yaml
trigger:
  - main
pool:
  vmImage: ubuntu-latest
steps:
  - script: echo Hello
    displayName: Run script
```
