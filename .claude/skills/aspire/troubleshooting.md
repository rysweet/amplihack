# Aspire Troubleshooting Guide

Common issues, debugging strategies, and solutions for .NET Aspire development.

**See also:** [GitHub Issues](https://github.com/dotnet/aspire/issues) for known problems and community solutions.

## Orchestration Issues

### Services Not Starting

**Symptom:** Dashboard shows service in "Starting" state indefinitely.

**Diagnosis:**
```bash
aspire run --verbose
# View service logs: Dashboard → Resources → [service-name] → Logs
```

**Common Causes:**

1. **Port Conflict**
   ```
   Error: Failed to bind to address http://localhost:5000: address already in use
   ```
   **Solution:** Use dynamic port allocation
   ```csharp
   builder.AddProject<Projects.Api>("api").WithHttpEndpoint();
   ```

2. **Missing Dependencies**
   ```
   Error: Unable to connect to database
   ```
   **Solution:** Use WithReference to ensure dependencies start first
   ```csharp
   var redis = builder.AddRedis("cache");
   var postgres = builder.AddPostgres("db").AddDatabase("appdb");
   var api = builder.AddProject<Projects.Api>("api")
       .WithReference(redis)
       .WithReference(postgres);
   ```

3. **Health Check Timeout**
   ```
   Warning: Health check timeout after 30s
   ```
   **Solution:** Increase timeout or fix slow startup
   ```csharp
   builder.AddProject<Projects.Api>("api")
       .WithHealthCheckTimeout(TimeSpan.FromSeconds(60));
   ```

### Services Fail Health Checks

**Symptom:** Service starts but marked unhealthy in Dashboard.

**Diagnosis:**
```bash
curl http://localhost:5000/health
# Dashboard → Resources → [service] → Health tab
```

**Solutions:**

1. **Add Health Endpoint**
   ```csharp
   builder.Services.AddHealthChecks()
       .AddDbContextCheck<AppDbContext>()
       .AddRedis(builder.Configuration.GetConnectionString("cache")!);
   app.MapHealthChecks("/health");
   ```

2. **Fix Database Connection**
   ```csharp
   builder.Services.AddHealthChecks()
       .AddNpgSql(builder.Configuration.GetConnectionString("db")!,
           timeout: TimeSpan.FromSeconds(5),
           failureStatus: HealthStatus.Unhealthy);
   ```

3. **Check Dependency Health**
   ```csharp
   builder.Services.AddHealthChecks()
       .AddRedis(builder.Configuration.GetConnectionString("cache")!, name: "redis-check");
   ```

### Startup Order Issues

**Symptom:** Service starts before dependencies are ready.

**Example Error:**
```
System.TimeoutException: Unable to connect to Redis
```

**Solution:** Use `WithReference` to establish dependencies
```csharp
var redis = builder.AddRedis("cache");
var api = builder.AddProject<Projects.Api>("api").WithReference(redis);
```

**If still failing:** Add retry logic
```csharp
builder.Services.AddStackExchangeRedisCache(options =>
{
    options.Configuration = builder.Configuration.GetConnectionString("cache");
})
.AddResilience(policy => policy
    .AddRetry(new RetryStrategyOptions
    {
        MaxRetryAttempts = 5,
        Delay = TimeSpan.FromSeconds(2)
    }));
```

## Dependency Conflicts

### NuGet Package Version Mismatches

**Symptom:**
```
Error: Package 'Aspire.Hosting.Redis' 8.0.0 is not compatible with 'Aspire.Hosting' 8.1.0
```

**Solution:** Ensure all Aspire packages use same version
```bash
# Check versions
dotnet list package

# Update all Aspire packages
dotnet add package Aspire.Hosting --version 8.1.0
dotnet add package Aspire.Hosting.Redis --version 8.1.0
dotnet add package Aspire.Hosting.PostgreSQL --version 8.1.0
```

**Or use Directory.Packages.props:**
```xml
<Project>
  <PropertyGroup>
    <ManagePackageVersionsCentrally>true</ManagePackageVersionsCentrally>
    <AspireVersion>8.1.0</AspireVersion>
  </PropertyGroup>

  <ItemGroup>
    <PackageVersion Include="Aspire.Hosting" Version="$(AspireVersion)" />
    <PackageVersion Include="Aspire.Hosting.Redis" Version="$(AspireVersion)" />
    <PackageVersion Include="Aspire.Hosting.PostgreSQL" Version="$(AspireVersion)" />
  </ItemGroup>
</Project>
```

### Docker Image Pull Failures

**Symptom:**
```
Error: Unable to pull image 'redis:latest': no such host
```

**Diagnosis:**
```bash
# Test Docker connectivity
docker pull redis:latest

# Check Docker daemon status
docker info
```

**Solutions:**

1. **Docker Not Running:** `open -a Docker` (macOS), `sudo systemctl start docker` (Linux), Start Docker Desktop (Windows)

2. **Network Issues:** Test connectivity with `ping docker.io`, configure proxy if needed

3. **Use Specific Image Version:**
   ```csharp
   builder.AddRedis("cache").WithImageTag("7.2-alpine");
   ```

### Missing Database Drivers

**Symptom:**
```
Error: No database provider has been configured for this DbContext
```

**Solution:** Add appropriate NuGet package
```bash
# PostgreSQL
dotnet add package Npgsql.EntityFrameworkCore.PostgreSQL

# SQL Server
dotnet add package Microsoft.EntityFrameworkCore.SqlServer

# MongoDB
dotnet add package MongoDB.Driver
```

**And configure:**
```csharp
builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseNpgsql(builder.Configuration.GetConnectionString("db")));
```

## Deployment Failures

### Azure Deployment - Authentication Errors

**Symptom:**
```
Error: Failed to authenticate with Azure. Run 'azd auth login'
```

**Solution:**
```bash
# Login to Azure
az login
azd auth login

# Verify authentication
az account show
azd env list
```

### Azure Deployment - Insufficient Permissions

**Symptom:**
```
Error: The client does not have authorization to perform action 'Microsoft.Resources/deployments/write'
```

**Solution:** Grant required permissions
```bash
# Check current role
az role assignment list --assignee $(az account show --query user.name -o tsv)

# Assign Contributor role (requires admin)
az role assignment create \
  --assignee user@example.com \
  --role Contributor \
  --scope /subscriptions/{subscription-id}
```

**Minimum Required Roles:** Contributor (resource creation), User Access Administrator (managed identities)

### Azure Deployment - Resource Quota Exceeded

**Symptom:**
```
Error: Operation could not be completed as it results in exceeding quota limit
```

**Diagnosis:**
```bash
# Check current quota usage
az vm list-usage --location eastus -o table
az network vnet list --query "length([*])"
```

**Solutions:**

1. **Request Quota Increase:** Azure Portal → Subscriptions → Usage + quotas → Submit request

2. **Deploy to Different Region:** `azd env set AZURE_LOCATION westus2 && azd deploy`

3. **Reduce Resource Count:** `builder.AddProject<Projects.Api>("api").WithReplicas(1)`

### Azure Deployment - Container Build Failures

**Symptom:**
```
Error: Failed to build container image for 'api'
```

**Diagnosis:**
```bash
# Test local build
docker build -t api:test .

# Check Dockerfile
cat Dockerfile
```

**Common Issues:**

1. **Missing Dockerfile:** `dotnet new dockerfile --name Dockerfile`

2. **Build Context Issues:** Ensure correct paths in multi-stage Dockerfile (base → build → publish → final)

3. **Registry Authentication:** `az acr login --name myregistry`

## Connection Issues

### Service Discovery Not Working

**Symptom:** Service can't resolve other services by name.

**Example Error:**
```
HttpRequestException: No such host is known: api
```

**Diagnosis:**
```csharp
// Log connection string to verify
_logger.LogInformation("Connecting to: {Connection}",
    builder.Configuration.GetConnectionString("api"));
```

**Solutions:**

1. **Missing Reference:** Add `.WithReference(catalogApi)` to dependent service

2. **Wrong Connection String Name:** Match `GetConnectionString("name")` with AppHost resource name

3. **HTTP Client Configuration:**
   ```csharp
   builder.Services.AddHttpClient("catalog", client =>
   {
       var baseAddress = builder.Configuration.GetConnectionString("catalog-api");
       client.BaseAddress = new Uri(baseAddress!);
   });
   ```

### Redis Connection Failures

**Symptom:**
```
RedisConnectionException: It was not possible to connect to the redis server
```

**Diagnosis:**
```bash
aspire run  # Dashboard → Resources → cache → Status should be "Healthy"
redis-cli ping  # Should return: PONG
```

**Solutions:**

1. **Wait for Redis Startup**
   ```csharp
   builder.Services.AddStackExchangeRedisCache(options =>
   {
       options.Configuration = builder.Configuration.GetConnectionString("cache");
   })
   .AddStandardResilienceHandler();  // Adds retry policy
   ```

2. **Check Connection String Format:** Local `localhost:6379`, Azure `host:6380,ssl=True,password=...`

3. **Enable Connection Multiplexing**
   ```csharp
   builder.Services.AddSingleton<IConnectionMultiplexer>(sp =>
   {
       var connection = builder.Configuration.GetConnectionString("cache");
       return ConnectionMultiplexer.Connect(connection!);
   });
   ```

### Database Connection Timeouts

**Symptom:**
```
Npgsql.NpgsqlException: Connection timed out
```

**Solutions:**

1. **Increase Timeout**
   ```csharp
   builder.Services.AddDbContext<AppDbContext>(options =>
       options.UseNpgsql(
           builder.Configuration.GetConnectionString("db"),
           npgsqlOptions => npgsqlOptions.CommandTimeout(60)));
   ```

2. **Add Retry Policy**
   ```csharp
   builder.Services.AddDbContext<AppDbContext>(options =>
       options.UseNpgsql(
           builder.Configuration.GetConnectionString("db"),
           npgsqlOptions => npgsqlOptions.EnableRetryOnFailure(
               maxRetryCount: 5,
               maxRetryDelay: TimeSpan.FromSeconds(10),
               errorCodesToAdd: null)));
   ```

3. **Check Database Health:** Local: `docker logs [container-id]`, Azure: `az postgres flexible-server show`

## Dashboard Issues

### Dashboard Not Opening

**Symptom:** `aspire run` succeeds but Dashboard doesn't open in browser.

**Solutions:**

1. **Manual Navigation:** `aspire run` shows URL, open `http://localhost:15888` manually

2. **Port Conflict:** Check with `lsof -i :15888` or `netstat`, use `aspire run --dashboard-port 16000`

### Missing Telemetry Data

**Symptom:** Dashboard shows no traces or metrics for services.

**Solutions:**

1. **Add ServiceDefaults:**
   ```csharp
   builder.AddServiceDefaults();  // Adds OpenTelemetry
   var app = builder.Build();
   app.MapDefaultEndpoints();
   app.Run();
   ```

2. **Verify OpenTelemetry Configuration:** Check ServiceDefaults/Extensions.cs configures `.WithTracing()` and `.WithMetrics()`

3. **Check Dashboard Connection:** Service logs should show `OpenTelemetry exporting to http://localhost:4317`

## Performance Issues

### Slow Service Startup

**Symptom:** Services take minutes to start.

**Diagnosis:**
```bash
# Profile startup time
dotnet run --project MyApp.AppHost
# Note timestamps in console output
```

**Solutions:**

1. **Reduce Container Image Size:** Use Alpine-based images (`mcr.microsoft.com/dotnet/aspnet:8.0-alpine`)

2. **Parallel Startup:** Independent services start in parallel automatically

3. **Use Existing Containers:** `builder.AddConnectionString("cache")` for already-running services

### High Memory Usage

**Symptom:** Dashboard shows services using excessive memory.

**Diagnosis:** `docker stats` or Dashboard → Resources → [service] → Metrics → Memory

**Solutions:**

1. **Set Resource Limits**
   ```csharp
   builder.AddContainer("api", "my-api")
       .WithAnnotation(new ResourceLimits
       {
           MemoryLimit = "512Mi"
       });
   ```

2. **Optimize Application:** Use HttpClient factory, enable connection pooling with `.MaxPoolSize(50)`

## Environment-Specific Issues

### Differences Between Local and Cloud

**Symptom:** Works locally but fails in Azure.

**Common Causes:**

1. **Environment Detection**
   ```csharp
   if (builder.Environment.IsDevelopment())
   {
       // Local: uses AddRedis
       builder.AddRedis("cache");
   }
   else
   {
       // Cloud: uses Azure Redis (from config)
       builder.AddConnectionString("cache");
   }
   ```

2. **Managed Identity Not Configured**
   ```csharp
   // Local: uses connection string with password
   // Azure: uses managed identity (no password)

   builder.Services.AddDbContext<AppDbContext>(options =>
   {
       var connection = builder.Configuration.GetConnectionString("db");
       options.UseSqlServer(connection, sqlOptions =>
       {
           if (!builder.Environment.IsDevelopment())
           {
               sqlOptions.UseAzureIdentity();  // Managed identity
           }
       });
   });
   ```

3. **Missing Environment Variables**
   ```bash
   # Set in Azure Container App
   az containerapp update \
     --name my-api \
     --set-env-vars "FeatureFlags__NewUI=true"
   ```

## Getting Help

### Enable Verbose Logging

```bash
# Run with verbose output
aspire run --verbose

# Set log level
export Logging__LogLevel__Default=Debug
aspire run
```

### Collect Diagnostic Information

```bash
# Export Dashboard data
curl http://localhost:15888/api/resources > resources.json
curl http://localhost:15888/api/logs > logs.txt

# Collect Docker logs
docker-compose logs > docker-logs.txt

# Azure deployment logs
az containerapp logs show --name my-api --resource-group mygroup
```

### Common Log Patterns to Search For

| Pattern | Meaning |
|---------|---------|
| `Failed to bind to address` | Port conflict |
| `Unable to connect to` | Dependency not ready |
| `Health check timeout` | Service not responding |
| `Authentication failed` | Credentials issue |
| `No such host` | Service discovery problem |
| `Connection refused` | Service not listening |

### Report Issues

1. Check [GitHub Issues](https://github.com/dotnet/aspire/issues)
2. Search for error message
3. Include diagnostic information:
   - Aspire version (`dotnet workload list`)
   - OS and Docker version
   - AppHost code (minimal repro)
   - Full error message and stack trace

## Resources

**Troubleshooting Guides:**
- [Common Issues FAQ](https://learn.microsoft.com/dotnet/aspire/troubleshooting/overview) - Official troubleshooting guide
- [Health Checks](https://learn.microsoft.com/dotnet/aspire/fundamentals/health-checks) - Debugging health check failures
- [Networking Issues](https://learn.microsoft.com/dotnet/aspire/fundamentals/networking-overview#troubleshooting) - Service discovery problems

**Community Support:**
- [GitHub Discussions](https://github.com/dotnet/aspire/discussions) - Q&A and community help
- [Stack Overflow](https://stackoverflow.com/questions/tagged/dotnet-aspire) - Tagged questions
- [Discord Server](https://aka.ms/dotnet-discord) - Real-time community support

Most issues resolve by ensuring dependencies are properly referenced and health checks configured correctly.
