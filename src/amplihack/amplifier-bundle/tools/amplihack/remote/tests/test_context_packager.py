"""Unit tests for context_packager module."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from ..context_packager import SECRET_PATTERNS, ContextPackager
from ..errors import PackagingError


class TestContextPackager(unittest.TestCase):
    """Test cases for ContextPackager class."""

    def setUp(self):
        """Create temporary git repository for testing."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.repo_path = self.temp_dir / "test_repo"
        self.repo_path.mkdir()

        # Initialize git repository
        subprocess.run(["git", "init"], cwd=self.repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"], cwd=self.repo_path, check=True
        )
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=self.repo_path, check=True)

        # Create .claude directory
        claude_dir = self.repo_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "test.txt").write_text("test content")

        # Create initial commit
        subprocess.run(["git", "add", "."], cwd=self.repo_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=self.repo_path,
            check=True,
            capture_output=True,
        )

    def tearDown(self):
        """Clean up temporary directory."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_secret_detection_anthropic_key(self):
        """Test detection of Anthropic API key."""
        # Create file with secret
        test_file = self.repo_path / "config.py"
        test_file.write_text(
            'ANTHROPIC_API_KEY = "sk-ant-1234567890abcdef"'
        )  # pragma: allowlist secret

        # Add to git
        subprocess.run(["git", "add", "config.py"], cwd=self.repo_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Add config"],
            cwd=self.repo_path,
            check=True,
            capture_output=True,
        )

        packager = ContextPackager(self.repo_path)
        secrets = packager.scan_secrets()

        self.assertGreater(len(secrets), 0)
        self.assertIn("config.py", secrets[0].file_path)

    def test_secret_detection_openai_key(self):
        """Test detection of OpenAI API key."""
        test_file = self.repo_path / "api.py"
        test_file.write_text('OPENAI_API_KEY = "sk-proj-abcdef123456"')  # pragma: allowlist secret

        subprocess.run(["git", "add", "api.py"], cwd=self.repo_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Add api"], cwd=self.repo_path, check=True, capture_output=True
        )

        packager = ContextPackager(self.repo_path)
        secrets = packager.scan_secrets()

        self.assertGreater(len(secrets), 0)

    def test_secret_detection_password(self):
        """Test detection of password."""
        test_file = self.repo_path / "db.py"
        test_file.write_text('password = "SuperSecret123"')  # pragma: allowlist secret

        subprocess.run(["git", "add", "db.py"], cwd=self.repo_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Add db"], cwd=self.repo_path, check=True, capture_output=True
        )

        packager = ContextPackager(self.repo_path)
        secrets = packager.scan_secrets()

        self.assertGreater(len(secrets), 0)

    def test_no_secrets_clean_repo(self):
        """Test that clean repo has no secrets."""
        packager = ContextPackager(self.repo_path)
        secrets = packager.scan_secrets()

        self.assertEqual(len(secrets), 0)

    def test_create_bundle(self):
        """Test git bundle creation."""
        with ContextPackager(self.repo_path) as packager:
            bundle_path = packager.create_bundle()

            self.assertTrue(bundle_path.exists())
            self.assertGreater(bundle_path.stat().st_size, 0)

    def test_package_clean_repo(self):
        """Test packaging clean repository."""
        with ContextPackager(self.repo_path) as packager:
            archive_path = packager.package()

            self.assertTrue(archive_path.exists())
            self.assertGreater(archive_path.stat().st_size, 0)
            self.assertTrue(str(archive_path).endswith(".tar.gz"))

    def test_package_with_secrets_fails(self):
        """Test that packaging fails when secrets detected."""
        # Add secret (realistic format: sk-ant-api03-{64 chars})
        # Use 'config.py' not 'secret.py' since *secret* files are auto-excluded
        test_file = self.repo_path / "config.py"
        realistic_secret = (
            "sk-ant-api03-" + "a" * 64
        )  # Realistic Anthropic API key format # pragma: allowlist secret
        test_file.write_text(f'API_KEY = "{realistic_secret}"')
        subprocess.run(["git", "add", "config.py"], cwd=self.repo_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Add config"],
            cwd=self.repo_path,
            check=True,
            capture_output=True,
        )

        with ContextPackager(self.repo_path) as packager:
            with self.assertRaises(PackagingError) as ctx:
                packager.package()

            self.assertIn("secret", str(ctx.exception).lower())

    def test_exclusion_patterns(self):
        """Test that excluded files are not scanned."""
        # Create .env file (should be excluded)
        env_file = self.repo_path / ".env"
        env_file.write_text('SECRET_KEY="should-be-excluded"')  # pragma: allowlist secret

        packager = ContextPackager(self.repo_path)
        self.assertTrue(packager._is_excluded(".env"))

    def test_context_manager_cleanup(self):
        """Test that context manager cleans up temp files."""
        packager = ContextPackager(self.repo_path)

        with packager:
            _archive_path = packager.package()
            temp_dir = packager.temp_dir
            self.assertTrue(temp_dir.exists())

        # After context exit, temp dir should be cleaned up
        self.assertFalse(temp_dir.exists())

    def test_missing_claude_directory_fails(self):
        """Test that packaging fails if .claude directory missing."""
        # Remove .claude directory
        shutil.rmtree(self.repo_path / ".claude")

        with ContextPackager(self.repo_path) as packager:
            with self.assertRaises(PackagingError) as ctx:
                packager.package()

            self.assertIn(".claude", str(ctx.exception))

    def test_archive_size_limit(self):
        """Test that oversized archives are rejected."""
        # Add large random file that won't compress well (binary-like data)
        large_file = self.repo_path / "large.bin"
        # Use random-ish data that compresses poorly
        import random

        random.seed(42)
        large_content = bytes([random.randint(0, 255) for _ in range(50000)])  # 50KB random
        large_file.write_bytes(large_content)
        subprocess.run(["git", "add", "large.bin"], cwd=self.repo_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Add large file"],
            cwd=self.repo_path,
            check=True,
            capture_output=True,
        )

        # Create packager with tiny size limit (500 bytes)
        packager = ContextPackager(self.repo_path, max_size_mb=0.0005)  # 500 bytes

        with self.assertRaises(PackagingError) as ctx:
            with packager:
                packager.package()

        self.assertIn("size", str(ctx.exception).lower())


class TestSecretPatterns(unittest.TestCase):
    """Test secret detection patterns."""

    def test_anthropic_key_pattern(self):
        """Test Anthropic key pattern matching."""
        import re

        pattern = SECRET_PATTERNS["anthropic_key"]

        # Should match
        self.assertIsNotNone(
            re.search(pattern, 'ANTHROPIC_API_KEY = "sk-ant-abc123"')
        )  # pragma: allowlist secret

        # Should not match
        self.assertIsNone(re.search(pattern, 'SOME_OTHER_KEY = "value"'))

    def test_github_pat_pattern(self):
        """Test GitHub PAT pattern matching."""
        import re

        pattern = SECRET_PATTERNS["github_pat"]

        # Should match
        self.assertIsNotNone(re.search(pattern, 'token = "ghp_' + "a" * 36 + '"'))

        # Should not match short strings
        self.assertIsNone(re.search(pattern, "ghp_short"))


if __name__ == "__main__":
    unittest.main()
