# Aspire Technical Reference

Complete API reference and architectural details for .NET Aspire orchestration.

**See also:** [Official API documentation](https://learn.microsoft.com/dotnet/api/aspire.hosting) for complete method signatures.

## AppHost API Reference

### DistributedApplication Builder

```csharp
var builder = DistributedApplication.CreateBuilder(args);
```

**Properties:**
- `builder.Configuration` - IConfiguration for appsettings.json
- `builder.Environment` - IHostEnvironment (Development, Staging, Production)
- `builder.Services` - IServiceCollection for dependency injection

**Methods:**
- `builder.AddProject<TProject>(string name)` - Add .NET project
- `builder.AddContainer(string name, string image)` - Add container
- `builder.AddExecutable(string name, string command, string workingDirectory)` - Add process
- `builder.Build()` - Build application
- `.Run()` - Start orchestration

### Resource Types

See [component overview](https://learn.microsoft.com/dotnet/aspire/fundamentals/components-overview) for all available resource types.

#### AddProject

Adds a .NET project to the application model. [API docs](https://learn.microsoft.com/dotnet/api/aspire.hosting.projectresourcebuilderextensions.addproject).

```csharp
builder.AddProject<Projects.Api>("api")
    .WithReference(redis)
    .WithHttpEndpoint(port: 8080, name: "http")
    .WithEnvironment("LOG_LEVEL", "Debug")
    .WithReplicas(3);
```

**Configuration:**
- `WithReference(IResourceBuilder)` - Add dependency reference
- `WithHttpEndpoint(int? port, string? name)` - HTTP endpoint
- `WithHttpsEndpoint(int? port, string? name)` - HTTPS endpoint
- `WithEnvironment(string, string)` - Environment variable
- `WithEnvironment(Action<EnvironmentCallbackContext>)` - Dynamic environment
- `WithReplicas(int)` - Replica count for cloud deployment

#### AddRedis

Adds Redis cache server. [Component docs](https://learn.microsoft.com/dotnet/aspire/caching/stackexchange-redis-component).

```csharp
builder.AddRedis("cache")
    .WithDataVolume()                    // Persistent storage
    .WithRedisCommander()                // Add Redis Commander UI
    .WithRedisInsight()                  // Add RedisInsight UI
    .WithImageTag("7.2-alpine")         // Specific Redis version
    .WithPersistence()                   // Enable RDB persistence
    .WithPersistence(interval: 900, changesThreshold: 1)  // Custom persistence
```

**Configuration:**
- `WithDataVolume(string? name)` - Mount volume for data persistence
- `WithRedisCommander(int? port)` - Add Redis Commander web UI
- `WithRedisInsight(int? port)` - Add RedisInsight web UI
- `WithImageTag(string tag)` - Specify Docker image tag
- `WithPersistence(int? interval, int? changesThreshold)` - Configure RDB persistence

#### AddPostgres

Adds PostgreSQL database server. [Component docs](https://learn.microsoft.com/dotnet/aspire/database/postgresql-component).

```csharp
builder.AddPostgres("pg")
    .WithDataVolume()                    // Persistent storage
    .WithPgAdmin()                       // Add pgAdmin UI
    .AddDatabase("mydb")                 // Create database
    .AddDatabase("otherdb");             // Multiple databases
```

**Configuration:**
- `WithDataVolume(string? name)` - Mount volume for data persistence
- `WithPgAdmin(int? port)` - Add pgAdmin web UI
- `WithImageTag(string tag)` - Specify Docker image tag
- `AddDatabase(string name)` - Create database (returns database resource)

**Database Resource:**
```csharp
var db = postgres.AddDatabase("mydb");
builder.AddProject<Projects.Api>("api")
    .WithReference(db);  // Reference specific database
```

#### AddSqlServer

Adds SQL Server database.

```csharp
builder.AddSqlServer("sql")
    .WithDataVolume()
    .AddDatabase("mydb");
```

**Configuration:** Similar to PostgreSQL.

#### AddMongoDB

Adds MongoDB database.

```csharp
builder.AddMongoDB("mongo")
    .WithDataVolume()
    .WithMongoExpress()                  // Add Mongo Express UI
    .AddDatabase("mydb");
```

**Configuration:**
- `WithDataVolume(string? name)` - Mount volume for data persistence
- `WithMongoExpress(int? port)` - Add Mongo Express web UI
- `AddDatabase(string name)` - Create database

#### AddRabbitMQ

Adds RabbitMQ message broker.

```csharp
builder.AddRabbitMQ("messaging")
    .WithDataVolume()
    .WithManagementPlugin();             // Enable management UI
```

**Configuration:**
- `WithDataVolume(string? name)` - Mount volume for data persistence
- `WithManagementPlugin(int? port)` - Enable RabbitMQ management UI

#### AddKafka

Adds Apache Kafka message broker.

```csharp
builder.AddKafka("kafka")
    .WithDataVolume()
    .WithKafkaUI();                      // Add Kafka UI
```

**Configuration:**
- `WithDataVolume(string? name)` - Mount volume for data persistence
- `WithKafkaUI(int? port)` - Add Kafka UI web interface

#### AddContainer

Adds generic Docker container.

```csharp
builder.AddContainer("nginx", "nginx:latest")
    .WithHttpEndpoint(port: 80, targetPort: 80)
    .WithBindMount("./nginx.conf", "/etc/nginx/nginx.conf")
    .WithVolume("nginx-data", "/data")
    .WithEnvironment("NGINX_PORT", "80");
```

**Configuration:**
- `WithHttpEndpoint(int?, int?, string?)` - Expose HTTP port
- `WithHttpsEndpoint(int?, int?, string?)` - Expose HTTPS port
- `WithBindMount(string, string, bool)` - Mount host directory
- `WithVolume(string, string, bool)` - Mount named volume
- `WithEnvironment(string, string)` - Environment variable

#### AddExecutable

Adds executable process.

```csharp
builder.AddExecutable("python-app", "python", ".")
    .WithArgs("app.py", "--port", "8000")
    .WithHttpEndpoint(port: 8000)
    .WithEnvironment("PYTHONPATH", "/app");
```

**Configuration:**
- `WithArgs(params string[])` - Command arguments
- `WithHttpEndpoint(int?, string?)` - Register HTTP endpoint
- `WithEnvironment(string, string)` - Environment variable

#### AddConnectionString

References external service via connection string from appsettings.json.

```csharp
// appsettings.json: "ConnectionStrings": { "external-api": "https://api.external.com" }
var externalApi = builder.AddConnectionString("external-api");
builder.AddProject<Projects.Api>("api").WithReference(externalApi);
```

**Use Cases:** External APIs, cloud-managed databases, third-party services

## Service Discovery & Environment Injection

See [service discovery overview](https://learn.microsoft.com/dotnet/aspire/service-discovery/overview).

### Automatic Connection String Generation

When you add a reference:
```csharp
var redis = builder.AddRedis("cache");
var api = builder.AddProject<Projects.Api>("api")
    .WithReference(redis);
```

**AppHost generates:**
```csharp
// Environment variable automatically injected into API:
ConnectionStrings__cache = "localhost:6379"  // Local
// or
ConnectionStrings__cache = "my-redis.redis.cache.windows.net:6380,ssl=True"  // Azure
```

**Service reads:**
```csharp
var connection = builder.Configuration.GetConnectionString("cache");
// Returns: "localhost:6379" or Azure Redis URL
```

### Environment Variable Naming

Reference name `"cache"` becomes:
- Connection string: `ConnectionStrings__cache`
- Configuration key: `ConnectionStrings:cache`

Reference name `"user-db"` becomes:
- Connection string: `ConnectionStrings__user_db`
- Configuration key: `ConnectionStrings:user-db`

**Convention:** Hyphens in names become underscores in environment variables.

### Dynamic Environment Configuration

```csharp
var api = builder.AddProject<Projects.Api>("api")
    .WithEnvironment(context =>
    {
        // Access other resources
        var redisEndpoint = context.ExecutionContext.IsPublishMode
            ? "my-redis.azure.com"
            : "localhost:6379";

        context.EnvironmentVariables["REDIS_URL"] = redisEndpoint;
        context.EnvironmentVariables["ENVIRONMENT"] = builder.Environment.EnvironmentName;
    });
```

## DCP Orchestration Internals

### Developer Control Plane (DCP)

[DCP](https://learn.microsoft.com/dotnet/aspire/fundamentals/networking-overview#aspire-orchestration) is the orchestration engine managing resource lifecycles.

**Architecture:**
```
AppHost (Program.cs)
    ↓ defines
App Model (IResource graph)
    ↓ consumed by
DCP (Orchestrator)
    ↓ manages
Docker Containers + Processes + Databases
```

**DCP Operations:**

1. **Parse AppHost**: Read Program.cs and build resource graph
2. **Resolve Dependencies**: Topological sort for startup order
3. **Provision Resources**: Start containers, processes in correct order
4. **Inject Environment**: Generate connection strings, inject into services
5. **Health Monitoring**: Poll health endpoints, restart on failure
6. **Log Aggregation**: Collect logs from all resources
7. **Telemetry**: Forward OpenTelemetry data to Dashboard

### Resource Lifecycle States

```
Defined → Starting → Running → Healthy
                ↓
           Failed → Restarting → Running
```

**States:**
- **Defined**: Resource declared in AppHost
- **Starting**: Container/process launching
- **Running**: Process started, not yet healthy
- **Healthy**: Health check passing
- **Failed**: Startup failed or health check failing
- **Restarting**: Attempting automatic recovery

### Dependency Resolution

```csharp
var redis = builder.AddRedis("cache");
var postgres = builder.AddPostgres("db").AddDatabase("mydb");
var api = builder.AddProject<Projects.Api>("api")
    .WithReference(redis)
    .WithReference(postgres);
```

**Startup Order:**
1. Redis container starts
2. PostgreSQL container starts
3. Wait for Redis and PostgreSQL health checks
4. API project starts with connection strings injected

**Parallel Startup:** Independent resources (Redis, PostgreSQL) start in parallel. Only dependent resources (API) wait.

### Health Checks

**Container Health:**
```csharp
builder.AddContainer("nginx", "nginx:latest")
    .WithHealthCheck("http://localhost/health");  // HTTP endpoint
```

**Project Health:**
```csharp
// ServiceDefaults automatically adds health checks
builder.Services.AddHealthChecks()
    .AddCheck("self", () => HealthCheckResult.Healthy());
```

**DCP Behavior:**
- Polls health endpoint every 10 seconds
- 3 consecutive failures → marks unhealthy
- Unhealthy → automatic restart
- Max 5 restarts before giving up

## Configuration Options

### Resource Limits

```csharp
builder.AddContainer("nginx", "nginx:latest")
    .WithAnnotation(new ResourceLimits
    {
        CpuLimit = 2.0,      // CPU cores
        MemoryLimit = "1Gi"   // Memory
    });
```

### Volumes and Persistence

**Named Volumes:**
```csharp
builder.AddPostgres("db")
    .WithDataVolume("postgres-data");  // Named volume
```

**Bind Mounts:**
```csharp
builder.AddContainer("nginx", "nginx:latest")
    .WithBindMount("./config/nginx.conf", "/etc/nginx/nginx.conf", isReadOnly: true);
```

**Volume Lifecycle:**
- Named volumes persist across `aspire run` sessions
- Bind mounts reference host filesystem
- Volumes deleted with `aspire down --volumes`

### Network Configuration

**Port Mapping:**
```csharp
builder.AddContainer("nginx", "nginx:latest")
    .WithHttpEndpoint(port: 8080, targetPort: 80);  // Host:8080 → Container:80
```

**Service-to-Service Communication:**
- Services communicate using service names (automatic DNS)
- Example: `http://api/users` (no need for localhost:port)

### Secrets Management

**Local Development:**
```csharp
builder.Configuration.AddUserSecrets<Program>();  // User secrets
```

**Cloud Deployment:**
```csharp
// Azure Key Vault automatically configured
builder.AddAzureKeyVault("vault");

var api = builder.AddProject<Projects.Api>("api")
    .WithReference(keyVault);  // Managed identity access
```

## Dashboard API

See [Dashboard documentation](https://learn.microsoft.com/dotnet/aspire/fundamentals/dashboard).

### Accessing Dashboard Programmatically

```bash
# Dashboard exposes REST API
GET http://localhost:15888/api/resources        # List all resources
GET http://localhost:15888/api/logs?name=api    # Get logs for resource
GET http://localhost:15888/api/metrics          # Prometheus-compatible metrics
```

### OpenTelemetry Integration

**Automatic Instrumentation:**
- HTTP requests (client + server)
- Database queries (Entity Framework, Dapper)
- Message queues (RabbitMQ, Kafka)
- Redis operations

**Custom Telemetry:**
```csharp
// ServiceDefaults automatically configures OpenTelemetry
using var activity = source.StartActivity("custom-operation");
activity?.SetTag("user.id", userId);
```

### Log Aggregation

**Structured Logging:**
```csharp
logger.LogInformation("User {UserId} performed {Action}", userId, action);
// Appears in Dashboard with structured fields
```

**Log Levels:**
- Trace, Debug, Information, Warning, Error, Critical
- Dashboard filters by level

## Azure Deployment Details

See [Azure deployment guide](https://learn.microsoft.com/dotnet/aspire/deployment/azure/aca-deployment).

### Bicep Generation

`azd deploy` analyzes AppHost and generates [Bicep templates](https://learn.microsoft.com/dotnet/aspire/deployment/azure/aca-deployment#deployment-manifest-and-bicep-template):

```bicep
// Generated from AddRedis("cache")
resource redis 'Microsoft.Cache/Redis@2023-08-01' = {
  name: 'my-app-cache'
  location: resourceGroup().location
  properties: {
    sku: { name: 'Basic', family: 'C', capacity: 1 }
  }
}

// Generated from AddProject<Api>("api")
resource apiApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'my-app-api'
  properties: {
    configuration: {
      secrets: [
        { name: 'redis-connection', value: redis.properties.hostName }
      ]
    }
    template: {
      containers: [{
        name: 'api'
        image: 'myacr.azurecr.io/api:latest'
        env: [
          { name: 'ConnectionStrings__cache', secretRef: 'redis-connection' }
        ]
      }]
    }
  }
}
```

### Azure Resources Mapping

| Aspire Resource | Azure Resource | Notes |
|----------------|----------------|-------|
| AddProject | Azure Container Apps | Serverless container hosting |
| AddRedis | Azure Cache for Redis | Managed Redis |
| AddPostgres | Azure Database for PostgreSQL | Managed PostgreSQL |
| AddSqlServer | Azure SQL Database | Managed SQL Server |
| AddMongoDB | Azure CosmosDB (MongoDB API) | Managed MongoDB |
| AddRabbitMQ | Azure Service Bus | Managed messaging |
| AddKafka | Azure Event Hubs | Kafka-compatible |

### Managed Identity Configuration

```csharp
// Local: uses connection strings
// Azure: automatically configures managed identity

var keyVault = builder.AddAzureKeyVault("vault");
var api = builder.AddProject<Projects.Api>("api")
    .WithReference(keyVault);  // Managed identity granted Key Vault access
```

**Azure Behavior:**
- Container App gets system-assigned managed identity
- Identity granted access to Key Vault, databases, storage
- No connection strings or passwords in configuration

## Advanced Patterns

### Custom Resource Types

```csharp
// Implement IResource for custom resources
public class CustomResource : IResource
{
    public string Name { get; }
    // Custom implementation
}

public static class CustomResourceExtensions
{
    public static IResourceBuilder<CustomResource> AddCustom(
        this IDistributedApplicationBuilder builder,
        string name)
    {
        var resource = new CustomResource(name);
        return builder.AddResource(resource);
    }
}

// Usage:
builder.AddCustom("my-resource");
```

### Conditional Resources

```csharp
if (builder.Environment.IsDevelopment())
{
    builder.AddRedis("cache");  // Local Redis
}
else
{
    builder.AddConnectionString("cache");  // Azure Redis (from config)
}
```

### Multi-Region Deployment

```csharp
var primaryDb = builder.AddPostgres("db-primary");
var replicaDb = builder.AddPostgres("db-replica")
    .WithReplicaOf(primaryDb);

var api = builder.AddProject<Projects.Api>("api")
    .WithReference(primaryDb)      // Write operations
    .WithReference(replicaDb);     // Read operations
```

## Resources

**API Reference:**
- [Aspire.Hosting Namespace](https://learn.microsoft.com/dotnet/api/aspire.hosting) - Complete API documentation
- [Component Overview](https://learn.microsoft.com/dotnet/aspire/fundamentals/components-overview) - All available integrations
- [AppHost Reference](https://learn.microsoft.com/dotnet/aspire/fundamentals/app-host-overview) - Detailed AppHost guide

**Advanced Topics:**
- [Networking & Service Discovery](https://learn.microsoft.com/dotnet/aspire/fundamentals/networking-overview)
- [Health Checks](https://learn.microsoft.com/dotnet/aspire/fundamentals/health-checks)
- [Testing Aspire Apps](https://learn.microsoft.com/dotnet/aspire/fundamentals/testing)

See patterns.md for complete production deployment strategies.
