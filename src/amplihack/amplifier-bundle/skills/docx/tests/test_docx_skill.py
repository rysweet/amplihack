"""Basic verification tests for DOCX skill.

These tests verify the DOCX skill integration:
- Level 1: Skill file structure
- Level 2: Dependency availability
- Level 3: Basic functionality (if dependencies available)
- Level 4: Integration (future)

Tests skip gracefully if dependencies are missing.
"""

from pathlib import Path

import pytest
import yaml

# Define skill dependencies
PYTHON_PACKAGES_REQUIRED = ["defusedxml"]
PYTHON_PACKAGES_OPTIONAL = []
SYSTEM_COMMANDS_REQUIRED = ["pandoc", "soffice"]
SYSTEM_COMMANDS_OPTIONAL = ["pdftoppm", "node"]


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
    assert metadata["name"] == "docx", "YAML name field should be 'docx'"
    assert "description" in metadata, "YAML missing 'description' field"


def test_readme_exists():
    """Verify README.md exists with integration notes."""
    readme = Path(__file__).parent.parent / "README.md"
    assert readme.exists(), "README.md not found"

    content = readme.read_text()
    assert "amplihack" in content.lower(), "README missing amplihack context"
    assert "docx" in content.lower(), "README should mention DOCX"
    assert "tracked changes" in content.lower() or "redlining" in content.lower(), (
        "README should mention tracked changes or redlining"
    )


def test_dependencies_file_exists():
    """Verify DEPENDENCIES.md exists."""
    deps_file = Path(__file__).parent.parent / "DEPENDENCIES.md"
    assert deps_file.exists(), "DEPENDENCIES.md not found"

    content = deps_file.read_text()
    # Check for key dependencies mentioned
    assert "defusedxml" in content.lower(), "DEPENDENCIES.md should mention defusedxml"
    assert "pandoc" in content.lower(), "DEPENDENCIES.md should mention pandoc"
    assert "libreoffice" in content.lower() or "soffice" in content.lower(), (
        "DEPENDENCIES.md should mention LibreOffice"
    )


def test_examples_exist():
    """Verify examples directory and content exist."""
    examples_dir = Path(__file__).parent.parent / "examples"
    assert examples_dir.exists(), "examples/ directory not found"

    example_file = examples_dir / "example_usage.md"
    assert example_file.exists(), "examples/example_usage.md not found"

    content = example_file.read_text()
    assert len(content) > 100, "example_usage.md appears to be empty or too short"


def test_ooxml_symlink_exists():
    """Verify ooxml symlink or directory exists."""
    ooxml_path = Path(__file__).parent.parent / "ooxml"

    # Should exist as symlink or directory
    assert ooxml_path.exists(), "ooxml/ symlink or directory not found"

    # Check if scripts directory exists via symlink
    scripts_path = ooxml_path / "scripts"
    assert scripts_path.exists(), "ooxml/scripts/ not found (symlink may be broken)"

    # Verify unpack.py and pack.py exist
    assert (scripts_path / "unpack.py").exists(), "unpack.py not found"
    assert (scripts_path / "pack.py").exists(), "pack.py not found"


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
    python_ok = all(check_python_package(pkg) for pkg in PYTHON_PACKAGES_REQUIRED)
    system_ok = all(check_system_command(cmd) for cmd in SYSTEM_COMMANDS_REQUIRED)
    return python_ok and system_ok


@pytest.mark.skipif(
    not all(check_python_package(pkg) for pkg in PYTHON_PACKAGES_REQUIRED),
    reason="Required Python packages not installed (defusedxml)",
)
def test_required_python_dependencies():
    """Test that required Python packages are available."""
    for package in PYTHON_PACKAGES_REQUIRED:
        assert check_python_package(package), f"Required package {package} not installed"


@pytest.mark.skipif(
    not all(check_system_command(cmd) for cmd in SYSTEM_COMMANDS_REQUIRED),
    reason="Required system commands not installed (pandoc, soffice)",
)
def test_required_system_dependencies():
    """Test that required system commands are available."""
    for command in SYSTEM_COMMANDS_REQUIRED:
        assert check_system_command(command), f"Required command {command} not installed"


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
def test_defusedxml_basic_functionality():
    """Test basic defusedxml functionality."""
    from defusedxml import minidom

    # Parse simple XML
    xml_string = '<?xml version="1.0"?><root><item>Test</item></root>'
    dom = minidom.parseString(xml_string)

    # Verify parsing worked
    root = dom.documentElement
    assert root.tagName == "root", "Root element should be 'root'"

    items = root.getElementsByTagName("item")
    assert len(items) == 1, "Should have 1 item element"
    assert items[0].firstChild.nodeValue == "Test", "Item text should be 'Test'"


@pytest.mark.skipif(
    not check_dependencies(),
    reason="Required dependencies not installed",
)
def test_ooxml_unpack_script_exists():
    """Test that OOXML unpack script is accessible."""
    ooxml_path = Path(__file__).parent.parent / "ooxml"
    unpack_script = ooxml_path / "scripts" / "unpack.py"

    assert unpack_script.exists(), "unpack.py script not found"

    # Verify script is executable or Python file
    assert unpack_script.suffix == ".py", "unpack.py should be a Python file"

    # Verify script has content
    content = unpack_script.read_text()
    assert len(content) > 100, "unpack.py appears to be empty or too short"
    assert "defusedxml" in content, "unpack.py should use defusedxml"


@pytest.mark.skipif(
    not check_dependencies(),
    reason="Required dependencies not installed",
)
def test_ooxml_pack_script_exists():
    """Test that OOXML pack script is accessible."""
    ooxml_path = Path(__file__).parent.parent / "ooxml"
    pack_script = ooxml_path / "scripts" / "pack.py"

    assert pack_script.exists(), "pack.py script not found"

    # Verify script is Python file
    assert pack_script.suffix == ".py", "pack.py should be a Python file"

    # Verify script has content
    content = pack_script.read_text()
    assert len(content) > 100, "pack.py appears to be empty or too short"
    assert "defusedxml" in content, "pack.py should use defusedxml"


@pytest.mark.skipif(
    not check_dependencies(),
    reason="Required dependencies not installed",
)
def test_pandoc_basic_functionality():
    """Test basic pandoc functionality."""
    import subprocess
    import tempfile

    # Create temporary markdown file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as tmp:
        tmp.write("# Test Document\n\nThis is a test paragraph.")
        tmp_path = tmp.name

    try:
        # Convert markdown to DOCX
        output_path = tmp_path.replace(".md", ".docx")
        result = subprocess.run(
            ["pandoc", tmp_path, "-o", output_path], capture_output=True, text=True, timeout=10
        )

        assert result.returncode == 0, f"Pandoc conversion failed: {result.stderr}"
        assert Path(output_path).exists(), "Output DOCX file not created"

        # Verify output file is not empty
        assert Path(output_path).stat().st_size > 0, "Output DOCX file is empty"

        # Clean up
        Path(output_path).unlink()
    finally:
        Path(tmp_path).unlink()


@pytest.mark.skipif(
    not check_dependencies(),
    reason="Required dependencies not installed",
)
def test_soffice_basic_functionality():
    """Test basic LibreOffice (soffice) functionality."""
    import subprocess

    # Just verify soffice can report version
    result = subprocess.run(["soffice", "--version"], capture_output=True, text=True, timeout=5)

    assert result.returncode == 0, "soffice --version failed"
    assert "libreoffice" in result.stdout.lower(), "Output should mention LibreOffice"


@pytest.mark.skipif(
    not check_dependencies(),
    reason="Required dependencies not installed",
)
def test_ooxml_xml_manipulation():
    """Test XML manipulation capabilities."""
    from defusedxml import minidom

    # Create a simple OOXML-like structure
    doc = minidom.parseString("""<?xml version="1.0"?>
    <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
        <w:body>
            <w:p>
                <w:r>
                    <w:t>Hello World</w:t>
                </w:r>
            </w:p>
        </w:body>
    </w:document>
    """)

    # Test XML traversal
    text_nodes = doc.getElementsByTagName("w:t")
    assert len(text_nodes) == 1, "Should have 1 text node"
    assert text_nodes[0].firstChild.nodeValue == "Hello World", "Text should be 'Hello World'"

    # Test XML modification
    text_nodes[0].firstChild.nodeValue = "Modified Text"
    assert text_nodes[0].firstChild.nodeValue == "Modified Text", "Text should be modified"

    # Test XML serialization
    xml_bytes = doc.toxml(encoding="UTF-8")
    assert b"Modified Text" in xml_bytes, "Serialized XML should contain modified text"


@pytest.mark.skipif(
    not check_dependencies(),
    reason="Required dependencies not installed",
)
def test_tracked_changes_xml_structure():
    """Test understanding of tracked changes XML structure."""
    from defusedxml import minidom

    # Create a document with tracked changes
    doc = minidom.parseString("""<?xml version="1.0"?>
    <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
        <w:body>
            <w:p>
                <w:r>
                    <w:t>The term is </w:t>
                </w:r>
                <w:del w:id="1" w:author="Reviewer">
                    <w:r>
                        <w:delText>30</w:delText>
                    </w:r>
                </w:del>
                <w:ins w:id="2" w:author="Reviewer">
                    <w:r>
                        <w:t>60</w:t>
                    </w:r>
                </w:ins>
                <w:r>
                    <w:t> days</w:t>
                </w:r>
            </w:p>
        </w:body>
    </w:document>
    """)

    # Verify deletion structure
    deletions = doc.getElementsByTagName("w:del")
    assert len(deletions) == 1, "Should have 1 deletion"
    assert deletions[0].getAttribute("w:author") == "Reviewer", "Deletion should have author"

    # Verify insertion structure
    insertions = doc.getElementsByTagName("w:ins")
    assert len(insertions) == 1, "Should have 1 insertion"
    assert insertions[0].getAttribute("w:author") == "Reviewer", "Insertion should have author"

    # Verify deleted text
    del_text_nodes = doc.getElementsByTagName("w:delText")
    assert len(del_text_nodes) == 1, "Should have 1 deleted text node"
    assert del_text_nodes[0].firstChild.nodeValue == "30", "Deleted text should be '30'"


# Level 4: Integration Tests (Future)


@pytest.mark.skip(reason="Integration tests not yet implemented")
def test_skill_invocation():
    """Test that skill can be invoked in Claude Code."""
    # Future: Test skill invocation through Claude Code API


@pytest.mark.skip(reason="Integration tests not yet implemented")
def test_full_unpack_pack_cycle():
    """Test complete unpack/modify/pack workflow."""
    # Future: Test with actual DOCX file in fixtures


@pytest.mark.skip(reason="Integration tests not yet implemented")
def test_tracked_changes_workflow():
    """Test complete tracked changes workflow."""
    # Future: Test redlining workflow end-to-end


# Utility function for manual testing


def print_dependency_report():
    """Print comprehensive dependency report."""
    print("\n" + "=" * 60)
    print("DOCX Skill Dependency Report")
    print("=" * 60)

    print("\nRequired Python Packages:")
    for package in PYTHON_PACKAGES_REQUIRED:
        status = "✓ Installed" if check_python_package(package) else "✗ MISSING"
        print(f"  {package:20s}: {status}")

    print("\nRequired System Commands:")
    for command in SYSTEM_COMMANDS_REQUIRED:
        status = "✓ Available" if check_system_command(command) else "✗ MISSING"
        print(f"  {command:20s}: {status}")

    print("\nOptional Python Packages:")
    for package in PYTHON_PACKAGES_OPTIONAL:
        status = "✓ Installed" if check_python_package(package) else "✗ Not installed"
        print(f"  {package:20s}: {status}")

    print("\nOptional System Commands:")
    for command in SYSTEM_COMMANDS_OPTIONAL:
        status = "✓ Available" if check_system_command(command) else "✗ Not available"
        print(f"  {command:20s}: {status}")

    print("\n" + "=" * 60)

    all_required = all(check_python_package(pkg) for pkg in PYTHON_PACKAGES_REQUIRED) and all(
        check_system_command(cmd) for cmd in SYSTEM_COMMANDS_REQUIRED
    )

    if all_required:
        print("✓ DOCX skill is ready to use (core functionality)")
    else:
        print("✗ DOCX skill is missing required dependencies")
        print("\nInstall with:")
        print("  pip install defusedxml")
        print("  sudo apt-get install pandoc libreoffice  # Ubuntu")
        print("  brew install pandoc libreoffice  # macOS")

    print("=" * 60 + "\n")


if __name__ == "__main__":
    # When run directly, print dependency report
    print_dependency_report()

    # Run tests
    import sys

    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
