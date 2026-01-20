"""
Unit tests for BundlePackager base class.

Tests all common file operation methods shared between UVXPackager and FilesystemPackager.
"""

import json
from datetime import datetime
from uuid import uuid4

import pytest

from amplihack.bundle_generator.base_packager import BundlePackager
from amplihack.bundle_generator.models import AgentBundle, GeneratedAgent


@pytest.fixture
def base_packager():
    """Create a BundlePackager instance for testing."""
    return BundlePackager()


@pytest.fixture
def sample_agent():
    """Create a sample agent for testing."""
    return GeneratedAgent(
        id=uuid4(),
        name="test_agent",
        type="specialized",
        role="Test agent for unit tests",
        description="A test agent",
        content="""# Test Agent

This is a test agent for unit testing purposes. It demonstrates the basic structure
and content that all agents should have. This agent validates testing functionality.""",
        capabilities=["testing", "validation"],
        dependencies=[],
        tests=["def test_example():\n    assert True"],
        documentation="## Test Agent Documentation\n\nThis is documentation for the test agent.",
        model="claude-3-sonnet-20241022",
    )


@pytest.fixture
def sample_bundle(sample_agent):
    """Create a sample bundle for testing."""
    return AgentBundle(
        id=uuid4(),
        name="test-bundle",
        version="1.0.0",
        description="A test bundle for unit tests",
        agents=[sample_agent],
        manifest={
            "bundle": {
                "id": str(uuid4()),
                "name": "test-bundle",
                "version": "1.0.0",
                "description": "A test bundle",
            },
            "agents": [
                {
                    "name": "test_agent",
                    "type": "specialized",
                    "role": "Test agent",
                }
            ],
        },
        metadata={"preferences": {"test": "value"}},
        status="ready",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def temp_package_dir(tmp_path):
    """Create a temporary package directory for testing."""
    package_dir = tmp_path / "test-package"
    return package_dir


# =============================================================================
# Directory Structure Tests
# =============================================================================


def test_create_directory_structure(base_packager, temp_package_dir):
    """Test that directory structure is created correctly."""
    base_packager.create_directory_structure(temp_package_dir)

    # Verify all directories exist
    assert temp_package_dir.exists()
    assert (temp_package_dir / "agents").exists()
    assert (temp_package_dir / "tests").exists()
    assert (temp_package_dir / "docs").exists()
    assert (temp_package_dir / "config").exists()


def test_create_directory_structure_idempotent(base_packager, temp_package_dir):
    """Test that creating directory structure twice doesn't fail."""
    base_packager.create_directory_structure(temp_package_dir)
    base_packager.create_directory_structure(temp_package_dir)  # Should not raise

    assert temp_package_dir.exists()


# =============================================================================
# Agent Writing Tests
# =============================================================================


def test_write_agents(base_packager, sample_bundle, temp_package_dir):
    """Test that agents are written correctly."""
    base_packager.create_directory_structure(temp_package_dir)
    base_packager.write_agents(sample_bundle, temp_package_dir)

    agent_file = temp_package_dir / "agents" / "test_agent.md"
    assert agent_file.exists()
    assert "Test Agent" in agent_file.read_text()


def test_write_multiple_agents(base_packager, sample_bundle, temp_package_dir):
    """Test writing multiple agents."""
    # Add another agent
    agent2 = GeneratedAgent(
        id=uuid4(),
        name="test_agent_2",
        type="specialized",
        role="Second test agent",
        description="Another test agent",
        content="""# Test Agent 2

This is the second test agent for validating multi-agent bundle functionality.
It ensures that multiple agents can be written to the bundle correctly.""",
        capabilities=["testing"],
        dependencies=[],
    )
    sample_bundle.agents.append(agent2)

    base_packager.create_directory_structure(temp_package_dir)
    base_packager.write_agents(sample_bundle, temp_package_dir)

    assert (temp_package_dir / "agents" / "test_agent.md").exists()
    assert (temp_package_dir / "agents" / "test_agent_2.md").exists()


# =============================================================================
# Test Writing Tests
# =============================================================================


def test_write_tests(base_packager, sample_bundle, temp_package_dir):
    """Test that test files are written correctly."""
    base_packager.create_directory_structure(temp_package_dir)
    base_packager.write_tests(sample_bundle, temp_package_dir)

    # Verify __init__.py created
    init_file = temp_package_dir / "tests" / "__init__.py"
    assert init_file.exists()
    assert "Tests for agent bundle" in init_file.read_text()

    # Verify test file created
    test_file = temp_package_dir / "tests" / "test_test_agent.py"
    assert test_file.exists()
    assert "assert True" in test_file.read_text()


def test_write_tests_no_tests(base_packager, sample_bundle, temp_package_dir):
    """Test writing when agent has no tests."""
    sample_bundle.agents[0].tests = None

    base_packager.create_directory_structure(temp_package_dir)
    base_packager.write_tests(sample_bundle, temp_package_dir)

    # __init__.py should still exist
    assert (temp_package_dir / "tests" / "__init__.py").exists()

    # No test file should be created
    assert not (temp_package_dir / "tests" / "test_test_agent.py").exists()


# =============================================================================
# Documentation Writing Tests
# =============================================================================


def test_write_documentation(base_packager, sample_bundle, temp_package_dir):
    """Test that documentation is written correctly."""
    base_packager.create_directory_structure(temp_package_dir)
    base_packager.write_documentation(sample_bundle, temp_package_dir)

    doc_file = temp_package_dir / "docs" / "test_agent_docs.md"
    assert doc_file.exists()
    assert "Test Agent Documentation" in doc_file.read_text()


def test_write_documentation_no_docs(base_packager, sample_bundle, temp_package_dir):
    """Test when agent has no documentation."""
    sample_bundle.agents[0].documentation = None

    base_packager.create_directory_structure(temp_package_dir)
    base_packager.write_documentation(sample_bundle, temp_package_dir)

    # No doc file should be created
    assert not (temp_package_dir / "docs" / "test_agent_docs.md").exists()


# =============================================================================
# Configuration Writing Tests
# =============================================================================


def test_write_configuration(base_packager, sample_bundle, temp_package_dir):
    """Test that configuration is written correctly."""
    base_packager.create_directory_structure(temp_package_dir)
    base_packager.write_configuration(sample_bundle, temp_package_dir)

    config_file = temp_package_dir / "config" / "bundle_config.json"
    assert config_file.exists()

    config = json.loads(config_file.read_text())
    assert config["bundle_name"] == "test-bundle"
    assert config["bundle_version"] == "1.0.0"
    assert "test_agent" in config["enabled_agents"]
    assert config["preferences"]["test"] == "value"


# =============================================================================
# Manifest Writing Tests
# =============================================================================


def test_write_manifest(base_packager, sample_bundle, temp_package_dir):
    """Test that manifest is written correctly."""
    base_packager.create_directory_structure(temp_package_dir)
    base_packager.write_manifest(sample_bundle, temp_package_dir)

    manifest_file = temp_package_dir / "manifest.json"
    assert manifest_file.exists()

    manifest = json.loads(manifest_file.read_text())
    assert "bundle" in manifest
    assert manifest["bundle"]["name"] == "test-bundle"
    assert manifest["bundle"]["version"] == "1.0.0"
    assert len(manifest["agents"]) == 1
    assert manifest["agents"][0]["name"] == "test_agent"


# =============================================================================
# README Writing Tests
# =============================================================================


def test_write_readme(base_packager, sample_bundle, temp_package_dir):
    """Test that README is written correctly."""
    base_packager.create_directory_structure(temp_package_dir)
    base_packager.write_readme(sample_bundle, temp_package_dir)

    readme_file = temp_package_dir / "README.md"
    assert readme_file.exists()

    readme_content = readme_file.read_text()
    assert "# test-bundle" in readme_content
    assert "Installation" in readme_content
    assert "Quick Start" in readme_content
    assert "test_agent" in readme_content


# =============================================================================
# Python __init__ Writing Tests
# =============================================================================


def test_write_python_init(base_packager, sample_bundle, temp_package_dir):
    """Test that __init__.py is written correctly."""
    base_packager.create_directory_structure(temp_package_dir)
    base_packager.write_python_init(sample_bundle, temp_package_dir)

    init_file = temp_package_dir / "__init__.py"
    assert init_file.exists()

    init_content = init_file.read_text()
    assert f'__version__ = "{sample_bundle.version}"' in init_content
    assert "def load():" in init_content
    assert "def get_agent(name):" in init_content
    assert "def list_agents():" in init_content


# =============================================================================
# setup.py Writing Tests
# =============================================================================


def test_write_setup_py(base_packager, sample_bundle, temp_package_dir):
    """Test that setup.py is written correctly."""
    base_packager.create_directory_structure(temp_package_dir)
    base_packager.write_setup_py(sample_bundle, temp_package_dir)

    setup_file = temp_package_dir / "setup.py"
    assert setup_file.exists()

    setup_content = setup_file.read_text()
    assert "from setuptools import setup" in setup_content
    assert f'name="{sample_bundle.name}"' in setup_content
    assert f'version="{sample_bundle.version}"' in setup_content
    assert 'python_requires=">=3.11"' in setup_content


def test_write_setup_py_special_chars_in_description(
    base_packager, sample_bundle, temp_package_dir
):
    """Test setup.py with special characters in description."""
    sample_bundle.description = 'Test "bundle" with\nnewlines'

    base_packager.create_directory_structure(temp_package_dir)
    base_packager.write_setup_py(sample_bundle, temp_package_dir)

    setup_file = temp_package_dir / "setup.py"
    setup_content = setup_file.read_text()

    # Should escape quotes and remove newlines
    assert '\\"' in setup_content or "bundle with newlines" in setup_content


# =============================================================================
# pyproject.toml Writing Tests
# =============================================================================


def test_write_pyproject_toml(base_packager, sample_bundle, temp_package_dir):
    """Test that pyproject.toml is written correctly."""
    base_packager.create_directory_structure(temp_package_dir)
    base_packager.write_pyproject_toml(sample_bundle, temp_package_dir)

    pyproject_file = temp_package_dir / "pyproject.toml"
    assert pyproject_file.exists()

    pyproject_content = pyproject_file.read_text()
    assert "[build-system]" in pyproject_content
    assert "[project]" in pyproject_content
    assert f'name = "{sample_bundle.name}"' in pyproject_content
    assert f'version = "{sample_bundle.version}"' in pyproject_content
    assert 'requires-python = ">=3.11"' in pyproject_content


def test_write_pyproject_toml_special_chars_in_description(
    base_packager, sample_bundle, temp_package_dir
):
    """Test pyproject.toml with special characters in description."""
    sample_bundle.description = 'Test "bundle" with\nnewlines'

    base_packager.create_directory_structure(temp_package_dir)
    base_packager.write_pyproject_toml(sample_bundle, temp_package_dir)

    pyproject_file = temp_package_dir / "pyproject.toml"
    pyproject_content = pyproject_file.read_text()

    # Should escape quotes and remove newlines
    assert "bundle with newlines" in pyproject_content or '\\"' in pyproject_content


# =============================================================================
# Integration Tests
# =============================================================================


def test_write_all_common_files(base_packager, sample_bundle, temp_package_dir):
    """Test that all common files are written correctly."""
    base_packager.write_all_common_files(sample_bundle, temp_package_dir)

    # Verify directory structure
    assert temp_package_dir.exists()
    assert (temp_package_dir / "agents").exists()
    assert (temp_package_dir / "tests").exists()
    assert (temp_package_dir / "docs").exists()
    assert (temp_package_dir / "config").exists()

    # Verify files
    assert (temp_package_dir / "agents" / "test_agent.md").exists()
    assert (temp_package_dir / "tests" / "__init__.py").exists()
    assert (temp_package_dir / "tests" / "test_test_agent.py").exists()
    assert (temp_package_dir / "docs" / "test_agent_docs.md").exists()
    assert (temp_package_dir / "config" / "bundle_config.json").exists()
    assert (temp_package_dir / "manifest.json").exists()
    assert (temp_package_dir / "README.md").exists()
    assert (temp_package_dir / "__init__.py").exists()
    assert (temp_package_dir / "setup.py").exists()
    assert (temp_package_dir / "pyproject.toml").exists()


def test_write_all_common_files_minimal_bundle(base_packager, temp_package_dir):
    """Test with minimal bundle (no tests, no docs)."""
    minimal_agent = GeneratedAgent(
        id=uuid4(),
        name="minimal_agent",
        type="specialized",
        role="Minimal agent",
        description="Minimal test",
        content="""# Minimal Agent

This is a minimal agent with just basic content for testing minimal bundle generation.
It has no tests or documentation, just the core agent definition.""",
        capabilities=[],
        dependencies=[],
    )

    minimal_bundle = AgentBundle(
        id=uuid4(),
        name="minimal-bundle",
        version="1.0.0",
        description="Minimal bundle",
        agents=[minimal_agent],
        manifest={"bundle": {}, "agents": []},
        metadata={},
        status="ready",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    base_packager.write_all_common_files(minimal_bundle, temp_package_dir)

    # Should still create all structure
    assert temp_package_dir.exists()
    assert (temp_package_dir / "agents" / "minimal_agent.md").exists()
    assert (temp_package_dir / "manifest.json").exists()
    assert (temp_package_dir / "README.md").exists()


# =============================================================================
# Edge Case Tests
# =============================================================================


def test_write_agent_with_special_chars_in_name(base_packager, sample_bundle, temp_package_dir):
    """Test agent with unusual but valid characters in name."""
    sample_bundle.agents[0].name = "test-agent_v2"

    base_packager.create_directory_structure(temp_package_dir)
    base_packager.write_agents(sample_bundle, temp_package_dir)

    assert (temp_package_dir / "agents" / "test-agent_v2.md").exists()


def test_empty_metadata(base_packager, sample_bundle, temp_package_dir):
    """Test with empty metadata."""
    sample_bundle.metadata = {}

    base_packager.create_directory_structure(temp_package_dir)
    base_packager.write_configuration(sample_bundle, temp_package_dir)

    config_file = temp_package_dir / "config" / "bundle_config.json"
    config = json.loads(config_file.read_text())
    assert config["preferences"] == {}
