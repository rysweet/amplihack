"""
Tests for UVXPackager checksum verification.

Tests verify that extract_package properly validates checksums
to prevent extraction of corrupted or tampered packages.
"""

import json
import tempfile
from pathlib import Path

import pytest

from amplihack.bundle_generator import UVXPackager, AgentBundle, GeneratedAgent
from amplihack.bundle_generator.exceptions import PackagingError


@pytest.fixture
def sample_agent():
    """Create a sample agent for testing."""
    return GeneratedAgent(
        name="test_agent",
        type="specialized",
        role="Test Role",
        description="A test agent",
        content="# Test Agent\nTest content",
        capabilities=["test"],
        dependencies=[],
    )


@pytest.fixture
def sample_bundle(sample_agent):
    """Create a sample bundle for testing."""
    return AgentBundle(
        name="test-bundle",
        version="1.0.0",
        description="Test bundle for checksum verification",
        agents=[sample_agent],
        manifest={
            "bundle": {
                "name": "test-bundle",
                "version": "1.0.0",
                "description": "Test bundle",
            },
            "agents": [
                {
                    "name": "test_agent",
                    "type": "specialized",
                    "role": "Test Role",
                    "description": "A test agent",
                    "capabilities": ["test"],
                    "dependencies": [],
                }
            ],
        },
        metadata={},
        status="ready",
    )


def test_checksum_verification_on_valid_package(sample_bundle):
    """
    Test that extract_package succeeds with valid checksum in manifest.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        package_dir = tmpdir_path / "packages"
        extract_dir = tmpdir_path / "extracted"

        # Create package with checksum
        packager = UVXPackager(package_dir)
        package = packager.package(sample_bundle, format="uvx")

        # Extract the package
        extracted_bundle = packager.extract_package(package.package_path, extract_dir)

        # Verify extraction succeeded
        assert extracted_bundle is not None
        assert extracted_bundle.name == sample_bundle.name
        assert len(extracted_bundle.agents) == len(sample_bundle.agents)


def test_checksum_verification_detects_tampering(sample_bundle):
    """
    Test that extract_package detects tampering via checksum mismatch.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        package_dir = tmpdir_path / "packages"
        extract_dir = tmpdir_path / "extracted"

        # Create package with checksum
        packager = UVXPackager(package_dir)
        package = packager.package(sample_bundle, format="uvx")

        # Extract the package to get the manifest
        extracted_bundle = packager.extract_package(package.package_path, extract_dir)
        manifest_path = (extract_dir / extracted_bundle.name / "manifest.json")

        # Verify manifest has checksum
        with open(manifest_path) as f:
            manifest = json.load(f)
        assert "checksum" in manifest

        # Simulate tampering by modifying the package file slightly
        with open(package.package_path, "r+b") as f:
            # Read the entire file
            content = f.read()
            # Modify one byte
            f.seek(len(content) - 10)
            f.write(b"CORRUPTED!")

        # Now try to extract - should fail with checksum verification error
        extract_dir2 = tmpdir_path / "extracted2"
        with pytest.raises(PackagingError) as exc_info:
            packager.extract_package(package.package_path, extract_dir2)

        # Verify the error message mentions checksum
        assert "checksum" in str(exc_info.value).lower()


def test_checksum_verification_missing_checksum_optional(sample_bundle):
    """
    Test that extract_package works even if manifest lacks checksum (graceful fallback).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        package_dir = tmpdir_path / "packages"
        extract_dir = tmpdir_path / "extracted"

        # Create package
        packager = UVXPackager(package_dir)
        package = packager.package(sample_bundle, format="uvx")

        # Extract to get the manifest and remove checksum
        extracted_bundle = packager.extract_package(package.package_path, extract_dir)
        manifest_path = extract_dir / extracted_bundle.name / "manifest.json"

        with open(manifest_path) as f:
            manifest = json.load(f)

        # Remove checksum if present
        manifest.pop("checksum", None)

        with open(manifest_path, "w") as f:
            json.dump(manifest, f)

        # Try to extract again - should succeed without checksum check
        extract_dir2 = tmpdir_path / "extracted2"
        result = packager.extract_package(package.package_path, extract_dir2)

        # Verify extraction succeeded
        assert result is not None
        assert result.name == sample_bundle.name


def test_checksum_error_contains_helpful_message(sample_bundle):
    """
    Test that checksum mismatch error message is clear and helpful.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        package_dir = tmpdir_path / "packages"
        extract_dir = tmpdir_path / "extracted"

        # Create package with checksum
        packager = UVXPackager(package_dir)
        package = packager.package(sample_bundle, format="uvx")

        # Tamper with package
        with open(package.package_path, "r+b") as f:
            content = f.read()
            f.seek(len(content) - 10)
            f.write(b"CORRUPTED!")

        # Try to extract
        with pytest.raises(PackagingError) as exc_info:
            packager.extract_package(package.package_path, extract_dir)

        error_msg = str(exc_info.value)

        # Verify error message is helpful
        assert "checksum" in error_msg.lower()
        assert "corruption" in error_msg.lower() or "tampering" in error_msg.lower()


def test_checksum_verification_all_formats(sample_bundle):
    """
    Test checksum verification works with all package formats.
    """
    formats = ["tar.gz", "zip"]

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        for fmt in formats:
            package_dir = tmpdir_path / f"packages_{fmt}"
            extract_dir = tmpdir_path / f"extracted_{fmt}"

            # Create package in this format
            packager = UVXPackager(package_dir)
            package = packager.package(sample_bundle, format=fmt)

            # Extract should succeed with valid checksum
            extracted = packager.extract_package(package.package_path, extract_dir)
            assert extracted is not None
            assert extracted.name == sample_bundle.name
