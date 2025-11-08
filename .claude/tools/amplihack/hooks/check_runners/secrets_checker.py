#!/usr/bin/env python3
"""
Secrets checker - detects potential secrets in code using detect-secrets.
"""

import json
import subprocess
import time

from .base_checker import BaseChecker
from ..violations import CheckResult


class SecretsChecker(BaseChecker):
    """Checks for secrets using detect-secrets tool."""

    @property
    def name(self) -> str:
        return "secrets"

    def is_detect_secrets_available(self) -> bool:
        """Check if detect-secrets is installed.

        Returns:
            True if detect-secrets is available
        """
        try:
            result = subprocess.run(
                ["detect-secrets", "--version"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def check(self, files: list[str]) -> CheckResult:
        """Check files for potential secrets.

        Args:
            files: List of file paths to check

        Returns:
            CheckResult with any violations found
        """
        start_time = time.time()
        violations = []

        # Check if detect-secrets is available
        if not self.is_detect_secrets_available():
            execution_time = time.time() - start_time
            return CheckResult(
                checker_name=self.name,
                violations=[],
                execution_time=execution_time,
                success=True,
                error_message="detect-secrets not installed, skipping secrets check",
            )

        # Run detect-secrets scan on each file
        for filepath in files:
            if not self.file_exists(filepath):
                continue

            try:
                # Run detect-secrets on single file
                result = self.run_command(
                    ["detect-secrets", "scan", "--baseline", "/dev/null", filepath],
                    timeout=30,
                )

                if result.returncode != 0 and result.stdout:
                    # Parse JSON output
                    try:
                        scan_result = json.loads(result.stdout)

                        # Extract results for this file
                        if "results" in scan_result and filepath in scan_result["results"]:
                            for secret in scan_result["results"][filepath]:
                                line_num = secret.get("line_number")
                                secret_type = secret.get("type", "Unknown")

                                violations.append(
                                    self.create_violation(
                                        file=filepath,
                                        line=line_num,
                                        message=f"Potential secret detected: {secret_type}",
                                        remediation="Remove secret and use environment variables or secret management",
                                        severity="error",
                                    )
                                )
                    except json.JSONDecodeError:
                        # If JSON parsing fails, just note it
                        pass

            except subprocess.TimeoutExpired:
                violations.append(
                    self.create_violation(
                        file=filepath,
                        message="Secrets check timed out",
                        remediation="File may be too large for secrets scanning",
                        severity="warning",
                    )
                )
            except Exception as e:
                # Don't fail the whole check if one file has issues
                pass

        execution_time = time.time() - start_time

        return CheckResult(
            checker_name=self.name,
            violations=violations,
            execution_time=execution_time,
            success=True,
        )
