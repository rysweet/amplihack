# .NET Installation Reference

Comprehensive reference for .NET SDK and runtime installation across all supported platforms.

## Contents

- [Windows Installation](#windows-installation)
- [macOS Installation](#macos-installation)
- [Linux Installation](#linux-installation)
- [Version Management](#version-management)
- [Offline Installation](#offline-installation)
- [Docker Installation](#docker-installation)
- [CI/CD Integration](#cicd-integration)
- [Troubleshooting](#troubleshooting)

## Windows Installation

### WinGet (Windows Package Manager)

**Advantages**: Automatic updates, clean uninstall, version management

```powershell
# Search available versions
winget search Microsoft.DotNet.SDK
# Output:
# Name              Id                      Version
# .NET SDK 8.0      Microsoft.DotNet.SDK.8  8.0.100
# .NET SDK 7.0      Microsoft.DotNet.SDK.7  7.0.410

# Install latest .NET 8
winget install Microsoft.DotNet.SDK.8

# Install specific version
winget install Microsoft.DotNet.SDK.8 --version 8.0.100

# Install preview versions
winget install Microsoft.DotNet.SDK.Preview

# Upgrade existing installation
winget upgrade Microsoft.DotNet.SDK.8

# Uninstall
winget uninstall Microsoft.DotNet.SDK.8
```

### Visual Studio Integration

**When to use**: Already using Visual Studio, need integrated development environment

```powershell
# Detected Visual Studio installations:
# - Visual Studio 2022 Community (17.8.0)
#   Location: C:\Program Files\Visual Studio\2022\Community
#   .NET SDKs: 6.0.420, 7.0.410
# - Visual Studio 2022 Professional (17.8.0)
#   Location: C:\Program Files\Visual Studio\2022\Professional
#   .NET SDKs: 8.0.100
```

**Installation steps**:

1. Open Visual Studio Installer
2. Click "Modify" on your installation
3. Under "Workloads", select:
   - ".NET desktop development" (for WPF, WinForms)
   - "ASP.NET and web development" (for web apps)
   - ".NET Multi-platform App UI development" (for MAUI)
4. Under "Individual components", select specific SDK versions
5. Click "Modify" to install

**Verify installation**:

```powershell
# Check Visual Studio's .NET SDKs
Get-ChildItem "C:\Program Files\Microsoft Visual Studio\2022\*\MSBuild\Current\Bin\Roslyn" -Recurse
```

### Standalone Installer

**When to use**: No package manager, controlled installation, offline scenarios

```powershell
# Download from: https://dotnet.microsoft.com/download/dotnet/8.0
# Choose architecture:
# - x64 (64-bit Intel/AMD)
# - x86 (32-bit, legacy)
# - Arm64 (ARM-based Windows devices)

# Interactive installation
.\dotnet-sdk-8.0.100-win-x64.exe

# Silent installation (for scripts)
.\dotnet-sdk-8.0.100-win-x64.exe /install /quiet /norestart /log install.log

# Silent installation with custom location
.\dotnet-sdk-8.0.100-win-x64.exe /install /quiet /norestart /InstallPath="D:\dotnet"

# Verify installation
$env:PATH -split ';' | Select-String dotnet
dotnet --info
```

### PowerShell Install Script

**When to use**: Automation, CI/CD, multiple versions, custom locations

```powershell
# Download script
Invoke-WebRequest -Uri https://dot.net/v1/dotnet-install.ps1 -OutFile dotnet-install.ps1

# Install latest .NET 8 SDK
.\dotnet-install.ps1 -Channel 8.0

# Install specific version
.\dotnet-install.ps1 -Version 8.0.100

# Install to custom directory
.\dotnet-install.ps1 -Channel 8.0 -InstallDir "C:\CustomPath\dotnet"

# Install runtime only (smaller)
.\dotnet-install.ps1 -Channel 8.0 -Runtime dotnet

# Install ASP.NET Core runtime
.\dotnet-install.ps1 -Channel 8.0 -Runtime aspnetcore

# Install without modifying PATH
.\dotnet-install.ps1 -Channel 8.0 -NoPath

# Install preview version
.\dotnet-install.ps1 -Channel 9.0 -Quality preview

# Dry run (show what would be installed)
.\dotnet-install.ps1 -Channel 8.0 -DryRun
```

**Script parameters reference**:

- `-Channel` - Major.Minor version (e.g., 8.0, 7.0)
- `-Version` - Exact version (e.g., 8.0.100)
- `-Quality` - Release quality: GA, preview, daily
- `-Runtime` - Runtime type: dotnet, aspnetcore, windowsdesktop
- `-Architecture` - x64, x86, arm64
- `-InstallDir` - Custom installation path
- `-NoPath` - Don't modify PATH environment variable

## macOS Installation

### Official Installer Package (Recommended)

**Advantages**: Native installation, automatic PATH setup, easy uninstall

```bash
# Detect architecture
uname -m
# Output: arm64 (Apple Silicon) or x86_64 (Intel)

# Download appropriate installer:
# Apple Silicon: dotnet-sdk-8.0.100-osx-arm64.pkg
# Intel: dotnet-sdk-8.0.100-osx-x64.pkg
# From: https://dotnet.microsoft.com/download/dotnet/8.0

# Install via GUI (double-click .pkg) or command line:
sudo installer -pkg dotnet-sdk-8.0.100-osx-arm64.pkg -target /

# Verify installation
dotnet --info
# Look for:
# .NET SDK:
#   Version:   8.0.100
#   Base Path: /usr/local/share/dotnet/sdk/8.0.100/

which dotnet
# Output: /usr/local/share/dotnet/dotnet
```

**Installation location**: `/usr/local/share/dotnet/`

**Uninstall**:

```bash
# Remove .NET installation
sudo rm -rf /usr/local/share/dotnet

# Remove symlinks
sudo rm /usr/local/bin/dotnet
sudo rm -rf /etc/paths.d/dotnet
```

### Homebrew

**Advantages**: Easy updates, integrated with other tools, version management

```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install latest .NET SDK
brew install dotnet

# Install specific version (if available in formulae)
brew install dotnet@8
brew install dotnet@7

# Link specific version
brew link dotnet@8

# Update .NET
brew update
brew upgrade dotnet

# List installed versions
brew list --versions dotnet

# Uninstall
brew uninstall dotnet
```

**Installation location**: `/opt/homebrew/` (Apple Silicon) or `/usr/local/` (Intel)

### Install Script (Bash)

**When to use**: Custom locations, multiple versions, automation

```bash
# Download install script
curl -sSL https://dot.net/v1/dotnet-install.sh -o dotnet-install.sh
chmod +x dotnet-install.sh

# Install latest .NET 8 SDK
./dotnet-install.sh --channel 8.0

# Install specific version
./dotnet-install.sh --version 8.0.100

# Install to custom directory
./dotnet-install.sh --channel 8.0 --install-dir ~/.dotnet

# Install runtime only
./dotnet-install.sh --channel 8.0 --runtime dotnet

# Install ASP.NET Core runtime
./dotnet-install.sh --channel 8.0 --runtime aspnetcore

# Install for all users (requires sudo)
sudo ./dotnet-install.sh --channel 8.0 --install-dir /usr/local/share/dotnet

# Add to PATH (if custom location)
echo 'export PATH="$HOME/.dotnet:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### Manual Binary Installation

**When to use**: Complete control, offline installation, non-standard setups

```bash
# Download tarball
curl -sSL -o dotnet-sdk-8.0.100-osx-arm64.tar.gz \
  https://download.visualstudio.microsoft.com/download/pr/[hash]/dotnet-sdk-8.0.100-osx-arm64.tar.gz

# Create installation directory
mkdir -p $HOME/.dotnet

# Extract archive
tar -xzf dotnet-sdk-8.0.100-osx-arm64.tar.gz -C $HOME/.dotnet

# Add to PATH
echo 'export PATH="$HOME/.dotnet:$PATH"' >> ~/.zshrc
echo 'export DOTNET_ROOT="$HOME/.dotnet"' >> ~/.zshrc
source ~/.zshrc

# Verify
dotnet --version
# Output: 8.0.100
```

## Linux Installation

### Ubuntu/Debian

#### Ubuntu 22.04 LTS (Jammy)

```bash
# Add Microsoft package repository
wget https://packages.microsoft.com/config/ubuntu/22.04/packages-microsoft-prod.deb -O packages-microsoft-prod.deb
sudo dpkg -i packages-microsoft-prod.deb
rm packages-microsoft-prod.deb

# Update package index
sudo apt-get update

# Install .NET 8 SDK
sudo apt-get install -y dotnet-sdk-8.0

# Install specific components
sudo apt-get install -y aspnetcore-runtime-8.0  # ASP.NET Core runtime
sudo apt-get install -y dotnet-runtime-8.0      # .NET runtime only

# List installed packages
apt list --installed | grep dotnet

# Uninstall
sudo apt-get remove dotnet-sdk-8.0
sudo apt-get autoremove
```

#### Ubuntu 20.04 LTS (Focal)

```bash
wget https://packages.microsoft.com/config/ubuntu/20.04/packages-microsoft-prod.deb -O packages-microsoft-prod.deb
sudo dpkg -i packages-microsoft-prod.deb
rm packages-microsoft-prod.deb

sudo apt-get update
sudo apt-get install -y dotnet-sdk-8.0
```

#### Debian 12 (Bookworm)

```bash
wget https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb -O packages-microsoft-prod.deb
sudo dpkg -i packages-microsoft-prod.deb
rm packages-microsoft-prod.deb

sudo apt-get update
sudo apt-get install -y dotnet-sdk-8.0
```

### Fedora/RHEL/CentOS

#### Fedora 39

```bash
# Install .NET SDK (available in Fedora repositories)
sudo dnf install dotnet-sdk-8.0

# Install runtime only
sudo dnf install aspnetcore-runtime-8.0

# List installed versions
dnf list installed | grep dotnet
```

#### RHEL 9

```bash
# Register Microsoft repository
sudo dnf install https://packages.microsoft.com/config/rhel/9/packages-microsoft-prod.rpm

# Install SDK
sudo dnf install dotnet-sdk-8.0

# Enable specific version
sudo dnf install dotnet-sdk-8.0
```

#### CentOS Stream 9

```bash
# Add Microsoft repository
sudo dnf install https://packages.microsoft.com/config/centos/9/packages-microsoft-prod.rpm

# Install SDK
sudo dnf install dotnet-sdk-8.0
```

### Arch Linux

```bash
# Install from official repositories
sudo pacman -S dotnet-sdk

# Install runtime only
sudo pacman -S aspnet-runtime
sudo pacman -S dotnet-runtime

# Install specific version (from AUR if needed)
yay -S dotnet-sdk-8.0

# List installed packages
pacman -Q | grep dotnet
```

### Alpine Linux

```bash
# Alpine uses musl libc, requires special .NET build
# Download install script
wget https://dot.net/v1/dotnet-install.sh
chmod +x dotnet-install.sh

# Install .NET 8
./dotnet-install.sh --channel 8.0 --install-dir /usr/share/dotnet

# Add to PATH
export PATH="$PATH:/usr/share/dotnet"
echo 'export PATH="$PATH:/usr/share/dotnet"' >> ~/.profile

# For system-wide installation
sudo ./dotnet-install.sh --channel 8.0 --install-dir /usr/share/dotnet
sudo ln -s /usr/share/dotnet/dotnet /usr/bin/dotnet
```

### Snap (Cross-Distribution)

```bash
# Install .NET SDK via Snap
sudo snap install dotnet-sdk --classic --channel=8.0

# Snap installation includes automatic updates
# Installed to: /snap/dotnet-sdk/current/

# Link to make globally available
sudo snap alias dotnet-sdk.dotnet dotnet

# Check snap info
snap info dotnet-sdk
```

### Generic Linux Install Script

**For distributions without package manager support**:

```bash
# Download script
curl -sSL https://dot.net/v1/dotnet-install.sh -o dotnet-install.sh
chmod +x dotnet-install.sh

# Install to /usr/local/share/dotnet
sudo ./dotnet-install.sh --channel 8.0 --install-dir /usr/local/share/dotnet

# Create symlink
sudo ln -s /usr/local/share/dotnet/dotnet /usr/local/bin/dotnet

# Verify
dotnet --version
```

## Version Management

### global.json Schema

```json
{
  "sdk": {
    "version": "8.0.100",
    "rollForward": "latestPatch",
    "allowPrerelease": false
  },
  "msbuild-sdks": {
    "Microsoft.Build.NoTargets": "3.7.0"
  }
}
```

### Roll-Forward Policies

| Policy          | Behavior                       | Example (requested 8.0.100)          |
| --------------- | ------------------------------ | ------------------------------------ |
| `patch`         | Same feature band, newer patch | 8.0.101 ✓, 8.0.200 ✗                 |
| `feature`       | Same minor, newer feature band | 8.0.200 ✓, 8.1.100 ✗                 |
| `minor`         | Same major, newer minor        | 8.1.100 ✓, 9.0.100 ✗                 |
| `major`         | Any newer version              | 9.0.100 ✓                            |
| `latestPatch`   | Latest patch in feature band   | Latest 8.0.1xx                       |
| `latestFeature` | Latest feature band in minor   | Latest 8.0.xxx                       |
| `latestMinor`   | Latest minor in major          | Latest 8.x.xxx                       |
| `latestMajor`   | Latest installed version       | Latest x.x.xxx                       |
| `disable`       | Exact match required           | 8.0.100 only, fails if not installed |

### Creating global.json

```bash
# Create with specific SDK version
dotnet new globaljson --sdk-version 8.0.100

# Create with latest installed SDK
dotnet new globaljson

# Create with roll-forward policy
dotnet new globaljson --sdk-version 8.0.100 --roll-forward latestPatch
```

### Managing Multiple SDKs

```bash
# List all installed SDKs
dotnet --list-sdks
# Output:
# 6.0.420 [/usr/local/share/dotnet/sdk]
# 7.0.410 [/usr/local/share/dotnet/sdk]
# 8.0.100 [/usr/local/share/dotnet/sdk]

# List all installed runtimes
dotnet --list-runtimes
# Output:
# Microsoft.AspNetCore.App 6.0.28 [/usr/local/share/dotnet/shared/Microsoft.AspNetCore.App]
# Microsoft.AspNetCore.App 8.0.0 [/usr/local/share/dotnet/shared/Microsoft.AspNetCore.App]
# Microsoft.NETCore.App 6.0.28 [/usr/local/share/dotnet/shared/Microsoft.NETCore.App]
# Microsoft.NETCore.App 8.0.0 [/usr/local/share/dotnet/shared/Microsoft.NETCore.App]

# Use specific SDK for command
DOTNET_ROOT=/path/to/dotnet dotnet build

# Environment variable to force SDK version
export DOTNET_ROLL_FORWARD=disable
export DOTNET_ROOT=/usr/local/share/dotnet
```

### Version Selection Algorithm

1. Check for `global.json` in current directory and walk up directory tree
2. Apply `rollForward` policy from `global.json`
3. If no `global.json`, use latest installed SDK
4. If requested version not found, fail (with `rollForward: disable`) or use policy

```bash
# See which SDK will be used
dotnet --version

# See detailed version selection info
export DOTNET_MULTILEVEL_LOOKUP=0
dotnet --info
```

## Offline Installation

### Windows Offline

```powershell
# Download binaries from: https://dotnet.microsoft.com/download/dotnet/8.0
# Select: Binaries → x64 → .zip

# Extract to installation directory
Expand-Archive -Path dotnet-sdk-8.0.100-win-x64.zip -DestinationPath "C:\Program Files\dotnet"

# Add to system PATH
$currentPath = [Environment]::GetEnvironmentVariable("PATH", "Machine")
$newPath = "C:\Program Files\dotnet;" + $currentPath
[Environment]::SetEnvironmentVariable("PATH", $newPath, "Machine")

# Verify (restart shell first)
dotnet --version
```

### macOS Offline

```bash
# Download tarball
# https://dotnet.microsoft.com/download/dotnet/8.0
# Select: Binaries → macOS → .tar.gz

# Extract to system location
sudo mkdir -p /usr/local/share/dotnet
sudo tar -xzf dotnet-sdk-8.0.100-osx-arm64.tar.gz -C /usr/local/share/dotnet

# Create symlink
sudo ln -s /usr/local/share/dotnet/dotnet /usr/local/bin/dotnet

# Verify
dotnet --version
```

### Linux Offline

```bash
# Download tarball for your architecture
# x64: dotnet-sdk-8.0.100-linux-x64.tar.gz
# ARM64: dotnet-sdk-8.0.100-linux-arm64.tar.gz
# ARM32: dotnet-sdk-8.0.100-linux-arm.tar.gz

# Extract to system location
sudo mkdir -p /usr/local/share/dotnet
sudo tar -xzf dotnet-sdk-8.0.100-linux-x64.tar.gz -C /usr/local/share/dotnet

# Create symlink
sudo ln -s /usr/local/share/dotnet/dotnet /usr/local/bin/dotnet

# Set environment variables
echo 'export DOTNET_ROOT=/usr/local/share/dotnet' >> ~/.bashrc
echo 'export PATH=$PATH:/usr/local/share/dotnet' >> ~/.bashrc
source ~/.bashrc

# Verify
dotnet --version
```

## Docker Installation

### SDK Images

```dockerfile
# Multi-stage build with .NET 8
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /source

# Copy project file and restore dependencies
COPY *.csproj .
RUN dotnet restore

# Copy source code and build
COPY . .
RUN dotnet publish -c Release -o /app

# Runtime image (smaller)
FROM mcr.microsoft.com/dotnet/aspnet:8.0
WORKDIR /app
COPY --from=build /app .

EXPOSE 80
ENTRYPOINT ["dotnet", "MyApp.dll"]
```

### Available Images

```bash
# SDK images (for building)
docker pull mcr.microsoft.com/dotnet/sdk:8.0
docker pull mcr.microsoft.com/dotnet/sdk:8.0-alpine
docker pull mcr.microsoft.com/dotnet/sdk:8.0-jammy  # Ubuntu 22.04

# Runtime images (for running)
docker pull mcr.microsoft.com/dotnet/runtime:8.0
docker pull mcr.microsoft.com/dotnet/aspnet:8.0

# Minimal runtime (for self-contained apps)
docker pull mcr.microsoft.com/dotnet/runtime-deps:8.0
```

### Size Optimization

```dockerfile
# Alpine-based SDK (smaller)
FROM mcr.microsoft.com/dotnet/sdk:8.0-alpine AS build
WORKDIR /app
COPY . .
RUN dotnet publish -c Release -o out \
    -r linux-musl-x64 \
    --self-contained false

# Runtime-deps only (minimal)
FROM mcr.microsoft.com/dotnet/runtime-deps:8.0-alpine
WORKDIR /app
COPY --from=build /app/out .
ENTRYPOINT ["./MyApp"]
```

**Image sizes**:

- `sdk:8.0` - ~900 MB
- `sdk:8.0-alpine` - ~600 MB
- `aspnet:8.0` - ~200 MB
- `aspnet:8.0-alpine` - ~110 MB
- `runtime-deps:8.0-alpine` - ~15 MB

## CI/CD Integration

### GitHub Actions

```yaml
name: .NET Build

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Setup .NET
        uses: actions/setup-dotnet@v4
        with:
          dotnet-version: "8.0.x"

      - name: Restore dependencies
        run: dotnet restore

      - name: Build
        run: dotnet build --no-restore

      - name: Test
        run: dotnet test --no-build --verbosity normal
```

### Multi-version matrix

```yaml
jobs:
  build:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        dotnet-version: ["6.0.x", "7.0.x", "8.0.x"]

    steps:
      - uses: actions/checkout@v4

      - name: Setup .NET ${{ matrix.dotnet-version }}
        uses: actions/setup-dotnet@v4
        with:
          dotnet-version: ${{ matrix.dotnet-version }}

      - run: dotnet build
      - run: dotnet test
```

### Azure Pipelines

```yaml
trigger:
  - main

pool:
  vmImage: "ubuntu-latest"

variables:
  buildConfiguration: "Release"

steps:
  - task: UseDotNet@2
    displayName: "Install .NET SDK"
    inputs:
      packageType: "sdk"
      version: "8.0.x"

  - script: dotnet restore
    displayName: "Restore dependencies"

  - script: dotnet build --configuration $(buildConfiguration)
    displayName: "Build"

  - script: dotnet test --configuration $(buildConfiguration) --no-build
    displayName: "Test"
```

### GitLab CI

```yaml
image: mcr.microsoft.com/dotnet/sdk:8.0

stages:
  - build
  - test

build:
  stage: build
  script:
    - dotnet restore
    - dotnet build --configuration Release
  artifacts:
    paths:
      - bin/Release/

test:
  stage: test
  script:
    - dotnet test --configuration Release
```

## Troubleshooting

### PATH Issues

#### Windows

```powershell
# Check if dotnet is in PATH
$env:PATH -split ';' | Select-String dotnet

# If not found, add manually
$dotnetPath = "C:\Program Files\dotnet"
$currentPath = [Environment]::GetEnvironmentVariable("PATH", "Machine")
if ($currentPath -notlike "*$dotnetPath*") {
    [Environment]::SetEnvironmentVariable("PATH", "$dotnetPath;$currentPath", "Machine")
}

# Verify (restart shell)
dotnet --version
```

#### macOS/Linux

```bash
# Check PATH
echo $PATH | tr ':' '\n' | grep dotnet

# Add to PATH permanently
echo 'export PATH="$PATH:/usr/local/share/dotnet"' >> ~/.bashrc  # or ~/.zshrc
source ~/.bashrc

# Verify
which dotnet
dotnet --version
```

### SDK Not Found

```bash
# Verify installation location
dotnet --info
# Look for "Base Path:" and ".NET SDKs installed:"

# If SDKs listed but not found, check DOTNET_ROOT
export DOTNET_ROOT=/usr/local/share/dotnet
echo 'export DOTNET_ROOT=/usr/local/share/dotnet' >> ~/.bashrc

# Clear NuGet cache if corrupted
dotnet nuget locals all --clear
```

### Version Conflicts

```bash
# Check all installed SDKs
dotnet --list-sdks

# Project requires specific version not installed
cat global.json
# {
#   "sdk": {
#     "version": "7.0.410"  # Not installed
#   }
# }

# Solution 1: Install required version
sudo apt-get install dotnet-sdk-7.0

# Solution 2: Update global.json to use available version
dotnet new globaljson --sdk-version 8.0.100 --force

# Solution 3: Use rollForward policy
# Edit global.json:
{
  "sdk": {
    "version": "7.0.410",
    "rollForward": "latestMinor"  # Will use 8.0.x
  }
}
```

### Permission Denied

```bash
# Linux/macOS: Installation requires sudo
sudo apt-get install dotnet-sdk-8.0  # Linux
sudo installer -pkg dotnet-sdk.pkg -target /  # macOS

# User-level installation (no sudo)
curl -sSL https://dot.net/v1/dotnet-install.sh | bash -s -- --install-dir ~/.dotnet
echo 'export PATH="$HOME/.dotnet:$PATH"' >> ~/.bashrc
```

### Library Dependencies (Linux)

```bash
# Ubuntu/Debian: Install required libraries
sudo apt-get update
sudo apt-get install -y \
    libc6 libgcc1 libgssapi-krb5-2 libicu70 \
    libssl3 libstdc++6 zlib1g libgdiplus

# Fedora/RHEL: Install dependencies
sudo dnf install -y \
    krb5-libs libicu openssl-libs zlib
```

### Package Conflicts (Ubuntu)

```bash
# Remove conflicting packages
sudo apt-get remove 'dotnet*' 'aspnet*' 'netstandard*'
sudo apt-get autoremove

# Clean package cache
sudo apt-get clean

# Re-add Microsoft repository and install
wget https://packages.microsoft.com/config/ubuntu/22.04/packages-microsoft-prod.deb -O packages-microsoft-prod.deb
sudo dpkg -i packages-microsoft-prod.deb
rm packages-microsoft-prod.deb
sudo apt-get update
sudo apt-get install -y dotnet-sdk-8.0
```

### Slow NuGet Restore

```bash
# Clear NuGet caches
dotnet nuget locals all --clear

# Use local package source
dotnet restore --source ~/.nuget/packages

# Disable parallel restore
dotnet restore --disable-parallel

# Enable verbose logging
dotnet restore --verbosity detailed
```

### macOS Gatekeeper Issues

```bash
# If macOS blocks dotnet execution
xattr -r -d com.apple.quarantine /usr/local/share/dotnet

# Allow in System Preferences
# System Preferences → Security & Privacy → General
# Click "Allow Anyway" next to dotnet message
```

### Verification Commands

```bash
# Complete diagnostic output
dotnet --info

# Check SDK versions
dotnet --list-sdks

# Check runtime versions
dotnet --list-runtimes

# Test with new console app
dotnet new console -n test-app
cd test-app
dotnet run
# Output: Hello, World!
```

## Additional Resources

- [.NET Installation Guide](https://learn.microsoft.com/en-us/dotnet/core/install/)
- [Troubleshooting .NET Errors](https://learn.microsoft.com/en-us/dotnet/core/install/troubleshoot)
- [.NET Release Notes](https://github.com/dotnet/core/tree/main/release-notes)
- [Docker Official Images](https://hub.docker.com/_/microsoft-dotnet)
- [global.json Overview](https://learn.microsoft.com/en-us/dotnet/core/tools/global-json)
