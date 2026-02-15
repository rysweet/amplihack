"""
Setup script for Documentation Analyzer Agent
"""

from setuptools import find_packages, setup

setup(
    name="doc-analyzer",
    version="0.1.0",
    description="Learning agent for analyzing documentation quality",
    author="Amplihack",
    packages=find_packages(exclude=["tests", "tests.*"]),
    install_requires=[
        "amplihack-memory-lib>=0.1.0",
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "markdown>=3.5.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "doc-analyzer=cli:main",
        ],
    },
    python_requires=">=3.8",
)
