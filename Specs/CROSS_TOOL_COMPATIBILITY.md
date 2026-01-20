# Module Specification: Cross-Tool Compatibility Strategy

## Purpose

Ensure amplihack plugin works with Claude Code, GitHub Copilot, AND Codex by verifying compatibility and documenting differences.

## Problem

Issue #1948 requirement #6: "Compatibility: Claude Code, GitHub Copilot, AND Codex". Currently:
- Plugin designed for Claude Code
- Unknown compatibility with GitHub Copilot plugin format
- Unknown compatibility with Codex plugin format
- No compatibility testing or documentation

## Solution Overview

Three-phase approach:
1. **Research Phase:** Document plugin formats for each tool
2. **Compatibility Matrix:** Identify differences and required adaptations
3. **Testing Phase:** Verify plugin works or document limitations

## Contract

### Inputs

**Plugin Manifest (`.claude-plugin/plugin.json`):**
- Current format (Claude Code)
- May need variants for other tools

**Hook Configuration (`hooks.json`):**
- Current format uses Claude Code lifecycle hooks
- May need adaptation for other tools

### Outputs

**Compatibility Report:**
- Document what works out-of-box
- Document required adaptations
- Document known limitations
- Provide migration guidance

**Adapted Configurations (if needed):**
- `.copilot-plugin/plugin.json` (if format differs)
- `.codex-plugin/plugin.json` (if format differs)
- Tool-specific hook configurations

### Side Effects

- May create tool-specific plugin configurations
- Documents compatibility matrix in README

## Implementation Design

### Phase 1: Research (No Code)

**Research Questions:**

1. **GitHub Copilot:**
   - Does Copilot support plugin architecture?
   - What is the plugin manifest format?
   - Does it support hooks? What lifecycle events?
   - Does it support `${PLUGIN_ROOT}` variable substitution?

2. **Codex:**
   - Does Codex support plugin architecture?
   - What is the plugin manifest format?
   - Does it support hooks? What lifecycle events?
   - Does it support path variable substitution?

**Research Sources:**
- Official documentation for each tool
- GitHub repositories (search for "copilot plugin", "codex plugin")
- Community forums and discussions
- Experimental testing if documentation is lacking

### Phase 2: Compatibility Matrix

**Plugin Manifest Compatibility:**

| Feature | Claude Code | GitHub Copilot | Codex |
|---------|-------------|----------------|-------|
| Plugin support | ✅ Yes | ❓ Research | ❓ Research |
| Manifest format | `plugin.json` | ❓ Research | ❓ Research |
| Required fields | `name`, `version`, `entry_point` | ❓ | ❓ |
| Hook support | ✅ Yes | ❓ | ❓ |
| Path variables | ✅ `${CLAUDE_PLUGIN_ROOT}` | ❓ | ❓ |
| Marketplace | ✅ `extraKnownMarketplaces` | ❓ | ❓ |

**Hook Lifecycle Compatibility:**

| Hook Type | Claude Code | GitHub Copilot | Codex |
|-----------|-------------|----------------|-------|
| SessionStart | ✅ Supported | ❓ | ❓ |
| Stop | ✅ Supported | ❓ | ❓ |
| PreToolUse | ✅ Supported | ❓ | ❓ |
| PostToolUse | ✅ Supported | ❓ | ❓ |
| UserPromptSubmit | ✅ Supported | ❓ | ❓ |
| PreCompact | ✅ Supported | ❓ | ❓ |

### Phase 3: Compatibility Strategy

**Strategy 1: Universal Plugin (Ideal)**

If all tools support similar plugin formats:
- Single `plugin.json` works for all tools
- Hooks use common lifecycle events
- Path variables work across tools

**Implementation:**
- Keep current plugin structure
- Document tested compatibility
- Provide tool-specific installation instructions

**Strategy 2: Tool-Specific Variants (If Needed)**

If tools have incompatible formats:
- Create tool-specific plugin directories:
  ```
  .claude-plugin/     # Claude Code plugin
  .copilot-plugin/    # GitHub Copilot plugin (if format differs)
  .codex-plugin/      # Codex plugin (if format differs)
  ```
- Share common `.claude/` content (agents, commands, skills)
- Adapt manifest and hooks per tool

**Implementation:**
```
amplihack/
├── .claude-plugin/           # Claude Code manifest
│   └── plugin.json
├── .copilot-plugin/          # Copilot manifest (if needed)
│   └── plugin.json
├── .codex-plugin/            # Codex manifest (if needed)
│   └── plugin.json
└── .claude/                  # Shared content
    ├── agents/               # Works for all tools
    ├── commands/             # Works for all tools
    ├── skills/               # Works for all tools
    └── tools/
        └── amplihack/
            └── hooks/
                ├── hooks.claude.json      # Claude Code hooks
                ├── hooks.copilot.json     # Copilot hooks (if needed)
                └── hooks.codex.json       # Codex hooks (if needed)
```

**Strategy 3: Graceful Degradation (Fallback)**

If some tools don't support plugins:
- Document that plugin mode only works in Claude Code
- Provide fallback installation (per-project `.claude/` copy)
- Maintain backward compatibility

**Implementation:**
- Keep existing per-project copy mode as fallback
- Document tool compatibility in README
- Provide migration guide for each tool

## Testing Strategy

### Test Plan

**Claude Code (Primary Target):**
1. Install plugin via `amplihack plugin install`
2. Verify hooks load in new Claude Code session
3. Verify commands, agents, skills discoverable
4. Test in real project workflow

**GitHub Copilot (Secondary):**
1. Research Copilot plugin architecture
2. If supported: Adapt manifest and test installation
3. If not supported: Document limitation, provide workaround
4. Test agent/command functionality if available

**Codex (Tertiary):**
1. Research Codex plugin architecture
2. If supported: Adapt manifest and test installation
3. If not supported: Document limitation, provide workaround
4. Test agent/command functionality if available

### Success Criteria

**Minimum Viable Compatibility:**
- ✅ Plugin works in Claude Code (primary requirement)
- ⚠️  Copilot/Codex compatibility documented (even if "not supported")
- ✅ Fallback mode available for unsupported tools

**Ideal Compatibility:**
- ✅ Plugin works in all three tools
- ✅ Single manifest supports all tools
- ✅ Hooks work across tools (or gracefully degrade)

## Implementation Steps

### Step 1: Research Phase (4-8 hours)

```markdown
## Research Checklist

### GitHub Copilot
- [ ] Check official Copilot documentation for plugin support
- [ ] Search GitHub for "copilot plugin" examples
- [ ] Test if Copilot supports `.copilot-plugin/` directory
- [ ] Document findings in COPILOT_COMPATIBILITY.md

### Codex
- [ ] Check official Codex documentation for plugin support
- [ ] Search GitHub for "codex plugin" examples
- [ ] Test if Codex supports plugin architecture
- [ ] Document findings in CODEX_COMPATIBILITY.md
```

### Step 2: Adaptation Phase (2-4 hours, if needed)

```bash
# If Copilot format differs:
mkdir .copilot-plugin
cp .claude-plugin/plugin.json .copilot-plugin/plugin.json
# Edit to match Copilot format

# If Codex format differs:
mkdir .codex-plugin
cp .claude-plugin/plugin.json .codex-plugin/plugin.json
# Edit to match Codex format
```

### Step 3: Documentation Phase (1-2 hours)

Create compatibility guide in README:

```markdown
## Cross-Tool Compatibility

### Claude Code ✅
- **Status:** Fully supported
- **Installation:** `amplihack plugin install`
- **Features:** Hooks, agents, commands, skills, marketplace

### GitHub Copilot ⚠️
- **Status:** [Research result]
- **Installation:** [Tool-specific instructions or "Not supported"]
- **Limitations:** [List any limitations]

### Codex ⚠️
- **Status:** [Research result]
- **Installation:** [Tool-specific instructions or "Not supported"]
- **Limitations:** [List any limitations]
```

## Dependencies

- **None** (research and documentation)
- **Tools:** Claude Code, GitHub Copilot, Codex (for testing)

## Testing Requirements

### Research Verification Tests

```python
def test_claude_code_compatibility():
    """Verify plugin works in Claude Code."""
    # This is the primary test - already covered by plugin installation tests
    pass

def test_copilot_compatibility():
    """Document Copilot compatibility status."""
    # Research-based documentation test
    # Verify COPILOT_COMPATIBILITY.md exists and has findings
    compatibility_doc = Path("docs/COPILOT_COMPATIBILITY.md")
    assert compatibility_doc.exists(), "Copilot compatibility not documented"

    content = compatibility_doc.read_text()
    assert "Plugin Support:" in content
    assert "Manifest Format:" in content

def test_codex_compatibility():
    """Document Codex compatibility status."""
    # Research-based documentation test
    compatibility_doc = Path("docs/CODEX_COMPATIBILITY.md")
    assert compatibility_doc.exists(), "Codex compatibility not documented"

    content = compatibility_doc.read_text()
    assert "Plugin Support:" in content
    assert "Manifest Format:" in content
```

### Integration Tests (If Compatible)

```python
def test_copilot_plugin_installation():
    """Test plugin installation in Copilot (if supported)."""
    # Only runs if Copilot supports plugins
    if not copilot_supports_plugins():
        pytest.skip("Copilot does not support plugins")

    # Test installation
    # ...

def test_codex_plugin_installation():
    """Test plugin installation in Codex (if supported)."""
    # Only runs if Codex supports plugins
    if not codex_supports_plugins():
        pytest.skip("Codex does not support plugins")

    # Test installation
    # ...
```

## Complexity Assessment

- **Research:** 4-8 hours
- **Adaptation:** 0-4 hours (depends on compatibility)
- **Documentation:** 1-2 hours
- **Testing:** 2-4 hours
- **Total:** 7-18 hours (depends on research findings)
- **Risk:** Medium (external tool dependencies, unknowns)

## Success Metrics

**Research Phase:**
- [ ] Copilot plugin support status documented
- [ ] Codex plugin support status documented
- [ ] Compatibility matrix complete

**Adaptation Phase (if needed):**
- [ ] Tool-specific manifests created
- [ ] Tool-specific hooks configured
- [ ] Installation instructions provided

**Documentation Phase:**
- [ ] README updated with compatibility info
- [ ] Tool-specific guides created
- [ ] Migration instructions provided

**Testing Phase:**
- [ ] Claude Code plugin tested (primary)
- [ ] Copilot compatibility verified or limitation documented
- [ ] Codex compatibility verified or limitation documented

## Deliverables

1. **Research Documents:**
   - `docs/COPILOT_COMPATIBILITY.md`
   - `docs/CODEX_COMPATIBILITY.md`
   - Compatibility matrix in README

2. **Tool-Specific Configs (if needed):**
   - `.copilot-plugin/plugin.json`
   - `.codex-plugin/plugin.json`
   - Tool-specific hook configurations

3. **Installation Guides:**
   - Claude Code: Already have
   - Copilot: Tool-specific or "not supported"
   - Codex: Tool-specific or "not supported"

## Philosophy Compliance

- ✅ **Ruthless Simplicity:** Research first, adapt only if needed
- ✅ **Zero-BS Implementation:** Document actual findings, not assumptions
- ✅ **Modular Design:** Tool-specific configs isolated
- ✅ **Regeneratable:** Configs can be regenerated from research
- ✅ **Single Responsibility:** Each config targets one tool

## Realistic Expectations

**Most Likely Outcome:**
- Claude Code: ✅ Full support (this is the primary target)
- GitHub Copilot: ⚠️  Limited or no plugin support (focus on Copilot Chat)
- Codex: ⚠️  Unknown (less public documentation)

**Fallback Plan:**
If Copilot/Codex don't support plugins:
- Document compatibility clearly
- Provide per-project `.claude/` copy instructions
- Maintain backward compatibility

**This is acceptable** - Issue #1948 requires compatibility *verification*, not necessarily full support.

## References

- Issue #1948, Requirement #6: "Compatibility: Claude Code, GitHub Copilot, AND Codex"
- `ISSUE_1948_REQUIREMENTS.md`, Gap 4 (lines 349-374)
- Claude Code Plugin Documentation
- GitHub Copilot Documentation
- Codex Documentation
