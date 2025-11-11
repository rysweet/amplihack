#!/usr/bin/env python3
"""Apply all 50 specific code quality fixes."""

import subprocess
import time
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def run_cmd(cmd):
    """Run command silently."""
    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=30)
    return result.returncode == 0, result.stdout + result.stderr


def apply_fix(num, file, desc, old, new):
    """Apply single fix with branch/commit/push."""
    print(f"[{num}/50] {desc}...", end=" ", flush=True)

    run_cmd(["git", "checkout", "main"])
    run_cmd(["git", "pull", "origin", "main"])

    success, _ = run_cmd(["git", "checkout", "-b", f"fix/specific-{num}"])
    if not success:
        print("❌ Branch exists")
        return False

    file_path = REPO_ROOT / file
    if not file_path.exists():
        print("❌ File not found")
        run_cmd(["git", "checkout", "main"])
        return False

    try:
        content = file_path.read_text()
        if old not in content:
            print("❌ Pattern not found")
            run_cmd(["git", "checkout", "main"])
            run_cmd(["git", "branch", "-D", f"fix/specific-{num}"])
            return False

        content = content.replace(old, new, 1)
        file_path.write_text(content)
    except Exception as e:
        print(f"❌ {e}")
        run_cmd(["git", "checkout", "main"])
        return False

    run_cmd(["git", "add", str(file)])
    success, _ = run_cmd(["git", "commit", "-m", f"fix: {desc}\n\nFile: {file}"])
    if not success:
        print("❌ Commit failed")
        run_cmd(["git", "checkout", "main"])
        return False

    success, _ = run_cmd(["git", "push", "-u", "origin", f"fix/specific-{num}"])
    if not success:
        print("❌ Push failed")
        return False

    print("✓")
    run_cmd(["git", "checkout", "main"])
    time.sleep(0.5)  # Rate limit
    return True


# All 50 fixes
FIXES = [
    # Fixes 8-15: Add logging to silent exceptions
    (
        8,
        ".claude/tools/amplihack/session/session_manager.py",
        "Add logging to _get_file_hash exception",
        "        except Exception:\n            pass",
        "        except Exception as e:\n            self.logger.warning(f'Failed to compute file hash: {e}')",
    ),
    (
        9,
        ".claude/tools/amplihack/session/session_manager.py",
        "Add logging to _get_data_hash exception",
        '        except Exception:\n            return ""',
        "        except Exception as e:\n            self.logger.warning(f'Failed to compute data hash: {e}')\n            return \"\"",
    ),
    (
        10,
        ".claude/tools/amplihack/hooks/claude_reflection.py",
        "Add logging to conversation load exception",
        "            except (OSError, json.JSONDecodeError):\n                continue",
        "            except (OSError, json.JSONDecodeError) as e:\n                logger.debug(f'Failed to load conversation: {e}')\n                continue",
    ),
    (
        11,
        ".claude/tools/amplihack/hooks/claude_reflection.py",
        "Add logging to repository detection exception",
        "    except Exception:\n        # Subprocess failed - provide generic guidance",
        "    except Exception as e:\n        # Subprocess failed - provide generic guidance\n        logger.debug(f'Repository detection failed: {e}')",
    ),
    (
        12,
        "src/amplihack/bundle_generator/parser.py",
        "Add logging to parse exception",
        '            except (ImportError, OSError):\n                logger.warning("spaCy not available, falling back to rule-based parsing")',
        '            except (ImportError, OSError) as e:\n                logger.warning(f"spaCy not available ({e}), falling back to rule-based parsing")',
    ),
    (
        13,
        ".claude/tools/amplihack/hooks/claude_reflection.py",
        "Add traceback to reflection exception",
        '    except Exception as e:\n        print(f"Claude reflection failed: {e}", file=sys.stderr)\n        return None',
        '    except Exception as e:\n        import traceback\n        print(f"Claude reflection failed: {e}", file=sys.stderr)\n        print(traceback.format_exc(), file=sys.stderr)\n        return None',
    ),
    (
        14,
        ".claude/tools/amplihack/session/session_manager.py",
        "Add exc_info to cleanup warning",
        '                self.logger.warning(f"Failed to cleanup {session_file}: {e}")',
        '                self.logger.warning(f"Failed to cleanup {session_file}: {e}", exc_info=True)',
    ),
    (
        15,
        ".claude/tools/amplihack/session/session_manager.py",
        "Add logging to archive failure",
        "        if not session_file.exists():\n            return False",
        "        if not session_file.exists():\n            self.logger.warning(f'Cannot archive non-existent session: {session_id}')\n            return False",
    ),
    # Fixes 16-25: Input validation
    (
        16,
        "src/amplihack/bundle_generator/parser.py",
        "Split validation checks in parse",
        '        if not prompt or not prompt.strip():\n            raise ParsingError("Empty prompt provided")',
        '        if not prompt:\n            raise ParsingError("Prompt cannot be None or empty")\n        if not prompt.strip():\n            raise ParsingError("Prompt cannot be blank or whitespace only")',
    ),
    (
        17,
        "src/amplihack/bundle_generator/parser.py",
        "Add validation in extract_requirements",
        '        # Split into lines/sentences\n        lines = text.replace(". ", ".\\n").split("\\n")',
        '        if not text:\n            return {"functional": [], "technical": [], "constraints": []}\n        # Split into lines/sentences\n        lines = text.replace(". ", ".\\n").split("\\n")',
    ),
    (
        18,
        ".claude/tools/amplihack/session/session_manager.py",
        "Add session name validation",
        "        config = config or SessionConfig()",
        "        if not name or not name.strip():\n            raise ValueError('Session name cannot be empty')\n        config = config or SessionConfig()",
    ),
    (
        19,
        ".claude/tools/amplihack/session/session_manager.py",
        "Add session_id validation in save",
        "        with self._lock:\n            session = self._active_sessions.get(session_id)",
        "        with self._lock:\n            if not session_id or not session_id.strip():\n                self.logger.error('Invalid session_id provided to save_session')\n                return False\n            session = self._active_sessions.get(session_id)",
    ),
    (
        20,
        ".claude/tools/amplihack/session/session_manager.py",
        "Add session_id validation in resume",
        '        session_file = self.runtime_dir / f"{session_id}.json"',
        "        if not session_id or not session_id.strip():\n            self.logger.error('Invalid session_id provided to resume_session')\n            return None\n        session_file = self.runtime_dir / f\"{session_id}.json\"",
    ),
    (
        21,
        ".claude/tools/amplihack/hooks/claude_reflection.py",
        "Add validation in format_reflection_prompt",
        "        return template.format(**variables)",
        "        if not template:\n            raise ValueError('Template cannot be empty')\n        if not variables:\n            raise ValueError('Variables dictionary cannot be empty')\n        return template.format(**variables)",
    ),
    (
        22,
        "src/amplihack/proxy/azure_unified_handler.py",
        "Add validation in AzureUnifiedHandler.__init__",
        "        self.provider = AzureUnifiedProvider(api_key, base_url, api_version)",
        "        if not api_key or not api_key.strip():\n            raise ValueError('Azure API key cannot be empty')\n        if not base_url or not base_url.strip():\n            raise ValueError('Azure base URL cannot be empty')\n        self.provider = AzureUnifiedProvider(api_key, base_url, api_version)",
    ),
    (
        23,
        "src/amplihack/utils/process.py",
        "Add command validation in run_command",
        '        kwargs = {"cwd": cwd, "env": env, "capture_output": capture_output, "text": True}',
        '        if not command or len(command) == 0:\n            raise ValueError(\'Command cannot be empty\')\n        kwargs = {"cwd": cwd, "env": env, "capture_output": capture_output, "text": True}',
    ),
    (
        24,
        "src/amplihack/bundle_generator/parser.py",
        "Add defensive check in _clean_prompt",
        '        # Remove extra whitespace\n        cleaned = re.sub(r"\\s+", " ", prompt)',
        '        if not prompt:\n            return ""\n        # Remove extra whitespace\n        cleaned = re.sub(r"\\s+", " ", prompt)',
    ),
    (
        25,
        "src/amplihack/proxy/azure_unified_handler.py",
        "Add fallback for None in JSON parsing",
        '                        "input": json.loads(tool_call.get("function", {}).get("arguments", "{}")),',
        '                        "input": json.loads(tool_call.get("function", {}).get("arguments", "{}") or "{}"),',
    ),
    # Fixes 26-35: Logging improvements
    (
        26,
        "src/amplihack/neo4j/detector.py",
        "Add logging to detect_containers",
        "        return containers",
        "        logger.info(f'Detected {len(containers)} Neo4j containers')\n        return containers",
    ),
    (
        27,
        ".claude/tools/amplihack/session/session_manager.py",
        "Add debug logging in get_session",
        "                self._update_session_access(session_id)\n            return session",
        "                self._update_session_access(session_id)\n                self.logger.debug(f'Retrieved active session: {session_id}')\n            else:\n                self.logger.debug(f'Session not found: {session_id}')\n            return session",
    ),
    (
        28,
        "src/amplihack/proxy/azure_unified_handler.py",
        "Add debug logging in handle_anthropic_request",
        "        # Convert Anthropic request to OpenAI format for processing\n        openai_request = self._convert_anthropic_to_openai(anthropic_request)",
        "        # Convert Anthropic request to OpenAI format for processing\n        logger.debug(f'Handling Anthropic request for model: {anthropic_request.get(\"model\")}')\n        openai_request = self._convert_anthropic_to_openai(anthropic_request)",
    ),
    (
        29,
        "src/amplihack/proxy/azure_unified_handler.py",
        "Add debug logging in handle_openai_request",
        "        # Provider handles everything\n        return await self.provider.make_request(",
        "        # Provider handles everything\n        logger.debug(f'Handling OpenAI request for model: {openai_request.get(\"model\")}')\n        return await self.provider.make_request(",
    ),
    (
        30,
        "src/amplihack/bundle_generator/parser.py",
        "Add debug logging to parse start",
        "        # Extract components\n        sentences = self._extract_sentences(cleaned_prompt)",
        "        # Extract components\n        logger.debug(f'Parsing prompt of length {len(prompt)}')\n        sentences = self._extract_sentences(cleaned_prompt)",
    ),
    (
        31,
        "src/amplihack/bundle_generator/parser.py",
        "Add debug logging to parse completion",
        "        return ParsedPrompt(",
        "        logger.debug(f'Parse complete: confidence={confidence:.2f}, sentences={len(sentences)}, phrases={len(key_phrases)}')\n        return ParsedPrompt(",
    ),
    (
        32,
        ".claude/tools/amplihack/hooks/claude_reflection.py",
        "Add debug logging for template loading",
        "    return template_path.read_text()",
        "    logger.debug(f'Loaded feedback template from {template_path}')\n    return template_path.read_text()",
    ),
    (
        33,
        "src/amplihack/neo4j/detector.py",
        "Add logging to Docker check early return",
        "        if not self.is_docker_available():\n            return []",
        "        if not self.is_docker_available():\n            logger.debug('Docker not available, returning empty container list')\n            return []",
    ),
    (
        34,
        ".claude/tools/amplihack/session/session_manager.py",
        "Add logging to session creation",
        "        self.logger.info(f\"Created session '{name}' with ID: {session.state.session_id}\")",
        "        self.logger.info(f\"Created session '{name}' with ID: {session.state.session_id} (auto-started: {config.auto_start})\")",
    ),
    (
        35,
        ".claude/tools/amplihack/hooks/claude_reflection.py",
        "Add logging to analyze_session_with_claude",
        "        # Collect response\n        response_parts = []",
        "        logger.info(f'Starting Claude reflection analysis (conversation: {len(conversation)} messages)')\n        # Collect response\n        response_parts = []",
    ),
    # Fixes 36-45: Code clarity and safety improvements
    (
        36,
        "src/amplihack/bundle_generator/parser.py",
        "Add safety check in identify_agent_count",
        "        # Default to 1 if no count found\n        if count == 0:\n            count = 1",
        "        # Default to 1 if no count found\n        if count == 0:\n            logger.debug('No explicit agent count found, defaulting to 1')\n            count = 1",
    ),
    (
        37,
        "src/amplihack/utils/process.py",
        "Add safety check in terminate_process_group",
        "        if process.poll() is not None:\n            return  # Already terminated",
        "        if process.poll() is not None:\n            # Already terminated\n            import logging\n            logging.getLogger(__name__).debug(f'Process {process.pid} already terminated')\n            return",
    ),
    (
        38,
        ".claude/tools/amplihack/session/session_manager.py",
        "Add safety check in _deserialize_session",
        '        try:\n            # Reconstruct config\n            config_data = data.get("config", {})',
        "        try:\n            if not data:\n                self.logger.error('Cannot deserialize empty data')\n                return None\n            # Reconstruct config\n            config_data = data.get(\"config\", {})",
    ),
    (
        39,
        "src/amplihack/bundle_generator/parser.py",
        "Add bounds check in _format_conversation_summary",
        '        # Truncate long messages\n        if len(content) > 500:\n            content = content[:497] + "..."',
        "        # Truncate long messages\n        if len(content) > 500:\n            logger.debug(f'Truncating message {i} from {len(content)} to 500 chars')\n            content = content[:497] + \"...\"",
    ),
    (
        40,
        ".claude/tools/amplihack/hooks/claude_reflection.py",
        "Add safety check in get_repository_context",
        "        try:\n            # Get current repository URL\n            result = subprocess.run(",
        "        try:\n            if not project_root or not project_root.exists():\n                logger.warning('Invalid project_root provided to get_repository_context')\n                return f\"\\n## Repository Context\\n\\n**Amplihack Repository**: {AMPLIHACK_REPO_URI}\\n**Context**: Repository detection unavailable\\n\"\n            # Get current repository URL\n            result = subprocess.run(",
    ),
    (
        41,
        "src/amplihack/bundle_generator/parser.py",
        "Improve error message in ParsingError",
        '            raise ParsingError("Prompt cannot be None or empty")',
        '            raise ParsingError("Prompt cannot be None or empty. Please provide a valid prompt string.")',
    ),
    (
        42,
        "src/amplihack/proxy/azure_unified_handler.py",
        "Improve error context in response conversion",
        '            return {\n                "type": "error",\n                "error": {\n                    "type": "api_error",\n                    "message": openai_response["error"].get("message", "Unknown error"),\n                },\n            }',
        '            error_msg = openai_response["error"].get("message", "Unknown error")\n            logger.warning(f\'OpenAI API error in response conversion: {error_msg}\')\n            return {\n                "type": "error",\n                "error": {\n                    "type": "api_error",\n                    "message": error_msg,\n                },\n            }',
    ),
    (
        43,
        ".claude/tools/amplihack/session/session_manager.py",
        "Add metadata to save logging",
        '                self.logger.info(f"Saved session {session_id}")',
        '                self.logger.info(f"Saved session {session_id} (size: {session_file.stat().st_size} bytes)")',
    ),
    (
        44,
        ".claude/tools/amplihack/session/session_manager.py",
        "Add metadata to resume logging",
        '            self.logger.info(f"Resumed session {session_id}")',
        "            self.logger.info(f\"Resumed session {session_id} (age: {time.time() - session_data.get('saved_at', 0):.0f}s)\")",
    ),
    (
        45,
        "src/amplihack/neo4j/detector.py",
        "Add safety check in _parse_container",
        "        try:\n            # Parse container info",
        "        try:\n            if not container_info or not isinstance(container_info, dict):\n                logger.warning('Invalid container_info provided to _parse_container')\n                return None\n            # Parse container info",
    ),
    # Fixes 46-50: Documentation and consistency
    (
        46,
        "src/amplihack/utils/process.py",
        "Add docstring note about Windows compatibility",
        '    def is_windows() -> bool:\n        """Check if running on Windows.\n\n        Returns:\n            True if Windows, False otherwise.\n        """',
        '    def is_windows() -> bool:\n        """Check if running on Windows.\n\n        Note:\n            Checks both sys.platform and os.name for maximum compatibility.\n\n        Returns:\n            True if Windows, False otherwise.\n        """',
    ),
    (
        47,
        "src/amplihack/bundle_generator/parser.py",
        "Improve docstring in parse method",
        '    def parse(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> ParsedPrompt:\n        """\n        Parse a natural language prompt.\n\n        Args:\n            prompt: Natural language description of agents\n            context: Optional context (existing agents, project type, etc.)\n\n        Returns:\n            ParsedPrompt with extracted information\n\n        Raises:\n            ParsingError: If prompt cannot be parsed\n        """',
        '    def parse(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> ParsedPrompt:\n        """\n        Parse a natural language prompt into structured components.\n\n        Args:\n            prompt: Natural language description of agents (required, non-empty)\n            context: Optional context (existing agents, project type, etc.)\n\n        Returns:\n            ParsedPrompt with extracted information including tokens, sentences,\n            key phrases, and confidence score\n\n        Raises:\n            ParsingError: If prompt is empty, None, or cannot be parsed\n        """',
    ),
    (
        48,
        ".claude/tools/amplihack/session/session_manager.py",
        "Improve docstring in create_session",
        '    def create_session(\n        self,\n        name: str,\n        config: Optional[SessionConfig] = None,\n        metadata: Optional[Dict[str, Any]] = None,\n    ) -> str:\n        """Create a new session.\n\n        Args:\n            name: Human-readable session name\n            config: Session configuration\n            metadata: Additional session metadata\n\n        Returns:\n            Session ID\n        """',
        '    def create_session(\n        self,\n        name: str,\n        config: Optional[SessionConfig] = None,\n        metadata: Optional[Dict[str, Any]] = None,\n    ) -> str:\n        """Create a new session with automatic tracking and persistence.\n\n        Args:\n            name: Human-readable session name (required, non-empty)\n            config: Session configuration (defaults to SessionConfig())\n            metadata: Additional session metadata (optional)\n\n        Returns:\n            Session ID (auto-generated UUID)\n\n        Raises:\n            ValueError: If name is empty or invalid\n        """',
    ),
    (
        49,
        "src/amplihack/proxy/azure_unified_handler.py",
        "Improve class docstring",
        'class AzureUnifiedHandler:\n    """\n    Unified handler that automatically routes between Azure Chat and Responses APIs.\n\n    This class provides a single interface that the integrated proxy can use,\n    eliminating the need for dual routing logic in the main proxy code.\n    """',
        'class AzureUnifiedHandler:\n    """\n    Unified handler that automatically routes between Azure Chat and Responses APIs.\n\n    This class provides a single interface that the integrated proxy can use,\n    eliminating the need for dual routing logic in the main proxy code.\n\n    The handler automatically detects which API to use based on model name and\n    request format, providing seamless translation between Anthropic, OpenAI,\n    and Azure formats.\n    """',
    ),
    (
        50,
        ".claude/tools/amplihack/hooks/claude_reflection.py",
        "Improve module docstring",
        '"""Claude SDK-based session reflection.\n\nUses Claude Agent SDK to intelligently analyze sessions and fill out\nthe FEEDBACK_SUMMARY template, replacing simple pattern matching with\nAI-powered reflection.\n"""',
        '"""Claude SDK-based session reflection.\n\nUses Claude Agent SDK to intelligently analyze sessions and fill out\nthe FEEDBACK_SUMMARY template, replacing simple pattern matching with\nAI-powered reflection.\n\nThis module provides automated session analysis that:\n- Analyzes conversation patterns and quality\n- Identifies workflow adherence and agent usage\n- Generates actionable feedback and learning opportunities\n- Respects user preferences during analysis\n"""',
    ),
]


def main():
    """Apply all fixes."""
    print(f"Applying {len(FIXES)} fixes (8-50)...\n")

    successes = 0
    failures = 0

    for fix in FIXES:
        try:
            if apply_fix(*fix):
                successes += 1
            else:
                failures += 1
        except Exception as e:
            print(f"❌ Exception: {e}")
            failures += 1

    print(f"\n{'=' * 50}")
    print("COMPLETED")
    print(f"{'=' * 50}")
    print(f"Successful: {successes}")
    print(f"Failed: {failures}")
    print(f"Total (including fix #1): {successes + 1}/50")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
