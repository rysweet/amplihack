# Smart Memory Management for Claude Code Launch

**Automatic memory optimization that prevents out-of-memory crashes when launching Claude Code**

## What is Smart Memory Management?

Smart Memory Management be an intelligent system that automatically detects yer system's available RAM and configures Node.js memory settings fer optimal Claude Code performance. It prevents OOM (Out Of Memory) crashes by settin' appropriate memory limits before launch.

## Why Use Smart Memory Management?

Smart Memory Management helps prevent common launch failures:

✅ **Prevents OOM crashes** - Automatically configures memory before problems occur
✅ **Optimized performance** - Uses 25% of available RAM (minimum 8GB)
✅ **User consent first** - Always asks before changing settings
✅ **Preserves existing config** - Honors user's NODE_OPTIONS if already set
✅ **Safety warnings** - Alerts when memory be below recommended threshold

## How It Works

When ye launch amplihack:

1. **Detects system RAM** - Reads total memory from system
2. **Calculates optimal limit** - Uses formula: `max(8192, total_ram_mb // 4)` capped at 32GB
3. **Checks existing settings** - Preserves user's NODE_OPTIONS if present
4. **Requests consent** - Asks before applying new settings
5. **Applies configuration** - Sets `NODE_OPTIONS=--max-old-space-size=N` for session

### The Memory Formula

Smart Memory Management uses a proven formula fer memory allocation:

```
N = max(8192, total_ram_mb // 4)

Where:
- Minimum: 8192 MB (8 GB)
- Maximum: 32768 MB (32 GB)
- Default: 25% of total system RAM
```

**Example Calculations:**

| System RAM | Formula | Result | Notes |
|-----------|---------|--------|-------|
| 16 GB | max(8192, 4096) | 8192 MB | Uses minimum |
| 32 GB | max(8192, 8192) | 8192 MB | Balanced |
| 64 GB | max(8192, 16384) | 16384 MB | 25% allocation |
| 128 GB | max(8192, 32768) | 32768 MB | Capped at max |
| 256 GB | max(8192, 64000) | 32768 MB | Capped at max |

## Quick Start

### Enable Smart Memory Management

Smart Memory Management be enabled by default when ye launch amplihack. No setup required!

```bash
# Normal launch - memory management activates automatically
amplihack

# First launch output example:
# Detected 32GB system RAM
# Recommended NODE_OPTIONS: --max-old-space-size=8192
# Apply this setting? (y/n):
```

### Disable Smart Memory Management

If ye need to manage memory manually:

```bash
# Method 1: Set your own NODE_OPTIONS (highest priority)
export NODE_OPTIONS="--max-old-space-size=16384"
amplihack

# Method 2: Environment variable to skip detection
export AMPLIHACK_SKIP_MEMORY_CHECK=1
amplihack

# Method 3: Use minimal memory
export AMPLIHACK_MINIMAL_MEMORY=1  # Forces 8192 MB
amplihack
```

## Common Scenarios

### Scenario 1: First Launch on New System

```bash
$ amplihack

Ahoy! Detectin' system memory...
System RAM: 64 GB
Recommended memory limit: 16384 MB (16 GB)

This prevents Claude Code from crashin' due to memory limits.
Apply NODE_OPTIONS=--max-old-space-size=16384? (y/n): y

Applyin' memory settings fer this session...
Launchin' Claude Code with optimized memory...
```

### Scenario 2: User Has Existing NODE_OPTIONS

```bash
$ export NODE_OPTIONS="--max-old-space-size=20480"
$ amplihack

Detected existing NODE_OPTIONS: --max-old-space-size=20480
Honorin' yer custom memory settings (20 GB)
Launchin' Claude Code...
```

### Scenario 3: Low Memory System

```bash
$ amplihack

Ahoy! Detectin' system memory...
System RAM: 16 GB
Recommended memory limit: 8192 MB (8 GB)

⚠️  WARNING: Yer system has 16 GB RAM. Recommended minimum be 32 GB fer optimal performance.
Claude Code may experience slowdowns or crashes with limited memory.

Apply NODE_OPTIONS=--max-old-space-size=8192? (y/n): y

Applyin' memory settings fer this session...
Launchin' Claude Code with minimum recommended memory...
```

### Scenario 4: High Memory Server

```bash
$ amplihack

Ahoy! Detectin' system memory...
System RAM: 256 GB
Recommended memory limit: 32768 MB (32 GB)

Note: Memory capped at 32 GB fer stability.
Apply NODE_OPTIONS=--max-old-space-size=32768? (y/n): y

Applyin' memory settings fer this session...
Launchin' Claude Code with maximum memory allocation...
```

## Configuration

### Environment Variables

Smart Memory Management supports these environment variables:

| Variable | Purpose | Values | Default |
|----------|---------|--------|---------|
| `NODE_OPTIONS` | Manual memory control | `--max-old-space-size=N` | None |
| `AMPLIHACK_SKIP_MEMORY_CHECK` | Disable detection | `1` or `true` | Not set |
| `AMPLIHACK_MINIMAL_MEMORY` | Force minimum | `1` or `true` | Not set |
| `AMPLIHACK_MEMORY_LIMIT` | Override formula | Integer (MB) | Calculated |

### Override Memory Calculation

Ye can override the automatic calculation:

```bash
# Set specific memory limit (in MB)
export AMPLIHACK_MEMORY_LIMIT=12288  # 12 GB
amplihack
```

### Persistence Across Sessions

Settings be per-session by default. To make permanent:

```bash
# Add to yer shell profile (~/.bashrc, ~/.zshrc, etc.)
echo 'export NODE_OPTIONS="--max-old-space-size=16384"' >> ~/.bashrc
source ~/.bashrc
```

## Troubleshooting

### Problem: Still Getting OOM Crashes

**Symptoms:**
- Claude Code crashes with "JavaScript heap out of memory"
- Process terminates unexpectedly during large operations

**Solutions:**

1. Check if settings be applied:
   ```bash
   echo $NODE_OPTIONS
   # Should show: --max-old-space-size=NNNN
   ```

2. Manually increase memory:
   ```bash
   export NODE_OPTIONS="--max-old-space-size=16384"
   amplihack
   ```

3. Verify system has enough free RAM:
   ```bash
   # Linux/Mac
   free -h

   # Check for available memory (should be > 8GB)
   ```

### Problem: Memory Detection Not Working

**Symptoms:**
- No memory detection message at launch
- Launches directly without memory check

**Solutions:**

1. Check if ye have existing NODE_OPTIONS:
   ```bash
   echo $NODE_OPTIONS
   # If set, amplihack honors yer choice
   ```

2. Check if memory check be disabled:
   ```bash
   echo $AMPLIHACK_SKIP_MEMORY_CHECK
   # If "1", detection be disabled
   ```

3. Force memory detection:
   ```bash
   unset NODE_OPTIONS
   unset AMPLIHACK_SKIP_MEMORY_CHECK
   amplihack
   ```

### Problem: Warning About Low Memory

**Symptoms:**
- Warning message: "System has less than 32 GB RAM"
- Performance slowdowns during large operations

**Solutions:**

1. This be informational - Claude Code will still work with 8 GB minimum

2. If experiencing performance issues, close other memory-heavy applications:
   ```bash
   # Check memory usage
   top -o MEM
   # Close unnecessary applications
   ```

3. Consider upgrading system RAM for optimal experience (32 GB recommended)

4. Use `AMPLIHACK_MINIMAL_MEMORY` to reduce memory allocation if needed:
   ```bash
   export AMPLIHACK_MINIMAL_MEMORY=1
   amplihack
   ```

### Problem: Custom NODE_OPTIONS Be Ignored

**Symptoms:**
- Set NODE_OPTIONS but amplihack changes it
- Memory settings don't match what ye specified

**Solution:**

Smart Memory Management always honors existing NODE_OPTIONS. If this be happenin':

1. Verify yer NODE_OPTIONS be exported:
   ```bash
   export NODE_OPTIONS="--max-old-space-size=20480"
   echo $NODE_OPTIONS  # Should show yer value
   amplihack
   ```

2. Check if another tool be modifying NODE_OPTIONS in background

3. Set NODE_OPTIONS immediately before launch:
   ```bash
   NODE_OPTIONS="--max-old-space-size=20480" amplihack
   ```

## Technical Details

### Memory Detection Implementation

Smart Memory Management detects system RAM using platform-specific methods:

**Linux:**
```bash
# Uses /proc/meminfo
grep MemTotal /proc/meminfo | awk '{print $2 / 1024}'
```

**macOS:**
```bash
# Uses sysctl
sysctl -n hw.memsize | awk '{print $1 / 1024 / 1024}'
```

**Windows (WSL/Git Bash):**
```bash
# Uses wmic or systeminfo
wmic OS get TotalVisibleMemorySize | tail -1 | awk '{print $1 / 1024}'
```

### Why These Memory Limits?

The formula `max(8192, total_ram_mb // 4)` capped at 32GB be based on:

1. **8 GB Minimum**: Claude Code requires at least 8 GB fer stable operation
2. **25% System RAM**: Leaves 75% fer OS and other applications
3. **32 GB Maximum**: Prevents excessive memory allocation that can cause system instability
4. **Node.js V8 Limits**: V8 engine performs best with memory allocations between 8-32 GB

### Memory Formula Rationale

| Factor | Reasoning |
|--------|-----------|
| Minimum 8GB | Prevents crashes during large context operations |
| 25% of RAM | Balances performance with system stability |
| Maximum 32GB | V8 garbage collection optimizations, diminishing returns beyond 32GB |
| User override | Power users may need different allocations fer specific workloads |

## Advanced Usage

### Debugging Memory Issues

Enable detailed memory logging:

```bash
export NODE_OPTIONS="--max-old-space-size=16384 --expose-gc --trace-gc"
amplihack

# Logs will show garbage collection activity
```

### Testing Different Memory Allocations

Benchmark different memory settings:

```bash
# Test with 12 GB
NODE_OPTIONS="--max-old-space-size=12288" amplihack
# Run yer workload, note performance

# Test with 16 GB
NODE_OPTIONS="--max-old-space-size=16384" amplihack
# Run same workload, compare performance

# Test with 24 GB
NODE_OPTIONS="--max-old-space-size=24576" amplihack
# Run same workload, compare performance
```

### CI/CD Integration

Fer automated environments:

```bash
# GitHub Actions / GitLab CI
export NODE_OPTIONS="--max-old-space-size=8192"
export AMPLIHACK_SKIP_MEMORY_CHECK=1  # Skip interactive prompts
amplihack --non-interactive
```

### Docker Containers

When runnin' in containers:

```dockerfile
# Dockerfile
FROM node:20
ENV NODE_OPTIONS="--max-old-space-size=8192"
ENV AMPLIHACK_SKIP_MEMORY_CHECK=1
```

## Best Practices

1. **Let automatic detection work** - Default settings be optimized fer most systems
2. **Monitor memory usage** - Use `top` or Activity Monitor to verify allocation
3. **Increase gradually** - If needin' more memory, increase by 4GB increments
4. **Keep under 50% system RAM** - Leave room fer OS and other applications
5. **Document custom settings** - Note why ye chose specific values fer team members

## Integration with Other Features

Smart Memory Management integrates seamlessly with:

- **UVX Deployment** - Memory settings be preserved when usin' `uvx amplihack`
- **Profile Management** - Different profiles can have different memory settings
- **Interactive Installation** - Memory configuration be part of initial setup
- **Power Steering** - Checks memory settings before completin' sessions

## Related Documentation

- [Prerequisites](../PREREQUISITES.md) - System requirements including RAM recommendations
- [Interactive Installation](../INTERACTIVE_INSTALLATION.md) - Initial setup includin' memory configuration
- [Profile Management](../PROFILE_MANAGEMENT.md) - Per-profile memory settings
- [Troubleshooting](../troubleshooting/README.md) - General troubleshootin' guide

---

**Implementation Status**: [IMPLEMENTED]

This feature has been implemented as part of Issue #1953.
