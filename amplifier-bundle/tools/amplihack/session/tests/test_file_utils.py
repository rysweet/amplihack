"""Tests for defensive file I/O utilities."""

import json
import os
import tempfile
import time
from pathlib import Path

import pytest

from ..file_utils import (
    BatchFileOperations,
    FileCorruptionError,
    RetryExhaustedError,
    cleanup_temp_files,
    file_lock,
    get_file_checksum,
    retry_file_operation,
    safe_copy_file,
    safe_move_file,
    safe_read_file,
    safe_read_json,
    safe_write_file,
    safe_write_json,
)


class TestRetryDecorator:
    """Test retry_file_operation decorator."""

    def test_successful_operation(self):
        """Test successful operation without retries."""

        @retry_file_operation(max_retries=3)
        def successful_operation():
            return "success"

        result = successful_operation()
        assert result == "success"

    def test_retry_on_failure(self):
        """Test retry behavior on failures."""
        call_count = 0

        @retry_file_operation(max_retries=2, delay=0.01)
        def failing_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise OSError("Temporary failure")
            return "success"

        result = failing_operation()
        assert result == "success"
        assert call_count == 3

    def test_retry_exhausted(self):
        """Test retry exhaustion."""

        @retry_file_operation(max_retries=2, delay=0.01)
        def always_failing():
            raise OSError("Persistent failure")

        with pytest.raises(RetryExhaustedError):
            always_failing()

    def test_custom_exceptions(self):
        """Test custom exception handling."""

        @retry_file_operation(max_retries=1, exceptions=(ValueError,))
        def value_error_operation():
            raise ValueError("Custom error")

        with pytest.raises(RetryExhaustedError):
            value_error_operation()

        @retry_file_operation(max_retries=1, exceptions=(ValueError,))
        def os_error_operation():
            raise OSError("OS error")

        with pytest.raises(OSError):  # Should not be retried
            os_error_operation()


class TestFileLock:
    """Test file locking functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_successful_lock(self, temp_dir):
        """Test successful file locking."""
        lock_file = temp_dir / "test.lock"

        with file_lock(lock_file):
            assert lock_file.exists()

        assert not lock_file.exists()

    def test_lock_conflict(self, temp_dir):
        """Test lock conflict handling."""
        lock_file = temp_dir / "test.lock"

        # Create lock file manually
        lock_file.touch()

        with pytest.raises(TimeoutError), file_lock(lock_file, timeout=0.1):
            pass

    def test_lock_cleanup_on_error(self, temp_dir):
        """Test lock cleanup on exception."""
        lock_file = temp_dir / "test.lock"

        try:
            with file_lock(lock_file):
                raise ValueError("Test error")
        except ValueError:
            pass

        assert not lock_file.exists()


class TestChecksumOperations:
    """Test checksum functionality."""

    @pytest.fixture
    def temp_file(self):
        """Temporary file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            temp_path = Path(f.name)

        yield temp_path
        temp_path.unlink(missing_ok=True)

    def test_checksum_calculation(self, temp_file):
        """Test checksum calculation."""
        checksum = get_file_checksum(temp_file)
        assert len(checksum) == 32  # MD5 hex length
        assert checksum.isalnum()

    def test_checksum_algorithms(self, temp_file):
        """Test different checksum algorithms."""
        md5_sum = get_file_checksum(temp_file, "md5")
        sha1_sum = get_file_checksum(temp_file, "sha1")
        sha256_sum = get_file_checksum(temp_file, "sha256")

        assert len(md5_sum) == 32
        assert len(sha1_sum) == 40
        assert len(sha256_sum) == 64

    def test_checksum_consistency(self, temp_file):
        """Test checksum consistency."""
        checksum1 = get_file_checksum(temp_file)
        checksum2 = get_file_checksum(temp_file)
        assert checksum1 == checksum2

    def test_checksum_nonexistent_file(self):
        """Test checksum of non-existent file."""
        checksum = get_file_checksum(Path("nonexistent.txt"))
        assert checksum == ""


class TestSafeFileOperations:
    """Test safe file I/O operations."""

    @pytest.fixture
    def temp_dir(self):
        """Temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_safe_read_file(self, temp_dir):
        """Test safe file reading."""
        test_file = temp_dir / "test.txt"
        test_content = "Hello, World!"

        # Write test file
        test_file.write_text(test_content)

        # Read with safe_read_file
        content = safe_read_file(test_file)
        assert content == test_content

    def test_safe_read_nonexistent_file(self):
        """Test reading non-existent file."""
        content = safe_read_file("nonexistent.txt")
        assert content is None

    def test_safe_write_file(self, temp_dir):
        """Test safe file writing."""
        test_file = temp_dir / "test.txt"
        test_content = "Hello, World!"

        result = safe_write_file(test_file, test_content)
        assert result is True
        assert test_file.read_text() == test_content

    def test_atomic_write(self, temp_dir):
        """Test atomic file writing."""
        test_file = temp_dir / "atomic.txt"
        test_content = "Atomic content"

        result = safe_write_file(test_file, test_content, atomic=True)
        assert result is True
        assert test_file.read_text() == test_content

    def test_write_with_backup(self, temp_dir):
        """Test writing with backup creation."""
        test_file = temp_dir / "backup_test.txt"
        original_content = "Original content"
        new_content = "New content"

        # Create original file
        test_file.write_text(original_content)

        # Write with backup
        result = safe_write_file(test_file, new_content, backup=True)
        assert result is True
        assert test_file.read_text() == new_content

        # Check backup exists
        backup_file = test_file.with_suffix(".txt.backup")
        assert backup_file.exists()
        assert backup_file.read_text() == original_content

    def test_write_verification(self, temp_dir):
        """Test write verification."""
        test_file = temp_dir / "verify.txt"
        test_content = "Verified content"

        result = safe_write_file(test_file, test_content, verify_write=True)
        assert result is True

    def test_write_with_checksum_verification(self, temp_dir):
        """Test reading with checksum verification."""
        test_file = temp_dir / "checksum.txt"
        test_content = "Checksum content"

        # Write file and get checksum
        safe_write_file(test_file, test_content)
        expected_checksum = get_file_checksum(test_file)

        # Read with verification
        content = safe_read_file(
            test_file, verify_checksum=True, expected_checksum=expected_checksum
        )
        assert content == test_content

    def test_checksum_verification_failure(self, temp_dir):
        """Test checksum verification failure."""
        test_file = temp_dir / "bad_checksum.txt"
        test_file.write_text("content")

        with pytest.raises(FileCorruptionError):
            safe_read_file(test_file, verify_checksum=True, expected_checksum="wrong_checksum")


class TestJSONOperations:
    """Test JSON file operations."""

    @pytest.fixture
    def temp_dir(self):
        """Temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_safe_write_json(self, temp_dir):
        """Test safe JSON writing."""
        test_file = temp_dir / "test.json"
        test_data = {"key": "value", "number": 42, "list": [1, 2, 3]}

        result = safe_write_json(test_file, test_data)
        assert result is True

        # Verify content
        with open(test_file) as f:
            loaded_data = json.load(f)
        assert loaded_data == test_data

    def test_safe_read_json(self, temp_dir):
        """Test safe JSON reading."""
        test_file = temp_dir / "test.json"
        test_data = {"key": "value", "nested": {"a": 1, "b": 2}}

        # Write JSON file
        with open(test_file, "w") as f:
            json.dump(test_data, f)

        # Read with safe_read_json
        loaded_data = safe_read_json(test_file)
        assert loaded_data == test_data

    def test_read_invalid_json(self, temp_dir):
        """Test reading invalid JSON."""
        test_file = temp_dir / "invalid.json"
        test_file.write_text("invalid json content")

        result = safe_read_json(test_file, default={"default": True})
        assert result == {"default": True}

    def test_read_nonexistent_json(self):
        """Test reading non-existent JSON file."""
        result = safe_read_json("nonexistent.json", default=[])
        assert result == []

    def test_json_schema_validation(self, temp_dir):
        """Test JSON schema validation."""
        test_file = temp_dir / "schema.json"
        test_data = {"name": "test", "value": 42}

        safe_write_json(test_file, test_data)

        def validate_schema(data):
            assert "name" in data
            assert "value" in data
            assert isinstance(data["value"], int)

        # Valid data
        result = safe_read_json(test_file, validate_schema=validate_schema)
        assert result == test_data

        # Invalid data
        invalid_data = {"name": "test"}  # Missing "value"
        safe_write_json(test_file, invalid_data)

        result = safe_read_json(
            test_file, default={"default": True}, validate_schema=validate_schema
        )
        assert result == {"default": True}


class TestFileCopyMove:
    """Test file copy and move operations."""

    @pytest.fixture
    def temp_dir(self):
        """Temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_safe_copy_file(self, temp_dir):
        """Test safe file copying."""
        src_file = temp_dir / "source.txt"
        dst_file = temp_dir / "destination.txt"
        test_content = "Copy test content"

        src_file.write_text(test_content)

        result = safe_copy_file(src_file, dst_file)
        assert result is True
        assert dst_file.exists()
        assert dst_file.read_text() == test_content
        assert src_file.exists()  # Original should still exist

    def test_copy_with_verification(self, temp_dir):
        """Test copy with integrity verification."""
        src_file = temp_dir / "source.txt"
        dst_file = temp_dir / "destination.txt"
        test_content = "Verified copy content"

        src_file.write_text(test_content)

        result = safe_copy_file(src_file, dst_file, verify_copy=True)
        assert result is True
        assert dst_file.read_text() == test_content

    def test_copy_nonexistent_source(self, temp_dir):
        """Test copying non-existent source."""
        src_file = temp_dir / "nonexistent.txt"
        dst_file = temp_dir / "destination.txt"

        result = safe_copy_file(src_file, dst_file)
        assert result is False

    def test_safe_move_file(self, temp_dir):
        """Test safe file moving."""
        src_file = temp_dir / "source.txt"
        dst_file = temp_dir / "destination.txt"
        test_content = "Move test content"

        src_file.write_text(test_content)

        result = safe_move_file(src_file, dst_file)
        assert result is True
        assert dst_file.exists()
        assert dst_file.read_text() == test_content
        assert not src_file.exists()  # Original should be moved

    def test_move_with_verification(self, temp_dir):
        """Test move with integrity verification."""
        src_file = temp_dir / "source.txt"
        dst_file = temp_dir / "destination.txt"
        test_content = "Verified move content"

        src_file.write_text(test_content)

        result = safe_move_file(src_file, dst_file, verify_move=True)
        assert result is True
        assert dst_file.read_text() == test_content


class TestCleanupOperations:
    """Test cleanup functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_cleanup_temp_files(self, temp_dir):
        """Test temporary file cleanup."""
        # Create some temporary files
        old_file = temp_dir / "old.tmp"
        new_file = temp_dir / "new.tmp"
        other_file = temp_dir / "other.txt"

        old_file.touch()
        new_file.touch()
        other_file.touch()

        # Make old file appear old
        old_time = time.time() - (25 * 3600)  # 25 hours old
        os.utime(old_file, (old_time, old_time))

        # Cleanup files older than 24 hours
        cleaned_count = cleanup_temp_files(temp_dir, max_age_hours=24.0)

        assert cleaned_count == 1
        assert not old_file.exists()
        assert new_file.exists()
        assert other_file.exists()  # Different extension


class TestBatchOperations:
    """Test batch file operations."""

    @pytest.fixture
    def temp_dir(self):
        """Temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_batch_write_operations(self, temp_dir):
        """Test batch write operations."""
        with BatchFileOperations() as batch:
            batch.add_write(temp_dir / "file1.txt", "Content 1")
            batch.add_write(temp_dir / "file2.txt", "Content 2")
            batch.add_write(temp_dir / "file3.txt", "Content 3")

        # Check all files were created
        assert (temp_dir / "file1.txt").read_text() == "Content 1"
        assert (temp_dir / "file2.txt").read_text() == "Content 2"
        assert (temp_dir / "file3.txt").read_text() == "Content 3"

    def test_batch_copy_operations(self, temp_dir):
        """Test batch copy operations."""
        # Create source files
        src1 = temp_dir / "src1.txt"
        src2 = temp_dir / "src2.txt"
        src1.write_text("Source 1")
        src2.write_text("Source 2")

        with BatchFileOperations() as batch:
            batch.add_copy(src1, temp_dir / "dst1.txt")
            batch.add_copy(src2, temp_dir / "dst2.txt")

        # Check files were copied
        assert (temp_dir / "dst1.txt").read_text() == "Source 1"
        assert (temp_dir / "dst2.txt").read_text() == "Source 2"

    def test_batch_move_operations(self, temp_dir):
        """Test batch move operations."""
        # Create source files
        src1 = temp_dir / "move_src1.txt"
        src2 = temp_dir / "move_src2.txt"
        src1.write_text("Move Source 1")
        src2.write_text("Move Source 2")

        with BatchFileOperations() as batch:
            batch.add_move(src1, temp_dir / "move_dst1.txt")
            batch.add_move(src2, temp_dir / "move_dst2.txt")

        # Check files were moved
        assert (temp_dir / "move_dst1.txt").read_text() == "Move Source 1"
        assert (temp_dir / "move_dst2.txt").read_text() == "Move Source 2"
        assert not src1.exists()
        assert not src2.exists()

    def test_batch_mixed_operations(self, temp_dir):
        """Test batch with mixed operation types."""
        src_file = temp_dir / "mixed_src.txt"
        src_file.write_text("Mixed source")

        batch = BatchFileOperations()
        batch.add_write(temp_dir / "write_test.txt", "Write content")
        batch.add_copy(src_file, temp_dir / "copy_test.txt")

        results = batch.execute()

        assert all(results)  # All operations successful
        assert (temp_dir / "write_test.txt").read_text() == "Write content"
        assert (temp_dir / "copy_test.txt").read_text() == "Mixed source"

    def test_batch_operation_failure(self, temp_dir):
        """Test batch operation with failures."""
        batch = BatchFileOperations()
        batch.add_write(temp_dir / "good.txt", "Good content")
        batch.add_copy(Path("nonexistent.txt"), temp_dir / "bad.txt")

        results = batch.execute()

        assert len(results) == 2
        assert results[0] is True  # Write should succeed
        assert results[1] is False  # Copy should fail
