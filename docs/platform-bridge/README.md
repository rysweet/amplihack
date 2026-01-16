# Platform Bridge - Multi-Platform Support for Git Workflows

Automatic platform detection and unified interface fer GitHub and Azure DevOps operations in DEFAULT_WORKFLOW.

## Quick Start

The platform bridge automatically detects whether yer repository be hosted on GitHub or Azure DevOps and uses the appropriate CLI tools. No configuration needed, matey!

```python
from claude.tools.platform_bridge import PlatformBridge

# Automatically detects platform from git remote
bridge = PlatformBridge()

# Create an issue/work item
issue = bridge.create_issue(
    title="Add authentication",
    body="Implement JWT authentication"
)

# Create a draft pull request
pr = bridge.create_draft_pr(
    title="feat: Add JWT auth",
    body="Implementation of authentication system",
    source_branch="feat/auth",
    target_branch="main"
)
```

## What Problem Does This Solve?

Before the platform bridge, DEFAULT_WORKFLOW.md hardcoded GitHub-specific commands (`gh issue create`, `gh pr create`) throughout all 22 steps. This meant:

- Azure DevOps users couldn't use the workflow without manual workarounds
- Every workflow step required platform-specific instructions
- Switching between GitHub and Azure DevOps projects required different workflows

The platform bridge solves this by:

- **Automatic Detection**: Examines `git remote` URLs to determine platform
- **Unified Interface**: Single API that works fer both GitHub and Azure DevOps
- **Zero Configuration**: Works without user intervention or config changes
- **Graceful Fallback**: Clear error messages when CLI tools be missin'

## Core Capabilities

The platform bridge supports five core operations needed by DEFAULT_WORKFLOW:

| Operation | GitHub Command | Azure DevOps Command | Workflow Step |
|-----------|---------------|---------------------|---------------|
| Create Issue | `gh issue create` | `az boards work-item create` | Step 3 |
| Create Draft PR | `gh pr create --draft` | `az repos pr create --draft` | Step 15 |
| Mark PR Ready | `gh pr ready` | `az repos pr update --status Active` | Step 20 |
| Add PR Comment | `gh pr comment` | `az repos pr create-thread` | Steps 16-17 |
| Check CI Status | `gh pr checks` | `az pipelines runs list` | Step 21 |

## How Platform Detection Works

The platform bridge examines yer git remote URLs to determine the platform:

```python
# Detects GitHub
git remote -v
# origin  https://github.com/owner/repo.git (fetch)
# → Platform: github

# Detects Azure DevOps
git remote -v
# origin  https://dev.azure.com/org/project/_git/repo (fetch)
# → Platform: azdo
```

**Detection Logic**:
1. Runs `git remote -v` to get all remotes
2. Checks `origin` remote first (most common)
3. Falls back to first available remote if `origin` doesn't exist
4. Examines URL patterns:
   - `github.com` → GitHub
   - `dev.azure.com` or `visualstudio.com` → Azure DevOps
5. Raises clear error if platform cannot be determined

## Prerequisites

Ye need the appropriate CLI tools installed fer yer platform:

**For GitHub repositories:**
```bash
# Install GitHub CLI
brew install gh  # macOS
# OR
sudo apt install gh  # Ubuntu/Debian
```

**For Azure DevOps repositories:**
```bash
# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash  # Ubuntu/Debian
# OR
brew install azure-cli  # macOS
```

Ye **don't** need both CLIs installed - only the one fer yer current repository's platform.

## Usage Examples

### Creating an Issue/Work Item

```python
from claude.tools.platform_bridge import PlatformBridge

bridge = PlatformBridge()

# Works on both GitHub and Azure DevOps
issue = bridge.create_issue(
    title="Implement feature X",
    body="Detailed description here"
)

print(f"Created: {issue['url']}")
# GitHub: https://github.com/owner/repo/issues/42
# Azure DevOps: https://dev.azure.com/org/project/_workitems/edit/42
```

### Creating a Draft Pull Request

```python
# Create draft PR (both platforms)
pr = bridge.create_draft_pr(
    title="feat: Add new feature",
    body="## Summary\n\nImplementation details...",
    source_branch="feat/new-feature",
    target_branch="main"
)

print(f"Draft PR created: {pr['url']}")
```

### Marking PR Ready for Review

```python
# Mark PR as ready (removes draft status)
result = bridge.mark_pr_ready(pr_number=42)

if result['success']:
    print("PR is now ready fer review!")
```

### Adding Comments to PR

```python
# Add comment to PR
comment = bridge.add_pr_comment(
    pr_number=42,
    comment="All tests be passin' - ready fer merge!"
)
```

### Checking CI Status

```python
# Check CI pipeline status
status = bridge.check_ci_status(pr_number=42)

if status['all_passing']:
    print("All checks passed!")
else:
    print(f"Failed checks: {status['failed_checks']}")
```

## Error Handling

The platform bridge provides clear, actionable error messages:

```python
try:
    bridge = PlatformBridge()
except PlatformDetectionError as e:
    # Could not determine platform from git remotes
    print(f"Platform detection failed: {e}")

try:
    issue = bridge.create_issue(title="Test", body="Body")
except CLIToolMissingError as e:
    # GitHub CLI or Azure CLI not installed
    print(f"Missing tool: {e}")
    print(f"Install with: {e.install_command}")
```

**Common Error Scenarios**:

1. **No Git Remote**: Repository has no remotes configured
   - Error: "No git remotes found. Add a remote with `git remote add origin <url>`"

2. **Unknown Platform**: Remote URL doesn't match GitHub or Azure DevOps patterns
   - Error: "Could not detect platform from remote URL: <url>"

3. **Missing CLI Tool**: Required CLI not installed
   - Error: "GitHub CLI not found. Install with: brew install gh"

4. **Authentication Required**: CLI tool not authenticated
   - Error: "GitHub CLI not authenticated. Run: gh auth login"

## Integration with DEFAULT_WORKFLOW

The platform bridge be integrated into DEFAULT_WORKFLOW.md at these steps:

**Step 3: Create Issue/Work Item**
```python
# Platform-agnostic issue creation
bridge = PlatformBridge()
issue = bridge.create_issue(title=title, body=body)
```

**Step 15: Create Draft PR**
```python
# Works on both GitHub and Azure DevOps
pr = bridge.create_draft_pr(
    title=pr_title,
    body=pr_body,
    source_branch=current_branch,
    target_branch="main"
)
```

**Step 20: Mark PR Ready**
```python
# Remove draft status
bridge.mark_pr_ready(pr_number=pr_number)
```

**Step 21: Check CI Status**
```python
# Platform-agnostic CI status check
status = bridge.check_ci_status(pr_number=pr_number)
if not status['all_passing']:
    print("CI checks still runnin' or failed")
```

## Architecture

The platform bridge follows the **Brick Philosophy** - a self-contained module with clear public contract:

```
.claude/tools/platform_bridge/
├── __init__.py              # Public API via __all__
├── detector.py              # Platform detection logic
├── operations.py            # PlatformOperations interface
├── github_bridge.py         # GitHub implementation
├── azdo_bridge.py          # Azure DevOps implementation
├── exceptions.py            # Custom exceptions
├── tests/                   # Unit tests
│   ├── test_detector.py
│   ├── test_github.py
│   └── test_azdo.py
└── README.md               # This file
```

**Public API** (`__all__`):
- `PlatformBridge` - Main entry point
- `detect_platform()` - Standalone detection function
- `PlatformDetectionError` - Exception fer detection failures
- `CLIToolMissingError` - Exception fer missing CLI tools

## Security Considerations

The platform bridge delegates authentication to official CLI tools:

- **GitHub**: Uses `gh` CLI authentication (`gh auth login`)
- **Azure DevOps**: Uses `az` CLI authentication (`az login`)

**Input Validation**:
- All subprocess calls use parameterized commands (no shell injection)
- Branch names, titles, and bodies be validated before passin' to CLI
- URL parsing uses standard library `urllib.parse`

**Subprocess Safety**:
- Timeouts on all subprocess calls (default 30 seconds)
- Standard error captured and parsed
- Exit codes checked before processin' output

See [Security Documentation](../security/platform-bridge-security.md) fer complete security analysis.

## Troubleshooting

### Platform Detection Fails

**Problem**: `PlatformDetectionError: Could not detect platform`

**Solutions**:
1. Check git remotes: `git remote -v`
2. Ensure remote URL contains `github.com` or `dev.azure.com`
3. Add remote if missin': `git remote add origin <url>`

### CLI Tool Not Found

**Problem**: `CLIToolMissingError: GitHub CLI not found`

**Solutions**:
1. Install the required CLI tool (see Prerequisites)
2. Verify installation: `gh --version` or `az --version`
3. Ensure CLI be in yer PATH

### Authentication Errors

**Problem**: CLI commands fail with authentication errors

**Solutions**:
1. **GitHub**: Run `gh auth login` and follow prompts
2. **Azure DevOps**: Run `az login` and authenticate
3. Verify authentication: `gh auth status` or `az account show`

### Wrong Platform Detected

**Problem**: Bridge detects wrong platform

**Solutions**:
1. Check which remote be detected: `git remote -v`
2. Ensure `origin` points to correct URL
3. Platform detection prioritizes `origin` over other remotes

## See Also

- [Platform Bridge API Reference](../reference/platform-bridge-api.md) - Complete API documentation
- [Contributing to Platform Bridge](../contributing/platform-bridge.md) - Extend with new platforms
- [DEFAULT_WORKFLOW.md](../../.claude/workflow/DEFAULT_WORKFLOW.md) - Full workflow integration
- [Security Analysis](../security/platform-bridge-security.md) - Security implementation details
