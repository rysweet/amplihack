"""File operation utilities - Batch 257"""

import shutil
from pathlib import Path
from typing import List, Optional

def safe_copy(src: Path, dst: Path, backup: bool = True) -> bool:
    """Safely copy file with optional backup.

    Args:
        src: Source file path
        dst: Destination file path
        backup: Whether to backup existing destination

    Returns:
        True if successful, False otherwise
    """
    try:
        if not src.exists():
            print(f"Source file does not exist: {src}")
            return False

        if dst.exists() and backup:
            backup_path = dst.with_suffix(dst.suffix + '.bak')
            shutil.copy2(dst, backup_path)
            print(f"Created backup: {backup_path}")

        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return True
    except Exception as e:
        print(f"Copy failed: {e}")
        return False

def find_files(directory: Path, pattern: str, recursive: bool = True) -> List[Path]:
    """Find files matching pattern.

    Args:
        directory: Directory to search
        pattern: Glob pattern to match
        recursive: Whether to search recursively

    Returns:
        List of matching file paths
    """
    if recursive:
        return list(directory.rglob(pattern))
    else:
        return list(directory.glob(pattern))
