# How to Generate Safe Filenames

Create filesystem-safe filenames from user input using the `slugify` utility.

## Quick Start

```python
from amplihack.utils.string_utils import slugify

# Convert user input to safe filename
user_input = "My Document (v2.1).txt"
safe_name = slugify(user_input, separator="_")
print(safe_name)
# Output: my_document_v2_1_txt
```

## Common Scenarios

### Document Management

Handle user-uploaded documents:

```python
from amplihack.utils.string_utils import slugify
from pathlib import Path
import mimetypes

def save_uploaded_file(original_name: str, content: bytes) -> Path:
    """Save uploaded file with sanitized name."""
    # Extract extension
    name_parts = original_name.rsplit(".", 1)
    if len(name_parts) == 2:
        base_name, extension = name_parts
    else:
        base_name = original_name
        extension = "bin"  # Default for unknown

    # Sanitize the base name
    safe_base = slugify(base_name, separator="_", max_length=100)

    # Ensure we have a valid name
    if safe_base == "untitled":
        import time
        safe_base = f"upload_{int(time.time())}"

    # Construct final path
    filename = f"{safe_base}.{extension.lower()}"
    filepath = Path("uploads") / filename

    # Write file
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_bytes(content)

    return filepath

# Example usage
path = save_uploaded_file("Annual Report (2024) - FINAL!.pdf", b"content")
print(path)
# Output: uploads/annual_report_2024_final.pdf
```

### Batch Processing

Process multiple files with unique names:

```python
from collections import defaultdict

class FilenameGenerator:
    """Generate unique filenames from user input."""

    def __init__(self):
        self.used_names = defaultdict(int)

    def generate(self, name: str, extension: str = "") -> str:
        """Generate unique filename, appending numbers if needed."""
        # Create base slug
        base = slugify(name, separator="_", max_length=80)

        if base == "untitled":
            base = "file"

        # Check for uniqueness
        if base not in self.used_names:
            self.used_names[base] = 1
            final_name = base
        else:
            self.used_names[base] += 1
            final_name = f"{base}_{self.used_names[base]}"

        # Add extension
        if extension:
            extension = extension.lstrip(".")
            return f"{final_name}.{extension}"

        return final_name

# Example usage
generator = FilenameGenerator()

files = [
    ("My Photo.jpg", "jpg"),
    ("My Photo.jpg", "jpg"),  # Duplicate
    ("Family Photo!", "png"),
    ("###.txt", "txt"),  # Special chars only
]

for name, ext in files:
    safe_name = generator.generate(name, ext)
    print(safe_name)
# Output:
# my_photo.jpg
# my_photo_2.jpg
# family_photo.png
# file.txt
```

### Download Filenames

Generate download-safe filenames:

```python
from datetime import datetime

def create_download_name(
    file_type: str,
    description: str = "",
    include_timestamp: bool = True
) -> str:
    """Create descriptive download filename."""
    parts = []

    # Add type
    type_slug = slugify(file_type, separator="_")
    parts.append(type_slug)

    # Add description if provided
    if description:
        desc_slug = slugify(description, separator="_", max_length=30)
        if desc_slug != "untitled":
            parts.append(desc_slug)

    # Add timestamp if requested
    if include_timestamp:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        parts.append(timestamp)

    return "_".join(parts)

# Example usage
# Report with description
name1 = create_download_name("Report", "Q4 Sales Analysis")
print(f"{name1}.pdf")
# Output: report_q4_sales_analysis_20240315_143022.pdf

# Export without description
name2 = create_download_name("Export", include_timestamp=True)
print(f"{name2}.csv")
# Output: export_20240315_143022.csv

# Archive with custom description
name3 = create_download_name(
    "Backup",
    "Database Full",
    include_timestamp=False
)
print(f"{name3}.tar.gz")
# Output: backup_database_full.tar.gz
```

### Cross-Platform Compatibility

Ensure filenames work on all operating systems:

```python
def create_portable_filename(name: str, strict: bool = True) -> str:
    """Create filename safe for all platforms."""
    # Basic slugification
    safe_name = slugify(name, separator="_", max_length=200)

    if strict:
        # Remove additional problematic characters for maximum compatibility
        # Windows reserved characters
        windows_reserved = '<>:"|?*'
        for char in windows_reserved:
            safe_name = safe_name.replace(char, "_")

        # Avoid Windows reserved names
        reserved_names = {
            "con", "prn", "aux", "nul",
            "com1", "com2", "com3", "com4",
            "lpt1", "lpt2", "lpt3"
        }

        if safe_name.lower() in reserved_names:
            safe_name = f"{safe_name}_file"

        # Don't end with dot or space (Windows)
        safe_name = safe_name.rstrip(". ")

    return safe_name or "file"

# Example usage
# Normal usage
name1 = create_portable_filename("Project: Phase 1")
print(name1)
# Output: project_phase_1

# Windows reserved name
name2 = create_portable_filename("CON")
print(name2)
# Output: con_file

# Special characters
name3 = create_portable_filename("file<>name|test*")
print(name3)
# Output: file_name_test
```

### Archive Organization

Organize files in archives with clean paths:

```python
import zipfile
from pathlib import Path

def add_to_archive(
    archive: zipfile.ZipFile,
    file_path: Path,
    archive_name: str = None
) -> str:
    """Add file to archive with sanitized name."""
    # Use provided name or original filename
    if archive_name:
        name = archive_name
    else:
        name = file_path.name

    # Sanitize for archive storage
    safe_name = slugify(
        name.rsplit(".", 1)[0],
        separator="_",
        max_length=100
    )

    # Preserve extension
    if "." in file_path.name:
        extension = file_path.suffix
        archive_path = f"{safe_name}{extension}"
    else:
        archive_path = safe_name

    # Write to archive
    archive.write(file_path, arcname=archive_path)

    return archive_path

# Example usage
with zipfile.ZipFile("export.zip", "w") as zf:
    # Add files with sanitized names
    paths = [
        Path("Report (Draft).pdf"),
        Path("Data - 2024!.csv"),
        Path("配置.json"),  # Non-ASCII name
    ]

    for path in paths:
        archived_as = add_to_archive(zf, path)
        print(f"Added: {archived_as}")
# Output:
# Added: report_draft.pdf
# Added: data_2024.csv
# Added: untitled.json
```

## Handling Edge Cases

### Empty or Invalid Input

```python
def robust_filename(user_input: str, default_prefix: str = "file") -> str:
    """Handle all edge cases for filename generation."""
    if not user_input or not user_input.strip():
        # Empty input
        import uuid
        return f"{default_prefix}_{uuid.uuid4().hex[:8]}"

    slug = slugify(user_input, separator="_")

    if slug == "untitled":
        # Only special characters
        import hashlib
        hash_suffix = hashlib.md5(user_input.encode()).hexdigest()[:8]
        return f"{default_prefix}_{hash_suffix}"

    return slug

# Example usage
print(robust_filename(""))           # Output: file_a3b2c1d4
print(robust_filename("   "))        # Output: file_e5f6g7h8
print(robust_filename("!!!***"))     # Output: file_1a2b3c4d
print(robust_filename("Normal"))     # Output: normal
```

### Length Constraints

```python
def fit_filename_to_limit(
    name: str,
    extension: str = "",
    max_total: int = 255
) -> str:
    """Ensure filename fits filesystem limits."""
    # Reserve space for extension
    ext_length = len(extension) + 1 if extension else 0
    max_base = max_total - ext_length

    # Slugify with length limit
    base = slugify(name, separator="_", max_length=max_base)

    if base == "untitled":
        base = "file"

    # Construct final name
    if extension:
        return f"{base}.{extension}"

    return base

# Example usage
long_name = "A" * 300
filename = fit_filename_to_limit(long_name, "txt", max_total=255)
print(len(filename))  # Output: 255
print(filename[:50])   # Output: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.txt
```

## Security Considerations

### Path Traversal Prevention

```python
def secure_filename(untrusted_input: str) -> str:
    """Prevent path traversal attacks."""
    # Remove any path components
    name = untrusted_input.replace("/", "_").replace("\\", "_")

    # Remove parent directory references
    name = name.replace("..", "_")

    # Slugify for safety
    safe = slugify(name, separator="_")

    # Never return empty
    if safe == "untitled":
        import secrets
        return f"secure_{secrets.token_hex(4)}"

    return safe

# Example usage
print(secure_filename("../../../etc/passwd"))  # Output: _etc_passwd
print(secure_filename("..\\windows\\system32")) # Output: _windows_system32
print(secure_filename("normal_file.txt"))       # Output: normal_file_txt
```

## Best Practices

1. **Always validate the result** - Check for "untitled" return value
2. **Preserve extensions separately** - Handle extensions outside of slugification
3. **Use underscores for filenames** - More compatible than hyphens
4. **Implement uniqueness checks** - Avoid overwriting existing files
5. **Consider filesystem limits** - 255 characters for most systems
6. **Handle Unicode gracefully** - Non-ASCII characters will be removed
7. **Never trust user input** - Always sanitize for security

## See Also

- [URL Generation Guide](./url-generation.md) - Creating web-safe URLs
- [slugify Function Reference](../reference/slugify.md) - Complete API documentation
- [String Utilities Reference](../reference/string-utils.md) - Other string functions
