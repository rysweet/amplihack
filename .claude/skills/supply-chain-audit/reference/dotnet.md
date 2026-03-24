# Dimension 7: .NET / NuGet Supply Chain

## Overview

.NET projects face supply chain risks from unlocked package restores, unauthorized
NuGet sources, and missing vulnerability audit gates.

---

## Check 1: NuGet Lock File (RestoreLockedMode)

### Detection

```bash
# Check if lock files exist
find . -name "packages.lock.json" | wc -l

# Check if RestoreLockedMode is enabled
grep -r "RestoreLockedMode" **/*.csproj **/*.props 2>/dev/null
```

### Pattern

```xml
<!-- VIOLATION — no lock mode, package versions can drift -->
<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <PackageReference Include="Newtonsoft.Json" Version="13.0.3" />
  </ItemGroup>
</Project>

<!-- CORRECT — with lock mode in Directory.Build.props -->
<Project>
  <PropertyGroup>
    <RestoreLockedMode Condition="'$(CI)' == 'true'">true</RestoreLockedMode>
    <RestorePackagesWithLockFile>true</RestorePackagesWithLockFile>
  </PropertyGroup>
</Project>
```

Generate lock files locally:

```bash
dotnet restore --use-lock-file
# Commit the resulting packages.lock.json
git add **/packages.lock.json
```

### Severity

| Finding                                                | Severity |
| ------------------------------------------------------ | -------- |
| `packages.lock.json` missing entirely                  | High     |
| `RestoreLockedMode` not set for CI builds              | Medium   |
| Lock file present but not committed to version control | High     |

---

## Check 2: NuGet Source Authorization

### Detection

```bash
# Check NuGet.Config for package sources
find . -name "NuGet.Config" | xargs grep -l "<packageSources>" 2>/dev/null
```

### Pattern

```xml
<!-- VIOLATION — public source without clear-text disable -->
<configuration>
  <packageSources>
    <add key="nuget.org" value="https://api.nuget.org/v3/index.json" />
    <add key="internal" value="https://pkgs.dev.azure.com/myorg/_packaging/feed/nuget/v3/index.json" />
  </packageSources>
</configuration>

<!-- CONCERN — dependency confusion risk if internal package names overlap with nuget.org -->
<!-- CORRECT — explicit source mapping (NuGet 6.0+) prevents dependency confusion -->
<configuration>
  <packageSources>
    <clear />  <!-- disable all default sources -->
    <add key="internal" value="https://pkgs.dev.azure.com/myorg/_packaging/feed/nuget/v3/index.json" />
    <add key="nuget.org" value="https://api.nuget.org/v3/index.json" />
  </packageSources>
  <packageSourceMapping>
    <packageSource key="internal">
      <package pattern="MyOrg.*" />  <!-- only internal packages from internal source -->
    </packageSource>
    <packageSource key="nuget.org">
      <package pattern="*" />  <!-- everything else from nuget.org -->
    </packageSource>
  </packageSourceMapping>
</configuration>
```

### Dependency Confusion Risk

If both internal and public sources are listed without `packageSourceMapping`, NuGet
may resolve an internal package name from the public source if an attacker publishes
a higher-versioned package with that name.

### Severity

| Finding                                                             | Severity |
| ------------------------------------------------------------------- | -------- |
| Internal source + public source without `packageSourceMapping`      | High     |
| No `<clear />` before `packageSources` list                         | Medium   |
| Unrecognized custom source (not nuget.org or internal Azure DevOps) | High     |

---

## Check 3: NuGetAudit Vulnerability Gate

NuGet 6.8+ (included in .NET 8 SDK) has built-in vulnerability auditing.

### Detection

```bash
# Check SDK version
dotnet --version

# Run audit manually
dotnet list package --vulnerable --include-transitive
```

### CI Integration

```yaml
- name: Audit NuGet packages
  run: dotnet list package --vulnerable --include-transitive 2>&1 | tee nuget-audit.txt

- name: Fail on high/critical vulnerabilities
  run: |
    if grep -q "High\|Critical" nuget-audit.txt; then
      echo "::error::High or Critical NuGet vulnerabilities found"
      exit 1
    fi
```

### Directory.Build.props Audit Configuration

```xml
<!-- Fail build on high/critical vulnerabilities (NuGet 6.8+) -->
<Project>
  <PropertyGroup>
    <NuGetAudit>true</NuGetAudit>
    <NuGetAuditMode>all</NuGetAuditMode>          <!-- include transitive deps -->
    <NuGetAuditLevel>high</NuGetAuditLevel>        <!-- fail on High and Critical -->
    <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
  </PropertyGroup>
</Project>
```

### Severity

| Finding                                      | Severity                |
| -------------------------------------------- | ----------------------- |
| .NET 8+ project without `NuGetAudit` enabled | Medium                  |
| Known High/Critical CVE in direct dependency | High/Critical (per CVE) |
| No CI step auditing for vulnerabilities      | Medium                  |

---

## Check 4: Central Package Management

For multi-project solutions, `Directory.Packages.props` centralizes version control:

```xml
<!-- Directory.Packages.props — single source of truth for versions -->
<Project>
  <PropertyGroup>
    <ManagePackageVersionsCentrally>true</ManagePackageVersionsCentrally>
  </PropertyGroup>
  <ItemGroup>
    <PackageVersion Include="Newtonsoft.Json" Version="13.0.3" />
    <PackageVersion Include="Microsoft.Extensions.Logging" Version="8.0.0" />
  </ItemGroup>
</Project>
```

Individual projects then omit versions:

```xml
<PackageReference Include="Newtonsoft.Json" />  <!-- version from Directory.Packages.props -->
```

Flag as **Medium** if solution has 3+ projects without central package management.

---

## Verification Checklist (.NET / NuGet)

- [ ] `packages.lock.json` exists and is committed for each project
- [ ] `RestoreLockedMode=true` in CI environment
- [ ] `NuGet.Config` has `<packageSourceMapping>` if internal sources are present
- [ ] `NuGetAudit=true` with `NuGetAuditLevel=high` in Directory.Build.props
- [ ] CI pipeline has a step that fails on High/Critical NuGet advisories
- [ ] No `<clear />` missing when mixing public and private sources
