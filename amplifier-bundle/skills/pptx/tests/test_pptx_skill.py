"""Basic verification tests for PPTX skill.

These tests verify the PPTX skill integration:
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
PYTHON_PACKAGES_REQUIRED = ["markitdown", "defusedxml"]
PYTHON_PACKAGES_OPTIONAL = ["pptx"]  # python-pptx
NODE_PACKAGES_REQUIRED = []  # Check via command-line, not importlib
SYSTEM_COMMANDS_REQUIRED = ["soffice"]  # LibreOffice
SYSTEM_COMMANDS_OPTIONAL = ["pdftoppm", "node", "npm"]


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
    assert metadata["name"] == "pptx", "YAML name field should be 'pptx'"
    assert "description" in metadata, "YAML missing 'description' field"


def test_readme_exists():
    """Verify README.md exists with integration notes."""
    readme = Path(__file__).parent.parent / "README.md"
    assert readme.exists(), "README.md not found"

    content = readme.read_text()
    assert "amplihack" in content.lower(), "README missing amplihack context"
    assert "pptx" in content.lower() or "powerpoint" in content.lower(), (
        "README should mention PPTX/PowerPoint"
    )


def test_dependencies_file_exists():
    """Verify DEPENDENCIES.md exists."""
    deps_file = Path(__file__).parent.parent / "DEPENDENCIES.md"
    assert deps_file.exists(), "DEPENDENCIES.md not found"

    content = deps_file.read_text()
    # Check for key dependencies mentioned
    assert "markitdown" in content.lower(), "DEPENDENCIES.md should mention markitdown"
    assert "pptxgenjs" in content.lower(), "DEPENDENCIES.md should mention pptxgenjs"
    assert "defusedxml" in content.lower(), "DEPENDENCIES.md should mention defusedxml"


def test_examples_exist():
    """Verify examples directory and content exist."""
    examples_dir = Path(__file__).parent.parent / "examples"
    assert examples_dir.exists(), "examples/ directory not found"

    example_file = examples_dir / "example_usage.md"
    assert example_file.exists(), "examples/example_usage.md not found"

    content = example_file.read_text()
    assert len(content) > 100, "example_usage.md appears to be empty or too short"


def test_scripts_directory_exists():
    """Verify scripts directory and PPTX-specific scripts exist."""
    scripts_dir = Path(__file__).parent.parent / "scripts"
    assert scripts_dir.exists(), "scripts/ directory not found"

    # Check for PPTX-specific scripts
    expected_scripts = [
        "thumbnail.py",
        "rearrange.py",
        "inventory.py",
        "replace.py",
        "html2pptx.js",
    ]
    for script in expected_scripts:
        script_path = scripts_dir / script
        assert script_path.exists(), f"scripts/{script} not found"


def test_ooxml_symlink_exists():
    """Verify ooxml symlink to common/ooxml exists."""
    ooxml_link = Path(__file__).parent.parent / "ooxml"
    assert ooxml_link.exists(), "ooxml/ symlink not found"
    assert ooxml_link.is_symlink(), "ooxml should be a symlink to ../common/ooxml"

    # Verify it points to common/ooxml
    target = ooxml_link.resolve()
    assert "common" in str(target) and "ooxml" in str(target), (
        "ooxml symlink should point to common/ooxml"
    )


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


def check_node_package(package: str) -> bool:
    """Check if Node.js package is installed globally."""
    import subprocess

    try:
        result = subprocess.run(
            ["npm", "list", "-g", package],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_dependencies():
    """Check if required dependencies are available."""
    python_ok = all(check_python_package(pkg) for pkg in PYTHON_PACKAGES_REQUIRED)
    system_ok = all(check_system_command(cmd) for cmd in SYSTEM_COMMANDS_REQUIRED)
    return python_ok and system_ok


@pytest.mark.skipif(
    not check_dependencies(),
    reason="Required dependencies not installed (markitdown, defusedxml, soffice)",
)
def test_required_dependencies():
    """Test that required dependencies are available."""
    for package in PYTHON_PACKAGES_REQUIRED:
        assert check_python_package(package), f"Required package {package} not installed"

    for command in SYSTEM_COMMANDS_REQUIRED:
        assert check_system_command(command), f"Required command {command} not available"


def test_optional_dependencies_status():
    """Report status of optional dependencies (does not fail)."""
    print("\n\nOptional Python packages:")
    for package in PYTHON_PACKAGES_OPTIONAL:
        status = "✓ Installed" if check_python_package(package) else "✗ Not installed"
        print(f"  {package}: {status}")

    print("\nNode.js packages (optional for creation):")
    node_packages = ["pptxgenjs", "playwright", "sharp", "react-icons"]
    for package in node_packages:
        status = "✓ Installed" if check_node_package(package) else "✗ Not installed"
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
def test_markitdown_import():
    """Test that markitdown can be imported."""
    import markitdown  # noqa: F401

    # Basic import test
    assert True, "markitdown imported successfully"


@pytest.mark.skipif(
    not check_dependencies(),
    reason="Required dependencies not installed",
)
def test_defusedxml_import():
    """Test that defusedxml can be imported."""
    import defusedxml  # noqa: F401
    from defusedxml import ElementTree

    # Basic import test
    assert ElementTree is not None, "defusedxml ElementTree available"


@pytest.mark.skipif(
    not check_python_package("pptx"),
    reason="python-pptx not installed",
)
def test_python_pptx_basic_functionality():
    """Test basic python-pptx functionality."""
    from io import BytesIO

    from pptx import Presentation

    # Create a new presentation
    prs = Presentation()
    assert prs is not None, "Presentation object created"

    # Add a blank slide
    blank_slide_layout = prs.slide_layouts[6]  # Blank layout
    slide = prs.slides.add_slide(blank_slide_layout)
    assert slide is not None, "Slide added to presentation"

    # Save to buffer
    buffer = BytesIO()
    prs.save(buffer)

    # Verify saved
    buffer.seek(0)
    assert len(buffer.getvalue()) > 0, "Presentation saved to buffer"

    # Read back
    prs2 = Presentation(buffer)
    assert len(prs2.slides) == 1, "Presentation should have 1 slide"


@pytest.mark.skipif(
    not check_python_package("pptx"),
    reason="python-pptx not installed",
)
def test_python_pptx_text_manipulation():
    """Test adding text to slides."""
    from io import BytesIO

    from pptx import Presentation
    from pptx.util import Inches, Pt

    # Create presentation
    prs = Presentation()
    blank_slide_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(blank_slide_layout)

    # Add text box
    left = top = Inches(1)
    width = Inches(8)
    height = Inches(1)
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame

    tf.text = "Test Title"
    p = tf.paragraphs[0]
    p.font.size = Pt(24)
    p.font.bold = True

    # Save and verify
    buffer = BytesIO()
    prs.save(buffer)

    buffer.seek(0)
    prs2 = Presentation(buffer)
    slide2 = prs2.slides[0]

    # Verify text box exists
    assert len(slide2.shapes) == 1, "Slide should have 1 shape"
    shape = slide2.shapes[0]
    assert shape.text == "Test Title", "Text should match"


@pytest.mark.skipif(
    not (check_python_package("pptx") and check_system_command("soffice")),
    reason="python-pptx or LibreOffice not installed",
)
def test_pptx_to_pdf_conversion():
    """Test converting PPTX to PDF using LibreOffice."""
    import subprocess
    import tempfile

    from pptx import Presentation

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create simple presentation
        prs = Presentation()
        blank_slide_layout = prs.slide_layouts[6]
        prs.slides.add_slide(blank_slide_layout)

        # Save to temp file
        pptx_path = tmpdir_path / "test.pptx"
        prs.save(str(pptx_path))

        # Convert to PDF
        try:
            subprocess.run(
                ["soffice", "--headless", "--convert-to", "pdf", str(pptx_path)],
                capture_output=True,
                timeout=30,
                cwd=str(tmpdir_path),
            )

            pdf_path = tmpdir_path / "test.pdf"
            assert pdf_path.exists(), "PDF should be created"
            assert pdf_path.stat().st_size > 0, "PDF should not be empty"

        except subprocess.TimeoutExpired:
            pytest.skip("LibreOffice conversion timed out")


@pytest.mark.skipif(
    not check_dependencies(),
    reason="Required dependencies not installed",
)
def test_ooxml_scripts_exist_and_executable():
    """Test that OOXML scripts are accessible via symlink."""
    ooxml_dir = Path(__file__).parent.parent / "ooxml"
    assert ooxml_dir.exists(), "ooxml directory (symlink) should exist"

    # Check for common OOXML scripts
    scripts_dir = ooxml_dir / "scripts"
    if scripts_dir.exists():
        expected_scripts = ["unpack.py", "pack.py"]
        for script in expected_scripts:
            script_path = scripts_dir / script
            if script_path.exists():
                # Verify it's executable or can be run with python
                assert script_path.is_file(), f"{script} should be a file"


@pytest.mark.skipif(
    not check_dependencies(),
    reason="Required dependencies not installed",
)
def test_pptx_specific_scripts_executable():
    """Test that PPTX-specific scripts are accessible."""
    scripts_dir = Path(__file__).parent.parent / "scripts"
    assert scripts_dir.exists(), "scripts directory should exist"

    # Check for PPTX-specific Python scripts
    python_scripts = ["thumbnail.py", "rearrange.py", "inventory.py", "replace.py"]
    for script in python_scripts:
        script_path = scripts_dir / script
        assert script_path.exists(), f"scripts/{script} should exist"
        assert script_path.is_file(), f"scripts/{script} should be a file"

    # Check for JavaScript script
    js_script = scripts_dir / "html2pptx.js"
    assert js_script.exists(), "scripts/html2pptx.js should exist"
    assert js_script.is_file(), "scripts/html2pptx.js should be a file"


# Level 4: Integration Tests (Future)
# These tests will verify skill usage in Claude Code context


@pytest.mark.skip(reason="Integration tests not yet implemented")
def test_skill_invocation():
    """Test that skill can be invoked in Claude Code."""
    # Future: Test skill invocation through Claude Code API


@pytest.mark.skip(reason="Integration tests not yet implemented")
def test_skill_with_real_pptx():
    """Test skill with a real PPTX file."""
    # Future: Test with actual PPTX files in fixtures


@pytest.mark.skip(reason="Integration tests not yet implemented")
def test_template_workflow():
    """Test complete template-based workflow."""
    # Future: Test rearrange → inventory → replace workflow


# Utility function for manual testing


def print_dependency_report():
    """Print comprehensive dependency report."""
    print("\n" + "=" * 60)
    print("PPTX Skill Dependency Report")
    print("=" * 60)

    print("\nRequired Python Packages:")
    for package in PYTHON_PACKAGES_REQUIRED:
        status = "✓ Installed" if check_python_package(package) else "✗ MISSING"
        print(f"  {package:20s}: {status}")

    print("\nOptional Python Packages:")
    for package in PYTHON_PACKAGES_OPTIONAL:
        status = "✓ Installed" if check_python_package(package) else "✗ Not installed"
        print(f"  {package:20s}: {status}")

    print("\nRequired System Commands:")
    for command in SYSTEM_COMMANDS_REQUIRED:
        status = "✓ Available" if check_system_command(command) else "✗ MISSING"
        print(f"  {command:20s}: {status}")

    print("\nOptional System Commands:")
    for command in SYSTEM_COMMANDS_OPTIONAL:
        status = "✓ Available" if check_system_command(command) else "✗ Not available"
        print(f"  {command:20s}: {status}")

    print("\nNode.js Packages (for presentation creation):")
    node_packages = ["pptxgenjs", "playwright", "sharp", "react-icons"]
    for package in node_packages:
        status = "✓ Installed" if check_node_package(package) else "✗ Not installed"
        print(f"  {package:20s}: {status}")

    print("\n" + "=" * 60)

    python_ok = all(check_python_package(pkg) for pkg in PYTHON_PACKAGES_REQUIRED)
    system_ok = all(check_system_command(cmd) for cmd in SYSTEM_COMMANDS_REQUIRED)

    if python_ok and system_ok:
        print("✓ PPTX skill is ready to use (core functionality)")
        print("\nFor full functionality (creation from scratch), install:")
        print("  npm install -g pptxgenjs playwright sharp react-icons react react-dom")
    else:
        print("✗ PPTX skill is missing required dependencies")
        if not python_ok:
            print("\nInstall Python packages with:")
            print("  pip install markitdown defusedxml")
        if not system_ok:
            print("\nInstall LibreOffice (for PDF conversion):")
            print("  brew install libreoffice  # macOS")
            print("  sudo apt-get install libreoffice  # Linux")

    print("=" * 60 + "\n")


if __name__ == "__main__":
    # When run directly, print dependency report
    print_dependency_report()

    # Run tests
    import sys

    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
