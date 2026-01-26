# Platform Bridge API Reference

Complete API documentation fer the platform bridge module.

## Module: `claude.tools.platform_bridge`

### Public API

```python
__all__ = [
    "PlatformBridge",
    "detect_platform",
    "Platform",
    "PlatformDetectionError",
    "CLIToolMissingError"
]
```

## Classes

### `PlatformBridge`

Main entry point fer platform-agnostic git operations.

**Constructor**:

```python
PlatformBridge(repo_path: str = ".") -> PlatformBridge
```

**Parameters**:

- `repo_path` (str, optional): Path to git repository. Defaults to current directory.

**Raises**:

- `PlatformDetectionError`: If platform cannot be determined from git remotes
- `NotAGitRepositoryError`: If repo_path not be a git repository

**Example**:

```python
from claude.tools.platform_bridge import PlatformBridge

# Use current directory
bridge = PlatformBridge()

# Use specific repository
bridge = PlatformBridge("/path/to/repo")
```

**Attributes**:

- `platform` (Platform): Detected platform (GitHub or AzureDevOps)
- `repo_path` (Path): Absolute path to repository

---

### `PlatformBridge.create_issue()`

Create an issue (GitHub) or work item (Azure DevOps).

**Signature**:

```python
def create_issue(
    self,
    title: str,
    body: str,
    labels: Optional[List[str]] = None
) -> Dict[str, Any]
```

**Parameters**:

- `title` (str): Issue/work item title (required, max 256 characters)
- `body` (str): Issue/work item description (required)
- `labels` (List[str], optional): Labels/tags to apply (GitHub only)

**Returns**:

```python
{
    "number": 42,                    # Issue/work item number
    "url": "https://...",            # Web URL to issue
    "title": "Issue title",          # Created title
    "state": "open"                  # Current state
}
```

**Raises**:

- `CLIToolMissingError`: If gh/az CLI not installed
- `subprocess.CalledProcessError`: If CLI command fails

**Example**:

```python
issue = bridge.create_issue(
    title="Add authentication",
    body="Implement JWT authentication\n\n## Requirements\n- Token validation\n- Refresh tokens",
    labels=["enhancement", "security"]  # GitHub only
)

print(f"Created issue #{issue['number']}: {issue['url']}")
```

**GitHub Command**:

```bash
gh issue create --title "..." --body "..." --label "enhancement,security"
```

**Azure DevOps Command**:

```bash
az boards work-item create --type "User Story" --title "..." --description "..."
```

---

### `PlatformBridge.create_draft_pr()`

Create a draft pull request on both platforms.

**Signature**:

```python
def create_draft_pr(
    self,
    title: str,
    body: str,
    source_branch: str,
    target_branch: str = "main"
) -> Dict[str, Any]
```

**Parameters**:

- `title` (str): PR title (required, max 256 characters)
- `body` (str): PR description in markdown (required)
- `source_branch` (str): Source branch name (required)
- `target_branch` (str): Target branch name (default: "main")

**Returns**:

```python
{
    "number": 123,                   # PR number
    "url": "https://...",            # Web URL to PR
    "title": "PR title",             # Created title
    "state": "draft",                # Initial state
    "source_branch": "feat/auth",    # Source branch
    "target_branch": "main"          # Target branch
}
```

**Raises**:

- `CLIToolMissingError`: If gh/az CLI not installed
- `BranchNotFoundError`: If source branch doesn't exist
- `subprocess.CalledProcessError`: If CLI command fails

**Example**:

```python
pr = bridge.create_draft_pr(
    title="feat: Add JWT authentication",
    body="## Summary\n\nImplements JWT authentication\n\n## Test Plan\n- Unit tests\n- Integration tests",
    source_branch="feat/auth",
    target_branch="main"
)

print(f"Draft PR #{pr['number']}: {pr['url']}")
```

**GitHub Command**:

```bash
gh pr create --draft --title "..." --body "..." --head feat/auth --base main
```

**Azure DevOps Command**:

```bash
az repos pr create --draft true --title "..." --description "..." --source-branch feat/auth --target-branch main
```

---

### `PlatformBridge.mark_pr_ready()`

Mark a draft PR as ready fer review.

**Signature**:

```python
def mark_pr_ready(self, pr_number: int) -> Dict[str, Any]
```

**Parameters**:

- `pr_number` (int): Pull request number (required)

**Returns**:

```python
{
    "number": 123,              # PR number
    "state": "open",            # New state (no longer draft)
    "success": True             # Operation succeeded
}
```

**Raises**:

- `CLIToolMissingError`: If gh/az CLI not installed
- `PRNotFoundError`: If PR number doesn't exist
- `subprocess.CalledProcessError`: If CLI command fails

**Example**:

```python
result = bridge.mark_pr_ready(pr_number=123)

if result['success']:
    print(f"PR #{result['number']} be ready fer review!")
```

**GitHub Command**:

```bash
gh pr ready 123
```

**Azure DevOps Command**:

```bash
az repos pr update --id 123 --status Active
```

---

### `PlatformBridge.add_pr_comment()`

Add a comment to a pull request.

**Signature**:

```python
def add_pr_comment(
    self,
    pr_number: int,
    comment: str
) -> Dict[str, Any]
```

**Parameters**:

- `pr_number` (int): Pull request number (required)
- `comment` (str): Comment text in markdown (required)

**Returns**:

```python
{
    "comment_id": "456",         # Comment identifier
    "pr_number": 123,            # PR number
    "body": "Comment text",      # Created comment
    "url": "https://..."         # Web URL to comment
}
```

**Raises**:

- `CLIToolMissingError`: If gh/az CLI not installed
- `PRNotFoundError`: If PR number doesn't exist
- `subprocess.CalledProcessError`: If CLI command fails

**Example**:

```python
comment = bridge.add_pr_comment(
    pr_number=123,
    comment="All tests be passin'! Ready fer merge. 🚢"
)

print(f"Added comment: {comment['url']}")
```

**GitHub Command**:

```bash
gh pr comment 123 --body "All tests be passin'! Ready fer merge. 🚢"
```

**Azure DevOps Command**:

```bash
az repos pr create-thread --id 123 --comment-text "All tests be passin'! Ready fer merge. 🚢"
```

---

### `PlatformBridge.check_ci_status()`

Check CI/CD pipeline status fer a pull request.

**Signature**:

```python
def check_ci_status(self, pr_number: int) -> Dict[str, Any]
```

**Parameters**:

- `pr_number` (int): Pull request number (required)

**Returns**:

```python
{
    "all_passing": True,           # All checks passed
    "total_checks": 5,             # Total number of checks
    "passed": 5,                   # Number passed
    "failed": 0,                   # Number failed
    "pending": 0,                  # Number still runnin'
    "checks": [                    # List of individual checks
        {
            "name": "build",
            "status": "success",
            "url": "https://..."
        },
        {
            "name": "test",
            "status": "success",
            "url": "https://..."
        }
    ]
}
```

**Raises**:

- `CLIToolMissingError`: If gh/az CLI not installed
- `PRNotFoundError`: If PR number doesn't exist
- `subprocess.CalledProcessError`: If CLI command fails

**Example**:

```python
status = bridge.check_ci_status(pr_number=123)

if status['all_passing']:
    print("All checks passed! Ready to merge.")
elif status['pending'] > 0:
    print(f"Waitin' on {status['pending']} checks...")
else:
    print(f"Failed checks: {status['failed']}")
    for check in status['checks']:
        if check['status'] == 'failure':
            print(f"  - {check['name']}: {check['url']}")
```

**GitHub Command**:

```bash
gh pr checks 123
```

**Azure DevOps Command**:

```bash
az pipelines runs list --branch refs/pull/123/merge
```

---

## Functions

### `detect_platform()`

Standalone function to detect platform from git remotes without creatin' a PlatformBridge instance.

**Signature**:

```python
def detect_platform(repo_path: str = ".") -> Platform
```

**Parameters**:

- `repo_path` (str, optional): Path to git repository. Defaults to current directory.

**Returns**:

- `Platform.GITHUB` - Repository hosted on GitHub
- `Platform.AZDO` - Repository hosted on Azure DevOps

**Raises**:

- `PlatformDetectionError`: If platform cannot be determined
- `NotAGitRepositoryError`: If repo_path not be a git repository

**Example**:

```python
from claude.tools.platform_bridge import detect_platform, Platform

platform = detect_platform()

if platform == Platform.GITHUB:
    print("This be a GitHub repository")
elif platform == Platform.AZDO:
    print("This be an Azure DevOps repository")
```

**Detection Logic**:

1. Run `git remote -v` in repo_path
2. Extract URLs from output
3. Check `origin` remote first
4. Fall back to first available remote
5. Match URL patterns:
   - `github.com` → `Platform.GITHUB`
   - `dev.azure.com` or `visualstudio.com` → `Platform.AZDO`
6. Raise `PlatformDetectionError` if no match

---

## Enums

### `Platform`

Enumeration of supported platforms.

```python
class Platform(Enum):
    GITHUB = "github"
    AZDO = "azdo"
```

**Members**:

- `Platform.GITHUB` - GitHub platform
- `Platform.AZDO` - Azure DevOps platform

**Example**:

```python
from claude.tools.platform_bridge import Platform

if bridge.platform == Platform.GITHUB:
    print("Using GitHub operations")
```

---

## Exceptions

### `PlatformDetectionError`

Raised when platform cannot be determined from git remotes.

**Inheritance**: `Exception`

**Common Causes**:

- No git remotes configured
- Remote URL doesn't match known patterns
- Not a git repository

**Example**:

```python
from claude.tools.platform_bridge import PlatformBridge, PlatformDetectionError

try:
    bridge = PlatformBridge()
except PlatformDetectionError as e:
    print(f"Could not detect platform: {e}")
    print("Add a remote: git remote add origin <url>")
```

---

### `CLIToolMissingError`

Raised when required CLI tool (gh or az) not be installed.

**Inheritance**: `Exception`

**Attributes**:

- `tool_name` (str): Name of missing tool ("gh" or "az")
- `install_command` (str): Platform-specific installation command

**Example**:

```python
from claude.tools.platform_bridge import PlatformBridge, CLIToolMissingError

try:
    bridge = PlatformBridge()
    issue = bridge.create_issue(title="Test", body="Body")
except CLIToolMissingError as e:
    print(f"Missing: {e.tool_name}")
    print(f"Install with: {e.install_command}")
```

---

### `PRNotFoundError`

Raised when specified PR number doesn't exist.

**Inheritance**: `Exception`

**Attributes**:

- `pr_number` (int): PR number that wasn't found

**Example**:

```python
from claude.tools.platform_bridge import PRNotFoundError

try:
    bridge.mark_pr_ready(pr_number=999)
except PRNotFoundError as e:
    print(f"PR #{e.pr_number} doesn't exist")
```

---

### `BranchNotFoundError`

Raised when specified branch doesn't exist in repository.

**Inheritance**: `Exception`

**Attributes**:

- `branch_name` (str): Branch name that wasn't found

**Example**:

```python
from claude.tools.platform_bridge import BranchNotFoundError

try:
    pr = bridge.create_draft_pr(
        title="Test",
        body="Body",
        source_branch="nonexistent-branch"
    )
except BranchNotFoundError as e:
    print(f"Branch '{e.branch_name}' doesn't exist")
```

---

## Type Hints

All functions use proper type hints:

```python
from typing import Dict, List, Optional, Any
from pathlib import Path

class PlatformBridge:
    def __init__(self, repo_path: str = ".") -> None: ...

    def create_issue(
        self,
        title: str,
        body: str,
        labels: Optional[List[str]] = None
    ) -> Dict[str, Any]: ...

    def create_draft_pr(
        self,
        title: str,
        body: str,
        source_branch: str,
        target_branch: str = "main"
    ) -> Dict[str, Any]: ...
```

---

## Thread Safety

The platform bridge be **thread-safe** fer read operations but **not thread-safe** fer write operations:

**Safe** (multiple threads):

```python
# Multiple threads can check CI status simultaneously
status1 = bridge.check_ci_status(pr_number=123)
status2 = bridge.check_ci_status(pr_number=456)
```

**Unsafe** (avoid):

```python
# Don't create multiple PRs from different threads
# Results be unpredictable
```

Fer concurrent operations, create separate `PlatformBridge` instances per thread.

---

## See Also

- [Platform Bridge Overview](../platform-bridge/README.md) - Complete usage guide
- [Security Documentation](../security/platform-bridge-security.md) - Security analysis
- [Contributing Guide](../contributing/platform-bridge.md) - Extend with new platforms
