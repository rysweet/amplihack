# MarkItDown Reference Documentation

**Source**: https://github.com/microsoft/markitdown
**Version**: Based on microsoft/markitdown main branch
**Last Updated**: 2026-02-14

## Table of Contents

1. [Complete API Reference](#complete-api-reference)
2. [Installation and Setup](#installation-and-setup)
3. [Configuration Options](#configuration-options)
4. [Azure Document Intelligence Integration](#azure-document-intelligence-integration)
5. [LLM Integration for Images](#llm-integration-for-images)
6. [Plugin Development](#plugin-development)
7. [Docker Deployment](#docker-deployment)
8. [MCP Server Setup](#mcp-server-setup)
9. [Error Handling](#error-handling)
10. [Troubleshooting](#troubleshooting)

---

## Complete API Reference

### MarkItDown Class

```python
class MarkItDown:
    def __init__(
        self,
        llm_client=None,
        llm_model=None,
        docintel_endpoint=None,
        enable_plugins=True
    ):
        """Initialize MarkItDown converter.

        Args:
            llm_client: OpenAI-compatible client for image descriptions
            llm_model: Model name (e.g., "gpt-4o", "gpt-4-vision-preview")
            docintel_endpoint: Azure Document Intelligence endpoint URL
            enable_plugins: Whether to enable plugin system (default: True)
        """
```

### convert() Method

```python
def convert(
    self,
    source: str | Path | bytes,
    file_extension: str = None
) -> ConversionResult:
    """Convert file to Markdown.

    Args:
        source: File path, URL, or bytes
        file_extension: Optional extension override (e.g., ".pdf")

    Returns:
        ConversionResult with text_content and metadata

    Raises:
        FileNotFoundError: Source file doesn't exist
        UnsupportedFormatError: File format not supported
        ConversionError: Conversion failed
    """
```

### ConversionResult

```python
@dataclass
class ConversionResult:
    text_content: str  # Markdown output
    metadata: dict     # File metadata (author, title, etc.)
```

---

## Installation and Setup

### Full Installation

```bash
# Install all optional dependencies
pip install 'markitdown[all]'
```

### Selective Installation

```bash
# Core only (CSV, JSON, XML, HTML, text)
pip install markitdown

# PDF support
pip install 'markitdown[pdf]'

# Office documents
pip install 'markitdown[docx, pptx, xlsx]'

# Images with OCR
pip install 'markitdown[ocr]'

# Audio transcription
pip install 'markitdown[audio]'

# Combine multiple features
pip install 'markitdown[pdf, docx, pptx, xlsx, ocr]'
```

### From Source

```bash
git clone git@github.com:microsoft/markitdown.git
cd markitdown
pip install -e 'packages/markitdown[all]'
```

### System Requirements

- Python 3.10 or higher
- For PDF: poppler-utils (optional, improves quality)
- For OCR: tesseract (optional)
- For audio: ffmpeg (optional)

---

## Configuration Options

### Basic Configuration

```python
from markitdown import MarkItDown

# Default configuration
md = MarkItDown()

# Disable plugins
md = MarkItDown(enable_plugins=False)
```

### With LLM for Images

```python
from openai import OpenAI

client = OpenAI(api_key="your-key")
md = MarkItDown(
    llm_client=client,
    llm_model="gpt-4o"  # or "gpt-4-vision-preview"
)
```

### With Azure Document Intelligence

```python
md = MarkItDown(
    docintel_endpoint="https://<your-resource>.cognitiveservices.azure.com/"
)
```

### Environment Variables

```bash
# OpenAI API Key
export OPENAI_API_KEY="sk-..."  # pragma: allowlist secret

# Azure Document Intelligence
export AZURE_DOCINTEL_ENDPOINT="https://..."
export AZURE_DOCINTEL_KEY="..."
```

---

## Azure Document Intelligence Integration

Azure Document Intelligence provides superior PDF conversion quality compared to basic extraction.

### Setup

1. **Create Azure Resource**:

   ```bash
   az cognitiveservices account create \
     --name my-docintel \
     --resource-group my-rg \
     --kind FormRecognizer \
     --sku S0 \
     --location westus2
   ```

2. **Get Endpoint and Key**:

   ```bash
   az cognitiveservices account show \
     --name my-docintel \
     --resource-group my-rg \
     --query properties.endpoint

   az cognitiveservices account keys list \
     --name my-docintel \
     --resource-group my-rg
   ```

3. **Use in Code**:

   ```python
   import os
   from markitdown import MarkItDown

   md = MarkItDown(
       docintel_endpoint=os.getenv("AZURE_DOCINTEL_ENDPOINT")
   )
   result = md.convert("complex-document.pdf")
   ```

### Benefits

- **Better Layout Detection**: Recognizes columns, tables, forms
- **Higher Accuracy**: Superior text extraction
- **Complex Documents**: Handles multi-column, forms, tables
- **Metadata Extraction**: Author, title, creation date

---

## LLM Integration for Images

### OpenAI Integration

```python
from openai import OpenAI
from markitdown import MarkItDown

client = OpenAI()
md = MarkItDown(llm_client=client, llm_model="gpt-4o")

# Image with AI-generated description
result = md.convert("diagram.png")
print(result.text_content)  # Includes AI description
```

### Azure OpenAI Integration

```python
from openai import AzureOpenAI
from markitdown import MarkItDown

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version="2024-02-01",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

md = MarkItDown(llm_client=client, llm_model="gpt-4o")
result = md.convert("image.jpg")
```

### Custom LLM Providers

Any OpenAI-compatible API works:

```python
from openai import OpenAI

# Example: Anthropic via OpenAI compatibility
client = OpenAI(
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    base_url="https://api.anthropic.com/v1"
)

md = MarkItDown(llm_client=client, llm_model="claude-3-opus-20240229")
```

### Image Description Behavior

- **With LLM**: Generates detailed description
- **Without LLM**: Uses EXIF data + OCR (if available)
- **Fallback**: Basic metadata (dimensions, format)

---

## Plugin Development

### Plugin Interface

```python
from markitdown import DocumentConverter

class CustomConverter(DocumentConverter):
    """Convert custom format to Markdown."""

    def convert(
        self,
        source: str | bytes,
        **kwargs
    ) -> ConversionResult:
        """Implement conversion logic."""
        # Your conversion code here
        markdown_text = self._process(source)

        return ConversionResult(
            text_content=markdown_text,
            metadata={"format": "custom"}
        )
```

### Registering Plugins

```python
from markitdown import MarkItDown

md = MarkItDown(enable_plugins=True)

# Register custom converter
md.register_converter(".xyz", CustomConverter())

# Use it
result = md.convert("file.xyz")
```

### Built-in Converters

- `PDFConverter`: PDF files
- `DocxConverter`: Word documents
- `PptxConverter`: PowerPoint
- `XlsxConverter`: Excel
- `ImageConverter`: Images with OCR/LLM
- `HTMLConverter`: HTML files
- `AudioConverter`: Audio with transcription
- `ZipConverter`: ZIP archives (processes contents)
- `CSVConverter`: CSV files
- `JSONConverter`: JSON files
- `XMLConverter`: XML files

---

## Docker Deployment

### Using Pre-built Image

```bash
# Run with file mount
docker run -v $(pwd):/data microsoft/markitdown /data/document.pdf
```

### Custom Dockerfile

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    poppler-utils \
    tesseract-ocr \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN pip install 'markitdown[all]'

WORKDIR /workspace
CMD ["markitdown"]
```

### Docker Compose

```yaml
version: "3.8"
services:
  markitdown:
    image: microsoft/markitdown
    volumes:
      - ./documents:/data
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    command: /data/document.pdf -o /data/output.md
```

---

## MCP Server Setup

MarkItDown includes a Model Context Protocol (MCP) server for LLM integrations.

### Setup

```bash
# Install MCP server
npm install -g @microsoft/markitdown-mcp

# Run server
markitdown-mcp --port 3000
```

### Configuration

```json
{
  "mcpServers": {
    "markitdown": {
      "command": "markitdown-mcp",
      "args": ["--port", "3000"],
      "env": {
        "OPENAI_API_KEY": "sk-..." // pragma: allowlist secret
      }
    }
  }
}
```

### Usage with Claude Code

MCP server allows Claude to convert documents during conversations:

```
User: "Convert the PDF report to markdown"
Claude: [Uses MCP server to call markitdown]
```

---

## Error Handling

### Common Exceptions

```python
from markitdown import (
    MarkItDown,
    UnsupportedFormatError,
    ConversionError
)

md = MarkItDown()

try:
    result = md.convert("document.xyz")
except FileNotFoundError:
    print("File not found")
except UnsupportedFormatError as e:
    print(f"Format not supported: {e}")
except ConversionError as e:
    print(f"Conversion failed: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Graceful Degradation

```python
def safe_convert(file_path):
    """Convert with fallback."""
    md = MarkItDown()

    try:
        # Try with full features
        result = md.convert(file_path)
        return result.text_content
    except ConversionError:
        # Fallback: basic text extraction
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except:
            return f"Failed to process {file_path}"
```

---

## Troubleshooting

### PDF Conversion Issues

**Problem**: Low-quality PDF extraction

**Solution**:

```python
# Use Azure Document Intelligence
md = MarkItDown(docintel_endpoint="<endpoint>")

# Or ensure poppler-utils installed
# sudo apt-get install poppler-utils
```

### Image Description Not Working

**Problem**: Images don't get AI descriptions

**Solution**:

```python
# Verify LLM client configured
from openai import OpenAI
client = OpenAI()  # Requires OPENAI_API_KEY
md = MarkItDown(llm_client=client, llm_model="gpt-4o")
```

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'markitdown'`

**Solution**:

```bash
# Ensure Python >= 3.10
python --version

# Reinstall with all dependencies
pip install --upgrade 'markitdown[all]'
```

### Memory Issues with Large Files

**Problem**: Out of memory with large PDFs

**Solution**:

```python
# Process in chunks or use streaming
import tempfile
from pathlib import Path

def process_large_pdf(pdf_path, chunk_size=10):
    """Process PDF in page chunks."""
    # Split PDF into smaller files first
    # Then convert each chunk
    pass
```

### Character Encoding Errors

**Problem**: Unicode decode errors

**Solution**:

```python
# Explicit encoding
result = md.convert(file_path)
text = result.text_content.encode('utf-8', errors='ignore').decode('utf-8')
```

### Plugin Not Loading

**Problem**: Custom plugin not recognized

**Solution**:

```python
# Ensure plugins enabled
md = MarkItDown(enable_plugins=True)

# Register before use
md.register_converter(".custom", CustomConverter())

# Verify registration
print(md.list_converters())
```

---

## Performance Optimization

### Batch Processing

```python
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

def convert_batch(files, max_workers=4):
    """Convert multiple files in parallel."""
    md = MarkItDown()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(md.convert, f): f for f in files}
        results = {}

        for future in futures:
            file = futures[future]
            try:
                results[file] = future.result()
            except Exception as e:
                results[file] = None
                print(f"Failed {file}: {e}")

    return results
```

### Caching Results

```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=100)
def convert_cached(file_path):
    """Cache conversion results."""
    md = MarkItDown()
    return md.convert(file_path)
```

---

## Security Considerations

### Input Validation

```python
import mimetypes
from pathlib import Path

ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.pptx', '.xlsx', '.txt', '.md'}

def safe_convert(file_path):
    """Validate before conversion."""
    path = Path(file_path)

    # Check extension
    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Extension {path.suffix} not allowed")

    # Check MIME type
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type not in ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
        raise ValueError(f"MIME type {mime_type} not allowed")

    # Convert
    md = MarkItDown()
    return md.convert(file_path)
```

### Sandboxing

```python
import tempfile
import shutil

def convert_sandboxed(file_path):
    """Convert in isolated temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Copy to temp
        temp_file = Path(tmpdir) / Path(file_path).name
        shutil.copy(file_path, temp_file)

        # Convert
        md = MarkItDown()
        result = md.convert(str(temp_file))

        # Temp directory auto-cleaned
        return result
```

---

## References

- **GitHub Repository**: https://github.com/microsoft/markitdown
- **Issues**: https://github.com/microsoft/markitdown/issues
- **PyPI Package**: https://pypi.org/project/markitdown/
- **MCP Protocol**: https://modelcontextprotocol.io/
- **Azure Document Intelligence**: https://azure.microsoft.com/en-us/products/ai-services/ai-document-intelligence
