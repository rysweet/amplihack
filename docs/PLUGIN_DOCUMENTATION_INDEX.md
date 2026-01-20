# Plugin Documentation Index

Complete guide t' amplihack's Claude Code plugin architecture documentation.

## Overview

This index provides navigation t' all plugin-related documentation created fer Issue #1948. All documentation be written as if the feature be FULLY IMPLEMENTED and DEPLOYED.

## Documentation Files

### 1. [Plugin Architecture](./PLUGIN_ARCHITECTURE.md)

**Audience**: Developers, architects, technical users

**Contents**:

- Complete technical architecture with diagrams
- Plugin manifest structure and configuration
- Hook registration with `${CLAUDE_PLUGIN_ROOT}` variable substitution
- Installation flow diagrams
- Settings integration details
- Backward compatibility with per-project mode
- Cross-tool compatibility (Claude Code, Copilot, Codex)
- Security considerations
- Troubleshooting guide

**When to read**:

- Understanding how the plugin system works internally
- Debuggin' installation or hook loading issues
- Extendin' the plugin architecture
- Contributing t' amplihack development

**Key Sections**:

- Architecture diagram (ASCII art)
- Plugin manifest format
- Hook registration with path variables
- Mode detection precedence
- Verification checklist

---

### 2. [Migration Guide](./MIGRATION_GUIDE.md)

**Audience**: Users with existing per-project installations

**Contents**:

- Complete migration path from per-project t' plugin mode
- Benefits comparison (plugin vs per-project)
- Three migration methods (clean, gradual, hybrid)
- Custom content preservation strategies
- Reverting migration instructions
- Verification steps
- Troubleshootin' common issues
- Migration checklist

**When to read**:

- Ye have existing projects with `.claude/` directories
- Decidin' between plugin and per-project modes
- Need step-by-step migration instructions
- Want t' preserve custom agents/commands/skills

**Key Sections**:

- When to migrate vs stay per-project
- Method 1: Clean migration (recommended)
- Method 2: Gradual migration (test first)
- Method 3: Hybrid mode (mixed approach)
- Preservin' customizations
- Troubleshootin' failed migrations

---

### 3. [CLI Commands Reference](./PLUGIN_CLI_HELP.md)

**Audience**: All users

**Contents**:

- Complete reference fer `amplihack plugin` commands
- Complete reference fer `amplihack mode` commands
- Detailed examples fer each command
- Output samples (success and failure cases)
- Environment variables
- Common workflows
- Exit codes
- Help text examples

**When to read**:

- Need syntax reference fer plugin commands
- Want t' understand command output
- Writin' scripts that use plugin commands
- Troubleshootin' command failures

**Key Sections**:

- `amplihack plugin install` - Full documentation
- `amplihack plugin uninstall` - Full documentation
- `amplihack plugin verify` - Full documentation
- `amplihack mode status` - Full documentation
- `amplihack mode migrate-to-plugin` - Full documentation
- `amplihack mode migrate-to-local` - Full documentation
- Common workflows section

---

### 4. [README Plugin Section](./README_PLUGIN_SECTION.md)

**Audience**: New users, quick start

**Contents**:

- Quick overview o' plugin installation
- Installation methods (plugin vs per-project)
- Plugin location and structure
- Mode detection explanation
- Quick command reference
- Migration quickstart
- Verification steps
- Troubleshootin' quick fixes
- Cross-tool compatibility table

**When to read**:

- First time installin' amplihack as plugin
- Need quick reference fer plugin commands
- Decidin' between installation methods
- Quick troubleshootin' reference

**Where to use**:
This content should be inserted into main `README.md` after the "Create Alias for Easy Access" section (after line 101).

**Key Sections**:

- Installation methods comparison
- Plugin location structure
- Mode detection precedence
- Quick command reference
- Cross-tool support table

---

## Quick Start Guide

### For New Users

1. **Start here**: [README Plugin Section](./README_PLUGIN_SECTION.md)
   - Understand installation options
   - Choose plugin vs per-project mode
   - Install and verify

2. **Then read**: [CLI Commands Reference](./PLUGIN_CLI_HELP.md)
   - Learn `amplihack plugin` commands
   - Understand verification process

3. **Deep dive** (optional): [Plugin Architecture](./PLUGIN_ARCHITECTURE.md)
   - Technical details
   - How hooks work
   - Troubleshootin' advanced issues

### For Existing Users (Migration)

1. **Start here**: [Migration Guide](./MIGRATION_GUIDE.md)
   - Decide if migration be right fer ye
   - Choose migration method
   - Follow step-by-step instructions

2. **Reference**: [CLI Commands Reference](./PLUGIN_CLI_HELP.md)
   - Command syntax fer migration
   - Verification commands

3. **Troubleshoot**: [Plugin Architecture](./PLUGIN_ARCHITECTURE.md)
   - Mode detection details
   - Hook loading issues
   - Settings integration problems

### For Developers/Contributors

1. **Start here**: [Plugin Architecture](./PLUGIN_ARCHITECTURE.md)
   - Complete technical architecture
   - Implementation details
   - Extension points

2. **Implementation reference**: Specification files in `Specs/`
   - `PLUGIN_CLI_COMMANDS.md` - CLI implementation spec
   - `PLUGIN_MARKETPLACE_CONFIG.md` - Marketplace integration spec
   - `CROSS_TOOL_COMPATIBILITY.md` - Compatibility research
   - `BACKWARD_COMPATIBILITY.md` - Mode detection spec

---

## Documentation Structure

```
docs/
├── PLUGIN_DOCUMENTATION_INDEX.md      # This file (navigation)
├── PLUGIN_ARCHITECTURE.md             # Technical architecture
├── MIGRATION_GUIDE.md                 # Per-project → plugin migration
├── PLUGIN_CLI_HELP.md                 # CLI command reference
└── README_PLUGIN_SECTION.md           # README.md insert (quick start)
```

## Related Specifications

Implementation specifications (developer reference):

```
Specs/
├── PLUGIN_CLI_COMMANDS.md             # CLI implementation spec
├── PLUGIN_MARKETPLACE_CONFIG.md       # Marketplace integration
├── CROSS_TOOL_COMPATIBILITY.md        # Copilot/Codex compatibility
├── BACKWARD_COMPATIBILITY.md          # Mode detection logic
└── HOOK_REGISTRATION_AUDIT.md         # Hook path variable usage
```

---

## Common Use Cases

### Use Case 1: Fresh Plugin Installation

**Goal**: Install amplihack as plugin fer first time

**Path**:

1. Read: [README Plugin Section](./README_PLUGIN_SECTION.md) - Installation methods
2. Execute: `amplihack plugin install https://github.com/rysweet/amplihack`
3. Verify: `amplihack plugin verify amplihack`
4. Reference: [CLI Commands Reference](./PLUGIN_CLI_HELP.md) - If issues

---

### Use Case 2: Migrate Existing Project

**Goal**: Convert per-project `.claude/` t' plugin

**Path**:

1. Read: [Migration Guide](./MIGRATION_GUIDE.md) - Choose migration method
2. Backup custom content (if any)
3. Execute: `amplihack plugin install` (if not installed)
4. Execute: `amplihack mode migrate-to-plugin`
5. Verify: `amplihack mode status`
6. Troubleshoot: [Plugin Architecture](./PLUGIN_ARCHITECTURE.md) - If issues

---

### Use Case 3: Update Plugin

**Goal**: Get latest amplihack changes

**Path**:

1. Execute: `amplihack plugin install --force https://github.com/rysweet/amplihack`
2. Verify: `amplihack plugin verify amplihack`
3. Reference: [CLI Commands Reference](./PLUGIN_CLI_HELP.md) - Command details

---

### Use Case 4: Revert t' Per-Project

**Goal**: Create local `.claude/` fer project-specific customizations

**Path**:

1. Execute: `amplihack mode migrate-to-local`
2. Customize: Edit `.claude/agents/`, `.claude/commands/`, etc.
3. Verify: `amplihack mode status` (should show "local")
4. Reference: [Migration Guide](./MIGRATION_GUIDE.md) - Customization guidance

---

### Use Case 5: Troubleshoot Installation

**Goal**: Fix plugin installation or discovery issues

**Path**:

1. Diagnose: `amplihack plugin verify amplihack`
2. Check mode: `amplihack mode status`
3. Reference: [Plugin Architecture](./PLUGIN_ARCHITECTURE.md#troubleshooting)
4. Reinstall: `amplihack plugin install --force`
5. Reference: [CLI Commands Reference](./PLUGIN_CLI_HELP.md) - Command details

---

## FAQ Quick Reference

**Q: Which installation method should I use?**

- Read: [README Plugin Section](./README_PLUGIN_SECTION.md#installation-methods)

**Q: How do I migrate from per-project to plugin?**

- Read: [Migration Guide](./MIGRATION_GUIDE.md#migration-methods)

**Q: What's the command syntax fer plugin operations?**

- Read: [CLI Commands Reference](./PLUGIN_CLI_HELP.md)

**Q: How does mode detection work?**

- Read: [Plugin Architecture](./PLUGIN_ARCHITECTURE.md#backward-compatibility)

**Q: How do I preserve custom agents when migratin'?**

- Read: [Migration Guide](./MIGRATION_GUIDE.md#preservin-customizations)

**Q: Can I use both plugin and local .claude/?**

- Yes! Read: [Plugin Architecture](./PLUGIN_ARCHITECTURE.md#backward-compatibility)
- Local takes precedence (intentional design)

**Q: How do I troubleshoot installation issues?**

- Read: [Plugin Architecture](./PLUGIN_ARCHITECTURE.md#troubleshooting)
- Run: `amplihack plugin verify amplihack`

**Q: What's the difference between plugin and per-project modes?**

- Read: [Migration Guide](./MIGRATION_GUIDE.md#benefits-o-plugin-mode)

---

## Documentation Maintenance

### Updating Documentation

When plugin implementation changes:

1. **Update technical details**: [Plugin Architecture](./PLUGIN_ARCHITECTURE.md)
2. **Update commands**: [CLI Commands Reference](./PLUGIN_CLI_HELP.md)
3. **Update migration steps**: [Migration Guide](./MIGRATION_GUIDE.md)
4. **Update quick start**: [README Plugin Section](./README_PLUGIN_SECTION.md)
5. **Update this index**: Add new sections or use cases

### Documentation Testing

Before releasin' documentation:

- [ ] Verify all commands in examples work
- [ ] Test migration steps on real project
- [ ] Confirm troubleshootin' steps resolve issues
- [ ] Check all internal links work
- [ ] Validate code examples run without errors

---

## Additional Resources

### Implementation Specifications

- `Specs/PLUGIN_CLI_COMMANDS.md` - CLI handler implementation
- `Specs/PLUGIN_MARKETPLACE_CONFIG.md` - Marketplace integration
- `Specs/CROSS_TOOL_COMPATIBILITY.md` - Compatibility matrix
- `Specs/BACKWARD_COMPATIBILITY.md` - Mode detection logic

### Related Documentation

- `README.md` - Main project documentation
- `CLAUDE.md` - Framework usage guide
- `.claude/context/PHILOSOPHY.md` - Development philosophy

### Issue Tracking

- **Issue #1948**: Plugin architecture implementation ([view on GitHub](https://github.com/rysweet/amplihack/issues/1948))

---

## Next Steps

After readin' documentation:

1. **Install Plugin**: Follow [README Plugin Section](./README_PLUGIN_SECTION.md)
2. **Migrate Projects**: Use [Migration Guide](./MIGRATION_GUIDE.md)
3. **Learn Commands**: Reference [CLI Commands Reference](./PLUGIN_CLI_HELP.md)
4. **Understand Architecture**: Deep dive into [Plugin Architecture](./PLUGIN_ARCHITECTURE.md)

Happy sailin'! 🏴‍☠️
