# Azure Artifacts Complete Command Reference

Complete reference for `az artifacts` command group covering package feeds, universal packages, and artifact management.

## Feed Management

### List Feeds

```bash
# List all feeds in organization
az artifacts feed list

# List feeds in specific project
az artifacts feed list --project MyProject

# List as table
az artifacts feed list --output table

# Get feed details as JSON
az artifacts feed list --output json > feeds.json
```

### Show Feed

```bash
# Show feed by name
az artifacts feed show --feed myfeed --project MyProject

# Show feed by ID
az artifacts feed show --feed FEED_ID

# Get feed as JSON
az artifacts feed show --feed myfeed --output json
```

### Create Feed

```bash
# Create feed
az artifacts feed create --name "myfeed" --project MyProject

# Create organization-level feed
az artifacts feed create --name "org-feed" --organization https://dev.azure.com/myorg

# Create with description
az artifacts feed create \
  --name "production-feed" \
  --project MyProject \
  --description "Production packages"
```

### Update Feed

```bash
# Update feed description
az artifacts feed update \
  --feed myfeed \
  --description "Updated description"

# Update feed upstream sources
az artifacts feed update \
  --feed myfeed \
  --project MyProject
```

### Delete Feed

```bash
# Delete feed
az artifacts feed delete --feed myfeed --yes

# Delete project feed
az artifacts feed delete --feed myfeed --project MyProject --yes
```

## Feed Permissions

### List Feed Permissions

```bash
# List permissions for feed
az artifacts feed permission list --feed myfeed --project MyProject

# Get specific user permission
az artifacts feed permission show \
  --feed myfeed \
  --user user@example.com \
  --project MyProject
```

### Add Feed Permissions

```bash
# Add user to feed with contributor role
az artifacts feed permission add \
  --feed myfeed \
  --user user@example.com \
  --role contributor \
  --project MyProject

# Add group with reader role
az artifacts feed permission add \
  --feed myfeed \
  --group "Build Service" \
  --role reader \
  --project MyProject

# Role options: reader, contributor, collaborator, administrator
```

### Remove Feed Permissions

```bash
# Remove user from feed
az artifacts feed permission remove \
  --feed myfeed \
  --user user@example.com \
  --yes \
  --project MyProject
```

## Universal Packages

### List Universal Packages

```bash
# List all packages in feed
az artifacts universal list --feed myfeed --project MyProject

# List as table
az artifacts universal list --feed myfeed --output table

# Get package list as JSON
az artifacts universal list --feed myfeed --output json > packages.json
```

### Show Universal Package

```bash
# Show package details
az artifacts universal show \
  --feed myfeed \
  --name mypackage \
  --version 1.0.0 \
  --project MyProject

# Get package as JSON
az artifacts universal show \
  --feed myfeed \
  --name mypackage \
  --version 1.0.0 \
  --output json
```

### Publish Universal Package

```bash
# Publish package from directory
az artifacts universal publish \
  --feed myfeed \
  --name mypackage \
  --version 1.0.0 \
  --path ./dist \
  --project MyProject

# Publish with description
az artifacts universal publish \
  --feed myfeed \
  --name api-package \
  --version 2.1.0 \
  --path ./build/output \
  --description "API build v2.1.0" \
  --project MyProject

# Publish from specific directory
az artifacts universal publish \
  --feed production-feed \
  --name deployment-package \
  --version 1.0.0-rc1 \
  --path /path/to/artifacts \
  --project MyProject
```

### Download Universal Package

```bash
# Download package to directory
az artifacts universal download \
  --feed myfeed \
  --name mypackage \
  --version 1.0.0 \
  --path ./download \
  --project MyProject

# Download to specific location
az artifacts universal download \
  --feed myfeed \
  --name api-package \
  --version 2.1.0 \
  --path /var/lib/packages \
  --project MyProject

# Download latest version
VERSION=$(az artifacts universal list --feed myfeed --project MyProject --query "[?name=='mypackage'] | [0].versions[0].version" -o tsv)
az artifacts universal download \
  --feed myfeed \
  --name mypackage \
  --version "$VERSION" \
  --path ./download \
  --project MyProject
```

## NuGet Packages

### List NuGet Packages

```bash
# List NuGet packages in feed (using REST API)
az devops invoke \
  --area packaging \
  --resource packages \
  --route-parameters feedId=FEED_ID project=MyProject \
  --api-version 6.0-preview.1 \
  --http-method GET

# Query specific package
az devops invoke \
  --area packaging \
  --resource packages \
  --route-parameters feedId=FEED_ID packageId=PACKAGE_ID project=MyProject \
  --api-version 6.0-preview.1 \
  --http-method GET
```

### Publish NuGet Package

```bash
# Configure NuGet source
az artifacts feed show --feed myfeed --project MyProject --query "packageEndpoints.nuGet.publishEndpoint" -o tsv

# Use dotnet CLI to publish
dotnet nuget push package.nupkg \
  --source https://pkgs.dev.azure.com/myorg/MyProject/_packaging/myfeed/nuget/v3/index.json \
  --api-key az
```

## npm Packages

### List npm Packages

```bash
# Get npm feed endpoint
az artifacts feed show --feed myfeed --project MyProject --query "packageEndpoints.npm.publishEndpoint" -o tsv

# Use npm CLI to list packages
npm search --registry=https://pkgs.dev.azure.com/myorg/MyProject/_packaging/myfeed/npm/registry/
```

### Publish npm Package

```bash
# Configure npm registry
NPM_REGISTRY=$(az artifacts feed show --feed myfeed --project MyProject --query "packageEndpoints.npm.publishEndpoint" -o tsv)

# Publish package
npm publish --registry="$NPM_REGISTRY"
```

## Python Packages (PyPI)

### List Python Packages

```bash
# Get Python feed endpoint
az artifacts feed show --feed myfeed --project MyProject --query "packageEndpoints.pypi.publishEndpoint" -o tsv
```

### Publish Python Package

```bash
# Configure twine
pip install twine

# Upload package
twine upload \
  --repository-url https://pkgs.dev.azure.com/myorg/MyProject/_packaging/myfeed/pypi/upload \
  dist/*
```

## Maven Packages

### Publish Maven Package

```bash
# Get Maven feed endpoint
az artifacts feed show --feed myfeed --project MyProject --query "packageEndpoints.maven.publishEndpoint" -o tsv

# Configure settings.xml and use mvn deploy
mvn deploy -DrepositoryId=azure-artifacts -DaltDeploymentRepository=azure-artifacts::default::https://pkgs.dev.azure.com/myorg/MyProject/_packaging/myfeed/maven/v1
```

## Scripting Examples

### Automated Package Publishing

```bash
#!/bin/bash
VERSION="1.0.$(date +%Y%m%d%H%M%S)"
npm run build
az artifacts universal publish --feed myfeed --name myapp --version "$VERSION" --path ./dist --description "Build $VERSION" --project MyProject
```

### Package Promotion Pipeline

```bash
#!/bin/bash
[ -z "$1" ] && echo "Usage: $0 <version>" && exit 1
TEMP=$(mktemp -d)
az artifacts universal download --feed dev-feed --name myapp --version "$1" --path "$TEMP" --project MyProject
az artifacts universal publish --feed prod-feed --name myapp --version "$1" --path "$TEMP" --description "Promoted" --project MyProject
rm -rf "$TEMP"
```

### Feed Audit Report

```bash
#!/bin/bash
# Generate feed usage report

FEED="myfeed"
REPORT_FILE="feed-report-$(date +%Y%m%d).txt"

echo "Feed Audit Report: $FEED" > "$REPORT_FILE"
echo "Generated: $(date)" >> "$REPORT_FILE"
echo "===================================" >> "$REPORT_FILE"

echo -e "\nFeed Details:" >> "$REPORT_FILE"
az artifacts feed show --feed "$FEED" --project MyProject >> "$REPORT_FILE"

echo -e "\nPackages:" >> "$REPORT_FILE"
az artifacts universal list --feed "$FEED" --project MyProject --output table >> "$REPORT_FILE"

echo -e "\nPermissions:" >> "$REPORT_FILE"
az artifacts feed permission list --feed "$FEED" --project MyProject --output table >> "$REPORT_FILE"

echo "Report saved to $REPORT_FILE"
```

### Package Cleanup

```bash
#!/bin/bash
# Delete old package versions (keep latest N versions)

FEED="myfeed"
PACKAGE_NAME="myapp"
KEEP_VERSIONS=5

echo "Cleaning up old versions of $PACKAGE_NAME (keeping latest $KEEP_VERSIONS)..."

# Get all versions (would need REST API for deletion)
az devops invoke \
  --area packaging \
  --resource packages \
  --route-parameters feedId="$FEED" packageName="$PACKAGE_NAME" project=MyProject \
  --api-version 6.0-preview.1 \
  --http-method GET \
  --query "versions[$(($KEEP_VERSIONS)):]" \
  -o json | jq -r '.[].version' | while read version; do
    echo "Would delete version: $version"
    # Deletion requires REST API call
    # az devops invoke --http-method DELETE ...
done
```

### Multi-Feed Package Sync

```bash
#!/bin/bash
# Sync packages between feeds

SOURCE_FEED="dev-feed"
TARGET_FEED="staging-feed"
TEMP_DIR="/tmp/feed-sync"

echo "Syncing packages from $SOURCE_FEED to $TARGET_FEED..."

mkdir -p "$TEMP_DIR"

# List packages in source feed
az artifacts universal list --feed "$SOURCE_FEED" --project MyProject --output json | jq -r '.[] | "\(.name):\(.version)"' | while IFS=: read -r name version; do
  echo "Syncing $name:$version..."

  # Download from source
  az artifacts universal download \
    --feed "$SOURCE_FEED" \
    --name "$name" \
    --version "$version" \
    --path "$TEMP_DIR/$name/$version" \
    --project MyProject

  # Publish to target
  az artifacts universal publish \
    --feed "$TARGET_FEED" \
    --name "$name" \
    --version "$version" \
    --path "$TEMP_DIR/$name/$version" \
    --description "Synced from $SOURCE_FEED" \
    --project MyProject

  # Cleanup
  rm -rf "$TEMP_DIR/$name"
done

echo "Sync complete"
```

### Package Dependency Checker

```bash
#!/bin/bash
# Check if package dependencies exist in feed

FEED="myfeed"
PACKAGE_NAME=$1
VERSION=$2

if [ -z "$PACKAGE_NAME" ] || [ -z "$VERSION" ]; then
  echo "Usage: $0 <package-name> <version>"
  exit 1
fi

echo "Checking dependencies for $PACKAGE_NAME:$VERSION..."

# Download package
TEMP_DIR=$(mktemp -d)
az artifacts universal download \
  --feed "$FEED" \
  --name "$PACKAGE_NAME" \
  --version "$VERSION" \
  --path "$TEMP_DIR" \
  --project MyProject

# Check for dependency file (format varies by package type)
if [ -f "$TEMP_DIR/package.json" ]; then
  echo "Found package.json, checking npm dependencies..."
  jq -r '.dependencies | keys[]' "$TEMP_DIR/package.json" | while read dep; do
    echo "  Dependency: $dep"
  done
fi

# Cleanup
rm -rf "$TEMP_DIR"
```

## Best Practices

- Semantic versioning (major.minor.patch)
- Separate feeds per environment
- Retention policies for cleanup
- Feed views for lifecycle
- Feed permissions for security
- Automate via CI/CD
- Never overwrite versions
- Include descriptions

## Advanced Patterns

### CI/CD Integration

```yaml
# Azure Pipelines YAML example
trigger:
  - main

pool:
  vmImage: "ubuntu-latest"

steps:
  - task: UniversalPackages@0
    displayName: "Publish Universal Package"
    inputs:
      command: "publish"
      publishDirectory: "$(Build.ArtifactStagingDirectory)"
      feedsToUsePublish: "internal"
      vstsFeedPublish: "myfeed"
      vstsFeedPackagePublish: "myapp"
      versionOption: "patch"
```

### Package Metadata Management

```bash
#!/bin/bash
# Add metadata to published packages

FEED="myfeed"
PACKAGE="myapp"
VERSION="1.0.0"

# Get package ID
PACKAGE_ID=$(az devops invoke \
  --area packaging \
  --resource packages \
  --route-parameters feedId="$FEED" packageName="$PACKAGE" project=MyProject \
  --api-version 6.0-preview.1 \
  --http-method GET \
  --query "id" -o tsv)

# Update metadata (requires REST API)
echo "Package ID: $PACKAGE_ID"
```

### Feed Views Configuration

```bash
# List feed views
az devops invoke \
  --area packaging \
  --resource views \
  --route-parameters feedId=FEED_ID project=MyProject \
  --api-version 6.0-preview.1 \
  --http-method GET

# Create view
# Requires REST API with JSON payload
```

## Troubleshooting

**Auth issues**: Verify with `az account show`, check permissions, use PAT with Packaging scope

**Not found**: Verify feed exists, list packages, check spelling/version

**Upload fails**: Check quota, verify path exists, check permissions

**Download fails**: Verify version exists, check path is writable, use full paths

## References

- [Azure Artifacts CLI Reference](https://learn.microsoft.com/en-us/cli/azure/artifacts)
- [Universal Packages Documentation](https://learn.microsoft.com/en-us/azure/devops/artifacts/quickstarts/universal-packages)
- [Package Management Best Practices](https://learn.microsoft.com/en-us/azure/devops/artifacts/concepts/best-practices)
- [Azure Artifacts REST API](https://learn.microsoft.com/en-us/rest/api/azure/devops/artifacts)
