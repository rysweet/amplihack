"""Rich formatting utilities for terminal output.

This module provides Rich library integration for:
- Progress bars
- Spinners for long operations
- Color-coded status messages
- Context managers for clean output
"""

import sys
from contextlib import contextmanager
from typing import Iterator, Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text

from .enhancements import is_rich_enabled


# Shared console instance
_console = Console()


def _get_console() -> Console:
    """Get the shared console instance.

    Returns:
        Rich Console instance for output
    """
    return _console


@contextmanager
def progress_spinner(message: str) -> Iterator[None]:
    """Show a spinner for long-running operations.

    Args:
        message: Status message to display with spinner

    Yields:
        None (context manager)

    Example:
        >>> with progress_spinner("Analyzing files..."):
        ...     analyze_codebase()
    """
    if not is_rich_enabled() or not sys.stdout.isatty():
        # Fallback: print message without spinner
        print(f"{message}...", flush=True)
        yield
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=_get_console(),
        transient=True,
    ) as progress:
        progress.add_task(description=message, total=None)
        yield


def create_progress_bar(total: int, description: str = "Processing") -> Progress:
    """Create a progress bar for batch operations.

    Args:
        total: Total number of items to process
        description: Description text for the progress bar

    Returns:
        Rich Progress instance (use as context manager)

    Example:
        >>> with create_progress_bar(100, "Processing files") as progress:
        ...     task_id = progress.add_task(description, total=100)
        ...     for i in range(100):
        ...         process_item(i)
        ...         progress.update(task_id, advance=1)
    """
    if not is_rich_enabled() or not sys.stdout.isatty():
        # Return a no-op progress bar
        class NoOpProgress:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def add_task(self, *args, **kwargs):
                return 0
            def update(self, *args, **kwargs):
                pass

        return NoOpProgress()

    return Progress(
        console=_get_console(),
        transient=False,
    )


def format_success(message: str) -> None:
    """Print a success message with color formatting.

    Args:
        message: Success message to display

    Example:
        >>> format_success("Tests passed!")
    """
    if is_rich_enabled() and sys.stdout.isatty():
        text = Text(f"✓ {message}", style="bold green")
        _get_console().print(text)
    else:
        print(f"✓ {message}")


def format_error(message: str) -> None:
    """Print an error message with color formatting.

    Args:
        message: Error message to display

    Example:
        >>> format_error("Test failed")
    """
    if is_rich_enabled() and sys.stderr.isatty():
        text = Text(f"✗ {message}", style="bold red")
        _get_console().print(text, file=sys.stderr)
    else:
        print(f"✗ {message}", file=sys.stderr)


def format_warning(message: str) -> None:
    """Print a warning message with color formatting.

    Args:
        message: Warning message to display

    Example:
        >>> format_warning("Deprecation notice")
    """
    if is_rich_enabled() and sys.stdout.isatty():
        text = Text(f"⚠ {message}", style="bold yellow")
        _get_console().print(text)
    else:
        print(f"⚠ {message}")


def format_info(message: str) -> None:
    """Print an info message with color formatting.

    Args:
        message: Info message to display

    Example:
        >>> format_info("Starting analysis...")
    """
    if is_rich_enabled() and sys.stdout.isatty():
        text = Text(f"ℹ {message}", style="bold blue")
        _get_console().print(text)
    else:
        print(f"ℹ {message}")
