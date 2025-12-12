# Common Skills Infrastructure

## Overview

This directory contains shared infrastructure used by multiple Office skills. The goal is to follow the DRY (Don't Repeat Yourself) principle while maintaining the brick philosophy - each component is independently functional and clearly bounded.

## Components

### 1. OOXML Scripts (`ooxml/`)

**Purpose**: Shared scripts for Office Open XML manipulation

**Used by**: DOCX skill, PPTX skill (future)

**Description**: Office documents (.docx, .pptx, .xlsx) are ZIP archives containing XML files. These scripts provide core operations for unpacking, modifying, and repacking Office documents.

**Key Scripts**:

- `unpack.py`: Extract Office file to directory with formatted XML
- `pack.py`: Repackage directory into Office file with validation

**Documentation**: [ooxml/README.md](ooxml/README.md)

**Access Pattern**: Skills reference via symlink

```bash
docx/ooxml -> ../common/ooxml
pptx/ooxml -> ../common/ooxml  # Future
```

### 2. Verification Utilities (`verification/`)

**Purpose**: Dependency verification scripts

**Used by**: All skills

**Description**: Scripts to check if required Python packages and system commands are installed. Provides consistent dependency checking across all skills.

**Key Script**:

- `verify_skill.py`: Check dependencies for a specific skill

**Usage**:

```bash
python common/verification/verify_skill.py pdf
python common/verification/verify_skill.py docx
```

**Output**: Reports installed/missing dependencies with clear status

### 3. Shared Dependencies (`dependencies.txt`)

**Purpose**: Track dependencies shared across multiple skills

**Format**: Plain text listing of shared dependencies with usage notes

**Contents**:

- Python packages (e.g., defusedxml)
- System packages (e.g., LibreOffice, poppler-utils)
- Notes on which skills use each dependency

## Architecture Principles

### Single Source of Truth

Shared code lives in one place:

- OOXML scripts: `common/ooxml/`
- Verification utilities: `common/verification/`

Skills reference via symlinks, not copies.

### Explicit Dependencies

Each skill declares its dependencies explicitly:

- Skill-specific: In skill's DEPENDENCIES.md
- Shared: Noted in common/dependencies.txt

No implicit assumptions about what's installed.

### Graceful Degradation

Common utilities handle missing dependencies gracefully:

- Verification script reports status without failing
- Tests skip appropriately if dependencies unavailable
- Clear error messages with installation instructions

### Minimal Coupling

Common components have minimal interdependencies:

- OOXML scripts standalone (only need defusedxml)
- Verification utilities standalone (only need Python stdlib)
- No circular dependencies between components

## Directory Structure

```
.claude/skills/common/
├── README.md                # This file
├── dependencies.txt         # Shared dependencies tracker
├── ooxml/                   # OOXML manipulation scripts
│   ├── README.md            # OOXML documentation
│   └── scripts/
│       ├── unpack.py
│       └── pack.py
└── verification/            # Dependency verification
    ├── README.md            # Verification documentation
    └── verify_skill.py      # Main verification script
```

## Usage Examples

### Verifying Dependencies

```bash
# Check if DOCX skill dependencies are installed
cd .claude/skills
python common/verification/verify_skill.py docx

# Check all skills
python common/verification/verify_skill.py all
```

### Using OOXML Scripts

```bash
# From DOCX skill directory
python ooxml/scripts/unpack.py document.docx unpacked/
# ... modify XML files ...
python ooxml/scripts/pack.py unpacked/ modified.docx
```

### Checking Shared Dependencies

```bash
# View shared dependencies
cat common/dependencies.txt

# See which skills share a dependency
grep "LibreOffice" common/dependencies.txt
```

## Shared Dependencies Reference

### Python Packages

**defusedxml** (Used by: DOCX, PPTX)

- Purpose: Secure XML parsing for OOXML operations
- Why shared: Both DOCX and PPTX manipulate Office XML
- Installation: `pip install defusedxml`

### System Packages

**LibreOffice (soffice)** (Used by: XLSX, DOCX, PPTX)

- Purpose: Document validation and conversion
- Why shared: All Office formats need validation
- Installation:
  - macOS: `brew install libreoffice`
  - Ubuntu: `sudo apt-get install libreoffice`

**poppler-utils** (Used by: DOCX, PDF)

- Purpose: PDF processing (pdftoppm, pdftotext)
- Why shared: Both skills work with PDF conversion
- Installation:
  - macOS: `brew install poppler`
  - Ubuntu: `sudo apt-get install poppler-utils`

## Design Decisions

### Why Symlinks?

**Decision**: Use symlinks for OOXML scripts rather than copies or imports

**Rationale**:

- Single source of truth (update in one place)
- Clear dependency (visible in directory structure)
- Simple (no complex import paths or packaging)
- Git-friendly (symlinks tracked in repository)

**Trade-off**: Symlinks may not work on Windows without Developer Mode

**Mitigation**: Document Windows setup, provide fallback instructions

### Why Common Directory?

**Decision**: Create common/ directory rather than top-level shared modules

**Rationale**:

- Keeps all skills infrastructure in .claude/skills/
- Clear namespace (common/ signals shared code)
- Easy to find and maintain
- Follows brick philosophy (clear boundaries)

### Why Not Packaging?

**Decision**: Don't create Python packages for shared code

**Rationale**:

- Overkill for small utilities
- Would complicate installation
- Skills should be independently usable
- Symlinks and direct script execution simpler

## Maintenance Guidelines

### Adding Shared Code

When considering adding code to common/:

1. **Is it used by 2+ skills?** If no, keep in skill directory
2. **Is it independently functional?** If no, refactor first
3. **Does it have clear boundaries?** If no, simplify interface
4. **Will it evolve independently?** If yes, keep separate

### Updating Shared Code

When modifying common/ components:

1. **Check all users**: Which skills reference this code?
2. **Test all skills**: Run tests for all dependent skills
3. **Update documentation**: Reflect changes in READMEs
4. **Consider versioning**: For breaking changes, consider skill migration

### Deprecating Shared Code

When removing common/ components:

1. **Identify dependents**: List all skills using the component
2. **Migrate or inline**: Move to skill-specific if still needed
3. **Update symlinks**: Remove broken links
4. **Document removal**: Note in INTEGRATION_STATUS.md

## Testing

### Verify Common Infrastructure

```bash
# Check OOXML scripts exist and are executable
test -x common/ooxml/scripts/unpack.py && echo "unpack.py OK"
test -x common/ooxml/scripts/pack.py && echo "pack.py OK"

# Check verification script works
python common/verification/verify_skill.py --help

# Verify symlinks are correct
ls -la docx/ooxml  # Should show -> ../common/ooxml
```

### Test OOXML Scripts

```bash
# Create test document
echo '<?xml version="1.0"?><root><test>data</test></root>' > test.xml
zip test.docx test.xml

# Test unpack
python common/ooxml/scripts/unpack.py test.docx unpacked/
test -f unpacked/test.xml && echo "Unpack OK"

# Test pack
python common/ooxml/scripts/pack.py unpacked/ repacked.docx --force
test -f repacked.docx && echo "Pack OK"
```

## Troubleshooting

### Symlink Not Found

**Problem**: `ls: docx/ooxml: No such file or directory`

**Solution**:

```bash
cd .claude/skills/docx
ln -s ../common/ooxml ooxml
ls -la ooxml  # Verify
```

### Script Not Executable

**Problem**: `Permission denied` when running scripts

**Solution**:

```bash
chmod +x common/ooxml/scripts/*.py
chmod +x common/verification/*.py
```

### Import Errors in Scripts

**Problem**: `ModuleNotFoundError: No module named 'defusedxml'`

**Solution**:

```bash
pip install defusedxml
python -c "import defusedxml; print('OK')"
```

### Verification Script Fails

**Problem**: Verification script itself fails to run

**Solution**:

```bash
# Check Python version (needs 3.x)
python --version

# Run directly
python3 common/verification/verify_skill.py docx
```

## Future Enhancements

### Planned Additions

1. **PPTX OOXML Scripts** (PR #4)
   - rearrange.py (slide reordering)
   - inventory.py (content listing)
   - replace.py (content replacement)

2. **Verification Enhancements**
   - Auto-suggest installation commands
   - Check version compatibility
   - Dependency conflict detection

3. **Common Test Utilities**
   - Shared pytest fixtures
   - Mock document generators
   - Test data helpers

### Not Planned

1. **Package Management**: Not creating pip-installable packages (too complex)
2. **Automatic Installation**: Won't auto-install dependencies (explicit > implicit)
3. **Version Pinning**: Won't pin exact versions (let users choose)

## Philosophy Compliance

Common infrastructure follows amplihack principles:

### Ruthless Simplicity

- Simple scripts, not frameworks
- Clear single-purpose utilities
- No unnecessary abstractions

### Modular Design

- Each component independently functional
- Clear boundaries and interfaces
- Minimal interdependencies

### Explicit Over Implicit

- Symlinks visible in directory structure
- Dependencies clearly documented
- No magic or hidden coupling

### Regeneratable

- All components can be rebuilt from documentation
- Clear specifications for each utility
- Self-contained implementations

## References

- [OOXML Scripts Documentation](ooxml/README.md)
- [Verification Utilities Documentation](verification/README.md)
- [Shared Dependencies List](dependencies.txt)
- [Skills Integration Status](../INTEGRATION_STATUS.md)
- [Architecture Specification](../../../../Specs/OFFICE_SKILLS_INTEGRATION_ARCHITECTURE.md)

## Contributing

To contribute to common infrastructure:

1. Ensure change benefits 2+ skills
2. Test with all dependent skills
3. Update all relevant documentation
4. Submit PR with clear justification

## Support

For issues with common infrastructure:

1. Check component-specific README (ooxml/, verification/)
2. Review troubleshooting section above
3. Test with latest dependencies
4. Open issue with reproduction steps

---

**Last Updated**: 2025-11-08
**Maintained By**: amplihack project
**Current Components**: OOXML scripts, verification utilities
