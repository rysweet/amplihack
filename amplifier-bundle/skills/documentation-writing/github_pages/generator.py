"""Site generator for GitHub Pages documentation.

Generates MkDocs documentation sites with Material theme from docs/ directory,
README.md, and command help text.

Philosophy:
- Single responsibility: Generate documentation site
- Discover content from multiple sources (docs/, README, commands)
- Build with MkDocs
- Graceful error handling with clear messages
"""

import subprocess
from pathlib import Path

from . import GenerationResult, SiteConfig
from .mkdocs_config import (
    build_mkdocs_config,
    write_mkdocs_yaml,
)


def generate_site(config: SiteConfig) -> GenerationResult:
    """Generate documentation site using MkDocs.

    Args:
        config: Site configuration

    Returns:
        GenerationResult with success status and details

    Raises:
        FileNotFoundError: If docs_dir doesn't exist
        PermissionError: If unable to write to output directory
        subprocess.CalledProcessError: If mkdocs build fails
    """
    if config is None:
        raise TypeError("Config cannot be None")

    docs_path = Path(config.docs_dir)
    output_path = Path(config.output_dir)
    project_root = docs_path.parent

    # Verify docs directory exists
    if not docs_path.exists():
        raise FileNotFoundError(f"Documentation directory not found: {config.docs_dir}")

    errors: list[str] = []
    warnings: list[str] = []

    # Discover content
    content_files = discover_content(docs_path)

    if not content_files:
        warnings.append("No markdown files found in docs directory")

    # Check for README to potentially include
    readme = discover_readme(project_root)
    if readme:
        # If no index.md exists, create one from README
        index_path = docs_path / "index.md"
        if not index_path.exists():
            try:
                readme_content = readme.read_text()
                index_path.write_text(readme_content)
                content_files.insert(0, index_path)
            except Exception as e:
                warnings.append(f"Could not copy README to index.md: {e}")
    else:
        if not (docs_path / "index.md").exists():
            warnings.append("No README.md or index.md found")

    # Discover commands for reference documentation
    commands = discover_commands()
    if commands:
        _generate_command_reference(docs_path, commands)
        # Refresh content list
        content_files = discover_content(docs_path)

    # Build MkDocs configuration
    mkdocs_config = build_mkdocs_config(
        project_name=config.project_name,
        project_url=config.project_url,
        docs_dir=str(docs_path),
        theme_features=config.theme_features,
        nav_structure=config.nav_structure,
    )

    # Write mkdocs.yml to project root
    config_path = project_root / "mkdocs.yml"
    write_mkdocs_yaml(mkdocs_config, config_path)

    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)

    # Build site with MkDocs
    try:
        result = subprocess.run(
            ["mkdocs", "build", "--site-dir", str(output_path)],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            errors.append(f"MkDocs build failed: {result.stderr}")
            return GenerationResult(
                success=False,
                site_dir=output_path,
                pages=[],
                errors=errors,
                warnings=warnings,
                config_file=config_path,
            )

        # Collect generated pages
        pages = _collect_generated_pages(output_path)

        return GenerationResult(
            success=True,
            site_dir=output_path,
            pages=pages,
            errors=errors,
            warnings=warnings,
            config_file=config_path,
        )

    except FileNotFoundError:
        raise FileNotFoundError(
            "MkDocs not found. Install with: pip install mkdocs mkdocs-material"
        )
    except subprocess.TimeoutExpired:
        errors.append("MkDocs build timed out after 120 seconds")
        return GenerationResult(
            success=False,
            site_dir=output_path,
            pages=[],
            errors=errors,
            warnings=warnings,
            config_file=config_path,
        )


def preview_locally(config_path: Path | str = "mkdocs.yml", port: int = 8000) -> None:
    """Start local preview server for documentation site.

    Args:
        config_path: Path to mkdocs.yml configuration
        port: Port to serve on (default: 8000)

    Note:
        This function blocks until the server is stopped (Ctrl+C).
    """
    config_path = Path(config_path)
    project_root = config_path.parent

    subprocess.run(
        ["mkdocs", "serve", "--dev-addr", f"127.0.0.1:{port}"],
        cwd=str(project_root),
    )


def discover_content(docs_dir: Path) -> list[Path]:
    """Discover markdown content in documentation directory.

    Args:
        docs_dir: Path to docs directory

    Returns:
        List of markdown file paths (sorted)
    """
    if not docs_dir.exists():
        return []

    # Find all markdown files
    md_files = list(docs_dir.rglob("*.md"))

    # Filter to only markdown files (exclude other file types)
    md_files = [f for f in md_files if f.suffix.lower() == ".md"]

    # Sort with index.md first, then alphabetically
    def sort_key(path: Path) -> tuple[int, str]:
        if path.name.lower() == "index.md":
            return (0, str(path))
        return (1, str(path))

    return sorted(md_files, key=sort_key)


def discover_readme(project_root: Path) -> Path | None:
    """Discover README.md in project root.

    Args:
        project_root: Path to project root directory

    Returns:
        Path to README.md if it exists, None otherwise
    """
    readme_names = ["README.md", "readme.md", "Readme.md", "README.MD"]

    for name in readme_names:
        readme_path = project_root / name
        if readme_path.exists():
            return readme_path

    return None


def discover_commands() -> dict[str, str]:
    """Discover command help text from CLI.

    Returns:
        Dictionary mapping command names to help text
    """
    commands: dict[str, str] = {}

    # Try to discover amplihack commands
    try:
        result = subprocess.run(
            ["amplihack", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            commands["amplihack"] = result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass  # No amplihack CLI available

    return commands


def _generate_command_reference(docs_dir: Path, commands: dict[str, str]) -> None:
    """Generate command reference documentation.

    Args:
        docs_dir: Path to docs directory
        commands: Dictionary of command names to help text
    """
    if not commands:
        return

    reference_dir = docs_dir / "reference"
    reference_dir.mkdir(exist_ok=True)

    cli_doc = reference_dir / "cli.md"

    content = "# CLI Reference\n\n"
    content += "Command-line interface reference documentation.\n\n"

    for cmd_name, help_text in commands.items():
        content += f"## {cmd_name}\n\n"
        content += "```\n"
        content += help_text
        content += "\n```\n\n"

    cli_doc.write_text(content)


def _collect_generated_pages(site_dir: Path) -> list[str]:
    """Collect list of generated HTML pages.

    Args:
        site_dir: Path to generated site directory

    Returns:
        List of relative paths to HTML pages
    """
    if not site_dir.exists():
        return []

    pages = []
    for html_file in site_dir.rglob("*.html"):
        rel_path = html_file.relative_to(site_dir)
        pages.append(str(rel_path))

    return sorted(pages)
