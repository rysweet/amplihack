# PDF Skill Integration

## Overview

The PDF skill provides comprehensive PDF manipulation capabilities for Claude Code, enabling text and table extraction, PDF creation, document merging/splitting, and form handling. This is the first Office skill integrated into amplihack, establishing the foundation for the broader Office skills integration.

## Capabilities

- Extract text from PDFs with layout preservation
- Extract tables and convert to structured data (Excel, CSV)
- Create new PDFs programmatically with text, shapes, and multi-page layouts
- Merge multiple PDFs into a single document
- Split PDFs into individual pages
- Rotate pages and manipulate PDF structure
- Extract and manipulate PDF metadata
- Add watermarks to documents
- Password protection and decryption
- OCR for scanned documents (with optional dependencies)
- Extract images from PDFs
- Fill and process PDF forms

## Integration with amplihack

The PDF skill follows amplihack's brick philosophy:

- **Self-contained**: All PDF processing code and dependencies isolated in this directory
- **Clear contract**: Well-defined inputs (PDF files) and outputs (text, tables, new PDFs)
- **Regeneratable**: Can be rebuilt from SKILL.md specification
- **Zero-BS**: No placeholders - all functionality works or gracefully degrades
- **Independent**: Works without other Office skills, no cross-dependencies

## Quick Start

1. Install dependencies (see [DEPENDENCIES.md](DEPENDENCIES.md))
2. Verify installation: `python ../common/verification/verify_skill.py pdf`
3. Use the skill in Claude Code conversations

Example conversation:

```
User: Extract all tables from this sales report PDF and save to Excel
Claude: [Uses PDF skill to extract tables with pdfplumber and saves to .xlsx]
```

## Architecture

- **SKILL.md**: Official skill definition from Anthropic (copied verbatim)
- **README.md**: This file - amplihack-specific integration notes
- **DEPENDENCIES.md**: Complete dependency documentation with installation instructions
- **examples/**: Practical usage examples
- **tests/**: Verification tests that skip gracefully if dependencies missing

## Dependencies

The PDF skill has minimal required dependencies and several optional ones:

**Required (Core functionality):**

- pypdf: PDF manipulation
- pdfplumber: Text and table extraction
- reportlab: PDF creation
- pandas: Data manipulation

**Optional (Enhanced functionality):**

- pytesseract: OCR for scanned PDFs
- pdf2image: PDF to image conversion
- poppler-utils: Command-line PDF tools
- qpdf: Advanced PDF manipulation
- pdftk: PDF toolkit

See [DEPENDENCIES.md](DEPENDENCIES.md) for detailed installation instructions.

## Testing

Run tests to verify the skill:

```bash
cd .claude/skills/pdf
pytest tests/ -v
```

Tests will skip gracefully if dependencies are not installed, showing which features are available.

## Usage Examples

See [examples/example_usage.md](examples/example_usage.md) for common workflows:

- Extracting text from research papers
- Converting tables from financial reports to Excel
- Creating automated report PDFs
- Merging multiple invoices
- Bulk processing document archives

## Known Limitations

1. **OCR requires additional setup**: pytesseract and tesseract engine must be installed separately
2. **Large PDFs**: Memory-intensive operations on very large files may require streaming approaches
3. **Complex layouts**: Table extraction accuracy depends on document structure
4. **Scanned documents**: Text extraction requires OCR, which is slower and less accurate
5. **Platform differences**: Some command-line tools (pdftk) may not be available on all platforms

## Philosophy Compliance

This integration follows amplihack's core principles:

- **Ruthless simplicity**: Uses established libraries, no custom PDF parsers
- **Modular design**: PDF skill is a brick with clear studs (public API)
- **Explicit dependencies**: All requirements documented, no automatic installation
- **Graceful degradation**: Optional features skip cleanly if dependencies missing
- **Documentation-first**: Complete docs before code execution

## Troubleshooting

**Skill not recognized:**

1. Verify SKILL.md exists in this directory
2. Check YAML frontmatter is valid
3. Restart Claude Code session

**ImportError for dependencies:**

1. Run verification script: `python ../common/verification/verify_skill.py pdf`
2. Install missing dependencies from DEPENDENCIES.md
3. Re-run tests to confirm

**OCR not working:**

1. Install tesseract engine (system package)
2. Install pytesseract Python package
3. Verify: `tesseract --version`

**Table extraction poor quality:**

1. Try different pages or PDFs
2. Check if PDF is scanned (requires OCR first)
3. Consider manual extraction for complex layouts

## Contributing

This skill is sourced from Anthropic's official skills repository. For issues:

1. **amplihack integration issues**: Open issue in amplihack repository
2. **Skill functionality issues**: Report to Anthropic skills repository
3. **Documentation improvements**: Submit PR to amplihack

## References

- [SKILL.md](SKILL.md) - Official skill documentation
- [DEPENDENCIES.md](DEPENDENCIES.md) - Complete dependency list
- [examples/example_usage.md](examples/example_usage.md) - Usage examples
- [tests/test_pdf_skill.py](tests/test_pdf_skill.py) - Verification tests
- [Anthropic Skills Repository](https://github.com/anthropics/skills/tree/main/document-skills/pdf)

## License

The PDF skill is provided by Anthropic under their proprietary license. See SKILL.md and Anthropic's LICENSE.txt for complete terms. The amplihack integration code (this README, DEPENDENCIES.md, tests, examples) follows amplihack's license.

---

**Integration Status**: Complete (PR #1)
**Last Updated**: 2025-11-08
**Maintained By**: amplihack project
