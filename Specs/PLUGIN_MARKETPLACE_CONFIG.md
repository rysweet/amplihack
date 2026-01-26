# Module Specification: Plugin Marketplace Configuration

## Purpose

Configure amplihack plugin to be discoverable in Claude Code's plugin marketplace via `extraKnownMarketplaces` setting.

## Problem

Issue #1948 requirement #5 mandates marketplace source: `github.com/rysweet/amplihack`. Currently:

- No marketplace configuration exists
- Plugin won't appear in Claude Code `/plugin` command
- Users cannot discover amplihack via marketplace

## Solution Overview

Add `extraKnownMarketplaces` configuration to settings generation:

1. Add marketplace config to `.claude-plugin/plugin.json`
2. Update `SettingsGenerator` to include marketplace in generated settings
3. Ensure marketplace appears in `~/.claude/settings.json`

## Contract

### Inputs

**Plugin Manifest (`.claude-plugin/plugin.json`):**

```json
{
  "name": "amplihack",
  "marketplace": {
    "name": "amplihack",
    "url": "https://github.com/rysweet/amplihack",
    "type": "github"
  }
}
```

**Settings Generator:**

- Reads manifest marketplace config
- Merges into user settings

### Outputs

**Generated `~/.claude/settings.json`:**

```json
{
  "extraKnownMarketplaces": [
    {
      "name": "amplihack",
      "url": "https://github.com/rysweet/amplihack"
    }
  ],
  "enabledPlugins": ["amplihack"]
}
```

### Side Effects

- Updates `~/.claude/settings.json` with marketplace config
- Makes plugin discoverable via `/plugin` command in Claude Code

## Implementation Design

### File Modifications

```
.claude-plugin/
└── plugin.json               # Modified: Add marketplace section

src/amplihack/settings_generator/
└── generator.py              # Modified: Include marketplace in settings
```

### Change 1: Plugin Manifest (`plugin.json`)

**Location:** `.claude-plugin/plugin.json`

**Current State (lines 1-17):**

```json
{
  "name": "amplihack",
  "version": "0.9.0",
  "description": "AI-powered development framework...",
  "author": {...},
  "homepage": "https://github.com/rysweet/amplihack",
  "repository": "https://github.com/rysweet/amplihack",
  "license": "MIT",
  "keywords": [...],
  "commands": ["./.claude/commands/"],
  "agents": "./.claude/agents/",
  "skills": "./.claude/skills/",
  "hooks": "./.claude/tools/amplihack/hooks/hooks.json"
}
```

**New State (add marketplace section):**

```json
{
  "name": "amplihack",
  "version": "0.9.0",
  "description": "AI-powered development framework with specialized agents and automated workflows for Claude Code",
  "author": {
    "name": "Microsoft Amplihack Team",
    "url": "https://github.com/rysweet/amplihack"
  },
  "homepage": "https://github.com/rysweet/amplihack",
  "repository": "https://github.com/rysweet/amplihack",
  "license": "MIT",
  "keywords": ["claude-code", "ai", "agents", "workflows", "automation", "development"],
  "commands": ["./.claude/commands/"],
  "agents": "./.claude/agents/",
  "skills": "./.claude/skills/",
  "hooks": "./.claude/tools/amplihack/hooks/hooks.json",
  "marketplace": {
    "name": "amplihack",
    "url": "https://github.com/rysweet/amplihack",
    "type": "github",
    "description": "Official amplihack plugin marketplace"
  }
}
```

### Change 2: Settings Generator (`generator.py`)

**Location:** `src/amplihack/settings_generator/generator.py`

**Assumption:** Current `generate()` method exists and creates settings dict

**Modification:** Add marketplace config generation

```python
def generate(self, manifest: dict, user_settings: Optional[dict] = None) -> dict:
    """Generate settings.json from plugin manifest.

    Args:
        manifest: Parsed plugin.json manifest
        user_settings: Existing user settings to merge with

    Returns:
        Complete settings dictionary
    """
    settings = user_settings.copy() if user_settings else {}

    # Existing code for hooks, commands, agents, skills...
    # ...

    # NEW: Add marketplace configuration
    if "marketplace" in manifest:
        marketplace_config = manifest["marketplace"]
        if "extraKnownMarketplaces" not in settings:
            settings["extraKnownMarketplaces"] = []

        # Check if marketplace already exists (by name)
        marketplace_name = marketplace_config.get("name")
        existing_marketplaces = settings["extraKnownMarketplaces"]
        marketplace_exists = any(
            m.get("name") == marketplace_name for m in existing_marketplaces
        )

        if not marketplace_exists:
            settings["extraKnownMarketplaces"].append({
                "name": marketplace_config["name"],
                "url": marketplace_config["url"]
            })

    # Existing code for enabledPlugins...
    # ...

    return settings
```

**Implementation Notes:**

1. **Idempotency:** Check if marketplace already exists before adding
2. **Minimal Config:** Only include `name` and `url` (Claude Code requirement)
3. **Optional Field:** If `marketplace` not in manifest, skip (backward compatible)

### Change 3: CLI Integration (Optional Enhancement)

**Location:** `src/amplihack/cli.py`

**Current UVX Mode Code (lines 590-657):**

Add marketplace when generating settings in UVX mode:

```python
# After line 601 (where settings dict is created):
# Create settings.json with plugin references
settings = {
    "extraKnownMarketplaces": [
        {
            "name": "amplihack",
            "url": "https://github.com/rysweet/amplihack"
        }
    ],
    "hooks": {
        # ... existing hooks ...
    }
}
```

**Note:** This is a simple inline addition. For production, should use `SettingsGenerator` instead.

## Dependencies

- **Standard Library:** `json`
- **Internal:** `SettingsGenerator` (already exists)

## Implementation Notes

### Key Design Decisions

1. **Manifest-Driven:** Marketplace config lives in `plugin.json` (single source of truth)
2. **Generator Integration:** `SettingsGenerator` reads manifest and includes marketplace
3. **Idempotent:** Can be run multiple times without duplicating marketplace entries
4. **Minimal Config:** Only include fields Claude Code requires (`name`, `url`)

### Simplicity Optimizations

- Use existing `SettingsGenerator` infrastructure
- No new modules or classes
- 20-30 lines of code total
- Leverage existing manifest parsing

### Testing Strategy

**Unit Tests:**

- Test `SettingsGenerator.generate()` includes marketplace
- Test marketplace deduplication (don't add duplicates)
- Test backward compatibility (manifest without marketplace)

**Integration Tests:**

- Generate settings from real manifest
- Verify marketplace appears in settings.json
- Verify no duplicates on repeated generation

**E2E Tests:**

- Install plugin
- Check `~/.claude/settings.json` contains marketplace
- Verify `/plugin` command shows amplihack (manual test)

## Test Requirements

### Unit Tests (`tests/unit/test_settings_generator.py`)

```python
def test_generate_includes_marketplace():
    """Test that marketplace config is included in generated settings."""
    manifest = {
        "name": "test-plugin",
        "marketplace": {
            "name": "test-plugin",
            "url": "https://github.com/example/test-plugin"
        }
    }
    generator = SettingsGenerator()
    settings = generator.generate(manifest)

    assert "extraKnownMarketplaces" in settings
    assert len(settings["extraKnownMarketplaces"]) == 1
    assert settings["extraKnownMarketplaces"][0]["name"] == "test-plugin"
    assert settings["extraKnownMarketplaces"][0]["url"] == "https://github.com/example/test-plugin"

def test_generate_no_duplicate_marketplace():
    """Test that marketplace is not duplicated on repeated generation."""
    manifest = {"name": "test", "marketplace": {"name": "test", "url": "https://test"}}
    existing_settings = {
        "extraKnownMarketplaces": [{"name": "test", "url": "https://test"}]
    }

    generator = SettingsGenerator()
    settings = generator.generate(manifest, existing_settings)

    assert len(settings["extraKnownMarketplaces"]) == 1

def test_generate_without_marketplace():
    """Test backward compatibility when manifest has no marketplace."""
    manifest = {"name": "test"}
    generator = SettingsGenerator()
    settings = generator.generate(manifest)

    # Should not crash, marketplace field is optional
    assert isinstance(settings, dict)
```

### Integration Tests (`tests/integration/test_marketplace_config.py`)

```python
def test_marketplace_in_generated_settings(tmp_path):
    """Test marketplace appears in generated settings.json."""
    # Create manifest with marketplace
    manifest_dir = tmp_path / ".claude-plugin"
    manifest_dir.mkdir(parents=True)
    manifest_path = manifest_dir / "plugin.json"

    manifest = {
        "name": "amplihack",
        "version": "0.9.0",
        "marketplace": {
            "name": "amplihack",
            "url": "https://github.com/rysweet/amplihack"
        }
    }

    import json
    manifest_path.write_text(json.dumps(manifest, indent=2))

    # Generate settings
    from amplihack.settings_generator import SettingsGenerator
    generator = SettingsGenerator()
    settings = generator.generate(manifest)

    # Verify marketplace is present
    assert "extraKnownMarketplaces" in settings
    marketplaces = settings["extraKnownMarketplaces"]
    assert len(marketplaces) == 1
    assert marketplaces[0]["name"] == "amplihack"
    assert marketplaces[0]["url"] == "https://github.com/rysweet/amplihack"
```

## Complexity Assessment

- **Total Lines:** ~30 lines
  - `plugin.json` modification: ~8 lines (add marketplace section)
  - `generator.py` modification: ~15 lines (add marketplace generation)
  - `cli.py` modification: ~7 lines (inline marketplace for UVX mode)
- **Effort:** 1-2 hours
- **Risk:** Low (additive change, backward compatible)

## Success Metrics

- [ ] `.claude-plugin/plugin.json` contains marketplace section
- [ ] `SettingsGenerator.generate()` includes marketplace in output
- [ ] Generated `~/.claude/settings.json` contains `extraKnownMarketplaces`
- [ ] Marketplace is not duplicated on repeated generation
- [ ] Backward compatible (works without marketplace in manifest)
- [ ] `/plugin` command shows amplihack (manual verification)

## Philosophy Compliance

- ✅ **Ruthless Simplicity:** Minimal code change (~30 lines)
- ✅ **Zero-BS Implementation:** No stubs, working code only
- ✅ **Modular Design:** Changes isolated to manifest and generator
- ✅ **Regeneratable:** Can rebuild from spec
- ✅ **Single Responsibility:** Generator handles settings, manifest holds config

## Verification Steps

After implementation:

1. **Check Manifest:**

   ```bash
   cat .claude-plugin/plugin.json | jq '.marketplace'
   ```

   Should show marketplace config.

2. **Check Generated Settings:**

   ```bash
   cat ~/.claude/settings.json | jq '.extraKnownMarketplaces'
   ```

   Should show amplihack marketplace.

3. **Check Claude Code:**
   ```bash
   claude
   /plugin
   ```
   Should list amplihack plugin (manual verification).

## References

- Issue #1948, Requirement #5: "Marketplace source: github.com/rysweet/amplihack"
- Claude Code Plugin Documentation (marketplace configuration format)
- `ISSUE_1948_REQUIREMENTS.md`, Gap 2 (lines 165-183)
