# .NET / NuGet Supply Chain — Dimension 7

## Lock Files and Restore Integrity

**Critical**: `dotnet restore` in CI without `--locked-mode` — allows silent package substitution.
**High**: `packages.lock.json` missing from one or more projects.
**High**: `<RestoreLockedMode>true</RestoreLockedMode>` absent from `Directory.Build.props`.
**Medium**: `packages.lock.json` exists but is not committed (present in `.gitignore`).

Fix: Add to `Directory.Build.props`:

```xml
<PropertyGroup>
  <RestoreLockedMode>true</RestoreLockedMode>
</PropertyGroup>
```

And add `--locked-mode` to CI restore commands.

## Package Source Verification

Scan `nuget.config` for:
**High**: sources other than `https://api.nuget.org/v3/index.json` without `<clear/>` before them.
Without `<clear/>`, nuget.org remains an active fallback — enabling dependency confusion attacks.
**Medium**: `<packageSourceMapping>` absent (no restriction on which packages come from which feed).
**Info**: private feed present but using HTTP (not HTTPS).

Compliant `nuget.config` pattern:

```xml
<packageSources>
  <clear />
  <add key="nuget.org" value="https://api.nuget.org/v3/index.json" />
  <add key="myFeed" value="https://pkgs.dev.azure.com/org/_packaging/feed/nuget/v3/index.json" />
</packageSources>
<packageSourceMapping>
  <packageSource key="nuget.org">
    <package pattern="*" />
  </packageSource>
  <packageSource key="myFeed">
    <package pattern="MyOrg.*" />
  </packageSource>
</packageSourceMapping>
```

## Vulnerability Scanning

**Medium**: `<NuGetAudit>true</NuGetAudit>` absent from `Directory.Build.props` (.NET 8+).
**Info**: `<NuGetAuditLevel>` set to `high` or `critical` (misses low/moderate vulns).

Add to `Directory.Build.props`:

```xml
<PropertyGroup>
  <NuGetAudit>true</NuGetAudit>
  <NuGetAuditLevel>low</NuGetAuditLevel>
  <NuGetAuditMode>all</NuGetAuditMode>
</PropertyGroup>
```
