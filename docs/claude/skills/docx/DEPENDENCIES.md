# Dependencies for DOCX Skill

## Overview

The DOCX skill requires Python packages for OOXML manipulation, Node.js packages for document creation, and system packages for text extraction and validation. This document provides complete installation instructions for all dependencies.

## Dependency Categories

### Required (Core Functionality)

These packages are required for basic DOCX skill functionality:

**Python Packages:**

- `defusedxml>=0.7.0` - Secure XML parsing for OOXML operations
- `pytest>=7.0.0` - Testing framework for skill verification

**System Packages:**

- `pandoc` - Document conversion and text extraction
- `LibreOffice (soffice)` - Document validation and PDF conversion

### Optional (Enhanced Functionality)

These packages enable additional features but the skill works without them:

**Node Packages:**

- `docx` - Creating new Word documents from JavaScript/TypeScript

**System Packages:**

- `poppler-utils` - PDF to image conversion (pdftoppm)

## Installation Instructions

### Quick Install (Required Only)

Install core packages for basic DOCX functionality:

```bash
# Python packages
pip install defusedxml pytest

# System packages (Ubuntu/Debian)
sudo apt-get install pandoc libreoffice

# System packages (macOS)
brew install pandoc libreoffice
```

### Complete Install (All Features)

Install all packages for full functionality:

```bash
# Python packages
pip install defusedxml pytest

# Node packages
npm install -g docx

# System packages (see platform-specific instructions below)
```

### Platform-Specific Installation

#### macOS

```bash
# Install Homebrew if not already installed
# /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Python packages
pip install defusedxml pytest

# System packages
brew install pandoc libreoffice poppler

# Node packages (optional)
npm install -g docx
```

#### Ubuntu/Debian Linux

```bash
# Python packages
pip install defusedxml pytest

# System packages
sudo apt-get update
sudo apt-get install -y pandoc libreoffice poppler-utils

# Node packages (optional)
# Install Node.js first if not available
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt-get install -y nodejs
npm install -g docx
```

#### Fedora/RHEL/CentOS

```bash
# Python packages
pip install defusedxml pytest

# System packages
sudo dnf install -y pandoc libreoffice poppler-utils

# Node packages (optional)
# Install Node.js first if not available
curl -fsSL https://rpm.nodesource.com/setup_lts.x | sudo bash -
sudo dnf install -y nodejs
npm install -g docx
```

#### Windows

```bash
# Python packages
pip install defusedxml pytest

# System packages via Chocolatey (recommended)
choco install pandoc libreoffice poppler

# Or download manually:
# - Pandoc: https://pandoc.org/installing.html
# - LibreOffice: https://www.libreoffice.org/download/
# - Poppler: https://github.com/oschwartz10612/poppler-windows/releases

# Node packages (optional)
npm install -g docx

# Add installation directories to PATH environment variable
```

## Verification

Verify installations with these commands:

### Python Packages

```bash
# Check defusedxml
python -c "import defusedxml; print('defusedxml installed')"

# Check pytest
pytest --version
```

### System Packages

```bash
# Check pandoc
pandoc --version

# Check LibreOffice
soffice --version

# Check poppler-utils (optional)
pdftoppm -v
```

### Node Packages

```bash
# Check Node.js
node --version

# Check docx package (optional)
npm list -g docx
```

### Automated Verification

Use the pytest test suite to check all dependencies:

```bash
cd .claude/skills/docx
python tests/test_docx_skill.py
```

This will run comprehensive dependency checks and display a detailed report showing which packages are installed and which are missing. Tests will skip gracefully if optional dependencies are unavailable.

## Dependency Details

### pytest

**Purpose**: Testing framework for verifying skill functionality

**Capabilities**:

- Unit testing for DOCX skill components
- Integration testing for workflows
- Dependency verification tests
- Automated test discovery and execution
- Flexible test fixtures and parametrization

**Use in DOCX skill**:

- Verify skill dependencies are installed
- Test OOXML manipulation functions
- Validate tracked changes workflows
- Ensure skill integration with Claude Code

**Version Requirements**: pytest>=7.0.0

**License**: MIT

**Documentation**: https://docs.pytest.org/

### defusedxml

**Purpose**: Secure XML parsing for OOXML operations

**Capabilities**:

- Safe XML parsing that prevents XML bombs and entity expansion attacks
- Drop-in replacement for standard xml.dom.minidom
- Required for OOXML unpack/pack scripts
- Essential for all document manipulation

**Security**: Protects against XML-based attacks (XXE, billion laughs, quadratic blowup)

**License**: Python Software Foundation License

**Documentation**: https://github.com/tiran/defusedxml

### pandoc

**Purpose**: Universal document converter and text extraction tool

**Capabilities**:

- Convert DOCX to markdown with structure preservation
- Support for tracked changes (--track-changes flag)
- Extract text while maintaining formatting information
- Convert between 40+ document formats
- Preserve document structure (headings, lists, tables)

**Use in DOCX skill**:

- Text extraction: `pandoc document.docx -o output.md`
- Tracked changes: `pandoc --track-changes=all document.docx -o output.md`
- Document analysis and verification

**License**: GPL

**Documentation**: https://pandoc.org/

### LibreOffice (soffice)

**Purpose**: Office suite for document validation and conversion

**Capabilities**:

- Validate DOCX files (detect corruption)
- Convert DOCX to PDF for image export
- Headless mode for automated processing
- Support for all Office formats

**Use in DOCX skill**:

- Pack script validation: Verifies document integrity after OOXML edits
- PDF conversion: `soffice --headless --convert-to pdf document.docx`
- Ensures edited documents open correctly in Word

**License**: Mozilla Public License 2.0

**Documentation**: https://www.libreoffice.org/

### docx (Node Package, Optional)

**Purpose**: Create Word documents programmatically using JavaScript/TypeScript

**Capabilities**:

- Create new DOCX files from scratch
- Rich formatting (bold, italic, colors, fonts)
- Tables, sections, headers, footers
- Images and embedded media
- Paragraph and document styling

**Use in DOCX skill**:

- Creating new documents from scratch
- JavaScript/TypeScript-based document generation
- Alternative to Python-based OOXML manipulation

**License**: MIT

**Documentation**: https://docx.js.org/

### poppler-utils (Optional System Package)

**Purpose**: PDF manipulation and conversion tools

**Capabilities**:

- `pdftoppm`: Convert PDF pages to images (JPEG, PNG)
- `pdftotext`: Extract text from PDFs
- `pdfinfo`: Display PDF metadata

**Use in DOCX skill**:

- Visual analysis: Convert DOCX → PDF → Images for review
- Two-step workflow: soffice (DOCX→PDF) + pdftoppm (PDF→images)

**License**: GPL

**Documentation**: https://poppler.freedesktop.org/

## Troubleshooting

### ImportError: No module named 'defusedxml'

**Solution**: Install defusedxml

```bash
pip install defusedxml
```

### ImportError: No module named 'pytest'

**Solution**: Install pytest

```bash
pip install pytest
```

### Command not found: pandoc

**Solution**: Install pandoc

```bash
# macOS
brew install pandoc

# Ubuntu/Debian
sudo apt-get install pandoc

# Windows
choco install pandoc
```

### Command not found: soffice

**Solution**: Install LibreOffice

```bash
# macOS
brew install --cask libreoffice

# Ubuntu/Debian
sudo apt-get install libreoffice

# Windows
choco install libreoffice
```

### Pack script validation fails

**Solution**: Either install LibreOffice or use --force flag

```bash
# Install LibreOffice (recommended)
brew install libreoffice  # macOS
sudo apt-get install libreoffice  # Ubuntu

# Or skip validation (not recommended)
python ooxml/scripts/pack.py unpacked/ output.docx --force
```

### docx package not found (npm)

**Solution**: Install Node.js and docx package

```bash
# Install Node.js first
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo bash -
sudo apt-get install nodejs

# Install docx package
npm install -g docx
```

### pdftoppm not found

**Solution**: Install poppler-utils

```bash
# macOS
brew install poppler

# Ubuntu/Debian
sudo apt-get install poppler-utils

# Windows
choco install poppler
```

### Permission denied errors

**Solution**: Use pip with --user flag or virtual environment

```bash
pip install --user defusedxml
```

### Version conflicts

**Solution**: Use virtual environment for isolation

```bash
python -m venv docx_skill_env
source docx_skill_env/bin/activate  # Linux/macOS
# or
docx_skill_env\Scripts\activate  # Windows

pip install defusedxml
```

## Minimal Installation

For testing or minimal functionality:

```bash
# Absolute minimum (text extraction only)
brew install pandoc  # macOS
sudo apt-get install pandoc  # Ubuntu

# Recommended minimum (text extraction + OOXML editing + testing)
pip install defusedxml pytest
brew install pandoc libreoffice  # macOS
sudo apt-get install pandoc libreoffice  # Ubuntu
```

## Docker Installation

For containerized environments:

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    pandoc \
    libreoffice \
    poppler-utils \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip install --no-cache-dir defusedxml pytest

# Install Node packages (optional)
RUN npm install -g docx
```

## CI/CD Considerations

For GitHub Actions or other CI environments:

```yaml
# .github/workflows/test.yml
- name: Install DOCX skill dependencies
  run: |
    pip install defusedxml pytest
    sudo apt-get update
    sudo apt-get install -y pandoc libreoffice poppler-utils
    npm install -g docx
```

Note: Tests should skip gracefully if optional dependencies are missing.

## Upgrading Dependencies

To upgrade to latest versions:

```bash
# Upgrade Python packages
pip install --upgrade defusedxml pytest

# Upgrade system packages
brew upgrade pandoc libreoffice poppler  # macOS
sudo apt-get update && sudo apt-get upgrade pandoc libreoffice poppler-utils  # Ubuntu

# Upgrade Node packages
npm update -g docx
```

## Dependency Licenses Summary

| Package       | License | Commercial Use        |
| ------------- | ------- | --------------------- |
| pytest        | MIT     | Yes                   |
| defusedxml    | PSF     | Yes                   |
| pandoc        | GPL     | Yes (linking allowed) |
| LibreOffice   | MPL 2.0 | Yes                   |
| docx (npm)    | MIT     | Yes                   |
| poppler-utils | GPL     | Yes (linking allowed) |

All dependencies are permissive licenses compatible with commercial use.

## Shared Dependencies

The DOCX skill shares some dependencies with other Office skills:

**Shared with PPTX:**

- defusedxml (OOXML parsing)
- LibreOffice (validation)

**Shared with PDF:**

- poppler-utils (PDF processing)

See `~/.amplihack/.claude/skills/common/dependencies.txt` for complete shared dependency information.

## Advanced Installation

### Custom LibreOffice Path

If LibreOffice is installed in a non-standard location:

```bash
# Set custom soffice path
export SOFFICE_PATH="/custom/path/to/soffice"

# Or edit pack.py to use custom path
```

### Specific Package Versions

For reproducible environments:

```bash
# Python packages with versions
pip install defusedxml==0.7.1 pytest==7.4.3

# Node packages with versions
npm install -g docx@8.5.0
```

### Offline Installation

For air-gapped environments:

```bash
# Download packages
pip download defusedxml pytest -d ./packages

# Install offline
pip install --no-index --find-links=./packages defusedxml pytest
```

---

**Last Updated**: 2025-11-08
**Maintained By**: amplihack project
