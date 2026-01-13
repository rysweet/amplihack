---
skill:
  name: pdf
  description: PDF document operations - creation, merging, extraction
---

# PDF Operations

## Libraries
- **PyPDF2**: Reading, merging, splitting
- **reportlab**: Creating PDFs from scratch
- **pdfplumber**: Text extraction with layout

## Common Operations

```python
from pypdf import PdfReader, PdfWriter

# Merge PDFs
writer = PdfWriter()
for pdf in ["doc1.pdf", "doc2.pdf"]:
    writer.append(pdf)
writer.write("merged.pdf")

# Extract text
reader = PdfReader("document.pdf")
text = "\n".join(page.extract_text() for page in reader.pages)
```

## CLI Tools
```bash
# Merge with pdftk
pdftk file1.pdf file2.pdf cat output merged.pdf

# Extract pages
pdftk input.pdf cat 1-5 output pages1-5.pdf
```
