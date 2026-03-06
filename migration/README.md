# Migration Guides

Step-by-step guides for upgrading amplihack features and dependencies.

## Available Migration Guides

### [claude-trace to Native Binary](./claude-trace-to-native.md)

**Migration from the deprecated claude-trace NPM package to native binary trace logging.**

- **Why migrate**: Better performance, zero dependencies, automatic security
- **Effort**: 30-60 minutes
- **Breaking changes**: File format (JSON → JSONL), directory structure, API
- **When to migrate**: Before upgrading to amplihack v1.0+

**Quick start**:

```bash
# 1. Remove old dependency
npm uninstall claude-trace

# 2. Enable native trace logging
export AMPLIHACK_TRACE_LOGGING=true

# 3. Update scripts for JSONL format
cat .claude/runtime/amplihack-traces/*.jsonl | jq .
```

See [complete guide](./claude-trace-to-native.md) for detailed steps.

---

## Future Migration Guides

As amplihack evolves, migration guides will be added here for:

- Memory system upgrades (Neo4j → Kùzu)
- Plugin architecture migrations
- Workflow format changes
- API breaking changes

---

## General Migration Best Practices

### Before You Start

1. **Backup your data**: Archive current state before migrating
2. **Read the full guide**: Understand breaking changes and impacts
3. **Test in development**: Never migrate production directly
4. **Plan rollback**: Know how to revert if issues arise

### During Migration

1. **Follow the checklist**: Use provided migration checklists
2. **Verify each step**: Test after each major change
3. **Document issues**: Note any problems for future reference
4. **Keep notes**: Track what worked and what didn't

### After Migration

1. **Test thoroughly**: Verify all functionality works
2. **Monitor performance**: Check for regressions
3. **Update documentation**: Reflect changes in your docs
4. **Share feedback**: Report issues or improvements

---

## Migration Support

If you encounter issues during migration:

1. Check the specific guide's troubleshooting section
2. Search [GitHub Issues](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues)
3. File a new issue with migration context

---

## Related Documentation

- [Features & Integrations](../index.md#-features--integrations) - All features
- [Troubleshooting](../troubleshooting/README.md) - Common issues
- [Configuration](../index.md#%EF%B8%8F-configuration--deployment) - Configuration guides
