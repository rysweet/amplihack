"""Setup script for amplihack-memory-lib."""

from setuptools import find_packages, setup

setup(
    name="amplihack-memory-lib",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.10",
    install_requires=[
        "kuzu>=0.3.0",
    ],
)
