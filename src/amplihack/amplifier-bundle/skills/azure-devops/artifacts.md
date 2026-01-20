# Artifacts and Package Management Guide

Guide for working with Azure Artifacts - package feeds for NuGet, npm, Python, Maven, and Universal packages.

## Overview

Azure Artifacts provides package management integrated with Azure DevOps:

- **Feeds** - Package repositories
- **Packages** - NuGet, npm, Python, Maven, Universal
- **Upstream sources** - Proxy public registries
- **Retention policies** - Automatic cleanup

## Common Commands

### List Feeds

```bash
az artifacts feed list --output table
```

### Create Feed

```bash
az artifacts feed create --name my-feed --description "Team packages"
```

### Show Feed Details

```bash
az artifacts feed show --feed my-feed
```

### List Packages in Feed

```bash
az artifacts package list --feed my-feed --output table
```

### Download Package

```bash
az artifacts universal download \
  --feed my-feed \
  --name my-package \
  --version 1.0.0 \
  --path ./download
```

## Package Types

### NuGet (.NET)

#### Publish NuGet Package

```bash
# Add feed as source
nuget sources add \
  -Name AzureDevOps \
  -Source https://pkgs.dev.azure.com/ORG/_packaging/FEED/nuget/v3/index.json

# Push package
nuget push MyPackage.1.0.0.nupkg \
  -Source AzureDevOps \
  -ApiKey az
```

#### Consume NuGet Package

Add to project file:

```xml
<PackageReference Include="MyPackage" Version="1.0.0" />
```

### npm (JavaScript)

#### Publish npm Package

```bash
# Set registry
npm config set registry https://pkgs.dev.azure.com/ORG/_packaging/FEED/npm/registry/

# Authenticate
npm login --registry=https://pkgs.dev.azure.com/ORG/_packaging/FEED/npm/registry/

# Publish
npm publish
```

#### Consume npm Package

Add to .npmrc:

```
registry=https://pkgs.dev.azure.com/ORG/_packaging/FEED/npm/registry/
always-auth=true
```

### Python (PyPI)

#### Publish Python Package

```bash
# Install twine
pip install twine

# Upload to feed
twine upload --repository-url https://pkgs.dev.azure.com/ORG/_packaging/FEED/pypi/upload dist/*
```

#### Consume Python Package

Configure pip:

```bash
pip install --index-url https://pkgs.dev.azure.com/ORG/_packaging/FEED/pypi/simple/ my-package
```

### Universal Packages

#### Publish Universal Package

```bash
az artifacts universal publish \
  --feed my-feed \
  --name my-package \
  --version 1.0.0 \
  --description "My package" \
  --path ./package-contents
```

#### Download Universal Package

```bash
az artifacts universal download \
  --feed my-feed \
  --name my-package \
  --version 1.0.0 \
  --path ./download
```

## Feed Permissions

Common permission levels:

- **Reader** - Download packages
- **Contributor** - Download and publish packages
- **Owner** - Full control including feed settings

### Grant Feed Permissions

```bash
az artifacts feed permission add \
  --feed my-feed \
  --user user@domain.com \
  --role contributor
```

## Upstream Sources

### Configure Upstream

Upstream sources proxy public registries:

```bash
az artifacts feed upstream add \
  --feed my-feed \
  --name nuget-org \
  --protocol nuget \
  --upstream-source-type public
```

Benefits:

- Cached packages for faster downloads
- Protection against upstream deletions
- Single source for all dependencies

## Retention Policies

### Configure Retention

```bash
az artifacts feed retention set \
  --feed my-feed \
  --count-limit 100 \
  --days-to-keep-recently-downloaded 30
```

Keeps:

- Last 100 versions
- Packages downloaded in last 30 days

## Common Workflows

### Publish from Pipeline

In azure-pipelines.yml:

```yaml
- task: UniversalPackages@0
  displayName: "Publish package"
  inputs:
    command: publish
    publishDirectory: "$(Build.ArtifactStagingDirectory)"
    feedsToUsePublish: "internal"
    vstsFeedPublish: "my-feed"
    vstsFeedPackagePublish: "my-package"
    versionOption: "patch"
```

### Consume in Pipeline

```yaml
- task: UniversalPackages@0
  displayName: "Download package"
  inputs:
    command: download
    downloadDirectory: "$(Build.SourcesDirectory)"
    feedsToUse: "internal"
    vstsFeed: "my-feed"
    vstsFeedPackage: "my-package"
    vstsPackageVersion: "1.0.0"
```

### Version Promotion

Promote package to release view:

```bash
az artifacts package promote \
  --feed my-feed \
  --package my-package \
  --version 1.0.0 \
  --view Release
```

## Views

Feeds can have views for different quality levels:

- **Local** - All versions
- **Prerelease** - Preview versions
- **Release** - Production-ready versions

### List Views

```bash
az artifacts feed view list --feed my-feed
```

### Create View

```bash
az artifacts feed view create \
  --feed my-feed \
  --name Staging \
  --description "Staging packages"
```

## Best Practices

1. **Use upstream sources** - Cache public packages
2. **Set retention policies** - Manage storage costs
3. **Use views** - Separate prerelease from production
4. **Version semantically** - Follow SemVer (major.minor.patch)
5. **Automate publishing** - Use pipelines

## Tips

1. **Authentication** - Use PAT tokens with Packaging (Read/Write) scope
2. **Multiple feeds** - Separate by team or project
3. **Feed URLs** - Different per package type (npm, NuGet, PyPI)
4. **Permissions** - Start restrictive, grant as needed
5. **Monitoring** - Review package usage and storage

## Troubleshooting

### "Feed not found"

List available feeds:

```bash
az artifacts feed list
```

### "Authentication failed"

Generate PAT token with Packaging scope:

1. Personal Access Tokens in Azure DevOps
2. Create token with Packaging (Read/Write)
3. Use as password in package manager

### "Version already exists"

Cannot overwrite published versions. Increment version number.

## See Also

- [Azure Artifacts Docs](https://learn.microsoft.com/en-us/azure/devops/artifacts/)
- [Package Types](https://learn.microsoft.com/en-us/azure/devops/artifacts/concepts/feeds)
- [Upstream Sources](https://learn.microsoft.com/en-us/azure/devops/artifacts/concepts/upstream-sources)
