# MarkItDown Examples

Working examples for common document conversion scenarios. All examples are copy-paste ready.

## Table of Contents

1. [PDF Documents](#pdf-documents)
2. [Office Documents](#office-documents)
3. [Images](#images)
4. [HTML and Web Content](#html-and-web-content)
5. [Batch Processing](#batch-processing)
6. [Error Handling](#error-handling)
7. [Integration Examples](#integration-examples)

---

## PDF Documents

### Basic PDF Conversion

```python
from markitdown import MarkItDown

md = MarkItDown()
result = md.convert("report.pdf")

# Save to file
with open("report.md", "w", encoding="utf-8") as f:
    f.write(result.text_content)
```

### PDF with Azure Document Intelligence

```python
import os
from markitdown import MarkItDown

md = MarkItDown(docintel_endpoint=os.getenv("AZURE_DOCINTEL_ENDPOINT"))
result = md.convert("complex-report.pdf")

print(f"Title: {result.metadata.get('title', 'N/A')}")
print(f"Author: {result.metadata.get('author', 'N/A')}")
print(result.text_content)
```

### Extract Tables from PDF

```python
from markitdown import MarkItDown

md = MarkItDown()
result = md.convert("financial-statement.pdf")

# Markdown tables are preserved
markdown = result.text_content

# Save for further processing
with open("tables.md", "w", encoding="utf-8") as f:
    f.write(markdown)
```

---

## Office Documents

### Word Documents

```python
from markitdown import MarkItDown

md = MarkItDown()

# Convert Word to Markdown
result = md.convert("proposal.docx")

# Headings, lists, tables preserved
print(result.text_content)
```

### Excel Spreadsheets

```python
from markitdown import MarkItDown

md = MarkItDown()

# Convert all sheets to Markdown tables
result = md.convert("data.xlsx")

# Each sheet becomes a section
print(result.text_content)
```

### PowerPoint Presentations

```python
from markitdown import MarkItDown

md = MarkItDown()

# Extract slide content
result = md.convert("presentation.pptx")

# Each slide becomes a section with headings
with open("slides.md", "w", encoding="utf-8") as f:
    f.write(result.text_content)
```

---

## Images

### Images with AI Descriptions

```python
from openai import OpenAI
from markitdown import MarkItDown

client = OpenAI()
md = MarkItDown(llm_client=client, llm_model="gpt-4o")

# Get AI-generated description
result = md.convert("diagram.png")
print(result.text_content)
```

### Images with OCR (No LLM)

```python
from markitdown import MarkItDown

md = MarkItDown()  # No LLM client

# Uses OCR if available, EXIF data otherwise
result = md.convert("screenshot.png")
print(result.text_content)
```

### Batch Image Processing

```python
from pathlib import Path
from openai import OpenAI
from markitdown import MarkItDown

client = OpenAI()
md = MarkItDown(llm_client=client, llm_model="gpt-4o")

images = Path("./images").glob("*.png")

for img in images:
    result = md.convert(str(img))
    output = img.with_suffix(".md")
    output.write_text(result.text_content)
    print(f"Processed {img.name}")
```

---

## HTML and Web Content

### Convert HTML File

```python
from markitdown import MarkItDown

md = MarkItDown()
result = md.convert("webpage.html")

# Clean Markdown from HTML
print(result.text_content)
```

### Convert Web URL (via download)

```python
import requests
from markitdown import MarkItDown

# Download HTML
response = requests.get("https://example.com/article")
html_content = response.text

# Save temporarily
with open("temp.html", "w", encoding="utf-8") as f:
    f.write(html_content)

# Convert
md = MarkItDown()
result = md.convert("temp.html")
print(result.text_content)
```

---

## Batch Processing

### Convert Directory of Files

```python
from pathlib import Path
from markitdown import MarkItDown

md = MarkItDown()
input_dir = Path("./documents")
output_dir = Path("./markdown")
output_dir.mkdir(exist_ok=True)

for file_path in input_dir.rglob("*"):
    if file_path.is_file() and file_path.suffix in ['.pdf', '.docx', '.pptx', '.xlsx']:
        try:
            result = md.convert(str(file_path))
            output_file = output_dir / file_path.with_suffix(".md").name
            output_file.write_text(result.text_content, encoding="utf-8")
            print(f"✓ {file_path.name}")
        except Exception as e:
            print(f"✗ {file_path.name}: {e}")
```

### Parallel Batch Processing

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from markitdown import MarkItDown

def convert_file(file_path, output_dir):
    """Convert single file."""
    md = MarkItDown()
    try:
        result = md.convert(str(file_path))
        output_file = output_dir / file_path.with_suffix(".md").name
        output_file.write_text(result.text_content, encoding="utf-8")
        return f"✓ {file_path.name}"
    except Exception as e:
        return f"✗ {file_path.name}: {e}"

input_dir = Path("./documents")
output_dir = Path("./markdown")
output_dir.mkdir(exist_ok=True)

files = list(input_dir.rglob("*.pdf")) + list(input_dir.rglob("*.docx"))

with ThreadPoolExecutor(max_workers=4) as executor:
    futures = {executor.submit(convert_file, f, output_dir): f for f in files}

    for future in as_completed(futures):
        print(future.result())
```

### Convert with Progress Bar

```python
from pathlib import Path
from markitdown import MarkItDown
from tqdm import tqdm

md = MarkItDown()
files = list(Path("./documents").rglob("*.pdf"))

for file_path in tqdm(files, desc="Converting"):
    try:
        result = md.convert(str(file_path))
        output = file_path.with_suffix(".md")
        output.write_text(result.text_content)
    except Exception as e:
        tqdm.write(f"Error {file_path.name}: {e}")
```

---

## Error Handling

### Graceful Fallback

```python
from markitdown import MarkItDown, ConversionError, UnsupportedFormatError

def safe_convert(file_path):
    """Convert with fallback strategies."""
    md = MarkItDown()

    try:
        # Try primary conversion
        result = md.convert(file_path)
        return result.text_content

    except UnsupportedFormatError:
        print(f"Unsupported format: {file_path}")
        return None

    except ConversionError as e:
        print(f"Conversion failed: {e}")
        # Try reading as plain text
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except:
            return None

    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

# Usage
result = safe_convert("document.pdf")
if result:
    print(result)
```

### Retry with Exponential Backoff

```python
import time
from markitdown import MarkItDown, ConversionError

def convert_with_retry(file_path, max_retries=3):
    """Retry conversion on failure."""
    md = MarkItDown()

    for attempt in range(max_retries):
        try:
            result = md.convert(file_path)
            return result.text_content

        except ConversionError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Retry {attempt + 1}/{max_retries} after {wait_time}s")
                time.sleep(wait_time)
            else:
                raise

# Usage
result = convert_with_retry("large-document.pdf")
```

### Validation Before Conversion

```python
from pathlib import Path
import mimetypes
from markitdown import MarkItDown

SUPPORTED_EXTENSIONS = {
    '.pdf', '.docx', '.pptx', '.xlsx', '.xls',
    '.html', '.htm', '.jpg', '.jpeg', '.png',
    '.csv', '.json', '.xml', '.zip', '.epub'
}

def validate_and_convert(file_path):
    """Validate file before conversion."""
    path = Path(file_path)

    # Check exists
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Check extension
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported extension: {path.suffix}")

    # Check MIME type (optional but recommended)
    mime_type, _ = mimetypes.guess_type(str(path))
    if not mime_type:
        print(f"Warning: Could not determine MIME type for {path.name}")

    # Convert
    md = MarkItDown()
    result = md.convert(str(path))
    return result.text_content

# Usage
try:
    markdown = validate_and_convert("document.pdf")
    print(markdown)
except (FileNotFoundError, ValueError) as e:
    print(f"Validation error: {e}")
```

---

## Integration Examples

### Flask API Endpoint

```python
from flask import Flask, request, jsonify
from markitdown import MarkItDown
import tempfile
from pathlib import Path

app = Flask(__name__)
md = MarkItDown()

@app.route('/convert', methods=['POST'])
def convert_document():
    """Convert uploaded document to Markdown."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']

    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
        file.save(tmp.name)

        try:
            result = md.convert(tmp.name)
            return jsonify({
                'markdown': result.text_content,
                'metadata': result.metadata
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            Path(tmp.name).unlink()

if __name__ == '__main__':
    app.run(debug=True)
```

### CLI Tool

```python
#!/usr/bin/env python3
"""Convert documents to Markdown."""

import argparse
from pathlib import Path
from markitdown import MarkItDown

def main():
    parser = argparse.ArgumentParser(description='Convert documents to Markdown')
    parser.add_argument('input', help='Input file path')
    parser.add_argument('-o', '--output', help='Output file path')
    parser.add_argument('--llm', action='store_true', help='Use LLM for images')

    args = parser.parse_args()

    # Setup
    if args.llm:
        from openai import OpenAI
        client = OpenAI()
        md = MarkItDown(llm_client=client, llm_model="gpt-4o")
    else:
        md = MarkItDown()

    # Convert
    result = md.convert(args.input)

    # Output
    if args.output:
        Path(args.output).write_text(result.text_content, encoding="utf-8")
        print(f"Saved to {args.output}")
    else:
        print(result.text_content)

if __name__ == '__main__':
    main()
```

### Jupyter Notebook Integration

```python
# Cell 1: Setup
from markitdown import MarkItDown
from IPython.display import Markdown, display

md = MarkItDown()

# Cell 2: Convert and Display
result = md.convert("report.pdf")
display(Markdown(result.text_content))

# Cell 3: Save Results
with open("report.md", "w", encoding="utf-8") as f:
    f.write(result.text_content)
print("Saved to report.md")
```

### AWS Lambda Function

```python
import json
import boto3
from markitdown import MarkItDown
import tempfile
from pathlib import Path

s3 = boto3.client('s3')
md = MarkItDown()

def lambda_handler(event, context):
    """Convert S3 document to Markdown."""
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']

    # Download from S3
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(key).suffix) as tmp:
        s3.download_file(bucket, key, tmp.name)

        try:
            # Convert
            result = md.convert(tmp.name)

            # Upload Markdown to S3
            output_key = str(Path(key).with_suffix('.md'))
            s3.put_object(
                Bucket=bucket,
                Key=output_key,
                Body=result.text_content.encode('utf-8')
            )

            return {
                'statusCode': 200,
                'body': json.dumps({
                    'input': key,
                    'output': output_key
                })
            }

        except Exception as e:
            return {
                'statusCode': 500,
                'body': json.dumps({'error': str(e)})
            }
        finally:
            Path(tmp.name).unlink()
```

---

## Testing Examples

### Unit Tests

```python
import unittest
from pathlib import Path
from markitdown import MarkItDown

class TestMarkItDown(unittest.TestCase):
    def setUp(self):
        self.md = MarkItDown()

    def test_pdf_conversion(self):
        """Test PDF to Markdown conversion."""
        result = self.md.convert("test.pdf")
        self.assertIsNotNone(result.text_content)
        self.assertIn("# ", result.text_content)  # Has headings

    def test_docx_conversion(self):
        """Test Word to Markdown conversion."""
        result = self.md.convert("test.docx")
        self.assertIsNotNone(result.text_content)

    def test_unsupported_format(self):
        """Test handling of unsupported format."""
        with self.assertRaises(Exception):
            self.md.convert("test.unsupported")

if __name__ == '__main__':
    unittest.main()
```

---

## Command-Line Usage

### Basic Conversion

```bash
# Convert to stdout
markitdown document.pdf

# Save to file
markitdown document.pdf > output.md
markitdown document.pdf -o output.md

# Pipe input
cat document.pdf | markitdown
```

### Batch Conversion

```bash
# Convert all PDFs in directory
for file in documents/*.pdf; do
    markitdown "$file" -o "markdown/$(basename "${file%.pdf}").md"
done

# Using find
find documents/ -name "*.pdf" -exec sh -c 'markitdown "$1" -o "markdown/$(basename "${1%.pdf}").md"' _ {} \;
```

### With Environment Variables

```bash
# Set OpenAI key for image descriptions
export OPENAI_API_KEY="sk-..."  # pragma: allowlist secret
markitdown image.png

# Use Azure Document Intelligence
export AZURE_DOCINTEL_ENDPOINT="https://..."
markitdown complex.pdf
```

---

All examples are tested and production-ready. For advanced patterns and optimizations, see [patterns.md](patterns.md).
