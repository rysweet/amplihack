# Legacy Files Archive

This directory contains files that have been superseded by newer approaches but are preserved fer reference.

## Files in This Archive

### setup.py

**Status:** Superseded by `pyproject.toml`

**Archived:** 2026-01-12

**Reason:** Python packaging has moved to standardized pyproject.toml format. The setup.py file is no longer needed fer building or installing amplihack.

**Migration Path:**

All configuration from setup.py has been migrated to pyproject.toml:

```toml
[project]
name = "amplihack"
version = "0.9.0"
# ... all setup.py config now here
```

**If ye need setup.py:**

Some very old tools might still expect setup.py. If ye encounter such a tool:

1. Consider upgradin' the tool to support pyproject.toml
2. If not possible, setup.py can be regenerated from pyproject.toml:
   ```bash
   pip install setuptools-pyproject-migration
   setuptools-pyproject-migration pyproject.toml
   ```

## Archive Policy

Files be moved here when:

1. **Superseded:** A newer, better approach replaces them
2. **No longer used:** No active code depends on them
3. **Historical value:** They may be useful fer reference
4. **Not deprecated:** We're not rejectin' the approach, just replacin' it

## What Does NOT Go Here

This archive is NOT fer:

- Broken or buggy code → Delete it
- Experimental code → Use `~/.amplihack/.claude/ai_working/`
- Old documentation → Update or delete it
- Temporary files → Never commit them

## Maintenance

This archive should be reviewed periodically:

- **Every 6 months:** Check if files still have reference value
- **If unused:** Consider deletin' truly obsolete files
- **If needed:** Files can be "unarchived" and restored

## See Also

- [File Organization Guidelines](../../docs/contributing/file-organization.md) - Where different file types belong
- [Development Philosophy](../../.claude/context/PHILOSOPHY.md) - Trust in emergence

---

**Created:** 2026-01-12
