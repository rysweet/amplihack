# Copilot Launcher Audit - Potential Issues & Improvements

## Current Implementation Analysis

### What Happens On Every `amplihack copilot` Launch:

1. Check if Copilot CLI installed (line 46)
2. Auto-install if missing (line 47)
3. Write launcher_context.json (line 53-60)
4. Copy 35 agent files from package to user's .github/agents/ (line 82-89)
5. Inject preferences into AGENTS.md (line 91-95)
6. Launch Copilot (line 113)

## Potential Issues Found

### 🚨 Issue #1: Performance - Copying 35 Files Every Launch

**Current Code** (line 85-89):
```python
for source_file in source_agents.rglob("*.md"):
    dest_file = agents_dest / source_file.name
    # Always copy to get latest (fast operation)
    shutil.copy2(source_file, dest_file)
```

**Problem**:
- Copies **35 agent files** on EVERY launch
- Even if files haven't changed
- Line 88 comment says "fast operation" but is it necessary?

**Measurement**:
- 35 files × ~200 lines avg × file I/O = ~7,000 lines of file I/O per launch
- On slow filesystems (network drives, cloud sync) this could be noticeable

**Impact**: Medium - Adds unnecessary startup latency

**Suggested Fix**:
```python
# Check if already copied and up-to-date
if dest_file.exists():
    src_mtime = source_file.stat().st_mtime
    dest_mtime = dest_file.stat().st_mtime
    if dest_mtime >= src_mtime:
        continue  # Skip, already up-to-date

shutil.copy2(source_file, dest_file)
```

**Benefit**: Skip copying if files unchanged (99% of launches)

---

### 🚨 Issue #2: No Cleanup - Stale Agent Files Accumulate

**Current Code**: No cleanup of .github/agents/

**Problem**:
- If agent is removed from amplihack package, old file persists in user's .github/agents/
- If agent is renamed, both old and new files exist
- Over time, .github/agents/ could have obsolete agents

**Example Scenario**:
```bash
# amplihack v1.0: has architect.md
amplihack copilot  # Copies architect.md

# amplihack v1.1: architect.md renamed to system-architect.md
amplihack copilot  # Copies system-architect.md, but architect.md still exists!

# User now has BOTH, one is stale
```

**Impact**: Medium - Stale agents could confuse users

**Suggested Fix**:
```python
# Option A: Clean before copying
shutil.rmtree(agents_dest, ignore_errors=True)
agents_dest.mkdir(parents=True, exist_ok=True)

# Option B: Track copied files and remove extras
copied_files = set()
for source_file in source_agents.rglob("*.md"):
    # ... copy ...
    copied_files.add(dest_file.name)

# Remove files not in copied_files
for existing in agents_dest.glob("*.md"):
    if existing.name not in copied_files:
        existing.unlink()  # Remove stale agent
```

---

### 🚨 Issue #3: Name Collisions - Flattening Structure Loses Information

**Current Code** (line 87):
```python
dest_file = agents_dest / source_file.name
# Flattens: core/architect.md → architect.md
#          specialized/architect.md → architect.md (COLLISION!)
```

**Problem**:
- If two agents in different dirs have same name, last one wins
- Current agent structure:
  - `.claude/agents/amplihack/core/*.md` (6 agents)
  - `.claude/agents/amplihack/specialized/*.md` (28 agents)
- No collision NOW, but fragile

**Impact**: Low (no current collisions) but FRAGILE

**Suggested Fix**:
```python
# Preserve some structure or use unique names
relative_path = source_file.relative_to(source_agents)
if "core" in relative_path.parts:
    dest_name = f"core-{source_file.name}"
elif "specialized" in relative_path.parts:
    dest_name = f"specialized-{source_file.name}"
else:
    dest_name = source_file.name

dest_file = agents_dest / dest_name
```

OR just accept current approach but monitor for collisions.

---

### 🚨 Issue #4: Error Handling Swallows All Exceptions

**Current Code** (line 96-98):
```python
except Exception as e:
    # Fail gracefully - Copilot will work without preferences
    print(f"Warning: Could not prepare Copilot environment: {e}")
```

**Problem**:
- Catches ALL exceptions (ImportError, AttributeError, OSError, etc.)
- User only sees generic warning
- Debugging is hard - what actually failed?

**Impact**: Medium - Reduces debuggability

**Suggested Fix**:
```python
except ImportError as e:
    print(f"Warning: Adaptive hooks not available: {e}")
except OSError as e:
    print(f"Warning: File operation failed: {e}")
except Exception as e:
    # Log full traceback for debugging
    import traceback
    print(f"Warning: Could not prepare Copilot environment: {e}")
    if os.getenv("AMPLIHACK_DEBUG"):
        traceback.print_exc()
```

---

### 🚨 Issue #5: Preference File From Package, Not User's

**Current Code** (line 92-95):
```python
# Load preferences from PACKAGE and inject into user's AGENTS.md
prefs_file = package_dir / ".claude/context/USER_PREFERENCES.md"
if prefs_file.exists():
    prefs_content = prefs_file.read_text()
    strategy.inject_context(prefs_content)
```

**Problem**:
- Uses preferences from the PACKAGE (installed version)
- NOT from user's local .claude/context/USER_PREFERENCES.md
- User can't customize preferences in their project!

**Impact**: HIGH - Defeats the purpose of USER preferences!

**Expected Behavior**:
- If user has .claude/context/USER_PREFERENCES.md locally → use it
- Otherwise fallback to package version

**Suggested Fix**:
```python
# Try local first, fallback to package
prefs_file = user_dir / ".claude/context/USER_PREFERENCES.md"
if not prefs_file.exists():
    prefs_file = package_dir / ".claude/context/USER_PREFERENCES.md"

if prefs_file.exists():
    prefs_content = prefs_file.read_text()
    strategy.inject_context(prefs_content)
```

---

### 🚨 Issue #6: Hard-Coded Model Selection

**Current Code** (line 104):
```python
"--model", "claude-opus-4.5",  # Use Opus for best performance
```

**Problem**:
- Always uses Opus 4.5 (expensive!)
- User can't choose Sonnet or Haiku
- No way to override without modifying code

**Impact**: Medium - Cost and flexibility

**Suggested Fix**:
```python
# Check environment variable or config
default_model = os.getenv("COPILOT_MODEL", "claude-opus-4.5")
cmd = [
    "copilot",
    "--allow-all-tools",
    "--model", default_model,
    # ...
]
```

---

### 🚨 Issue #7: No Progress Feedback During Setup

**Current Code**: Silent file copying (line 85-89)

**Problem**:
- Copying 35 files might take 1-2 seconds
- User sees nothing, might think it's frozen
- Especially on slow filesystems

**Impact**: Low - UX issue

**Suggested Fix**:
```python
print("Preparing Copilot environment...")
copied = 0
for source_file in source_agents.rglob("*.md"):
    # ... copy ...
    copied += 1

print(f"✓ Prepared {copied} agents")
```

---

### 🚨 Issue #8: --add-dir Points to Wrong Location in UVX

**Current Code** (line 106):
```python
"--add-dir",
os.getcwd(),  # Add current directory for .github/agents/ access
```

**Analysis**:
- In UVX mode: cwd = user's directory (correct for .github/agents/)
- But .claude/ is in site-packages (NOT in cwd)
- Copilot might not see .claude/context/ files referenced by agents

**Impact**: Medium - Agents might not find @.claude/context/ references

**Suggested Fix**:
```python
# Add both user dir and package dir
"--add-dir", str(user_dir),
"--add-dir", str(package_dir),
```

---

### 🚨 Issue #9: Skills Not Copied

**Current Code**: Only copies agents from `.claude/agents/amplihack/`

**Observation**:
- 73 skills exist in `.claude/skills/`
- Skills referenced in .github/agents/skills/ (74 symlinks in repo)
- But skills NOT copied to user's directory in UVX mode

**Impact**: HIGH - Skills won't work in UVX mode!

**Current Status**: Unclear if skills need to be copied or if Copilot discovers them differently

**Need to Test**: Do skills work in UVX mode?

---

### 🚨 Issue #10: Commands Not Copied

**Similar to Issue #9**:
- 24 commands in `.github/commands/` (from repo)
- Are they in the package?
- Are they accessible in UVX mode?

**Need to Check**: build_hooks.py - does it package .github/commands/?

---

## Summary of Findings

| Issue | Severity | Impact | Fix Complexity |
|-------|----------|--------|----------------|
| #1: Copy on every launch | Medium | Startup latency | Low (add mtime check) |
| #2: No cleanup of stale files | Medium | Stale agents accumulate | Low (rmtree before copy) |
| #3: Name collision risk | Low | Fragile (no current issue) | Low (prefix with dir) |
| #4: Generic error handling | Medium | Hard to debug | Low (specific exceptions) |
| #5: **Package prefs, not user prefs** | **HIGH** | Users can't customize! | Low (check local first) |
| #6: Hard-coded Opus model | Medium | Cost, no flexibility | Low (env var) |
| #7: No progress feedback | Low | UX during setup | Low (print statement) |
| #8: --add-dir missing package | Medium | References might break | Low (add package dir) |
| #9: **Skills not copied** | **HIGH** | Skills won't work! | Medium (copy skills too) |
| #10: Commands not copied? | **HIGH** | Commands won't work! | Medium (verify/fix) |

**Priority Fixes**:
1. Issue #5 (user preferences)
2. Issue #9 (skills)
3. Issue #10 (commands)
4. Issue #1 (performance)
5. Issue #2 (cleanup)

## Recommendations

**Fix Immediately** (before merge):
- Issue #5: Check local USER_PREFERENCES.md first
- Issue #9: Copy skills if needed
- Issue #10: Verify commands are accessible

**Fix Soon** (post-merge):
- Issue #1: Add mtime check for performance
- Issue #2: Clean stale files
- Issue #6: Model selection via env var

**Monitor**:
- Issue #3: Name collisions (no current issue)
- Issue #4: Error handling (functional but could be better)
- Issue #7: UX feedback (nice-to-have)
- Issue #8: --add-dir scope (might be fine)
