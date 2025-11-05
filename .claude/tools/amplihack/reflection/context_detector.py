#!/usr/bin/env python3
"""
Context detector for reflection system.

Detects whether work is on amplihack-internal code or user projects,
enabling context-aware reflection prompts and repository routing.
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class WorkContext:
    """Work context information."""

    is_amplihack_internal: bool
    repository_url: Optional[str]
    repository_name: Optional[str]
    working_directory: Path


class ContextDetector:
    """Detects work context for reflection system."""

    # Known amplihack repository identifiers
    AMPLIHACK_REPO_PATTERNS = [
        "MicrosoftHackathon2025-AgenticCoding",
        "amplihack",
        "agentic-coding",
    ]

    def __init__(self, working_dir: Optional[Path] = None):
        """Initialize context detector.

        Args:
            working_dir: Working directory to analyze (defaults to cwd)
        """
        self.working_dir = working_dir or Path.cwd()

    def detect_context(self) -> WorkContext:
        """Detect current work context.

        Returns:
            WorkContext with detection results
        """
        # Get git remote URL
        repo_url = self._get_git_remote_url()
        repo_name = self._extract_repo_name(repo_url) if repo_url else None

        # Check if this is amplihack-internal work
        is_amplihack = self._is_amplihack_repository(repo_url, repo_name)

        return WorkContext(
            is_amplihack_internal=is_amplihack,
            repository_url=repo_url,
            repository_name=repo_name,
            working_directory=self.working_dir,
        )

    def _get_git_remote_url(self) -> Optional[str]:
        """Get git remote URL for current directory.

        Returns:
            Remote URL string, or None if not a git repo
        """
        try:
            result = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass

        return None

    def _extract_repo_name(self, url: Optional[str]) -> Optional[str]:
        """Extract repository name from git URL.

        Args:
            url: Git remote URL

        Returns:
            Repository name, or None if cannot extract
        """
        if not url:
            return None

        # Handle both HTTPS and SSH URLs
        # https://github.com/user/repo.git -> repo
        # git@github.com:user/repo.git -> repo
        try:
            # Remove .git suffix if present
            if url.endswith(".git"):
                url = url[:-4]

            # Extract last part of path
            if "/" in url:
                return url.split("/")[-1]
            elif ":" in url:  # SSH format
                return url.split(":")[-1].split("/")[-1]
        except (IndexError, AttributeError):
            pass

        return None

    def _is_amplihack_repository(
        self, repo_url: Optional[str], repo_name: Optional[str]
    ) -> bool:
        """Check if repository is amplihack-internal.

        Args:
            repo_url: Repository URL
            repo_name: Repository name

        Returns:
            True if amplihack-internal repository
        """
        if not repo_url and not repo_name:
            return False

        # Check exact repo name match against patterns
        if repo_name:
            repo_name_lower = repo_name.lower()
            for pattern in self.AMPLIHACK_REPO_PATTERNS:
                pattern_lower = pattern.lower()
                # Exact match (e.g., "amplihack")
                if repo_name_lower == pattern_lower:
                    return True
                # Pattern at start with hyphen (e.g., "amplihack-fork")
                # This ensures "not-amplihack" doesn't match
                if repo_name_lower.startswith(pattern_lower + "-"):
                    return True

        # Also check URL for pattern matches (in case repo name extraction failed)
        if repo_url:
            url_lower = repo_url.lower()
            for pattern in self.AMPLIHACK_REPO_PATTERNS:
                pattern_lower = pattern.lower()
                # Pattern should be preceded by / and followed by . or / or end of string
                # This prevents "not-amplihack" from matching "amplihack"
                if (
                    f"/{pattern_lower}.git" in url_lower
                    or url_lower.endswith(f"/{pattern_lower}")
                ):
                    return True

        return False

    def get_reflection_prompt_template(self, context: Optional[WorkContext] = None) -> str:
        """Get appropriate reflection prompt template for context.

        Args:
            context: Work context (detects if not provided)

        Returns:
            Reflection prompt template string
        """
        if context is None:
            context = self.detect_context()

        if context.is_amplihack_internal:
            return self._get_amplihack_internal_template()
        else:
            return self._get_user_project_template()

    def _get_amplihack_internal_template(self) -> str:
        """Get reflection template for amplihack-internal work.

        Returns:
            Template string
        """
        return """You are analyzing a completed Claude Code session working on **amplihack framework internals**.

## Session Conversation

The session had {message_count} messages. Here are key excerpts:

{conversation_summary}

## Your Task - Framework Development Analysis

Please analyze this session and fill out the following feedback template:

{template}

## Guidelines for Framework Work

1. **Framework Philosophy Adherence** - Did the work follow amplihack's ruthless simplicity principles?
2. **Agent Design** - Were agents used appropriately? Is there proper separation of concerns?
3. **Regenerability** - Can these changes be regenerated from specifications?
4. **User Impact** - How will these internal changes affect end users?
5. **Self-Improvement** - What did we learn about the framework itself?
6. **Testing** - Are framework features properly tested?

## Focus Areas

- Philosophy compliance (ruthless simplicity, zero-BS, modular design)
- Agent orchestration effectiveness
- Framework feature quality
- Documentation and specifications
- Integration with existing framework patterns

Please provide the filled-out template now, focusing on framework development concerns.
"""

    def _get_user_project_template(self) -> str:
        """Get reflection template for user project work.

        Returns:
            Template string
        """
        return """You are analyzing a completed Claude Code session working on a **user project**.

## Session Conversation

The session had {message_count} messages. Here are key excerpts:

{conversation_summary}

## Your Task - Project Development Analysis

Please analyze this session and fill out the following feedback template:

{template}

## Guidelines for User Project Work

1. **User Requirements** - Were user requirements understood and met?
2. **Code Quality** - Is the code clean, maintainable, and well-tested?
3. **Workflow Adherence** - Did Claude follow the DEFAULT_WORKFLOW.md steps?
4. **Agent Usage** - Which specialized agents were used effectively?
5. **User Satisfaction** - Were interactions smooth and productive?
6. **Learning Opportunities** - What could improve future similar sessions?

## Focus Areas

- User requirement fulfillment
- Code quality and maintainability
- Workflow process compliance
- Agent coordination and effectiveness
- Communication clarity
- Problem-solving approach

Please provide the filled-out template now, focusing on user project development concerns.
"""

    def get_issue_repository(self, context: Optional[WorkContext] = None) -> Optional[str]:
        """Get target repository for reflection issues.

        Args:
            context: Work context (detects if not provided)

        Returns:
            Repository identifier (owner/repo format), or None for current repo
        """
        if context is None:
            context = self.detect_context()

        if context.is_amplihack_internal:
            # Issues for amplihack work go to amplihack repo
            # If we're already in it, return None (use current repo)
            # Otherwise, return explicit amplihack repo
            return None  # Current repo
        else:
            # Issues for user project work go to current repo
            return None  # Current repo

        # Note: In the future, we could route to specific repos:
        # return "rysweet/MicrosoftHackathon2025-AgenticCoding"


# Convenience functions for direct use
def detect_work_context(working_dir: Optional[Path] = None) -> WorkContext:
    """Detect work context for current directory.

    Args:
        working_dir: Working directory (defaults to cwd)

    Returns:
        WorkContext with detection results
    """
    detector = ContextDetector(working_dir)
    return detector.detect_context()


def get_reflection_prompt(
    working_dir: Optional[Path] = None, context: Optional[WorkContext] = None
) -> str:
    """Get appropriate reflection prompt template.

    Args:
        working_dir: Working directory (defaults to cwd)
        context: Pre-detected context (detects if not provided)

    Returns:
        Reflection prompt template string
    """
    detector = ContextDetector(working_dir)
    return detector.get_reflection_prompt_template(context)


def get_issue_target_repo(
    working_dir: Optional[Path] = None, context: Optional[WorkContext] = None
) -> Optional[str]:
    """Get target repository for reflection issues.

    Args:
        working_dir: Working directory (defaults to cwd)
        context: Pre-detected context (detects if not provided)

    Returns:
        Repository identifier, or None for current repo
    """
    detector = ContextDetector(working_dir)
    return detector.get_issue_repository(context)


# For testing
if __name__ == "__main__":
    import sys

    detector = ContextDetector()
    context = detector.detect_context()

    print("Work Context Detection")
    print("=" * 70)
    print(f"Working Directory: {context.working_directory}")
    print(f"Repository URL: {context.repository_url or 'Not detected'}")
    print(f"Repository Name: {context.repository_name or 'Not detected'}")
    print(f"Is Amplihack Internal: {context.is_amplihack_internal}")
    print()
    print("Reflection Prompt Template:")
    print("-" * 70)
    print(detector.get_reflection_prompt_template(context)[:500] + "...")
    print()
    print(f"Issue Target Repo: {detector.get_issue_repository(context) or 'Current repository'}")
