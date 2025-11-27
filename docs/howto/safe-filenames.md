# Generate Safe Filenames from User Input

Create filesystem-safe filenames from any text input using the amplihack slugify utility.

## Quick Start

```python
from amplihack.utils.string_utils import slugify
from pathlib import Path

def safe_filename(user_input, preserve_extension=True):
    """Convert user input to safe filename."""
    if preserve_extension and "." in user_input:
        name, ext = user_input.rsplit(".", 1)
        safe_name = slugify(name, separator="_", max_length=50)
        return f"{safe_name}.{ext.lower()}"

    return slugify(user_input, separator="_", max_length=50)

# Example
filename = safe_filename("Project Report (Final).docx")
print(filename)
# Output: project_report_final.docx
```

## Filesystem Considerations

### Cross-Platform Compatibility

Different operating systems have different filename restrictions:

```python
from amplihack.utils.string_utils import slugify
import platform

class FilenameGenerator:
    """Generate safe filenames for any OS."""

    # Reserved names on Windows
    WINDOWS_RESERVED = {
        "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4",
        "COM5", "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2",
        "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
    }

    def generate(self, text, max_length=255):
        """Generate OS-safe filename."""
        # Use underscore separator for filenames
        base_name = slugify(text, separator="_", max_length=max_length)

        # Handle Windows reserved names
        if platform.system() == "Windows":
            upper_name = base_name.upper()
            if upper_name in self.WINDOWS_RESERVED:
                base_name = f"file_{base_name}"

        # Ensure not empty
        if not base_name:
            base_name = "unnamed_file"

        return base_name

# Usage
gen = FilenameGenerator()
print(gen.generate("CON"))  # Windows reserved name
# Output: file_con (on Windows), con (on Unix)
```

### Handle File Extensions

Preserve and validate file extensions:

```python
from amplihack.utils.string_utils import slugify
from pathlib import Path

def process_filename_with_extension(filename):
    """Process filename preserving extension."""
    path = Path(filename)

    # Extract components
    stem = path.stem
    suffix = path.suffix.lower()

    # Generate safe stem
    safe_stem = slugify(stem, separator="_", max_length=200)

    # Validate extension
    if suffix and suffix[1:].isalnum():
        return f"{safe_stem}{suffix}"
    else:
        return safe_stem

# Examples
print(process_filename_with_extension("My Document.PDF"))
# Output: my_document.pdf

print(process_filename_with_extension("Report (2024).xlsx"))
# Output: report_2024.xlsx

print(process_filename_with_extension("No Extension"))
# Output: no_extension
```

### Length Limitations

Respect filesystem path length limits:

```python
from amplihack.utils.string_utils import slugify
import os

def filename_with_path_limit(filename, directory_path, max_path=260):
    """Generate filename respecting path limits."""
    # Windows MAX_PATH is 260 characters

    dir_length = len(os.path.abspath(directory_path))
    separator_length = 1  # Path separator
    available_length = max_path - dir_length - separator_length - 10  # Safety margin

    # Ensure positive length
    if available_length < 20:
        available_length = 20

    return slugify(filename, separator="_", max_length=available_length)

# Example
directory = "/home/user/documents/projects/2024/reports"
long_name = "Quarterly Business Report with Financial Analysis and Projections"

safe_name = filename_with_path_limit(long_name, directory)
print(f"Safe name: {safe_name}")
print(f"Full path length: {len(os.path.join(directory, safe_name))}")
```

## Common Patterns

### Timestamped Filenames

Add timestamps for versioning:

```python
from amplihack.utils.string_utils import slugify
from datetime import datetime

def timestamped_filename(base_name, extension=None):
    """Create filename with timestamp."""
    # Generate safe base name
    safe_base = slugify(base_name, separator="_")

    # Add timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if extension:
        return f"{safe_base}_{timestamp}.{extension}"
    return f"{safe_base}_{timestamp}"

# Examples
print(timestamped_filename("Backup"))
# Output: backup_20241127_143052

print(timestamped_filename("Database Export", "sql"))
# Output: database_export_20241127_143052.sql
```

### Unique Filename Generation

Prevent overwriting with unique names:

```python
from amplihack.utils.string_utils import slugify
from pathlib import Path

def unique_filename(base_name, directory, extension=""):
    """Generate unique filename in directory."""
    safe_base = slugify(base_name, separator="_")

    if extension and not extension.startswith("."):
        extension = f".{extension}"

    # Try original name first
    filename = f"{safe_base}{extension}"
    filepath = Path(directory) / filename

    # Add counter if exists
    counter = 1
    while filepath.exists():
        filename = f"{safe_base}_{counter}{extension}"
        filepath = Path(directory) / filename
        counter += 1

    return filename

# Example usage
directory = Path("./uploads")
directory.mkdir(exist_ok=True)

# First file
name1 = unique_filename("User Report", directory, "pdf")
print(name1)  # Output: user_report.pdf

# Create dummy file
(directory / name1).touch()

# Second file with same name
name2 = unique_filename("User Report", directory, "pdf")
print(name2)  # Output: user_report_1.pdf
```

### Batch File Renaming

Process multiple files consistently:

```python
from amplihack.utils.string_utils import slugify
from pathlib import Path

def batch_rename_files(directory, pattern="*", prefix="", preserve_extensions=True):
    """Rename all files in directory with safe names."""
    directory = Path(directory)
    renamed_files = []

    for old_path in directory.glob(pattern):
        if old_path.is_file():
            # Generate new name
            if preserve_extensions:
                stem = old_path.stem
                suffix = old_path.suffix
                new_stem = slugify(f"{prefix}{stem}", separator="_")
                new_name = f"{new_stem}{suffix}"
            else:
                new_name = slugify(f"{prefix}{old_path.name}", separator="_")

            # Rename file
            new_path = old_path.parent / new_name

            # Handle duplicates
            counter = 1
            while new_path.exists() and new_path != old_path:
                if preserve_extensions:
                    new_name = f"{new_stem}_{counter}{suffix}"
                else:
                    new_name = f"{slugify(old_path.name, separator='_')}_{counter}"
                new_path = old_path.parent / new_name
                counter += 1

            if new_path != old_path:
                old_path.rename(new_path)
                renamed_files.append((old_path.name, new_name))

    return renamed_files

# Example: Clean up downloads folder
# renamed = batch_rename_files("./downloads", pattern="*.pdf", prefix="doc_")
# for old, new in renamed:
#     print(f"{old} -> {new}")
```

### Content-Based Naming

Generate descriptive filenames from content:

```python
from amplihack.utils.string_utils import slugify
import hashlib

def content_based_filename(content, title=None, extension="txt"):
    """Generate filename based on content and optional title."""

    if title:
        # Use provided title
        base_name = slugify(title, separator="_", max_length=50)
    else:
        # Use first line or content hash
        first_line = content.split("\n")[0][:50] if content else ""
        if first_line:
            base_name = slugify(first_line, separator="_", max_length=50)
        else:
            # Fall back to content hash
            content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
            base_name = f"document_{content_hash}"

    return f"{base_name}.{extension}"

# Examples
content1 = "Project Status Report\nQ4 2024\nAll objectives met..."
print(content_based_filename(content1))
# Output: project_status_report.txt

content2 = "# Technical Documentation\n\nAPI Reference..."
print(content_based_filename(content2, extension="md"))
# Output: technical_documentation.md

content3 = ""
print(content_based_filename(content3, title="Empty File"))
# Output: empty_file.txt
```

## Security Considerations

### Prevent Directory Traversal

```python
from amplihack.utils.string_utils import slugify
from pathlib import Path

def secure_filename(user_input):
    """Generate filename preventing directory traversal."""
    # Remove any path components
    basename = Path(user_input).name

    # Remove dangerous patterns
    dangerous_patterns = ["../", "..\\", "..", "/", "\\"]
    for pattern in dangerous_patterns:
        basename = basename.replace(pattern, "")

    # Generate safe name
    safe_name = slugify(basename, separator="_")

    # Ensure not empty
    return safe_name if safe_name else "unnamed"

# Examples showing security
print(secure_filename("../../../etc/passwd"))
# Output: etcpasswd

print(secure_filename("..\\..\\windows\\system32\\config"))
# Output: windowssystem32config

print(secure_filename("innocent.txt"))
# Output: innocent_txt
```

### Sanitize User Uploads

```python
from amplihack.utils.string_utils import slugify
from pathlib import Path
import mimetypes

class UploadSanitizer:
    """Sanitize uploaded filenames."""

    ALLOWED_EXTENSIONS = {
        '.jpg', '.jpeg', '.png', '.gif', '.pdf',
        '.doc', '.docx', '.xls', '.xlsx', '.txt'
    }

    def sanitize(self, original_filename, user_id=None):
        """Sanitize uploaded filename."""
        path = Path(original_filename)
        extension = path.suffix.lower()

        # Validate extension
        if extension not in self.ALLOWED_EXTENSIONS:
            raise ValueError(f"File type {extension} not allowed")

        # Generate safe base name
        base_name = slugify(path.stem, separator="_", max_length=100)

        # Add user prefix if provided
        if user_id:
            base_name = f"user_{user_id}_{base_name}"

        # Add timestamp for uniqueness
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

        return f"{base_name}_{timestamp}{extension}"

# Usage
sanitizer = UploadSanitizer()
safe_name = sanitizer.sanitize("Vacation Photos (2024).JPG", user_id=42)
print(safe_name)
# Output: user_42_vacation_photos_2024_20241127143052.jpg
```

## Best Practices

### 1. Use Underscores for Filenames

```python
# Good: Underscores for files
filename = slugify(text, separator="_")

# Less ideal: Hyphens can cause issues in some contexts
filename = slugify(text, separator="-")
```

### 2. Preserve Original Extensions

```python
# Good: Keep original extension
name, ext = filename.rsplit(".", 1)
safe_name = f"{slugify(name, separator='_')}.{ext}"

# Bad: Lose file type information
safe_name = slugify(entire_filename, separator="_")
```

### 3. Add Metadata When Helpful

```python
# Good: Include useful context
filename = f"{user_id}_{timestamp}_{slugify(title, separator='_')}.pdf"

# Bad: No way to identify or sort files
filename = f"{slugify(title, separator='_')}.pdf"
```

## See Also

- [URL Generation Guide](./url-generation.md) - Creating URL slugs
- [String Utilities Reference](../reference/string-utils.md) - Complete API documentation
- [Slugify Function Reference](../reference/slugify.md) - Technical details

---

**Security Note**: Always validate file extensions and scan for malware when accepting user uploads, regardless of filename sanitization.
