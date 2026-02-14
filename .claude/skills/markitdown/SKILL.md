---
name: markitdown
version: 1.0.0
description: Convert documents (PDF, Word, Excel, PowerPoint, images, HTML) to Markdown using microsoft/markitdown. Use for document analysis, content extraction, preprocessing for LLMs, or batch document conversion. Supports images with OCR/LLM descriptions, audio transcription, and ZIP archives.
auto_activates:
  - "convert to markdown"
  - "extract document content"
  - "PDF to markdown"
  - "Word to markdown"
  - "document analysis"
  - "batch convert documents"
source_urls:
  - https://github.com/microsoft/markitdown
priority_score: 42.0
evaluation_criteria:
  frequency: HIGH
  impact: HIGH
  complexity: LOW
  reusability: HIGH
  philosophy_alignment: HIGH
  uniqueness: MEDIUM
---

# Document to Markdown Conversion

## Overview

Convert various document formats to clean Markdown using Microsoft's MarkItDown tool. Optimized for LLM processing, content extraction, and document analysis workflows.

**Supported Formats**: PDF, Word (.docx), PowerPoint (.pptx), Excel (.xlsx/.xls), Images (with OCR/LLM), HTML, Audio (with transcription), CSV, JSON, XML, ZIP archives, EPubs

## Quick Start

### Basic Usage

```python
from markitdown import MarkItDown

md = MarkItDown()
result = md.convert("document.pdf")
print(result.text_content)
```

### Command Line

```bash
# Convert single file
markitdown document.pdf > output.md
markitdown document.pdf -o output.md

# Pipe input
cat document.pdf | markitdown
```

## Common Patterns

### PDF Documents

```python
# Basic PDF conversion
md = MarkItDown()
result = md.convert("report.pdf")

# With Azure Document Intelligence (better quality)
md = MarkItDown(docintel_endpoint="<your-endpoint>")
result = md.convert("report.pdf")
```

### Office Documents

```python
# Word documents - preserves structure
result = md.convert("document.docx")

# Excel - converts tables to markdown tables
result = md.convert("spreadsheet.xlsx")

# PowerPoint - extracts slide content
result = md.convert("presentation.pptx")
```

### Images with Descriptions

```python
# Using LLM for image descriptions
from openai import OpenAI

client = OpenAI()
md = MarkItDown(llm_client=client, llm_model="gpt-4o")
result = md.convert("diagram.jpg")  # Gets AI-generated description
```

### Batch Processing

```python
from pathlib import Path

md = MarkItDown()
documents = Path(".").glob("*.pdf")

for doc in documents:
    result = md.convert(str(doc))
    output_path = doc.with_suffix(".md")
    output_path.write_text(result.text_content)
```

## Installation

```bash
# Full installation (all features)
pip install 'markitdown[all]'

# Selective features
pip install 'markitdown[pdf, docx, pptx]'
```

**Requirements**: Python 3.10 or higher

## Key Features

- **Structure Preservation**: Maintains headings, lists, tables, links
- **Plugin System**: Extend with custom converters
- **Docker Support**: Containerized deployments
- **MCP Integration**: Model Context Protocol server for LLM apps

## When to Read Supporting Files

- **[reference.md](reference.md)** - Read when you need:
  - Complete API reference and all configuration options
  - Azure Document Intelligence integration details
  - Plugin development guide
  - Docker and MCP server setup
  - Troubleshooting and error handling

- **[examples.md](examples.md)** - Read when you need:
  - Working examples for specific file types
  - Batch processing workflows
  - Error handling patterns
  - Integration with existing pipelines

- **[patterns.md](patterns.md)** - Read when you need:
  - Production deployment patterns
  - Performance optimization strategies
  - Security considerations
  - Anti-patterns to avoid

## Quick Reference

| File Type  | Use Case          | Command                                                     |
| ---------- | ----------------- | ----------------------------------------------------------- |
| PDF        | Reports, papers   | `md.convert("file.pdf")`                                    |
| Word       | Documents         | `md.convert("file.docx")`                                   |
| Excel      | Data tables       | `md.convert("file.xlsx")`                                   |
| PowerPoint | Presentations     | `md.convert("file.pptx")`                                   |
| Images     | Diagrams with OCR | `md = MarkItDown(llm_client=client); md.convert("img.jpg")` |
| HTML       | Web pages         | `md.convert("page.html")`                                   |
| ZIP        | Archives          | `md.convert("archive.zip")` - processes contents            |

## Common Issues

**Import Error**: Ensure Python >= 3.10 and markitdown installed
**Missing Dependencies**: Install with `pip install 'markitdown[all]'`
**Image Descriptions Not Working**: Requires LLM client (OpenAI or compatible)

For detailed troubleshooting, see [reference.md](reference.md).
