"""Documentation checks mixin - checks for documentation completeness and organization."""

# Minimum number of navigation paths required in README for discoverability
MIN_README_PATHS = 2


class ChecksDocsMixin:
    """Mixin with documentation completeness and organization check methods."""

    # Paths that indicate user-facing/public code changes requiring doc updates
    # Paths indicating user-facing/public code. __init__.py and __main__.py
    # are only public when inside a public directory (commands, skills, etc.)
    # so they are checked separately via _is_public_init.
    PUBLIC_CODE_INDICATORS = [
        "/commands/",
        "/skills/",
        "/scenarios/",
        "/cli/",
        "/cli.py",
        "__main__.py",
        "setup.py",
        "pyproject.toml",
    ]

    def _check_documentation_updates(self, transcript: list[dict], session_id: str) -> bool:
        """Check if relevant documentation files were updated.

        Only flags missing docs when PUBLIC-FACING code was changed (commands,
        skills, CLIs, public APIs). Internal code changes (hooks, utilities,
        tests, configs) do not require documentation updates.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if docs updated or not applicable, False if needed but missing
        """
        public_code_modified = False
        doc_files_modified = False

        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            tool_name = block.get("name", "")
                            if tool_name in ["Write", "Edit"]:
                                tool_input = block.get("input", {})
                                file_path = tool_input.get("file_path", "").lower()

                                # Only flag public-facing code changes
                                is_code = any(
                                    file_path.endswith(ext) for ext in self.CODE_FILE_EXTENSIONS
                                )
                                is_public = any(
                                    indicator in file_path
                                    for indicator in self.PUBLIC_CODE_INDICATORS
                                )
                                # __init__.py is public only inside public dirs
                                if "__init__.py" in file_path and any(
                                    d in file_path
                                    for d in ["/commands/", "/skills/", "/scenarios/"]
                                ):
                                    is_public = True
                                if is_code and is_public:
                                    public_code_modified = True

                                # Check for doc files using class constant
                                if any(
                                    file_path.endswith(ext)
                                    if ext.startswith(".")
                                    else ext in file_path
                                    for ext in self.DOC_FILE_EXTENSIONS
                                ):
                                    doc_files_modified = True

        # Only flag if public-facing code was changed without doc updates
        if public_code_modified and not doc_files_modified:
            return False

        return True

    def _check_tutorial_needed(self, transcript: list[dict], session_id: str) -> bool:
        """Check if new feature needs tutorial/how-to.

        Detects new user-facing features that should have examples.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if tutorial exists or not needed, False if missing
        """
        # Look for new feature indicators
        feature_keywords = ["new feature", "add feature", "implement feature", "create feature"]
        has_new_feature = False

        for msg in transcript:
            if msg.get("type") == "user":
                content = str(msg.get("message", {}).get("content", "")).lower()
                if any(keyword in content for keyword in feature_keywords):
                    has_new_feature = True
                    break

        if not has_new_feature:
            return True  # No new feature, tutorial not needed

        # Check for example/tutorial files
        tutorial_patterns = ["example", "tutorial", "how_to", "guide", "demo"]
        has_tutorial = False

        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            tool_name = block.get("name", "")
                            if tool_name in ["Write", "Edit"]:
                                file_path = block.get("input", {}).get("file_path", "").lower()
                                if any(pattern in file_path for pattern in tutorial_patterns):
                                    has_tutorial = True
                                    break

        return has_tutorial

    def _check_presentation_needed(self, transcript: list[dict], session_id: str) -> bool:
        """Check if work needs presentation deck.

        Detects high-impact work that should be presented to stakeholders.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if presentation exists or not needed, False if missing
        """
        # This is a low-priority check, default to satisfied
        # Could be enhanced to detect high-impact work patterns
        return True

    def _check_feature_docs_discoverable(self, transcript: list[dict], session_id: str) -> bool:
        """Check if feature documentation is discoverable from multiple paths.

        Verifies new features have documentation discoverable from README and docs/ directory.
        This ensures users can find documentation through:
        1. README features/documentation section
        2. docs/ directory listing

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if docs are discoverable or not applicable, False if missing navigation
        """
        try:
            # Phase 1: Detect new features
            # Look for new commands, agents, skills, scenarios in Write/Edit operations
            new_features = []
            docs_file = None

            for msg in transcript:
                if msg.get("type") == "assistant" and "message" in msg:
                    content = msg["message"].get("content", [])
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "tool_use":
                                tool_name = block.get("name", "")
                                if tool_name in ["Write", "Edit"]:
                                    file_path = block.get("input", {}).get("file_path", "")

                                    # Detect new feature by file location
                                    if ".claude/commands/" in file_path and file_path.endswith(
                                        ".md"
                                    ):
                                        new_features.append(("command", file_path))
                                    elif ".claude/agents/" in file_path and file_path.endswith(
                                        ".md"
                                    ):
                                        new_features.append(("agent", file_path))
                                    elif ".claude/skills/" in file_path:
                                        new_features.append(("skill", file_path))
                                    elif ".claude/scenarios/" in file_path:
                                        new_features.append(("scenario", file_path))

                                    # Track docs file creation in docs/
                                    if "docs/" in file_path and file_path.endswith(".md"):
                                        docs_file = file_path

            # Edge case 1: No new features detected
            if not new_features:
                return True

            # Edge case 2: Docs-only session (no code files modified)
            # But NOT if the "docs" are actually feature definitions (.md files
            # in commands/agents/skills) — those ARE the feature, not just docs
            if self._is_docs_only_session(transcript) and not new_features:
                return True

            # Edge case 3: Internal changes (tools/, tests/, etc.)
            # If all features are in internal paths, pass
            internal_paths = [".claude/tools/", "tests/", ".claude/runtime/"]
            all_internal = all(
                any(internal in feature[1] for internal in internal_paths)
                for feature in new_features
            )
            if all_internal:
                return True

            # Phase 2: Check for docs file in docs/ directory
            if not docs_file:
                return False  # New feature but no docs file created

            # Phase 3: Verify 2+ navigation paths in README
            readme_paths_count = 0

            for msg in transcript:
                if msg.get("type") == "assistant" and "message" in msg:
                    content = msg["message"].get("content", [])
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "tool_use":
                                tool_name = block.get("name", "")
                                if tool_name in ["Write", "Edit"]:
                                    file_path = block.get("input", {}).get("file_path", "")

                                    # Check if README was edited
                                    if "readme.md" in file_path.lower():
                                        # Get the new content to check for documentation links
                                        new_string = block.get("input", {}).get("new_string", "")
                                        content_to_check = block.get("input", {}).get("content", "")
                                        full_content = new_string or content_to_check

                                        # Count references to the docs file
                                        if docs_file and full_content:
                                            # Extract just the filename from the path
                                            doc_filename = docs_file.split("/")[-1]
                                            # Count occurrences of the doc filename in README content
                                            readme_paths_count += full_content.count(doc_filename)

            # Need at least 2 navigation paths (e.g., Features section + Documentation section)
            if readme_paths_count < MIN_README_PATHS:
                return False

            # All checks passed
            return True

        except Exception as e:
            # Fail-open: Return True on errors to avoid blocking users
            self._log(f"PR content validation error (fail-open): {e}", "WARNING", exc_info=True)
            return True

    def _is_docs_only_session(self, transcript: list[dict]) -> bool:
        """Check if session only modified documentation files.

        Helper method to detect docs-only sessions where no code files were touched.

        Args:
            transcript: List of message dictionaries

        Returns:
            True if only .md files were modified, False if code files modified
        """
        try:
            code_modified = False
            docs_modified = False

            for msg in transcript:
                if msg.get("type") == "assistant" and "message" in msg:
                    content = msg["message"].get("content", [])
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "tool_use":
                                tool_name = block.get("name", "")
                                if tool_name in ["Write", "Edit"]:
                                    file_path = block.get("input", {}).get("file_path", "")

                                    # Check for code files using class constant
                                    if any(
                                        file_path.endswith(ext) for ext in self.CODE_FILE_EXTENSIONS
                                    ):
                                        code_modified = True

                                    # Check for doc files using class constant
                                    if any(
                                        file_path.endswith(ext)
                                        if ext.startswith(".")
                                        else ext in file_path
                                        for ext in self.DOC_FILE_EXTENSIONS
                                    ):
                                        docs_modified = True

            # Docs-only session if docs modified but no code files
            return docs_modified and not code_modified

        except Exception as e:
            # Fail-open: Return False on errors (assume code might be modified)
            self._log(
                f"Docs-only session detection error (fail-open): {e}", "WARNING", exc_info=True
            )
            return False

    def _check_docs_organization(self, transcript: list[dict], session_id: str) -> bool:
        """Check if investigation/session docs are organized properly.

        Verifies documentation is in correct directories.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if docs properly organized, False otherwise
        """
        # Check for doc files created in wrong locations
        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            if block.get("name") == "Write":
                                file_path = block.get("input", {}).get("file_path", "")

                                # Check for investigation/session docs in wrong places
                                if any(
                                    pattern in file_path.lower()
                                    for pattern in ["investigation", "session", "log"]
                                ):
                                    # Should be in .claude/runtime or .claude/docs
                                    if ".claude" not in file_path:
                                        return False

        return True

    def _check_investigation_docs(self, transcript: list[dict], session_id: str) -> bool:
        """Check if investigation findings were documented.

        Ensures exploration work is captured in persistent documentation.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if investigation documented, False if missing
        """
        # Look for investigation indicators
        investigation_keywords = [
            "investigate",
            "investigation",
            "explore",
            "exploration",
            "research",
            "analyze",
            "analyse",
            "analysis",
            "findings",
        ]

        has_investigation = False
        for msg in transcript:
            if msg.get("type") == "user":
                content = str(msg.get("message", {}).get("content", "")).lower()
                if any(keyword in content for keyword in investigation_keywords):
                    has_investigation = True
                    break

        if not has_investigation:
            return True  # No investigation, docs not needed

        # Check for documentation of findings
        doc_created = False
        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            if block.get("name") == "Write":
                                file_path = block.get("input", {}).get("file_path", "").lower()
                                if any(
                                    pattern in file_path for pattern in [".md", "readme", "doc"]
                                ):
                                    doc_created = True
                                    break

        return doc_created
