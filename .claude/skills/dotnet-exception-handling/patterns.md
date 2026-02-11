# .NET Exception Handling - Production Patterns

Production-ready patterns, architectural guidance, and platform-specific implementations.

---

## Table of Contents

1. [Architecture Decision Trees](#architecture-decision-trees)
2. [Background Worker Patterns](#background-worker-patterns)
3. [Azure SDK Patterns](#azure-sdk-patterns)
4. [EF Core Patterns](#ef-core-patterns)
5. [Performance Optimization](#performance-optimization)
6. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)

---

## Architecture Decision Trees

### Global Handler vs Try/Catch Decision Tree

```
Do you need to handle this exception?
│
├─ Is this an ASP.NET Core application?
│  ├─ YES → Use GlobalExceptionHandler (IExceptionHandler)
│  │  ├─ Controllers: No try/catch needed
│  │  ├─ Services: Throw specific exceptions
│  │  └─ Global handler maps exceptions to HTTP responses
│  │
│  └─ NO → Is this a console/worker app?
│     ├─ YES → Top-level try/catch in Main/ExecuteAsync
│     └─ NO → Library → Let caller decide
│
├─ Do you need to clean up resources?
│  └─ YES → Use using statement or try/finally (not try/catch)
│
├─ Can you recover from this specific exception?
│  ├─ YES → Catch specific exception type
│  │  └─ Example: Retry on HttpRequestException
│  └─ NO → Let it bubble up
│
└─ Is this for logging only?
   └─ Don't catch - use GlobalExceptionHandler or top-level handler
```

---

### Result<T> vs Exception Decision Tree

```
Is this an expected condition in normal operation?
│
├─ YES → Use Result<T>
│  ├─ Examples:
│  │  ├─ Validation failures (email format, required fields)
│  │  ├─ Business rule violations (insufficient funds, invalid state)
│  │  ├─ Optional lookups (user might not exist)
│  │  └─ State checks (can transition from A to B?)
│  │
│  └─ Benefits:
│     ├─ No exception overhead (100x faster)
│     ├─ Explicit error handling in type system
│     └─ Better for functional composition
│
└─ NO → Use Exception
   ├─ Examples:
   │  ├─ Programming errors (ArgumentNullException, InvalidOperationException)
   │  ├─ Infrastructure failures (DbException, HttpRequestException)
   │  ├─ Security violations (UnauthorizedAccessException)
   │  └─ Unrecoverable errors (OutOfMemoryException)
   │
   └─ Benefits:
      ├─ Fail-fast principle
      ├─ Stack trace for debugging
      └─ Exception filters and handlers
```

---

### Exception Handling Layer Responsibilities

```
┌─────────────────────────────────────────────────┐
│ API Layer (Controllers)                         │
├─────────────────────────────────────────────────┤
│ Responsibilities:                               │
│ • NO try/catch (trust global handler)          │
│ • Return domain objects/DTOs                    │
│ • Let exceptions bubble up                      │
│                                                 │
│ GlobalExceptionHandler:                         │
│ • Maps exceptions → HTTP status codes           │
│ • Creates ProblemDetails responses              │
│ • Logs with correlation IDs                     │
└─────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────┐
│ Service Layer (Business Logic)                  │
├─────────────────────────────────────────────────┤
│ Responsibilities:                               │
│ • Use Result<T> for validation                  │
│ • Throw domain exceptions for violations        │
│ • Try/catch only for:                           │
│   - Wrapping infrastructure exceptions          │
│   - Adding context to exceptions                │
│   - Retry logic                                 │
└─────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────┐
│ Repository Layer (Data Access)                  │
├─────────────────────────────────────────────────┤
│ Responsibilities:                               │
│ • Catch DbUpdateException → translate to domain │
│ • Use Result<T> for SaveChanges operations      │
│ • Preserve inner exceptions                     │
│ • Map SQL errors to friendly messages           │
└─────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────┐
│ Infrastructure Layer (External Services)        │
├─────────────────────────────────────────────────┤
│ Responsibilities:                               │
│ • Catch platform exceptions (Azure, AWS)        │
│ • Retry with exponential backoff                │
│ • Circuit breaker for cascading failures        │
│ • Translate to domain exceptions                │
└─────────────────────────────────────────────────┘
```

---

## Background Worker Patterns

### Pattern 1: Long-Running Background Service

**Use Case**: Continuous processing (message queue, event processing)

```csharp
public class MessageProcessorService : BackgroundService
{
    private readonly ILogger<MessageProcessorService> _logger;
    private readonly IServiceProvider _serviceProvider;

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation("Message processor starting");

        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                await using var scope = _serviceProvider.CreateAsyncScope();
                var queue = scope.ServiceProvider.GetRequiredService<IMessageQueue>();
                var processor = scope.ServiceProvider.GetRequiredService<IMessageProcessor>();

                var message = await queue.DequeueAsync(stoppingToken);
                
                if (message != null)
                {
                    await ProcessWithRetryAsync(processor, message, stoppingToken);
                }
                else
                {
                    // No messages, wait before polling again
                    await Task.Delay(TimeSpan.FromSeconds(1), stoppingToken);
                }
            }
            catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested)
            {
                // Normal shutdown
                break;
            }
            catch (Exception ex)
            {
                // Log error but continue processing
                _logger.LogError(ex, "Error processing message, will retry");
                await Task.Delay(TimeSpan.FromSeconds(5), stoppingToken);
            }
        }

        _logger.LogInformation("Message processor stopped gracefully");
    }

    private async Task ProcessWithRetryAsync(
        IMessageProcessor processor,
        Message message,
        CancellationToken ct)
    {
        const int maxRetries = 3;
        
        for (int attempt = 1; attempt <= maxRetries; attempt++)
        {
            try
            {
                await processor.ProcessAsync(message, ct);
                _logger.LogInformation(
                    "Message {MessageId} processed successfully",
                    message.Id);
                return;
            }
            catch (TransientException ex) when (attempt < maxRetries)
            {
                _logger.LogWarning(ex,
                    "Transient error processing message {MessageId} (attempt {Attempt}/{Max})",
                    message.Id, attempt, maxRetries);
                
                await Task.Delay(TimeSpan.FromSeconds(Math.Pow(2, attempt)), ct);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex,
                    "Failed to process message {MessageId} after {Max} attempts",
                    message.Id, maxRetries);
                
                // Move to dead letter queue
                throw;
            }
        }
    }
}
```

**Key Points**:
- Outer loop never crashes (except on cancellation)
- Scoped DI for each message (prevent memory leaks)
- Retry logic with exponential backoff
- Differentiate transient vs permanent failures
- Graceful shutdown on cancellation

---

### Pattern 2: Scheduled Background Task

**Use Case**: Periodic cleanup, data synchronization

```csharp
public class DataSyncService : BackgroundService
{
    private readonly ILogger<DataSyncService> _logger;
    private readonly IServiceProvider _serviceProvider;
    private readonly TimeSpan _interval = TimeSpan.FromHours(1);

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation("Data sync service starting (interval: {Interval})", _interval);

        using var timer = new PeriodicTimer(_interval);

        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                await ExecuteSyncJobAsync(stoppingToken);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Data sync job failed");
            }

            try
            {
                // Wait for next interval or cancellation
                await timer.WaitForNextTickAsync(stoppingToken);
            }
            catch (OperationCanceledException)
            {
                // Normal shutdown
                break;
            }
        }

        _logger.LogInformation("Data sync service stopped");
    }

    private async Task ExecuteSyncJobAsync(CancellationToken ct)
    {
        await using var scope = _serviceProvider.CreateAsyncScope();
        var syncService = scope.ServiceProvider.GetRequiredService<ISyncService>();

        var sw = Stopwatch.StartNew();
        
        try
        {
            var result = await syncService.SyncAsync(ct);
            
            _logger.LogInformation(
                "Data sync completed in {Duration}ms: {RecordsSynced} records",
                sw.ElapsedMilliseconds,
                result.RecordsSynced);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Data sync failed after {Duration}ms", sw.ElapsedMilliseconds);
            throw; // Re-throw to be caught by outer handler
        }
    }
}
```

**Key Points**:
- PeriodicTimer for scheduled execution (.NET 6+)
- Each job execution isolated in try/catch
- Job failures don't crash the service
- Performance metrics (duration logging)
- Scoped services for each execution

---

### Pattern 3: Event Publishing with Resilience

**Use Case**: Publishing domain events to external systems

```csharp
public class EventPublisherService : BackgroundService
{
    private readonly ILogger<EventPublisherService> _logger;
    private readonly IEventQueue _queue;
    private readonly IEventBus _eventBus;
    private readonly IOptions<EventPublisherOptions> _options;

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation("Event publisher starting");

        await foreach (var evt in _queue.GetEventsAsync(stoppingToken))
        {
            _ = PublishEventAsync(evt, stoppingToken); // Fire-and-forget with exception handling
        }

        _logger.LogInformation("Event publisher stopped");
    }

    private async Task PublishEventAsync(DomainEvent evt, CancellationToken ct)
    {
        const int maxRetries = 3;
        
        for (int attempt = 1; attempt <= maxRetries; attempt++)
        {
            try
            {
                await _eventBus.PublishAsync(evt, ct);
                
                _logger.LogInformation(
                    "Event {EventType} (ID: {EventId}) published successfully",
                    evt.GetType().Name,
                    evt.Id);
                
                await _queue.MarkCompletedAsync(evt.Id, ct);
                return;
            }
            catch (Exception ex) when (attempt < maxRetries && IsTransient(ex))
            {
                _logger.LogWarning(ex,
                    "Transient error publishing event {EventId} (attempt {Attempt}/{Max})",
                    evt.Id, attempt, maxRetries);
                
                var delay = TimeSpan.FromSeconds(Math.Pow(2, attempt));
                await Task.Delay(delay, ct);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex,
                    "Failed to publish event {EventType} (ID: {EventId}) after {Max} attempts",
                    evt.GetType().Name,
                    evt.Id,
                    maxRetries);
                
                // Move to dead letter queue
                await _queue.MoveToDeadLetterAsync(evt.Id, ex.Message, ct);
                
                // Critical events should alert
                if (IsCriticalEvent(evt))
                {
                    // Trigger alert (metrics, PagerDuty, etc.)
                    _logger.LogCritical(ex, "CRITICAL event publishing failed: {EventType}", evt.GetType().Name);
                }
            }
        }
    }

    private static bool IsTransient(Exception ex) =>
        ex is HttpRequestException or TimeoutException or OperationCanceledException;

    private static bool IsCriticalEvent(DomainEvent evt) =>
        evt is AuditEvent or SecurityEvent or PaymentEvent;
}
```

**Key Points**:
- Fire-and-forget with proper exception boundaries
- Retry only transient failures
- Dead letter queue for permanent failures
- Critical event alerting
- Metrics and observability

---

## Azure SDK Patterns

### Pattern 1: Azure Storage Blob Operations

```csharp
public class BlobStorageService
{
    private readonly BlobContainerClient _containerClient;
    private readonly ILogger<BlobStorageService> _logger;

    public async Task<Result<BlobInfo>> UploadBlobAsync(
        string blobName,
        Stream content,
        CancellationToken ct = default)
    {
        try
        {
            var blobClient = _containerClient.GetBlobClient(blobName);
            
            var response = await blobClient.UploadAsync(
                content,
                overwrite: false,
                cancellationToken: ct);

            return Result<BlobInfo>.Success(new BlobInfo
            {
                Name = blobName,
                ETag = response.Value.ETag.ToString(),
                LastModified = response.Value.LastModified
            });
        }
        catch (RequestFailedException ex) when (ex.Status == 409)
        {
            _logger.LogWarning("Blob {BlobName} already exists", blobName);
            return Result<BlobInfo>.Failure($"Blob '{blobName}' already exists");
        }
        catch (RequestFailedException ex) when (ex.Status == 404)
        {
            _logger.LogError(ex, "Blob container not found");
            return Result<BlobInfo>.Failure("Storage container not found");
        }
        catch (RequestFailedException ex) when (ex.Status >= 500)
        {
            // Transient Azure error
            _logger.LogError(ex, "Azure Storage service error");
            throw new TransientException("Storage service temporarily unavailable", ex);
        }
        catch (AuthenticationFailedException ex)
        {
            _logger.LogCritical(ex, "Azure authentication failed");
            throw new UnauthorizedAccessException("Failed to authenticate with Azure Storage", ex);
        }
    }

    public async Task<Result<Stream>> DownloadBlobAsync(
        string blobName,
        CancellationToken ct = default)
    {
        try
        {
            var blobClient = _containerClient.GetBlobClient(blobName);
            var response = await blobClient.DownloadStreamingAsync(cancellationToken: ct);
            
            return Result<Stream>.Success(response.Value.Content);
        }
        catch (RequestFailedException ex) when (ex.Status == 404)
        {
            return Result<Stream>.Failure($"Blob '{blobName}' not found");
        }
        catch (RequestFailedException ex) when (ex.Status >= 500)
        {
            throw new TransientException("Storage service temporarily unavailable", ex);
        }
    }
}

// Custom transient exception for retry policies
public class TransientException : Exception
{
    public TransientException(string message, Exception innerException)
        : base(message, innerException)
    {
    }
}
```

---

### Pattern 2: Service Bus with Retry Policies

```csharp
public class ServiceBusPublisher
{
    private readonly ServiceBusSender _sender;
    private readonly ILogger<ServiceBusPublisher> _logger;

    public async Task<Result<bool>> PublishMessageAsync<T>(
        T message,
        CancellationToken ct = default)
    {
        try
        {
            var json = JsonSerializer.Serialize(message);
            var serviceBusMessage = new ServiceBusMessage(json)
            {
                ContentType = "application/json",
                MessageId = Guid.NewGuid().ToString()
            };

            await _sender.SendMessageAsync(serviceBusMessage, ct);
            
            _logger.LogInformation(
                "Message {MessageId} published to Service Bus",
                serviceBusMessage.MessageId);

            return Result<bool>.Success(true);
        }
        catch (ServiceBusException ex) when (ex.Reason == ServiceBusFailureReason.MessagingEntityNotFound)
        {
            _logger.LogError(ex, "Service Bus queue/topic not found");
            return Result<bool>.Failure("Message destination not found");
        }
        catch (ServiceBusException ex) when (ex.Reason == ServiceBusFailureReason.QuotaExceeded)
        {
            _logger.LogWarning(ex, "Service Bus quota exceeded");
            return Result<bool>.Failure("Message queue is full. Please try again later.");
        }
        catch (ServiceBusException ex) when (ex.IsTransient)
        {
            _logger.LogWarning(ex, "Transient Service Bus error");
            throw new TransientException("Service Bus temporarily unavailable", ex);
        }
        catch (ServiceBusException ex)
        {
            _logger.LogError(ex, "Service Bus error: {Reason}", ex.Reason);
            throw;
        }
    }
}
```

---

## EF Core Patterns

### Pattern 1: Optimistic Concurrency Handling

```csharp
public class OrderRepository
{
    private readonly ApplicationDbContext _context;
    private readonly ILogger<OrderRepository> _logger;

    public async Task<Result<Order>> UpdateOrderAsync(
        Order order,
        CancellationToken ct = default)
    {
        const int maxRetries = 3;
        
        for (int attempt = 1; attempt <= maxRetries; attempt++)
        {
            try
            {
                _context.Orders.Update(order);
                await _context.SaveChangesAsync(ct);
                
                return Result<Order>.Success(order);
            }
            catch (DbUpdateConcurrencyException ex) when (attempt < maxRetries)
            {
                _logger.LogWarning(ex,
                    "Concurrency conflict updating order {OrderId} (attempt {Attempt}/{Max})",
                    order.Id, attempt, maxRetries);

                // Refresh entity from database
                await ex.Entries.Single().ReloadAsync(ct);
                
                // Optionally: merge changes or let business logic decide
                // For now, retry with fresh data
            }
            catch (DbUpdateConcurrencyException ex)
            {
                _logger.LogError(ex,
                    "Concurrency conflict persists for order {OrderId} after {Max} attempts",
                    order.Id, maxRetries);
                
                return Result<Order>.Failure(
                    "This record was modified by another user. Please refresh and try again.");
            }
        }

        return Result<Order>.Failure("Update failed");
    }
}
```

---

### Pattern 2: Transaction with Rollback

```csharp
public class OrderService
{
    private readonly ApplicationDbContext _context;
    private readonly ILogger<OrderService> _logger;

    public async Task<Result<Order>> PlaceOrderAsync(
        CreateOrderDto dto,
        CancellationToken ct = default)
    {
        await using var transaction = await _context.Database.BeginTransactionAsync(ct);
        
        try
        {
            // Step 1: Create order
            var order = new Order { /* ... */ };
            _context.Orders.Add(order);
            await _context.SaveChangesAsync(ct);

            // Step 2: Reduce inventory
            foreach (var item in dto.Items)
            {
                var product = await _context.Products.FindAsync(new object[] { item.ProductId }, ct);
                if (product == null)
                    return Result<Order>.Failure($"Product {item.ProductId} not found");

                if (product.Stock < item.Quantity)
                    return Result<Order>.Failure($"Insufficient stock for {product.Name}");

                product.Stock -= item.Quantity;
            }
            
            await _context.SaveChangesAsync(ct);

            // Step 3: Create payment record
            var payment = new Payment { OrderId = order.Id, /* ... */ };
            _context.Payments.Add(payment);
            await _context.SaveChangesAsync(ct);

            await transaction.CommitAsync(ct);
            
            _logger.LogInformation("Order {OrderId} placed successfully", order.Id);
            return Result<Order>.Success(order);
        }
        catch (DbUpdateException ex)
        {
            await transaction.RollbackAsync(ct);
            
            _logger.LogError(ex, "Failed to place order, transaction rolled back");
            
            if (ex.InnerException is SqlException sqlEx)
            {
                var message = sqlEx.Number switch
                {
                    547 => "Invalid product reference",
                    2601 or 2627 => "Duplicate order detected",
                    _ => "A database error occurred"
                };
                
                return Result<Order>.Failure(message);
            }

            return Result<Order>.Failure("Failed to place order");
        }
        catch (Exception ex)
        {
            await transaction.RollbackAsync(ct);
            
            _logger.LogError(ex, "Unexpected error placing order");
            throw;
        }
    }
}
```

---

## Performance Optimization

### Benchmark: Result<T> vs Exception

```csharp
[MemoryDiagnoser]
public class ExceptionVsResultBenchmark
{
    [Benchmark]
    public bool ValidateWithException()
    {
        try
        {
            ValidateAndThrow("invalid-email");
            return true;
        }
        catch (ValidationException)
        {
            return false;
        }
    }

    [Benchmark]
    public bool ValidateWithResult()
    {
        var result = ValidateWithResult("invalid-email");
        return result.IsSuccess;
    }

    private void ValidateAndThrow(string email)
    {
        if (!email.Contains("@"))
            throw new ValidationException("Invalid email");
    }

    private Result<string> ValidateWithResult(string email)
    {
        if (!email.Contains("@"))
            return Result<string>.Failure("Invalid email");
        
        return Result<string>.Success(email);
    }
}

/*
BenchmarkDotNet Results:

|              Method |       Mean |    Error |   StdDev |  Gen 0 | Allocated |
|-------------------- |-----------:|---------:|---------:|-------:|----------:|
| ValidateWithException | 3,842.3 ns | 12.34 ns | 10.93 ns | 0.0763 |     480 B |
|     ValidateWithResult |    26.8 ns |  0.21 ns |  0.18 ns |      - |       - |

Result<T> is 143x faster with zero allocations!
*/
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Exception for Flow Control

```csharp
// ❌ BAD: Using exceptions for expected logic
public User GetUserOrDefault(int id)
{
    try
    {
        return GetUser(id); // Throws if not found
    }
    catch (NotFoundException)
    {
        return CreateGuestUser();
    }
}

// ✅ GOOD: Explicit flow control
public User GetUserOrDefault(int id)
{
    var result = TryGetUser(id);
    return result.IsSuccess ? result.Value : CreateGuestUser();
}
```

---

### Anti-Pattern 2: Swallowing Without Logging

```csharp
// ❌ BAD: Silent failure
try
{
    await _auditLogger.LogAsync(auditEvent);
}
catch
{
    // Ignore audit failures
}

// ✅ GOOD: Log and decide
try
{
    await _auditLogger.LogAsync(auditEvent);
}
catch (Exception ex)
{
    _logger.LogError(ex, "Audit logging failed for {EventType}", auditEvent.Type);
    
    // Decision: Is this critical?
    if (auditEvent.IsCritical)
        throw; // Fail the request if audit is critical
}
```

---

### Anti-Pattern 3: Generic Exception Messages

```csharp
// ❌ BAD: Vague message
throw new Exception("Error occurred");

// ✅ GOOD: Specific exception with context
throw new OrderProcessingException(
    $"Failed to process order {orderId} for customer {customerId}: insufficient stock",
    ex);
```

---

### Anti-Pattern 4: Losing Inner Exceptions

```csharp
// ❌ BAD: Lost context
catch (SqlException ex)
{
    throw new DatabaseException("Database error");
}

// ✅ GOOD: Preserved chain
catch (SqlException ex)
{
    throw new DatabaseException(
        $"Database error during {operation}", 
        ex); // Inner exception preserved
}
```

---

**References**:
- [.NET Performance Tips](https://learn.microsoft.com/en-us/dotnet/core/performance/)
- [Azure SDK Design Guidelines](https://azure.github.io/azure-sdk/general_introduction.html)
- [EF Core: Concurrency Conflicts](https://learn.microsoft.com/en-us/ef/core/saving/concurrency)
