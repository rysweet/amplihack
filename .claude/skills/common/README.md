# Common Office Skills Infrastructure

This directory contains shared components used across multiple Office skills.

## Contents

### verification/
Dependency verification utilities for checking if skills are ready to use.

**Key file**: `verify_skill.py`

```bash
# Verify specific skill
python verification/verify_skill.py pdf

# Verify all skills
python verification/verify_skill.py all
```

### dependencies.txt
Documentation of dependencies shared across multiple skills:
- Python packages (defusedxml, pandas)
- System packages (LibreOffice, poppler-utils, Node.js)
- Node packages (docx, pptxgenjs)

### ooxml/ (Planned for PR #3)
Shared OOXML (Office Open XML) manipulation scripts used by docx and pptx skills.

**Will include**:
- `unpack.py` - Extract OOXML ZIP archives
- `pack.py` - Repackage OOXML ZIP archives
- `rearrange.py` - Reorder slides (pptx)
- `inventory.py` - List presentation content (pptx)
- `replace.py` - Content replacement (pptx)

## Purpose

The common directory serves three main purposes:

1. **DRY Principle**: Avoid duplicating code and documentation across skills
2. **Consistency**: Provide uniform utilities for all skills
3. **Maintainability**: Update shared components in one place

## Design Philosophy

Following amplihack's principles:

- **Ruthless simplicity**: Minimal abstractions, direct implementations
- **Clear boundaries**: Shared code only when truly reusable
- **No premature abstraction**: Add to common/ only after 2+ skills need it
- **Explicit over implicit**: Clear documentation of what's shared

## Current Shared Components

### Verification Utilities (PR #1)

**Problem**: Each skill needs to verify its dependencies are installed.

**Solution**: Single verification script that checks Python packages and system commands.

**Usage**: All skills can use `verify_skill.py` for dependency checks.

**Pattern**:
```python
# In skill tests
from verify_skill import check_python_package, check_system_command

if not check_python_package("pypdf"):
    pytest.skip("pypdf not installed")
```

### Dependency Documentation (PR #1)

**Problem**: Some dependencies are shared across multiple skills.

**Solution**: `dependencies.txt` documents shared dependencies with install instructions.

**Usage**: Skills reference this file in their DEPENDENCIES.md.

**Pattern**:
```markdown
# In skill DEPENDENCIES.md
Some dependencies are shared across skills.
See [common/dependencies.txt](../common/dependencies.txt) for:
- LibreOffice (used by xlsx, docx, pptx)
- poppler-utils (used by pdf, docx)
```

## Future Shared Components

### OOXML Scripts (Planned PR #3)

**Problem**: docx and pptx both need OOXML manipulation.

**Solution**: Extract scripts to `common/ooxml/`, symlink from skill directories.

**Rationale**: OOXML scripts are identical across skills, maintain single source of truth.

**Pattern**:
```bash
# Symlink setup
cd .claude/skills/docx
ln -s ../common/ooxml scripts

cd .claude/skills/pptx
ln -s ../common/ooxml scripts
```

## Adding New Shared Components

When to add to common/:

1. **Used by 2+ skills**: Don't abstract prematurely
2. **Truly identical**: Not just similar, but identical code
3. **Stable interface**: Won't change frequently
4. **Clear benefit**: DRY principle provides real value

Process:

1. Implement in first skill
2. Identify duplication in second skill
3. Extract to common/ with clear documentation
4. Update both skills to use shared component
5. Add tests for shared component

## Testing

Shared components should have tests:

```bash
# Test verification utilities
python verification/verify_skill.py all

# Test OOXML scripts (when added)
cd ooxml
pytest tests/
```

## Documentation

Each shared component needs:

- **README section**: Describe component and usage
- **Inline comments**: Explain non-obvious code
- **Examples**: Show how skills use the component
- **Tests**: Verify component works independently

## Version Management

Shared components follow semantic versioning:

- **Major**: Breaking changes to interface
- **Minor**: New functionality, backwards compatible
- **Patch**: Bug fixes

Document changes in this README.

## Maintenance

Shared components require extra care:

- Changes affect multiple skills
- Test all dependent skills after changes
- Update documentation when interface changes
- Consider backwards compatibility

## References

- [Root Skills README](../README.md)
- [Integration Status](../INTEGRATION_STATUS.md)
- [Architecture Specification](../../../Specs/OFFICE_SKILLS_INTEGRATION_ARCHITECTURE.md)

---

**Last Updated**: 2025-11-08
**Current Components**: verification, dependencies documentation
**Planned Components**: OOXML scripts (PR #3)
**Maintained By**: amplihack project
