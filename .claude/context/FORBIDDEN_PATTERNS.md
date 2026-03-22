# Forbidden Patterns — Things AI Agents Must Never Do

These patterns are **absolutely prohibited** in any code generated or modified by AI agents.
They represent the most common ways that agents silently degrade software quality. Every
pattern here has been observed in real agent-generated code and causes real production failures.

**The unifying principle: Errors must be visible. Failures must be loud. Nothing is silently
swallowed, dropped, degraded, or hidden.**

---

## 1. Error Swallowing & Broad Catches

Catch blocks that suppress errors are the most common agent-introduced defect. A catch block
that does not re-throw (or convert to an explicit, visible failure) is a bug factory.

**NEVER:**

```csharp
// C# — catch that returns a default instead of propagating
catch (Exception) { return null; }
catch (Exception) { return false; }
catch (Exception) { return string.Empty; }
catch (Exception) { return new List<T>(); }
catch (Exception ex) { _logger.LogWarning(ex, "..."); }  // log-only, no re-throw
catch { }  // empty catch block
```

```python
# Python — bare except or overly broad catch
except Exception:
    pass
except Exception:
    return None
except Exception as e:
    logger.warning(f"Error: {e}")  # log-only, no re-raise
except:  # bare except — catches SystemExit, KeyboardInterrupt
    pass
```

```typescript
// TypeScript/JavaScript — swallowing errors
catch (e) { return undefined; }
catch (e) { console.warn(e); }  // log-only, no re-throw
catch (e) { /* empty */ }
catch (e) { return []; }  // returning empty collection hides failure
```

```go
// Go — ignoring error returns
result, _ := someFunction()         // discarded error
if err != nil { return nil, nil }   // converting error to nil
if err != nil { log.Println(err) }  // log-only, no return of error
```

```java
// Java — broad catch blocks
catch (Exception e) { return null; }
catch (Exception e) { e.printStackTrace(); }  // log-only, no re-throw
catch (Throwable t) { /* empty */ }
```

```rust
// Rust — suppressing Results
let _ = fallible_function();             // discarded Result
.unwrap_or_default()  // on Results where the error matters
if let Err(e) = result { eprintln!("{e}"); }  // log-only, no propagation
```

**INSTEAD:** Let exceptions propagate. Use typed/specific catches only when you have a
genuine recovery strategy. If you catch, you must either re-throw, return an error type,
or take a **visible** corrective action.

---

## 2. Silent Fallbacks & Default Values That Hide Failures

A fallback is a silent failure. If something should have a value and doesn't, that is an
error — not an opportunity to substitute a default.

**NEVER:**

```csharp
// C# — null-coalescing that silently changes behavior
var timeout = config.GetValue<int?>("Timeout") ?? 30;      // missing config = silent default
var endpoint = Environment.GetEnvironmentVariable("API_URL") ?? "http://localhost";
if (string.IsNullOrEmpty(connectionString)) return;         // silently skips work
```

```python
# Python — getattr/dict.get hiding missing values
timeout = config.get("timeout", 30)           # missing config = silent default
endpoint = os.environ.get("API_URL", "http://localhost")
value = getattr(obj, "attr", None)            # silently returns None if attr missing
result = data.get("key") or default_value     # falsy values silently replaced
```

```typescript
// TypeScript/JavaScript — optional chaining eating nulls
const value = config?.settings?.timeout ?? 30; // entire chain can be null silently
const result = response?.data?.items || []; // failure looks like empty success
```

```go
// Go — zero-value fallbacks
timeout := config.Timeout  // zero value of int is 0, silently wrong
if endpoint == "" { endpoint = "http://localhost" }  // hiding missing config
```

**INSTEAD:** Validate configuration at startup. Fail loudly if required values are missing.
Use explicit validation functions, not fallback defaults.

---

## 3. Data Loss & Result Dropping

Discarding return values, fire-and-forget async, and silent truncation all cause data loss.

**NEVER:**

```csharp
// C# — fire-and-forget, unchecked results
_ = SomeAsyncMethod();                          // fire-and-forget, errors lost
Task.WhenAll(tasks);                            // individual failures not checked
await httpClient.PostAsync(url, content);        // response status not checked
items.Take(100);                                // silent truncation without logging
signalRHub.SendAsync("Notify", data);           // broadcast failure silently swallowed
```

```python
# Python — discarded futures, unchecked results
asyncio.create_task(some_coroutine())           # fire-and-forget
asyncio.gather(*tasks)                          # individual failures hidden by default
requests.post(url, json=data)                   # response not checked
results[:100]                                   # silent truncation
subprocess.run(cmd)                             # return code not checked
```

```typescript
// TypeScript/JavaScript — unhandled promises
someAsyncFunction(); // no await, no .catch()
Promise.all(promises); // unhandled rejections
fetch(url, { method: "POST" }); // response not checked
array.slice(0, 100); // silent truncation without logging
```

```go
// Go — discarded returns
go someFunction()                 // goroutine errors lost
http.Post(url, contentType, body) // response not checked
io.Copy(dst, src)                 // bytes written not checked
```

**INSTEAD:** Always await async operations. Always check return values. If you must
truncate, log it. If you must fire-and-forget, use a supervised error channel.

---

## 4. Shell Scripting — NEVER Hide Errors

Shell scripts are the worst offenders for silent failure. These patterns are **absolutely
forbidden** in any shell script, Makefile, CI pipeline, or Dockerfile.

**NEVER:**

```bash
# Suppressing exit codes
some_command || true                  # FORBIDDEN — hides failures
some_command || :                     # FORBIDDEN — same thing

# Suppressing output (hides error messages)
some_command > /dev/null 2>&1        # FORBIDDEN — errors invisible
some_command 2>/dev/null             # FORBIDDEN — stderr suppressed
some_command &>/dev/null             # FORBIDDEN — all output suppressed

# Ignoring return codes
set +e                               # FORBIDDEN — disables error checking
command1; command2                   # FORBIDDEN if command1 failure should stop command2

# Fallback commands
some_command || fallback_command     # FORBIDDEN — fallback is a silent failure
tool --flag 2>/dev/null || alt_tool  # FORBIDDEN — hides why first tool failed
```

**INSTEAD:**

```bash
set -euo pipefail                    # REQUIRED at top of every script
some_command                         # let it fail loudly
if ! some_command; then
    echo "ERROR: some_command failed" >&2
    exit 1
fi
```

**The only acceptable exception** to output suppression is when the _success output_ of a
command is genuinely unwanted noise AND stderr is still visible:

```bash
some_command > /dev/null             # OK ONLY if stderr preserved AND exit code checked
```

---

## 5. Retry Logic That Eventually Gives Up Silently

**NEVER:**

```csharp
// C# — retry that silently stops trying
for (int i = 0; i < 3; i++) {
    try { await DoWork(); return; }
    catch { await Task.Delay(1000); }
}
// Falls through silently after 3 failures
```

```python
# Python — same pattern
for attempt in range(3):
    try:
        do_work()
        return
    except Exception:
        time.sleep(1)
# Silent failure after retries exhausted
```

**INSTEAD:** After retries are exhausted, raise/throw the last exception. Never fall
through silently.

---

## 6. Async Anti-Patterns

**NEVER:**

```csharp
async void SomeMethod() { }           // async void — exceptions cannot be caught
task.Result;                            // sync-over-async — causes deadlocks
task.Wait();                            // sync-over-async — causes deadlocks
```

```python
# Unobserved coroutines
async def handler():
    some_coroutine()                    # coroutine created but never awaited
```

```typescript
async function handler() {
  someAsyncFunction(); // promise created but never awaited
}
```

**ALWAYS** propagate CancellationTokens, dispose CancellationTokenSources and Timers,
and await all async operations.

---

## 7. Configuration & Environment Divergence

**NEVER:**

- Define environment variables in one place (e.g., docker-compose, AppHost, Bicep) that
  services read with silent fallback defaults
- Have services expect configuration that the deployment system doesn't provide
- Use `IsDevelopment()` guards that could accidentally apply in staging/production

**INSTEAD:** Validate all required configuration at service startup. If a required
environment variable or config key is missing, fail immediately with a clear error message.

---

## 8. Validation Gaps

**NEVER:**

- Accept user input without validation at API boundaries
- Use string interpolation in SQL, GraphQL, or Cypher queries (injection risk)
- Allow unbounded queries (missing pagination limits, missing request size limits)
- Parse enums from user input without validation
- Trust deserialized objects from external sources without null checks

**INSTEAD:** Validate at the boundary. Use parameterized queries. Set explicit limits.

---

## 9. Health Checks & Observability

**NEVER:**

- Report `Degraded` when the service is actually `Unhealthy`
- Have background workers whose failures don't surface to health endpoints
- Use log-only error handling with no metric/counter escalation
- Treat permanent errors (malformed JSON) as transient (retry them)
- Mark partial success as full success

**INSTEAD:** Health checks must reflect actual health. Errors must produce metrics.
Permanent vs transient errors must be distinguished.
