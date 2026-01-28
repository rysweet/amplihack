---
name: aspire
description: .NET Aspire orchestration for cloud-native distributed applications. Handles dependency management, local dev with Docker, Azure deployment, service discovery, and observability dashboards. Use when setting up microservices, containerized apps, or distributed systems with .NET.
version: 1.0.0
last_updated: 2025-01-28
source_urls:
  - https://aspire.dev
  - https://learn.microsoft.com/en-us/dotnet/aspire
activation_keywords:
  - aspire
  - distributed app
  - microservices
  - service discovery
  - apphost
  - cloud-native
  - orchestration
auto_activate: true
token_budget: 1800
---

# .NET Aspire Orchestration

## Overview

.NET Aspire orchestrates distributed cloud-native apps, eliminating manual wiring of containers, databases, and microservices.

**Key Components:**
- **AppHost**: Code-first resource topology definition
- **DCP**: Kubernetes-compatible orchestration engine
- **Dashboard**: OpenTelemetry observability UI

**Workflow:**
```
Local:  dotnet new aspire → aspire run → Docker + Dashboard
Cloud:  Same AppHost → azd deploy → Azure Container Apps
```

**Supports:** PostgreSQL, Redis, SQL Server, MongoDB, RabbitMQ, Kafka. Polyglot: C#, Python, Node.js, Go.

## Quick Start

```bash
# Install
curl -sSL https://aspire.dev/install.sh | bash  # macOS/Linux
irm https://aspire.dev/install.ps1 | iex         # Windows

# Create project
dotnet new aspire-apphost -n MyApp

# Basic AppHost (MyApp.AppHost/Program.cs)
var builder = DistributedApplication.CreateBuilder(args);
var redis = builder.AddRedis("cache");
var api = builder.AddProject<Projects.Api>("api").WithReference(redis);
builder.Build().Run();

# Run
aspire run  # Opens Dashboard at http://localhost:15888
```

## Core Workflows

### Project Setup

```bash
dotnet new aspire-apphost -n MyApp
dotnet new webapi -n MyApp.Api
dotnet add MyApp.AppHost reference MyApp.Api
```

**AppHost**: Resource topology in `Program.cs`
**ServiceDefaults**: Shared config (logging, telemetry, resilience)
**Services**: Your apps (APIs, workers, web apps)

### Dependency Configuration

```csharp
// PostgreSQL
var postgres = builder.AddPostgres("db").AddDatabase("mydb");
var api = builder.AddProject<Projects.Api>("api").WithReference(postgres);

// Redis
var redis = builder.AddRedis("cache").WithRedisCommander();
var api = builder.AddProject<Projects.Api>("api").WithReference(redis);

// RabbitMQ
var rabbitmq = builder.AddRabbitMQ("messaging");
var worker = builder.AddProject<Projects.Worker>("worker").WithReference(rabbitmq);

// Access in code (connection strings auto-injected)
builder.Services.AddStackExchangeRedisCache(options =>
{
    options.Configuration = builder.Configuration.GetConnectionString("cache");
});
```

### Local Development

```bash
aspire run  # Starts all services
```

**Dashboard** (localhost:15888): Resources, logs, traces, metrics
**Hot Reload**: Auto-rebuild on code changes
**Debugging**: Attach to individual services via IDE

### Cloud Deployment

```bash
azd init  # Initialize
azd up    # Deploy (generates Bicep → Azure Container Apps)
azd deploy -e production  # Deploy to specific environment
```

**Process**: AppHost → Bicep generation → Container Apps + networking + managed identities

**Environment-specific config:**
```csharp
if (builder.Environment.IsProduction())
{
    postgres.WithReplicas(3);
    redis.WithPersistence();
}
```

## Navigation Guide

**Read when you need:**
- **reference.md** - Complete API reference, DCP internals, advanced config (health checks, volumes, ports)
- **examples.md** - Working code for integrations, multi-service templates, Azure deployment
- **patterns.md** - Production strategies (HA, multi-region), security (Key Vault, managed identities), performance
- **troubleshooting.md** - Debug orchestration, dependency conflicts, deployment failures

## Quick Reference

**Common Patterns:**
```csharp
// Multiple databases
var pg = builder.AddPostgres("pg").AddDatabase("authdb").AddDatabase("catalogdb");
var authApi = builder.AddProject<Projects.AuthApi>("auth")
    .WithReference(pg.GetDatabase("authdb"));

// Ports
var api = builder.AddProject<Projects.Api>("api").WithHttpEndpoint(port: 8080);

// External services
var external = builder.AddConnectionString("external-api");

// Environment variables
var api = builder.AddProject<Projects.Api>("api")
    .WithEnvironment("LOG_LEVEL", "Debug");
```

**Essential Commands:**
```bash
aspire run          # Start local development
azd up              # Full Azure deployment
azd deploy          # Deploy updates
azd down            # Tear down resources
```

**Best Practices:**
1. Keep AppHost simple (topology only, no business logic)
2. Use `WithReference()` over hardcoded connection strings
3. Use `builder.Environment` for env-specific config
4. Use Dashboard for debugging (no separate logging)

**More AppHost patterns:**
```csharp
builder.AddProject<Projects.Api>("api");  // Simple service
builder.AddProject<Projects.Api>("api").WithReference(redis).WithReference(postgres);  // With deps
builder.AddContainer("nginx", "nginx:latest").WithHttpEndpoint(port: 80);  // Container
builder.AddExecutable("python-app", "python", ".").WithArgs("app.py");  // Executable
```

**Service discovery** (automatic):
```csharp
.WithReference(redis)  // AppHost
var conn = builder.Configuration.GetConnectionString("cache");  // Service reads auto
```

## Integration with Amplihack

**Command**: `/ultrathink "Setup Aspire for microservices"`
- prompt-writer clarifies requirements → architect uses reference.md for API design
- builder uses examples.md for implementation → reviewer checks patterns.md for best practices
- tester uses troubleshooting.md for validation

**Agent-Skill mapping**: architect→reference.md, builder→examples.md, reviewer→patterns.md, tester→troubleshooting.md
