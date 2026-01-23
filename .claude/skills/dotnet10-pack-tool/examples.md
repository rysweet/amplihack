# .NET 10 Hybrid Pack Tool - Examples

Real-world examples and usage patterns for building hybrid .NET tools.

## Example 1: Simple CLI Tool

### Project Setup

```bash
dotnet new console -n my-hybrid-tool
cd my-hybrid-tool
```

### Program.cs

```csharp
using System.Runtime.InteropServices;

Console.WriteLine("Hello from my-hybrid-tool!");
Console.WriteLine($"Runtime: {RuntimeInformation.FrameworkDescription}");
Console.WriteLine($"RID: {RuntimeInformation.RuntimeIdentifier}");

#if NATIVE_AOT
Console.WriteLine("Mode: Native AOT 🚀");
#else
Console.WriteLine("Mode: CoreCLR");
#endif
```

### my-hybrid-tool.csproj

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net10.0</TargetFramework>
    <PackAsTool>true</PackAsTool>
    <ToolCommandName>my-hybrid-tool</ToolCommandName>
    <ToolPackageRuntimeIdentifiers>any;osx-arm64;linux-x64</ToolPackageRuntimeIdentifiers>
    <PublishAot>true</PublishAot>
    <PackageId>my-hybrid-tool</PackageId>
    <Version>1.0.0</Version>
  </PropertyGroup>

  <PropertyGroup Condition="'$(PublishAot)' == 'true'">
    <DefineConstants>$(DefineConstants);NATIVE_AOT</DefineConstants>
    <InvariantGlobalization>true</InvariantGlobalization>
    <OptimizationPreference>Size</OptimizationPreference>
    <StripSymbols>true</StripSymbols>
  </PropertyGroup>
</Project>
```

### Build

```bash
# Pointer package
dotnet pack -o ./packages

# macOS ARM64 (if on Mac)
dotnet pack -r osx-arm64 -o ./packages

# Linux x64 (via container)
docker run --rm -v "$(pwd):/src" -w /src \
    mcr.microsoft.com/dotnet/sdk:10.0-noble-aot \
    dotnet pack -r linux-x64 -o /src/packages

# CoreCLR fallback
dotnet pack -r any -p:PublishAot=false -o ./packages
```

### Install & Test

```bash
# Install from local packages
dotnet tool install -g my-hybrid-tool --add-source ./packages

# Run
my-hybrid-tool
```

---

## Example 2: Using `dnx` (Quick Test)

The .NET 10 SDK includes `dnx` for running tools without installation:

```bash
# Run directly from NuGet
dnx dotnet10-hybrid-tool

# Output (on macOS ARM64):
# Hi, I'm a 'DotNetCliTool v2' tool!
# Yes, I'm quite fancy.
#
# Version: .NET 10.0.2
# RID: osx-arm64
# Mode: Native AOT
```

---

## Example 3: Minimal Build Script

For simple projects without CI/CD:

```bash
#!/bin/bash
set -e

PACKAGES_DIR="./packages"
rm -rf "$PACKAGES_DIR" bin obj
mkdir -p "$PACKAGES_DIR"

# Build all packages
dotnet pack -o "$PACKAGES_DIR"                           # Pointer
dotnet pack -r osx-arm64 -o "$PACKAGES_DIR"              # macOS
dotnet pack -r any -p:PublishAot=false -o "$PACKAGES_DIR" # Fallback

echo "Packages built:"
ls -la "$PACKAGES_DIR"
```

---

## Example 4: Adding Windows Support

To add Windows Native AOT (requires Windows machine or CI):

### Update .csproj

```xml
<ToolPackageRuntimeIdentifiers>any;osx-arm64;linux-x64;win-x64</ToolPackageRuntimeIdentifiers>
```

### Build on Windows

```powershell
# On Windows machine or GitHub Actions windows-latest
dotnet pack -r win-x64 -o ./packages
```

### Or Let Windows Use Fallback

If you don't need Windows AOT performance, the `any` package works:

```xml
<!-- Windows users get CoreCLR automatically -->
<ToolPackageRuntimeIdentifiers>any;osx-arm64;linux-x64</ToolPackageRuntimeIdentifiers>
```

---

## Example 5: Testing Local Packages

```bash
# Create a local NuGet source
mkdir -p ~/.nuget/local-packages
cp packages/*.nupkg ~/.nuget/local-packages/

# Add local source
dotnet nuget add source ~/.nuget/local-packages --name local-packages

# Install from local
dotnet tool install -g my-hybrid-tool --version 1.0.0

# Or use dnx for quick test
dnx my-hybrid-tool --add-source ./packages
```

---

## Example 6: Version Bumping

```bash
# Update version in .csproj
<VersionPrefix>1.1.0</VersionPrefix>

# Rebuild all packages
./build-packages.sh

# Upgrade installed tool
dotnet tool update -g my-hybrid-tool
```

---

## Example 7: Conditional AOT Features

Some features aren't AOT-compatible. Use conditional compilation:

```csharp
public class MyTool
{
    public void Run()
    {
#if NATIVE_AOT
        // AOT-safe implementation
        RunOptimized();
#else
        // Full CoreCLR features (reflection, dynamic code, etc.)
        RunWithReflection();
#endif
    }

    private void RunOptimized()
    {
        // Source-generated serialization, no reflection
        Console.WriteLine("Running optimized path");
    }

    private void RunWithReflection()
    {
        // Can use reflection, Activator.CreateInstance, etc.
        Console.WriteLine("Running with full CLR features");
    }
}
```

---

## Common Mistakes

### ❌ Wrong: Using RuntimeIdentifiers

```xml
<!-- This auto-generates ALL RID packages with CoreCLR -->
<RuntimeIdentifiers>osx-arm64;linux-x64;win-x64</RuntimeIdentifiers>
```

### ✅ Correct: Using ToolPackageRuntimeIdentifiers

```xml
<!-- This creates pointer package only, manual RID builds for AOT -->
<ToolPackageRuntimeIdentifiers>any;osx-arm64;linux-x64</ToolPackageRuntimeIdentifiers>
```

### ❌ Wrong: Forgetting -p:PublishAot=false for `any`

```bash
# This tries to build AOT for "any" which fails
dotnet pack -r any -o ./packages
```

### ✅ Correct: Disable AOT for fallback

```bash
dotnet pack -r any -p:PublishAot=false -o ./packages
```

### ❌ Wrong: Cross-OS AOT compilation

```bash
# Can't build Windows AOT from macOS
dotnet pack -r win-x64 -o ./packages  # Fails!
```

### ✅ Correct: Use containers for cross-arch, native machines for cross-OS

```bash
# On macOS: build macOS + Linux via containers
dotnet pack -r osx-arm64 -o ./packages
docker run ... dotnet pack -r linux-x64 -o /src/packages

# Windows: build on Windows machine/runner
# Or: let Windows use CoreCLR fallback (any)
```

---

## Troubleshooting

### "Tool not found after install"

```bash
# Check installation path
dotnet tool list -g

# Ensure ~/.dotnet/tools is in PATH
export PATH="$HOME/.dotnet/tools:$PATH"
```

### "Wrong package installed"

```bash
# Verify which package was installed
dotnet tool list -g | grep my-tool

# Reinstall to get latest
dotnet tool uninstall -g my-tool
dotnet tool install -g my-tool
```

### "Build fails with trimming warnings"

Add to .csproj:

```xml
<PropertyGroup>
  <SuppressTrimAnalysisWarnings>true</SuppressTrimAnalysisWarnings>
  <!-- Or fix the warnings properly -->
</PropertyGroup>
```

### "Container can't access packages directory"

```bash
# Use absolute paths
docker run --rm -v "$(pwd):/src" -w /src \
    mcr.microsoft.com/dotnet/sdk:10.0-noble-aot \
    dotnet pack -r linux-x64 -o /src/packages
```
