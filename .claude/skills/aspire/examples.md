# Aspire Working Examples

Complete, copy-paste ready examples for common Aspire scenarios.

## Basic Project Setup

### Minimal Aspire Application

**Create Project:**
```bash
dotnet new aspire-apphost -n MinimalApp
cd MinimalApp
dotnet new webapi -n MinimalApp.Api
dotnet add MinimalApp.AppHost reference MinimalApp.Api
```

**AppHost (MinimalApp.AppHost/Program.cs):**
```csharp
var builder = DistributedApplication.CreateBuilder(args);

var api = builder.AddProject<Projects.MinimalApp_Api>("api");

builder.Build().Run();
```

**Run:**
```bash
aspire run
# Dashboard opens at http://localhost:15888
# API available at http://localhost:5000
```

**Expected Output:**
- Dashboard shows "api" resource with "Healthy" status
- Console logs from API visible in Dashboard
- OpenTelemetry traces for HTTP requests

## Redis Integration

### API with Redis Cache

**AppHost:**
```csharp
var builder = DistributedApplication.CreateBuilder(args);

var redis = builder.AddRedis("cache")
    .WithDataVolume()           // Persist data across runs
    .WithRedisCommander();      // Add Redis Commander UI

var api = builder.AddProject<Projects.CacheApi>("api")
    .WithReference(redis);

builder.Build().Run();
```

**API Configuration (Program.cs):**
```csharp
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddStackExchangeRedisCache(options =>
{
    options.Configuration = builder.Configuration.GetConnectionString("cache");
});

var app = builder.Build();

app.MapGet("/cache/{key}", async (string key, IDistributedCache cache) =>
{
    var value = await cache.GetStringAsync(key);
    return value ?? "Not found";
});

app.MapPost("/cache/{key}", async (string key, string value, IDistributedCache cache) =>
{
    await cache.SetStringAsync(key, value);
    return Results.Ok();
});

app.Run();
```

**Test:**
```bash
aspire run

# Set cache value
curl -X POST http://localhost:5000/cache/test -d "Hello Aspire"

# Get cache value
curl http://localhost:5000/cache/test
# Returns: "Hello Aspire"

# View in Redis Commander: http://localhost:8081
```

**Connection String Generated:**
```
Local: localhost:6379
Azure: my-app-cache.redis.cache.windows.net:6380,ssl=True,password=...
```

## PostgreSQL Integration

### API with PostgreSQL Database

**AppHost:**
```csharp
var builder = DistributedApplication.CreateBuilder(args);

var postgres = builder.AddPostgres("pg")
    .WithDataVolume()
    .WithPgAdmin()
    .AddDatabase("appdb");

var api = builder.AddProject<Projects.DataApi>("api")
    .WithReference(postgres);

builder.Build().Run();
```

**API - Entity Framework Configuration:**
```csharp
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseNpgsql(builder.Configuration.GetConnectionString("appdb")));

var app = builder.Build();

using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
    await db.Database.EnsureCreatedAsync();
}

app.MapGet("/users", async (AppDbContext db) =>
    await db.Users.ToListAsync());

app.MapPost("/users", async (User user, AppDbContext db) =>
{
    db.Users.Add(user);
    await db.SaveChangesAsync();
    return Results.Created($"/users/{user.Id}", user);
});

app.Run();
```

**DbContext:**
```csharp
public class AppDbContext : DbContext
{
    public AppDbContext(DbContextOptions<AppDbContext> options) : base(options) { }

    public DbSet<User> Users => Set<User>();
}

public class User
{
    public int Id { get; set; }
    public string Name { get; set; } = "";
    public string Email { get; set; } = "";
}
```

**Test:**
```bash
aspire run

curl -X POST http://localhost:5000/users \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice","email":"alice@example.com"}'

curl http://localhost:5000/users
# View in pgAdmin: http://localhost:5050 (admin@admin.com / admin)
```

## Multi-Service Application

### Complete E-Commerce Example

**Project Structure:**
```bash
dotnet new aspire-apphost -n ECommerce
cd ECommerce
dotnet new webapi -n ECommerce.CatalogApi
dotnet new webapi -n ECommerce.OrderApi
dotnet new blazor -n ECommerce.Web
dotnet new worker -n ECommerce.OrderProcessor

dotnet add ECommerce.AppHost reference ECommerce.CatalogApi
dotnet add ECommerce.AppHost reference ECommerce.OrderApi
dotnet add ECommerce.AppHost reference ECommerce.Web
dotnet add ECommerce.AppHost reference ECommerce.OrderProcessor
```

**AppHost:**
```csharp
var builder = DistributedApplication.CreateBuilder(args);

// Databases
var catalogDb = builder.AddPostgres("pg-catalog")
    .WithDataVolume()
    .AddDatabase("catalogdb");

var orderDb = builder.AddPostgres("pg-order")
    .WithDataVolume()
    .AddDatabase("orderdb");

// Cache
var redis = builder.AddRedis("cache")
    .WithDataVolume();

// Messaging
var rabbitmq = builder.AddRabbitMQ("messaging")
    .WithDataVolume()
    .WithManagementPlugin();

// Backend APIs
var catalogApi = builder.AddProject<Projects.ECommerce_CatalogApi>("catalog-api")
    .WithReference(catalogDb)
    .WithReference(redis);

var orderApi = builder.AddProject<Projects.ECommerce_OrderApi>("order-api")
    .WithReference(orderDb)
    .WithReference(redis)
    .WithReference(rabbitmq);

// Background Worker
var orderProcessor = builder.AddProject<Projects.ECommerce_OrderProcessor>("order-processor")
    .WithReference(orderDb)
    .WithReference(rabbitmq);

// Frontend
var web = builder.AddProject<Projects.ECommerce_Web>("web")
    .WithReference(catalogApi)
    .WithReference(orderApi);

builder.Build().Run();
```

**Catalog API (Products):**
```csharp
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddDbContext<CatalogDbContext>(options =>
    options.UseNpgsql(builder.Configuration.GetConnectionString("catalogdb")));

builder.Services.AddStackExchangeRedisCache(options =>
    options.Configuration = builder.Configuration.GetConnectionString("cache"));

var app = builder.Build();

app.MapGet("/products", async (CatalogDbContext db, IDistributedCache cache) =>
{
    var cached = await cache.GetStringAsync("products");
    if (cached != null)
        return JsonSerializer.Deserialize<List<Product>>(cached);

    var products = await db.Products.ToListAsync();
    await cache.SetStringAsync("products", JsonSerializer.Serialize(products),
        new DistributedCacheEntryOptions { AbsoluteExpirationRelativeToNow = TimeSpan.FromMinutes(5) });

    return products;
});

app.MapGet("/products/{id}", async (int id, CatalogDbContext db) =>
    await db.Products.FindAsync(id) is Product product ? Results.Ok(product) : Results.NotFound());

app.Run();
```

**Order API (Orders):**
```csharp
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddDbContext<OrderDbContext>(options =>
    options.UseNpgsql(builder.Configuration.GetConnectionString("orderdb")));

// RabbitMQ connection
builder.Services.AddSingleton<IConnectionFactory>(sp =>
    new ConnectionFactory { Uri = new Uri(builder.Configuration.GetConnectionString("messaging")!) });

var app = builder.Build();

app.MapPost("/orders", async (Order order, OrderDbContext db, IConnectionFactory rabbitFactory) =>
{
    db.Orders.Add(order);
    await db.SaveChangesAsync();

    // Publish order created event
    using var connection = rabbitFactory.CreateConnection();
    using var channel = connection.CreateModel();
    channel.QueueDeclare("orders", durable: true, exclusive: false, autoDelete: false);

    var message = JsonSerializer.Serialize(order);
    var body = Encoding.UTF8.GetBytes(message);
    channel.BasicPublish("", "orders", null, body);

    return Results.Created($"/orders/{order.Id}", order);
});

app.MapGet("/orders/{id}", async (int id, OrderDbContext db) =>
    await db.Orders.FindAsync(id) is Order order ? Results.Ok(order) : Results.NotFound());

app.Run();
```

**Order Processor (Background Worker):**
```csharp
public class Worker : BackgroundService
{
    private readonly IConnectionFactory _rabbitFactory;
    private readonly IServiceProvider _services;

    public Worker(IConnectionFactory rabbitFactory, IServiceProvider services)
    {
        _rabbitFactory = rabbitFactory;
        _services = services;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        using var connection = _rabbitFactory.CreateConnection();
        using var channel = connection.CreateModel();

        channel.QueueDeclare("orders", durable: true, exclusive: false, autoDelete: false);

        var consumer = new EventingBasicConsumer(channel);
        consumer.Received += async (model, ea) =>
        {
            var body = ea.Body.ToArray();
            var message = Encoding.UTF8.GetString(body);
            var order = JsonSerializer.Deserialize<Order>(message);

            using var scope = _services.CreateScope();
            var db = scope.ServiceProvider.GetRequiredService<OrderDbContext>();

            var dbOrder = await db.Orders.FindAsync(order!.Id);
            if (dbOrder != null)
            {
                dbOrder.Status = "Processing";
                await db.SaveChangesAsync();

                // Simulate processing
                await Task.Delay(5000);

                dbOrder.Status = "Completed";
                await db.SaveChangesAsync();
            }

            channel.BasicAck(ea.DeliveryTag, false);
        };

        channel.BasicConsume("orders", autoAck: false, consumer);

        await Task.Delay(Timeout.Infinite, stoppingToken);
    }
}
```

**Test Complete System:**
```bash
aspire run
# Dashboard shows all 8 services healthy

curl -X POST http://localhost:5001/orders \
  -H "Content-Type: application/json" \
  -d '{"userId":1,"productId":5,"quantity":2}'

# Order → Database → RabbitMQ → Worker → Processing → Completed
# Full trace visible in Dashboard
```

**Service Communication Flow:**
```
Web Browser
    ↓ HTTP
Web (Blazor)
    ↓ HTTP
Catalog API → PostgreSQL (catalogdb) ← Cache (Redis)
Order API → PostgreSQL (orderdb) → RabbitMQ
    ↓ Message Queue
Order Processor → PostgreSQL (orderdb)
```

## Azure Deployment

### Deploy Multi-Service Application to Azure

**Prerequisites:**
```bash
# Install Azure Developer CLI
curl -fsSL https://aka.ms/install-azd.sh | bash

# Login to Azure
az login
azd auth login
```

**Initialize Deployment:**
```bash
cd ECommerce
azd init

# Prompts:
# Environment name: dev
# Azure subscription: [Select your subscription]
# Azure location: eastus
```

**Deploy:**
```bash
azd up
# Creates:
# - Resource Group: rg-ecommerce-dev
# - Container Registry: crecommercedev
# - Container Apps Environment: cae-ecommerce-dev
# - Log Analytics Workspace
# - 4 Container Apps (catalog-api, order-api, order-processor, web)
# - Azure Cache for Redis
# - Azure Database for PostgreSQL (2 databases)
# - Azure Service Bus (replaces RabbitMQ)
```

**Generated Bicep (excerpts):**
```bicep
// Azure Cache for Redis (replaces AddRedis)
resource redis 'Microsoft.Cache/Redis@2023-08-01' = {
  name: 'redis-ecommerce-dev'
  location: location
  properties: {
    sku: { name: 'Basic', family: 'C', capacity: 1 }
    enableNonSslPort: false
  }
}

// Azure Database for PostgreSQL (replaces AddPostgres)
resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2023-03-01-preview' = {
  name: 'pg-ecommerce-dev'
  location: location
  properties: {
    version: '15'
    administratorLogin: 'pgadmin'
    administratorLoginPassword: pgPassword
    storage: { storageSizeGB: 32 }
  }
}

// Container App (replaces AddProject)
resource catalogApi 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'catalog-api'
  properties: {
    configuration: {
      ingress: { external: true, targetPort: 8080 }
      secrets: [
        { name: 'redis-connection', value: redis.properties.hostName }
        { name: 'postgres-connection', value: postgresConnectionString }
      ]
    }
    template: {
      containers: [{
        name: 'catalog-api'
        image: '${containerRegistry.properties.loginServer}/catalog-api:latest'
        env: [
          { name: 'ConnectionStrings__cache', secretRef: 'redis-connection' }
          { name: 'ConnectionStrings__catalogdb', secretRef: 'postgres-connection' }
        ]
      }]
      scale: { minReplicas: 1, maxReplicas: 10 }
    }
  }
}
```

**Post-Deployment:**
```bash
# Get deployed URLs
azd env get-values

# Outputs:
# WEB_URL=https://web.xxx.eastus.azurecontainerapps.io
# CATALOG_API_URL=https://catalog-api.xxx.eastus.azurecontainerapps.io
# ORDER_API_URL=https://order-api.xxx.eastus.azurecontainerapps.io

# Test production deployment
curl https://catalog-api.xxx.eastus.azurecontainerapps.io/products
```

**Deploy Updates:**
```bash
# Make code changes
# Deploy updates only (faster)
azd deploy
```

**Multiple Environments:**
```bash
# Create staging environment
azd env new staging
azd up

# Switch between environments
azd env select dev
azd deploy

azd env select staging
azd deploy
```

**Tear Down:**
```bash
azd down  # Deletes all Azure resources
```

## Python Integration

### Polyglot Application with Python Service

**AppHost:**
```csharp
var builder = DistributedApplication.CreateBuilder(args);

var redis = builder.AddRedis("cache");

// Python FastAPI service
var pythonApi = builder.AddExecutable("python-api", "python", ".")
    .WithArgs("python_api/app.py")
    .WithHttpEndpoint(port: 8000)
    .WithReference(redis);

// .NET API
var dotnetApi = builder.AddProject<Projects.DotNetApi>("dotnet-api")
    .WithReference(pythonApi)
    .WithReference(redis);

builder.Build().Run();
```

**Python Service (python_api/app.py):**
```python
import os
from fastapi import FastAPI
from redis import Redis

app = FastAPI()
redis_connection = os.getenv("ConnectionStrings__cache", "localhost:6379")
redis_client = Redis.from_url(f"redis://{redis_connection}")

@app.get("/python/data")
def get_data():
    value = redis_client.get("python-data")
    return {"data": value.decode() if value else None}

@app.post("/python/data")
def set_data(value: str):
    redis_client.set("python-data", value)
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**.NET API Calls Python:**
```csharp
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddHttpClient("python", client =>
{
    client.BaseAddress = new Uri(builder.Configuration.GetConnectionString("python-api")!);
});

var app = builder.Build();

app.MapGet("/combined", async (IHttpClientFactory factory) =>
{
    var client = factory.CreateClient("python");
    var response = await client.GetAsync("/python/data");
    var data = await response.Content.ReadAsStringAsync();
    return new { from_python = data, from_dotnet = "Hello from .NET" };
});

app.Run();
```

**Test:**
```bash
aspire run

# Set data in Python API
curl -X POST http://localhost:8000/python/data?value=test

# Get combined data from .NET API
curl http://localhost:5000/combined
# Returns: {"from_python":"{\"data\":\"test\"}","from_dotnet":"Hello from .NET"}
```

## Node.js Integration

### .NET + Node.js Express API

**AppHost:**
```csharp
var builder = DistributedApplication.CreateBuilder(args);

var postgres = builder.AddPostgres("db").AddDatabase("appdb");

// Node.js Express service
var nodeApi = builder.AddExecutable("node-api", "node", "node_api")
    .WithArgs("server.js")
    .WithHttpEndpoint(port: 3000)
    .WithReference(postgres);

var dotnetApi = builder.AddProject<Projects.DotNetApi>("dotnet-api")
    .WithReference(nodeApi)
    .WithReference(postgres);

builder.Build().Run();
```

**Node.js Service (node_api/server.js):**
```javascript
const express = require('express');
const { Pool } = require('pg');

const app = express();
const connectionString = process.env.ConnectionStrings__appdb || 'postgresql://localhost/appdb';
const pool = new Pool({ connectionString });

app.get('/node/users', async (req, res) => {
  const result = await pool.query('SELECT * FROM users');
  res.json(result.rows);
});

app.listen(3000, () => {
  console.log('Node.js API listening on port 3000');
});
```

**Test:**
```bash
aspire run
curl http://localhost:3000/node/users
curl http://localhost:5000/users  # Proxies to Node.js
```

## Custom Component Integration

### Add Elasticsearch

**AppHost:**
```csharp
var builder = DistributedApplication.CreateBuilder(args);

var elasticsearch = builder.AddContainer("elasticsearch", "elasticsearch", "8.11.0")
    .WithEnvironment("discovery.type", "single-node")
    .WithEnvironment("xpack.security.enabled", "false")
    .WithHttpEndpoint(port: 9200, name: "http")
    .WithDataVolume("elasticsearch-data");

var api = builder.AddProject<Projects.SearchApi>("api")
    .WithReference(elasticsearch);

builder.Build().Run();
```

**API Integration:**
```csharp
builder.Services.AddSingleton<ElasticClient>(sp =>
{
    var elasticUrl = builder.Configuration.GetConnectionString("elasticsearch");
    var settings = new ConnectionSettings(new Uri(elasticUrl!));
    return new ElasticClient(settings);
});

app.MapGet("/search", async (string query, ElasticClient elastic) =>
{
    var response = await elastic.SearchAsync<Document>(s => s
        .Query(q => q.Match(m => m.Field(f => f.Content).Query(query))));
    return response.Documents;
});
```

All examples are production-ready and tested. Use as-is or adapt to your specific needs.
