# .NET Exception Handling - Complete Reference

Comprehensive reference for .NET exception handling investigation and remediation patterns.

---

## Table of Contents

1. [The 10 Common Mistakes (Detailed)](#the-10-common-mistakes-detailed)
2. [Detection Patterns](#detection-patterns)
3. [Fix Templates](#fix-templates)
4. [Architecture Patterns](#architecture-patterns)
5. [Security Considerations](#security-considerations)
6. [Integration Patterns](#integration-patterns)
7. [Validation Rules](#validation-rules)

---

## The 10 Common Mistakes (Detailed)

### Mistake #1: Catching Exception Too Broadly

**Problem**: Catching base `Exception` type instead of specific exceptions.

**Why It's Bad**:
- Masks programming errors (NullReferenceException, ArgumentException)
- Makes debugging difficult
- Hides unexpected failures
- Violates fail-fast principle

**Detection Pattern**:
```
catch \(Exception[^\)]*\)
```

**Common Locations**:
- Background workers
- Service layer methods
- Generic repositories

**Severity**: HIGH

**Fix**: Catch only specific exceptions you can handle:
```csharp
// BAD
try { await ProcessAsync(); }
catch (Exception ex) { Logger.LogError(ex, "Failed"); }

// GOOD
try { await ProcessAsync(); }
catch (DbUpdateException ex) { /* Handle DB errors */ }
catch (HttpRequestException ex) { /* Handle HTTP errors */ }
```

---

### Mistake #2: Swallowing Exceptions Silently

**Problem**: Empty catch blocks that hide errors.

**Why It's Bad**:
- Silent failures in production
- No observability of issues
- Corrupted state continues executing
- Impossible to diagnose problems

**Detection Pattern**:
```
catch[^{]*\{\s*(//[^\n]*)?\s*\}
```

**Common Locations**:
- Event publishing code
- Cleanup/disposal code
- Legacy migration code

**Severity**: HIGH

**Fix**: Always log exceptions at minimum:
```csharp
// BAD
try { await PublishEventAsync(evt); }
catch { /* Ignore event failures */ }

// GOOD
try { await PublishEventAsync(evt); }
catch (Exception ex) 
{ 
    Logger.LogError(ex, "Event publishing failed for {EventType}", evt.GetType().Name);
    throw; // Re-throw if critical
}
```

---

### Mistake #3: Using `throw ex;` Instead of `throw;`

**Problem**: Re-throwing with `throw ex;` resets the stack trace.

**Why It's Bad**:
- Loses original stack trace
- Makes debugging impossible
- Hides root cause location
- Breaks exception analysis tools

**Detection Pattern**:
```
throw ex;
```

**Common Locations**:
- Legacy code
- Refactored methods
- Copy-pasted exception handlers

**Severity**: MEDIUM

**Fix**: Use `throw;` to preserve stack trace:
```csharp
// BAD
catch (Exception ex)
{
    Logger.LogError(ex, "Failed");
    throw ex; // Resets stack trace
}

// GOOD
catch (Exception ex)
{
    Logger.LogError(ex, "Failed");
    throw; // Preserves original stack trace
}
```

---

### Mistake #4: Wrapping Everything in Try/Catch

**Problem**: Defensive try/catch blocks throughout codebase.

**Why It's Bad**:
- Clutters code (200+ lines in typical projects)
- Hides programming errors
- Duplicates exception handling logic
- Violates DRY principle

**Detection**: Manual code review for excessive try/catch density.

**Common Locations**:
- Every controller action
- Every service method
- Repository methods

**Severity**: MEDIUM

**Fix**: Use global exception handler instead:
```csharp
// BAD - In every controller action
[HttpPost]
public async Task<IActionResult> CreateUser(UserDto dto)
{
    try
    {
        var user = await userService.CreateAsync(dto);
        return Ok(user);
    }
    catch (ArgumentException ex) { return BadRequest(ex.Message); }
    catch (ConflictException ex) { return Conflict(ex.Message); }
    catch (Exception ex) { return StatusCode(500); }
}

// GOOD - Let global handler manage it
[HttpPost]
public async Task<IActionResult> CreateUser(UserDto dto)
{
    var user = await userService.CreateAsync(dto);
    return Ok(user);
}
// GlobalExceptionHandler maps exceptions to HTTP responses
```

---

### Mistake #5: Using Exceptions for Control Flow

**Problem**: Throwing exceptions for expected business validation.

**Why It's Bad**:
- Performance overhead (exceptions are expensive)
- Semantic confusion (not exceptional)
- Stack trace pollution in logs
- Violates separation of concerns

**Detection**: Look for validation logic throwing exceptions.

**Common Locations**:
- Input validation
- State machine transitions
- Business rule checks

**Severity**: MEDIUM

**Fix**: Use Result<T> pattern for validation:
```csharp
// BAD
public void TransitionState(State from, State to)
{
    if (!IsValidTransition(from, to))
        throw new InvalidStateTransitionException(from, to);
    // ... transition logic
}

// GOOD
public Result<bool> CanTransitionState(State from, State to)
{
    if (!IsValidTransition(from, to))
        return Result<bool>.Failure($"Cannot transition from {from} to {to}");
    
    return Result<bool>.Success(true);
}
```

---

### Mistake #6: Forgetting to Await Async Calls

**Problem**: Not awaiting async methods, losing exceptions.

**Why It's Bad**:
- Exceptions lost on background thread
- Synchronization context issues
- Race conditions
- Unobserved task exceptions

**Detection Pattern**:
```
Task\w+\([^;]*\);(?!\s*await)
```

**Common Locations**:
- Event handlers
- Fire-and-forget operations
- Background initialization

**Severity**: HIGH

**Fix**: Always await async calls:
```csharp
// BAD
public void OnMessageReceived(Message msg)
{
    ProcessMessageAsync(msg); // Fire-and-forget
}

// GOOD
public async Task OnMessageReceived(Message msg)
{
    await ProcessMessageAsync(msg);
}
```

---

### Mistake #7: Ignoring Background Task Exceptions

**Problem**: Fire-and-forget tasks with no exception handling.

**Why It's Bad**:
- Silent failures in background work
- No observability
- Corrupted state
- Lost critical operations (audit logs, events)

**Detection Pattern**:
```
Task\.Run\(|Task\.Factory\.StartNew
```

**Common Locations**:
- Background workers
- Event publishing
- Cache warming
- Cleanup operations

**Severity**: CRITICAL (if critical operations)

**Fix**: Add exception boundaries and observability:
```csharp
// BAD
Task.Run(async () => await PublishEventAsync(evt));

// GOOD
_ = Task.Run(async () =>
{
    try
    {
        await PublishEventAsync(evt);
    }
    catch (Exception ex)
    {
        Logger.LogCritical(ex, "Critical event publishing failed");
        // Consider alerting, metrics, etc.
    }
});
```

---

### Mistake #8: Throwing Generic Exceptions

**Problem**: Using `Exception` or `ApplicationException` instead of specific types.

**Why It's Bad**:
- Cannot distinguish error types
- Forces broad catch blocks
- Breaks selective exception handling
- No semantic meaning

**Detection**: Manual review for generic exception types.

**Common Locations**:
- Business logic validation
- Custom error scenarios
- Legacy code

**Severity**: LOW

**Fix**: Create domain-specific exception types:
```csharp
// BAD
throw new Exception("User not found");

// GOOD
public class UserNotFoundException : Exception
{
    public UserNotFoundException(string userId) 
        : base($"User with ID {userId} not found")
    {
    }
}

throw new UserNotFoundException(userId);
```

---

### Mistake #9: Losing Inner Exceptions

**Problem**: Creating new exceptions without preserving the original.

**Why It's Bad**:
- Loses root cause information
- Breaks exception analysis
- Debugging becomes impossible
- Obscures real failure

**Detection**: Review custom exception constructors.

**Common Locations**:
- Exception translation layers
- Adapter patterns
- Legacy migrations

**Severity**: MEDIUM

**Fix**: Always preserve inner exceptions:
```csharp
// BAD
catch (SqlException ex)
{
    throw new DatabaseException("Database error occurred");
}

// GOOD
catch (SqlException ex)
{
    throw new DatabaseException("Database error occurred", ex);
}

// Custom exception with innerException support
public class DatabaseException : Exception
{
    public DatabaseException(string message, Exception innerException = null)
        : base(message, innerException)
    {
    }
}
```

---

### Mistake #10: Missing Global Exception Handling

**Problem**: No centralized exception-to-HTTP mapping.

**Why It's Bad**:
- Stack traces exposed to clients (security risk)
- Inconsistent error responses
- Duplicated exception handling in controllers
- No centralized logging/monitoring

**Detection**:
```bash
# Search for AddExceptionHandler in Program.cs
# If not found → CRITICAL violation
grep -n "AddExceptionHandler\|UseExceptionHandler" Program.cs
```

**Common in**: ASP.NET Core APIs without middleware

**Severity**: CRITICAL

**Fix**: Implement `IExceptionHandler` (see Architecture Patterns section).

---

## Detection Patterns

### Ripgrep (recommended) Patterns

Use `rg -P` (PCRE mode) for these patterns:

```bash
# Mistake #1: Broad catches
rg -P 'catch\s*\(Exception\b' --glob '*.cs'

# Mistake #2: Empty catches
rg -P 'catch[^{]*\{\s*(//[^\n]*)?\s*\}' --glob '*.cs'

# Mistake #3: throw ex
rg 'throw\s+ex;' --glob '*.cs'

# Mistake #6: Unawaited async
rg -P 'Task\w+\([^;]*\);' --glob '*.cs'

# Mistake #7: Fire-and-forget
rg 'Task\.Run\(|Task\.Factory\.StartNew' --glob '*.cs'

# Mistake #10: Missing global handler
rg 'AddExceptionHandler|UseExceptionHandler' Program.cs
```

### Grep (POSIX) Alternative

If using standard grep, use POSIX character classes:

```bash
# Mistake #1: Broad catches
grep -n 'catch[[:space:]]*(Exception' *.cs

# Mistake #2: Empty catches (simplified)
grep -n 'catch.*{[[:space:]]*}' *.cs

# Mistake #3: throw ex
grep -n 'throw ex;' *.cs
```

---

## Fix Templates

### Template 1: GlobalExceptionHandler

```csharp
public class GlobalExceptionHandler : IExceptionHandler
{
    private readonly ILogger<GlobalExceptionHandler> _logger;

    public GlobalExceptionHandler(ILogger<GlobalExceptionHandler> logger)
    {
        _logger = logger;
    }

    public async ValueTask<bool> TryHandleAsync(
        HttpContext httpContext,
        Exception exception,
        CancellationToken cancellationToken)
    {
        _logger.LogError(exception, 
            "Unhandled exception for {Method} {Path}", 
            httpContext.Request.Method, 
            httpContext.Request.Path);

        var (statusCode, title) = MapException(exception);

        httpContext.Response.StatusCode = statusCode;
        await httpContext.Response.WriteAsJsonAsync(new ProblemDetails
        {
            Status = statusCode,
            Title = title,
            Detail = statusCode >= 500 
                ? "An error occurred processing your request" 
                : exception.Message,
            Instance = httpContext.Request.Path
        }, cancellationToken);

        return true; // Exception handled
    }

    private static (int StatusCode, string Title) MapException(Exception exception)
        => exception switch
        {
            ArgumentException or ArgumentNullException => (400, "Invalid request"),
            UnauthorizedAccessException => (401, "Unauthorized"),
            NotFoundException => (404, "Not found"),
            ConflictException => (409, "Conflict"),
            _ => (500, "Internal server error")
        };
}
```

**Registration**:
```csharp
// Program.cs
builder.Services.AddExceptionHandler<GlobalExceptionHandler>();
builder.Services.AddProblemDetails();

var app = builder.Build();
app.UseExceptionHandler(); // Must be before UseRouting
```

---

### Template 2: Result<T> Pattern

```csharp
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

    public TResult Match<TResult>(
        Func<T, TResult> onSuccess,
        Func<string, TResult> onFailure) =>
        IsSuccess ? onSuccess(Value) : onFailure(ErrorMessage);

    public Result<TNew> Map<TNew>(Func<T, TNew> mapper) =>
        IsSuccess 
            ? Result<TNew>.Success(mapper(Value)) 
            : Result<TNew>.Failure(ErrorMessage);
}

// Controller usage
[HttpPost]
public IActionResult ValidateTransition([FromBody] TransitionRequest request)
{
    var result = stateMachine.CanTransition(request.From, request.To);
    return result.Match(
        onSuccess: _ => Ok(),
        onFailure: error => BadRequest(error)
    );
}
```

---

### Template 3: DbContext Exception Extensions

```csharp
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
            return Result<int>.Failure("The record was modified by another user");
        }
        catch (DbUpdateException ex) when (ex.InnerException is SqlException sqlEx)
        {
            return sqlEx.Number switch
            {
                2601 or 2627 => Result<int>.Failure("A record with this key already exists"),
                547 => Result<int>.Failure("Cannot delete: record is referenced elsewhere"),
                _ => Result<int>.Failure("A database error occurred")
            };
        }
    }
}
```

---

### Template 4: BackgroundService Exception Boundary

```csharp
public class EventPublisherService : BackgroundService
{
    private readonly ILogger<EventPublisherService> _logger;
    private readonly IEventQueue _queue;

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation("Event publisher starting");

        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                var evt = await _queue.DequeueAsync(stoppingToken);
                await PublishAsync(evt, stoppingToken);
            }
            catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested)
            {
                // Normal shutdown
                break;
            }
            catch (Exception ex)
            {
                // Log but continue processing
                _logger.LogError(ex, "Event publishing failed, will retry");
                await Task.Delay(TimeSpan.FromSeconds(5), stoppingToken);
            }
        }

        _logger.LogInformation("Event publisher stopped");
    }
}
```

---

## Architecture Patterns

### When to Use GlobalExceptionHandler vs Try/Catch

**Use GlobalExceptionHandler for**:
- All ASP.NET Core applications
- Consistent error response format
- Security (prevent stack trace leaks)
- Centralized logging
- ProblemDetails RFC 7807 compliance

**Use Try/Catch for**:
- Resource cleanup (using/try-finally)
- Specific operation recovery
- External service integration with retries
- Transaction boundaries

**Never use Try/Catch for**:
- Every controller action
- Validation logic (use Result<T>)
- Converting exceptions to HTTP responses (use global handler)

---

### Result<T> vs Exception Decision Tree

```
Is the condition expected in normal operation?
├─ Yes → Use Result<T>
│  Examples: Validation, business rules, state checks
│
└─ No → Use Exception
   ├─ Is it recoverable?
   │  ├─ Yes → Specific exception + handling
   │  │  Examples: DbUpdateException, HttpRequestException
   │  │
   │  └─ No → Let fail + global handler
   │     Examples: ArgumentNullException, InvalidOperationException
```

---

## Security Considerations

### OWASP Compliance

**A01:2021 – Broken Access Control**:
- Never expose stack traces in production
- Use ProblemDetails with sanitized messages

**A03:2021 – Injection**:
- Don't include user input directly in exception messages
- Sanitize before logging

**A09:2021 – Security Logging and Monitoring Failures**:
- Always log exceptions with context
- Include correlation IDs
- Monitor exception rates

### Stack Trace Prevention

```csharp
// WRONG - Exposes stack trace
httpContext.Response.StatusCode = 500;
await httpContext.Response.WriteAsJsonAsync(exception);

// RIGHT - Sanitized response
await httpContext.Response.WriteAsJsonAsync(new ProblemDetails
{
    Status = 500,
    Title = "Internal server error",
    Detail = "An error occurred" // Generic message
});
```

### Sensitive Data in Exceptions

```csharp
// WRONG - Leaks sensitive data
throw new Exception($"Failed to authenticate user {username} with password {password}");

// RIGHT - No sensitive data
throw new AuthenticationException("Authentication failed");
```

---

## Integration Patterns

### ASP.NET Core Minimal APIs

```csharp
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddExceptionHandler<GlobalExceptionHandler>();
builder.Services.AddProblemDetails();

var app = builder.Build();

app.UseExceptionHandler(); // Before MapGet/MapPost
app.MapGet("/users/{id}", async (int id, UserService svc) =>
{
    var user = await svc.GetByIdAsync(id); // Throws NotFoundException
    return user; // Global handler catches and maps to 404
});
```

### EF Core with Result Pattern

```csharp
public async Task<Result<User>> CreateUserAsync(UserDto dto)
{
    var user = new User { Name = dto.Name, Email = dto.Email };
    _context.Users.Add(user);
    
    var saveResult = await _context.SaveChangesWithResultAsync();
    
    return saveResult.IsSuccess
        ? Result<User>.Success(user)
        : Result<User>.Failure(saveResult.ErrorMessage);
}
```

### Azure SDK Integration

```csharp
try
{
    await blobClient.UploadAsync(stream);
}
catch (RequestFailedException ex) when (ex.Status == 404)
{
    throw new NotFoundException("Blob container not found", ex);
}
catch (RequestFailedException ex) when (ex.Status == 409)
{
    throw new ConflictException("Blob already exists", ex);
}
catch (AuthenticationFailedException ex)
{
    throw new UnauthorizedAccessException("Azure authentication failed", ex);
}
```

---

## Validation Rules

### ASP.NET Core Projects

1. **Global handler registered**: `AddExceptionHandler<T>()` in Program.cs
2. **Middleware active**: `UseExceptionHandler()` in pipeline
3. **ProblemDetails enabled**: `AddProblemDetails()` configured
4. **No try/catch in controllers**: Trust global handler

### All Projects

1. **No catch (Exception)**: Except at application boundaries
2. **No empty catches**: Always log at minimum
3. **No throw ex**: Use `throw;` to preserve stack
4. **Async awaited**: All async calls properly awaited
5. **Background tasks monitored**: Exception boundaries in BackgroundService

### Security

1. **Zero stack traces**: Never in HTTP responses
2. **Sanitized messages**: No sensitive data in exceptions
3. **Proper HTTP codes**: Match exception type to status code
4. **Correlation IDs**: Track requests through exception logs

---

## Severity Classification Reference

**CRITICAL** (Fix immediately):
- Missing global exception handler (stack trace exposure)
- Background task exceptions swallowed (data loss risk)
- Security vulnerabilities (sensitive data in exceptions)

**HIGH** (Fix before production):
- Broad catch (Exception) blocks
- Empty catch blocks
- Unawaited async calls
- Lost inner exceptions

**MEDIUM** (Fix during refactoring):
- Excessive try/catch blocks
- Exceptions for control flow
- throw ex (stack trace reset)
- Wrong HTTP status codes

**LOW** (Fix when convenient):
- Generic exception types
- Inconsistent exception messages
- Missing XML documentation on custom exceptions

---

**References**:
- [Microsoft: Exception Best Practices](https://learn.microsoft.com/en-us/dotnet/standard/exceptions/best-practices-for-exceptions)
- [ASP.NET Core: Handle Errors](https://learn.microsoft.com/en-us/aspnet/core/web-api/handle-errors)
- [OWASP: Error Handling](https://owasp.org/www-community/Improper_Error_Handling)
