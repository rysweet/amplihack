# DOCX Skill Usage Examples

## Overview

This document provides practical examples of using the DOCX skill in Claude Code conversations. These examples demonstrate common workflows including document creation, tracked changes (redlining), text extraction, and OOXML manipulation.

## Example 1: Create a Business Proposal Document

### Scenario

Create a professional business proposal with title page, executive summary, sections, and a pricing table.

### Conversation

**User**: Create a business proposal document for a software development project with title page, executive summary, scope, timeline, and pricing table

**Claude**: I'll create a structured business proposal using docx-js.

```javascript
import {
  Document,
  Paragraph,
  TextRun,
  Table,
  TableCell,
  TableRow,
  Packer,
  AlignmentType,
  BorderStyle,
} from "docx";
import * as fs from "fs";

const doc = new Document({
  sections: [
    {
      properties: {},
      children: [
        // Title Page
        new Paragraph({
          children: [
            new TextRun({
              text: "SOFTWARE DEVELOPMENT PROPOSAL",
              bold: true,
              size: 32,
            }),
          ],
          alignment: AlignmentType.CENTER,
          spacing: { after: 400 },
        }),
        new Paragraph({
          children: [new TextRun({ text: "Client: Acme Corporation", size: 24 })],
          alignment: AlignmentType.CENTER,
          spacing: { after: 200 },
        }),
        new Paragraph({
          children: [new TextRun({ text: "Date: November 8, 2025", size: 20 })],
          alignment: AlignmentType.CENTER,
          spacing: { after: 800 },
        }),

        // Executive Summary
        new Paragraph({
          children: [new TextRun({ text: "Executive Summary", bold: true, size: 28 })],
          spacing: { before: 400, after: 200 },
        }),
        new Paragraph({
          children: [
            new TextRun({
              text: "This proposal outlines a comprehensive software development project to build a modern web application. The project will deliver a scalable, secure platform within 12 weeks.",
            }),
          ],
          spacing: { after: 200 },
        }),

        // Project Scope
        new Paragraph({
          children: [new TextRun({ text: "Project Scope", bold: true, size: 28 })],
          spacing: { before: 400, after: 200 },
        }),
        new Paragraph({
          children: [new TextRun({ text: "1. User Authentication System", bold: true })],
          spacing: { after: 100 },
        }),
        new Paragraph({
          children: [new TextRun({ text: "   - OAuth 2.0 integration" })],
          spacing: { after: 100 },
        }),
        new Paragraph({
          children: [new TextRun({ text: "   - Role-based access control" })],
          spacing: { after: 100 },
        }),
        new Paragraph({
          children: [new TextRun({ text: "2. Database Architecture", bold: true })],
          spacing: { after: 100 },
        }),
        new Paragraph({
          children: [new TextRun({ text: "   - PostgreSQL backend" })],
          spacing: { after: 100 },
        }),
        new Paragraph({
          children: [new TextRun({ text: "   - Optimized queries and indexing" })],
          spacing: { after: 200 },
        }),

        // Timeline
        new Paragraph({
          children: [new TextRun({ text: "Project Timeline", bold: true, size: 28 })],
          spacing: { before: 400, after: 200 },
        }),
        new Paragraph({
          children: [new TextRun({ text: "Total Duration: 12 weeks" })],
          spacing: { after: 200 },
        }),

        // Pricing Table
        new Paragraph({
          children: [new TextRun({ text: "Pricing Breakdown", bold: true, size: 28 })],
          spacing: { before: 400, after: 200 },
        }),
        new Table({
          rows: [
            new TableRow({
              children: [
                new TableCell({
                  children: [
                    new Paragraph({ children: [new TextRun({ text: "Phase", bold: true })] }),
                  ],
                }),
                new TableCell({
                  children: [
                    new Paragraph({ children: [new TextRun({ text: "Duration", bold: true })] }),
                  ],
                }),
                new TableCell({
                  children: [
                    new Paragraph({ children: [new TextRun({ text: "Cost", bold: true })] }),
                  ],
                }),
              ],
            }),
            new TableRow({
              children: [
                new TableCell({ children: [new Paragraph("Discovery & Planning")] }),
                new TableCell({ children: [new Paragraph("2 weeks")] }),
                new TableCell({ children: [new Paragraph("$15,000")] }),
              ],
            }),
            new TableRow({
              children: [
                new TableCell({ children: [new Paragraph("Development")] }),
                new TableCell({ children: [new Paragraph("8 weeks")] }),
                new TableCell({ children: [new Paragraph("$60,000")] }),
              ],
            }),
            new TableRow({
              children: [
                new TableCell({ children: [new Paragraph("Testing & Deployment")] }),
                new TableCell({ children: [new Paragraph("2 weeks")] }),
                new TableCell({ children: [new Paragraph("$15,000")] }),
              ],
            }),
            new TableRow({
              children: [
                new TableCell({
                  children: [
                    new Paragraph({ children: [new TextRun({ text: "Total", bold: true })] }),
                  ],
                }),
                new TableCell({
                  children: [
                    new Paragraph({ children: [new TextRun({ text: "12 weeks", bold: true })] }),
                  ],
                }),
                new TableCell({
                  children: [
                    new Paragraph({ children: [new TextRun({ text: "$90,000", bold: true })] }),
                  ],
                }),
              ],
            }),
          ],
        }),
      ],
    },
  ],
});

const buffer = await Packer.toBuffer(doc);
fs.writeFileSync("business_proposal.docx", buffer);
console.log("Created business_proposal.docx");
```

### Expected Output

- Professional `business_proposal.docx` file
- Formatted title page with proper alignment
- Structured sections with headings
- Pricing table with borders and formatting
- Ready for review and customization

---

## Example 2: Extract Text with Tracked Changes

### Scenario

Review a contract that has tracked changes and extract all text including insertions and deletions.

### Conversation

**User**: Extract text from contract.docx showing all tracked changes

**Claude**: I'll use pandoc to convert the document with all tracked changes preserved.

```bash
# Extract with all tracked changes visible
pandoc --track-changes=all contract.docx -o contract_with_changes.md

# View the markdown
cat contract_with_changes.md
```

Alternative formats:

```bash
# Accept all changes
pandoc --track-changes=accept contract.docx -o contract_clean.md

# Reject all changes
pandoc --track-changes=reject contract.docx -o contract_original.md

# Extract to plain text
pandoc contract.docx -o contract.txt
```

### Expected Output

- Markdown file with tracked changes formatted as strikethrough and underline
- Insertions shown as additions
- Deletions shown as strikethrough
- Structure preserved (headings, lists, tables)

---

## Example 3: Implement Contract Redlines (Tracked Changes)

### Scenario

Legal document needs systematic review with tracked changes. Change "30 days" to "60 days" throughout, update party names, and modify payment terms.

### Conversation

**User**: Review contract.docx and implement these changes with tracking: 1) Change all "30 days" to "60 days", 2) Update "Vendor Corp" to "Supplier LLC", 3) Change payment terms from net-30 to net-60

**Claude**: I'll implement these changes using the redlining workflow with batching.

**Step 1: Convert to markdown and analyze**

```bash
pandoc --track-changes=all contract.docx -o current.md
cat current.md
```

**Step 2: Identify changes and create batches**

Batch 1: Timeline changes (30 → 60 days)

- Section 2.1: "delivered within 30 days"
- Section 5.3: "terminate with 30 days notice"
- Section 7.2: "respond within 30 days"

Batch 2: Party name updates

- Preamble: "Vendor Corp"
- Throughout document: "Vendor Corp" → "Supplier LLC"

Batch 3: Payment terms

- Section 4.1: "net-30" → "net-60"
- Section 4.2: "30 days from invoice" → "60 days from invoice"

**Step 3: Unpack document**

```bash
python ooxml/scripts/unpack.py contract.docx unpacked/
# Note the suggested RSID: 00AB12CD
```

**Step 4: Implement Batch 1 (Timeline changes)**

```bash
# Find occurrences in XML
grep -n "30 days" unpacked/word/document.xml
```

```python
# batch1_timeline.py
from defusedxml import minidom

doc = minidom.parse("unpacked/word/document.xml")
RSID = "00AB12CD"  # From unpack script

# Find and replace "30 days" with tracked changes
# Using minimal edits principle - only mark changed text
for text_node in doc.getElementsByTagName("w:t"):
    if text_node.firstChild and "30 days" in text_node.firstChild.nodeValue:
        parent = text_node.parentNode  # <w:r>
        paragraph = parent.parentNode  # <w:p>

        # Split: "delivered within 30 days" → "delivered within " + DEL"30" + INS"60" + " days"
        original_text = text_node.firstChild.nodeValue
        before = original_text.split("30 days")[0]
        after = original_text.split("30 days")[1]

        # Create replacement runs with minimal edits
        # Unchanged text before
        if before:
            unchanged_before = doc.createElement("w:r")
            unchanged_before.setAttribute("w:rsidR", parent.getAttribute("w:rsidR"))
            t_before = doc.createElement("w:t")
            t_before.appendChild(doc.createTextNode(before))
            unchanged_before.appendChild(t_before)

        # Deletion: "30"
        del_run = doc.createElement("w:del")
        del_run.setAttribute("w:id", "1")
        del_run.setAttribute("w:author", "Claude")
        del_r = doc.createElement("w:r")
        del_t = doc.createElement("w:delText")
        del_t.appendChild(doc.createTextNode("30"))
        del_r.appendChild(del_t)
        del_run.appendChild(del_r)

        # Insertion: "60"
        ins_run = doc.createElement("w:ins")
        ins_run.setAttribute("w:id", "2")
        ins_run.setAttribute("w:author", "Claude")
        ins_r = doc.createElement("w:r")
        ins_r.setAttribute("w:rsidR", RSID)
        ins_t = doc.createElement("w:t")
        ins_t.appendChild(doc.createTextNode("60"))
        ins_r.appendChild(ins_t)
        ins_run.appendChild(ins_r)

        # Unchanged text after
        if after or " days":
            unchanged_after = doc.createElement("w:r")
            unchanged_after.setAttribute("w:rsidR", parent.getAttribute("w:rsidR"))
            t_after = doc.createElement("w:t")
            t_after.appendChild(doc.createTextNode(" days" + after))
            unchanged_after.appendChild(t_after)

        # Replace in paragraph
        paragraph.removeChild(parent)
        if before:
            paragraph.insertBefore(unchanged_before, None)
        paragraph.insertBefore(del_run, None)
        paragraph.insertBefore(ins_run, None)
        paragraph.insertBefore(unchanged_after, None)

with open("unpacked/word/document.xml", "wb") as f:
    f.write(doc.toxml(encoding="UTF-8"))

print("Batch 1 complete: Timeline changes")
```

**Step 5: Verify Batch 1**

```bash
python ooxml/scripts/pack.py unpacked/ contract_batch1.docx
pandoc --track-changes=all contract_batch1.docx -o verify1.md
grep "60 days" verify1.md  # Should find changes
```

**Step 6: Implement remaining batches**

(Similar process for Batch 2 and Batch 3...)

**Step 7: Final pack and verification**

```bash
python ooxml/scripts/pack.py unpacked/ contract_reviewed.docx
pandoc --track-changes=all contract_reviewed.docx -o final_verification.md

# Verify all changes
grep "60 days" final_verification.md
grep "Supplier LLC" final_verification.md
grep "net-60" final_verification.md
```

### Expected Output

- `contract_reviewed.docx` with systematic tracked changes
- All changes batched logically for easier debugging
- Minimal edits (only changed text marked)
- Original formatting preserved for unchanged text
- Ready for legal review

---

## Example 4: Extract Document Comments

### Scenario

A reviewed document has comments that need to be extracted and analyzed.

### Conversation

**User**: Extract all comments from reviewed_document.docx

**Claude**: I'll unpack the document and read the comments XML.

```bash
# Unpack document
python ooxml/scripts/unpack.py reviewed_document.docx unpacked/

# Read comments
cat unpacked/word/comments.xml
```

Python script for structured extraction:

```python
from defusedxml import minidom

doc = minidom.parse("unpacked/word/comments.xml")

comments = []
for comment in doc.getElementsByTagName("w:comment"):
    comment_id = comment.getAttribute("w:id")
    author = comment.getAttribute("w:author")
    date = comment.getAttribute("w:date")

    # Extract comment text
    text_parts = []
    for t in comment.getElementsByTagName("w:t"):
        if t.firstChild:
            text_parts.append(t.firstChild.nodeValue)
    text = "".join(text_parts)

    comments.append({
        "id": comment_id,
        "author": author,
        "date": date,
        "text": text
    })

# Print structured comments
for c in comments:
    print(f"Comment {c['id']} by {c['author']} on {c['date']}:")
    print(f"  {c['text']}")
    print()
```

### Expected Output

- List of all comments with metadata
- Comment ID, author, date, and text content
- Structured format for analysis

---

## Example 5: Convert Document to Images for Visual Review

### Scenario

Need to visually review a document as images for presentation or markup.

### Conversation

**User**: Convert contract.docx to JPEG images for each page

**Claude**: I'll use a two-step process: DOCX → PDF → images.

```bash
# Step 1: Convert DOCX to PDF
soffice --headless --convert-to pdf contract.docx

# Step 2: Convert PDF to JPEG images (150 DPI)
pdftoppm -jpeg -r 150 contract.pdf page

# List generated images
ls -lh page-*.jpg
```

For specific pages or higher quality:

```bash
# High quality (300 DPI)
pdftoppm -jpeg -r 300 contract.pdf page

# Specific page range (pages 2-5)
pdftoppm -jpeg -r 150 -f 2 -l 5 contract.pdf page

# PNG format instead of JPEG
pdftoppm -png -r 150 contract.pdf page
```

### Expected Output

- `page-1.jpg`, `page-2.jpg`, etc. for each document page
- JPEG images suitable for visual review and annotation
- Adjustable quality based on DPI setting

---

## Example 6: Batch Process Multiple Documents

### Scenario

Extract text from all Word documents in a directory for analysis.

### Conversation

**User**: Extract text from all .docx files in the contracts/ directory

**Claude**: I'll batch process all documents with pandoc.

```bash
# Create output directory
mkdir -p extracted_text

# Process all DOCX files
for file in contracts/*.docx; do
    filename=$(basename "$file" .docx)
    echo "Processing $filename..."
    pandoc "$file" -o "extracted_text/${filename}.txt"
done

# Create index
ls -1 extracted_text/*.txt > extracted_text/index.txt

echo "Extracted $(ls -1 extracted_text/*.txt | wc -l) documents"
```

With tracked changes:

```bash
for file in contracts/*.docx; do
    filename=$(basename "$file" .docx)
    pandoc --track-changes=all "$file" -o "extracted_text/${filename}_with_changes.md"
done
```

### Expected Output

- Text files for each Word document
- Organized in `extracted_text/` directory
- Index file listing all extracted documents
- Progress output for each file

---

## Example 7: Add Header and Footer to Document

### Scenario

Need to add page numbers and company logo to document headers/footers.

### Conversation

**User**: Add page numbers to the footer and company name to the header of report.docx

**Claude**: I'll create a document with headers and footers using docx-js.

```javascript
import {
  Document,
  Paragraph,
  TextRun,
  Header,
  Footer,
  PageNumber,
  AlignmentType,
  Packer,
} from "docx";
import * as fs from "fs";

const doc = new Document({
  sections: [
    {
      headers: {
        default: new Header({
          children: [
            new Paragraph({
              children: [
                new TextRun({
                  text: "Acme Corporation - Confidential",
                  bold: true,
                }),
              ],
              alignment: AlignmentType.CENTER,
            }),
          ],
        }),
      },
      footers: {
        default: new Footer({
          children: [
            new Paragraph({
              children: [
                new TextRun({ text: "Page " }),
                PageNumber.CURRENT,
                new TextRun({ text: " of " }),
                PageNumber.TOTAL_PAGES,
              ],
              alignment: AlignmentType.CENTER,
            }),
          ],
        }),
      },
      children: [
        new Paragraph({
          children: [new TextRun({ text: "Document content here...", size: 24 })],
        }),
      ],
    },
  ],
});

const buffer = await Packer.toBuffer(doc);
fs.writeFileSync("report_with_header_footer.docx", buffer);
```

### Expected Output

- Document with header showing company name
- Footer with page numbers (Page X of Y)
- Headers/footers appear on all pages

---

## Example 8: Extract and Analyze Document Structure

### Scenario

Need to understand document structure (sections, headings, lists) for reorganization.

### Conversation

**User**: Analyze the structure of proposal.docx and show me all headings

**Claude**: I'll convert to markdown which preserves document structure.

```bash
# Convert to markdown (preserves headings, lists, tables)
pandoc proposal.docx -o proposal_structure.md

# Extract just headings
grep "^#" proposal_structure.md

# Or more detailed with levels
echo "Document Structure:"
grep "^#" proposal_structure.md | while read -r line; do
    level=$(echo "$line" | grep -o "^#*" | wc -c)
    heading=$(echo "$line" | sed 's/^#* //')
    indent=$(printf "%$((($level-1)*2))s")
    echo "${indent}Level $level: $heading"
done
```

Python script for detailed analysis:

```python
# Extract structure from markdown
with open("proposal_structure.md") as f:
    content = f.read()

headings = []
for line in content.split("\n"):
    if line.startswith("#"):
        level = line.count("#", 0, line.index(" "))
        text = line.lstrip("#").strip()
        headings.append({"level": level, "text": text})

# Print outline
for h in headings:
    indent = "  " * (h["level"] - 1)
    print(f"{indent}{h['level']}. {h['text']}")
```

### Expected Output

- Document outline with heading levels
- Hierarchical structure visualization
- Easy to identify sections for reorganization

---

## Example 9: Merge Multiple Documents

### Scenario

Combine several Word documents into a single consolidated document.

### Conversation

**User**: Merge section1.docx, section2.docx, and section3.docx into a single document

**Claude**: I'll use pandoc to merge the documents.

```bash
# Simple merge
pandoc section1.docx section2.docx section3.docx -o merged_document.docx

# Add page breaks between sections
pandoc section1.docx section2.docx section3.docx --reference-doc=template.docx -o merged_with_breaks.docx

# Convert all to markdown first for review
pandoc section1.docx -o section1.md
pandoc section2.docx -o section2.md
pandoc section3.docx -o section3.md

# Manually combine markdown and convert back
cat section1.md section2.md section3.md > combined.md
pandoc combined.md -o combined.docx
```

### Expected Output

- Single `merged_document.docx` file
- All content from source documents preserved
- Optional page breaks between sections
- Original formatting maintained

---

## Example 10: Create Document from Template with Data

### Scenario

Generate multiple contract documents from a template by replacing placeholder variables.

### Conversation

**User**: Create 3 contracts from template.docx by replacing {CLIENT_NAME}, {DATE}, and {AMOUNT} with data from data.json

**Claude**: I'll unpack the template, replace variables, and generate documents.

```json
// data.json
[
  { "client": "Acme Corp", "date": "2025-11-08", "amount": "$50,000" },
  { "client": "Beta Inc", "date": "2025-11-10", "amount": "$75,000" },
  { "client": "Gamma LLC", "date": "2025-11-12", "amount": "$100,000" }
]
```

```python
import json
import shutil
from pathlib import Path
from defusedxml import minidom

# Load data
with open("data.json") as f:
    clients = json.load(f)

# Process each client
for i, client in enumerate(clients, 1):
    # Copy template
    work_dir = Path(f"contract_{i}")
    shutil.copytree("template_unpacked", work_dir)

    # Load document XML
    doc_path = work_dir / "word" / "document.xml"
    doc = minidom.parse(str(doc_path))

    # Replace placeholders
    replacements = {
        "{CLIENT_NAME}": client["client"],
        "{DATE}": client["date"],
        "{AMOUNT}": client["amount"]
    }

    for text_node in doc.getElementsByTagName("w:t"):
        if text_node.firstChild:
            text = text_node.firstChild.nodeValue
            for placeholder, value in replacements.items():
                text = text.replace(placeholder, value)
            text_node.firstChild.nodeValue = text

    # Save modified XML
    with open(doc_path, "wb") as f:
        f.write(doc.toxml(encoding="UTF-8"))

    # Pack document
    output_file = f"contract_{client['client'].replace(' ', '_')}.docx"
    import subprocess
    subprocess.run([
        "python", "ooxml/scripts/pack.py",
        str(work_dir), output_file
    ])

    print(f"Generated {output_file}")
```

### Expected Output

- Three contract documents:
  - `contract_Acme_Corp.docx`
  - `contract_Beta_Inc.docx`
  - `contract_Gamma_LLC.docx`
- Each with personalized client data
- Identical structure from template

---

## Common Patterns

### Error Handling for OOXML Operations

```python
from defusedxml import minidom
from pathlib import Path

def safe_unpack_and_modify(docx_file, output_dir):
    try:
        # Unpack
        import subprocess
        result = subprocess.run(
            ["python", "ooxml/scripts/unpack.py", docx_file, output_dir],
            capture_output=True,
            text=True,
            check=True
        )

        # Modify
        doc_xml = Path(output_dir) / "word" / "document.xml"
        if not doc_xml.exists():
            raise FileNotFoundError(f"Document XML not found: {doc_xml}")

        doc = minidom.parse(str(doc_xml))
        # ... modifications ...

        return True
    except subprocess.CalledProcessError as e:
        print(f"Unpack failed: {e.stderr}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False
```

### Verify Changes Before Packing

```bash
# Always verify changes before final pack
grep -n "expected_text" unpacked/word/document.xml

# Pack with validation
python ooxml/scripts/pack.py unpacked/ output.docx

# If validation fails, use --force and manually check
python ooxml/scripts/pack.py unpacked/ output.docx --force

# Then verify document opens correctly
soffice output.docx  # Manual verification
```

### Batch Processing with Progress

```python
from pathlib import Path
from tqdm import tqdm  # pip install tqdm

docx_files = list(Path("documents").glob("*.docx"))
results = []

for docx_file in tqdm(docx_files, desc="Processing documents"):
    try:
        # Process document
        output = process_document(docx_file)
        results.append({"file": docx_file.name, "status": "success"})
    except Exception as e:
        results.append({"file": docx_file.name, "status": "failed", "error": str(e)})

# Summary
success_count = sum(1 for r in results if r["status"] == "success")
print(f"\nProcessed {len(results)} documents: {success_count} successful")
```

---

## Tips and Best Practices

1. **Choose the right tool**:
   - pandoc: Text extraction, quick conversions
   - docx-js: Creating new documents from scratch
   - OOXML editing: Precise tracked changes, complex operations

2. **Tracked changes workflow**:
   - Always batch changes (3-10 per batch)
   - Use minimal edits principle (only mark changed text)
   - Test each batch before proceeding
   - Keep original RSID for unchanged text

3. **Error prevention**:
   - Validate after packing (or use --force and manually verify)
   - Always grep before writing scripts (line numbers change)
   - Keep backup of original document
   - Test on sample document first

4. **Performance**:
   - Use pandoc for bulk text extraction
   - Cache unpacked directories for multiple edits
   - Batch process similar documents together

5. **Quality assurance**:
   - Convert to markdown for verification
   - Check document opens correctly in Word
   - Verify tracked changes appear as expected
   - Review comments and structure

---

## Next Steps

- Review [SKILL.md](../SKILL.md) for complete workflow reference
- Check [DEPENDENCIES.md](../DEPENDENCIES.md) for installation requirements
- See [README.md](../README.md) for integration details
- Run tests: `pytest tests/ -v`

---

**Last Updated**: 2025-11-08
**Maintained By**: amplihack project
