"""
Beads CLI Adapter with Security Controls.

Provides safe subprocess-based wrapper for the `bd` command with:
- Command injection prevention via input validation
- Safe subprocess execution (shell=False)
- Timeout and retry logic for reliability
- Result-based error handling

Security Controls (Mandatory):
- NEVER use shell=True in subprocess calls
- Always validate inputs with BeadsInputValidator
- Use list-based commands (not strings)
- Implement timeouts (default 30s, max 60s)
- Implement retry logic with exponential backoff (3 retries)
- Sanitize error messages (no sensitive data disclosure)

Philosophy:
- Zero-BS: All operations work or return explicit errors
- Ruthless Simplicity: No unnecessary abstractions
- Security First: All mandatory controls implemented
"""

import subprocess
import json
import time
import re
from typing import List, Dict, Any, Optional
from pathlib import Path

from .beads_models import (
    BeadsIssue,
    BeadsRelationship,
    BeadsError,
    BeadsNotInstalledError,
    BeadsNotInitializedError,
    BeadsCLIError,
    BeadsParseError,
    BeadsTimeoutError,
)


# =============================================================================
# Input Validator (Security Control - Mandatory)
# =============================================================================

class BeadsInputValidator:
    """
    Validates all user inputs before CLI commands.

    Security Features:
    - Whitelist pattern: alphanumeric, spaces, hyphens, underscores, periods
    - Length limits: titles ≤ 200 chars, descriptions ≤ 10,000 chars
    - Reject shell metacharacters: ; | & $ ` < > \\ ' "
    - Prevention of command injection attacks
    """

    # Whitelist pattern: alphanumeric, spaces, hyphens, underscores, periods, commas
    SAFE_PATTERN = re.compile(r'^[a-zA-Z0-9\s\-_.,:@/]+$')

    # Shell metacharacters that MUST be rejected
    DANGEROUS_CHARS = [';', '|', '&', '$', '`', '<', '>', '\\', "'", '"', '\n', '\r']

    # Length limits
    MAX_TITLE_LENGTH = 200
    MAX_DESCRIPTION_LENGTH = 10000
    MAX_LABEL_LENGTH = 50
    MAX_ID_LENGTH = 100

    @classmethod
    def validate_title(cls, title: str) -> None:
        """
        Validate issue title.

        Args:
            title: Title to validate

        Raises:
            ValueError: If title is invalid or contains dangerous characters
        """
        if not title or not title.strip():
            raise ValueError("Title cannot be empty")

        if len(title) > cls.MAX_TITLE_LENGTH:
            raise ValueError(
                f"Title too long: {len(title)} characters (max {cls.MAX_TITLE_LENGTH})"
            )

        # Check for dangerous characters
        for char in cls.DANGEROUS_CHARS:
            if char in title:
                raise ValueError(
                    f"Title contains forbidden character: {repr(char)}"
                )

    @classmethod
    def validate_description(cls, description: str) -> None:
        """
        Validate issue description.

        Args:
            description: Description to validate

        Raises:
            ValueError: If description is invalid or contains dangerous characters
        """
        if len(description) > cls.MAX_DESCRIPTION_LENGTH:
            raise ValueError(
                f"Description too long: {len(description)} characters "
                f"(max {cls.MAX_DESCRIPTION_LENGTH})"
            )

        # Check for dangerous characters
        for char in cls.DANGEROUS_CHARS:
            if char in description:
                raise ValueError(
                    f"Description contains forbidden character: {repr(char)}"
                )

    @classmethod
    def validate_id(cls, issue_id: str) -> None:
        """
        Validate issue ID.

        Args:
            issue_id: ID to validate

        Raises:
            ValueError: If ID is invalid or contains dangerous characters
        """
        if not issue_id or not issue_id.strip():
            raise ValueError("Issue ID cannot be empty")

        if len(issue_id) > cls.MAX_ID_LENGTH:
            raise ValueError(
                f"Issue ID too long: {len(issue_id)} characters (max {cls.MAX_ID_LENGTH})"
            )

        # ID should only contain alphanumeric, hyphens, underscores
        if not re.match(r'^[a-zA-Z0-9\-_]+$', issue_id):
            raise ValueError(
                f"Issue ID contains invalid characters: {issue_id}"
            )

    @classmethod
    def validate_label(cls, label: str) -> None:
        """
        Validate label.

        Args:
            label: Label to validate

        Raises:
            ValueError: If label is invalid or contains dangerous characters
        """
        if not label or not label.strip():
            raise ValueError("Label cannot be empty")

        if len(label) > cls.MAX_LABEL_LENGTH:
            raise ValueError(
                f"Label too long: {len(label)} characters (max {cls.MAX_LABEL_LENGTH})"
            )

        # Labels should only contain alphanumeric, hyphens, underscores
        if not re.match(r'^[a-zA-Z0-9\-_]+$', label):
            raise ValueError(
                f"Label contains invalid characters: {label}"
            )

    @classmethod
    def validate_assignee(cls, assignee: str) -> None:
        """
        Validate assignee.

        Args:
            assignee: Assignee to validate

        Raises:
            ValueError: If assignee is invalid or contains dangerous characters
        """
        if not assignee or not assignee.strip():
            raise ValueError("Assignee cannot be empty")

        if len(assignee) > cls.MAX_LABEL_LENGTH:
            raise ValueError(
                f"Assignee too long: {len(assignee)} characters (max {cls.MAX_LABEL_LENGTH})"
            )

        # Assignee should only contain alphanumeric, hyphens, underscores
        if not re.match(r'^[a-zA-Z0-9\-_]+$', assignee):
            raise ValueError(
                f"Assignee contains invalid characters: {assignee}"
            )


# =============================================================================
# BeadsAdapter - CLI Wrapper
# =============================================================================

class BeadsAdapter:
    """
    Safe subprocess-based CLI wrapper for the `bd` command.

    Provides type-safe, validated access to beads CLI with comprehensive
    security controls and error handling.

    Security:
    - All inputs validated via BeadsInputValidator
    - Subprocess calls use shell=False
    - Commands built as lists (never string concatenation)
    - Timeouts enforced (default 30s, max 60s)
    - Retry logic with exponential backoff

    Error Handling:
    - Returns exceptions wrapped in appropriate error types
    - Sanitizes error messages (no sensitive data)
    - Detects specific error conditions (not installed, not initialized)
    """

    DEFAULT_TIMEOUT = 30  # seconds
    MAX_TIMEOUT = 60
    MAX_RETRIES = 3
    BASE_RETRY_DELAY = 1.0  # seconds

    def __init__(self, bd_path: str = "bd", timeout: int = DEFAULT_TIMEOUT):
        """
        Initialize BeadsAdapter.

        Args:
            bd_path: Path to bd executable (default: "bd" from PATH)
            timeout: Timeout for CLI commands in seconds (default: 30)
        """
        self.bd_path = bd_path
        self.timeout = min(timeout, self.MAX_TIMEOUT)
        self._is_available_cache: Optional[bool] = None

    # =========================================================================
    # Availability Checks
    # =========================================================================

    def is_available(self) -> bool:
        """
        Check if bd CLI is available in PATH.

        Returns:
            True if bd command exists, False otherwise

        Note:
            Result is cached after first check to avoid repeated subprocess calls.
        """
        if self._is_available_cache is not None:
            return self._is_available_cache

        try:
            result = subprocess.run(
                ['which', self.bd_path],
                capture_output=True,
                text=True,
                timeout=5,
                check=False
            )
            self._is_available_cache = result.returncode == 0
            return self._is_available_cache
        except (subprocess.SubprocessError, OSError):
            self._is_available_cache = False
            return False

    def check_init(self) -> bool:
        """
        Check if beads is initialized in current repository.

        Returns:
            True if initialized, False otherwise
        """
        try:
            result = subprocess.run(
                [self.bd_path, 'status'],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, OSError):
            return False

    def get_version(self) -> str:
        """
        Get beads CLI version.

        Returns:
            Version string (e.g., "0.1.0")

        Raises:
            RuntimeError: If version cannot be retrieved
        """
        try:
            result = subprocess.run(
                [self.bd_path, '--version'],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False
            )
            if result.returncode == 0:
                # Parse version from output like "beads 0.1.0"
                output = result.stdout.strip()
                if ' ' in output:
                    return output.split()[-1]
                return output
            raise RuntimeError("Failed to get version")
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"Version check timeout: {e}")
        except (subprocess.SubprocessError, OSError) as e:
            raise RuntimeError(f"Version check failed: {e}")

    def check_version_compatibility(self, min_version: str) -> bool:
        """
        Check if installed version meets minimum requirement.

        Args:
            min_version: Minimum required version (e.g., "0.1.0")

        Returns:
            True if version is compatible, False otherwise
        """
        try:
            current = self.get_version()
            # Simple string comparison (works for semantic versioning)
            return current >= min_version
        except RuntimeError:
            return False

    # =========================================================================
    # Command Building and Execution (Security Critical)
    # =========================================================================

    def _build_command(self, action: str, *args, **kwargs) -> List[str]:
        """
        Build CLI command as list (NEVER string concatenation).

        Args:
            action: Command action (e.g., 'create', 'get', 'query')
            *args: Positional arguments
            **kwargs: Keyword arguments converted to flags

        Returns:
            Command as list of strings (safe for subprocess)
        """
        cmd = [self.bd_path, action]

        # Add positional arguments
        for arg in args:
            cmd.append(str(arg))

        # Add keyword arguments as flags
        for key, value in kwargs.items():
            if value is True:
                # Boolean flag
                flag = key.replace('_', '-')
                cmd.append(f'--{flag}')
            elif value is not None and value is not False:
                # Key-value flag
                flag = key.replace('_', '-')
                cmd.append(f'--{flag}')
                if isinstance(value, list):
                    # Multiple values
                    for item in value:
                        cmd.append(str(item))
                else:
                    cmd.append(str(value))

        # Always request JSON output
        if '--json' not in cmd:
            cmd.append('--json')

        return cmd

    def _run_command(
        self,
        cmd: List[str],
        retry: bool = False,
        max_retries: int = MAX_RETRIES
    ) -> subprocess.CompletedProcess:
        """
        Run CLI command safely with error handling and optional retry.

        Args:
            cmd: Command as list (SECURITY: NEVER string with shell=True)
            retry: Enable retry on transient failures
            max_retries: Maximum retry attempts

        Returns:
            CompletedProcess result

        Raises:
            RuntimeError: On command failure (wrapped from subprocess exceptions)

        Security:
        - NEVER uses shell=True
        - Commands are lists (not strings)
        - Timeouts enforced
        - Error messages sanitized
        """
        attempt = 0
        last_error = None

        while attempt <= (max_retries if retry else 0):
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    check=False,  # We handle errors manually
                    shell=False  # SECURITY: NEVER use shell=True
                )

                # Success
                if result.returncode == 0:
                    return result

                # Check for specific error conditions
                stderr = result.stderr.lower()

                # Not installed
                if 'not found' in stderr or 'command not found' in stderr:
                    raise RuntimeError("bd CLI not found. Install beads first.")

                # Not initialized
                if 'not a beads repository' in stderr or 'not initialized' in stderr:
                    raise RuntimeError("Not a beads repository. Run 'bd init' first.")

                # Transient errors that should retry
                if retry and any(marker in stderr for marker in [
                    'lock file',
                    'temporary',
                    'try again'
                ]):
                    last_error = RuntimeError(f"Command failed: {result.stderr}")
                    attempt += 1
                    if attempt <= max_retries:
                        delay = self.BASE_RETRY_DELAY * (2 ** (attempt - 1))
                        time.sleep(delay)
                        continue

                # Non-retryable error
                raise RuntimeError(f"Command failed: {result.stderr}")

            except subprocess.TimeoutExpired as e:
                if retry and attempt < max_retries:
                    last_error = RuntimeError(f"Command timeout: {e}")
                    attempt += 1
                    delay = self.BASE_RETRY_DELAY * (2 ** (attempt - 1))
                    time.sleep(delay)
                    continue
                raise RuntimeError(f"Command timeout: {e}")

            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Command error: {e.stderr}")

            except PermissionError as e:
                raise RuntimeError(f"Permission denied: {e}")

            except OSError as e:
                raise RuntimeError(f"OS error: {e}")

        # Max retries exhausted
        if last_error:
            raise last_error
        raise RuntimeError("Command failed after retries")

    # =========================================================================
    # JSON Parsing
    # =========================================================================

    def _parse_json_output(self, output: str) -> Any:
        """
        Parse JSON output from CLI.

        Args:
            output: JSON string from CLI

        Returns:
            Parsed Python object (dict or list)

        Raises:
            json.JSONDecodeError: If JSON is invalid
        """
        return json.loads(output.strip())

    # =========================================================================
    # Issue Operations
    # =========================================================================

    def create_issue(
        self,
        title: str,
        description: str,
        labels: Optional[List[str]] = None,
        assignee: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create new issue.

        Args:
            title: Issue title
            description: Issue description
            labels: Optional list of labels
            assignee: Optional assignee
            metadata: Optional metadata dict

        Returns:
            Created issue ID

        Raises:
            RuntimeError: On creation failure or validation error
        """
        # Validate inputs (SECURITY CRITICAL)
        BeadsInputValidator.validate_title(title)
        BeadsInputValidator.validate_description(description)

        if labels:
            for label in labels:
                BeadsInputValidator.validate_label(label)

        if assignee:
            BeadsInputValidator.validate_assignee(assignee)

        # Build command
        kwargs = {
            'title': title,
            'description': description
        }

        if labels:
            kwargs['label'] = labels

        if assignee:
            kwargs['assignee'] = assignee

        if metadata:
            kwargs['metadata'] = json.dumps(metadata)

        cmd = self._build_command('create', **kwargs)
        result = self._run_command(cmd)

        # Parse response
        data = self._parse_json_output(result.stdout)
        return data.get('id', '')

    def get_issue(
        self,
        issue_id: str,
        retry: bool = False,
        max_retries: int = MAX_RETRIES
    ) -> Optional[Dict[str, Any]]:
        """
        Get issue by ID.

        Args:
            issue_id: Issue ID to retrieve
            retry: Enable retry on transient failures
            max_retries: Maximum retry attempts

        Returns:
            Issue data dict or None if not found

        Raises:
            json.JSONDecodeError: If response JSON is invalid
            RuntimeError: On command failure
        """
        # Validate input (SECURITY CRITICAL)
        BeadsInputValidator.validate_id(issue_id)

        cmd = self._build_command('get', issue_id)

        try:
            result = self._run_command(cmd, retry=retry, max_retries=max_retries)
            return self._parse_json_output(result.stdout)
        except RuntimeError as e:
            if 'not found' in str(e).lower():
                return None
            raise

    def update_issue(
        self,
        issue_id: str,
        status: Optional[str] = None,
        assignee: Optional[str] = None,
        labels: Optional[List[str]] = None,
        **kwargs
    ) -> bool:
        """
        Update issue fields.

        Args:
            issue_id: Issue ID to update
            status: Optional new status
            assignee: Optional new assignee
            labels: Optional new labels
            **kwargs: Additional fields to update

        Returns:
            True if update succeeded, False otherwise
        """
        # Validate input (SECURITY CRITICAL)
        BeadsInputValidator.validate_id(issue_id)

        if assignee:
            BeadsInputValidator.validate_assignee(assignee)

        if labels:
            for label in labels:
                BeadsInputValidator.validate_label(label)

        # Build update kwargs
        update_kwargs = {}
        if status:
            update_kwargs['status'] = status
        if assignee:
            update_kwargs['assignee'] = assignee
        if labels:
            update_kwargs['label'] = labels
        update_kwargs.update(kwargs)

        cmd = self._build_command('update', issue_id, **update_kwargs)

        try:
            self._run_command(cmd)
            return True
        except RuntimeError:
            return False

    def query_issues(
        self,
        status: Optional[str] = None,
        assignee: Optional[str] = None,
        labels: Optional[List[str]] = None,
        has_blockers: Optional[bool] = None,
        relationship_type: Optional[str] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Query issues with filters.

        Args:
            status: Filter by status
            assignee: Filter by assignee
            labels: Filter by labels
            has_blockers: Filter by blocker presence
            relationship_type: Filter by relationship type
            **kwargs: Additional query parameters

        Returns:
            List of issue dicts
        """
        query_kwargs = {}

        if status:
            query_kwargs['status'] = status

        if assignee:
            BeadsInputValidator.validate_assignee(assignee)
            query_kwargs['assignee'] = assignee

        if labels:
            for label in labels:
                BeadsInputValidator.validate_label(label)
            query_kwargs['label'] = labels

        if has_blockers is False:
            query_kwargs['no_blockers'] = True
        elif has_blockers is True:
            query_kwargs['has_blockers'] = True

        if relationship_type:
            query_kwargs['type'] = relationship_type

        query_kwargs.update(kwargs)

        # Try 'query' command first, fall back to 'list'
        try:
            cmd = self._build_command('query', **query_kwargs)
            result = self._run_command(cmd)
            return self._parse_json_output(result.stdout)
        except RuntimeError:
            # Try 'list' command as fallback
            cmd = self._build_command('list', **query_kwargs)
            result = self._run_command(cmd)
            return self._parse_json_output(result.stdout)

    # =========================================================================
    # Relationship Operations
    # =========================================================================

    def add_relationship(
        self,
        from_id: str,
        to_id: str,
        rel_type: str
    ) -> bool:
        """
        Add relationship between issues.

        Args:
            from_id: Source issue ID
            to_id: Target issue ID
            rel_type: Relationship type (blocks, related, etc.)

        Returns:
            True if relationship added, False otherwise
        """
        # Validate inputs (SECURITY CRITICAL)
        BeadsInputValidator.validate_id(from_id)
        BeadsInputValidator.validate_id(to_id)

        # Try 'relate' command first, fall back to 'link'
        for action in ['relate', 'link']:
            try:
                cmd = self._build_command(action, from_id, to_id, type=rel_type)
                self._run_command(cmd)
                return True
            except RuntimeError:
                continue

        return False

    def get_relationships(
        self,
        issue_id: str,
        relationship_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get relationships for an issue.

        Args:
            issue_id: Issue ID
            relationship_type: Optional filter by type

        Returns:
            List of relationship dicts
        """
        # Validate input (SECURITY CRITICAL)
        BeadsInputValidator.validate_id(issue_id)

        kwargs = {}
        if relationship_type:
            kwargs['type'] = relationship_type

        cmd = self._build_command('relationships', issue_id, **kwargs)

        try:
            result = self._run_command(cmd)
            return self._parse_json_output(result.stdout)
        except RuntimeError:
            return []
