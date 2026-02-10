"""Hook execution manager.

This module provides centralized hook execution for stop hooks,
primarily used for graceful shutdown coordination.
"""

import importlib.util
import logging
from pathlib import Path

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


def _find_stop_hook() -> Path | None:
    """Find the stop.py hook file.

    Searches in multiple locations:
    1. Bundled hooks in installed package (site-packages/amplihack/.claude/)
    2. Local .claude directory (for development)

    Returns:
        Path to stop.py if found, None otherwise
    """
    import os

    # PRIORITY 1: Try installed plugin (when using Claude Code plugin system)
    if os.environ.get("AMPLIHACK_PLUGIN_INSTALLED") == "true":
        installed_plugin_path = (
            Path.home() / ".claude" / "plugins" / "cache" / "amplihack" / "amplihack" / "0.9.0"
        )
        plugin_stop_hook = installed_plugin_path / "tools" / "amplihack" / "hooks" / "stop.py"
        if plugin_stop_hook.exists():
            logger.debug(f"Using installed plugin stop hook: {plugin_stop_hook}")
            return plugin_stop_hook

    # PRIORITY 2: Try bundled hooks in installed package (for UV/pip installs)
    # This ensures installed versions use the hooks that were bundled with them
    module_dir = Path(__file__).parent.parent.parent.parent
    bundled_hook = module_dir / ".claude" / "tools" / "amplihack" / "hooks" / "stop.py"
    if bundled_hook.exists():
        logger.debug(f"Using bundled stop hook from package: {bundled_hook}")
        return bundled_hook

    # PRIORITY 3: Fall back to local .claude directory (for development)
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        claude_dir = parent / ".claude"
        if claude_dir.exists() and claude_dir.is_dir():
            stop_hook = claude_dir / "tools" / "amplihack" / "hooks" / "stop.py"
            if stop_hook.exists():
                logger.debug(f"Using local stop hook: {stop_hook}")
                return stop_hook

    logger.debug("Stop hook not found in standard locations")
    return None
