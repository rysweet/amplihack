#!/usr/bin/env python3
"""Verify skill dependencies are installed.

This utility checks that all required and optional dependencies for Office skills
are properly installed and available.

Usage:
    python verify_skill.py <skill>    # Verify specific skill
    python verify_skill.py all        # Verify all skills

Examples:
    python verify_skill.py pdf
    python verify_skill.py xlsx
    python verify_skill.py all
"""

import importlib
import subprocess
import sys
from typing import List, Tuple


def check_python_package(package: str) -> Tuple[bool, str]:
    """Check if Python package is installed.

    Args:
        package: Name of the Python package to check

    Returns:
        Tuple of (is_installed, status_message)
    """
    try:
        mod = importlib.import_module(package)
        version = getattr(mod, "__version__", "unknown")
        return True, f"Installed (v{version})"
    except ImportError:
        return False, "Not installed"


def check_system_command(command: str) -> Tuple[bool, str]:
    """Check if system command is available.

    Args:
        command: Name of the system command to check

    Returns:
        Tuple of (is_available, status_message)
    """
    try:
        result = subprocess.run(
            [command, "--version"],
            capture_output=True,
            check=True,
            timeout=5,
        )
        # Try to extract version from output
        output = result.stdout.decode("utf-8", errors="ignore").split("\n")[0]
        return True, f"Available ({output[:50]}...)" if len(
            output
        ) > 50 else f"Available ({output})"
    except subprocess.TimeoutExpired:
        return False, "Timeout (command hung)"
    except subprocess.CalledProcessError:
        return False, "Error running command"
    except FileNotFoundError:
        return False, "Not found"
    except Exception as e:
        return False, f"Error: {str(e)[:30]}"


def verify_skill(
    skill_name: str,
    python_packages_required: List[str],
    python_packages_optional: List[str],
    system_commands_optional: List[str],
) -> bool:
    """Verify all dependencies for a skill.

    Args:
        skill_name: Name of the skill
        python_packages_required: List of required Python packages
        python_packages_optional: List of optional Python packages
        system_commands_optional: List of optional system commands

    Returns:
        True if all required dependencies are met, False otherwise
    """
    print(f"Verifying {skill_name} skill dependencies...")
    print("=" * 70)

    all_required_ok = True

    # Check required Python packages
    if python_packages_required:
        print("\nRequired Python packages:")
        for package in python_packages_required:
            ok, status = check_python_package(package)
            symbol = "✓" if ok else "✗"
            print(f"  {symbol} {package:20s}: {status}")
            if not ok:
                all_required_ok = False

    # Check optional Python packages
    if python_packages_optional:
        print("\nOptional Python packages:")
        for package in python_packages_optional:
            ok, status = check_python_package(package)
            symbol = "✓" if ok else "○"
            print(f"  {symbol} {package:20s}: {status}")

    # Check optional system commands
    if system_commands_optional:
        print("\nOptional system commands:")
        for command in system_commands_optional:
            ok, status = check_system_command(command)
            symbol = "✓" if ok else "○"
            print(f"  {symbol} {command:20s}: {status}")

    # Summary
    print("\n" + "=" * 70)
    if all_required_ok:
        print(f"✓ {skill_name} skill is ready (all required dependencies met)")
    else:
        print(f"✗ {skill_name} skill is missing required dependencies")
        print("\nInstall missing packages:")
        missing = [pkg for pkg in python_packages_required if not check_python_package(pkg)[0]]
        if missing:
            print(f"  pip install {' '.join(missing)}")

    # Optional features summary
    optional_available = sum(1 for pkg in python_packages_optional if check_python_package(pkg)[0])
    optional_total = len(python_packages_optional)

    system_available = sum(1 for cmd in system_commands_optional if check_system_command(cmd)[0])
    system_total = len(system_commands_optional)

    if optional_total > 0 or system_total > 0:
        print("\nOptional features:")
        if optional_total > 0:
            print(f"  Python packages: {optional_available}/{optional_total} available")
        if system_total > 0:
            print(f"  System commands: {system_available}/{system_total} available")

    print("=" * 70 + "\n")

    return all_required_ok


# Define skill dependencies
SKILLS = {
    "pdf": {
        "python_required": ["pypdf", "pdfplumber", "reportlab", "pandas"],
        "python_optional": ["pytesseract", "pdf2image", "pillow"],
        "system_optional": ["pdftotext", "qpdf", "pdftk", "tesseract"],
    },
    "xlsx": {
        "python_required": ["pandas", "openpyxl"],
        "python_optional": [],
        "system_optional": ["soffice"],  # LibreOffice
    },
    "docx": {
        "python_required": ["defusedxml"],
        "python_optional": [],
        "system_optional": ["pandoc", "soffice", "pdftoppm"],
    },
    "pptx": {
        "python_required": ["markitdown", "defusedxml"],
        "python_optional": [],
        "system_optional": ["node", "soffice"],
    },
}


def main():
    """Main entry point for verification script."""
    if len(sys.argv) < 2:
        print("Usage: python verify_skill.py <skill|all>")
        print("\nAvailable skills:")
        for skill in SKILLS.keys():
            print(f"  - {skill}")
        print("\nOr use 'all' to verify all skills")
        sys.exit(1)

    skill = sys.argv[1].lower()

    if skill == "all":
        results = {}
        for skill_name, deps in SKILLS.items():
            ok = verify_skill(
                skill_name,
                deps["python_required"],
                deps["python_optional"],
                deps["system_optional"],
            )
            results[skill_name] = ok

        # Summary
        print("\n" + "=" * 70)
        print("OVERALL SUMMARY")
        print("=" * 70)
        for skill_name, ok in results.items():
            symbol = "✓" if ok else "✗"
            status = "Ready" if ok else "Missing dependencies"
            print(f"  {symbol} {skill_name:10s}: {status}")
        print("=" * 70)

        all_ok = all(results.values())
        sys.exit(0 if all_ok else 1)

    elif skill in SKILLS:
        deps = SKILLS[skill]
        ok = verify_skill(
            skill,
            deps["python_required"],
            deps["python_optional"],
            deps["system_optional"],
        )
        sys.exit(0 if ok else 1)

    else:
        print(f"Error: Unknown skill '{skill}'")
        print("\nAvailable skills:")
        for skill_name in SKILLS.keys():
            print(f"  - {skill_name}")
        sys.exit(1)


if __name__ == "__main__":
    main()
