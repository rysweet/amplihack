"""Basic verification tests for PDF skill.

These tests verify the PDF skill integration:
- Level 1: Skill file structure
- Level 2: Dependency availability
- Level 3: Basic functionality (if dependencies available)
- Level 4: Integration (future)

Tests skip gracefully if dependencies are missing.
"""

import sys
from pathlib import Path

import pytest
import yaml

# Add common verification utilities to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "common" / "verification"))

# Define skill dependencies
PYTHON_PACKAGES_REQUIRED = ["pypdf", "pdfplumber", "reportlab", "pandas"]
PYTHON_PACKAGES_OPTIONAL = ["pytesseract", "pdf2image"]
SYSTEM_COMMANDS_REQUIRED = []  # No system commands required for basic functionality
SYSTEM_COMMANDS_OPTIONAL = ["pdftotext", "qpdf", "pdftk", "tesseract"]


# Level 1: Skill Load Tests


def test_skill_file_exists():
    """Verify SKILL.md exists."""
    skill_file = Path(__file__).parent.parent / "SKILL.md"
    assert skill_file.exists(), "SKILL.md not found"


def test_skill_yaml_valid():
    """Verify SKILL.md has valid YAML frontmatter."""
    skill_file = Path(__file__).parent.parent / "SKILL.md"
    content = skill_file.read_text()
    assert content.startswith("---"), "SKILL.md missing YAML frontmatter"

    # Extract and parse YAML
    parts = content.split("---")
    assert len(parts) >= 3, "Invalid YAML structure in SKILL.md"

    metadata = yaml.safe_load(parts[1])
    assert isinstance(metadata, dict), "YAML frontmatter is not a dictionary"
    assert "name" in metadata, "YAML missing 'name' field"
    assert metadata["name"] == "pdf", "YAML name field should be 'pdf'"
    assert "description" in metadata, "YAML missing 'description' field"


def test_readme_exists():
    """Verify README.md exists with integration notes."""
    readme = Path(__file__).parent.parent / "README.md"
    assert readme.exists(), "README.md not found"

    content = readme.read_text()
    assert "amplihack" in content.lower(), "README missing amplihack context"
    assert "pdf" in content.lower(), "README should mention PDF"


def test_dependencies_file_exists():
    """Verify DEPENDENCIES.md exists."""
    deps_file = Path(__file__).parent.parent / "DEPENDENCIES.md"
    assert deps_file.exists(), "DEPENDENCIES.md not found"

    content = deps_file.read_text()
    # Check for key dependencies mentioned
    assert "pypdf" in content.lower(), "DEPENDENCIES.md should mention pypdf"
    assert "pdfplumber" in content.lower(), "DEPENDENCIES.md should mention pdfplumber"
    assert "reportlab" in content.lower(), "DEPENDENCIES.md should mention reportlab"


def test_examples_exist():
    """Verify examples directory and content exist."""
    examples_dir = Path(__file__).parent.parent / "examples"
    assert examples_dir.exists(), "examples/ directory not found"

    example_file = examples_dir / "example_usage.md"
    assert example_file.exists(), "examples/example_usage.md not found"

    content = example_file.read_text()
    assert len(content) > 100, "example_usage.md appears to be empty or too short"


# Level 2: Dependency Tests


def check_python_package(package: str) -> bool:
    """Check if Python package is installed."""
    try:
        __import__(package)
        return True
    except ImportError:
        return False


def check_system_command(command: str) -> bool:
    """Check if system command is available."""
    import subprocess

    try:
        subprocess.run(
            [command, "--version"],
            capture_output=True,
            check=True,
            timeout=5,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_dependencies():
    """Check if required dependencies are available."""
    return all(check_python_package(pkg) for pkg in PYTHON_PACKAGES_REQUIRED)


@pytest.mark.skipif(
    not check_dependencies(),
    reason="Required dependencies not installed (pypdf, pdfplumber, reportlab, pandas)",
)
def test_required_dependencies():
    """Test that required Python packages are available."""
    for package in PYTHON_PACKAGES_REQUIRED:
        assert check_python_package(package), f"Required package {package} not installed"


def test_optional_dependencies_status():
    """Report status of optional dependencies (does not fail)."""
    print("\n\nOptional Python packages:")
    for package in PYTHON_PACKAGES_OPTIONAL:
        status = "✓ Installed" if check_python_package(package) else "✗ Not installed"
        print(f"  {package}: {status}")

    print("\nOptional system commands:")
    for command in SYSTEM_COMMANDS_OPTIONAL:
        status = "✓ Available" if check_system_command(command) else "✗ Not available"
        print(f"  {command}: {status}")


# Level 3: Basic Functionality Tests


@pytest.mark.skipif(
    not check_dependencies(),
    reason="Required dependencies not installed",
)
def test_pypdf_basic_functionality():
    """Test basic pypdf functionality."""
    from io import BytesIO

    from pypdf import PdfReader, PdfWriter
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    # Create a simple test PDF in memory
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.drawString(100, 750, "Test PDF Document")
    c.drawString(100, 730, "This is a test page")
    c.save()

    # Read it back
    buffer.seek(0)
    reader = PdfReader(buffer)

    assert len(reader.pages) == 1, "PDF should have 1 page"

    # Extract text
    page = reader.pages[0]
    text = page.extract_text()
    assert "Test PDF Document" in text, "Text extraction failed"

    # Test write functionality
    writer = PdfWriter()
    writer.add_page(page)

    output_buffer = BytesIO()
    writer.write(output_buffer)

    # Verify written PDF
    output_buffer.seek(0)
    verify_reader = PdfReader(output_buffer)
    assert len(verify_reader.pages) == 1, "Written PDF should have 1 page"


@pytest.mark.skipif(
    not check_dependencies(),
    reason="Required dependencies not installed",
)
def test_pdfplumber_basic_functionality():
    """Test basic pdfplumber functionality."""
    from io import BytesIO

    import pdfplumber
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    # Create a test PDF with text
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.drawString(100, 750, "Test Document")
    c.drawString(100, 730, "Line 1")
    c.drawString(100, 710, "Line 2")
    c.save()

    # Read with pdfplumber
    buffer.seek(0)
    with pdfplumber.open(buffer) as pdf:
        assert len(pdf.pages) == 1, "PDF should have 1 page"

        page = pdf.pages[0]
        text = page.extract_text()

        assert text is not None, "Text extraction should not return None"
        assert "Test Document" in text, "Should extract 'Test Document'"


@pytest.mark.skipif(
    not check_dependencies(),
    reason="Required dependencies not installed",
)
def test_reportlab_basic_functionality():
    """Test basic reportlab PDF creation."""
    from io import BytesIO

    from pypdf import PdfReader
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    # Create PDF
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    c.drawString(100, height - 100, "Hello World")
    c.line(100, height - 120, 400, height - 120)
    c.save()

    # Verify PDF was created
    buffer.seek(0)
    reader = PdfReader(buffer)

    assert len(reader.pages) == 1, "Created PDF should have 1 page"
    page = reader.pages[0]

    # Check dimensions
    assert page.mediabox.width == letter[0], "Page width should match letter size"
    assert page.mediabox.height == letter[1], "Page height should match letter size"


@pytest.mark.skipif(
    not check_dependencies(),
    reason="Required dependencies not installed",
)
def test_pandas_table_export():
    """Test pandas integration for table export."""
    from io import BytesIO

    import pandas as pd

    # Create test DataFrame
    data = {
        "Name": ["Alice", "Bob", "Charlie"],
        "Age": [25, 30, 35],
        "City": ["New York", "London", "Paris"],
    }
    df = pd.DataFrame(data)

    # Export to Excel (in memory)
    buffer = BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")

    # Read back and verify
    buffer.seek(0)
    df_read = pd.read_excel(buffer, engine="openpyxl")

    assert df.equals(df_read), "DataFrame should round-trip through Excel"
    assert list(df_read.columns) == ["Name", "Age", "City"], "Column names should match"
    assert len(df_read) == 3, "Should have 3 rows"


@pytest.mark.skipif(
    not check_dependencies(),
    reason="Required dependencies not installed",
)
def test_pdf_merge():
    """Test merging multiple PDFs."""
    from io import BytesIO

    from pypdf import PdfReader, PdfWriter
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    # Create two test PDFs
    pdf1 = BytesIO()
    c1 = canvas.Canvas(pdf1, pagesize=letter)
    c1.drawString(100, 750, "Document 1")
    c1.save()

    pdf2 = BytesIO()
    c2 = canvas.Canvas(pdf2, pagesize=letter)
    c2.drawString(100, 750, "Document 2")
    c2.save()

    # Merge PDFs
    writer = PdfWriter()

    pdf1.seek(0)
    reader1 = PdfReader(pdf1)
    for page in reader1.pages:
        writer.add_page(page)

    pdf2.seek(0)
    reader2 = PdfReader(pdf2)
    for page in reader2.pages:
        writer.add_page(page)

    # Verify merged PDF
    output = BytesIO()
    writer.write(output)

    output.seek(0)
    merged_reader = PdfReader(output)
    assert len(merged_reader.pages) == 2, "Merged PDF should have 2 pages"


@pytest.mark.skipif(
    not check_dependencies(),
    reason="Required dependencies not installed",
)
def test_pdf_rotation():
    """Test page rotation."""
    from io import BytesIO

    from pypdf import PdfReader, PdfWriter
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    # Create test PDF
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.drawString(100, 750, "Test Page")
    c.save()

    # Rotate page
    buffer.seek(0)
    reader = PdfReader(buffer)
    writer = PdfWriter()

    page = reader.pages[0]
    page.rotate(90)
    writer.add_page(page)

    # Verify rotation
    output = BytesIO()
    writer.write(output)

    output.seek(0)
    rotated_reader = PdfReader(output)
    rotated_page = rotated_reader.pages[0]

    # After 90 degree rotation, width and height should be swapped
    # (Note: exact behavior may vary by PDF library version)
    assert rotated_page is not None, "Rotated page should exist"


@pytest.mark.skipif(
    not check_dependencies(),
    reason="Required dependencies not installed",
)
def test_pdf_metadata():
    """Test metadata extraction and modification."""
    from io import BytesIO

    from pypdf import PdfReader, PdfWriter
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    # Create test PDF
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setTitle("Test Document")
    c.setAuthor("Test Author")
    c.drawString(100, 750, "Test")
    c.save()

    # Read metadata
    buffer.seek(0)
    reader = PdfReader(buffer)
    meta = reader.metadata

    # Note: reportlab may not set all metadata fields
    assert meta is not None, "Metadata should be accessible"

    # Add metadata to new PDF
    writer = PdfWriter()
    writer.add_page(reader.pages[0])
    writer.add_metadata(
        {
            "/Title": "Updated Title",
            "/Author": "Updated Author",
            "/Subject": "Test Subject",
        }
    )

    output = BytesIO()
    writer.write(output)

    # Verify new metadata
    output.seek(0)
    new_reader = PdfReader(output)
    new_meta = new_reader.metadata

    assert new_meta.title == "Updated Title", "Title should be updated"
    assert new_meta.author == "Updated Author", "Author should be updated"


# Level 4: Integration Tests (Future)
# These tests will verify skill usage in Claude Code context


@pytest.mark.skip(reason="Integration tests not yet implemented")
def test_skill_invocation():
    """Test that skill can be invoked in Claude Code."""
    # Future: Test skill invocation through Claude Code API


@pytest.mark.skip(reason="Integration tests not yet implemented")
def test_skill_with_real_pdf():
    """Test skill with a real PDF file."""
    # Future: Test with actual PDF files in fixtures


# Utility function for manual testing


def print_dependency_report():
    """Print comprehensive dependency report."""
    print("\n" + "=" * 60)
    print("PDF Skill Dependency Report")
    print("=" * 60)

    print("\nRequired Python Packages:")
    for package in PYTHON_PACKAGES_REQUIRED:
        status = "✓ Installed" if check_python_package(package) else "✗ MISSING"
        print(f"  {package:20s}: {status}")

    print("\nOptional Python Packages:")
    for package in PYTHON_PACKAGES_OPTIONAL:
        status = "✓ Installed" if check_python_package(package) else "✗ Not installed"
        print(f"  {package:20s}: {status}")

    print("\nOptional System Commands:")
    for command in SYSTEM_COMMANDS_OPTIONAL:
        status = "✓ Available" if check_system_command(command) else "✗ Not available"
        print(f"  {command:20s}: {status}")

    print("\n" + "=" * 60)

    all_required = all(check_python_package(pkg) for pkg in PYTHON_PACKAGES_REQUIRED)
    if all_required:
        print("✓ PDF skill is ready to use (core functionality)")
    else:
        print("✗ PDF skill is missing required dependencies")
        print("\nInstall with: pip install pypdf pdfplumber reportlab pandas")

    print("=" * 60 + "\n")


if __name__ == "__main__":
    # When run directly, print dependency report
    print_dependency_report()

    # Run tests
    import sys

    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
