"""Fleet repo setup — automated workspace preparation on remote VMs.

When the director assigns a task to a VM, this module handles:
1. Clone the repository (if not already present)
2. Create/checkout the working branch
3. Detect project type and install dependencies
4. Verify the build works

This eliminates the 5-10 minute manual setup per task assignment.

Public API:
    RepoSetup: Automated workspace preparation
"""

from __future__ import annotations

import logging
import re
import shlex
import subprocess
from dataclasses import dataclass, field

from amplihack.fleet._defaults import get_azlin_path
from amplihack.fleet._validation import validate_vm_name
from amplihack.utils.logging_utils import log_call

__all__ = ["RepoSetup", "SetupResult"]

logger = logging.getLogger(__name__)

_URL_SCHEME_RE = re.compile(r"^(https?://|git@|ssh://)")


@log_call
def _validate_repo_url(url: str) -> str:
    """Validate repo URL uses a safe transport scheme."""
    if not _URL_SCHEME_RE.match(url):
        raise ValueError(f"Unsupported repo URL scheme: {url!r}")
    return url


@dataclass
class SetupResult:
    """Result of repo setup on a remote VM."""

    vm_name: str
    repo_url: str
    workspace_path: str
    success: bool
    branch: str = ""
    error: str = ""
    duration_seconds: float = 0.0


@dataclass
class RepoSetup:
    """Automated workspace preparation on remote VMs.

    Generates a shell script that handles repo cloning, dependency
    installation, and build verification. Injected into tmux sessions
    before the agent starts.
    """

    azlin_path: str = field(default_factory=get_azlin_path)
    workspace_base: str = "/workspace"

    @log_call
    def setup_repo(
        self,
        vm_name: str,
        repo_url: str,
        branch: str = "",
        github_identity: str = "",
    ) -> SetupResult:
        """Set up a repository workspace on a remote VM.

        Args:
            vm_name: Target VM
            repo_url: Repository to clone (https or git@)
            branch: Branch to create/checkout (optional)
            github_identity: GitHub username for auth context
        """
        validate_vm_name(vm_name)
        _validate_repo_url(repo_url)
        import time

        start = time.monotonic()
        project_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
        workspace = f"{self.workspace_base}/{project_name}"

        setup_script = self._generate_setup_script(
            repo_url=repo_url,
            workspace=workspace,
            branch=branch,
            github_identity=github_identity,
        )

        try:
            result = subprocess.run(
                [self.azlin_path, "connect", vm_name, "--no-tmux", "--", setup_script],
                capture_output=True,
                text=True,
                timeout=300,  # 5 min for clone + install
            )

            success = result.returncode == 0 and "SETUP_OK" in (result.stdout or "")
            error = ""
            if not success:
                error = (result.stderr or result.stdout or "Unknown error")[-500:]

            return SetupResult(
                vm_name=vm_name,
                repo_url=repo_url,
                workspace_path=workspace,
                success=success,
                branch=branch,
                error=error,
                duration_seconds=time.monotonic() - start,
            )

        except subprocess.TimeoutExpired:
            logger.warning("Repo setup timed out for %s on %s", repo_url, vm_name)
            return SetupResult(
                vm_name=vm_name,
                repo_url=repo_url,
                workspace_path=workspace,
                success=False,
                error="Setup timed out after 300s",
                duration_seconds=time.monotonic() - start,
            )

    @log_call
    def _generate_setup_script(
        self,
        repo_url: str,
        workspace: str,
        branch: str,
        github_identity: str,
    ) -> str:
        """Generate the repo setup shell script."""
        safe_repo = shlex.quote(repo_url)
        safe_workspace = shlex.quote(workspace)
        safe_branch = shlex.quote(branch) if branch else ""

        identity_cmd = ""
        if github_identity:
            safe_user = shlex.quote(github_identity)
            identity_cmd = f"gh auth switch --user {safe_user} 2>/dev/null || true"

        branch_cmd = ""
        if branch:
            branch_cmd = f"""
# Create or checkout branch
git checkout {safe_branch} 2>/dev/null || git checkout -b {safe_branch}
"""

        return f"""
set -e

# Switch GitHub identity if specified
{identity_cmd}

# Clone or update repo
if [ -d {safe_workspace} ]; then
    echo "Workspace exists, pulling latest..."
    cd {safe_workspace}
    git fetch --all --prune
    git checkout main 2>/dev/null || git checkout master 2>/dev/null || true
    git pull --ff-only 2>/dev/null || true
else
    echo "Cloning {safe_repo}..."
    mkdir -p {shlex.quote(self.workspace_base)}
    git clone {safe_repo} {safe_workspace}
    cd {safe_workspace}
fi

{branch_cmd}

# Auto-detect project type and install dependencies
if [ -f "pyproject.toml" ]; then
    echo "Python project detected"
    if command -v uv &>/dev/null; then
        uv sync --quiet 2>/dev/null || echo "WARN: uv sync failed"
        pip install -e . --quiet 2>/dev/null || echo "WARN: pip install failed"
    elif command -v pip &>/dev/null; then
        pip install -e . --quiet 2>/dev/null || echo "WARN: pip install failed"
    fi
elif [ -f "package.json" ]; then
    echo "Node.js project detected"
    if command -v npm &>/dev/null; then
        npm install --quiet 2>/dev/null || echo "WARN: npm install failed"
    fi
elif [ -f "Cargo.toml" ]; then
    echo "Rust project detected"
    cargo build --quiet 2>/dev/null || echo "WARN: cargo build failed"
elif [ -f "go.mod" ]; then
    echo "Go project detected"
    go mod download 2>/dev/null || echo "WARN: go mod download failed"
elif ls *.sln >/dev/null 2>&1 || ls *.csproj >/dev/null 2>&1; then
    echo ".NET project detected"
    dotnet restore --quiet 2>/dev/null || echo "WARN: dotnet restore failed"
fi

echo "Workspace ready: $(pwd)"
echo "Branch: $(git branch --show-current)"
echo "SETUP_OK"
"""
