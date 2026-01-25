# .NET 10 Hybrid Pack Tool - Reference

Complete reference for building hybrid Native AOT + CoreCLR .NET tool packages.

## Architecture

### Package Structure

When you build with this pattern, you get:

```
packages/
├── your-tool.1.0.0.nupkg           # Pointer package (metapackage)
├── your-tool.any.1.0.0.nupkg       # CoreCLR fallback (works everywhere)
├── your-tool.osx-arm64.1.0.0.nupkg # Native AOT for macOS ARM64
├── your-tool.linux-arm64.1.0.0.nupkg # Native AOT for Linux ARM64
└── your-tool.linux-x64.1.0.0.nupkg   # Native AOT for Linux x64
```

### How It Works

```
User runs: dotnet tool install -g your-tool

.NET CLI:
1. Downloads pointer package (your-tool.1.0.0.nupkg)
2. Reads ToolPackageRuntimeIdentifiers metadata
3. Matches user's RID to available packages:
   - osx-arm64 → downloads your-tool.osx-arm64.nupkg (Native AOT)
   - linux-x64 → downloads your-tool.linux-x64.nupkg (Native AOT)
   - win-x64   → downloads your-tool.any.nupkg (CoreCLR fallback)
4. Installs only the matching package
```

**Key Benefit**: Users only download what they need. No wasted bandwidth on unused platform binaries.

## Complete .csproj Configuration

```xml
<Project Sdk="Microsoft.NET.Sdk">

  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net10.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>

    <!-- Package as .NET Tool -->
    <PackAsTool>true</PackAsTool>
    <ToolCommandName>your-tool-name</ToolCommandName>

    <!-- RIDs: CoreCLR fallback + Native AOT targets -->
    <ToolPackageRuntimeIdentifiers>any;osx-arm64;linux-arm64;linux-x64</ToolPackageRuntimeIdentifiers>

    <!-- Package metadata -->
    <PackageId>your-tool-name</PackageId>
    <VersionPrefix>1.0.0</VersionPrefix>
    <Authors>Your Name</Authors>
    <Description>Your tool description</Description>

    <!-- Enable Native AOT by default -->
    <PublishAot>true</PublishAot>
  </PropertyGroup>

  <!-- SourceLink and reproducible builds (for CI) -->
  <PropertyGroup Condition="'$(OfficialBuild)' == 'true'">
    <DebugType>embedded</DebugType>
    <ContinuousIntegrationBuild>true</ContinuousIntegrationBuild>
    <Deterministic>true</Deterministic>
    <PublishRepositoryUrl>true</PublishRepositoryUrl>
    <PackageLicenseExpression>MIT</PackageLicenseExpression>
    <PackageReadmeFile>README.md</PackageReadmeFile>
  </PropertyGroup>

  <ItemGroup Condition="'$(OfficialBuild)' == 'true'">
    <None Include="README.md" Pack="true" PackagePath="\" />
  </ItemGroup>

  <!-- Native AOT optimizations -->
  <PropertyGroup Condition="'$(PublishAot)' == 'true'">
    <DefineConstants>$(DefineConstants);NATIVE_AOT</DefineConstants>
    <InvariantGlobalization>true</InvariantGlobalization>
    <OptimizationPreference>Size</OptimizationPreference>
    <StripSymbols>true</StripSymbols>
  </PropertyGroup>

</Project>
```

## Complete Build Script

Reference implementation from [richlander/dotnet10-hybrid-tool](https://github.com/richlander/dotnet10-hybrid-tool):

```bash
#!/bin/bash
set -euo pipefail

# Build script for hybrid .NET tool packages
# Creates Native AOT packages for supported platforms + CoreCLR fallback

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGES_DIR="$SCRIPT_DIR/packages"
AOT_IMAGE="mcr.microsoft.com/dotnet/sdk:10.0-noble-aot"

# Get git commit for SourceLink
GIT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "")

# Build args for official builds
PACK_ARGS="-p:OfficialBuild=true"
if [ -n "$GIT_COMMIT" ]; then
    PACK_ARGS="$PACK_ARGS -p:SourceRevisionId=$GIT_COMMIT"
fi

# Clean function that handles root-owned files from docker
clean_build() {
    docker run --rm -v "$SCRIPT_DIR:/src" -w /src $AOT_IMAGE \
        bash -c 'find bin obj -mindepth 1 -delete 2>/dev/null || true; rm -rf bin obj'
}

# Clean previous builds
docker run --rm -v "$SCRIPT_DIR:/src" -w /src $AOT_IMAGE \
    bash -c 'find bin obj packages -mindepth 1 -delete 2>/dev/null || true; rm -rf bin obj packages'
mkdir -p "$PACKAGES_DIR"

echo "=== Step 1: Create pointer package ==="
dotnet pack $PACK_ARGS -o "$PACKAGES_DIR"

echo "=== Step 2: Build osx-arm64 with Native AOT ==="
clean_build
dotnet pack $PACK_ARGS -r osx-arm64 -o "$PACKAGES_DIR"

echo "=== Step 3: Build linux-arm64 with Native AOT (container) ==="
clean_build
docker run --rm \
    -v "$SCRIPT_DIR:/src" \
    -w /src \
    $AOT_IMAGE \
    dotnet pack $PACK_ARGS -r linux-arm64 -o /src/packages

echo "=== Step 4: Build linux-x64 with Native AOT (container + emulation) ==="
clean_build
docker run --rm --platform linux/amd64 \
    -v "$SCRIPT_DIR:/src" \
    -w /src \
    $AOT_IMAGE \
    dotnet pack $PACK_ARGS -r linux-x64 -o /src/packages

echo "=== Step 5: Build any runtime with CoreCLR ==="
clean_build
dotnet pack $PACK_ARGS -r any -p:PublishAot=false -o "$PACKAGES_DIR"

echo "=== Build complete ==="
ls -lh "$PACKAGES_DIR"
```

## Container-Based Builds

### Why Containers?

Native AOT cannot cross-compile across operating systems (only architectures). To build Linux binaries from macOS:

```bash
# Linux ARM64 (native on Apple Silicon via Rosetta-free container)
docker run --rm \
    -v "$(pwd):/src" \
    -w /src \
    mcr.microsoft.com/dotnet/sdk:10.0-noble-aot \
    dotnet pack -r linux-arm64 -o /src/packages

# Linux x64 (via emulation on Apple Silicon)
docker run --rm --platform linux/amd64 \
    -v "$(pwd):/src" \
    -w /src \
    mcr.microsoft.com/dotnet/sdk:10.0-noble-aot \
    dotnet pack -r linux-x64 -o /src/packages
```

### AOT-Compatible Container Image

Use `mcr.microsoft.com/dotnet/sdk:10.0-noble-aot` which includes:

- .NET 10 SDK
- Native AOT toolchain (clang, lld)
- All required build dependencies

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Build Hybrid Tool

on:
  push:
    tags: ["v*"]

jobs:
  build-pointer:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-dotnet@v4
        with:
          dotnet-version: "10.0.x"
      - run: dotnet pack -o ./packages
      - uses: actions/upload-artifact@v4
        with:
          name: pointer-package
          path: ./packages/*.nupkg

  build-linux-x64:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-dotnet@v4
        with:
          dotnet-version: "10.0.x"
      - run: dotnet pack -r linux-x64 -o ./packages
      - uses: actions/upload-artifact@v4
        with:
          name: linux-x64-package
          path: ./packages/*.nupkg

  build-linux-arm64:
    runs-on: ubuntu-24.04-arm
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-dotnet@v4
        with:
          dotnet-version: "10.0.x"
      - run: dotnet pack -r linux-arm64 -o ./packages
      - uses: actions/upload-artifact@v4
        with:
          name: linux-arm64-package
          path: ./packages/*.nupkg

  build-macos-arm64:
    runs-on: macos-14 # M1/M2 runner
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-dotnet@v4
        with:
          dotnet-version: "10.0.x"
      - run: dotnet pack -r osx-arm64 -o ./packages
      - uses: actions/upload-artifact@v4
        with:
          name: osx-arm64-package
          path: ./packages/*.nupkg

  build-coreclr-fallback:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-dotnet@v4
        with:
          dotnet-version: "10.0.x"
      - run: dotnet pack -r any -p:PublishAot=false -o ./packages
      - uses: actions/upload-artifact@v4
        with:
          name: any-package
          path: ./packages/*.nupkg

  publish:
    needs:
      [build-pointer, build-linux-x64, build-linux-arm64, build-macos-arm64, build-coreclr-fallback]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v4
        with:
          pattern: "*-package"
          path: packages
          merge-multiple: true
      - run: dotnet nuget push packages/*.nupkg --source nuget.org --api-key ${{ secrets.NUGET_API_KEY }}
```

## ToolPackageRuntimeIdentifiers vs RuntimeIdentifiers

| Property                        | Behavior                                        | Use Case             |
| ------------------------------- | ----------------------------------------------- | -------------------- |
| `RuntimeIdentifiers`            | Auto-generates RID packages during pack         | CoreCLR-only tools   |
| `ToolPackageRuntimeIdentifiers` | Creates pointer package only; manual RID builds | Hybrid AOT + CoreCLR |

**Why ToolPackageRuntimeIdentifiers for AOT?**

- AOT cannot cross-compile across OSes
- Manual builds give you control over which platforms get AOT
- CoreCLR fallback ensures universal compatibility

## Runtime Detection in Code

Check if running AOT vs CoreCLR:

```csharp
#if NATIVE_AOT
    Console.WriteLine("Mode: Native AOT");
#else
    Console.WriteLine("Mode: CoreCLR");
#endif

// Or at runtime:
var isAot = !System.Runtime.CompilerServices.RuntimeFeature.IsDynamicCodeSupported;
```

## Performance Comparison

From the reference implementation:

```bash
# Native AOT (osx-arm64)
$ time dotnet10-hybrid-tool
Hi, I'm a 'DotNetCliTool v2' tool!
dotnet10-hybrid-tool  0.00s user 0.01s system 60% cpu 0.015 total

# CoreCLR (any)
$ time dotnet10-hybrid-tool
Hi, I'm a 'DotNetCliTool v2' tool!
dotnet10-hybrid-tool  0.15s user 0.05s system 85% cpu 0.235 total
```

**~15x faster startup** with Native AOT.

## Troubleshooting

### "AOT build fails with missing symbols"

Ensure you're using the AOT-compatible SDK image:

```bash
docker pull mcr.microsoft.com/dotnet/sdk:10.0-noble-aot
```

### "Can't build Windows AOT from macOS"

Correct - AOT doesn't cross-compile OSes. Options:

1. Use GitHub Actions with Windows runner
2. Use Azure DevOps Windows agent
3. Windows users build locally
4. Windows falls back to CoreCLR (`any` package)

### "Package too large"

Enable size optimizations:

```xml
<PropertyGroup Condition="'$(PublishAot)' == 'true'">
  <OptimizationPreference>Size</OptimizationPreference>
  <StripSymbols>true</StripSymbols>
  <InvariantGlobalization>true</InvariantGlobalization>
</PropertyGroup>
```

### "Container build permission denied"

Files created by Docker may be root-owned:

```bash
# Clean with Docker to handle permissions
docker run --rm -v "$(pwd):/src" -w /src mcr.microsoft.com/dotnet/sdk:10.0-noble-aot \
    bash -c 'rm -rf bin obj'
```
