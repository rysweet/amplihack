---
skill:
  name: docx
  description: Word document operations - creation and manipulation
---

# Word Document Operations

## Library: python-docx

```python
from docx import Document

# Create document
doc = Document()
doc.add_heading("Title", 0)
doc.add_paragraph("Content here")
doc.add_table(rows=3, cols=3)
doc.save("document.docx")

# Read document
doc = Document("existing.docx")
for para in doc.paragraphs:
    print(para.text)
```

## Template-Based Generation
```python
# Use placeholders in template
doc = Document("template.docx")
for para in doc.paragraphs:
    if "{{name}}" in para.text:
        para.text = para.text.replace("{{name}}", actual_name)
```
