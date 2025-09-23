#!/usr/bin/env python3
"""
Claude Code hook for Azure OpenAI continuation control.
Prevents premature stopping when using Azure OpenAI models through the proxy.
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Clean import setup
sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from paths import get_project_root

    project_root = get_project_root()
except ImportError:
    # Fallback for standalone execution
    project_root = Path(__file__).parent.parent.parent.parent.parent

# Directories - use .claude at project root (not nested)
LOG_DIR = project_root / ".claude" / "runtime" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def log(message: str, level: str = "INFO"):
    """Simple logging to file"""
    timestamp = datetime.now().isoformat()
    log_file = LOG_DIR / "stop_azure_continuation.log"

    try:
        with open(log_file, "a") as f:
            f.write(f"[{timestamp}] {level}: {message}\n")
    except Exception:
        # Silently fail - don't disrupt the hook
        pass


def is_proxy_active() -> bool:
    """Check if Azure OpenAI proxy is active.

    Returns:
        True if proxy is active, False otherwise.
    """
    try:
        # Check for proxy environment variables
        base_url = os.environ.get("ANTHROPIC_BASE_URL", "")

        # Proxy is active if ANTHROPIC_BASE_URL is set to localhost
        if "localhost" in base_url or "127.0.0.1" in base_url:
            log(f"Proxy detected via ANTHROPIC_BASE_URL: {base_url}")
            return True

        # Check for other proxy indicators
        if os.environ.get("CLAUDE_CODE_PROXY_LAUNCHER"):
            log("Proxy detected via CLAUDE_CODE_PROXY_LAUNCHER")
            return True

        if os.environ.get("AZURE_OPENAI_KEY"):
            log("Proxy detected via AZURE_OPENAI_KEY")
            return True

        # Check if we're running with Azure config
        if os.environ.get("OPENAI_API_KEY") and os.environ.get("OPENAI_BASE_URL"):
            openai_url = os.environ.get("OPENAI_BASE_URL", "")
            if "azure" in openai_url.lower() or "openai.azure.com" in openai_url:
                log(f"Azure detected via OPENAI_BASE_URL: {openai_url}")
                return True

        return False
    except Exception as e:
        log(f"Error checking proxy status: {e}", "ERROR")
        return False


def extract_todo_items(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract TODO items from messages that used TodoWrite tool.

    Args:
        messages: List of conversation messages.

    Returns:
        List of todo items with their status.
    """
    todos = []

    try:
        for message in messages:
            if message.get("role") == "assistant":
                content = message.get("content", "")

                # Look for TodoWrite tool use
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "tool_use":
                            if item.get("name") == "TodoWrite":
                                input_data = item.get("input", {})
                                if "todos" in input_data:
                                    todos = input_data["todos"]
                                    log(f"Found {len(todos)} TODO items")
    except Exception as e:
        log(f"Error extracting TODO items: {e}", "ERROR")

    return todos


def has_uncompleted_todos(todos: List[Dict[str, Any]]) -> bool:
    """Check if there are uncompleted TODO items.

    Args:
        todos: List of todo items.

    Returns:
        True if there are pending or in_progress items.
    """
    for todo in todos:
        status = todo.get("status", "").lower()
        if status in ["pending", "in_progress"]:
            log(f"Found uncompleted todo: {todo.get('content', 'Unknown')}")
            return True
    return False


def check_for_continuation_phrases(messages: List[Dict[str, Any]]) -> bool:
    """Check if assistant mentioned next steps or continuation.

    Args:
        messages: List of conversation messages.

    Returns:
        True if continuation phrases found.
    """
    continuation_phrases = [
        r"next[ ,]+(?:i'll|let me|we'll|step)",
        r"(?:will|going to|about to|now i'll)[ ]+(?:create|implement|add|fix|update|work)",
        r"let me (?:now |also |next )?(?:create|implement|add|fix|update|work)",
        r"now let me",
        r"continuing with",
        r"moving on to",
        r"now for the",
        r"(?:after|once) (?:this|that),? (?:i'll|we'll|let's)",
        r"then (?:i'll|we'll|let me)",
        r"(?:first|second|third|next|finally),? (?:i'll|let me|we'll)",
        r"todo(?:s)? (?:list|items?)",
        r"remaining (?:tasks?|items?|work)",
        r"still need to",
    ]

    try:
        # Check last few assistant messages
        assistant_messages = [msg for msg in messages[-5:] if msg.get("role") == "assistant"]

        for message in assistant_messages:
            content = message.get("content", "")
            if isinstance(content, str):
                content_lower = content.lower()
                for pattern in continuation_phrases:
                    if re.search(pattern, content_lower):
                        log(f"Found continuation phrase matching: {pattern}")
                        return True
            elif isinstance(content, list):
                # Check text content in structured messages
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text = item.get("text", "").lower()
                        for pattern in continuation_phrases:
                            if re.search(pattern, text):
                                log(f"Found continuation phrase matching: {pattern}")
                                return True
    except Exception as e:
        log(f"Error checking continuation phrases: {e}", "ERROR")

    return False


def check_request_unfulfilled(messages: List[Dict[str, Any]]) -> bool:
    """Check if the original user request appears unfulfilled.

    Args:
        messages: List of conversation messages.

    Returns:
        True if request seems unfulfilled.
    """
    try:
        # Find the last user message
        user_messages = [msg for msg in messages if msg.get("role") == "user"]
        if not user_messages:
            return False

        last_user_msg = user_messages[-1]
        user_content = last_user_msg.get("content", "")

        # Check if user asked for multiple things
        if isinstance(user_content, str):
            # Look for enumeration or multiple requests
            multi_request_patterns = [
                r"\d+\.",  # Numbered list
                r"(?:and|also|then|plus|additionally)",  # Conjunctions
                r"(?:first|second|third|finally)",  # Sequence words
                r"requirements?:.*\n.*\d+",  # Requirements list
            ]

            for pattern in multi_request_patterns:
                if re.search(pattern, user_content.lower()):
                    log("User request contains multiple items")
                    # Check if assistant is still working through them
                    return check_for_continuation_phrases(messages)
    except Exception as e:
        log(f"Error checking request fulfillment: {e}", "ERROR")

    return False


def should_continue(messages: List[Dict[str, Any]]) -> bool:
    """Determine if the assistant should continue working.

    Args:
        messages: List of conversation messages.

    Returns:
        True if continuation is recommended.
    """
    try:
        # Extract TODO items
        todos = extract_todo_items(messages)

        # Check condition 1: Uncompleted TODO items
        if has_uncompleted_todos(todos):
            log("Decision: Continue - uncompleted TODOs found")
            return True

        # Check condition 2: Continuation phrases
        if check_for_continuation_phrases(messages):
            log("Decision: Continue - continuation phrases found")
            return True

        # Check condition 3: Request appears unfulfilled
        if check_request_unfulfilled(messages):
            log("Decision: Continue - request appears unfulfilled")
            return True

        log("Decision: Allow stop - no continuation indicators found")
        return False

    except Exception as e:
        log(f"Error in continuation logic: {e}", "ERROR")
        # Default to allowing stop on error
        return False


def main():
    """Process stop event with Azure continuation control."""
    try:
        log("Azure continuation hook triggered")

        # Check if proxy is active
        if not is_proxy_active():
            log("Proxy not active - hook bypassed")
            # Return empty response to allow normal stop
            json.dump({}, sys.stdout)
            return

        log("Proxy is active - analyzing continuation need")

        # Read input
        raw_input = sys.stdin.read()
        input_data = json.loads(raw_input)

        # Extract messages
        messages = input_data.get("messages", [])
        log(f"Processing {len(messages)} messages")

        # Determine if continuation is needed
        if should_continue(messages):
            # Use DecisionControl to continue
            output = {
                "decision": "continue",
                "instructions": "Continue working on remaining tasks. Check TODO list and complete any pending items.",
            }
            log("Returning continue decision")
        else:
            # Allow normal stop
            output = {}
            log("Allowing normal stop")

        # Write output
        json.dump(output, sys.stdout)

    except Exception as e:
        log(f"Critical error in hook: {e}", "ERROR")
        # On any error, default to allowing stop
        json.dump({}, sys.stdout)


if __name__ == "__main__":
    main()
