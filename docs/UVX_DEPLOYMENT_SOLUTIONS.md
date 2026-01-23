# UVX Deployment Solutions

## Problem Statement

When users run AmplifyHack via UVX:

```bash
uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding amplihack launch
```

The framework files (`~/.amplihack/.claude/`, `CLAUDE.md`, etc.) are downloaded to UVX's temporary cache directory, but Claude Code expects them in the working directory for `@` imports to work.

## Solution Comparison

### Option 1: Automatic Staging (Current Implementation)

**How it works:**

1. Detect UVX deployment automatically
2. Find framework files in UVX cache/installation
3. Copy essential files to working directory
4. Clean up on session end

**User Experience:**

```bash
# Simple command - everything automatic
uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding amplihack launch
```

**Pros:**

- ✅ Transparent user experience
- ✅ No extra CLI arguments needed
- ✅ Works with existing `@` import expectations
- ✅ Automatic cleanup
- ✅ Works with any UVX cache structure

**Cons:**

- ❌ More complex implementation
- ❌ File copying overhead
- ❌ Potential permission issues
- ❌ May not find files if UVX structure changes

### Option 2: Claude Code --add-dir (Alternative)

**How it works:**

1. User specifies UVX installation path manually
2. Claude Code includes that directory for `@` imports
3. No file copying needed

**User Experience:**

```bash
# User must know/find UVX path
uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding amplihack launch --add-dir $(uvx cache dir)/.../MicrosoftHackathon2025-AgenticCoding
```

**Pros:**

- ✅ Simpler implementation
- ✅ No file copying overhead
- ✅ Direct access to source files
- ✅ No cleanup needed

**Cons:**

- ❌ User must find UVX installation path
- ❌ More complex command line
- ❌ Not transparent
- ❌ Requires understanding of UVX internals

### Option 3: Hybrid Approach (Recommended)

**Implementation:**

1. Try automatic staging first (transparent)
2. If staging fails, provide fallback instructions with `--add-dir`
3. Make UVX path discovery available as utility

**User Experience:**

```bash
# Primary: Automatic (our current implementation)
uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding amplihack launch

# Fallback: Manual when automatic fails
amplihack find-uvx-path  # Helper command
uvx --from git+... amplihack launch --add-dir /path/from/helper
```

## Current Implementation Details

### Files Created:

- `src/amplihack/utils/uvx_staging.py` - Main staging logic
- `tests/test_uvx_staging.py` - Comprehensive tests
- Enhanced `FrameworkPathResolver` - Integration point

### Key Features:

1. **Multi-Strategy UVX Detection:**
   - Environment variables (`UV_PYTHON`, `UVX_CACHE`)
   - Python path analysis
   - Framework file availability check

2. **Smart Framework Discovery:**
   - Environment variable (`AMPLIHACK_ROOT`)
   - Python path search
   - UVX cache directory search

3. **Safe File Staging:**
   - Never overwrites existing files
   - Stages only essential files (`~/.amplihack/.claude/`, `CLAUDE.md`, `DISCOVERIES.md`)
   - Automatic cleanup on exit

4. **Graceful Fallbacks:**
   - Falls back to environment variables if staging fails
   - Silent failures don't break sessions

## Testing Results

### Local Deployment ✅

- Framework files found correctly
- No UVX detection triggered
- Normal operation maintained

### UVX Deployment Simulation ✅

- UVX environment detected correctly
- Framework files discovered in mock locations
- Staging successful with proper cleanup
- Integration with FrameworkPathResolver working

## Recommendation

**Keep the current automatic staging implementation** because:

1. **Better User Experience**: Users don't need to understand UVX internals
2. **Backward Compatibility**: Existing workflows continue to work
3. **Robust Fallbacks**: Multiple strategies increase success rate
4. **Test Coverage**: Comprehensive testing ensures reliability

The `--add-dir` option remains valuable as a:

- **Power User Feature**: For those who prefer explicit control
- **Debugging Tool**: When automatic staging fails
- **Fallback Option**: When UVX structure changes

## Future Improvements

1. **Add UVX path discovery utility**: `amplihack find-uvx-path`
2. **Environment variable override**: `AMPLIHACK_STAGING=false` to disable
3. **Verbose staging option**: `amplihack launch --verbose-staging`
4. **Integration testing**: Test with actual UVX installations

## Conclusion

The automatic staging approach provides the best balance of:

- User experience (transparent)
- Reliability (multiple fallbacks)
- Maintainability (comprehensive tests)

While `--add-dir` is simpler to implement, the staging approach better serves our goal of making AmplifyHack "just work" for users regardless of deployment method.
