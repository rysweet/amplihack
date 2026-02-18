"""Setup configuration for parallel-task-orchestrator skill.

Allows importing as a package: from parallel_task_orchestrator import ...
"""

from setuptools import setup, find_packages

setup(
    name="parallel-task-orchestrator",
    version="0.1.0",
    description="Parallel task orchestration for GitHub issues",
    packages=find_packages(where="."),
    package_dir={"": "."},
    python_requires=">=3.8",
    install_requires=[
        "pytest>=7.0.0",
        "pytest-cov>=4.0.0",
    ],
)
