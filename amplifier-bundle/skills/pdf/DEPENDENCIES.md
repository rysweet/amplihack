# Dependencies for PDF Skill

## Overview

The PDF skill requires Python packages for PDF manipulation and optionally system packages for enhanced functionality like OCR and command-line processing. This document provides complete installation instructions for all dependencies.

## Dependency Categories

### Required (Core Functionality)

These packages are required for basic PDF skill functionality:

**Python Packages:**

- `pypdf>=4.0.0` - PDF manipulation (merge, split, rotate, metadata)
- `pdfplumber>=0.10.0` - Text and table extraction with layout preservation
- `reportlab>=4.0.0` - PDF generation and creation
- `pandas>=2.0.0` - Data manipulation for table processing

### Optional (Enhanced Functionality)

These packages enable additional features but the skill works without them:

**Python Packages:**

- `pytesseract>=0.3.10` - OCR for scanned PDFs (requires tesseract engine)
- `pdf2image>=1.16.0` - PDF to image conversion for OCR (requires poppler)
- `pillow>=10.0.0` - Image processing support

**System Packages:**

- `poppler-utils` - Command-line PDF tools (pdftotext, pdfimages, pdftoppm)
- `qpdf` - Advanced PDF manipulation and repair
- `pdftk` - PDF toolkit for complex operations
- `tesseract-ocr` - OCR engine for pytesseract

## Installation Instructions

### Quick Install (Required Only)

Install core Python packages for basic PDF functionality:

```bash
pip install pypdf pdfplumber reportlab pandas
```

### Complete Install (All Features)

Install all packages for full functionality:

```bash
# Python packages
pip install pypdf pdfplumber reportlab pandas pytesseract pdf2image pillow

# System packages (see platform-specific instructions below)
```

### Platform-Specific Installation

#### macOS

```bash
# Install Homebrew if not already installed
# /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Python packages
pip install pypdf pdfplumber reportlab pandas pytesseract pdf2image pillow

# System packages
brew install poppler qpdf tesseract

# Note: pdftk is no longer maintained for macOS
# Alternative: use pypdf or qpdf for equivalent operations
```

#### Ubuntu/Debian Linux

```bash
# Python packages
pip install pypdf pdfplumber reportlab pandas pytesseract pdf2image pillow

# System packages
sudo apt-get update
sudo apt-get install -y poppler-utils qpdf pdftk tesseract-ocr

# Additional tesseract language packs (optional)
sudo apt-get install -y tesseract-ocr-eng tesseract-ocr-spa
```

#### Fedora/RHEL/CentOS

```bash
# Python packages
pip install pypdf pdfplumber reportlab pandas pytesseract pdf2image pillow

# System packages
sudo dnf install -y poppler-utils qpdf pdftk tesseract

# Additional tesseract language packs (optional)
sudo dnf install -y tesseract-langpack-eng tesseract-langpack-spa
```

#### Windows

```bash
# Python packages
pip install pypdf pdfplumber reportlab pandas pytesseract pdf2image pillow

# System packages
# Install via Chocolatey (recommended)
choco install poppler qpdf tesseract

# Or download manually:
# - Poppler: https://github.com/oschwartz10612/poppler-windows/releases
# - QPDF: https://qpdf.sourceforge.io/
# - Tesseract: https://github.com/UB-Mannheim/tesseract/wiki
# - PDFtk: https://www.pdflabs.com/tools/pdftk-the-pdf-toolkit/

# Add installation directories to PATH environment variable
```

## Verification

Verify installations with these commands:

### Python Packages

```bash
# Check pypdf
python -c "import pypdf; print(f'pypdf {pypdf.__version__}')"

# Check pdfplumber
python -c "import pdfplumber; print(f'pdfplumber {pdfplumber.__version__}')"

# Check reportlab
python -c "import reportlab; print(f'reportlab {reportlab.Version}')"

# Check pandas
python -c "import pandas; print(f'pandas {pandas.__version__}')"

# Check pytesseract (optional)
python -c "import pytesseract; print('pytesseract installed')"

# Check pdf2image (optional)
python -c "import pdf2image; print('pdf2image installed')"
```

### System Packages

```bash
# Check poppler-utils
pdftotext -v

# Check qpdf
qpdf --version

# Check pdftk (may not be available on all platforms)
pdftk --version

# Check tesseract
tesseract --version
```

### Automated Verification

Use the verification script to check all dependencies:

```bash
cd .claude/skills
python common/verification/verify_skill.py pdf
```

Expected output:

```
Verifying pdf skill dependencies...

Python packages:
  pypdf: Installed
  pdfplumber: Installed
  reportlab: Installed
  pandas: Installed
  pytesseract: Installed (or Not installed)
  pdf2image: Installed (or Not installed)

System commands:
  pdftotext: Available (or Not available)
  qpdf: Available (or Not available)
  pdftk: Available (or Not available)
  tesseract: Available (or Not available)

✓ pdf skill is ready (or ✗ pdf skill is missing dependencies)
```

## Dependency Details

### pypdf

**Purpose**: Core PDF manipulation library for Python

**Capabilities**:

- Merge multiple PDFs
- Split PDFs into individual pages
- Rotate, crop, and scale pages
- Extract metadata (title, author, creation date)
- Encrypt and decrypt PDFs
- Extract text (basic)

**License**: BSD-3-Clause

**Documentation**: https://pypdf.readthedocs.io/

### pdfplumber

**Purpose**: Advanced text and table extraction from PDFs

**Capabilities**:

- Extract text with layout preservation
- Extract tables with cell boundaries
- Access detailed page information (lines, curves, rectangles)
- Visual debugging tools
- Better handling of complex layouts than pypdf

**License**: MIT

**Documentation**: https://github.com/jsvine/pdfplumber

### reportlab

**Purpose**: PDF generation from Python code

**Capabilities**:

- Create PDFs from scratch
- Draw text, shapes, images
- Support for forms and interactive elements
- Multi-page documents with templates
- Tables and flowable layouts (Platypus)

**License**: BSD-3-Clause

**Documentation**: https://www.reportlab.com/docs/reportlab-userguide.pdf

### pandas

**Purpose**: Data manipulation for extracted tables

**Capabilities**:

- Convert extracted tables to DataFrames
- Export to Excel, CSV, JSON
- Data cleaning and transformation
- Analysis and aggregation

**License**: BSD-3-Clause

**Documentation**: https://pandas.pydata.org/docs/

### pytesseract (Optional)

**Purpose**: OCR (Optical Character Recognition) for scanned PDFs

**Capabilities**:

- Extract text from image-based PDFs
- Multi-language support
- Confidence scores for recognized text

**Requirements**: Requires tesseract-ocr system package

**License**: Apache-2.0

**Documentation**: https://github.com/madmaze/pytesseract

### pdf2image (Optional)

**Purpose**: Convert PDF pages to images for OCR processing

**Capabilities**:

- Convert PDF to PIL Image objects
- Specify DPI for quality control
- Page range selection

**Requirements**: Requires poppler-utils system package

**License**: MIT

**Documentation**: https://github.com/Belval/pdf2image

### poppler-utils (Optional System Package)

**Purpose**: Command-line PDF processing tools

**Tools Included**:

- `pdftotext`: Extract text from PDFs
- `pdfimages`: Extract images from PDFs
- `pdftoppm`: Convert PDF to PPM/PNG images
- `pdfinfo`: Display PDF metadata
- `pdfseparate`: Split PDF into pages
- `pdfunite`: Merge PDFs

**License**: GPL

**Documentation**: https://poppler.freedesktop.org/

### qpdf (Optional System Package)

**Purpose**: Command-line PDF transformation and inspection

**Capabilities**:

- Merge and split PDFs
- Rotate pages
- Encrypt and decrypt
- Linearize for web optimization
- Repair corrupted PDFs

**License**: Apache-2.0

**Documentation**: https://qpdf.sourceforge.io/

### pdftk (Optional System Package)

**Purpose**: PDF toolkit for complex operations

**Capabilities**:

- Merge, split, rotate PDFs
- Apply watermarks
- Fill PDF forms
- Update metadata
- Attach files

**Note**: No longer actively maintained, may not be available on newer systems

**License**: GPL

**Documentation**: https://www.pdflabs.com/docs/pdftk-man-page/

### tesseract-ocr (Optional System Package)

**Purpose**: OCR engine for extracting text from images

**Capabilities**:

- Text recognition from images
- 100+ language support
- Configurable recognition modes
- Output in multiple formats

**License**: Apache-2.0

**Documentation**: https://github.com/tesseract-ocr/tesseract

## Troubleshooting

### ImportError: No module named 'pypdf'

**Solution**: Install pypdf

```bash
pip install pypdf
```

### ModuleNotFoundError: No module named 'pdfplumber'

**Solution**: Install pdfplumber

```bash
pip install pdfplumber
```

### pytesseract.pytesseract.TesseractNotFoundError

**Solution**: Install tesseract-ocr system package

```bash
# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# Windows
choco install tesseract
```

### pdf2image requires poppler

**Solution**: Install poppler-utils

```bash
# macOS
brew install poppler

# Ubuntu/Debian
sudo apt-get install poppler-utils

# Windows
choco install poppler
```

### Command not found: qpdf

**Solution**: Install qpdf

```bash
# macOS
brew install qpdf

# Ubuntu/Debian
sudo apt-get install qpdf

# Windows
choco install qpdf
```

### Command not found: pdftk

**Solution**: pdftk may not be available on your platform. Use alternatives:

- Use pypdf for merge/split operations
- Use qpdf for advanced operations
- Use pypdf for form filling

### Permission denied errors

**Solution**: Use pip with --user flag or virtual environment

```bash
pip install --user pypdf pdfplumber reportlab pandas
```

### Version conflicts

**Solution**: Use virtual environment for isolation

```bash
python -m venv pdf_skill_env
source pdf_skill_env/bin/activate  # Linux/macOS
# or
pdf_skill_env\Scripts\activate  # Windows

pip install pypdf pdfplumber reportlab pandas
```

## Minimal Installation

For testing or minimal functionality:

```bash
# Absolute minimum (merge, split, basic text extraction)
pip install pypdf

# Recommended minimum (adds table extraction and PDF creation)
pip install pypdf pdfplumber reportlab pandas
```

## Docker Installation

For containerized environments:

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    poppler-utils \
    qpdf \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip install --no-cache-dir \
    pypdf \
    pdfplumber \
    reportlab \
    pandas \
    pytesseract \
    pdf2image \
    pillow
```

## CI/CD Considerations

For GitHub Actions or other CI environments:

```yaml
# .github/workflows/test.yml
- name: Install PDF skill dependencies
  run: |
    pip install pypdf pdfplumber reportlab pandas pytesseract pdf2image pillow
    sudo apt-get update
    sudo apt-get install -y poppler-utils qpdf tesseract-ocr
```

Note: Tests should skip gracefully if optional dependencies are missing.

## Upgrading Dependencies

To upgrade to latest versions:

```bash
# Upgrade all PDF skill dependencies
pip install --upgrade pypdf pdfplumber reportlab pandas pytesseract pdf2image pillow

# Or upgrade individually
pip install --upgrade pypdf
pip install --upgrade pdfplumber
```

## Dependency Licenses Summary

| Package       | License      | Commercial Use        |
| ------------- | ------------ | --------------------- |
| pypdf         | BSD-3-Clause | Yes                   |
| pdfplumber    | MIT          | Yes                   |
| reportlab     | BSD-3-Clause | Yes                   |
| pandas        | BSD-3-Clause | Yes                   |
| pytesseract   | Apache-2.0   | Yes                   |
| pdf2image     | MIT          | Yes                   |
| poppler-utils | GPL          | Yes (linking allowed) |
| qpdf          | Apache-2.0   | Yes                   |
| pdftk         | GPL          | Yes (linking allowed) |
| tesseract-ocr | Apache-2.0   | Yes                   |

All dependencies are permissive licenses compatible with commercial use.

---

**Last Updated**: 2025-11-08
**Maintained By**: amplihack project
