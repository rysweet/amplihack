# DOCX Skill Integration

## Overview

The DOCX skill provides comprehensive Word document manipulation capabilities for Claude Code, enabling document creation, editing with tracked changes (redlining), text extraction, and complex OOXML operations. This is the third Office skill integrated into amplihack, building on the common OOXML infrastructure established in PR #3.

## Capabilities

- Create new Word documents from scratch using docx-js
- Edit existing documents with tracked changes (redlining)
- Extract text and structure with pandoc
- Access raw XML for complex formatting and metadata
- Batch edit documents with systematic tracked changes workflow
- Convert documents to images for visual analysis
- Handle comments, embedded media, and document structure
- Minimal, precise edits that preserve original formatting

## Integration with amplihack

The DOCX skill follows amplihack's brick philosophy:

- **Self-contained**: All DOCX processing code and dependencies isolated in this directory
- **Clear contract**: Well-defined inputs (DOCX files) and outputs (modified DOCX, text, images)
- **Regeneratable**: Can be rebuilt from SKILL.md specification
- **Zero-BS**: No placeholders - all functionality works or gracefully degrades
- **Shared infrastructure**: Uses common OOXML scripts via symlink (single source of truth)
- **Independent**: Works without other Office skills, minimal cross-dependencies

## Quick Start

1. Install dependencies (see [DEPENDENCIES.md](DEPENDENCIES.md))
2. Verify installation: `python ../common/verification/verify_skill.py docx`
3. Use the skill in Claude Code conversations

Example conversation:

```
User: Create a Word document with a title, 3 sections, and a table
Claude: [Uses DOCX skill with docx-js to create structured document]
```

## Architecture

- **SKILL.md**: Official skill definition from Anthropic (copied verbatim)
- **README.md**: This file - amplihack-specific integration notes
- **DEPENDENCIES.md**: Complete dependency documentation with installation instructions
- **ooxml/**: Symlink to ../common/ooxml (shared OOXML infrastructure)
- **examples/**: Practical usage examples
- **tests/**: Verification tests that skip gracefully if dependencies missing

## Key Workflows

### 1. Creating New Documents

Use **docx-js** (JavaScript/TypeScript) to create documents from scratch:

```javascript
import { Document, Paragraph, TextRun, Packer } from "docx";

const doc = new Document({
  sections: [
    {
      properties: {},
      children: [
        new Paragraph({
          children: [new TextRun({ text: "Hello World", bold: true })],
        }),
      ],
    },
  ],
});

const buffer = await Packer.toBuffer(doc);
fs.writeFileSync("output.docx", buffer);
```

### 2. Editing with Tracked Changes (Redlining)

The redlining workflow is the **recommended default** for editing any document, especially legal, academic, business, or government docs:

1. Convert to markdown: `pandoc --track-changes=all document.docx -o current.md`
2. Identify and group changes into batches (3-10 changes per batch)
3. Unpack document: `python ooxml/scripts/unpack.py document.docx unpacked/`
4. Implement changes in batches using Python scripts
5. Pack document: `python ooxml/scripts/pack.py unpacked/ reviewed.docx`
6. Verify: `pandoc --track-changes=all reviewed.docx -o verification.md`

**Key Principle**: Minimal, precise edits - only mark text that actually changes, preserve original formatting for unchanged text.

### 3. Text Extraction

Use pandoc for quick text extraction with structure preservation:

```bash
pandoc document.docx -o output.md
pandoc --track-changes=all document.docx -o with-changes.md
```

### 4. Raw XML Access

For complex operations (comments, advanced formatting, metadata):

```bash
# Unpack document
python ooxml/scripts/unpack.py document.docx unpacked/

# Read XML files
cat unpacked/word/document.xml  # Main document content
cat unpacked/word/comments.xml  # Comments
ls unpacked/word/media/         # Embedded images

# Pack when done
python ooxml/scripts/pack.py unpacked/ output.docx
```

## Dependencies

The DOCX skill requires both Python and Node.js dependencies:

**Required (Core functionality):**

- defusedxml: Secure XML parsing
- pandoc: Text extraction and conversion
- LibreOffice: Document validation and PDF conversion

**Optional (Enhanced functionality):**

- docx (npm): Creating new documents
- poppler-utils: PDF to image conversion

See [DEPENDENCIES.md](DEPENDENCIES.md) for detailed installation instructions.

## Testing

Run tests to verify the skill:

```bash
cd .claude/skills/docx
pytest tests/ -v
```

Tests will skip gracefully if dependencies are not installed, showing which features are available.

## Usage Examples

See [examples/example_usage.md](examples/example_usage.md) for common workflows:

- Creating business documents from templates
- Implementing contract redlines with tracked changes
- Batch processing legal document reviews
- Extracting and analyzing document structure
- Converting documents to images for visual review
- Handling comments and embedded media
- Systematic editing workflows with batching
- Minimal, precise edits that preserve formatting

## Known Limitations

1. **Node.js required for creation**: docx-js requires Node.js runtime for creating new documents
2. **LibreOffice for validation**: Pack script validation requires LibreOffice installation
3. **Complex formatting**: Advanced Word features (SmartArt, complex tables) may require manual intervention
4. **Tracked changes complexity**: Large documents with many changes should use batching (3-10 changes per batch)
5. **Platform differences**: Some tools may have different behavior on Windows vs Unix
6. **RSID management**: Tracked changes require careful RSID handling for proper Word display

## Philosophy Compliance

This integration follows amplihack's core principles:

- **Ruthless simplicity**: Uses established tools (pandoc, docx-js, OOXML), no custom parsers
- **Modular design**: DOCX skill is a brick with clear studs (public API)
- **Explicit dependencies**: All requirements documented, no automatic installation
- **Graceful degradation**: Optional features skip cleanly if dependencies missing
- **Shared infrastructure**: OOXML scripts in common/ directory, symlinked for reuse
- **Documentation-first**: Complete docs before code execution
- **Minimal, precise edits**: Only mark changed text in tracked changes

## Troubleshooting

**Skill not recognized:**

1. Verify SKILL.md exists in this directory
2. Check YAML frontmatter is valid
3. Verify symlink: `ls -la ooxml/` should show link to ../common/ooxml
4. Restart Claude Code session

**ImportError for defusedxml:**

1. Run verification script: `python ../common/verification/verify_skill.py docx`
2. Install missing dependencies: `pip install defusedxml`
3. Re-run tests to confirm

**Pandoc not found:**

1. Install: `sudo apt-get install pandoc` (Ubuntu) or `brew install pandoc` (macOS)
2. Verify: `pandoc --version`

**Pack script fails validation:**

1. Check LibreOffice installed: `soffice --version`
2. Use `--force` flag to skip validation: `python ooxml/scripts/pack.py unpacked/ output.docx --force`
3. Manually verify document opens in Word

**Tracked changes not appearing:**

1. Verify RSID format (8 hex characters, e.g., "00AB12CD")
2. Check XML structure matches OOXML specification
3. Use minimal edits principle (only mark changed text)
4. Ensure proper `<w:ins>` and `<w:del>` tag structure

**Symlink not working (Windows):**

1. Check if symlinks are enabled (requires admin/developer mode)
2. Alternatively, copy common/ooxml/ to docx/ooxml/ (not recommended)
3. Update scripts to use absolute paths

## Contributing

This skill is sourced from Anthropic's official skills repository. For issues:

1. **amplihack integration issues**: Open issue in amplihack repository
2. **Skill functionality issues**: Report to Anthropic skills repository
3. **Documentation improvements**: Submit PR to amplihack
4. **OOXML script issues**: Check common/ooxml/README.md first

## References

- [SKILL.md](SKILL.md) - Official skill documentation
- [DEPENDENCIES.md](DEPENDENCIES.md) - Complete dependency list
- [examples/example_usage.md](examples/example_usage.md) - Usage examples
- [tests/test_docx_skill.py](tests/test_docx_skill.py) - Verification tests
- [../common/ooxml/README.md](../common/ooxml/README.md) - OOXML scripts documentation
- [Anthropic Skills Repository](https://github.com/anthropics/skills/tree/main/document-skills/docx)

## License

The DOCX skill is provided by Anthropic under their proprietary license. See SKILL.md and Anthropic's LICENSE.txt for complete terms. The amplihack integration code (this README, DEPENDENCIES.md, tests, examples) follows amplihack's license.

---

**Integration Status**: Complete (PR #3)
**Last Updated**: 2025-11-08
**Maintained By**: amplihack project
