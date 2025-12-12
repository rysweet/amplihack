# PDF Skill Usage Examples

## Overview

This document provides practical examples of using the PDF skill in Claude Code conversations. These examples demonstrate common workflows and expected outcomes.

## Example 1: Extract Text from a Research Paper

### Scenario

You have a research paper PDF and need to extract all text for analysis.

### Conversation

**User**: Extract all text from research_paper.pdf and save it to a text file

**Claude**: I'll extract the text from the PDF using pdfplumber for better layout preservation.

```python
import pdfplumber

with pdfplumber.open("research_paper.pdf") as pdf:
    text = ""
    for page in pdf.pages:
        text += page.extract_text()
        text += "\n\n--- Page Break ---\n\n"

with open("research_paper_text.txt", "w", encoding="utf-8") as f:
    f.write(text)

print(f"Extracted text from {len(pdf.pages)} pages")
```

### Expected Output

- `research_paper_text.txt` file created with all extracted text
- Text preserves paragraph structure and layout
- Page breaks clearly marked

---

## Example 2: Convert Tables to Excel

### Scenario

You have a financial report PDF with multiple tables that need to be extracted and analyzed in Excel.

### Conversation

**User**: Extract all tables from financial_report.pdf and save them to Excel

**Claude**: I'll use pdfplumber to extract tables and pandas to create a structured Excel file.

```python
import pdfplumber
import pandas as pd

all_tables = []

with pdfplumber.open("financial_report.pdf") as pdf:
    for page_num, page in enumerate(pdf.pages, 1):
        tables = page.extract_tables()
        for table_num, table in enumerate(tables, 1):
            if table and len(table) > 1:
                # First row as headers
                df = pd.DataFrame(table[1:], columns=table[0])
                df['source_page'] = page_num
                df['table_number'] = table_num
                all_tables.append(df)

if all_tables:
    # Save each table to separate sheet
    with pd.ExcelWriter("financial_tables.xlsx", engine='openpyxl') as writer:
        for i, df in enumerate(all_tables, 1):
            sheet_name = f"Table_{i}_Page_{df['source_page'].iloc[0]}"
            df.drop(['source_page', 'table_number'], axis=1).to_excel(
                writer, sheet_name=sheet_name, index=False
            )

    print(f"Extracted {len(all_tables)} tables to financial_tables.xlsx")
else:
    print("No tables found in PDF")
```

### Expected Output

- `financial_tables.xlsx` file with multiple sheets
- Each sheet contains one extracted table
- Sheet names indicate source page
- Headers preserved from PDF

---

## Example 3: Create a Report PDF

### Scenario

Generate a multi-page report PDF with title, sections, and formatted text.

### Conversation

**User**: Create a sales report PDF with title "Q4 2024 Sales Report", three sections, and a summary table

**Claude**: I'll use reportlab to create a structured PDF with proper formatting.

```python
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors

doc = SimpleDocTemplate("Q4_2024_Sales_Report.pdf", pagesize=letter)
styles = getSampleStyleSheet()
story = []

# Title
title = Paragraph("Q4 2024 Sales Report", styles['Title'])
story.append(title)
story.append(Spacer(1, 0.5*inch))

# Executive Summary
story.append(Paragraph("Executive Summary", styles['Heading1']))
story.append(Paragraph(
    "Total sales increased 15% compared to Q3 2024, driven by strong performance "
    "in the enterprise segment. Key highlights include...",
    styles['Normal']
))
story.append(Spacer(1, 0.3*inch))

# Section 1: Revenue Breakdown
story.append(Paragraph("Revenue Breakdown", styles['Heading1']))
story.append(Paragraph(
    "Revenue distribution across segments showed significant growth...",
    styles['Normal']
))
story.append(Spacer(1, 0.2*inch))

# Summary Table
data = [
    ['Segment', 'Q3 2024', 'Q4 2024', 'Growth'],
    ['Enterprise', '$2.5M', '$3.1M', '24%'],
    ['SMB', '$1.8M', '$2.0M', '11%'],
    ['Consumer', '$0.9M', '$1.0M', '11%'],
    ['Total', '$5.2M', '$6.1M', '17%']
]

table = Table(data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1*inch])
table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 12),
    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
    ('GRID', (0, 0), (-1, -1), 1, colors.black)
]))
story.append(table)
story.append(PageBreak())

# Section 2: Regional Performance
story.append(Paragraph("Regional Performance", styles['Heading1']))
story.append(Paragraph(
    "North America led growth with 20% increase, followed by Europe at 15%...",
    styles['Normal']
))
story.append(Spacer(1, 0.3*inch))

# Section 3: Future Outlook
story.append(Paragraph("Future Outlook", styles['Heading1']))
story.append(Paragraph(
    "Looking ahead to Q1 2025, we anticipate continued momentum with...",
    styles['Normal']
))

# Build PDF
doc.build(story)
print("Created Q4_2024_Sales_Report.pdf")
```

### Expected Output

- Professional multi-page PDF report
- Formatted title, sections, and body text
- Table with styling and borders
- Page breaks between major sections

---

## Example 4: Merge Multiple Invoices

### Scenario

Combine multiple invoice PDFs into a single document for archiving.

### Conversation

**User**: Merge all PDF files in the invoices/ directory into a single archive file

**Claude**: I'll use pypdf to merge all PDFs while preserving their content.

```python
from pypdf import PdfWriter, PdfReader
from pathlib import Path

writer = PdfWriter()
invoices_dir = Path("invoices")
pdf_files = sorted(invoices_dir.glob("*.pdf"))

if not pdf_files:
    print("No PDF files found in invoices/ directory")
else:
    for pdf_file in pdf_files:
        print(f"Adding {pdf_file.name}...")
        reader = PdfReader(pdf_file)
        for page in reader.pages:
            writer.add_page(page)

    # Add metadata
    writer.add_metadata({
        '/Title': 'Invoice Archive',
        '/Author': 'Automated System',
        '/Subject': f'Combined invoices from {len(pdf_files)} files'
    })

    output_file = "invoices_archive_2024.pdf"
    with open(output_file, "wb") as output:
        writer.write(output)

    print(f"\nMerged {len(pdf_files)} invoices into {output_file}")
    print(f"Total pages: {len(writer.pages)}")
```

### Expected Output

- Single `invoices_archive_2024.pdf` file
- All invoices combined in order
- Metadata indicating source count
- Console output showing merge progress

---

## Example 5: Extract Images from Catalog

### Scenario

Extract all product images from a catalog PDF for use in a website.

### Conversation

**User**: Extract all images from product_catalog.pdf and save them as separate files

**Claude**: I'll use poppler-utils' pdfimages command to extract all images.

```bash
# Create output directory
mkdir -p extracted_images

# Extract images (JPEG format)
pdfimages -j product_catalog.pdf extracted_images/product

# List extracted images
ls -lh extracted_images/

echo "Images extracted to extracted_images/"
```

Alternative Python approach:

```python
# If pdfimages is not available, use pdf2image
from pdf2image import convert_from_path
from pathlib import Path

output_dir = Path("extracted_images")
output_dir.mkdir(exist_ok=True)

# Convert each page to image
images = convert_from_path("product_catalog.pdf", dpi=300)

for i, image in enumerate(images, 1):
    image.save(output_dir / f"page_{i}.jpg", "JPEG")

print(f"Extracted {len(images)} page images to {output_dir}/")
```

### Expected Output

- `extracted_images/` directory created
- Individual image files (product-000.jpg, product-001.jpg, etc.)
- High-quality JPEG images suitable for web use

---

## Example 6: OCR Scanned Document

### Scenario

A scanned invoice PDF needs text extraction for accounting software.

### Conversation

**User**: Extract text from scanned_invoice.pdf using OCR

**Claude**: I'll use pytesseract to perform OCR on the scanned document.

```python
import pytesseract
from pdf2image import convert_from_path

# Convert PDF to images
print("Converting PDF to images...")
images = convert_from_path('scanned_invoice.pdf', dpi=300)

# OCR each page
full_text = ""
for i, image in enumerate(images, 1):
    print(f"Processing page {i}...")
    text = pytesseract.image_to_string(image)
    full_text += f"--- Page {i} ---\n\n"
    full_text += text
    full_text += "\n\n"

# Save extracted text
with open("scanned_invoice_text.txt", "w", encoding="utf-8") as f:
    f.write(full_text)

print(f"OCR complete. Extracted text from {len(images)} pages")
print("Saved to scanned_invoice_text.txt")
```

### Expected Output

- `scanned_invoice_text.txt` with recognized text
- Processing messages for each page
- Text accuracy depends on scan quality

---

## Example 7: Split PDF by Pages

### Scenario

Break a large document into individual page files for review.

### Conversation

**User**: Split large_document.pdf into individual page files

**Claude**: I'll extract each page as a separate PDF file.

```python
from pypdf import PdfReader, PdfWriter
from pathlib import Path

reader = PdfReader("large_document.pdf")
output_dir = Path("split_pages")
output_dir.mkdir(exist_ok=True)

for i, page in enumerate(reader.pages, 1):
    writer = PdfWriter()
    writer.add_page(page)

    output_file = output_dir / f"page_{i:03d}.pdf"
    with open(output_file, "wb") as output:
        writer.write(output)

print(f"Split {len(reader.pages)} pages into {output_dir}/")
```

### Expected Output

- `split_pages/` directory with individual PDFs
- Files named page_001.pdf, page_002.pdf, etc.
- Each file contains exactly one page

---

## Example 8: Add Password Protection

### Scenario

Protect a confidential document with a password before sharing.

### Conversation

**User**: Add password protection to confidential_report.pdf

**Claude**: I'll encrypt the PDF with a password.

```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("confidential_report.pdf")
writer = PdfWriter()

# Copy all pages
for page in reader.pages:
    writer.add_page(page)

# Add password protection
user_password = "view123"  # Password to open the PDF
owner_password = "admin456"  # Password for full permissions

writer.encrypt(
    user_password=user_password,
    owner_password=owner_password,
    permissions_flag=0b0100  # Allow printing only
)

# Save encrypted PDF
with open("confidential_report_protected.pdf", "wb") as output:
    writer.write(output)

print("PDF encrypted successfully")
print(f"User password: {user_password}")
print(f"Owner password: {owner_password}")
print("Permissions: Print only")
```

### Expected Output

- `confidential_report_protected.pdf` created
- Password required to open
- Limited permissions (print only)
- Original file unchanged

---

## Example 9: Rotate Pages

### Scenario

Some pages in a scanned document are oriented incorrectly.

### Conversation

**User**: Rotate pages 2 and 3 in document.pdf by 90 degrees clockwise

**Claude**: I'll rotate the specified pages and save the result.

```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("document.pdf")
writer = PdfWriter()

for i, page in enumerate(reader.pages):
    # Rotate pages 2 and 3 (indices 1 and 2)
    if i in [1, 2]:
        page.rotate(90)
    writer.add_page(page)

with open("document_rotated.pdf", "wb") as output:
    writer.write(output)

print(f"Rotated pages 2 and 3")
print(f"Total pages: {len(writer.pages)}")
```

### Expected Output

- `document_rotated.pdf` with corrected orientation
- Pages 2 and 3 rotated 90 degrees clockwise
- Other pages unchanged

---

## Example 10: Extract Metadata

### Scenario

Review PDF properties and metadata for document management.

### Conversation

**User**: Show me all metadata from annual_report.pdf

**Claude**: I'll extract and display all available PDF metadata.

```python
from pypdf import PdfReader
from datetime import datetime

reader = PdfReader("annual_report.pdf")
meta = reader.metadata

print("PDF Metadata:")
print("=" * 50)
print(f"Title: {meta.title or 'Not set'}")
print(f"Author: {meta.author or 'Not set'}")
print(f"Subject: {meta.subject or 'Not set'}")
print(f"Creator: {meta.creator or 'Not set'}")
print(f"Producer: {meta.producer or 'Not set'}")

if meta.creation_date:
    print(f"Created: {meta.creation_date}")
if meta.modification_date:
    print(f"Modified: {meta.modification_date}")

print(f"\nDocument Info:")
print(f"Pages: {len(reader.pages)}")
print(f"Encrypted: {reader.is_encrypted}")

# Get first page dimensions
page = reader.pages[0]
width = page.mediabox.width
height = page.mediabox.height
print(f"Page size: {width} x {height} points")
```

### Expected Output

```
PDF Metadata:
==================================================
Title: Annual Report 2024
Author: John Doe
Subject: Financial Annual Report
Creator: Microsoft Word
Producer: Adobe PDF Library
Created: 2024-01-15 14:30:00
Modified: 2024-01-20 09:15:00

Document Info:
Pages: 45
Encrypted: False
Page size: 612.0 x 792.0 points
```

---

## Common Patterns

### Error Handling

```python
from pypdf import PdfReader
from pypdf.errors import PdfReadError

try:
    reader = PdfReader("document.pdf")
    # Process PDF
except FileNotFoundError:
    print("Error: PDF file not found")
except PdfReadError:
    print("Error: Could not read PDF (may be corrupted)")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Progress Tracking

```python
from pypdf import PdfReader

reader = PdfReader("large_document.pdf")
total_pages = len(reader.pages)

for i, page in enumerate(reader.pages, 1):
    # Process page
    text = page.extract_text()

    # Show progress
    progress = (i / total_pages) * 100
    print(f"Progress: {progress:.1f}% ({i}/{total_pages})", end='\r')

print("\nComplete!")
```

### Batch Processing

```python
from pypdf import PdfReader
from pathlib import Path

pdf_files = Path("documents").glob("*.pdf")
results = []

for pdf_file in pdf_files:
    try:
        reader = PdfReader(pdf_file)
        results.append({
            'file': pdf_file.name,
            'pages': len(reader.pages),
            'status': 'success'
        })
    except Exception as e:
        results.append({
            'file': pdf_file.name,
            'pages': 0,
            'status': f'error: {str(e)}'
        })

# Summary
print(f"\nProcessed {len(results)} files")
for result in results:
    print(f"  {result['file']}: {result['pages']} pages - {result['status']}")
```

---

## Tips and Best Practices

1. **Choose the right tool**:
   - pypdf: Basic operations (merge, split, rotate)
   - pdfplumber: Text and table extraction
   - reportlab: PDF creation
   - OCR: Only for scanned documents

2. **Memory management**:
   - Process large PDFs page by page
   - Close file handles explicitly
   - Use context managers (`with` statements)

3. **Quality vs. Speed**:
   - Higher DPI (300+) for better OCR accuracy
   - Lower DPI (150) for faster processing
   - Balance based on requirements

4. **Error handling**:
   - Always handle FileNotFoundError
   - Check for corrupted PDFs
   - Validate extracted data

5. **Testing**:
   - Test with various PDF sources
   - Verify table extraction accuracy
   - Check character encoding in text

---

## Next Steps

- Review [SKILL.md](../SKILL.md) for complete API reference
- Check [DEPENDENCIES.md](../DEPENDENCIES.md) for installation requirements
- See [README.md](../README.md) for integration details
- Run tests: `pytest tests/ -v`

---

**Last Updated**: 2025-11-08
**Maintained By**: amplihack project
