"""CI/PR checks mixin - checks for CI status and PR hygiene."""

import re

# Pre-compiled pattern for merge preference detection
_MERGE_PREFERENCE_PATTERN = re.compile(
    r"(never|must not|do not|don't).*merge.*without.*(permission|approval|explicit)",
    re.IGNORECASE | re.DOTALL,
)


class ChecksCiPrMixin:
    """Mixin with CI status and PR hygiene check methods."""

    # Sentinel to distinguish "not yet cached" from False result
    _NO_AUTO_MERGE_UNSET = object()

    def _user_prefers_no_auto_merge(self) -> bool:
        """Detect if user has set preference to never auto-merge PRs.

        Searches .claude/context/USER_PREFERENCES.md for pattern:
        "(never|must not|do not|don't) ... merge ... without ... (permission|approval|explicit)"

        Result is cached per-instance — the preference file doesn't change during a session.

        Returns:
            True if preference detected, False otherwise (fail-open on any error)
        """
        # Return cached result if already computed (avoids repeated file I/O)
        cached = getattr(self, "_no_auto_merge_cache", self._NO_AUTO_MERGE_UNSET)
        if cached is not self._NO_AUTO_MERGE_UNSET:
            return cached  # type: ignore[return-value]

        result = False
        try:
            preferences_path = self.project_root / ".claude" / "context" / "USER_PREFERENCES.md"

            if preferences_path.exists():
                content = preferences_path.read_text(encoding="utf-8")
                result = _MERGE_PREFERENCE_PATTERN.search(content) is not None

        except Exception as e:
            # Fail-open: any error returns False
            self._log(f"Error detecting merge preference: {e}", "WARNING", exc_info=True)

        self._no_auto_merge_cache = result
        return result

    def _check_ci_status_no_auto_merge(self, transcript: list[dict]) -> bool:
        """Check CI status WITHOUT requiring PR merge.

        Used when user preference "never merge without permission" is active.
        Treats "PR ready + CI passing" as valid completion state.

        Args:
            transcript: List of message dictionaries

        Returns:
            True if PR ready and CI passing, False if CI failing or draft PR
        """
        # Look for PR and CI indicators
        pr_mentioned = False
        ci_mentioned = False
        ci_passing = False
        is_draft = False

        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict):
                            if block.get("type") == "text":
                                text = str(block.get("text", "")).lower()

                                # Check for PR mentions
                                if any(
                                    keyword in text
                                    for keyword in ["pr #", "pull request", "created pr"]
                                ):
                                    pr_mentioned = True

                                # Check for draft PR
                                if "draft" in text and "pr" in text:
                                    is_draft = True

                                # Check for CI mentions
                                if any(
                                    keyword in text
                                    for keyword in [
                                        "ci",
                                        "github actions",
                                        "continuous integration",
                                        "checks",
                                    ]
                                ):
                                    ci_mentioned = True

                                    # Check for passing indicators
                                    if any(
                                        keyword in text
                                        for keyword in [
                                            "passing",
                                            "passed",
                                            "success",
                                            "ready for review",
                                            "ready for your review",
                                        ]
                                    ):
                                        ci_passing = True

                                    # Check for failing indicators
                                    if any(
                                        keyword in text
                                        for keyword in ["failing", "failed", "error"]
                                    ):
                                        return False

        # If draft PR, not ready
        if is_draft:
            return False

        # If CI mentioned and failing, return False
        if ci_mentioned and not ci_passing:
            return False

        # If PR mentioned with CI passing, or PR ready indicators
        if pr_mentioned and (ci_passing or not ci_mentioned):
            return True

        # If neither PR nor CI mentioned, assume satisfied (fail-open)
        if not pr_mentioned and not ci_mentioned:
            return True

        # Default: if we have indicators but unclear state, be conservative
        return ci_passing or not ci_mentioned

    def _check_ci_status(self, transcript: list[dict], session_id: str) -> bool:
        """Check if CI passing/mergeable (preference-aware).

        This method delegates to the appropriate CI checker based on user preference:
        - If user prefers no auto-merge: use _check_ci_status_no_auto_merge()
        - Otherwise: use standard CI check logic (requires merge indicators)

        Heuristics (standard mode):
        - Look for CI status checks (gh pr view, CI commands)
        - Check for "passing", "success", "mergeable" (strict - requires "mergeable")
        - Look for failure indicators

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if CI passing or not applicable, False if CI failing
        """
        # Check user preference first (lazy detection)
        if self._user_prefers_no_auto_merge():
            return self._check_ci_status_no_auto_merge(transcript)

        # Standard logic for users without preference (strict - requires "mergeable")
        ci_mentioned = False
        mergeable_mentioned = False

        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict):
                            # Check text content for CI mentions
                            if block.get("type") == "text":
                                text = str(block.get("text", ""))
                                text_lower = text.lower()

                                if any(
                                    keyword in text_lower
                                    for keyword in [
                                        "ci",
                                        "github actions",
                                        "continuous integration",
                                    ]
                                ):
                                    ci_mentioned = True

                                # Standard mode: only accept explicit "mergeable" or "passing" + "mergeable"
                                # Don't accept just "ready" or "passing" alone
                                if "mergeable" in text_lower:
                                    mergeable_mentioned = True

                                # Check for failure indicators
                                if any(
                                    keyword in text_lower
                                    for keyword in ["failing", "failed", "error"]
                                ):
                                    return False

        # If CI not mentioned, consider satisfied (not applicable)
        if not ci_mentioned:
            return True

        # Standard mode requires explicit "mergeable" indicator
        return mergeable_mentioned

    def _check_pr_description(self, transcript: list[dict], session_id: str) -> bool:
        """Check if PR description is clear and complete.

        Verifies PR has summary, test plan, and context.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if PR description adequate, False if missing or incomplete
        """
        # Look for PR creation (gh pr create)
        pr_created = False
        pr_body = ""

        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            if block.get("name") == "Bash":
                                command = block.get("input", {}).get("command", "")
                                if "gh pr create" in command:
                                    pr_created = True
                                    pr_body = command.lower()

        if not pr_created:
            return True  # No PR, check not applicable

        # Check PR body for required sections
        required_sections = ["summary", "test", "plan"]
        has_all_sections = all(section in pr_body for section in required_sections)

        return has_all_sections

    def _check_review_responses(self, transcript: list[dict], session_id: str) -> bool:
        """Check if PR review comments were addressed.

        Verifies reviewer feedback was acknowledged and resolved.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if reviews addressed or no reviews, False if unaddressed feedback
        """
        # Look for review-related activity in user messages
        review_keywords = ["review", "feedback", "comment", "requested changes"]
        has_reviews = False

        for msg in transcript:
            if msg.get("type") == "user":
                content = str(msg.get("message", {}).get("content", "")).lower()
                if any(keyword in content for keyword in review_keywords):
                    has_reviews = True
                    break

        if not has_reviews:
            return True  # No reviews to address

        # Look for response indicators
        response_keywords = ["addressed", "fixed", "updated", "changed", "resolved"]
        has_responses = False

        for msg in transcript:
            if msg.get("type") == "assistant":
                content = msg.get("message", {}).get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text = str(block.get("text", "")).lower()
                            if any(keyword in text for keyword in response_keywords):
                                has_responses = True
                                break

        return has_responses

    def _check_branch_rebase(self, transcript: list[dict], session_id: str) -> bool:
        """Check if branch needs rebase on main.

        Verifies branch is up to date with main.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if branch is current, False if needs rebase
        """
        # Look for git status or branch checks
        for msg in transcript:
            if msg.get("type") == "tool_result":
                output = str(msg.get("message", {}).get("content", "")).lower()

                # Check for "behind" indicators
                if "behind" in output or "diverged" in output:
                    return False

                # Check for "up to date" indicators
                if "up to date" in output or "up-to-date" in output:
                    return True

        # Default to satisfied if no information
        return True

    def _check_ci_precommit_mismatch(self, transcript: list[dict], session_id: str) -> bool:
        """Check for CI failures contradicting passing pre-commit.

        Identifies divergence between local pre-commit and CI checks.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if no mismatch, False if divergence detected
        """
        # Look for pre-commit passing
        precommit_passed = False
        ci_failed = False

        for msg in transcript:
            if msg.get("type") in ["assistant", "tool_result"]:
                content_str = str(msg.get("message", {})).lower()

                # Check for pre-commit success
                if "pre-commit" in content_str or "precommit" in content_str:
                    if "passed" in content_str or "success" in content_str:
                        precommit_passed = True

                # Check for CI failure
                if "ci" in content_str or "github actions" in content_str:
                    if "failed" in content_str or "failing" in content_str:
                        ci_failed = True

        # If both conditions met, there's a mismatch
        if precommit_passed and ci_failed:
            return False

        return True
