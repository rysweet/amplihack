---
name: dotnet-exception-handling
description: Comprehensive .NET exception handling quality improvement workflow. Auto-detects .NET projects, investigates 10 common exception handling mistakes, generates prioritized findings, and orchestrates fixes following best practices.
version: 1.0.0
tags: [dotnet, quality, exception-handling, investigation, refactoring, security]
token_budget: 2000
maturity: experimental
source_urls:
  - https://abp.io/community/articles/top-10-exception-handling-mistakes-in-net-jhm8wzvg
  - https://learn.microsoft.com/en-us/dotnet/standard/exceptions/best-practices-for-exceptions
  - https://learn.microsoft.com/en-us/aspnet/core/web-api/handle-errors
---

# .NET Exception Handling Quality Improvement

## Purpose

Systematic investigation and remediation of .NET exception handling anti-patterns across your codebase. This skill detects, documents, and fixes the 10 most common exception handling mistakes in .NET applications, ensuring production-ready error handling.

Use this skill when you need to audit and improve exception handling in any .NET project (ASP.NET Core, worker services, class libraries).

## Core Responsibilities

1. **Auto-detect .NET projects** - Scans for *.csproj, *.sln, *.cs files
2. **Investigate 10 common mistakes** - Runs comprehensive codebase analysis
3. **Generate prioritized findings** - CRITICAL/HIGH/MEDIUM/LOW severity ratings
4. **Orchestrate fixes** - Uses default-workflow for implementation
5. **Validate improvements** - Ensures security, performance, maintainability

## Usage

### Basic Usage

```bash
/dotnet-exception-handling <path-to-dotnet-project>
```

### With Options

```bash
/dotnet-exception-handling <project-path> --priority critical
/dotnet-exception-handling <project-path> --fix-all
/dotnet-exception-handling <project-path> --investigation-only
```

### Arguments

- `project-path`: Path to .NET solution or project directory (default: current directory)
- `--priority`: Filter by severity level: `critical`, `high`, `medium`, `low`, `all` (default: `all`)
- `--fix-all`: Auto-implement all fixes in single PR (default: investigate only)
- `--investigation-only`: Skip fix orchestration, generate report only

## When to Use This Skill

Use this skill when:

- Preparing .NET code for production deployment
- Conducting code quality audits
- Reviewing PR changes for exception handling issues
- Onboarding to a new .NET codebase (understand error handling patterns)
- Implementing global exception handling middleware
- Refactoring legacy exception handling code
- Security review finds information disclosure vulnerabilities
- Production incidents trace to poor exception handling

## The 10 Common Mistakes

This skill detects and fixes:

1. **Catching Exception Too Broadly** - Base Exception caught instead of specific types
2. **Swallowing Exceptions Silently** - Empty catch blocks hiding errors
3. **Using `throw ex;` Instead of `throw;`** - Resetting stack traces
4. **Wrapping Everything in Try/Catch** - Excessive defensive coding
5. **Using Exceptions for Control Flow** - Exceptions for expected conditions
6. **Forgetting to Await Async Calls** - Unhandled exceptions on background threads
7. **Ignoring Background Task Exceptions** - Fire-and-forget patterns losing errors
8. **Throwing Generic Exceptions** - Vague exception types and messages
9. **Losing Inner Exceptions** - Breaking exception chains
10. **Missing Global Exception Handling** - No centralized error handling middleware

## Execution Workflow

When this skill is invoked, it follows a hybrid investigation + development workflow:

### Phase 1: Investigation (6 Steps)

**Step 1: Project Detection**
- Scan for .csproj, .sln files
- Identify ASP.NET Core projects (web APIs, MVC)
- Identify worker service projects (BackgroundService)
- Identify class library projects
- Count total C# files for scope estimation

**Step 2: Exception Pattern Analysis**
- Deploy 5 specialized analyzer agents in parallel:
  - **Background Worker Specialist** - Analyzes BackgroundService exception handling
  - **API Layer Specialist** - Reviews controllers and middleware
  - **Service Layer Specialist** - Examines business logic services
  - **Data Layer Specialist** - Checks EF Core exception handling
  - **Infrastructure Specialist** - Reviews Program.cs, configuration

**Step 3: Violation Detection**
- Use grep patterns to find each of the 10 mistakes:
  ```bash
  # Mistake #1: Broad catches
  catch \(Exception[^\)]*\)

  # Mistake #2: Empty catches
  catch[^{]*\{\s*(//[^\n]*)?\s*\}

  # Mistake #3: throw ex
  throw ex;

  # Mistake #7: Fire-and-forget
  Task\.Run\(|Task\.Factory\.StartNew

  # And 6 more patterns...
  ```

**Step 4: Severity Classification**
- **CRITICAL**: Security vulnerabilities (stack trace exposure, missing global handler)
- **HIGH**: Production reliability issues (swallowed exceptions, broad catches)
- **MEDIUM**: Code quality issues (excessive try/catch, wrong status codes)
- **LOW**: Style and consistency issues

**Step 5: Findings Report**
- Generate comprehensive markdown report with:
  - Executive summary (violation count by severity)
  - File:line references for each issue
  - Code snippets showing violations
  - Recommended fixes for each
  - Priority-based fix roadmap

**Step 6: Knowledge Capture**
- Store findings in `.claude/runtime/logs/EXCEPTION_HANDLING_INVESTIGATION_{date}.md`
- Update project memory with patterns found
- Prepare for development phase

### Phase 2: Development (If --fix-all)

**Step 7: Orchestrate Default Workflow**
- Invoke default-workflow skill with findings report as context
- Create GitHub issue documenting all violations
- Set up worktree and branch for fixes
- Architect solution (GlobalExceptionHandler, Result<T>, etc.)
- Write comprehensive failing tests (TDD)
- Implement all fixes following architecture
- Three-agent review (reviewer, security, philosophy)
- Create PR with complete documentation

**Step 8: Validation**
- Verify all tests pass (unit, integration, E2E)
- Check CI validation
- Ensure security requirements met (zero stack traces)
- Validate performance acceptable (<5ms overhead)

## Input Specifications

**Required Inputs:**
- Project path: string (directory containing .csproj or .sln)

**Optional Inputs:**
- Priority filter: enum [`critical`, `high`, `medium`, `low`, `all`]
- Fix mode: boolean (investigate-only vs. auto-fix)

## Output Specifications

**Returns:**
- Investigation report (markdown) with all findings
- If --fix-all: Complete PR with fixes, tests, and documentation

**Side Effects:**
- Creates files in `.claude/runtime/logs/`
- If --fix-all: Creates worktree, branch, commits, PR
- Updates project memory with patterns

## Examples

### Example 1: Investigation Only (Default)

```bash
/dotnet-exception-handling ./src/MyApi
```

**Output**:
```markdown
# Exception Handling Investigation Report

Total Violations: 23
- CRITICAL: 1 (Missing global exception handler)
- HIGH: 8 (Broad catch blocks, swallowed exceptions)
- MEDIUM: 12 (Controller try/catch, wrong status codes)
- LOW: 2 (Style issues)

## CRITICAL Issues
1. Program.cs:45 - No global exception handler configured
   Severity: CRITICAL - Stack traces exposed to clients
   Fix: Implement IExceptionHandler...

[Complete report with all 23 violations]
```

### Example 2: Fix Critical Issues Only

```bash
/dotnet-exception-handling ./src/MyApi --priority critical --fix-all
```

**Output**:
```
Investigation complete: 1 CRITICAL issue found
Creating GitHub issue #42
Setting up worktree: ./worktrees/feat-issue-42-exception-handling-critical
Implementing GlobalExceptionHandler...
Tests created: 15
All tests passing ✅
PR created: #43
```

### Example 3: Comprehensive Fix (All Violations)

```bash
/dotnet-exception-handling ./src/MyApi --fix-all
```

**Output**:
```
Investigation complete: 23 violations found across 45 files
Creating GitHub issue #44
Architecting solution: 6 brick modules
Writing 67 tests following TDD...
Implementing all fixes...
PR created: #45 (draft)
Review scores: Reviewer 9/10, Security PASS, Philosophy 94/100
Converting to Ready for Review...
PR #45 ready for merge (CI passing)
```

## Investigation Strategy

### High-Risk Location Prioritization

1. **Background Workers** (Highest Priority)
   - `BackgroundService` implementations
   - Risk: Swallowed exceptions, fire-and-forget tasks

2. **API Controllers** (High Priority)
   - ASP.NET Core controllers
   - Risk: Missing global handler, wrong status codes

3. **Service Layer** (Medium Priority)
   - Business logic services
   - Risk: Broad catches, exceptions for control flow

4. **Data Layer** (Medium Priority)
   - EF Core DbContext, repositories
   - Risk: Missing EF-specific exception handling

### Search Patterns for Each Mistake

**Mistake #1: Catching Exception Too Broadly**
```csharp
catch \(Exception[^\)]*\)
```
Found in: Background workers, service layers

**Mistake #2: Swallowing Exceptions**
```csharp
catch[^{]*\{\s*(//[^\n]*)?\s*\}
```
Found in: Event publishing, cleanup code

**Mistake #3: throw ex**
```csharp
throw ex;
```
Found in: Legacy code, refactored methods

**Mistake #10: Missing Global Handler**
```csharp
# Searches for AddExceptionHandler/UseExceptionHandler
# If not found in Program.cs → CRITICAL violation
```

## Architecture Patterns

### GlobalExceptionHandler (IExceptionHandler)

**Purpose**: Central exception-to-HTTP response mapping

**Implementation Template**:
```csharp
public class GlobalExceptionHandler : IExceptionHandler
{
    public async ValueTask<bool> TryHandleAsync(
        HttpContext httpContext,
        Exception exception,
        CancellationToken cancellationToken)
    {
        var (statusCode, title) = exception switch
        {
            ArgumentException => (400, "Invalid request"),
            NotFoundException => (404, "Not found"),
            ConflictException => (409, "Conflict"),
            _ => (500, "An unexpected error occurred")
        };

        httpContext.Response.StatusCode = statusCode;
        await httpContext.Response.WriteAsJsonAsync(new ProblemDetails
        {
            Status = statusCode,
            Title = title,
            Detail = statusCode >= 500
                ? "An error occurred"
                : exception.Message
        }, cancellationToken);

        return true;
    }
}
```

**Registration**:
```csharp
builder.Services.AddExceptionHandler<GlobalExceptionHandler>();
builder.Services.AddProblemDetails();

app.UseExceptionHandler();
```

### Result<T> Pattern (Railway-Oriented Programming)

**Purpose**: Validation without exceptions

**Implementation**:
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
}
```

**Usage**:
```csharp
// Instead of throwing for validation
if (!CanTransition(from, to))
    throw new InvalidStateTransitionException(from, to);

// Use Result pattern
public Result<bool> CanTransition(State from, State to)
{
    if (!validTransitions.Contains((from, to)))
        return Result<bool>.Failure($"Cannot transition from {from} to {to}");

    return Result<bool>.Success(true);
}

// Caller checks result
var result = stateMachine.CanTransition(current, target);
if (!result.IsSuccess)
    return BadRequest(result.ErrorMessage);
```

## Integration Points

### ASP.NET Core Web APIs
- Registers `IExceptionHandler` in DI container
- Middleware pipeline: `UseExceptionHandler()` after `UseRouting()`
- ProblemDetails RFC 7807 compliance

### EF Core
- Wraps `SaveChangesAsync` with exception translation
- Maps `DbUpdateConcurrencyException` → 409 Conflict
- Maps `DbUpdateException` (constraints) → 409 with friendly message

### Azure SDK
- Catches `Azure.RequestFailedException` with status code preservation
- Handles `AuthenticationFailedException` from DefaultAzureCredential
- Maps Service Bus `ServiceBusException` by reason

### Background Services
- `BackgroundService.ExecuteAsync` exception boundaries
- Event publishing failures logged and propagated (not swallowed)
- Retry policies with exponential backoff

## Validation Rules

The skill validates:

1. **All .csproj files are .NET 6+** - Modern exception handling APIs
2. **ASP.NET Core projects have global handler** - IExceptionHandler registered
3. **No catch (Exception) except at top level** - Specific exception types only
4. **Background workers rethrow critical failures** - Event publishing, audit logging
5. **Custom exceptions have innerException support** - Preserve exception chains
6. **Controllers trust global handler** - Minimal try/catch
7. **State validation uses Result<T>** - No exceptions for expected validation failures
8. **Security: Zero stack traces in responses** - ProblemDetails only

## Success Criteria

**Investigation Phase:**
- [ ] All C# files scanned for exception patterns
- [ ] Findings categorized by severity (CRITICAL/HIGH/MEDIUM/LOW)
- [ ] Each violation has file:line reference and recommended fix
- [ ] Investigation report stored in .claude/runtime/logs/

**Fix Phase** (if --fix-all):
- [ ] Global exception handler implemented (if missing)
- [ ] Custom exceptions enhanced with innerException support
- [ ] All broad catch blocks replaced with specific types
- [ ] State validation uses Result<T> instead of exceptions
- [ ] Background workers never swallow critical failures
- [ ] Controllers trust global handler (minimal try/catch)
- [ ] Comprehensive tests created (60% unit, 30% integration, 10% E2E)
- [ ] Security validated: Zero stack traces exposed
- [ ] Performance acceptable: <5ms p99 overhead
- [ ] PR ready for merge with CI passing

## Navigation Guide

### When to Read Supporting Files

**reference.md** - Read when you need:
- Complete descriptions of all 10 exception handling mistakes
- Detailed fix templates for each mistake type
- Advanced patterns (retry policies, circuit breakers, Result<T> chaining)
- Security considerations and OWASP compliance

**examples.md** - Read when you need:
- Before/after code examples for each mistake
- Complete working implementations (GlobalExceptionHandler, Result<T>, DbContextExtensions)
- Real-world scenarios from production codebases
- Testing patterns for exception handling

**patterns.md** - Read when you need:
- Architectural decision guide (when to use global handler vs try/catch)
- Result<T> vs exception decision tree
- Background worker exception handling patterns
- Azure SDK and EF Core specific exception patterns

## Workflow Integration

This skill orchestrates two canonical workflows:

1. **Investigation Workflow** (6 phases):
   - Scope Definition
   - Exploration Strategy
   - Parallel Deep Dives (5 specialized agents)
   - Verification & Testing
   - Synthesis
   - Knowledge Capture

2. **Default Workflow** (23 steps - if --fix-all):
   - Requirements Clarification
   - Architecture Design
   - TDD (tests first)
   - Implementation
   - Review (3 agents)
   - CI/CD validation
   - PR merge

## Example Workflow Execution

**Command**: `/dotnet-exception-handling ./src/MyService --fix-all`

**Execution Flow**:

```
1. [Investigation Phase - 6 Steps]
   ├─ Detect .NET project: Found MyService.csproj (.NET 10)
   ├─ Deploy 5 analyzer agents in parallel
   ├─ Find violations: 34 issues across 28 files
   ├─ Categorize: CRITICAL(1), HIGH(12), MEDIUM(18), LOW(3)
   ├─ Generate report: .claude/runtime/logs/EXCEPTION_INVESTIGATION_2026-02-10.md
   └─ Estimated effort: 12-16 hours

2. [Development Phase - 23 Steps]
   ├─ Create GitHub issue #42
   ├─ Create worktree: ./worktrees/feat-issue-42-exception-handling
   ├─ Design: GlobalExceptionHandler + Result<T> + 4 modules
   ├─ Write 45 TDD tests (failing)
   ├─ Implement all 34 fixes
   ├─ Three-agent review: PASS (reviewer, security, philosophy)
   ├─ CI validation: All checks passing
   └─ PR #43 ready for merge

3. [Summary]
   ├─ Violations fixed: 34/34 (100%)
   ├─ Tests created: 45 (60/30/10 pyramid)
   ├─ Philosophy score: 93/100 (A)
   ├─ Security: PASS (zero stack traces)
   └─ Ready for production deployment
```

## Philosophy Compliance

This skill follows amplihack principles:

**Ruthless Simplicity**:
- Removes defensive try/catch clutter (typical reduction: 200+ lines)
- Controllers trust global exception handler
- Result<T> for validation (eliminates exception overhead)

**Zero-BS**:
- Complete, working implementations (no TODOs or stubs)
- All fixes validated with tests
- Production-ready code only

**Brick Philosophy**:
- Self-contained modules (GlobalExceptionHandler, Result<T>, DbContextExtensions)
- Clear contracts (IExceptionHandler, Result pattern)
- Regeneratable from specifications

**Security-First**:
- Zero stack trace exposure
- ProblemDetails RFC 7807 compliance
- Sensitive data never in error messages

## References

- **Article**: [Top 10 Exception Handling Mistakes in .NET](https://abp.io/community/articles/top-10-exception-handling-mistakes-in-net-jhm8wzvg)
- **Microsoft Docs**: [Best Practices for Exceptions](https://learn.microsoft.com/en-us/dotnet/standard/exceptions/best-practices-for-exceptions)
- **ASP.NET Core**: [Handle Errors in Web APIs](https://learn.microsoft.com/en-us/aspnet/core/web-api/handle-errors)
- **Investigation Workflow**: `~/.amplihack/.claude/workflow/INVESTIGATION_WORKFLOW.md`
- **Default Workflow**: `~/.amplihack/.claude/workflow/DEFAULT_WORKFLOW.md`

## Related Skills

- `amplihack:security` - Security-focused code review
- `amplihack:reviewer` - General code quality review
- `amplihack:tester` - Test coverage analysis
- `amplihack:cleanup` - Ruthless simplification

## Maintenance

**Version History:**
- v1.0.0 (2026-02-10): Initial implementation based on CyberGym investigation

**Known Limitations:**
- Requires .NET 6+ for modern exception handling APIs (IExceptionHandler)
- Result<T> pattern requires C# 9+ (record types, init properties)
- Some patterns specific to ASP.NET Core (may not apply to class libraries)

**Future Enhancements:**
- Support for .NET Framework 4.x (different exception handling patterns)
- Integration with existing monitoring tools (Application Insights, Serilog)
- Automated migration scripts for common refactoring patterns
