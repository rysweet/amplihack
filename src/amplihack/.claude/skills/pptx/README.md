# PPTX Skill Integration

## Overview

The PPTX skill provides comprehensive PowerPoint presentation capabilities for Claude Code, enabling presentation creation, editing, analysis, and template-based workflows. This is the fourth and final Office skill integrated into amplihack, completing the full suite of document manipulation capabilities.

## Capabilities

- Create presentations from scratch with custom designs and 18 color palettes
- Edit existing presentations using OOXML manipulation
- Extract text from presentations to markdown
- Create presentations from templates with slide rearrangement
- Generate visual thumbnail grids for analysis
- Replace placeholder text while preserving formatting
- Access raw XML for comments, speaker notes, and animations
- Convert presentations to PDF and images
- Support for charts, tables, and complex layouts
- Design principles with web-safe fonts and visual hierarchy

## Integration with amplihack

The PPTX skill follows amplihack's brick philosophy:

- **Self-contained**: All PPTX processing code and dependencies isolated in this directory
- **Clear contract**: Well-defined inputs (PPTX files, HTML, templates) and outputs (presentations, thumbnails)
- **Regeneratable**: Can be rebuilt from SKILL.md specification
- **Zero-BS**: No placeholders - all functionality works or gracefully degrades
- **Shared infrastructure**: Uses common OOXML scripts (via symlink) shared with DOCX skill

## Quick Start

1. Install dependencies (see [DEPENDENCIES.md](DEPENDENCIES.md))
2. Verify installation: `python ../common/verification/verify_skill.py pptx`
3. Use the skill in Claude Code conversations

Example conversation:

```
User: Create a 5-slide presentation about AI trends with modern design
Claude: [Uses PPTX skill to create presentation with custom color palette and layouts]
```

## Architecture

- **SKILL.md**: Official skill definition from Anthropic (copied verbatim)
- **README.md**: This file - amplihack-specific integration notes
- **DEPENDENCIES.md**: Complete dependency documentation with installation instructions
- **scripts/**: PPTX-specific scripts (thumbnail.py, rearrange.py, inventory.py, replace.py, html2pptx.js)
- **ooxml/**: Symlink to ../common/ooxml for shared OOXML manipulation scripts
- **examples/**: Practical usage examples
- **tests/**: Verification tests that skip gracefully if dependencies missing

## Dependencies

The PPTX skill has the most comprehensive dependencies of all Office skills:

**Required (Core functionality):**

- markitdown: Text extraction from presentations
- defusedxml: Safe XML parsing for OOXML
- python-pptx: PowerPoint file manipulation

**Required (Presentation creation):**

- pptxgenjs: PowerPoint generation via html2pptx
- playwright: HTML rendering
- sharp: Image processing and SVG rasterization

**Required (System tools):**

- LibreOffice: PDF conversion
- poppler-utils: PDF to image conversion

See [DEPENDENCIES.md](DEPENDENCIES.md) for detailed installation instructions.

## Key Workflows

### 1. Creating from Scratch

Use html2pptx workflow for custom presentations:

- Choose from 18 pre-defined color palettes or create custom
- Apply design principles with visual hierarchy
- Generate HTML slides with proper dimensions
- Convert to PowerPoint with charts and tables
- Validate with thumbnail grids

### 2. Template-Based Creation

Work with existing templates:

- Extract template text and create thumbnail grids
- Analyze template inventory (slide layouts, placeholders)
- Rearrange and duplicate slides to match content
- Extract text inventory with formatting details
- Replace placeholder text while preserving design
- Validate replacements don't cause overflow

### 3. Editing Existing Presentations

OOXML manipulation for precise edits:

- Unpack presentation to XML files
- Edit slide content, notes, comments
- Validate changes immediately
- Repack to .pptx format

### 4. Analysis and Thumbnails

Visual analysis tools:

- Generate thumbnail grids (3-6 columns, configurable)
- Convert presentations to images for review
- Extract typography and color schemes
- Inventory slide structures and placeholders

## Design Principles

The PPTX skill emphasizes thoughtful design:

- **Content-informed design**: Match colors and styles to subject matter
- **18 color palettes**: From Classic Blue to Coastal Rose
- **Web-safe fonts only**: Arial, Helvetica, Times New Roman, Georgia, etc.
- **Visual hierarchy**: Clear contrast, proper sizing, clean alignment
- **Layout best practices**: Two-column for charts/tables, never vertical stacking
- **Consistency**: Repeat patterns and spacing across slides

## Testing

Run tests to verify the skill:

```bash
cd .claude/skills/pptx
pytest tests/ -v
```

Tests will skip gracefully if dependencies are not installed, showing which features are available.

## Usage Examples

See [examples/example_usage.md](examples/example_usage.md) for common workflows:

- Creating branded presentations from scratch
- Using templates for consistent design
- Editing existing presentations
- Generating presentation thumbnails
- Analyzing presentation structures
- Converting presentations to images
- Template-based workflows with inventory
- Design palette selection strategies
- Chart and data visualization
- Multi-column layout best practices

## Known Limitations

1. **Heavy dependencies**: Requires Node.js packages (pptxgenjs, playwright, sharp) and system tools (LibreOffice, poppler)
2. **Platform differences**: Some tools may require different installation on Windows
3. **Template complexity**: Complex templates with many overlapping shapes require careful inventory analysis
4. **HTML to PPTX conversion**: Requires careful dimension management and visual validation
5. **Large presentations**: Memory-intensive for presentations with many slides or large images
6. **Font limitations**: Limited to web-safe fonts for cross-platform compatibility

## Philosophy Compliance

This integration follows amplihack's core principles:

- **Ruthless simplicity**: Leverages established tools (pptxgenjs, python-pptx, OOXML)
- **Modular design**: PPTX skill is a brick with clear studs (public API)
- **Explicit dependencies**: All requirements documented, no automatic installation
- **Graceful degradation**: Tests skip cleanly if dependencies missing
- **Documentation-first**: Complete docs before code execution
- **Shared infrastructure**: Uses common OOXML scripts to avoid duplication

## OOXML Shared Infrastructure

The PPTX skill shares OOXML manipulation scripts with the DOCX skill:

- **Location**: `../common/ooxml/` (symlinked as `./ooxml/`)
- **Shared scripts**: unpack.py, pack.py, validate.py
- **PPTX-specific scripts**: thumbnail.py, rearrange.py, inventory.py, replace.py (in ./scripts/)
- **Single source of truth**: OOXML operations centralized to avoid duplication

See [../common/ooxml/README.md](../common/ooxml/README.md) for OOXML infrastructure details.

## Troubleshooting

**Skill not recognized:**

1. Verify SKILL.md exists in this directory
2. Check YAML frontmatter is valid
3. Restart Claude Code session

**ImportError for dependencies:**

1. Run verification script: `python ../common/verification/verify_skill.py pptx`
2. Install missing dependencies from DEPENDENCIES.md
3. Re-run tests to confirm

**Node packages not found:**

1. Install globally: `npm install -g pptxgenjs playwright sharp`
2. Verify: `npm list -g pptxgenjs`
3. Check PATH includes npm global bin directory

**LibreOffice conversion fails:**

1. Verify LibreOffice installed: `soffice --version`
2. Check headless mode works: `soffice --headless --convert-to pdf test.pptx`
3. Install if missing: `brew install libreoffice` (macOS) or `sudo apt-get install libreoffice` (Linux)

**Thumbnail generation fails:**

1. Check LibreOffice and poppler-utils installed
2. Verify pdftoppm available: `pdftoppm -v`
3. Install poppler: `brew install poppler` (macOS) or `sudo apt-get install poppler-utils` (Linux)

**Template workflow errors:**

1. Verify slide indices are 0-based (first slide = 0)
2. Check inventory JSON structure matches expected format
3. Validate shape names exist in inventory before replacement
4. Review error messages for specific validation failures

## Contributing

This skill is sourced from Anthropic's official skills repository. For issues:

1. **amplihack integration issues**: Open issue in amplihack repository
2. **Skill functionality issues**: Report to Anthropic skills repository
3. **Documentation improvements**: Submit PR to amplihack

## References

- [SKILL.md](SKILL.md) - Official skill documentation
- [DEPENDENCIES.md](DEPENDENCIES.md) - Complete dependency list
- [examples/example_usage.md](examples/example_usage.md) - Usage examples
- [tests/test_pptx_skill.py](tests/test_pptx_skill.py) - Verification tests
- [../common/ooxml/README.md](../common/ooxml/README.md) - OOXML infrastructure
- [Anthropic Skills Repository](https://github.com/anthropics/skills/tree/main/document-skills/pptx)

## License

The PPTX skill is provided by Anthropic under their proprietary license. See SKILL.md and Anthropic's LICENSE.txt for complete terms. The amplihack integration code (this README, DEPENDENCIES.md, tests, examples) follows amplihack's license.

---

**Integration Status**: Complete (PR #4)
**Last Updated**: 2025-11-08
**Maintained By**: amplihack project
**Completion Milestone**: ALL 4 Office skills now integrated (PDF, XLSX, DOCX, PPTX)
