"""GitHub issue parsing utilities.

Extracts sub-issue references and metadata from GitHub issue bodies.

Philosophy:
- Simple regex-based parsing
- Multiple reference format support (#123, GH-123, URLs)
- Validation and error handling
- Uses gh CLI for fetching

Public API:
    GitHubIssueParser: Main parser class
"""

import json
import re
import subprocess
from typing import List, Dict, Any, Optional


class GitHubIssueParser:
    """Parser for GitHub issue bodies to extract sub-issue references.

    Supports multiple reference formats:
    - #123 (hash format)
    - GH-123 (GitHub shorthand)
    - https://github.com/owner/repo/issues/123 (full URL)
    - Issue #123 (descriptive)
    """

    # Issue reference patterns
    PATTERNS = [
        r'#(\d+)',  # #123
        r'GH-(\d+)',  # GH-123
        r'issue[s]?\s+#?(\d+)',  # issue #123 or issues 123
        r'github\.com/[\w-]+/[\w-]+/issues/(\d+)',  # Full URL
    ]

    def parse_sub_issues(self, body: str) -> List[int]:
        """Parse sub-issue numbers from issue body.

        Excludes issues found in code blocks (```...```).

        Args:
            body: GitHub issue body text

        Returns:
            List of unique sub-issue numbers in order of appearance

        Example:
            >>> parser = GitHubIssueParser()
            >>> parser.parse_sub_issues("#123, #456, GH-789")
            [123, 456, 789]
        """
        if not body:
            return []

        # Remove code blocks first to avoid parsing issues inside them
        cleaned_body = re.sub(r'```.*?```', '', body, flags=re.DOTALL)

        sub_issues = []
        for pattern in self.PATTERNS:
            matches = re.findall(pattern, cleaned_body, re.IGNORECASE)
            for match in matches:
                try:
                    issue_num = int(match)
                    # Filter out invalid numbers (0, negative, or too large)
                    # GitHub's maximum issue ID is practically limited to 10^18 (max safe integer in many systems)
                    if 1 <= issue_num < 10**18:
                        sub_issues.append(issue_num)
                except (ValueError, OverflowError):
                    continue

        # Remove duplicates while preserving order
        seen = set()
        unique_issues = []
        for issue in sub_issues:
            if issue not in seen:
                seen.add(issue)
                unique_issues.append(issue)

        return unique_issues

    def fetch_issue_body(self, issue_number: int) -> str:
        """Fetch issue body from GitHub using gh CLI.

        Args:
            issue_number: GitHub issue number

        Returns:
            Issue body text

        Raises:
            RuntimeError: If gh CLI not installed
            ValueError: If issue not found
        """
        try:
            result = subprocess.run(
                ["gh", "issue", "view", str(issue_number), "--json", "body"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                raise ValueError(
                    f"Issue #{issue_number} not found or cannot be accessed"
                )

            data = json.loads(result.stdout)
            return data.get("body", "")

        except FileNotFoundError:
            raise RuntimeError(
                "gh CLI not installed. Install with: brew install gh (macOS) "
                "or see https://cli.github.com/manual/installation"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"Timeout fetching issue #{issue_number}. Check network connection."
            )
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Invalid JSON response from gh CLI: {e}"
            )

    def parse_metadata(self, body: str) -> Dict[str, Any]:
        """Parse issue metadata from body.

        Extracts:
        - Title (if present in markdown header)
        - Sub-issues
        - Sections

        Args:
            body: Issue body text

        Returns:
            Dictionary with metadata fields
        """
        metadata = {
            "title": self._extract_title(body),
            "sub_issues": self.parse_sub_issues(body),
            "sections": self._extract_sections(body),
        }
        return metadata

    def _extract_title(self, body: str) -> Optional[str]:
        """Extract title from markdown header."""
        match = re.search(r'^#\s+(.+)$', body, re.MULTILINE)
        return match.group(1).strip() if match else None

    def _extract_sections(self, body: str) -> List[str]:
        """Extract section headers from body."""
        matches = re.findall(r'^##\s+(.+)$', body, re.MULTILINE)
        return [m.strip() for m in matches]

    def validate_format(self, body: str) -> bool:
        """Validate that issue body has valid format for orchestration.

        Args:
            body: Issue body text

        Returns:
            True if valid format (contains at least one sub-issue)
        """
        sub_issues = self.parse_sub_issues(body)
        return len(sub_issues) > 0

    def parse_sub_issues_with_context(self, body: str) -> List[Dict[str, Any]]:
        """Parse sub-issues with surrounding context.

        Extracts issue number and associated description text.
        Handles multiple formats:
        - "- Sub-issue #101: Description"
        - "- Related: #102 - Description"
        - "- GH-103: Description"
        - "- See https://github.com/owner/repo/issues/104 for description"
        - "- #105: Description"

        Args:
            body: Issue body text

        Returns:
            List of dicts with 'issue_number' and 'description' keys

        Example:
            >>> parser.parse_sub_issues_with_context(
            ...     "- #123: Implement auth\\n- #456: Add tests"
            ... )
            [
                {'issue_number': 123, 'description': 'Implement auth'},
                {'issue_number': 456, 'description': 'Add tests'}
            ]
        """
        results = []

        # Pattern: captures various line formats with issue references
        # Supports:
        # - Sub-issue #101: text
        # - Related: #102 - text
        # - GH-103: text
        # - #105: text
        # - See URL for text
        patterns = [
            # "- Sub-issue #101: Description" or "- #101: Description"
            r'[-*]\s*(?:Sub-issue\s+)?#(\d+)[\s:]+([^\n]+)',
            # "- Related: #102 - Description"
            r'[-*]\s*Related:\s+#(\d+)\s*-\s*([^\n]+)',
            # "- GH-103: Description"
            r'[-*]\s*GH-(\d+)[\s:]+([^\n]+)',
            # "- See https://github.com/owner/repo/issues/104 for description"
            r'[-*]\s*See\s+https://github\.com/[\w-]+/[\w-]+/issues/(\d+)\s+for\s+([^\n]+)',
        ]

        seen = set()
        for pattern in patterns:
            matches = re.findall(pattern, body, re.MULTILINE | re.IGNORECASE)
            for issue_num_str, description in matches:
                try:
                    issue_num = int(issue_num_str)
                    if 1 <= issue_num < 10**18 and issue_num not in seen:
                        seen.add(issue_num)
                        results.append({
                            'issue_number': issue_num,
                            'description': description.strip()
                        })
                except ValueError:
                    continue

        return results

    def parse_complex_markdown(self, body: str) -> Dict[str, Any]:
        """Parse complex markdown structure including tables, lists, and code blocks.

        Args:
            body: Issue body with complex markdown

        Returns:
            Structured data with sections, tables, and sub-issues
        """
        return {
            "sub_issues": self.parse_sub_issues(body),
            "sub_issues_with_context": self.parse_sub_issues_with_context(body),
            "sections": self._extract_sections(body),
            "title": self._extract_title(body),
            "has_checklist": "- [ ]" in body or "- [x]" in body,
            "has_code_blocks": "```" in body,
        }


__all__ = ["GitHubIssueParser"]
