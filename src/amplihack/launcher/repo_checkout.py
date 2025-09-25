"""Simple GitHub repository checkout for Claude launcher."""

import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


def parse_github_uri(uri: str) -> str:
    """Convert any GitHub URI format to owner/repo.

    Args:
        uri: GitHub URI in any supported format

    Returns:
        owner/repo string
    """
    if not uri:
        raise ValueError("Empty GitHub URI")

    # Already in owner/repo format
    if re.match(r"^[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+$", uri):
        return uri

    # Extract from HTTPS URL
    https_match = re.match(
        r"https://github\.com/([a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+?)(?:\.git)?$", uri
    )
    if https_match:
        return https_match.group(1)

    # Extract from SSH URL
    ssh_match = re.match(r"git@github\.com:([a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+?)(?:\.git)?$", uri)
    if ssh_match:
        return ssh_match.group(1)

    raise ValueError(f"Invalid GitHub URI: {uri}")


def checkout_repository(repo_uri: str, base_dir: Optional[Path] = None) -> Optional[Path]:
    """Checkout a GitHub repository.

    Args:
        repo_uri: GitHub repository URI
        base_dir: Base directory for cloning

    Returns:
        Path to cloned repository or None if failed
    """
    try:
        owner_repo = parse_github_uri(repo_uri)
        repo_name = owner_repo.split("/")[1]

        if base_dir is None:
            base_dir = Path(tempfile.gettempdir()) / "claude-checkouts"
        base_dir.mkdir(parents=True, exist_ok=True)

        target_dir = base_dir / repo_name

        # Use existing if valid
        if target_dir.exists() and (target_dir / ".git").exists():
            print(f"Using existing repository: {target_dir}")
            return target_dir

        # Remove invalid directory
        if target_dir.exists():
            import shutil

            shutil.rmtree(target_dir)

        clone_url = f"https://github.com/{owner_repo}.git"

        result = subprocess.run(
            ["git", "clone", clone_url, str(target_dir)], capture_output=True, text=True
        )

        if result.returncode == 0:
            print(f"Cloned repository to: {target_dir}")
            return target_dir

        print(f"Clone failed: {result.stderr}")
        return None

    except Exception as e:
        print(f"Checkout error: {e}")
        return None
