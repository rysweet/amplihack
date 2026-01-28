# Framework Injection Architecture

Explains why amplihack injects AMPLIHACK.md on every message and how the UserPromptSubmit hook compares files to make intelligent injection decisions.

## The Problem

Users need two types of instructions in their CLAUDE.md:

1. **Project-specific context**: "This is a React app using TypeScript"
2. **Framework behaviors**: "Use amplihack agents, follow philosophy, etc."

When users customize CLAUDE.md for their project, they lose framework instructions. When they copy AMPLIHACK.md as CLAUDE.md, they lose project customization.

This is a genuine conflict - you can't have both in CLAUDE.md without duplication and maintenance burden.

## The Solution

**UserPromptSubmit hook automatically injects AMPLIHACK.md when it differs from CLAUDE.md.**

The hook runs on every message and:

1. Compares CLAUDE.md vs AMPLIHACK.md (content comparison)
2. Injects AMPLIHACK.md if files differ
3. Skips injection if files are identical
4. Uses mtime caching for performance (~99% cache hit rate)

This allows:

- **Project customization**: Edit CLAUDE.md for your project
- **Framework behaviors**: Get amplihack instructions automatically
- **No duplication**: AMPLIHACK.md injected only when needed
- **Fast operation**: Cache prevents repeated file reads

## How It Works

### File Comparison Strategy

```
On every user message:
    ↓
Read CLAUDE.md (project root)
Read AMPLIHACK.md (~/.amplihack/.claude/ or plugin)
    ↓
Normalize whitespace
Compare contents
    ↓
IF files differ → Inject AMPLIHACK.md
IF files identical → Skip injection
    ↓
Cache comparison result using (amplihack_mtime, claude_mtime)
```

### Injection Order

Context is injected in deliberate order:

1. **User preferences** (from USER_PREFERENCES.md)
   - Behavioral guidance: communication style, verbosity, etc.
2. **Agent memories** (if agents mentioned in prompt)
   - Context-specific knowledge for mentioned agents
3. **Framework instructions** (AMPLIHACK.md)
   - Full framework behaviors and patterns

This order ensures preferences override framework defaults, and framework instructions are available last as fallback guidance.

### Caching Mechanism

The hook caches comparison results using modification times:

```python
cache_key = (amplihack_mtime, claude_mtime)

# Cache hit: File mtimes haven't changed
if cached_key == cache_key:
    return cached_result

# Cache miss: Read and compare files
amplihack_content = read(AMPLIHACK.md)
claude_content = read(CLAUDE.md)
result = compare(amplihack_content, claude_content)
cache[cache_key] = result
```

**Performance**: ~99% cache hit rate after first message means <1ms overhead per message.

## Why This Location

AMPLIHACK.md is found in priority order:

1. **Plugin location** (`$CLAUDE_PLUGIN_ROOT/AMPLIHACK.md`) - Claude Code plugin mode
2. **Centralized staging** (`~/.amplihack/.claude/AMPLIHACK.md`) - All tools
3. **Per-project** (`.claude/AMPLIHACK.md`) - Development mode

This search order ensures correct framework instructions regardless of deployment mode.

## Design Decisions

### Why Not Always Inject?

Always injecting wastes tokens and time when CLAUDE.md already contains framework instructions.

In amplihack's own repository, CLAUDE.md is a symlink to AMPLIHACK.md. Injecting would duplicate ~2000 lines of instructions on every message.

### Why Content Comparison Not Filename?

Filenames don't indicate content. Users might:

- Copy AMPLIHACK.md to CLAUDE.md (files identical, skip injection)
- Modify CLAUDE.md slightly (files differ, inject)
- Symlink CLAUDE.md → AMPLIHACK.md (files identical, skip)

Content comparison handles all cases correctly.

### Why Whitespace Normalization?

Formatting differences (line endings, trailing spaces) shouldn't trigger injection:

```python
if claude_content.strip() == amplihack_content.strip():
    # Files are effectively identical
    skip_injection()
```

This prevents spurious injections from formatting-only changes.

### Why Cache on Both mtimes?

The hook caches on `(amplihack_mtime, claude_mtime)` because:

- If AMPLIHACK.md changes (package update), re-compare
- If CLAUDE.md changes (user edit), re-compare
- If neither changes (99% of messages), use cache

This provides perfect invalidation without re-reading files.

## Performance Characteristics

**First message per session**: ~50-100ms

- Read CLAUDE.md (~25ms)
- Read AMPLIHACK.md (~25ms)
- Normalize and compare (~10ms)
- Build injection context (~10ms)

**Subsequent messages**: <1ms

- Check mtimes (instant)
- Return cached result
- No file I/O

**Cache hit rate**: ~99% (invalidated only when files change)

## Deployment Modes

### Plugin Mode (Claude Code)

```
AMPLIHACK.md: $CLAUDE_PLUGIN_ROOT/AMPLIHACK.md
CLAUDE.md: project_root/CLAUDE.md

Hook compares across directories automatically.
```

### Centralized Staging (All Tools)

```
AMPLIHACK.md: ~/.amplihack/.claude/AMPLIHACK.md
CLAUDE.md: project_root/CLAUDE.md

Hook uses centralized framework instructions.
```

### Per-Project Mode (Development)

```
AMPLIHACK.md: project_root/.claude/AMPLIHACK.md
CLAUDE.md: project_root/CLAUDE.md

Hook operates within project directory.
```

The hook handles all three modes automatically without configuration.

## Error Handling

The hook uses graceful degradation:

- **AMPLIHACK.md missing**: Log warning, skip injection, continue
- **CLAUDE.md missing**: Treat as empty, inject AMPLIHACK.md
- **Read error**: Log warning, skip injection, continue
- **Compare error**: Log warning, skip injection, continue

**Never blocks Claude** - all errors result in empty injection and exit 0.

## Comparison to Other Approaches

### Alternative: Require AMPLIHACK.md in CLAUDE.md

**Rejected** because:

- Users must manually include AMPLIHACK.md
- Changes to framework require manual updates
- Easy to forget or get out of sync

### Alternative: Separate Framework Flag

**Rejected** because:

- Requires user configuration
- Doesn't handle custom CLAUDE.md case
- More complexity for users

### Alternative: Always Inject

**Rejected** because:

- Wastes tokens when files identical
- Slower performance
- Unnecessary in amplihack's own repo

The content-comparison approach handles all cases optimally.

## Security Considerations

Files compared are:

- **User-controlled**: Both CLAUDE.md and AMPLIHACK.md
- **Read-only**: Hook never modifies files
- **Isolated**: Comparison happens in hook process
- **Logged**: All activity logged for audit

No privilege escalation or file manipulation occurs.

## Related

- [Verify Framework Injection](../howto/verify-framework-injection.md) - Check if injection works
- [UserPromptSubmit Hook API](../reference/user-prompt-submit-hook-api.md) - Developer details
- [Unified Staging Architecture](unified-staging-architecture.md) - Where AMPLIHACK.md lives
