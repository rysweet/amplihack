"""MkDocs configuration builder for GitHub Pages.

Generates mkdocs.yml configuration with Material theme for GitHub Pages deployment.

Philosophy:
- Single responsibility: Build and write MkDocs configuration
- Standard YAML output compatible with MkDocs
- Material theme with sensible defaults
- Auto-generate navigation from docs/ structure
"""

from pathlib import Path
from typing import Any


def _validate_github_url(url: str) -> None:
    """Validate GitHub repository URL for security.

    Args:
        url: GitHub URL to validate

    Raises:
        ValueError: If URL is invalid or potentially dangerous
    """
    if not url:
        raise ValueError("GitHub URL cannot be empty")

    # Check for dangerous characters that could be used for injection
    dangerous_chars = [";", "&", "|", "`", "$", "(", ")", "<", ">", "\n", "\r", " "]
    for char in dangerous_chars:
        if char in url:
            raise ValueError(f"GitHub URL contains invalid character: {char}")

    # Validate URL format (must be GitHub)
    valid_prefixes = [
        "https://github.com/",
        "git@github.com:",
        "http://github.com/",  # Will be upgraded to HTTPS
    ]

    if not any(url.startswith(prefix) for prefix in valid_prefixes):
        raise ValueError(
            f"URL must be a valid GitHub URL (https://github.com/... or git@github.com:...): {url}"
        )


def build_mkdocs_config(
    project_name: str,
    project_url: str,
    docs_dir: str | Path = "docs",
    theme_features: list[str] | None = None,
    nav_structure: dict | list | None = None,
) -> dict[str, Any]:
    """Build complete MkDocs configuration dictionary.

    Args:
        project_name: Name of the project (used in site title)
        project_url: GitHub repository URL
        docs_dir: Path to documentation directory
        theme_features: List of Material theme features to enable
        nav_structure: Custom navigation (auto-generated if None)

    Returns:
        Dictionary ready to be written as mkdocs.yml

    Raises:
        ValueError: If project_url is invalid
    """
    _validate_github_url(project_url)
    docs_path = Path(docs_dir)

    # Build site URL from repo URL
    site_url = _construct_site_url(project_url)

    # Build theme configuration
    theme_config = build_material_theme_config(features=theme_features)

    # Build navigation
    if nav_structure is not None:
        nav = nav_structure
    else:
        # Auto-generate navigation from docs structure
        if docs_path.exists():
            md_files = list(docs_path.rglob("*.md"))
            nav = generate_nav_structure(md_files)
        else:
            nav = [{"Home": "index.md"}]

    config = {
        "site_name": project_name,
        "site_url": site_url,
        "repo_url": project_url,
        "repo_name": _extract_repo_name(project_url),
        "edit_uri": "edit/main/docs/",
        "theme": theme_config,
        "plugins": ["search"],
        "nav": nav,
        "markdown_extensions": [
            "pymdownx.highlight",
            "pymdownx.superfences",
            "pymdownx.tabbed",
            "admonition",
            "toc",
        ],
    }

    return config


def build_material_theme_config(
    features: list[str] | None = None,
) -> dict[str, Any]:
    """Build Material theme configuration.

    Args:
        features: List of Material theme features to enable

    Returns:
        Theme configuration dictionary
    """
    default_features = [
        "navigation.tabs",
        "navigation.sections",
        "navigation.expand",
        "search.highlight",
        "search.suggest",
        "content.code.copy",
    ]

    theme_config = {
        "name": "material",
        "features": features if features is not None else default_features,
        "palette": {
            "primary": "indigo",
            "accent": "indigo",
        },
        "icon": {
            "repo": "fontawesome/brands/github",
        },
    }

    return theme_config


def generate_nav_structure(files: list[Path]) -> list[dict[str, Any]]:
    """Generate navigation structure from documentation files.

    Args:
        files: List of markdown file paths

    Returns:
        Navigation structure as list of dicts for mkdocs.yml
    """
    if not files:
        return [{"Home": "index.md"}]

    # Group files by directory
    sections: dict[str, list[tuple[str, str]]] = {}
    root_files: list[tuple[str, str]] = []

    for file_path in files:
        # Get relative path from docs directory
        parts = file_path.parts
        # Find 'docs' in path and get relative path after it
        try:
            docs_idx = parts.index("docs")
            rel_parts = parts[docs_idx + 1 :]
        except ValueError:
            rel_parts = parts

        if len(rel_parts) == 1:
            # Root level file
            filename = rel_parts[0]
            name = _format_page_name(filename)
            root_files.append((name, filename))
        else:
            # File in subdirectory
            section = rel_parts[0]
            section_name = _format_section_name(section)
            filename = str(Path(*rel_parts))

            if section_name not in sections:
                sections[section_name] = []

            page_name = _format_page_name(rel_parts[-1])
            sections[section_name].append((page_name, filename))

    # Build navigation list
    nav: list[dict[str, Any]] = []

    # Add Home first if index.md exists
    home_files = [(name, path) for name, path in root_files if "index" in path.lower()]
    if home_files:
        nav.append({"Home": home_files[0][1]})
        root_files = [(n, p) for n, p in root_files if "index" not in p.lower()]

    # Add remaining root files
    for name, path in root_files:
        nav.append({name: path})

    # Add sections in Diataxis order if they exist
    diataxis_order = ["Tutorials", "How-To", "Reference", "Concepts"]
    added_sections = set()

    for section_name in diataxis_order:
        if section_name in sections:
            section_items = [{name: path} for name, path in sections[section_name]]
            nav.append({section_name: section_items})
            added_sections.add(section_name)

    # Add remaining sections alphabetically
    for section_name in sorted(sections.keys()):
        if section_name not in added_sections:
            section_items = [{name: path} for name, path in sections[section_name]]
            nav.append({section_name: section_items})

    return nav if nav else [{"Home": "index.md"}]


def write_mkdocs_yaml(config: dict[str, Any], output_path: Path) -> Path:
    """Write MkDocs configuration to YAML file.

    Args:
        config: Configuration dictionary
        output_path: Path to write mkdocs.yml

    Returns:
        Path to written file
    """
    import yaml

    yaml_content = yaml.dump(
        config,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        indent=2,
    )

    output_path.write_text(yaml_content)
    return output_path


def validate_config(config: dict[str, Any]) -> None:
    """Validate MkDocs configuration.

    Args:
        config: Configuration dictionary to validate

    Raises:
        ValueError: If configuration is invalid
    """
    if "site_name" not in config:
        raise ValueError("Configuration missing required field: site_name")

    if "theme" not in config:
        raise ValueError("Configuration missing required field: theme")

    if config["theme"].get("name") != "material":
        raise ValueError("Theme must be 'material' for GitHub Pages generation")


def _format_section_name(section: str) -> str:
    """Format directory name as section title.

    Args:
        section: Directory name (e.g., "api-reference", "howto")

    Returns:
        Formatted section name (e.g., "API Reference", "How-To")
    """
    # Handle special cases
    special_cases = {
        "api": "API",
        "api-reference": "API Reference",
        "howto": "How-To",
        "how-to": "How-To",
        "cli": "CLI",
    }

    lower_section = section.lower()
    if lower_section in special_cases:
        return special_cases[lower_section]

    # General formatting: replace dashes/underscores, title case
    formatted = section.replace("-", " ").replace("_", " ")
    return formatted.title()


def _format_page_name(filename: str) -> str:
    """Format filename as page title.

    Args:
        filename: Markdown filename (e.g., "getting-started.md")

    Returns:
        Formatted page name (e.g., "Getting Started")
    """
    # Remove .md extension
    name = filename.replace(".md", "")

    # Handle special cases
    if name.lower() == "index":
        return "Home"

    # General formatting
    formatted = name.replace("-", " ").replace("_", " ")
    return formatted.title()


def _extract_repo_info(repo_url: str) -> tuple[str, str]:
    """Extract owner and repository name from GitHub URL.

    Args:
        repo_url: GitHub repository URL

    Returns:
        Tuple of (owner, repo_name)

    Raises:
        ValueError: If URL is invalid
    """
    _validate_github_url(repo_url)

    # Handle both HTTPS and SSH formats
    # https://github.com/owner/repo
    # git@github.com:owner/repo.git

    url = repo_url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]

    if "github.com/" in url:
        parts = url.split("github.com/")[-1].split("/")
    elif "github.com:" in url:
        parts = url.split("github.com:")[-1].split("/")
    else:
        parts = url.split("/")[-2:]

    owner = parts[0] if len(parts) > 0 else "unknown"
    repo = parts[1] if len(parts) > 1 else "unknown"

    return owner, repo


def _extract_repo_name(repo_url: str) -> str:
    """Extract repository name from URL for display.

    Args:
        repo_url: GitHub repository URL

    Returns:
        Repository name in owner/repo format
    """
    owner, repo = _extract_repo_info(repo_url)
    return f"{owner}/{repo}"


def _construct_site_url(repo_url: str) -> str:
    """Construct GitHub Pages URL from repository URL.

    Args:
        repo_url: GitHub repository URL

    Returns:
        GitHub Pages URL
    """
    owner, repo = _extract_repo_info(repo_url)
    return f"https://{owner}.github.io/{repo}/"
