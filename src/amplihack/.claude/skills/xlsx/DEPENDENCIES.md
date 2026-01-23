# Dependencies for XLSX Skill

## Overview

The XLSX skill requires Python packages for spreadsheet manipulation and LibreOffice for formula recalculation. All dependencies are optional in the sense that tests will skip gracefully if they are not installed, but full functionality requires all dependencies.

## Python Packages

### pandas >= 1.5.0

**Purpose**: Data analysis, manipulation, and basic Excel I/O

**Features Used**:

- Reading Excel files: `pd.read_excel()`
- Writing Excel files: `df.to_excel()`
- Data analysis and statistics
- CSV/TSV file handling

**Installation**:

```bash
pip install pandas
```

### openpyxl >= 3.0.0

**Purpose**: Advanced Excel file manipulation with formula and formatting support

**Features Used**:

- Creating and loading workbooks
- Cell-level formula insertion
- Font, fill, and alignment styling
- Column/row dimension control
- Multiple worksheet management
- Preserving existing formulas when editing

**Installation**:

```bash
pip install openpyxl
```

**Note**: openpyxl is the default engine for pandas Excel operations on .xlsx files.

## System Packages

### LibreOffice (Version 6.0+)

**Purpose**: Formula recalculation engine for the recalc.py script

**Why Required**: Excel formulas inserted by openpyxl are stored as strings. LibreOffice's calculation engine evaluates these formulas and saves the computed values back to the file.

**Commands Used**:

- `soffice` - LibreOffice headless mode for automation
- StarBasic macro execution for `calculateAll()` and `store()`

**Installation**:

#### macOS

```bash
# Via Homebrew
brew install --cask libreoffice

# Manual download
# Download from https://www.libreoffice.org/download/download/
# Install the .dmg file
```

#### Linux (Ubuntu/Debian)

```bash
sudo apt-get update
sudo apt-get install libreoffice
```

#### Linux (Fedora/RHEL)

```bash
sudo dnf install libreoffice
```

#### Windows

```bash
# Via Chocolatey
choco install libreoffice

# Manual download
# Download from https://www.libreoffice.org/download/download/
# Run the installer
```

**Size Note**: LibreOffice is approximately 500MB download, 1.5GB installed.

## Optional Dependencies

### gtimeout (macOS only)

**Purpose**: Timeout support for macOS (Linux has timeout built-in)

**Installation**:

```bash
brew install coreutils
```

**Note**: The recalc.py script works without gtimeout on macOS, but timeout protection will be disabled.

## Dependency Installation

### Quick Install (All Dependencies)

```bash
# Install Python packages
pip install pandas openpyxl

# Install LibreOffice (choose your platform)

# macOS
brew install --cask libreoffice
brew install coreutils  # Optional: for timeout support

# Linux (Ubuntu/Debian)
sudo apt-get install libreoffice

# Linux (Fedora)
sudo dnf install libreoffice

# Windows (Chocolatey)
choco install libreoffice
```

### Minimal Install (Data Analysis Only)

If you only need data analysis without formula recalculation:

```bash
pip install pandas openpyxl
```

This provides full functionality except formula recalculation via recalc.py.

## Dependency Verification

### Verify Python Packages

```bash
# Check pandas
python -c "import pandas; print(f'pandas {pandas.__version__}')"

# Check openpyxl
python -c "import openpyxl; print(f'openpyxl {openpyxl.__version__}')"
```

Expected output:

```
pandas 2.0.0
openpyxl 3.1.2
```

### Verify LibreOffice

```bash
# Check LibreOffice is installed
soffice --version

# Test headless mode
soffice --headless --terminate_after_init
```

Expected output:

```
LibreOffice 7.5.3.2 10(Build:2)
```

### Automated Verification

Use the provided verification script:

```bash
cd .claude/skills
python common/verification/verify_skill.py xlsx
```

Expected output if all dependencies installed:

```
Verifying xlsx skill dependencies...

Python packages:
  pandas: Installed
  openpyxl: Installed

System commands:
  soffice: Available

✓ xlsx skill is ready
```

## Troubleshooting

### LibreOffice Not Found

**Symptom**: `soffice: command not found`

**Solution (macOS)**:

```bash
# Add LibreOffice to PATH
echo 'export PATH="/Applications/LibreOffice.app/Contents/MacOS:$PATH"' >> ~/.zshrc
source ~/.zshrc

# Or create symbolic link
sudo ln -s /Applications/LibreOffice.app/Contents/MacOS/soffice /usr/local/bin/soffice
```

**Solution (Linux)**:

```bash
# LibreOffice should install to /usr/bin/soffice
# If not, reinstall
sudo apt-get install --reinstall libreoffice
```

### pandas ImportError

**Symptom**: `ImportError: No module named 'pandas'`

**Solution**:

```bash
# Ensure pip is up to date
pip install --upgrade pip

# Install pandas
pip install pandas

# If using virtual environment, activate it first
source venv/bin/activate  # Unix
venv\Scripts\activate  # Windows
```

### openpyxl ImportError

**Symptom**: `ImportError: No module named 'openpyxl'`

**Solution**:

```bash
pip install openpyxl

# If using pandas, ensure openpyxl is in same environment
pip install pandas openpyxl
```

### LibreOffice Macro Not Configured

**Symptom**: recalc.py returns error about macro not configured

**Solution**: Run recalc.py once with any file. The script automatically sets up the required macro:

```bash
# Create a test file
python -c "from openpyxl import Workbook; wb = Workbook(); wb.save('test.xlsx')"

# Run recalc.py - this will set up the macro
python .claude/skills/xlsx/scripts/recalc.py test.xlsx

# Clean up
rm test.xlsx
```

### Permission Denied on recalc.py

**Symptom**: `Permission denied: recalc.py`

**Solution**:

```bash
chmod +x .claude/skills/xlsx/scripts/recalc.py
```

## Platform-Specific Notes

### macOS

- LibreOffice installs to `/Applications/LibreOffice.app`
- May need to add soffice to PATH (see troubleshooting)
- gtimeout via coreutils recommended but optional

### Linux

- LibreOffice typically pre-installed on many distributions
- timeout command built-in
- Headless mode works without display server

### Windows

- recalc.py has limited timeout support on Windows
- Formula recalculation still works without timeout
- Consider WSL for full Unix-like experience

## Docker Support

If you want to run the XLSX skill in a container:

```dockerfile
FROM python:3.11-slim

# Install LibreOffice
RUN apt-get update && apt-get install -y \
    libreoffice \
    libreoffice-calc \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip install pandas openpyxl

# Copy skill files
COPY .claude/skills/xlsx /app/xlsx

WORKDIR /app
```

## Dependency Matrix

| Feature              | pandas | openpyxl | LibreOffice |
| -------------------- | ------ | -------- | ----------- |
| Read Excel data      | ✓      | ✓        | -           |
| Write Excel data     | ✓      | ✓        | -           |
| Data analysis        | ✓      | -        | -           |
| Insert formulas      | -      | ✓        | -           |
| Cell formatting      | -      | ✓        | -           |
| Recalculate formulas | -      | -        | ✓           |
| Verify zero errors   | -      | ✓        | ✓           |

## Minimum Requirements

**For basic data analysis**: pandas only
**For formula creation**: pandas + openpyxl
**For complete functionality**: pandas + openpyxl + LibreOffice

## CI/CD Integration

For automated testing in CI environments:

```yaml
# GitHub Actions example
- name: Install dependencies
  run: |
    pip install pandas openpyxl pytest
    sudo apt-get install -y libreoffice

- name: Test XLSX skill
  run: pytest .claude/skills/xlsx/tests/
```

**Note**: Tests skip gracefully if LibreOffice is not available.

## Version Compatibility

| Package     | Minimum | Recommended | Tested |
| ----------- | ------- | ----------- | ------ |
| Python      | 3.8     | 3.11        | 3.11   |
| pandas      | 1.5.0   | 2.0.0+      | 2.2.0  |
| openpyxl    | 3.0.0   | 3.1.0+      | 3.1.2  |
| LibreOffice | 6.0     | 7.5+        | 7.5.3  |

## Security Considerations

**LibreOffice Macro Security**: The recalc.py script creates a StarBasic macro for formula recalculation. This macro only calls `calculateAll()` and `store()` - no network access, no file system operations beyond the target file.

**Untrusted Excel Files**: When opening Excel files from untrusted sources, be aware that openpyxl does not execute VBA macros, but malicious formulas could still be present. Use the recalc.py script to verify zero formula errors.

## Support and Resources

- **pandas documentation**: https://pandas.pydata.org/docs/
- **openpyxl documentation**: https://openpyxl.readthedocs.io/
- **LibreOffice documentation**: https://documentation.libreoffice.org/
- **Verification script**: `~/.amplihack/.claude/skills/common/verification/verify_skill.py`
