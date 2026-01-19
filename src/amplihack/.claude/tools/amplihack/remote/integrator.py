"""Result integration for remote execution.

This module handles integrating remote execution results back into
the local repository, including git branches, commits, and logs.
"""

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .errors import IntegrationError


@dataclass
class BranchInfo:
    """Information about a git branch."""

    name: str
    commit: str
    is_new: bool


@dataclass
class IntegrationSummary:
    """Summary of result integration."""

    branches: list[BranchInfo]
    commits_count: int
    files_changed: int
    logs_copied: bool
    has_conflicts: bool
    conflict_details: str | None = None


class Integrator:
    """Integrates remote execution results into local repository.

    Handles:
    - Fetching remote branches
    - Copying logs
    - Detecting conflicts
    - Creating integration summaries
    """

    def __init__(self, repo_path: Path):
        """Initialize integrator.

        Args:
            repo_path: Path to local git repository
        """
        self.repo_path = Path(repo_path).resolve()
        self._verify_git_repo()

    def _verify_git_repo(self):
        """Verify path is a git repository.

        Raises:
            IntegrationError: If not a git repository
        """
        if not (self.repo_path / ".git").exists():
            raise IntegrationError(
                f"Not a git repository: {self.repo_path}",
                context={"repo_path": str(self.repo_path)},
            )

    def integrate(self, results_dir: Path) -> IntegrationSummary:
        """Integrate remote results into local repository.

        Args:
            results_dir: Directory containing remote results

        Returns:
            IntegrationSummary with details

        Raises:
            IntegrationError: If integration fails
        """
        # Step 1: Import git branches
        branches = self._import_branches(results_dir)

        # Step 2: Count commits (new commits from remote)
        commits_count = self._count_new_commits(branches)

        # Step 3: Copy logs
        logs_copied = self._copy_logs(results_dir)

        # Step 4: Detect conflicts
        conflicts = self._detect_conflicts(branches)

        # Step 5: Count files changed
        files_changed = self._count_files_changed(branches)

        return IntegrationSummary(
            branches=branches,
            commits_count=commits_count,
            files_changed=files_changed,
            logs_copied=logs_copied,
            has_conflicts=len(conflicts) > 0,
            conflict_details="\n".join(conflicts) if conflicts else None,
        )

    def _import_branches(self, results_dir: Path) -> list[BranchInfo]:
        """Import git branches from remote bundle.

        Args:
            results_dir: Directory containing results.bundle

        Returns:
            List of imported branches

        Raises:
            IntegrationError: If import fails
        """
        bundle_path = results_dir / "results.bundle"
        if not bundle_path.exists():
            raise IntegrationError(
                "Results bundle not found", context={"expected_path": str(bundle_path)}
            )

        print("Importing remote branches...")

        # Get current branches to detect new ones
        current_branches = self._list_local_branches()

        try:
            # Fetch from bundle into remote-exec namespace
            result = subprocess.run(
                ["git", "fetch", str(bundle_path), "refs/heads/*:refs/remotes/remote-exec/*"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=60,
                check=True,
            )

            # Get imported branches
            imported_branches = self._list_remote_exec_branches()

            branch_info = []
            for branch_name in imported_branches:
                # Get commit hash
                result = subprocess.run(
                    ["git", "rev-parse", f"remote-exec/{branch_name}"],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                commit = result.stdout.strip()

                # Check if this is a new branch
                is_new = branch_name not in current_branches

                branch_info.append(BranchInfo(name=branch_name, commit=commit, is_new=is_new))

            print(f"Imported {len(branch_info)} branch(es)")
            return branch_info

        except subprocess.CalledProcessError as e:
            raise IntegrationError(
                f"Failed to import branches: {e.stderr}", context={"bundle_path": str(bundle_path)}
            )
        except subprocess.TimeoutExpired:
            raise IntegrationError(
                "Branch import timed out", context={"bundle_path": str(bundle_path)}
            )

    def _copy_logs(self, results_dir: Path) -> bool:
        """Copy logs from results to local repository.

        Args:
            results_dir: Directory containing extracted logs

        Returns:
            True if logs copied successfully
        """
        source_logs = results_dir / ".claude" / "runtime" / "logs"
        if not source_logs.exists():
            print("Warning: No logs found in results")
            return False

        # Create remote logs directory
        dest_logs = self.repo_path / ".claude" / "runtime" / "logs" / "remote"
        dest_logs.mkdir(parents=True, exist_ok=True)

        print("Copying execution logs...")

        try:
            # Copy all log files
            copied_count = 0
            for log_file in source_logs.rglob("*"):
                if log_file.is_file():
                    # Create relative path in destination
                    rel_path = log_file.relative_to(source_logs)
                    dest_file = dest_logs / rel_path
                    dest_file.parent.mkdir(parents=True, exist_ok=True)

                    # Copy file
                    shutil.copy2(log_file, dest_file)
                    copied_count += 1

            print(f"Copied {copied_count} log file(s) to {dest_logs}")
            return True

        except Exception as e:
            print(f"Warning: Failed to copy logs: {e}")
            return False

    def _detect_conflicts(self, branches: list[BranchInfo]) -> list[str]:
        """Detect potential merge conflicts.

        Args:
            branches: Imported branches

        Returns:
            List of conflict descriptions
        """
        conflicts = []

        for branch in branches:
            # Check if local branch exists and has diverged
            if not branch.is_new:
                try:
                    # Get local branch commit
                    result = subprocess.run(
                        ["git", "rev-parse", branch.name],
                        cwd=self.repo_path,
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )

                    if result.returncode == 0:
                        local_commit = result.stdout.strip()

                        # Check if commits differ
                        if local_commit != branch.commit:
                            # Check if fast-forward possible
                            result = subprocess.run(
                                ["git", "merge-base", "--is-ancestor", local_commit, branch.commit],
                                cwd=self.repo_path,
                                capture_output=True,
                                timeout=10,
                            )

                            if result.returncode != 0:
                                conflicts.append(
                                    f"Branch '{branch.name}' has diverged: "
                                    f"local={local_commit[:8]}, remote={branch.commit[:8]}"
                                )

                except Exception as e:
                    print(f"Warning: Could not check for conflicts on {branch.name}: {e}")

        return conflicts

    def _count_new_commits(self, branches: list[BranchInfo]) -> int:
        """Count new commits from imported branches.

        Args:
            branches: Imported branches

        Returns:
            Number of new commits
        """
        # Simple heuristic: count commits on new branches
        # For existing branches, this is approximate
        total_commits = 0

        for branch in branches:
            try:
                result = subprocess.run(
                    ["git", "rev-list", "--count", f"remote-exec/{branch.name}"],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=True,
                )
                count = int(result.stdout.strip())
                total_commits += count

            except Exception as e:
                # Log but continue - commit count is for summary only
                print(f"Warning: Could not count commits for {branch.name}: {e}")

        return total_commits

    def _count_files_changed(self, branches: list[BranchInfo]) -> int:
        """Count files changed across all branches.

        Args:
            branches: Imported branches

        Returns:
            Total number of files changed
        """
        if not branches:
            return 0

        # Count files changed in first branch (primary work)
        try:
            branch = branches[0]
            result = subprocess.run(
                [
                    "git",
                    "diff",
                    "--name-only",
                    f"remote-exec/{branch.name}~1",
                    f"remote-exec/{branch.name}",
                ],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                files = result.stdout.strip().split("\n")
                return len([f for f in files if f])

        except Exception as e:
            # Log but continue - file count is for summary only
            print(f"Warning: Could not count files changed: {e}")

        return 0

    def _list_local_branches(self) -> list[str]:
        """List all local branch names."""
        try:
            result = subprocess.run(
                ["git", "branch", "--format=%(refname:short)"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )
            return result.stdout.strip().split("\n")
        except Exception:
            return []

    def _list_remote_exec_branches(self) -> list[str]:
        """List all remote-exec namespace branches."""
        try:
            result = subprocess.run(
                ["git", "branch", "-r", "--format=%(refname:short)"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )
            branches = result.stdout.strip().split("\n")
            # Filter for remote-exec namespace and strip prefix
            return [b.replace("remote-exec/", "") for b in branches if b.startswith("remote-exec/")]
        except Exception:
            return []

    def create_summary_report(self, summary: IntegrationSummary) -> str:
        """Create human-readable summary report.

        Args:
            summary: Integration summary

        Returns:
            Formatted summary text
        """
        lines = ["", "=" * 60, "Remote Execution Results", "=" * 60, ""]

        # Branches
        lines.append(f"Branches ({len(summary.branches)}):")
        for branch in summary.branches:
            status = "NEW" if branch.is_new else "UPDATED"
            lines.append(f"  - {branch.name} ({status}): {branch.commit[:8]}")

        lines.append("")

        # Commits
        lines.append(f"Commits: {summary.commits_count}")
        lines.append(f"Files changed: {summary.files_changed}")
        lines.append(f"Logs copied: {'Yes' if summary.logs_copied else 'No'}")

        lines.append("")

        # Conflicts
        if summary.has_conflicts:
            lines.append("WARNING: Conflicts detected!")
            lines.append(summary.conflict_details or "")
            lines.append("")
            lines.append("Branches available in 'remote-exec/' namespace for manual merge:")
            for branch in summary.branches:
                lines.append(f"  git merge remote-exec/{branch.name}")
        else:
            lines.append("Status: No conflicts detected")
            lines.append("")
            lines.append("To merge remote changes:")
            for branch in summary.branches:
                lines.append(f"  git merge remote-exec/{branch.name}")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)
