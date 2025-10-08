"""Defensive file I/O utilities with retry logic and error handling."""

import hashlib
import json
import logging
import os
import shutil
import tempfile
import time
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class FileOperationError(Exception):
    """Base exception for file operation errors."""


class RetryExhaustedError(FileOperationError):
    """Raised when retry attempts are exhausted."""


class FileCorruptionError(FileOperationError):
    """Raised when file corruption is detected."""


def retry_file_operation(
    max_retries: int = 3,
    delay: float = 0.1,
    backoff: float = 2.0,
    exceptions: tuple = (OSError, IOError, PermissionError),
):
    """Decorator for retrying file operations with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay on each retry
        exceptions: Tuple of exceptions to catch and retry

    Example:
        >>> @retry_file_operation(max_retries=5, delay=0.2)
        ... def write_important_file(path, content):
        ...     with open(path, 'w') as f:
        ...         f.write(content)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        break

                    logger.warning(
                        f"File operation {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}"
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff

            raise RetryExhaustedError(
                f"File operation {func.__name__} failed after {max_retries + 1} attempts: {last_exception}"
            ) from last_exception

        return wrapper

    return decorator


@contextmanager
def file_lock(lock_file: Path, timeout: float = 30.0):
    """File-based locking context manager.

    Args:
        lock_file: Path to lock file
        timeout: Maximum time to wait for lock

    Raises:
        TimeoutError: If lock cannot be acquired within timeout
    """
    lock_acquired = False
    start_time = time.time()

    try:
        while time.time() - start_time < timeout:
            try:
                # Atomic lock creation
                lock_file.parent.mkdir(parents=True, exist_ok=True)
                fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                lock_acquired = True
                break
            except FileExistsError:
                time.sleep(0.1)

        if not lock_acquired:
            raise TimeoutError(f"Could not acquire file lock: {lock_file}")

        yield

    finally:
        if lock_acquired and lock_file.exists():
            try:
                lock_file.unlink()
            except Exception as e:
                logger.warning(f"Failed to release file lock: {e}")


def get_file_checksum(file_path: Path, algorithm: str = "md5") -> str:
    """Calculate file checksum for integrity verification.

    Args:
        file_path: Path to file
        algorithm: Hash algorithm (md5, sha1, sha256)

    Returns:
        Hexadecimal checksum string
    """
    hash_algo = hashlib.new(algorithm)

    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                hash_algo.update(chunk)
        return hash_algo.hexdigest()
    except Exception as e:
        logger.error(f"Failed to calculate checksum for {file_path}: {e}")
        return ""


@retry_file_operation(max_retries=3, delay=0.1)
def safe_read_file(
    file_path: Union[str, Path],
    encoding: str = "utf-8",
    verify_checksum: bool = False,
    expected_checksum: Optional[str] = None,
) -> Optional[str]:
    """Safely read file with error handling and optional integrity check.

    Args:
        file_path: Path to file
        encoding: File encoding
        verify_checksum: Whether to verify file integrity
        expected_checksum: Expected checksum for verification

    Returns:
        File content or None if failed

    Raises:
        FileCorruptionError: If checksum verification fails
    """
    file_path = Path(file_path)

    if not file_path.exists():
        logger.warning(f"File does not exist: {file_path}")
        return None

    try:
        # Verify checksum if requested
        if verify_checksum and expected_checksum:
            actual_checksum = get_file_checksum(file_path)
            if actual_checksum != expected_checksum:
                raise FileCorruptionError(
                    f"File checksum mismatch: expected {expected_checksum}, got {actual_checksum}"
                )

        with open(file_path, encoding=encoding) as f:
            content = f.read()

        logger.debug(f"Successfully read file: {file_path} ({len(content)} chars)")
        return content

    except Exception as e:
        logger.error(f"Failed to read file {file_path}: {e}")
        raise


@retry_file_operation(max_retries=3, delay=0.1)
def safe_write_file(
    file_path: Union[str, Path],
    content: str,
    encoding: str = "utf-8",
    mode: str = "w",
    atomic: bool = True,
    backup: bool = False,
    verify_write: bool = True,
) -> bool:
    """Safely write file with atomic operations and verification.

    Args:
        file_path: Path to file
        content: Content to write
        encoding: File encoding
        mode: Write mode ('w', 'a', etc.)
        atomic: Use atomic write (via temp file)
        backup: Create backup of existing file
        verify_write: Verify written content

    Returns:
        True if successful

    Raises:
        FileOperationError: If write operation fails
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Create backup if requested
        if backup and file_path.exists():
            backup_path = file_path.with_suffix(f"{file_path.suffix}.backup")
            shutil.copy2(file_path, backup_path)
            logger.debug(f"Created backup: {backup_path}")

        if atomic and mode == "w":
            # Atomic write using temporary file
            with tempfile.NamedTemporaryFile(
                mode=mode,
                encoding=encoding,
                dir=file_path.parent,
                prefix=f".{file_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as tmp_file:
                tmp_file.write(content)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())
                temp_path = Path(tmp_file.name)

            # Atomic move
            temp_path.replace(file_path)
        else:
            # Direct write
            with open(file_path, mode, encoding=encoding) as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())

        # Verify write if requested
        if verify_write and mode == "w":
            try:
                written_content = safe_read_file(file_path, encoding=encoding)
                if written_content != content:
                    raise FileCorruptionError("Written content does not match input")
            except Exception as e:
                logger.error(f"Write verification failed: {e}")
                raise

        logger.debug(f"Successfully wrote file: {file_path} ({len(content)} chars)")
        return True

    except Exception as e:
        logger.error(f"Failed to write file {file_path}: {e}")
        raise


@retry_file_operation(max_retries=3, delay=0.1)
def safe_read_json(
    file_path: Union[str, Path], default: Any = None, validate_schema: Optional[Callable] = None
) -> Any:
    """Safely read JSON file with validation.

    Args:
        file_path: Path to JSON file
        default: Default value if file doesn't exist or is invalid
        validate_schema: Optional function to validate JSON structure

    Returns:
        Parsed JSON data or default value
    """
    try:
        content = safe_read_file(file_path)
        if content is None:
            return default

        data = json.loads(content)

        # Validate schema if provided
        if validate_schema:
            try:
                validate_schema(data)
            except Exception as e:
                logger.error(f"JSON schema validation failed for {file_path}: {e}")
                return default

        logger.debug(f"Successfully read JSON: {file_path}")
        return data

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {file_path}: {e}")
        return default
    except Exception as e:
        logger.error(f"Failed to read JSON {file_path}: {e}")
        return default


@retry_file_operation(max_retries=3, delay=0.1)
def safe_write_json(
    file_path: Union[str, Path],
    data: Any,
    indent: int = 2,
    sort_keys: bool = True,
    atomic: bool = True,
    backup: bool = False,
) -> bool:
    """Safely write JSON file with formatting and verification.

    Args:
        file_path: Path to JSON file
        data: Data to serialize
        indent: JSON indentation
        sort_keys: Sort JSON keys
        atomic: Use atomic write
        backup: Create backup

    Returns:
        True if successful
    """
    try:
        json_content = json.dumps(
            data, indent=indent, sort_keys=sort_keys, ensure_ascii=False, default=str
        )

        success = safe_write_file(
            file_path, json_content, atomic=atomic, backup=backup, verify_write=True
        )

        if success:
            logger.debug(f"Successfully wrote JSON: {file_path}")

        return success

    except Exception as e:
        logger.error(f"Failed to write JSON {file_path}: {e}")
        raise


def safe_copy_file(
    src_path: Union[str, Path],
    dst_path: Union[str, Path],
    verify_copy: bool = True,
    preserve_metadata: bool = True,
) -> bool:
    """Safely copy file with verification.

    Args:
        src_path: Source file path
        dst_path: Destination file path
        verify_copy: Verify copy integrity
        preserve_metadata: Preserve file metadata

    Returns:
        True if successful
    """
    src_path = Path(src_path)
    dst_path = Path(dst_path)

    if not src_path.exists():
        logger.error(f"Source file does not exist: {src_path}")
        return False

    try:
        dst_path.parent.mkdir(parents=True, exist_ok=True)

        if preserve_metadata:
            shutil.copy2(src_path, dst_path)
        else:
            shutil.copy(src_path, dst_path)

        # Verify copy if requested
        if verify_copy:
            src_checksum = get_file_checksum(src_path)
            dst_checksum = get_file_checksum(dst_path)

            if src_checksum != dst_checksum:
                logger.error("Copy verification failed: checksum mismatch")
                dst_path.unlink(missing_ok=True)
                return False

        logger.debug(f"Successfully copied: {src_path} -> {dst_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to copy file {src_path} -> {dst_path}: {e}")
        return False


def safe_move_file(
    src_path: Union[str, Path], dst_path: Union[str, Path], verify_move: bool = True
) -> bool:
    """Safely move file with verification.

    Args:
        src_path: Source file path
        dst_path: Destination file path
        verify_move: Verify move integrity

    Returns:
        True if successful
    """
    src_path = Path(src_path)
    dst_path = Path(dst_path)

    if not src_path.exists():
        logger.error(f"Source file does not exist: {src_path}")
        return False

    try:
        # Calculate checksum before move if verification requested
        src_checksum = None
        if verify_move:
            src_checksum = get_file_checksum(src_path)

        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_path), str(dst_path))

        # Verify move if requested
        if verify_move and src_checksum:
            dst_checksum = get_file_checksum(dst_path)
            if src_checksum != dst_checksum:
                logger.error("Move verification failed: checksum mismatch")
                return False

        logger.debug(f"Successfully moved: {src_path} -> {dst_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to move file {src_path} -> {dst_path}: {e}")
        return False


def cleanup_temp_files(
    temp_dir: Union[str, Path], max_age_hours: float = 24.0, pattern: str = "*.tmp"
) -> int:
    """Clean up temporary files older than specified age.

    Args:
        temp_dir: Directory containing temporary files
        max_age_hours: Maximum age in hours
        pattern: File pattern to match

    Returns:
        Number of files cleaned up
    """
    temp_dir = Path(temp_dir)
    if not temp_dir.exists():
        return 0

    cutoff_time = time.time() - (max_age_hours * 3600)
    cleaned_count = 0

    try:
        for temp_file in temp_dir.glob(pattern):
            if temp_file.is_file() and temp_file.stat().st_mtime < cutoff_time:
                try:
                    temp_file.unlink()
                    cleaned_count += 1
                    logger.debug(f"Cleaned up temp file: {temp_file}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup {temp_file}: {e}")

        logger.info(f"Cleaned up {cleaned_count} temporary files from {temp_dir}")
        return cleaned_count

    except Exception as e:
        logger.error(f"Failed to cleanup temp files in {temp_dir}: {e}")
        return 0


class BatchFileOperations:
    """Context manager for batching multiple file operations efficiently."""

    def __init__(self, verify_all: bool = True):
        """Initialize batch operations.

        Args:
            verify_all: Verify all operations in batch
        """
        self.operations: List[Dict[str, Any]] = []
        self.verify_all = verify_all
        self.results: List[bool] = []

    def add_write(self, file_path: Union[str, Path], content: str, **kwargs) -> None:
        """Add write operation to batch."""
        self.operations.append(
            {"type": "write", "file_path": Path(file_path), "content": content, "kwargs": kwargs}
        )

    def add_copy(self, src_path: Union[str, Path], dst_path: Union[str, Path], **kwargs) -> None:
        """Add copy operation to batch."""
        self.operations.append(
            {
                "type": "copy",
                "src_path": Path(src_path),
                "dst_path": Path(dst_path),
                "kwargs": kwargs,
            }
        )

    def add_move(self, src_path: Union[str, Path], dst_path: Union[str, Path], **kwargs) -> None:
        """Add move operation to batch."""
        self.operations.append(
            {
                "type": "move",
                "src_path": Path(src_path),
                "dst_path": Path(dst_path),
                "kwargs": kwargs,
            }
        )

    def execute(self) -> List[bool]:
        """Execute all operations in batch.

        Returns:
            List of success flags for each operation
        """
        self.results.clear()

        for operation in self.operations:
            try:
                if operation["type"] == "write":
                    result = safe_write_file(
                        operation["file_path"], operation["content"], **operation["kwargs"]
                    )
                elif operation["type"] == "copy":
                    result = safe_copy_file(
                        operation["src_path"], operation["dst_path"], **operation["kwargs"]
                    )
                elif operation["type"] == "move":
                    result = safe_move_file(
                        operation["src_path"], operation["dst_path"], **operation["kwargs"]
                    )
                else:
                    result = False

                self.results.append(result)

            except Exception as e:
                logger.error(f"Batch operation failed: {e}")
                self.results.append(False)

        return self.results

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.operations and not self.results:
            # Auto-execute if not already done
            self.execute()
