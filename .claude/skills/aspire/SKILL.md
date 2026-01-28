---
name: aspire
description: Aspire orchestration for cloud-native distributed applications in any language (C#, Python, Node.js, Go). Handles dependency management, local dev with Docker, Azure deployment, service discovery, and observability dashboards. Use when setting up microservices, containerized apps, or polyglot distributed systems.
version: 1.0.0
source_urls:
  - https://learn.microsoft.com/dotnet/aspire/get-started/aspire-overview
  - https://learn.microsoft.com/dotnet/aspire/fundamentals/setup-tooling
  - https://github.com/dotnet/aspire
  - https://learn.microsoft.com/dotnet/aspire/database/postgresql-component
  - https://learn.microsoft.com/dotnet/aspire/caching/stackexchange-redis-component
  - https://learn.microsoft.com/dotnet/aspire/deployment/azure/aca-deployment
  - https://learn.microsoft.com/dotnet/aspire/service-discovery/overview
  - https://learn.microsoft.com/dotnet/aspire/fundamentals/dashboard
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

# Aspire Orchestration

## Overview

Code-first orchestration for polyglot distributed apps. [AppHost](https://learn.microsoft.com/dotnet/aspire/fundamentals/app-host-overview) defines topology, [DCP](https://learn.microsoft.com/dotnet/aspire/fundamentals/networking-overview#aspire-orchestration) orchestrates locally, [azd](https://learn.microsoft.com/azure/developer/azure-developer-cli) deploys to Azure.

**Stack:** PostgreSQL, Redis, MongoDB, RabbitMQ, Kafka + any language (C#, Python, Node.js, Go)
**Local:** `aspire run` → Docker + [Dashboard](https://learn.microsoft.com/dotnet/aspire/fundamentals/dashboard)
**Cloud:** `azd deploy` → Azure Container Apps

## Quick Start

```bash
# Install .NET 8+ and Aspire workload
# See: https://learn.microsoft.com/dotnet/aspire/fundamentals/setup-tooling
dotnet workload update
dotnet workload install aspire

# Create AppHost (orchestrates services in ANY language)
dotnet new aspire-apphost -n MyApp

# Basic AppHost - orchestrate Python, Node.js, .NET services
var builder = DistributedApplication.CreateBuilder(args);
var redis = builder.AddRedis("cache");

// Python service
var pythonApi = builder.AddExecutable("python-api", "python", ".").WithArgs("app.py").WithReference(redis);

// Node.js service
var nodeApi = builder.AddExecutable("node-api", "node", ".").WithArgs("server.js").WithReference(redis);

// .NET service
var dotnetApi = builder.AddProject<Projects.Api>("api").WithReference(redis);

builder.Build().Run();

# Run (orchestrates ALL languages)
aspire run  # Dashboard opens at http://localhost:15888
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

See [Azure deployment guide](https://learn.microsoft.com/dotnet/aspire/deployment/azure/aca-deployment).

```bash
azd init  # Initialize Azure Developer CLI
azd up    # Deploy (generates Bicep → Azure Container Apps)
azd deploy -e production  # Deploy to specific environment
```

**Generates:** Bicep → Container Apps + networking + managed identities

## Navigation Guide

**Read when you need:**
- **reference.md** - Complete API reference, [DCP internals](https://learn.microsoft.com/dotnet/aspire/fundamentals/networking-overview#aspire-orchestration), advanced config
- **examples.md** - Polyglot integration (Python, Node.js, Go), multi-service templates, Azure deployment
- **patterns.md** - Production strategies (HA, multi-region), [security](https://learn.microsoft.com/dotnet/aspire/security/overview), performance, polyglot communication
- **commands.md** - Complete CLI reference (installation, development, deployment, debugging - all platforms)
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
1. Keep AppHost simple (topology only)
2. Use `WithReference()` for service discovery
3. Use Dashboard for debugging

**Polyglot Patterns:**
```csharp
builder.AddProject<Projects.Api>("api");  // .NET service
builder.AddExecutable("python-api", "python", ".").WithArgs("app.py");  // Python
builder.AddExecutable("node-api", "node", ".").WithArgs("server.js");  // Node.js
builder.AddContainer("nginx", "nginx:latest").WithHttpEndpoint(port: 80);  // Any container
builder.AddExecutable("go-svc", "go", ".").WithArgs("run", "main.go");  // Go service
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

**Agent-Skill mapping**:
- architect → reference.md (API design)
- builder → examples.md (implementation)
- reviewer → patterns.md (best practices)
- tester → troubleshooting.md (validation)
- all agents → commands.md (CLI operations)

