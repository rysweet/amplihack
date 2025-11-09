"""Common utilities for amplihack modules."""

# Parsing utilities
from .parsing import (
    extract_numbered_items,
    extract_question_text,
    extract_urls_from_text,
    parse_markdown_table,
    split_into_sections,
)

# Subprocess utilities
from .subprocess_utils import (
    CommandNotFoundError,
    SubprocessError,
    check_command_exists,
    run_claude_command,
    run_command,
)

# Markdown utilities
from .markdown_utils import (
    MarkdownBuilder,
    create_code_block,
    create_markdown_header,
    create_markdown_table,
    truncate_text,
    write_markdown_file,
)

# Session utilities
from .session_utils import Statistics, generate_session_id, setup_logger

# Validation utilities
from .validation import (
    dir_exists,
    file_exists,
    is_empty,
    is_not_empty,
    normalize_empty_result,
    safe_call,
    validate_in_range,
    validate_not_empty,
    validate_type,
)

__all__ = [
    # Parsing
    "extract_numbered_items",
    "extract_question_text",
    "extract_urls_from_text",
    "parse_markdown_table",
    "split_into_sections",
    # Subprocess
    "CommandNotFoundError",
    "SubprocessError",
    "check_command_exists",
    "run_claude_command",
    "run_command",
    # Markdown
    "MarkdownBuilder",
    "create_code_block",
    "create_markdown_header",
    "create_markdown_table",
    "truncate_text",
    "write_markdown_file",
    # Session
    "Statistics",
    "generate_session_id",
    "setup_logger",
    # Validation
    "dir_exists",
    "file_exists",
    "is_empty",
    "is_not_empty",
    "normalize_empty_result",
    "safe_call",
    "validate_in_range",
    "validate_not_empty",
    "validate_type",
]
