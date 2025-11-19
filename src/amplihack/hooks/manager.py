"""Hook execution manager.

This module provides centralized hook execution for stop hooks,
primarily used for graceful shutdown coordination.
"""

import importlib.util
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def execute_stop_hook() -> None:
    """Execute the stop hook.

    Loads and executes the stop.py hook from .claude/tools/amplihack/hooks/.
    This is fail-safe - all exceptions are caught and logged.

    The stop hook is responsible for:
    - Neo4j cleanup and shutdown coordination
    - Session reflection (if enabled)
    - Any other cleanup tasks
    """
    try:
        # Find the stop.py file
        # Look relative to this file's location
        stop_hook_path = _find_stop_hook()

        if not stop_hook_path:
            logger.warning("Stop hook not found")
            return

        logger.info(f"Executing stop hook from: {stop_hook_path}")

        # Load and execute
        spec = importlib.util.spec_from_file_location("stop_hook", stop_hook_path)
        if not spec or not spec.loader:
            logger.warning("Could not load stop hook module")
            return

        stop_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stop_module)

        # Execute the stop() function
        if hasattr(stop_module, "stop"):
            logger.info("Calling stop() function from hook")
            stop_module.stop()
            logger.info("Stop hook execution complete")
        else:
            logger.warning("Stop hook module has no stop() function")

    except Exception as e:
        logger.warning(f"Failed to execute stop hook: {e}")


def _find_stop_hook() -> Optional[Path]:
    """Find the stop.py hook file.

    Searches in multiple locations:
    1. .claude/tools/amplihack/hooks/stop.py (relative to project root)
    2. Standard amplihack installation locations

    Returns:
        Path to stop.py if found, None otherwise
    """
    # Strategy 1: Try to find project root by looking for .claude directory
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        claude_dir = parent / ".claude"
        if claude_dir.exists() and claude_dir.is_dir():
            stop_hook = claude_dir / "tools" / "amplihack" / "hooks" / "stop.py"
            if stop_hook.exists():
                logger.debug(f"Found stop hook in parent directory: {stop_hook}")
                return stop_hook

    # Strategy 2: Try relative to this module's location
    # This handles development/testing scenarios
    module_dir = Path(__file__).parent.parent.parent.parent
    stop_hook = module_dir / ".claude" / "tools" / "amplihack" / "hooks" / "stop.py"
    if stop_hook.exists():
        logger.debug(f"Found stop hook relative to module: {stop_hook}")
        return stop_hook

    logger.debug("Stop hook not found in standard locations")
    return None
