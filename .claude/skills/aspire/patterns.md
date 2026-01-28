# Aspire Production Patterns

Best practices, production deployment strategies, and anti-patterns for .NET Aspire.

## Production Deployment Patterns

### High Availability Configuration

**Multi-Replica Services:**
```csharp
var builder = DistributedApplication.CreateBuilder(args);

var redis = builder.AddRedis("cache");
var postgres = builder.AddPostgres("db").AddDatabase("appdb");

var api = builder.AddProject<Projects.Api>("api")
    .WithReference(redis)
    .WithReference(postgres)
    .WithReplicas(3);  // 3 instances for HA

builder.Build().Run();
```

**Azure Deployment Result:** Container App scales 1-3 replicas with load balancing, health checks, automatic failover

**Database High Availability:**
```csharp
if (builder.Environment.IsProduction())
{
    var postgres = builder.AddPostgres("db")
        .WithHighAvailability()  // Enables replication
        .WithBackupRetention(days: 35)
        .AddDatabase("appdb");
}
else
{
    var postgres = builder.AddPostgres("db")
        .WithDataVolume()
        .AddDatabase("appdb");
}
```

### Multi-Region Deployment

**Primary + Read Replicas:**
```csharp
var builder = DistributedApplication.CreateBuilder(args);

// Primary database (writes)
var primaryDb = builder.AddPostgres("db-primary")
    .WithHighAvailability()
    .AddDatabase("appdb");

// Read replicas (reads)
var replicaEast = builder.AddPostgres("db-replica-east")
    .WithReplicaOf(primaryDb);

var replicaWest = builder.AddPostgres("db-replica-west")
    .WithReplicaOf(primaryDb);

// API in East region
var apiEast = builder.AddProject<Projects.Api>("api-east")
    .WithReference(primaryDb)       // Writes
    .WithReference(replicaEast)     // Reads
    .WithReplicas(3);

// API in West region
var apiWest = builder.AddProject<Projects.Api>("api-west")
    .WithReference(primaryDb)       // Writes
    .WithReference(replicaWest)     // Reads
    .WithReplicas(3);
```

**Application Code (CQRS Pattern):**
```csharp
public class DatabaseService
{
    private readonly AppDbContext _writeDb;
    private readonly AppDbContext _readDb;

    public DatabaseService(
        [FromKeyedServices("primary")] AppDbContext writeDb,
        [FromKeyedServices("replica")] AppDbContext readDb)
    {
        _writeDb = writeDb;
        _readDb = readDb;
    }

    public async Task<User> GetUserAsync(int id) =>
        await _readDb.Users.FindAsync(id);  // Read from replica

    public async Task CreateUserAsync(User user)
    {
        _writeDb.Users.Add(user);
        await _writeDb.SaveChangesAsync();  // Write to primary
    }
}
```

### Load Balancing Strategy

**Geographic Load Balancing:**
```csharp
// Azure Front Door configuration
if (builder.Environment.IsProduction())
{
    var frontDoor = builder.AddAzureFrontDoor("cdn")
        .WithOrigin("api-east", apiEast)
        .WithOrigin("api-west", apiWest)
        .WithRoutingPolicy(RoutingPolicy.Performance);  // Route to nearest region

    var web = builder.AddProject<Projects.Web>("web")
        .WithReference(frontDoor);
}
```

## Security Best Practices

### Secrets Management

**Local Development (User Secrets):**
```bash
dotnet user-secrets init
dotnet user-secrets set "ApiKeys:External" "dev-api-key-12345"
```

**Production (Azure Key Vault):**
```csharp
var builder = DistributedApplication.CreateBuilder(args);

var keyVault = builder.AddAzureKeyVault("vault");

var api = builder.AddProject<Projects.Api>("api")
    .WithReference(keyVault);  // Managed identity access granted

builder.Build().Run();
```

**API Access to Secrets:**
```csharp
var builder = WebApplication.CreateBuilder(args);

// Aspire automatically configures Key Vault with managed identity
var externalApiKey = builder.Configuration["ApiKeys:External"];

builder.Services.AddHttpClient("external", client =>
{
    client.DefaultRequestHeaders.Add("Authorization", $"Bearer {externalApiKey}");
});
```

**Never Store Secrets in Code:**
```csharp
// ❌ BAD - Hardcoded secret
var apiKey = "sk-12345-secret";

// ✅ GOOD - From configuration
var apiKey = builder.Configuration["ApiKeys:External"];
```

### Managed Identity Pattern

**Database Access Without Connection Strings:**
```csharp
var builder = DistributedApplication.CreateBuilder(args);

if (builder.Environment.IsProduction())
{
    // Azure SQL with managed identity
    var sqlDb = builder.AddAzureSqlDatabase("db")
        .WithManagedIdentity();  // No password needed

    var api = builder.AddProject<Projects.Api>("api")
        .WithReference(sqlDb);  // Identity granted db_datareader, db_datawriter
}
else
{
    // Local with connection string
    var sqlDb = builder.AddSqlServer("sql").AddDatabase("db");
    var api = builder.AddProject<Projects.Api>("api").WithReference(sqlDb);
}
```

**API Configuration:**
```csharp
builder.Services.AddDbContext<AppDbContext>(options =>
{
    var connection = builder.Configuration.GetConnectionString("db");
    options.UseSqlServer(connection, sqlOptions =>
    {
        if (builder.Environment.IsProduction())
        {
            // Managed identity authentication
            sqlOptions.UseAzureIdentity();
        }
    });
});
```

### Network Isolation

**Private Endpoints:**
```csharp
if (builder.Environment.IsProduction())
{
    var vnet = builder.AddAzureVirtualNetwork("vnet");

    var postgres = builder.AddPostgres("db")
        .WithPrivateEndpoint(vnet)  // Not exposed to internet
        .AddDatabase("appdb");

    var api = builder.AddProject<Projects.Api>("api")
        .WithVirtualNetwork(vnet)   // Inside VNet
        .WithReference(postgres);   // Private communication
}
```

**API Management Gateway:**
```csharp
var apiManagement = builder.AddAzureApiManagement("apim")
    .WithPolicy(new RateLimitPolicy(requestsPerMinute: 100))
    .WithPolicy(new IpFilterPolicy(allowedIps: ["10.0.0.0/8"]));

var api = builder.AddProject<Projects.Api>("api")
    .WithReference(postgres)
    .ExposeVia(apiManagement);  // All traffic goes through APIM
```

## Performance Optimization

### Connection Pooling

**Database Connection Pools:**
```csharp
builder.Services.AddDbContext<AppDbContext>(options =>
{
    options.UseNpgsql(builder.Configuration.GetConnectionString("db"), npgsqlOptions =>
    {
        npgsqlOptions.EnableRetryOnFailure(maxRetryCount: 3);
        npgsqlOptions.CommandTimeout(30);
        npgsqlOptions.MinPoolSize(5);    // Min connections
        npgsqlOptions.MaxPoolSize(100);  // Max connections
    });
});
```

**Redis Connection Multiplexing:**
```csharp
builder.Services.AddSingleton<IConnectionMultiplexer>(sp =>
{
    var connection = builder.Configuration.GetConnectionString("cache");
    return ConnectionMultiplexer.Connect(new ConfigurationOptions
    {
        EndPoints = { connection! },
        ConnectRetry = 3,
        ReconnectRetryPolicy = new ExponentialRetry(5000),
        AbortOnConnectFail = false
    });
});
```

### Caching Strategy

**Multi-Level Caching:**
```csharp
public class CatalogService
{
    private readonly IMemoryCache _memoryCache;
    private readonly IDistributedCache _redisCache;
    private readonly AppDbContext _db;

    public async Task<Product?> GetProductAsync(int id)
    {
        if (_memoryCache.TryGetValue($"product:{id}", out Product? product))
            return product;

        var cached = await _redisCache.GetStringAsync($"product:{id}");
        if (cached != null)
        {
            product = JsonSerializer.Deserialize<Product>(cached);
            _memoryCache.Set($"product:{id}", product, TimeSpan.FromMinutes(1));
            return product;
        }

        product = await _db.Products.FindAsync(id);
        if (product != null)
        {
            await _redisCache.SetStringAsync($"product:{id}",
                JsonSerializer.Serialize(product),
                new DistributedCacheEntryOptions { AbsoluteExpirationRelativeToNow = TimeSpan.FromMinutes(10) });

            _memoryCache.Set($"product:{id}", product, TimeSpan.FromMinutes(1));
        }

        return product;
    }
}
```

**Cache Invalidation:**
```csharp
public async Task UpdateProductAsync(Product product)
{
    _db.Products.Update(product);
    await _db.SaveChangesAsync();

    _memoryCache.Remove($"product:{product.Id}");
    await _redisCache.RemoveAsync($"product:{product.Id}");

    await _messageBus.PublishAsync(new CacheInvalidationEvent
    {
        CacheKey = $"product:{product.Id}"
    });
}
```

### Asynchronous Processing

**Background Jobs Pattern:**
```csharp
var builder = DistributedApplication.CreateBuilder(args);

var rabbitmq = builder.AddRabbitMQ("queue");
var postgres = builder.AddPostgres("db").AddDatabase("appdb");

var api = builder.AddProject<Projects.Api>("api")
    .WithReference(postgres)
    .WithReference(rabbitmq);

var worker = builder.AddProject<Projects.Worker>("worker")
    .WithReference(postgres)
    .WithReference(rabbitmq)
    .WithReplicas(5);

builder.Build().Run();
```

**API Publishes Job:**
```csharp
app.MapPost("/process", async (ProcessRequest request, IMessageBus bus) =>
{
    var jobId = Guid.NewGuid();
    await bus.PublishAsync(new ProcessJob { JobId = jobId, Data = request.Data });
    return Results.Accepted($"/jobs/{jobId}", new { jobId });
});

app.MapGet("/jobs/{jobId}", async (Guid jobId, AppDbContext db) =>
{
    var job = await db.Jobs.FindAsync(jobId);
    return job != null ? Results.Ok(job) : Results.NotFound();
});
```

**Worker Processes Asynchronously:**
```csharp
public class Worker : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        await foreach (var job in _messageBus.ConsumeAsync<ProcessJob>(stoppingToken))
        {
            var result = await ProcessAsync(job.Data);
            var dbJob = await _db.Jobs.FindAsync(job.JobId);
            dbJob.Status = "Completed";
            dbJob.Result = result;
            await _db.SaveChangesAsync();
        }
    }
}
```

## Monitoring and Observability

### Custom Metrics

**Export Business Metrics:**
```csharp
public class OrderService
{
    private readonly Counter<int> _orderCounter;
    private readonly Histogram<double> _orderValue;

    public OrderService(IMeterFactory meterFactory)
    {
        var meter = meterFactory.Create("ECommerce.Orders");
        _orderCounter = meter.CreateCounter<int>("orders.created");
        _orderValue = meter.CreateHistogram<double>("orders.value");
    }

    public async Task CreateOrderAsync(Order order)
    {
        await _db.Orders.AddAsync(order);
        await _db.SaveChangesAsync();

        _orderCounter.Add(1, new KeyValuePair<string, object?>("status", "success"));
        _orderValue.Record(order.TotalAmount);
    }
}
```

**Dashboard:** Metrics tab shows `orders.created` counter and `orders.value` distribution with percentiles (p50, p95, p99)

### Distributed Tracing

**Custom Spans:**
```csharp
public class CatalogService
{
    private readonly ActivitySource _activitySource;

    public CatalogService()
    {
        _activitySource = new ActivitySource("ECommerce.Catalog");
    }

    public async Task<Product?> GetProductAsync(int id)
    {
        using var activity = _activitySource.StartActivity("GetProduct");
        activity?.SetTag("product.id", id);

        var product = await _db.Products.FindAsync(id);

        activity?.SetTag("product.found", product != null);
        activity?.SetTag("product.category", product?.Category);

        return product;
    }
}
```

**Trace Propagation:** Automatic across HTTP calls, visible in Dashboard
```csharp
var client = _httpClientFactory.CreateClient("catalog-api");
var response = await client.GetAsync("/products/123");
```

### Structured Logging

**Rich Logging:**
```csharp
_logger.LogInformation(
    "Order {OrderId} created by user {UserId} with {ItemCount} items totaling {TotalAmount:C}",
    order.Id, order.UserId, order.Items.Count, order.TotalAmount);
// Dashboard shows structured fields: OrderId, UserId, ItemCount, TotalAmount
```

**Log Correlation:**
```csharp
using (_logger.BeginScope(new Dictionary<string, object>
{
    ["TransactionId"] = transactionId,
    ["CorrelationId"] = correlationId
}))
{
    _logger.LogInformation("Processing payment");
    await _paymentService.ProcessAsync();
    _logger.LogInformation("Payment processed");
}
```

## Anti-Patterns (What NOT to Do)

### ❌ Hardcoded Connection Strings

```csharp
// BAD - Bypasses Aspire service discovery
builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseNpgsql("Host=localhost;Database=mydb"));

// GOOD - Uses Aspire-managed connection
builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseNpgsql(builder.Configuration.GetConnectionString("db")));
```

### ❌ Manual Container Management

```csharp
// BAD - Starting containers manually
Process.Start("docker", "run -p 6379:6379 redis");

// GOOD - Let Aspire manage it
builder.AddRedis("cache");
```

### ❌ Bypassing ServiceDefaults

```csharp
// BAD - Custom telemetry configuration
builder.Services.AddOpenTelemetry()
    .WithTracing(/* manual config */);

// GOOD - Use ServiceDefaults for shared configuration
builder.AddServiceDefaults();  // Includes telemetry, health checks, resilience
```

### ❌ Ignoring Health Checks

```csharp
// BAD - No health check
builder.AddProject<Projects.Api>("api");

// GOOD - Add health checks
var api = builder.AddProject<Projects.Api>("api");

// In API project:
builder.Services.AddHealthChecks()
    .AddDbContextCheck<AppDbContext>()
    .AddRedis(builder.Configuration.GetConnectionString("cache")!);

app.MapHealthChecks("/health");
```

### ❌ Synchronous Blocking Calls

```csharp
// BAD - Blocking I/O
var product = _db.Products.Find(id);  // Blocks thread
var response = _httpClient.GetAsync(url).Result;  // Deadlock risk

// GOOD - Async all the way
var product = await _db.Products.FindAsync(id);
var response = await _httpClient.GetAsync(url);
```

### ❌ Missing Retry Policies

```csharp
// BAD - No resilience
builder.Services.AddHttpClient("external", client => { /* config */ });

// GOOD - Add retry and circuit breaker
builder.Services.AddHttpClient("external", client => { /* config */ })
    .AddStandardResilienceHandler();  // From ServiceDefaults

// Or custom policy:
builder.Services.AddHttpClient("external")
    .AddPolicyHandler(Policy
        .Handle<HttpRequestException>()
        .WaitAndRetryAsync(3, retryAttempt => TimeSpan.FromSeconds(Math.Pow(2, retryAttempt))));
```

### ❌ Single Point of Failure

```csharp
// BAD - Single instance in production
var api = builder.AddProject<Projects.Api>("api");

// GOOD - Multiple replicas
var api = builder.AddProject<Projects.Api>("api")
    .WithReplicas(3);  // High availability
```

### ❌ Ignoring Environment Differences

```csharp
// BAD - Same config for all environments
var postgres = builder.AddPostgres("db").AddDatabase("appdb");

// GOOD - Environment-specific config
var postgres = builder.Environment.IsProduction()
    ? builder.AddAzurePostgres("db").WithHighAvailability()
    : builder.AddPostgres("db").WithDataVolume();

var db = postgres.AddDatabase("appdb");
```

### ❌ Missing Resource Limits

```csharp
// BAD - Unbounded resource usage
builder.AddContainer("worker", "my-worker");

// GOOD - Set limits
builder.AddContainer("worker", "my-worker")
    .WithAnnotation(new ResourceLimits
    {
        CpuLimit = 1.0,
        MemoryLimit = "512Mi"
    });
```

### ❌ Not Using Dashboard

```csharp
// BAD - Adding custom logging infrastructure
builder.Services.AddSerilog();  // Unnecessary complexity

// GOOD - Use built-in Dashboard
// Aspire Dashboard already provides:
// - Structured logging
// - Distributed tracing
// - Metrics visualization
// - Resource monitoring
```

## Migration Strategies

### Docker Compose → Aspire

**Old (docker-compose.yml):**
```yaml
services:
  api:
    build: ./api
    ports:
      - "5000:80"
    environment:
      - ConnectionStrings__db=Host=postgres;Database=mydb
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres-data:/var/lib/postgresql/data

  redis:
    image: redis:7
```

**New (AppHost):**
```csharp
var builder = DistributedApplication.CreateBuilder(args);

var postgres = builder.AddPostgres("postgres")
    .WithDataVolume()
    .AddDatabase("mydb");

var redis = builder.AddRedis("redis")
    .WithDataVolume();

var api = builder.AddProject<Projects.Api>("api")
    .WithReference(postgres)
    .WithReference(redis);

builder.Build().Run();
```

**Benefits:**
- Type-safe configuration
- Automatic service discovery
- Built-in observability
- Same code deploys to cloud

### Kubernetes → Aspire

Aspire generates Kubernetes manifests via azd CLI. Migration path:

1. Convert Kubernetes Services → `AddProject` / `AddContainer`
2. Convert ConfigMaps → `WithEnvironment` / `WithReference`
3. Convert Secrets → Azure Key Vault integration
4. Convert Deployments → Aspire resource definitions

AppHost becomes the single source of truth for both local and cloud deployment.

## Production Checklist

Before deploying to production:

- [ ] Health checks configured for all services
- [ ] Secrets moved to Azure Key Vault (no hardcoded values)
- [ ] Managed identities enabled (no connection string passwords)
- [ ] Resource limits set (CPU, memory)
- [ ] Replica counts configured (min 2 for HA)
- [ ] Retry and circuit breaker policies added
- [ ] Monitoring and alerts configured
- [ ] Database backups enabled
- [ ] Network isolation (VNet, private endpoints)
- [ ] Load testing completed
- [ ] Disaster recovery plan documented

Use these patterns to build robust, scalable, production-ready Aspire applications.
