"""
Python packaging template generators.

Shared functions for generating setup.py and pyproject.toml files
for agent bundles. Eliminates duplication across packager and filesystem_packager.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import AgentBundle


def generate_pyproject_toml(bundle: "AgentBundle") -> str:
    """
    Generate pyproject.toml content for an agent bundle.

    Args:
        bundle: AgentBundle to generate pyproject.toml for

    Returns:
        Complete pyproject.toml file content as string
    """
    # Sanitize description for TOML (single line, no newlines)
    description_sanitized = bundle.description.replace("\n", " ").replace('"', '\\"').strip()

    return f"""[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "{bundle.name}"
version = "{bundle.version}"
description = "{description_sanitized}"
readme = "README.md"
requires-python = ">=3.11"
license = {{text = "MIT"}}
authors = [
    {{name = "Agent Bundle Generator"}},
]
keywords = ["amplihack", "agents", "ai", "automation"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]

dependencies = [
    "amplihack>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "black>=23.0",
    "ruff>=0.1.0",
]

[project.entry-points."amplihack.bundles"]
{bundle.name} = "{bundle.name}:load"

[tool.setuptools.packages.find]
where = ["."]
include = ["{bundle.name}*", "agents*", "config*"]

[tool.setuptools.package-data]
"*" = ["*.md", "*.json", "*.yaml"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_functions = "test_*"

[tool.black]
line-length = 100
target-version = ['py311']

[tool.ruff]
line-length = 100
target-version = "py311"
"""


def generate_setup_py(bundle: "AgentBundle") -> str:
    """
    Generate setup.py content for an agent bundle.

    Args:
        bundle: AgentBundle to generate setup.py for

    Returns:
        Complete setup.py file content as string
    """
    # Sanitize description for Python string (escape quotes, single line)
    description_sanitized = bundle.description.replace("\n", " ").replace('"', '\\"').strip()

    return f'''"""Setup script for {bundle.name}."""

from setuptools import setup, find_packages

setup(
    name="{bundle.name}",
    version="{bundle.version}",
    description="{description_sanitized}",
    author="Agent Bundle Generator",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "amplihack>=1.0.0",
    ],
    package_data={{
        "": ["*.json", "*.md", "*.yaml"],
        "agents": ["*.md"],
        "tests": ["*.py"],
        "docs": ["*.md"],
        "config": ["*.json"],
    }},
    entry_points={{
        "amplihack.bundles": [
            "{bundle.name} = {bundle.name}:load",
        ],
    }},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.11",
    ],
)
'''
