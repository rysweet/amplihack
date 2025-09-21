# Post-Edit Auto-Formatting Hook

Automatically formats files after they are edited using Claude Code's Edit tools.

## Overview

The `post_edit_format.py` hook is a POST_TOOL_USE hook that triggers specifically after the Edit, MultiEdit, Write, or NotebookEdit tools are used. It automatically formats the edited files using appropriate language-specific formatters.

## Features

- **Automatic Detection**: Detects when Edit-related tools are used
- **Language-Specific Formatting**: Uses the best available formatter for each file type
- **Graceful Fallback**: Falls back to alternative formatters if primary ones aren't available
- **Non-Intrusive**: Doesn't block edits if formatting fails
- **Configurable**: Can be enabled/disabled globally or per-language
- **Change Detection**: Only reports when files are actually modified

## Supported File Types

| Language               | Formatters (in order of preference) |
| ---------------------- | ----------------------------------- |
| Python (.py)           | black, ruff, autopep8               |
| JavaScript (.js)       | prettier, eslint                    |
| TypeScript (.ts, .tsx) | prettier, eslint                    |
| JSON (.json)           | prettier, jq                        |
| Markdown (.md)         | prettier, mdformat                  |
| YAML (.yaml, .yml)     | prettier                            |
| CSS/SCSS (.css, .scss) | prettier                            |
| HTML (.html)           | prettier                            |
| XML (.xml)             | prettier                            |

## Configuration

### Environment Variables

- **`CLAUDE_AUTO_FORMAT`**: Global toggle (default: `true`)
  - Set to `false` to disable all auto-formatting

- **Per-Language Controls**:
  - `CLAUDE_FORMAT_PYTHON`: Enable/disable Python formatting (default: `true`)
  - `CLAUDE_FORMAT_JS`: Enable/disable JavaScript formatting (default: `true`)
  - `CLAUDE_FORMAT_TS`: Enable/disable TypeScript formatting (default: `true`)
  - `CLAUDE_FORMAT_JSON`: Enable/disable JSON formatting (default: `true`)
  - `CLAUDE_FORMAT_MD`: Enable/disable Markdown formatting (default: `true`)

### Example Usage

```bash
# Disable all auto-formatting
export CLAUDE_AUTO_FORMAT=false

# Enable formatting but disable for Python only
export CLAUDE_AUTO_FORMAT=true
export CLAUDE_FORMAT_PYTHON=false
```

## Installation

1. The hook is already installed in `.claude/tools/amplihack/hooks/post_edit_format.py`

2. Install formatters you want to use:

   ```bash
   # Python formatters
   pip install black ruff autopep8

   # JavaScript/Web formatters
   npm install -g prettier eslint

   # JSON formatter (macOS)
   brew install jq

   # Markdown formatter
   pip install mdformat
   ```

## How It Works

1. **Tool Detection**: The hook receives POST_TOOL_USE events and checks if the tool was Edit, MultiEdit, Write, or NotebookEdit

2. **File Extraction**: Extracts the file path(s) that were edited

3. **Formatter Selection**: Based on file extension, selects appropriate formatters

4. **Format Execution**: Runs the first available formatter for that file type

5. **Change Detection**: Compares file hash before and after to detect changes

6. **User Feedback**: Reports which files were formatted and which formatter was used

## Testing

Run the test suite:

```bash
# Unit tests
python3 test_post_edit_format.py -v

# Integration tests
python3 test_integration.py

# Interactive demo
python3 demo_post_edit_format.py
```

## Files

- `post_edit_format.py` - Main hook implementation
- `test_post_edit_format.py` - Unit tests
- `test_integration.py` - Integration tests with real formatters
- `demo_post_edit_format.py` - Interactive demonstration
- `README_post_edit_format.md` - This documentation

## Logging

The hook logs all activities to:

- `.claude/runtime/logs/post_edit_format.log`

## Example Output

When a file is successfully formatted:

```
Auto-formatted 1 file(s):
  • example.py (formatted with black)
```

## Troubleshooting

1. **Formatter not found**: Install the required formatter (see Installation)
2. **Formatting disabled**: Check environment variables
3. **No changes made**: File may already be properly formatted
4. **Errors in log**: Check `.claude/runtime/logs/post_edit_format.log`

## Performance

- Formatters run with a 10-second timeout
- Only processes files that were actually edited
- Uses file hashing for efficient change detection
- Runs asynchronously without blocking the edit operation
