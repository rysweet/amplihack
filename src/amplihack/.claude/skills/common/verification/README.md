# Skill Verification Utilities

This directory contains utilities for verifying Office skill dependencies.

## verify_skill.py

Main verification script that checks if a skill's dependencies are installed.

### Usage

```bash
# Verify specific skill
python verify_skill.py pdf
python verify_skill.py xlsx
python verify_skill.py docx
python verify_skill.py pptx

# Verify all skills
python verify_skill.py all
```

### What It Checks

**Python Packages**:

- Uses `importlib` to attempt import
- Reports version if available
- Distinguishes required vs optional packages

**System Commands**:

- Runs `command --version` to check availability
- Handles timeouts and errors gracefully
- All system commands treated as optional

### Exit Codes

- `0`: All required dependencies met
- `1`: Missing required dependencies or unknown skill

### Output Format

```
Verifying pdf skill dependencies...
======================================================================

Required Python packages:
  ✓ pypdf               : Installed (v4.0.1)
  ✓ pdfplumber          : Installed (v0.10.3)
  ✓ reportlab           : Installed (v4.0.7)
  ✓ pandas              : Installed (v2.1.4)

Optional Python packages:
  ✓ pytesseract         : Installed (v0.3.10)
  ○ pdf2image           : Not installed

Optional system commands:
  ✓ pdftotext           : Available (pdftotext version 22.12.0)
  ✓ qpdf                : Available (qpdf version 11.6.3)
  ○ pdftk               : Not found
  ✓ tesseract           : Available (tesseract 5.3.3)

======================================================================
✓ pdf skill is ready (all required dependencies met)

Optional features:
  Python packages: 1/2 available
  System commands: 3/4 available
======================================================================
```

### Symbols

- `✓` : Installed/Available (required or optional)
- `✗` : Missing (required)
- `○` : Not installed/available (optional)

### Integration with Tests

Skills tests can use verification functions directly:

```python
import sys
from pathlib import Path

# Add verification utilities to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "common" / "verification"))
from verify_skill import check_python_package, check_system_command

# Check dependencies
def check_dependencies():
    return all(check_python_package(pkg) for pkg in REQUIRED_PACKAGES)

@pytest.mark.skipif(
    not check_dependencies(),
    reason="Required dependencies not installed"
)
def test_basic_functionality():
    # Test code here
    pass
```

## Supported Skills

Current skill definitions:

### pdf

- **Required Python**: pypdf, pdfplumber, reportlab, pandas
- **Optional Python**: pytesseract, pdf2image, pillow
- **Optional System**: pdftotext, qpdf, pdftk, tesseract

### xlsx

- **Required Python**: pandas, openpyxl
- **Optional System**: soffice (LibreOffice)

### docx

- **Required Python**: defusedxml
- **Optional System**: pandoc, soffice, pdftoppm

### pptx

- **Required Python**: markitdown, defusedxml
- **Optional System**: node, soffice

## Implementation Details

### check_python_package(package: str) -> Tuple[bool, str]

Attempts to import a Python package using `importlib`.

**Returns**:

- `(True, "Installed (v{version})")` if package found
- `(False, "Not installed")` if import fails

**Handles**:

- Missing `__version__` attribute
- Import errors
- Package aliases

### check_system_command(command: str) -> Tuple[bool, str]

Runs `command --version` to check if command is available.

**Returns**:

- `(True, "Available ({version})")` if command works
- `(False, "{error}")` for various error conditions

**Handles**:

- Command not found
- Command errors
- Timeouts (5 second limit)
- Non-zero exit codes

### verify_skill(skill_name, python_required, python_optional, system_optional) -> bool

Main verification function that checks all dependencies for a skill.

**Returns**:

- `True` if all required dependencies met
- `False` if any required dependency missing

**Side Effects**:

- Prints detailed status report to stdout
- Provides installation hints for missing packages

## Error Handling

The script handles various error conditions:

- **Unknown skill**: Prints list of available skills
- **Missing packages**: Shows pip install command
- **Command timeouts**: Marks as timeout, doesn't crash
- **Import errors**: Caught and reported cleanly

## Extensibility

To add a new skill:

1. Add skill definition to `SKILLS` dict:

   ```python
   SKILLS = {
       "newskill": {
           "python_required": ["package1", "package2"],
           "python_optional": ["optional1"],
           "system_optional": ["command1"],
       },
   }
   ```

2. Update skill's tests to reference verification

3. Document dependencies in skill's DEPENDENCIES.md

## Testing the Verifier

To test the verification script itself:

```bash
# Should succeed if pdf skill dependencies installed
python verify_skill.py pdf
echo $?  # Should be 0

# Should fail for non-existent skill
python verify_skill.py fake
echo $?  # Should be 1

# Should show summary for all skills
python verify_skill.py all
```

## Platform Compatibility

The script works on:

- macOS
- Linux (all distributions)
- Windows (with minor differences in command availability)

Platform-specific behaviors:

- Windows: Some commands (pdftk) may not be available
- macOS: Some commands need Homebrew installation
- Linux: Most commands available in package managers

## Performance

Verification is fast:

- Python checks: ~10ms per package
- System checks: ~100ms per command (with 5s timeout)
- Total time: Usually < 2 seconds for all skills

## Maintenance

Update this script when:

- New skills are added
- Dependency requirements change
- New dependency types needed (e.g., Rust packages)
- Output format improvements

## Related Files

- `../dependencies.txt` - Shared dependencies documentation
- `../../pdf/DEPENDENCIES.md` - PDF skill dependencies
- `../../*/tests/test_*_skill.py` - Skill test files that use verification

---

**Last Updated**: 2025-11-08
**Maintained By**: amplihack project
