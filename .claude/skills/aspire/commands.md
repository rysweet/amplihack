# Aspire Command Reference

Complete command reference for .NET Aspire CLI, Azure Developer CLI (azd), and related tooling.

## Installation Commands

### Aspire Installation

**macOS/Linux:**
```bash
# Install via script
curl -sSL https://aspire.dev/install.sh | bash

# Verify installation
aspire --version

# Update to latest version
aspire upgrade
```

**Windows (PowerShell):**
```powershell
# Install via script
irm https://aspire.dev/install.ps1 | iex

# Verify installation
aspire --version

# Update to latest version
aspire upgrade
```

**Alternative (via .NET SDK):**
```bash
# Install as .NET global tool (all platforms)
dotnet tool install -g Microsoft.DotNet.Aspire

# Update global tool
dotnet tool update -g Microsoft.DotNet.Aspire
```

### Azure Developer CLI (azd)

**macOS/Linux:**
```bash
# Install via homebrew (macOS)
brew tap azure/azd && brew install azd

# Or via script (macOS/Linux)
curl -fsSL https://aka.ms/install-azd.sh | bash

# Verify installation
azd version
```

**Windows (PowerShell):**
```powershell
# Install via PowerShell
powershell -ex AllSigned -c "Invoke-RestMethod 'https://aka.ms/install-azd.ps1' | Invoke-Expression"

# Or via winget
winget install microsoft.azd

# Verify installation
azd version
```

### Prerequisites

**.NET SDK (Required):**
```bash
# Install .NET 9 SDK
# Windows: Download from https://dot.net
# macOS: brew install dotnet-sdk
# Linux: See https://learn.microsoft.com/dotnet/core/install/linux

# Verify installation
dotnet --version  # Should be 9.0.0 or higher
```

**Docker Desktop (Required for local development):**
```bash
# Verify Docker is running
docker --version
docker ps  # Should not error
```

## Project Creation Commands

### Create AppHost

```bash
# Create AppHost project (orchestrates all services)
dotnet new aspire-apphost -n MyApp

# Options:
dotnet new aspire-apphost -n MyApp --output ./src/MyApp.AppHost
```

### Create Service Projects

```bash
# Create .NET API project
dotnet new webapi -n MyApp.Api

# Create .NET Web project (Blazor)
dotnet new blazor -n MyApp.Web

# Create .NET Worker project (background service)
dotnet new worker -n MyApp.Worker

# Add ServiceDefaults (shared config)
dotnet new aspire-servicedefaults -n MyApp.ServiceDefaults
```

### Link Projects

```bash
# Add project references to AppHost
cd MyApp.AppHost
dotnet add reference ../MyApp.Api/MyApp.Api.csproj
dotnet add reference ../MyApp.Web/MyApp.Web.csproj

# Add ServiceDefaults reference to services
cd ../MyApp.Api
dotnet add reference ../MyApp.ServiceDefaults/MyApp.ServiceDefaults.csproj
```

### Complete Project Setup

```bash
# One-liner: Create full Aspire solution
dotnet new aspire -n MyApp --use-redis-cache

# Creates:
# - MyApp.AppHost (orchestration)
# - MyApp.ServiceDefaults (shared config)
# - MyApp.Api (sample API)
# - MyApp.Web (sample Blazor app)
# - Solution file linking everything
```

## Local Development Commands

### Running Services

**Basic Run:**
```bash
# Start all services defined in AppHost
cd MyApp.AppHost
aspire run

# Or using dotnet
dotnet run

# Dashboard opens automatically at http://localhost:15888
```

**Run with Options:**
```bash
# Run without opening browser
aspire run --no-launch-profile

# Run with specific launch profile
dotnet run --launch-profile https

# Run with environment variables
ASPNETCORE_ENVIRONMENT=Staging aspire run

# Run with custom dashboard port
aspire run --dashboard-port 18888
```

### Stopping Services

```bash
# Stop all services (Ctrl+C in terminal)
# Or:
aspire stop

# Force stop all containers
docker stop $(docker ps -q --filter "label=aspire")

# Clean up volumes (removes all data)
aspire down --volumes
```

### Service Management

**View Running Services:**
```bash
# List all Aspire resources
aspire ps

# View Docker containers
docker ps --filter "label=aspire"

# View resource status
aspire status
```

**Restart Services:**
```bash
# Restart specific service (via Dashboard)
# Or restart all:
aspire restart

# Restart specific container
docker restart <container-name>
```

## Debugging Commands

### Logs

**View Logs via Dashboard:**
```bash
# Dashboard logs tab shows all services
# Access at http://localhost:15888/logs
```

**View Logs via CLI:**
```bash
# Follow logs for specific service
aspire logs api --follow

# View last 100 lines
aspire logs api --tail 100

# View logs for all services
aspire logs --all

# Docker logs (alternative)
docker logs -f <container-name>
```

### Distributed Tracing

**Access Traces:**
```bash
# Dashboard traces tab
# Access at http://localhost:15888/traces

# Export traces (OpenTelemetry format)
aspire traces export --output ./traces.json
```

### Metrics

**View Metrics:**
```bash
# Dashboard metrics tab
# Access at http://localhost:15888/metrics

# Prometheus endpoint
curl http://localhost:15888/metrics/prometheus
```

### Dashboard Commands

```bash
# Open Dashboard in browser
aspire dashboard

# Dashboard with custom port
aspire dashboard --port 18888

# Dashboard with authentication
aspire dashboard --auth basic --username admin --password secret
```

## Configuration Commands

### User Secrets

```bash
# Initialize user secrets for AppHost
cd MyApp.AppHost
dotnet user-secrets init

# Set secret
dotnet user-secrets set "ApiKeys:External" "secret-key-12345"

# List secrets
dotnet user-secrets list

# Remove secret
dotnet user-secrets remove "ApiKeys:External"

# Clear all secrets
dotnet user-secrets clear
```

### Environment Configuration

```bash
# Set environment for run
export ASPNETCORE_ENVIRONMENT=Staging
aspire run

# Windows PowerShell:
$env:ASPNETCORE_ENVIRONMENT="Staging"
aspire run
```

## Azure Deployment Commands

### Initialize Azure Deployment

```bash
# Initialize azd for Azure deployment
cd MyApp.AppHost
azd init

# Interactive prompts:
# - Environment name (e.g., "production")
# - Azure subscription
# - Azure region
```

### Login to Azure

```bash
# Login to Azure
azd auth login

# Login with specific tenant
azd auth login --tenant-id <tenant-id>

# Verify login status
azd auth status
```

### Deploy to Azure

**Full Deployment:**
```bash
# Deploy everything (infrastructure + code)
azd up

# This runs:
# 1. azd provision (creates Azure resources)
# 2. azd deploy (deploys code)
```

**Incremental Deployment:**
```bash
# Deploy code only (no infrastructure changes)
azd deploy

# Deploy specific service
azd deploy api

# Provision infrastructure only (no code deployment)
azd provision
```

**Environment-Specific Deployment:**
```bash
# Deploy to specific environment
azd deploy -e production

# Create new environment
azd env new staging
azd env select staging
azd up
```

### Monitor Deployment

```bash
# View deployment logs
azd deploy --output json

# Show deployed resources
azd show

# Get service endpoint URLs
azd endpoints
```

### Tear Down Azure Resources

```bash
# Delete all Azure resources
azd down

# Delete without confirmation prompt
azd down --force --purge

# List resources before deleting
azd show
```

## Testing Commands

### Run Tests

```bash
# Run all tests
dotnet test

# Run tests with coverage
dotnet test /p:CollectCoverage=true

# Run specific test project
dotnet test MyApp.Api.Tests/MyApp.Api.Tests.csproj
```

### Integration Tests

```bash
# Run integration tests against local Aspire
aspire run &
dotnet test --filter Category=Integration
```

## Build Commands

### Build Projects

```bash
# Build all projects
dotnet build

# Build specific project
dotnet build MyApp.Api/MyApp.Api.csproj

# Build for release
dotnet build -c Release
```

### Publish Projects

```bash
# Publish for deployment
dotnet publish -c Release

# Publish to folder
dotnet publish -c Release -o ./publish

# Publish for Linux container
dotnet publish -c Release -r linux-x64
```

## NuGet Package Management

### Add Aspire Components

```bash
# Add Redis component
dotnet add package Aspire.Hosting.Redis

# Add PostgreSQL component
dotnet add package Aspire.Hosting.PostgreSQL

# Add Azure Key Vault integration
dotnet add package Aspire.Azure.KeyVault

# Search for Aspire packages
dotnet search Aspire.Hosting
```

### Update Packages

```bash
# Update all Aspire packages to latest
dotnet list package --outdated
dotnet add package Aspire.Hosting --version 9.0.0

# Update all packages
dotnet restore --force
```

## Diagnostics Commands

### Health Checks

```bash
# Check service health via Dashboard
# Access at http://localhost:15888/health

# Or via curl
curl http://localhost:5000/health
curl http://localhost:5000/health/ready
```

### Troubleshooting

```bash
# View DCP logs (orchestrator)
aspire logs dcp

# View all container logs
docker logs $(docker ps -q --filter "label=aspire")

# Check for port conflicts
netstat -an | grep 15888  # Dashboard port
netstat -an | grep 6379   # Redis
netstat -an | grep 5432   # PostgreSQL
```

### Clean Up

```bash
# Remove all Aspire containers
docker rm -f $(docker ps -aq --filter "label=aspire")

# Remove all Aspire volumes
docker volume rm $(docker volume ls -q --filter "label=aspire")

# Clean Docker system
docker system prune -a --volumes
```

## Advanced Commands

### Custom Dashboard Configuration

```bash
# Run Dashboard with custom OTLP endpoint
aspire dashboard --otlp-endpoint http://localhost:4317

# Dashboard with resource limits
aspire dashboard --max-logs 100000 --max-traces 50000
```

### Export Configuration

```bash
# Export AppHost manifest (for debugging)
aspire manifest --output ./manifest.json

# Generate Docker Compose (for testing)
aspire export docker-compose --output ./docker-compose.yml
```

### Offline Development

```bash
# Pull all required Docker images
docker pull redis:7.2-alpine
docker pull postgres:15
docker pull rabbitmq:3-management

# Run without internet (uses cached images)
aspire run --offline
```

## Quick Reference Table

| Task | Command | Notes |
|------|---------|-------|
| **Setup** |
| Install Aspire | `curl -sSL https://aspire.dev/install.sh \| bash` | macOS/Linux |
| Install Aspire | `irm https://aspire.dev/install.ps1 \| iex` | Windows |
| Install azd | `brew install azd` | macOS |
| Install azd | `winget install microsoft.azd` | Windows |
| **Development** |
| Create project | `dotnet new aspire -n MyApp` | Full template |
| Run locally | `aspire run` | Opens Dashboard |
| View logs | `aspire logs api --follow` | Follow logs |
| Stop services | `aspire stop` | Stop all |
| **Deployment** |
| Initialize Azure | `azd init` | One-time setup |
| Login to Azure | `azd auth login` | Required once |
| Deploy everything | `azd up` | Infrastructure + code |
| Deploy code only | `azd deploy` | Faster updates |
| Tear down | `azd down` | Delete resources |
| **Debugging** |
| Dashboard | `http://localhost:15888` | All observability |
| Health check | `curl localhost:5000/health` | Service health |
| View traces | Dashboard → Traces tab | Distributed tracing |
| View metrics | Dashboard → Metrics tab | Performance data |
| **Cleanup** |
| Remove containers | `docker rm -f $(docker ps -aq)` | All containers |
| Remove volumes | `aspire down --volumes` | Includes data |
| Clean system | `docker system prune -a` | Full cleanup |

## Common Command Combinations

**Fresh Start:**
```bash
aspire down --volumes
docker system prune -f
aspire run
```

**Deploy to Azure Production:**
```bash
azd auth login
azd env select production
azd deploy
azd endpoints  # Get URLs
```

**Debug Failing Service:**
```bash
aspire logs api --tail 100
docker logs <container-id>
curl http://localhost:5000/health
```

**Update and Redeploy:**
```bash
# Local:
aspire restart

# Azure:
azd deploy -e production
```

## Platform-Specific Notes

### Windows-Specific

```powershell
# Use PowerShell for scripts
$env:ASPNETCORE_ENVIRONMENT="Production"

# Docker Desktop must be running
# Check: Get-Process "Docker Desktop"
```

### macOS-Specific

```bash
# Use Homebrew for installation
brew install azd dotnet-sdk

# Docker Desktop must be running
# Check: docker ps
```

### Linux-Specific

```bash
# Install .NET SDK first
# See: https://learn.microsoft.com/dotnet/core/install/linux

# Use script installation for Aspire
curl -sSL https://aspire.dev/install.sh | bash

# Add to PATH if needed
export PATH="$PATH:$HOME/.aspire/bin"
```

## Error Resolution Commands

**Port Already in Use:**
```bash
# Find process using port
lsof -i :15888  # macOS/Linux
netstat -ano | findstr :15888  # Windows

# Kill process
kill -9 <PID>  # macOS/Linux
taskkill /PID <PID> /F  # Windows
```

**Docker Not Running:**
```bash
# Start Docker Desktop manually
# Or check service:
sudo systemctl start docker  # Linux
```

**Cache Issues:**
```bash
# Clear NuGet cache
dotnet nuget locals all --clear

# Clear Docker build cache
docker builder prune -a
```

Use this reference for all Aspire CLI operations and deployment workflows.
