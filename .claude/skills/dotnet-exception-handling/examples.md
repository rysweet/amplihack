# .NET Exception Handling - Working Examples

Practical before/after code examples and complete implementations.

---

## Table of Contents

1. [Before/After Examples](#beforeafter-examples)
2. [Complete Implementations](#complete-implementations)
3. [Real-World Scenarios](#real-world-scenarios)
4. [Testing Patterns](#testing-patterns)

---

## Before/After Examples

### Example 1: API Controller with Global Handler

**Before** (Defensive try/catch everywhere):

```csharp
[ApiController]
[Route("api/users")]
public class UsersController : ControllerBase
{
    private readonly IUserService _userService;
    private readonly ILogger<UsersController> _logger;

    [HttpGet("{id}")]
    public async Task<IActionResult> GetUser(int id)
    {
        try
        {
            var user = await _userService.GetByIdAsync(id);
            if (user == null)
                return NotFound($"User {id} not found");
            
            return Ok(user);
        }
        catch (ArgumentException ex)
        {
            _logger.LogWarning(ex, "Invalid user ID");
            return BadRequest(ex.Message);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to get user");
            return StatusCode(500, "An error occurred");
        }
    }

    [HttpPost]
    public async Task<IActionResult> CreateUser([FromBody] CreateUserDto dto)
    {
        try
        {
            if (string.IsNullOrEmpty(dto.Email))
                return BadRequest("Email is required");
            
            var user = await _userService.CreateAsync(dto);
            return CreatedAtAction(nameof(GetUser), new { id = user.Id }, user);
        }
        catch (ConflictException ex)
        {
            _logger.LogWarning(ex, "User already exists");
            return Conflict(ex.Message);
        }
        catch (ArgumentException ex)
        {
            _logger.LogWarning(ex, "Invalid user data");
            return BadRequest(ex.Message);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to create user");
            return StatusCode(500, "An error occurred");
        }
    }
}
```

**After** (Trust global handler):

```csharp
[ApiController]
[Route("api/users")]
public class UsersController : ControllerBase
{
    private readonly IUserService _userService;

    [HttpGet("{id}")]
    public async Task<IActionResult> GetUser(int id)
    {
        var user = await _userService.GetByIdAsync(id);
        // NotFoundException thrown by service → Global handler → 404
        return Ok(user);
    }

    [HttpPost]
    public async Task<IActionResult> CreateUser([FromBody] CreateUserDto dto)
    {
        var user = await _userService.CreateAsync(dto);
        // ConflictException → Global handler → 409
        // ArgumentException → Global handler → 400
        return CreatedAtAction(nameof(GetUser), new { id = user.Id }, user);
    }
}

// Custom exceptions
public class NotFoundException : Exception
{
    public NotFoundException(string message) : base(message) { }
}

public class ConflictException : Exception
{
    public ConflictException(string message) : base(message) { }
}
```

**Lines Saved**: 30+ lines removed, cleaner code, consistent error responses.

---

### Example 2: Service Layer with Result<T>

**Before** (Exceptions for validation):

```csharp
public class OrderService
{
    public async Task ProcessOrderAsync(Order order)
    {
        if (order.Items.Count == 0)
            throw new InvalidOperationException("Order must have at least one item");
        
        if (order.TotalAmount <= 0)
            throw new InvalidOperationException("Order total must be positive");
        
        if (!CanShipTo(order.ShippingAddress))
            throw new InvalidOperationException($"Cannot ship to {order.ShippingAddress.Country}");
        
        await _orderRepository.SaveAsync(order);
    }
}

// Controller catches and maps
[HttpPost]
public async Task<IActionResult> CreateOrder([FromBody] CreateOrderDto dto)
{
    try
    {
        var order = MapToOrder(dto);
        await _orderService.ProcessOrderAsync(order);
        return Ok();
    }
    catch (InvalidOperationException ex)
    {
        return BadRequest(ex.Message);
    }
}
```

**After** (Result<T> for validation):

```csharp
public class OrderService
{
    public async Task<Result<Order>> ProcessOrderAsync(Order order)
    {
        if (order.Items.Count == 0)
            return Result<Order>.Failure("Order must have at least one item");
        
        if (order.TotalAmount <= 0)
            return Result<Order>.Failure("Order total must be positive");
        
        if (!CanShipTo(order.ShippingAddress))
            return Result<Order>.Failure($"Cannot ship to {order.ShippingAddress.Country}");
        
        await _orderRepository.SaveAsync(order);
        return Result<Order>.Success(order);
    }
}

// Controller uses Match pattern
[HttpPost]
public async Task<IActionResult> CreateOrder([FromBody] CreateOrderDto dto)
{
    var order = MapToOrder(dto);
    var result = await _orderService.ProcessOrderAsync(order);
    
    return result.Match(
        onSuccess: order => Ok(order),
        onFailure: error => BadRequest(error)
    );
}
```

**Benefits**: No exception overhead, clearer intent, better performance.

---

### Example 3: Background Worker Exception Handling

**Before** (Silent failures):

```csharp
public class EventPublisherWorker : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            var events = await _queue.GetPendingAsync();
            foreach (var evt in events)
            {
                Task.Run(async () => await PublishAsync(evt)); // Fire-and-forget
            }
            
            await Task.Delay(1000, stoppingToken);
        }
    }
}
```

**After** (Proper exception boundaries):

```csharp
public class EventPublisherWorker : BackgroundService
{
    private readonly ILogger<EventPublisherWorker> _logger;
    private readonly IEventQueue _queue;
    private readonly IEventPublisher _publisher;

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation("Event publisher starting");

        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                var events = await _queue.GetPendingAsync(stoppingToken);
                
                foreach (var evt in events)
                {
                    await PublishWithRetryAsync(evt, stoppingToken);
                }
                
                await Task.Delay(TimeSpan.FromSeconds(1), stoppingToken);
            }
            catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested)
            {
                // Normal shutdown
                break;
            }
            catch (Exception ex)
            {
                // Log error but continue processing
                _logger.LogError(ex, "Event publishing cycle failed");
                await Task.Delay(TimeSpan.FromSeconds(5), stoppingToken);
            }
        }

        _logger.LogInformation("Event publisher stopped gracefully");
    }

    private async Task PublishWithRetryAsync(Event evt, CancellationToken ct)
    {
        const int maxRetries = 3;
        
        for (int attempt = 1; attempt <= maxRetries; attempt++)
        {
            try
            {
                await _publisher.PublishAsync(evt, ct);
                _logger.LogInformation("Event {EventId} published successfully", evt.Id);
                return;
            }
            catch (Exception ex) when (attempt < maxRetries)
            {
                _logger.LogWarning(ex, 
                    "Event {EventId} publish failed (attempt {Attempt}/{Max})", 
                    evt.Id, attempt, maxRetries);
                
                await Task.Delay(TimeSpan.FromSeconds(Math.Pow(2, attempt)), ct);
            }
            catch (Exception ex)
            {
                // Final attempt failed
                _logger.LogError(ex, 
                    "Event {EventId} publish failed after {Max} attempts", 
                    evt.Id, maxRetries);
                
                throw; // Critical failure
            }
        }
    }
}
```

**Improvements**: No silent failures, retry logic, proper logging, graceful shutdown.

---

### Example 4: EF Core Exception Translation

**Before** (Generic database errors):

```csharp
public async Task<User> CreateUserAsync(CreateUserDto dto)
{
    try
    {
        var user = new User 
        { 
            Email = dto.Email, 
            Username = dto.Username 
        };
        
        _context.Users.Add(user);
        await _context.SaveChangesAsync();
        
        return user;
    }
    catch (DbUpdateException ex)
    {
        throw new Exception("Database error occurred", ex);
    }
}
```

**After** (Specific error mapping):

```csharp
public async Task<Result<User>> CreateUserAsync(CreateUserDto dto)
{
    var user = new User 
    { 
        Email = dto.Email, 
        Username = dto.Username 
    };
    
    _context.Users.Add(user);
    
    try
    {
        await _context.SaveChangesAsync();
        return Result<User>.Success(user);
    }
    catch (DbUpdateException ex) when (ex.InnerException is SqlException sqlEx)
    {
        var message = sqlEx.Number switch
        {
            2601 or 2627 => "A user with this email or username already exists",
            547 => "Cannot create user: referenced entity does not exist",
            _ => "A database error occurred"
        };
        
        _logger.LogWarning(ex, "User creation failed: {SqlError}", sqlEx.Number);
        return Result<User>.Failure(message);
    }
    catch (DbUpdateConcurrencyException ex)
    {
        _logger.LogWarning(ex, "Concurrency conflict creating user");
        return Result<User>.Failure("The operation failed due to a conflict. Please retry.");
    }
}
```

**Benefits**: User-friendly error messages, preserved exception chains, specific handling.

---

## Complete Implementations

### GlobalExceptionHandler (Production-Ready)

```csharp
using Microsoft.AspNetCore.Diagnostics;
using Microsoft.AspNetCore.Mvc;
using System.Diagnostics;

namespace MyApi.Infrastructure;

public class GlobalExceptionHandler : IExceptionHandler
{
    private readonly ILogger<GlobalExceptionHandler> _logger;
    private readonly IHostEnvironment _environment;

    public GlobalExceptionHandler(
        ILogger<GlobalExceptionHandler> logger,
        IHostEnvironment environment)
    {
        _logger = logger;
        _environment = environment;
    }

    public async ValueTask<bool> TryHandleAsync(
        HttpContext httpContext,
        Exception exception,
        CancellationToken cancellationToken)
    {
        var traceId = Activity.Current?.Id ?? httpContext.TraceIdentifier;
        
        _logger.LogError(exception,
            "Unhandled exception for {Method} {Path}. TraceId: {TraceId}",
            httpContext.Request.Method,
            httpContext.Request.Path,
            traceId);

        var (statusCode, title, detail) = MapException(exception);

        var problemDetails = new ProblemDetails
        {
            Status = statusCode,
            Title = title,
            Detail = detail,
            Instance = httpContext.Request.Path,
            Extensions =
            {
                ["traceId"] = traceId
            }
        };

        // Include exception details only in development
        if (_environment.IsDevelopment())
        {
            problemDetails.Extensions["exceptionType"] = exception.GetType().Name;
            problemDetails.Extensions["stackTrace"] = exception.StackTrace;
        }

        httpContext.Response.StatusCode = statusCode;
        httpContext.Response.ContentType = "application/problem+json";
        
        await httpContext.Response.WriteAsJsonAsync(problemDetails, cancellationToken);

        return true; // Exception handled
    }

    private static (int StatusCode, string Title, string Detail) MapException(Exception exception)
        => exception switch
        {
            ArgumentException or ArgumentNullException =>
                (400, "Bad Request", exception.Message),
            
            UnauthorizedAccessException =>
                (401, "Unauthorized", "You are not authorized to access this resource"),
            
            NotFoundException =>
                (404, "Not Found", exception.Message),
            
            ConflictException =>
                (409, "Conflict", exception.Message),
            
            ValidationException validationEx =>
                (422, "Validation Failed", FormatValidationErrors(validationEx)),
            
            OperationCanceledException =>
                (499, "Client Closed Request", "The request was cancelled"),
            
            _ =>
                (500, "Internal Server Error", "An unexpected error occurred")
        };

    private static string FormatValidationErrors(ValidationException exception)
    {
        if (exception.Errors?.Any() != true)
            return exception.Message;

        return string.Join("; ", exception.Errors.Select(e => $"{e.PropertyName}: {e.ErrorMessage}"));
    }
}

// Registration in Program.cs
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddExceptionHandler<GlobalExceptionHandler>();
builder.Services.AddProblemDetails();

var app = builder.Build();

app.UseExceptionHandler(); // Must be early in pipeline
app.UseHttpsRedirection();
app.UseAuthorization();
app.MapControllers();

app.Run();
```

---

### Result<T> with Chaining Support

```csharp
namespace MyApi.Core;

public readonly struct Result<T>
{
    public bool IsSuccess { get; }
    public T Value { get; }
    public string ErrorMessage { get; }

    private Result(bool isSuccess, T value, string errorMessage)
    {
        IsSuccess = isSuccess;
        Value = value;
        ErrorMessage = errorMessage;
    }

    public static Result<T> Success(T value) =>
        new(true, value, string.Empty);

    public static Result<T> Failure(string errorMessage) =>
        new(false, default!, errorMessage);

    // Pattern matching
    public TResult Match<TResult>(
        Func<T, TResult> onSuccess,
        Func<string, TResult> onFailure) =>
        IsSuccess ? onSuccess(Value) : onFailure(ErrorMessage);

    // Async pattern matching
    public async Task<TResult> MatchAsync<TResult>(
        Func<T, Task<TResult>> onSuccess,
        Func<string, Task<TResult>> onFailure) =>
        IsSuccess ? await onSuccess(Value) : await onFailure(ErrorMessage);

    // Map/Select (LINQ)
    public Result<TNew> Map<TNew>(Func<T, TNew> mapper) =>
        IsSuccess
            ? Result<TNew>.Success(mapper(Value))
            : Result<TNew>.Failure(ErrorMessage);

    // Bind/SelectMany (LINQ)
    public Result<TNew> Bind<TNew>(Func<T, Result<TNew>> binder) =>
        IsSuccess
            ? binder(Value)
            : Result<TNew>.Failure(ErrorMessage);

    // Async bind
    public async Task<Result<TNew>> BindAsync<TNew>(Func<T, Task<Result<TNew>>> binder) =>
        IsSuccess
            ? await binder(Value)
            : Result<TNew>.Failure(ErrorMessage);

    // Implicit conversion to boolean
    public static implicit operator bool(Result<T> result) => result.IsSuccess;

    // LINQ query syntax support
    public Result<TNew> Select<TNew>(Func<T, TNew> selector) => Map(selector);

    public Result<TNew> SelectMany<TNew>(Func<T, Result<TNew>> selector) => Bind(selector);

    public Result<TFinal> SelectMany<TNew, TFinal>(
        Func<T, Result<TNew>> selector,
        Func<T, TNew, TFinal> resultSelector) =>
        Bind(value => selector(value).Map(newValue => resultSelector(value, newValue)));
}

// Extension methods for common scenarios
public static class ResultExtensions
{
    public static Result<T> ToResult<T>(this T? value, string errorMessage)
        where T : class =>
        value is not null
            ? Result<T>.Success(value)
            : Result<T>.Failure(errorMessage);

    public static Result<T> ToResult<T>(this T? value, string errorMessage)
        where T : struct =>
        value.HasValue
            ? Result<T>.Success(value.Value)
            : Result<T>.Failure(errorMessage);

    public static async Task<Result<T>> AsResult<T>(this Task<T> task)
    {
        try
        {
            var value = await task;
            return Result<T>.Success(value);
        }
        catch (Exception ex)
        {
            return Result<T>.Failure(ex.Message);
        }
    }
}

// Usage examples
public class Examples
{
    // Simple usage
    public Result<User> GetUser(int id)
    {
        var user = _users.FirstOrDefault(u => u.Id == id);
        return user.ToResult($"User {id} not found");
    }

    // Chaining with LINQ query syntax
    public Result<decimal> CalculateDiscount(int userId, decimal amount)
    {
        var result =
            from user in GetUser(userId)
            from tier in GetLoyaltyTier(user.Points)
            from rate in GetDiscountRate(tier, amount)
            select amount * rate;

        return result;
    }

    // Chaining with method syntax
    public async Task<Result<Order>> ProcessOrderAsync(CreateOrderDto dto)
    {
        return await ValidateOrder(dto)
            .BindAsync(order => ApplyDiscountAsync(order))
            .BindAsync(order => SaveOrderAsync(order));
    }
}
```

---

### DbContext Extensions with Result<T>

```csharp
namespace MyApi.Infrastructure.Data;

public static class DbContextExtensions
{
    public static async Task<Result<int>> SaveChangesWithResultAsync(
        this DbContext context,
        CancellationToken ct = default)
    {
        try
        {
            var changes = await context.SaveChangesAsync(ct);
            return Result<int>.Success(changes);
        }
        catch (DbUpdateConcurrencyException ex)
        {
            var logger = context.GetService<ILogger<DbContext>>();
            logger?.LogWarning(ex, "Concurrency conflict during save");
            
            return Result<int>.Failure(
                "The record was modified by another user. Please refresh and try again.");
        }
        catch (DbUpdateException ex) when (ex.InnerException is SqlException sqlEx)
        {
            var logger = context.GetService<ILogger<DbContext>>();
            logger?.LogWarning(ex, "Database constraint violation: {SqlError}", sqlEx.Number);
            
            var message = sqlEx.Number switch
            {
                2601 or 2627 => "A record with this unique key already exists",
                547 => "Cannot complete operation: this record is referenced by other data",
                515 => "Cannot insert NULL into required field",
                _ => $"A database error occurred (Code: {sqlEx.Number})"
            };
            
            return Result<int>.Failure(message);
        }
    }

    public static async Task<Result<T>> FindByIdWithResultAsync<T>(
        this DbContext context,
        object id,
        CancellationToken ct = default)
        where T : class
    {
        var entity = await context.FindAsync<T>(new[] { id }, ct);
        return entity.ToResult($"{typeof(T).Name} with ID {id} not found");
    }
}
```

---

## Real-World Scenarios

### Scenario 1: Order Processing System

Complete example with validation, persistence, and external service calls.

```csharp
// Domain
public class Order
{
    public int Id { get; set; }
    public string CustomerId { get; set; } = string.Empty;
    public List<OrderItem> Items { get; set; } = new();
    public decimal TotalAmount { get; set; }
    public OrderStatus Status { get; set; }
}

public enum OrderStatus { Pending, Confirmed, Shipped, Delivered, Cancelled }

// Service
public class OrderService
{
    private readonly ApplicationDbContext _context;
    private readonly IPaymentGateway _paymentGateway;
    private readonly IInventoryService _inventory;
    private readonly ILogger<OrderService> _logger;

    public async Task<Result<Order>> CreateOrderAsync(
        CreateOrderDto dto,
        CancellationToken ct = default)
    {
        // Step 1: Validate input
        var validationResult = ValidateOrderDto(dto);
        if (!validationResult.IsSuccess)
            return Result<Order>.Failure(validationResult.ErrorMessage);

        // Step 2: Check inventory
        var inventoryResult = await _inventory.ReserveItemsAsync(dto.Items, ct);
        if (!inventoryResult.IsSuccess)
            return Result<Order>.Failure(inventoryResult.ErrorMessage);

        // Step 3: Process payment
        var paymentResult = await ProcessPaymentAsync(dto.PaymentInfo, dto.TotalAmount, ct);
        if (!paymentResult.IsSuccess)
        {
            // Rollback inventory reservation
            await _inventory.ReleaseItemsAsync(inventoryResult.Value, ct);
            return Result<Order>.Failure(paymentResult.ErrorMessage);
        }

        // Step 4: Create order
        var order = MapToOrder(dto, paymentResult.Value);
        _context.Orders.Add(order);

        var saveResult = await _context.SaveChangesWithResultAsync(ct);
        if (!saveResult.IsSuccess)
        {
            // Rollback payment and inventory
            await _paymentGateway.RefundAsync(paymentResult.Value, ct);
            await _inventory.ReleaseItemsAsync(inventoryResult.Value, ct);
            return Result<Order>.Failure(saveResult.ErrorMessage);
        }

        _logger.LogInformation(
            "Order {OrderId} created for customer {CustomerId}", 
            order.Id, 
            order.CustomerId);

        return Result<Order>.Success(order);
    }

    private Result<CreateOrderDto> ValidateOrderDto(CreateOrderDto dto)
    {
        if (string.IsNullOrWhiteSpace(dto.CustomerId))
            return Result<CreateOrderDto>.Failure("Customer ID is required");

        if (dto.Items == null || dto.Items.Count == 0)
            return Result<CreateOrderDto>.Failure("Order must have at least one item");

        if (dto.TotalAmount <= 0)
            return Result<CreateOrderDto>.Failure("Order total must be positive");

        return Result<CreateOrderDto>.Success(dto);
    }

    private async Task<Result<string>> ProcessPaymentAsync(
        PaymentInfo payment,
        decimal amount,
        CancellationToken ct)
    {
        try
        {
            var transactionId = await _paymentGateway.ChargeAsync(payment, amount, ct);
            return Result<string>.Success(transactionId);
        }
        catch (PaymentDeclinedException ex)
        {
            _logger.LogWarning(ex, "Payment declined for amount {Amount}", amount);
            return Result<string>.Failure("Payment was declined");
        }
        catch (PaymentGatewayException ex)
        {
            _logger.LogError(ex, "Payment gateway error");
            return Result<string>.Failure("Payment processing failed. Please try again.");
        }
    }
}

// Controller
[ApiController]
[Route("api/orders")]
public class OrdersController : ControllerBase
{
    private readonly OrderService _orderService;

    [HttpPost]
    public async Task<IActionResult> CreateOrder(
        [FromBody] CreateOrderDto dto,
        CancellationToken ct)
    {
        var result = await _orderService.CreateOrderAsync(dto, ct);

        return result.Match(
            onSuccess: order => CreatedAtAction(
                nameof(GetOrder), 
                new { id = order.Id }, 
                order),
            onFailure: error => BadRequest(new { error })
        );
    }

    [HttpGet("{id}")]
    public async Task<IActionResult> GetOrder(int id, CancellationToken ct)
    {
        var order = await _orderService.GetByIdAsync(id, ct);
        // NotFoundException thrown → Global handler → 404
        return Ok(order);
    }
}
```

---

## Testing Patterns

### Unit Testing GlobalExceptionHandler

```csharp
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging.Abstractions;
using System.IO;
using System.Text.Json;
using Xunit;

public class GlobalExceptionHandlerTests
{
    private readonly GlobalExceptionHandler _handler;
    private readonly DefaultHttpContext _httpContext;

    public GlobalExceptionHandlerTests()
    {
        var environment = new Mock<IHostEnvironment>();
        environment.Setup(e => e.EnvironmentName).Returns("Production");
        
        _handler = new GlobalExceptionHandler(
            NullLogger<GlobalExceptionHandler>.Instance,
            environment.Object);

        _httpContext = new DefaultHttpContext();
        _httpContext.Response.Body = new MemoryStream();
    }

    [Fact]
    public async Task ArgumentException_Returns400()
    {
        // Arrange
        var exception = new ArgumentException("Invalid parameter");

        // Act
        await _handler.TryHandleAsync(_httpContext, exception, CancellationToken.None);

        // Assert
        Assert.Equal(400, _httpContext.Response.StatusCode);
        
        _httpContext.Response.Body.Seek(0, SeekOrigin.Begin);
        var problemDetails = await JsonSerializer.DeserializeAsync<ProblemDetails>(
            _httpContext.Response.Body);

        Assert.NotNull(problemDetails);
        Assert.Equal(400, problemDetails.Status);
        Assert.Equal("Bad Request", problemDetails.Title);
        Assert.Equal("Invalid parameter", problemDetails.Detail);
    }

    [Fact]
    public async Task NotFoundException_Returns404()
    {
        // Arrange
        var exception = new NotFoundException("User not found");

        // Act
        await _handler.TryHandleAsync(_httpContext, exception, CancellationToken.None);

        // Assert
        Assert.Equal(404, _httpContext.Response.StatusCode);
    }

    [Fact]
    public async Task UnhandledException_Returns500_WithGenericMessage()
    {
        // Arrange
        var exception = new InvalidOperationException("Internal error details");

        // Act
        await _handler.TryHandleAsync(_httpContext, exception, CancellationToken.None);

        // Assert
        Assert.Equal(500, _httpContext.Response.StatusCode);
        
        _httpContext.Response.Body.Seek(0, SeekOrigin.Begin);
        var problemDetails = await JsonSerializer.DeserializeAsync<ProblemDetails>(
            _httpContext.Response.Body);

        Assert.Equal("An unexpected error occurred", problemDetails!.Detail);
        // Should NOT contain exception details in production
        Assert.DoesNotContain("Internal error details", problemDetails.Detail);
    }
}
```

### Unit Testing Result<T>

```csharp
public class ResultTests
{
    [Fact]
    public void Success_CreatesSuccessResult()
    {
        var result = Result<int>.Success(42);

        Assert.True(result.IsSuccess);
        Assert.Equal(42, result.Value);
        Assert.Empty(result.ErrorMessage);
    }

    [Fact]
    public void Failure_CreatesFailureResult()
    {
        var result = Result<int>.Failure("Error occurred");

        Assert.False(result.IsSuccess);
        Assert.Equal("Error occurred", result.ErrorMessage);
    }

    [Fact]
    public void Match_CallsOnSuccess_WhenSuccess()
    {
        var result = Result<int>.Success(42);

        var output = result.Match(
            onSuccess: value => $"Success: {value}",
            onFailure: error => $"Failure: {error}"
        );

        Assert.Equal("Success: 42", output);
    }

    [Fact]
    public void Match_CallsOnFailure_WhenFailure()
    {
        var result = Result<int>.Failure("Not found");

        var output = result.Match(
            onSuccess: value => $"Success: {value}",
            onFailure: error => $"Failure: {error}"
        );

        Assert.Equal("Failure: Not found", output);
    }

    [Fact]
    public void Map_TransformsSuccessValue()
    {
        var result = Result<int>.Success(42);

        var mapped = result.Map(x => x * 2);

        Assert.True(mapped.IsSuccess);
        Assert.Equal(84, mapped.Value);
    }

    [Fact]
    public void Map_PropagatesFailure()
    {
        var result = Result<int>.Failure("Error");

        var mapped = result.Map(x => x * 2);

        Assert.False(mapped.IsSuccess);
        Assert.Equal("Error", mapped.ErrorMessage);
    }

    [Fact]
    public void Bind_ChainsSuccessResults()
    {
        var result = Result<int>.Success(10);

        var chained = result.Bind(x => 
            x > 0 
                ? Result<string>.Success($"Positive: {x}")
                : Result<string>.Failure("Not positive")
        );

        Assert.True(chained.IsSuccess);
        Assert.Equal("Positive: 10", chained.Value);
    }

    [Fact]
    public void LinqQuery_ChainsResults()
    {
        var result =
            from x in Result<int>.Success(10)
            from y in Result<int>.Success(5)
            select x + y;

        Assert.True(result.IsSuccess);
        Assert.Equal(15, result.Value);
    }
}
```

### Integration Testing with GlobalExceptionHandler

```csharp
public class ExceptionHandlingIntegrationTests : IClassFixture<WebApplicationFactory<Program>>
{
    private readonly WebApplicationFactory<Program> _factory;
    private readonly HttpClient _client;

    public ExceptionHandlingIntegrationTests(WebApplicationFactory<Program> factory)
    {
        _factory = factory;
        _client = factory.CreateClient();
    }

    [Fact]
    public async Task NotFound_Returns404ProblemDetails()
    {
        // Act
        var response = await _client.GetAsync("/api/users/99999");

        // Assert
        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        
        var problemDetails = await response.Content.ReadFromJsonAsync<ProblemDetails>();
        Assert.NotNull(problemDetails);
        Assert.Equal(404, problemDetails.Status);
        Assert.Equal("Not Found", problemDetails.Title);
        Assert.Contains("traceId", problemDetails.Extensions);
    }

    [Fact]
    public async Task ValidationError_Returns422ProblemDetails()
    {
        // Arrange
        var dto = new CreateUserDto { Email = "invalid-email" }; // Invalid

        // Act
        var response = await _client.PostAsJsonAsync("/api/users", dto);

        // Assert
        Assert.Equal(HttpStatusCode.UnprocessableEntity, response.StatusCode);
        
        var problemDetails = await response.Content.ReadFromJsonAsync<ProblemDetails>();
        Assert.Equal(422, problemDetails!.Status);
    }

    [Fact]
    public async Task UnhandledException_Returns500_WithoutStackTrace()
    {
        // Act - Trigger internal error
        var response = await _client.GetAsync("/api/test/throw-error");

        // Assert
        Assert.Equal(HttpStatusCode.InternalServerError, response.StatusCode);
        
        var content = await response.Content.ReadAsStringAsync();
        
        // Should NOT contain stack trace in production
        Assert.DoesNotContain("at ", content); // Stack trace indicator
        Assert.DoesNotContain(".cs:line", content); // File/line indicator
    }
}
```

---

**References**:
- [xUnit Testing Patterns](https://xunit.net/)
- [Microsoft: Integration Tests](https://learn.microsoft.com/en-us/aspnet/core/test/integration-tests)
- [Moq Framework](https://github.com/moq/moq4)
