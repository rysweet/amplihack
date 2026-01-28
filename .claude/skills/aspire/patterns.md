# Aspire Production Patterns

Best practices, production deployment strategies, and anti-patterns for .NET Aspire.

**See also:** [Deployment overview](https://learn.microsoft.com/dotnet/aspire/deployment/overview) for complete Azure deployment strategies.

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

See [security overview](https://learn.microsoft.com/dotnet/aspire/security/overview) for complete security guidance.

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

## Polyglot Service Communication Patterns

### HTTP Communication

**Pattern: REST API between services**
```csharp
// AppHost - Python API calling Node.js service
var nodeApi = builder.AddExecutable("node-api", "node", ".")
    .WithArgs("server.js")
    .WithHttpEndpoint(port: 3000, name: "http");

var pythonApi = builder.AddExecutable("python-api", "python", ".")
    .WithArgs("app.py")
    .WithReference(nodeApi)
    .WithHttpEndpoint(port: 8000);
```

**Python Service (FastAPI):**
```python
from fastapi import FastAPI
import httpx
import os

app = FastAPI()

# Aspire injects: services__node_api__http__0=http://localhost:3000
node_url = os.environ.get("services__node_api__http__0")

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{node_url}/users/{user_id}")
        return response.json()
```

**Node.js Service (Express):**
```javascript
const express = require('express');
const app = express();

app.get('/users/:id', (req, res) => {
    res.json({ id: req.params.id, name: 'John Doe' });
});

app.listen(3000);
```

### gRPC Communication

**Pattern: High-performance RPC between services**
```csharp
// AppHost - Go gRPC server with C# client
var grpcServer = builder.AddExecutable("grpc-server", "go", ".")
    .WithArgs("run", "server.go")
    .WithHttpEndpoint(port: 9000, name: "grpc");

var api = builder.AddProject<Projects.Api>("api")
    .WithReference(grpcServer);
```

**Go gRPC Server:**
```go
// server.go
package main

import (
    "context"
    "net"
    "google.golang.org/grpc"
    pb "myapp/proto"
)

type server struct {
    pb.UnimplementedUserServiceServer
}

func (s *server) GetUser(ctx context.Context, req *pb.UserRequest) (*pb.UserResponse, error) {
    return &pb.UserResponse{Id: req.Id, Name: "John Doe"}, nil
}

func main() {
    lis, _ := net.Listen("tcp", ":9000")
    s := grpc.NewServer()
    pb.RegisterUserServiceServer(s, &server{})
    s.Serve(lis)
}
```

**C# gRPC Client:**
```csharp
var grpcUrl = builder.Configuration["services:grpc-server:grpc:0"];
var channel = GrpcChannel.ForAddress(grpcUrl!);
var client = new UserService.UserServiceClient(channel);

var response = await client.GetUserAsync(new UserRequest { Id = 123 });
```

### Message Queue Communication

**Pattern: Async communication with RabbitMQ**
```csharp
// AppHost - Polyglot services with RabbitMQ
var rabbitmq = builder.AddRabbitMQ("messaging");

var pythonProducer = builder.AddExecutable("producer", "python", ".")
    .WithArgs("producer.py")
    .WithReference(rabbitmq);

var nodeConsumer = builder.AddExecutable("consumer", "node", ".")
    .WithArgs("consumer.js")
    .WithReference(rabbitmq);
```

**Python Producer (pika):**
```python
import pika
import os
import json

rabbitmq_url = os.environ.get("ConnectionStrings__messaging")
params = pika.URLParameters(rabbitmq_url)
connection = pika.BlockingConnection(params)
channel = connection.channel()

channel.queue_declare(queue='tasks')
channel.basic_publish(exchange='', routing_key='tasks',
                      body=json.dumps({'task': 'process', 'data': 'value'}))
```

**Node.js Consumer (amqplib):**
```javascript
const amqp = require('amqplib');

const rabbitmqUrl = process.env.ConnectionStrings__messaging;
const connection = await amqp.connect(rabbitmqUrl);
const channel = await connection.createChannel();

await channel.assertQueue('tasks');
channel.consume('tasks', (msg) => {
    const task = JSON.parse(msg.content.toString());
    console.log('Processing:', task);
    channel.ack(msg);
});
```

### Redis Pub/Sub Communication

**Pattern: Event broadcasting across services**
```csharp
var redis = builder.AddRedis("cache");

var publisher = builder.AddExecutable("publisher", "python", ".")
    .WithArgs("publisher.py")
    .WithReference(redis);

var subscriber = builder.AddProject<Projects.Subscriber>("subscriber")
    .WithReference(redis);
```

**Python Publisher:**
```python
import redis
import os

r = redis.from_url(os.environ.get("ConnectionStrings__cache"))
r.publish('events', 'user.created:123')
```

**C# Subscriber:**
```csharp
var redis = ConnectionMultiplexer.Connect(builder.Configuration.GetConnectionString("cache")!);
var subscriber = redis.GetSubscriber();

await subscriber.SubscribeAsync("events", (channel, message) =>
{
    Console.WriteLine($"Event received: {message}");
});
```

## Language-Specific Best Practices

### Python Services

**Async/Await Pattern:**
```python
# Use asyncio for I/O-bound operations
import asyncio
import aioredis
import asyncpg

async def process_request():
    redis = await aioredis.from_url(os.environ.get("ConnectionStrings__cache"))
    db = await asyncpg.connect(os.environ.get("ConnectionStrings__db"))

    # Parallel I/O operations
    user, cache_data = await asyncio.gather(
        db.fetchrow("SELECT * FROM users WHERE id=$1", user_id),
        redis.get(f"user:{user_id}")
    )
```

**Environment Variable Handling:**
```python
# Aspire uses double underscore for nested config
# ConnectionStrings__cache → ConnectionStrings:cache
redis_conn = os.environ.get("ConnectionStrings__cache")
db_conn = os.environ.get("ConnectionStrings__db")

# Service endpoints use services__ prefix
api_url = os.environ.get("services__api__http__0")
```

### Node.js Services

**Event Loop Optimization:**
```javascript
// Use async/await for non-blocking I/O
const redis = require('redis');
const { Pool } = require('pg');

const redisClient = redis.createClient({
    url: process.env.ConnectionStrings__cache
});
const pgPool = new Pool({
    connectionString: process.env.ConnectionStrings__db
});

app.get('/users/:id', async (req, res) => {
    // Non-blocking parallel queries
    const [user, cachedData] = await Promise.all([
        pgPool.query('SELECT * FROM users WHERE id=$1', [req.params.id]),
        redisClient.get(`user:${req.params.id}`)
    ]);
    res.json(user.rows[0]);
});
```

**Graceful Shutdown:**
```javascript
// Handle SIGTERM from Aspire orchestration
process.on('SIGTERM', async () => {
    console.log('SIGTERM received, shutting down gracefully');
    await pgPool.end();
    await redisClient.quit();
    process.exit(0);
});
```

### Go Services

**Goroutine Management:**
```go
// Use context for cancellation propagation
func handleRequest(ctx context.Context, db *sql.DB, redis *redis.Client) error {
    // Use goroutines for parallel operations
    var user User
    var cacheData string

    errGroup, ctx := errgroup.WithContext(ctx)

    errGroup.Go(func() error {
        return db.QueryRowContext(ctx, "SELECT * FROM users WHERE id=$1", id).Scan(&user)
    })

    errGroup.Go(func() error {
        cacheData, err = redis.Get(ctx, fmt.Sprintf("user:%d", id)).Result()
        return err
    })

    return errGroup.Wait()
}
```

**Environment Configuration:**
```go
// Read Aspire-injected connection strings
redisConn := os.Getenv("ConnectionStrings__cache")
dbConn := os.Getenv("ConnectionStrings__db")

// Parse and connect
redisClient := redis.NewClient(&redis.Options{
    Addr: redisConn,
})
db, _ := sql.Open("postgres", dbConn)
```

## Development Workflow Patterns

### Hot Reload per Language

**C# (Built-in):**
```bash
# Automatic hot reload with dotnet watch
aspire run  # Hot reload enabled by default
```

**Python (with watchdog):**
```python
# Add to Dockerfile or startup script
pip install watchdog
watchmedo auto-restart --patterns="*.py" --recursive -- python app.py
```

**Node.js (with nodemon):**
```json
// package.json
{
    "scripts": {
        "dev": "nodemon server.js"
    },
    "devDependencies": {
        "nodemon": "^3.0.0"
    }
}
```

**AppHost Configuration:**
```csharp
if (builder.Environment.IsDevelopment())
{
    builder.AddExecutable("node-api", "npm", ".")
        .WithArgs("run", "dev");  // Uses nodemon
}
else
{
    builder.AddExecutable("node-api", "node", ".")
        .WithArgs("server.js");
}
```

### Debugging Polyglot Applications

**Attach Debugger to Specific Service:**

**Python (VS Code):**
```json
// .vscode/launch.json
{
    "name": "Attach to Python API",
    "type": "python",
    "request": "attach",
    "connect": {
        "host": "localhost",
        "port": 5678
    }
}
```

**Start Python service with debugpy:**
```python
# app.py
import debugpy
debugpy.listen(5678)
# debugpy.wait_for_client()  # Uncomment to wait for debugger
```

**Node.js (VS Code):**
```json
// .vscode/launch.json
{
    "name": "Attach to Node API",
    "type": "node",
    "request": "attach",
    "port": 9229
}
```

**Start Node.js with inspect:**
```javascript
// AppHost
builder.AddExecutable("node-api", "node", ".")
    .WithArgs("--inspect=9229", "server.js");
```

**Go (Delve):**
```bash
# Install delve
go install github.com/go-delve/delve/cmd/dlv@latest

# Start with debugger
dlv debug --headless --listen=:2345 --api-version=2
```

### Shared Configuration Pattern

**appsettings.json (shared config):**
```json
{
    "Logging": {
        "LogLevel": { "Default": "Information" }
    },
    "ConnectionStrings": {
        "external-api": "https://api.external.com"
    }
}
```

**Read in Python:**
```python
import json
with open('appsettings.json') as f:
    config = json.load(f)
    external_api = config['ConnectionStrings']['external-api']
```

**Read in Node.js:**
```javascript
const config = require('./appsettings.json');
const externalApi = config.ConnectionStrings['external-api'];
```

**Read in Go:**
```go
import "encoding/json"

type Config struct {
    ConnectionStrings map[string]string `json:"ConnectionStrings"`
}

file, _ := os.Open("appsettings.json")
var config Config
json.NewDecoder(file).Decode(&config)
externalApi := config.ConnectionStrings["external-api"]
```

## Polyglot Anti-Patterns

### ❌ Language-Specific Serialization Pitfalls

**Bad - Python datetime to JSON:**
```python
# BAD - Python datetime not JSON serializable
import datetime
data = {'timestamp': datetime.datetime.now()}
json.dumps(data)  # ERROR: datetime not serializable
```

**Good - ISO 8601 strings:**
```python
# GOOD - Use ISO 8601 strings
data = {'timestamp': datetime.datetime.now().isoformat()}
json.dumps(data)  # Works across all languages
```

### ❌ Async/Sync Boundary Violations

**Bad - Blocking in async context:**
```python
# BAD - Blocking I/O in async function
async def get_user(user_id):
    response = requests.get(f"http://api/users/{user_id}")  # Blocks event loop
    return response.json()
```

**Good - Use async libraries:**
```python
# GOOD - Non-blocking async I/O
async def get_user(user_id):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://api/users/{user_id}")
        return response.json()
```

### ❌ Inconsistent Error Handling

**Bad - Language-specific error formats:**
```python
# Python returns dict
{"error": "Not found", "code": 404}

# Node.js returns different format
{"message": "Not found", "statusCode": 404}
```

**Good - Standardized error format:**
```json
{
    "error": {
        "code": "NOT_FOUND",
        "message": "Resource not found",
        "statusCode": 404,
        "timestamp": "2026-01-28T12:00:00Z"
    }
}
```

### ❌ Hardcoded Service URLs

**Bad - Hardcoded endpoints:**
```python
# BAD - Hardcoded URL breaks in different environments
api_url = "http://localhost:3000/users"
```

**Good - Environment-based discovery:**
```python
# GOOD - Use Aspire service discovery
api_url = os.environ.get("services__node_api__http__0")
users_endpoint = f"{api_url}/users"
```

### ❌ Missing Health Checks

**Bad - No health endpoint:**
```python
# BAD - Service has no health check
app = FastAPI()
# No /health endpoint
```

**Good - Implement health checks:**
```python
# GOOD - Health endpoint for DCP monitoring
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "python-api"}
```

## Quick Reference: Polyglot Patterns

| Pattern | Use Case | Languages | Latency | Complexity |
|---------|----------|-----------|---------|------------|
| **HTTP REST** | Public APIs, CRUD operations | All | 5-50ms | Low |
| **gRPC** | Internal services, high throughput | C#, Go, Python | 1-10ms | Medium |
| **Message Queue** | Async tasks, decoupling | All | 10-100ms | Medium |
| **Redis Pub/Sub** | Real-time events, broadcasting | All | 1-5ms | Low |
| **Shared Database** | Data consistency (use sparingly) | All | 1-10ms | Low |

**Recommendation:** Start with HTTP REST, migrate to gRPC for performance-critical paths, use message queues for long-running tasks.

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

## Polyglot Service Communication

**HTTP Communication (Recommended):**

Services in different languages communicate via HTTP using service discovery:

```csharp
// AppHost - Python and .NET services
var pythonApi = builder.AddExecutable("python-api", "python", ".").WithArgs("app.py").WithHttpEndpoint(port: 8000);
var dotnetApi = builder.AddProject<Projects.Api>("api").WithReference(pythonApi);
```

```csharp
// .NET calls Python service
builder.Services.AddHttpClient("python", client =>
{
    client.BaseAddress = new Uri(builder.Configuration.GetConnectionString("python-api")!);
});

app.MapGet("/call-python", async (IHttpClientFactory factory) =>
{
    var client = factory.CreateClient("python");
    return await client.GetStringAsync("/endpoint");
});
```

```python
# Python calls .NET service (reads connection string from environment)
import os
import httpx

dotnet_url = os.getenv("ConnectionStrings__api")  # Injected by Aspire
async with httpx.AsyncClient() as client:
    response = await client.get(f"{dotnet_url}/endpoint")
```

**Shared Infrastructure:**

All services access databases, caches, queues via connection strings injected by AppHost—language-agnostic.

**Learn more:** [Service discovery](https://learn.microsoft.com/dotnet/aspire/service-discovery/overview), [Python integration](https://learn.microsoft.com/dotnet/aspire/get-started/build-aspire-apps-with-python), [Node.js integration](https://learn.microsoft.com/dotnet/aspire/get-started/build-aspire-apps-with-nodejs).

## Resources

**Production Guidance:**
- [Deployment Overview](https://learn.microsoft.com/dotnet/aspire/deployment/overview)
- [Azure Deployment Guide](https://learn.microsoft.com/dotnet/aspire/deployment/azure/aca-deployment)
- [Security Best Practices](https://learn.microsoft.com/dotnet/aspire/security/overview)
- [Monitoring & Observability](https://learn.microsoft.com/dotnet/aspire/fundamentals/dashboard)

**Advanced Topics:**
- [Testing Strategies](https://learn.microsoft.com/dotnet/aspire/fundamentals/testing)
- [Performance Tuning](https://learn.microsoft.com/dotnet/aspire/fundamentals/performance)
- [Multi-Region Deployment](https://learn.microsoft.com/azure/container-apps/disaster-recovery)

Use these patterns to build robust, scalable, production-ready Aspire applications.
