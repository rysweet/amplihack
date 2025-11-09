# OOXML Common Infrastructure

## Overview

This directory contains shared OOXML (Office Open XML) manipulation scripts used by the DOCX and PPTX skills. These scripts provide core functionality for unpacking, modifying, and repacking Office documents (.docx, .pptx, .xlsx).

## Purpose

OOXML is the XML-based file format used by Microsoft Office (Word, PowerPoint, Excel). Office documents are essentially ZIP archives containing XML files and resources. These scripts enable:

- **Unpacking**: Extract ZIP archive and format XML for readability
- **Packing**: Repackage modified XML back into Office format
- **Validation**: Verify document integrity after modifications
- **Safe parsing**: Use defusedxml to prevent XML attacks

## Scripts

### unpack.py

Unpacks an Office file into a directory with formatted XML.

**Usage:**
```bash
python ooxml/scripts/unpack.py <office_file> <output_directory>
```

**What it does:**
1. Extracts ZIP archive to output directory
2. Pretty-prints all XML files for readability
3. For DOCX files: Suggests an RSID for tracked changes

**Example:**
```bash
python ooxml/scripts/unpack.py document.docx unpacked/

# Output structure:
# unpacked/
# ├── word/
# │   ├── document.xml       # Main document content
# │   ├── comments.xml        # Comments (if any)
# │   ├── styles.xml          # Document styles
# │   └── media/              # Embedded images
# ├── _rels/                  # Relationships
# └── [Content_Types].xml     # Content type mappings

# For .docx files, outputs:
# Suggested RSID for edit session: 00AB12CD
```

**Dependencies:**
- Python 3.x
- defusedxml

### pack.py

Packs a directory back into an Office file with validation.

**Usage:**
```bash
python ooxml/scripts/pack.py <input_directory> <office_file> [--force]
```

**What it does:**
1. Removes XML pretty-printing whitespace
2. Creates ZIP archive with proper structure
3. Validates document with LibreOffice (optional)
4. Ensures document is not corrupted

**Options:**
- `--force`: Skip validation (use if LibreOffice not available)

**Example:**
```bash
# Pack with validation (recommended)
python ooxml/scripts/pack.py unpacked/ output.docx

# Pack without validation (if LibreOffice not available)
python ooxml/scripts/pack.py unpacked/ output.docx --force
```

**Dependencies:**
- Python 3.x
- defusedxml
- LibreOffice (soffice) - for validation (optional with --force)

## File Structure

```
.claude/skills/common/ooxml/
├── README.md           # This file
└── scripts/
    ├── unpack.py       # Unpack Office files
    └── pack.py         # Pack Office files
```

## Usage from Skills

### DOCX Skill

The DOCX skill uses these scripts via symlink:

```bash
# In docx/ directory
ls -la ooxml  # → symlink to ../common/ooxml

# Use scripts
python ooxml/scripts/unpack.py document.docx unpacked/
# ... modify XML ...
python ooxml/scripts/pack.py unpacked/ modified.docx
```

### PPTX Skill (Future)

The PPTX skill will also use these scripts via symlink, plus additional PPTX-specific scripts:

```bash
# PPTX-specific scripts (to be added):
# - rearrange.py (slide reordering)
# - inventory.py (content inventory)
# - replace.py (content replacement)
```

## Key XML Files

### DOCX Files

- **word/document.xml**: Main document content
  - Contains paragraphs (`<w:p>`), runs (`<w:r>`), text (`<w:t>`)
  - Tracked changes: `<w:ins>` (insertions), `<w:del>` (deletions)

- **word/comments.xml**: Document comments
  - Comment references in document.xml
  - Comment text and metadata

- **word/styles.xml**: Document styles
  - Paragraph and character styles
  - Document defaults

- **word/media/**: Embedded images and media files

### PPTX Files (Future)

- **ppt/presentation.xml**: Presentation structure
- **ppt/slides/slide[N].xml**: Individual slides
- **ppt/slideLayouts/**: Slide layouts
- **ppt/media/**: Embedded images and media

### XLSX Files (Future)

- **xl/workbook.xml**: Workbook structure
- **xl/worksheets/sheet[N].xml**: Individual worksheets
- **xl/sharedStrings.xml**: Shared string table

## Common Workflows

### Workflow 1: Simple Text Replacement

```bash
# 1. Unpack
python ooxml/scripts/unpack.py document.docx unpacked/

# 2. Find and replace in XML
grep -n "old text" unpacked/word/document.xml
sed -i 's/old text/new text/g' unpacked/word/document.xml

# 3. Pack
python ooxml/scripts/pack.py unpacked/ modified.docx
```

### Workflow 2: Tracked Changes (Redlining)

```bash
# 1. Unpack and note RSID
python ooxml/scripts/unpack.py contract.docx unpacked/
# Note suggested RSID: 00AB12CD

# 2. Use Python script to implement tracked changes
python implement_changes.py unpacked/ 00AB12CD

# 3. Pack
python ooxml/scripts/pack.py unpacked/ reviewed.docx
```

### Workflow 3: Extract Metadata

```bash
# 1. Unpack
python ooxml/scripts/unpack.py document.docx unpacked/

# 2. Read core properties
cat unpacked/docProps/core.xml  # Title, author, dates

# 3. Read custom properties
cat unpacked/docProps/custom.xml  # Custom metadata
```

## Security Considerations

### defusedxml Protection

All scripts use `defusedxml` instead of standard `xml.dom.minidom` to prevent:

- **XXE (XML External Entity) attacks**: Prevents loading external entities
- **Billion Laughs attack**: Prevents exponential entity expansion
- **Quadratic blowup**: Prevents DTD validation DoS
- **DTD retrieval**: Prevents external DTD loading

### Safe Unpacking

The unpack script:
- Uses `zipfile.ZipFile` (safe for ZIP bombs with reasonable files)
- Creates output directory with proper permissions
- Does not execute any code from unpacked files

### Validation

The pack script validates documents before completion:
- Uses LibreOffice to verify document structure
- Detects corruption early (before sharing document)
- Can be skipped with --force if needed

## Troubleshooting

### ImportError: defusedxml

**Problem**: `ModuleNotFoundError: No module named 'defusedxml'`

**Solution**:
```bash
pip install defusedxml
```

### Pack validation fails

**Problem**: `Validation error: Document validation failed`

**Solution 1 - Install LibreOffice**:
```bash
brew install libreoffice  # macOS
sudo apt-get install libreoffice  # Ubuntu
```

**Solution 2 - Skip validation**:
```bash
python ooxml/scripts/pack.py unpacked/ output.docx --force
# Then manually verify document opens in Word
```

### XML not formatted

**Problem**: XML files are not pretty-printed after unpacking

**Solution**: Ensure defusedxml is installed and unpack script ran successfully:
```bash
python -c "import defusedxml; print('OK')"
python ooxml/scripts/unpack.py document.docx unpacked/
```

### Symlink not working (Windows)

**Problem**: Symlink not created or broken on Windows

**Solution 1 - Enable Developer Mode**:
- Windows 10/11: Settings → Update & Security → For Developers → Developer Mode

**Solution 2 - Copy instead of symlink**:
```bash
# Not recommended, but works
cp -r .claude/skills/common/ooxml .claude/skills/docx/
```

### Document corrupted after packing

**Problem**: Document won't open after repacking

**Causes**:
1. Invalid XML syntax (missing tags, incorrect nesting)
2. Missing required files
3. Incorrect content types

**Solution**:
```bash
# Check XML syntax
xmllint --noout unpacked/word/document.xml

# Verify required files exist
ls unpacked/word/document.xml
ls unpacked/_rels/.rels
ls unpacked/[Content_Types].xml

# Pack with validation
python ooxml/scripts/pack.py unpacked/ output.docx
```

## Performance Considerations

### Large Documents

For documents with many pages/slides:
- Unpacking: O(n) where n = file size
- XML formatting: O(m) where m = XML content size
- Packing: O(n)
- Validation: O(n) (LibreOffice conversion)

Typical times (on modern hardware):
- Small document (10 pages): < 1 second
- Medium document (100 pages): 2-5 seconds
- Large document (500 pages): 10-20 seconds

### Batch Processing

For processing multiple documents:
```bash
# Sequential processing
for file in *.docx; do
    python ooxml/scripts/unpack.py "$file" "unpacked_${file%.docx}"
    # ... modifications ...
    python ooxml/scripts/pack.py "unpacked_${file%.docx}" "modified_${file}"
done

# Parallel processing (faster)
ls *.docx | xargs -n1 -P4 -I{} python ooxml/scripts/unpack.py {} unpacked_{}
```

## Best Practices

1. **Always backup originals**: Keep original files before modification
2. **Validate after packing**: Use validation (or manually verify)
3. **Test on samples first**: Test modifications on sample documents
4. **Use version control**: Commit unpacked XML for diff tracking
5. **Minimal modifications**: Only change what's necessary
6. **Preserve structure**: Maintain XML structure and attributes

## Integration with Skills

These scripts are designed to be:
- **Skill-agnostic**: Work with DOCX, PPTX, XLSX
- **Symlink-friendly**: Skills reference via symlink
- **Single source of truth**: One implementation, multiple users
- **Independently testable**: Can be tested without skills

## Future Extensions

Planned additions for PPTX support:
- `rearrange.py`: Reorder slides in presentations
- `inventory.py`: List all content (text, images, shapes)
- `replace.py`: Batch replace text/content across slides

## References

- [Office Open XML Specification](http://www.ecma-international.org/publications/standards/Ecma-376.htm)
- [defusedxml Documentation](https://github.com/tiran/defusedxml)
- [Python zipfile Documentation](https://docs.python.org/3/library/zipfile.html)

## License

These scripts are sourced from Anthropic's official skills repository. See Anthropic's LICENSE.txt for terms. Integration code follows amplihack's license.

---

**Last Updated**: 2025-11-08
**Maintained By**: amplihack project
