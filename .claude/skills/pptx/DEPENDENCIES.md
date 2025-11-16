# Dependencies for PPTX Skill

## Overview

The PPTX skill requires Python packages for PowerPoint manipulation, Node.js packages for presentation generation, and system packages for conversion and image processing. This is the most comprehensive dependency set of all Office skills. This document provides complete installation instructions for all dependencies.

## Dependency Categories

### Required (Core Functionality)

These packages are required for basic PPTX skill functionality:

**Python Packages:**

- `markitdown>=0.1.0` - Text extraction from presentations to markdown
- `python-pptx>=0.6.21` - PowerPoint file manipulation and reading
- `defusedxml>=0.7.1` - Safe XML parsing for OOXML operations

### Required (Presentation Creation)

These packages are required for creating presentations from scratch:

**Node.js Packages:**

- `pptxgenjs` - PowerPoint generation from HTML (html2pptx workflow)
- `playwright` - HTML rendering for accurate slide conversion
- `sharp` - SVG rasterization and image processing
- `react-icons` - Icon support for presentations
- `react` - React library for icon rendering
- `react-dom` - React DOM for icon rendering

### Required (System Tools)

These system packages are required for conversion and analysis:

**System Packages:**

- `LibreOffice` - PDF conversion (soffice command)
- `poppler-utils` - PDF to image conversion (pdftoppm command)

## Installation Instructions

### Quick Install (All Dependencies)

Install all packages for full PPTX functionality:

```bash
# Python packages
pip install markitdown python-pptx defusedxml

# Node.js packages (install globally)
npm install -g pptxgenjs playwright sharp react-icons react react-dom

# Initialize playwright browsers
playwright install

# System packages (see platform-specific instructions below)
```

### Platform-Specific Installation

#### macOS

```bash
# Python packages
pip install markitdown python-pptx defusedxml

# Node.js packages
npm install -g pptxgenjs playwright sharp react-icons react react-dom
playwright install

# System packages
brew install libreoffice poppler

# Verify LibreOffice
soffice --version

# Verify poppler
pdftoppm -v
```

#### Ubuntu/Debian Linux

```bash
# Python packages
pip install markitdown python-pptx defusedxml

# Node.js packages (ensure Node.js is installed first)
npm install -g pptxgenjs playwright sharp react-icons react react-dom
playwright install

# System packages
sudo apt-get update
sudo apt-get install -y libreoffice poppler-utils

# Verify installations
soffice --version
pdftoppm -v
```

#### Fedora/RHEL/CentOS

```bash
# Python packages
pip install markitdown python-pptx defusedxml

# Node.js packages
npm install -g pptxgenjs playwright sharp react-icons react react-dom
playwright install

# System packages
sudo dnf install -y libreoffice poppler-utils

# Verify installations
soffice --version
pdftoppm -v
```

#### Windows

```bash
# Python packages
pip install markitdown python-pptx defusedxml

# Node.js packages
npm install -g pptxgenjs playwright sharp react-icons react react-dom
playwright install

# System packages via Chocolatey (recommended)
choco install libreoffice poppler

# Or download manually:
# - LibreOffice: https://www.libreoffice.org/download/
# - Poppler: https://github.com/oschwartz10612/poppler-windows/releases

# Add installation directories to PATH environment variable
```

## Verification

Verify installations with these commands:

### Python Packages

```bash
# Check markitdown
python -c "import markitdown; print('markitdown installed')"

# Check python-pptx
python -c "import pptx; print(f'python-pptx {pptx.__version__}')"

# Check defusedxml
python -c "import defusedxml; print('defusedxml installed')"
```

### Node.js Packages

```bash
# Check pptxgenjs
npm list -g pptxgenjs

# Check playwright
npm list -g playwright
playwright --version

# Check sharp
npm list -g sharp

# Check react-icons
npm list -g react-icons
```

### System Packages

```bash
# Check LibreOffice
soffice --version

# Check poppler-utils
pdftoppm -v
pdfinfo -v
```

### Automated Verification

Use the verification script to check all dependencies:

```bash
cd .claude/skills
python common/verification/verify_skill.py pptx
```

Expected output:

```
Verifying pptx skill dependencies...

Python packages:
  markitdown: Installed
  python-pptx: Installed
  defusedxml: Installed

Node.js packages:
  pptxgenjs: Installed
  playwright: Installed
  sharp: Installed

System commands:
  soffice: Available
  pdftoppm: Available

✓ pptx skill is ready
```

## Dependency Details

### markitdown

**Purpose**: Text extraction from PowerPoint presentations to markdown format

**Capabilities**:

- Convert .pptx to markdown
- Preserve slide structure
- Extract text content
- Support for multiple Office formats

**License**: MIT

**Documentation**: https://github.com/microsoft/markitdown

**Installation Notes**: Use `markitdown[pptx]` to ensure PPTX support dependencies are included

### python-pptx

**Purpose**: PowerPoint file manipulation and reading in Python

**Capabilities**:

- Read existing .pptx files
- Access slide content and structure
- Extract text and shapes
- Modify presentations programmatically
- Access slide layouts and masters

**License**: MIT

**Documentation**: https://python-pptx.readthedocs.io/

### defusedxml

**Purpose**: Secure XML parsing for OOXML operations

**Capabilities**:

- Safe XML parsing (prevents XML bombs and vulnerabilities)
- Drop-in replacement for standard XML libraries
- Used by OOXML manipulation scripts

**License**: Python Software Foundation License

**Documentation**: https://github.com/tiran/defusedxml

### pptxgenjs

**Purpose**: PowerPoint generation from HTML (html2pptx workflow)

**Capabilities**:

- Convert HTML slides to PowerPoint
- Accurate positioning and styling
- Chart and table support
- Custom layouts and designs
- Multi-slide presentations

**License**: MIT

**Documentation**: https://gitbrent.github.io/PptxGenJS/

**Installation Notes**: Install globally with `-g` flag for command-line access

### playwright

**Purpose**: HTML rendering for accurate slide conversion

**Capabilities**:

- Headless browser automation
- HTML to image rendering
- Screenshot capture
- Cross-browser support

**License**: Apache-2.0

**Documentation**: https://playwright.dev/

**Installation Notes**: After installing, run `playwright install` to download browser binaries

### sharp

**Purpose**: SVG rasterization and image processing

**Capabilities**:

- Convert SVG to PNG
- Image resizing and optimization
- Format conversion
- High-performance image processing

**License**: Apache-2.0

**Documentation**: https://sharp.pixelplumbing.com/

### react-icons

**Purpose**: Icon library for presentations

**Capabilities**:

- Access to popular icon sets
- SVG icon rendering
- Integration with React

**License**: MIT

**Documentation**: https://react-icons.github.io/react-icons/

**Installation Notes**: Requires react and react-dom as peer dependencies

### LibreOffice

**Purpose**: PDF conversion from PowerPoint

**Capabilities**:

- Convert .pptx to .pdf headlessly
- Command-line batch processing
- Cross-platform support
- Preserves layouts and formatting

**Command**: `soffice`

**License**: Mozilla Public License 2.0

**Documentation**: https://www.libreoffice.org/

**Size Warning**: LibreOffice is a large download (500MB+)

### poppler-utils

**Purpose**: PDF to image conversion for thumbnails

**Capabilities**:

- Convert PDF pages to images (pdftoppm)
- Extract PDF metadata (pdfinfo)
- Various PDF utility commands
- High-quality rendering

**Commands**: `pdftoppm`, `pdfinfo`, `pdfimages`

**License**: GPL

**Documentation**: https://poppler.freedesktop.org/

## Troubleshooting

### ImportError: No module named 'markitdown'

**Solution**: Install markitdown with PPTX support

```bash
pip install "markitdown[pptx]"
```

### ModuleNotFoundError: No module named 'pptx'

**Solution**: Install python-pptx

```bash
pip install python-pptx
```

### Error: Cannot find module 'pptxgenjs'

**Solution**: Install pptxgenjs globally

```bash
npm install -g pptxgenjs
```

### playwright: command not found

**Solution**: Install playwright and browser binaries

```bash
npm install -g playwright
playwright install
```

### sharp: Error loading shared library

**Solution**: Rebuild sharp or install system dependencies

```bash
npm uninstall -g sharp
npm install -g sharp

# On Linux, may need:
sudo apt-get install -y libvips-dev
```

### Command not found: soffice

**Solution**: Install LibreOffice

```bash
# macOS
brew install libreoffice

# Ubuntu/Debian
sudo apt-get install libreoffice

# Windows
choco install libreoffice
```

### Command not found: pdftoppm

**Solution**: Install poppler-utils

```bash
# macOS
brew install poppler

# Ubuntu/Debian
sudo apt-get install poppler-utils

# Windows
choco install poppler
```

### playwright install fails

**Solution**: Check Node.js version and install browsers manually

```bash
# Verify Node.js version (requires Node 14+)
node --version

# Try installing browsers separately
npx playwright install chromium
```

### Permission denied errors

**Solution**: Use npm with --unsafe-perm flag or install in user directory

```bash
npm install -g --unsafe-perm pptxgenjs playwright sharp

# Or use a Node version manager like nvm
nvm use 18
npm install -g pptxgenjs playwright sharp
```

## Minimal Installation

For testing or specific workflows:

```bash
# Text extraction only
pip install markitdown defusedxml

# OOXML manipulation only
pip install python-pptx defusedxml

# Full creation workflow
pip install markitdown python-pptx defusedxml
npm install -g pptxgenjs playwright sharp react-icons react react-dom
playwright install
```

## Docker Installation

For containerized environments:

```dockerfile
FROM node:18-slim

# Install Python
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    libreoffice \
    poppler-utils \
    libvips-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip3 install --no-cache-dir \
    markitdown \
    python-pptx \
    defusedxml

# Install Node.js packages
RUN npm install -g \
    pptxgenjs \
    playwright \
    sharp \
    react-icons \
    react \
    react-dom

# Install playwright browsers
RUN playwright install --with-deps chromium

# Set working directory
WORKDIR /workspace
```

## CI/CD Considerations

For GitHub Actions or other CI environments:

```yaml
# .github/workflows/test.yml
- name: Install PPTX skill dependencies
  run: |
    # Python packages
    pip install markitdown python-pptx defusedxml

    # System packages
    sudo apt-get update
    sudo apt-get install -y libreoffice poppler-utils

    # Node.js packages
    npm install -g pptxgenjs playwright sharp react-icons react react-dom
    playwright install --with-deps chromium
```

Note: Tests should skip gracefully if optional dependencies are missing.

## Upgrading Dependencies

To upgrade to latest versions:

```bash
# Upgrade Python packages
pip install --upgrade markitdown python-pptx defusedxml

# Upgrade Node.js packages
npm update -g pptxgenjs playwright sharp react-icons react react-dom

# Update playwright browsers
playwright install
```

## Dependency Licenses Summary

| Package       | License    | Commercial Use        |
| ------------- | ---------- | --------------------- |
| markitdown    | MIT        | Yes                   |
| python-pptx   | MIT        | Yes                   |
| defusedxml    | PSFL       | Yes                   |
| pptxgenjs     | MIT        | Yes                   |
| playwright    | Apache-2.0 | Yes                   |
| sharp         | Apache-2.0 | Yes                   |
| react-icons   | MIT        | Yes                   |
| react         | MIT        | Yes                   |
| react-dom     | MIT        | Yes                   |
| LibreOffice   | MPL-2.0    | Yes                   |
| poppler-utils | GPL        | Yes (linking allowed) |

All dependencies are permissive licenses compatible with commercial use.

## Node.js Version Requirements

**Minimum Node.js Version**: 14.x
**Recommended**: 18.x LTS or higher

Check your Node.js version:

```bash
node --version
```

If needed, upgrade Node.js:

```bash
# Using nvm (recommended)
nvm install 18
nvm use 18

# Or download from nodejs.org
```

## Common Installation Patterns

### Development Environment

```bash
# Full installation for development
pip install markitdown python-pptx defusedxml
npm install -g pptxgenjs playwright sharp react-icons react react-dom
playwright install
brew install libreoffice poppler  # macOS
```

### Production Environment

```bash
# Minimal installation for specific workflows
pip install markitdown defusedxml  # Text extraction only
# OR
pip install python-pptx defusedxml  # OOXML manipulation only
# OR
# Full installation if creating presentations
```

### Testing Environment

```bash
# Install all dependencies for comprehensive testing
pip install markitdown python-pptx defusedxml pytest
npm install -g pptxgenjs playwright sharp react-icons react react-dom
playwright install --with-deps
sudo apt-get install -y libreoffice poppler-utils  # Linux
```

---

**Last Updated**: 2025-11-08
**Maintained By**: amplihack project
