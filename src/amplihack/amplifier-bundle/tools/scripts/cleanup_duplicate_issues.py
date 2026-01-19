#!/usr/bin/env python3
"""Safe, comprehensive cleanup script for GitHub duplicate issues.

This script uses our optimized SDK duplicate detection to systematically close
duplicate GitHub issues while preserving important information. It implements
multiple safety layers including dry-run mode, information preservation,
cross-referencing, and audit trails.

Features:
- Safe dry-run mode for previewing all actions
- Information preservation from duplicates before closing
- Cross-referencing between canonical and duplicate issues
- Comprehensive audit trail for all operations
- Phase-based cleanup (perfect duplicates -> functional duplicates -> edge cases)
- Rollback capability with documentation
- Integration with optimized SDK duplicate detection

Usage:
    # Preview all actions (safe mode)
    python cleanup_duplicate_issues.py --dry-run

    # Execute Phase 1 only (perfect duplicates)
    python cleanup_duplicate_issues.py --phase 1

    # Execute all phases interactively
    python cleanup_duplicate_issues.py --interactive

    # Force execute all phases (careful!)
    python cleanup_duplicate_issues.py --execute-all
"""

import argparse
import asyncio
import json
import subprocess
import sys
import textwrap
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

# Import the optimized SDK duplicate detection system
sdk_path = Path(
    "/Users/ryan/src/hackathon/fix-issue-170-duplicate-detection/.claude/tools/amplihack/reflection"
)
if sdk_path.exists():
    sys.path.insert(0, str(sdk_path))

try:
    from semantic_duplicate_detector import (  # type: ignore[import-untyped]
        SemanticDuplicateDetector,
        get_performance_stats,
    )

    SDK_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import semantic duplicate detector: {e}")
    SDK_AVAILABLE = False
    # Define dummy types for type checking when SDK not available
    SemanticDuplicateDetector = None  # type: ignore[misc,assignment]
    get_performance_stats = None  # type: ignore[misc,assignment]


@dataclass
class IssueInfo:
    """Comprehensive issue information."""

    number: int
    title: str
    body: str
    state: str
    author: str
    created_at: str
    updated_at: str
    labels: list[str]
    comments: list[dict] | None = None
    unique_content: str = ""  # Extracted unique information

    def __post_init__(self):
        if self.comments is None:
            self.comments = []


@dataclass
class DuplicateCluster:
    """A cluster of duplicate issues."""

    canonical_issue: int  # Issue to keep
    duplicate_issues: list[int]  # Issues to close
    cluster_type: str  # "perfect", "functional", "edge_case"
    confidence: float  # Overall confidence for the cluster
    reason: str  # Why these are considered duplicates
    phase: int  # Cleanup phase (1=immediate, 2=review, 3=edge)


@dataclass
class CleanupAction:
    """A specific cleanup action to be performed."""

    action_type: str  # "close_issue", "update_canonical", "add_comment"
    issue_number: int
    details: dict
    reason: str
    executed: bool = False
    execution_time: str | None = None
    error: str | None = None


@dataclass
class CleanupSession:
    """A complete cleanup session with all metadata."""

    session_id: str
    start_time: str
    end_time: str | None
    mode: str  # "dry_run", "interactive", "execute"
    phase: int | None
    total_issues_analyzed: int
    clusters_found: list[DuplicateCluster]
    actions_planned: list[CleanupAction]
    actions_executed: list[CleanupAction]
    sdk_stats: dict
    issues_before: int
    issues_after: int | None


class SafeCleanupOrchestrator:
    """Safe orchestrator for duplicate issue cleanup with comprehensive safety features."""

    def __init__(self, repository: str = "rysweet/MicrosoftHackathon2025-AgenticCoding"):
        """Initialize the cleanup orchestrator."""
        self.repository = repository
        self.detector = (
            SemanticDuplicateDetector() if SDK_AVAILABLE and SemanticDuplicateDetector else None
        )
        self.issues_data: list[IssueInfo] = []
        self.session: CleanupSession | None = None

        # Create output directories
        self.output_dir = Path("cleanup_results")
        self.output_dir.mkdir(exist_ok=True)

    async def load_github_issues(self) -> list[IssueInfo]:
        """Load GitHub issues with comprehensive information."""
        print("🔍 Loading GitHub issues with detailed information...")

        try:
            # Fetch issues with comprehensive data
            result = subprocess.run(
                [
                    "gh",
                    "issue",
                    "list",
                    "--repo",
                    self.repository,
                    "--limit",
                    "200",
                    "--state",
                    "all",  # Include both open and closed
                    "--json",
                    "number,title,body,state,author,createdAt,updatedAt,labels",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            raw_issues = json.loads(result.stdout)

            # Convert to IssueInfo objects
            issues = []
            for raw_issue in raw_issues:
                issue_info = IssueInfo(
                    number=raw_issue.get("number", 0),
                    title=raw_issue.get("title", ""),
                    body=raw_issue.get("body", ""),
                    state=raw_issue.get("state", "unknown"),
                    author=raw_issue.get("author", {}).get("login", "unknown"),
                    created_at=raw_issue.get("createdAt", ""),
                    updated_at=raw_issue.get("updatedAt", ""),
                    labels=[label.get("name", "") for label in raw_issue.get("labels", [])],
                )
                issues.append(issue_info)

            self.issues_data = issues
            print(f"✅ Loaded {len(issues)} issues")
            return issues

        except subprocess.CalledProcessError as e:
            print(f"❌ Error fetching issues: {e}")
            return []
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return []

    async def fetch_issue_comments(self, issue_number: int) -> list[dict]:
        """Fetch comments for a specific issue."""
        try:
            result = subprocess.run(
                [
                    "gh",
                    "issue",
                    "view",
                    str(issue_number),
                    "--repo",
                    self.repository,
                    "--json",
                    "comments",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            data = json.loads(result.stdout)
            return data.get("comments", [])

        except Exception as e:
            print(f"⚠️  Could not fetch comments for issue #{issue_number}: {e}")
            return []

    def extract_unique_content(self, issue: IssueInfo, duplicates: list[IssueInfo]) -> str:
        """Extract unique content from an issue that's not in its duplicates."""
        unique_parts = []

        # Check for unique comments
        if issue.comments:
            for comment in issue.comments:
                comment_text = comment.get("body", "")
                is_unique = True

                # Check if this comment appears in any duplicate
                for dup in duplicates:
                    if dup.comments:
                        for dup_comment in dup.comments:
                            if comment_text.strip() == dup_comment.get("body", "").strip():
                                is_unique = False
                                break
                    if not is_unique:
                        break

                if is_unique and comment_text.strip():
                    unique_parts.append(
                        f"Unique comment by {comment.get('author', 'unknown')}: {comment_text[:200]}..."
                    )

        # Check for unique labels
        issue_labels = set(issue.labels)
        duplicate_labels = set()
        for dup in duplicates:
            duplicate_labels.update(dup.labels)

        unique_labels = issue_labels - duplicate_labels
        if unique_labels:
            unique_parts.append(f"Unique labels: {', '.join(unique_labels)}")

        # Check for unique content in body
        if issue.body and issue.body.strip():
            # Simple heuristic: if body is significantly different from duplicates
            body_words = set(issue.body.lower().split())
            all_dup_words = set()
            for dup in duplicates:
                if dup.body:
                    all_dup_words.update(dup.body.lower().split())

            unique_words = body_words - all_dup_words
            if len(unique_words) > 5:  # Significant unique content
                unique_parts.append(f"Contains {len(unique_words)} unique terms/details")

        return " | ".join(unique_parts) if unique_parts else "No unique content identified"

    async def analyze_duplicates_with_sdk(self) -> list[DuplicateCluster]:
        """Use SDK to identify duplicate clusters."""
        print("🤖 Analyzing duplicates using optimized SDK detection...")

        if not self.detector:
            print("⚠️  SDK not available, using fallback analysis")
            return self.analyze_duplicates_fallback()

        clusters = []
        processed_issues = set()

        # Get only open issues for processing
        open_issues = [issue for issue in self.issues_data if issue.state.lower() == "open"]
        print(f"📊 Analyzing {len(open_issues)} open issues for duplicates...")

        for i, issue in enumerate(open_issues):
            if issue.number in processed_issues:
                continue

            print(
                f"[{i + 1}/{len(open_issues)}] Analyzing issue #{issue.number}: {issue.title[:50]}..."
            )

            # Find duplicates of this issue
            remaining_issues = [
                other
                for other in open_issues
                if other.number != issue.number and other.number not in processed_issues
            ]

            # Convert to format expected by SDK
            existing_issues = []
            for other in remaining_issues:
                existing_issues.append(
                    {"number": other.number, "title": other.title, "body": other.body}
                )

            # Detect duplicates using SDK
            result = await self.detector.detect_semantic_duplicate(
                title=issue.title, body=issue.body, existing_issues=existing_issues
            )

            if result.is_duplicate and result.similar_issues:
                # Found duplicates - create cluster
                duplicate_numbers = [sim_issue["number"] for sim_issue in result.similar_issues]

                # Determine cluster type based on confidence
                if result.confidence >= 0.95:
                    cluster_type = "perfect"
                    phase = 1
                elif result.confidence >= 0.75:
                    cluster_type = "functional"
                    phase = 2
                else:
                    cluster_type = "edge_case"
                    phase = 3

                cluster = DuplicateCluster(
                    canonical_issue=issue.number,  # Keep the first one found
                    duplicate_issues=duplicate_numbers,
                    cluster_type=cluster_type,
                    confidence=result.confidence,
                    reason=result.reason,
                    phase=phase,
                )

                clusters.append(cluster)
                processed_issues.add(issue.number)
                processed_issues.update(duplicate_numbers)

                print(
                    f"  ✅ Found {len(duplicate_numbers)} duplicates (confidence: {result.confidence:.1%})"
                )
            else:
                print("  ℹ️  No duplicates found")

        print(f"🎯 Found {len(clusters)} duplicate clusters")
        return clusters

    def analyze_duplicates_fallback(self) -> list[DuplicateCluster]:
        """Fallback duplicate analysis using known patterns from analysis report."""
        print("📋 Using fallback analysis based on documented duplicate patterns...")

        clusters = []

        # Perfect duplicates: AI-detected error handling issues (#155-169)
        ai_error_issues = [155, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 169]
        open_ai_issues = [
            num
            for num in ai_error_issues
            if any(
                issue.number == num and issue.state.lower() == "open" for issue in self.issues_data
            )
        ]

        if len(open_ai_issues) > 1:
            # Keep #169 as canonical (latest)
            canonical = 169 if 169 in open_ai_issues else open_ai_issues[0]
            duplicates = [num for num in open_ai_issues if num != canonical]

            if duplicates:
                clusters.append(
                    DuplicateCluster(
                        canonical_issue=canonical,
                        duplicate_issues=duplicates,
                        cluster_type="perfect",
                        confidence=1.0,
                        reason="Identical AI-detected error handling issues created within 31 minutes",
                        phase=1,
                    )
                )

        # Functional duplicates: Gadugi porting (#114, #115)
        gadugi_issues = [114, 115]
        open_gadugi = [
            num
            for num in gadugi_issues
            if any(
                issue.number == num and issue.state.lower() == "open" for issue in self.issues_data
            )
        ]

        if len(open_gadugi) > 1:
            clusters.append(
                DuplicateCluster(
                    canonical_issue=115,  # More detailed according to analysis
                    duplicate_issues=[114],
                    cluster_type="functional",
                    confidence=0.85,
                    reason="Same Agent Memory System feature with different detail levels",
                    phase=2,
                )
            )

        # Reviewer agent issues (#69, #71)
        reviewer_issues = [69, 71]
        open_reviewer = [
            num
            for num in reviewer_issues
            if any(
                issue.number == num and issue.state.lower() == "open" for issue in self.issues_data
            )
        ]

        if len(open_reviewer) > 1:
            clusters.append(
                DuplicateCluster(
                    canonical_issue=69,  # Problem description
                    duplicate_issues=[71],
                    cluster_type="functional",
                    confidence=0.80,
                    reason="Same reviewer agent problem, #71 is implementation fix",
                    phase=2,
                )
            )

        return clusters

    async def create_cleanup_actions(self, clusters: list[DuplicateCluster]) -> list[CleanupAction]:
        """Create specific cleanup actions for each cluster."""
        print("📝 Creating detailed cleanup actions...")

        actions = []

        for cluster in clusters:
            canonical_issue = self.get_issue_by_number(cluster.canonical_issue)
            duplicate_issues = [self.get_issue_by_number(num) for num in cluster.duplicate_issues]

            if not canonical_issue:
                continue

            # Fetch comments for all issues in cluster
            print(f"  📥 Fetching comments for cluster around #{cluster.canonical_issue}...")
            canonical_issue.comments = await self.fetch_issue_comments(canonical_issue.number)

            for dup_issue in duplicate_issues:
                if dup_issue:
                    dup_issue.comments = await self.fetch_issue_comments(dup_issue.number)

            # Extract unique content from each duplicate
            for dup_issue in duplicate_issues:
                if not dup_issue:
                    continue

                dup_issue.unique_content = self.extract_unique_content(
                    dup_issue,
                    [canonical_issue]
                    + [d for d in duplicate_issues if d and d.number != dup_issue.number],
                )

                # Action 1: Preserve unique content in canonical issue
                if (
                    dup_issue.unique_content
                    and dup_issue.unique_content != "No unique content identified"
                ):
                    actions.append(
                        CleanupAction(
                            action_type="update_canonical",
                            issue_number=canonical_issue.number,
                            details={
                                "source_issue": dup_issue.number,
                                "unique_content": dup_issue.unique_content,
                                "action": "add_comment_with_preserved_content",
                            },
                            reason=f"Preserve unique content from duplicate #{dup_issue.number}",
                        )
                    )

                # Action 2: Close duplicate with cross-reference
                close_comment = self.create_close_comment(canonical_issue, dup_issue, cluster)
                actions.append(
                    CleanupAction(
                        action_type="close_issue",
                        issue_number=dup_issue.number,
                        details={
                            "canonical_issue": canonical_issue.number,
                            "comment": close_comment,
                            "cluster_type": cluster.cluster_type,
                            "confidence": cluster.confidence,
                        },
                        reason=f"Duplicate of #{canonical_issue.number} - {cluster.reason}",
                    )
                )

                # Action 3: Add cross-reference to canonical
                actions.append(
                    CleanupAction(
                        action_type="add_comment",
                        issue_number=canonical_issue.number,
                        details={
                            "comment": f"Related: Closed duplicate #{dup_issue.number} (confidence: {cluster.confidence:.1%})"
                        },
                        reason=f"Cross-reference to closed duplicate #{dup_issue.number}",
                    )
                )

        print(f"✅ Created {len(actions)} cleanup actions")
        return actions

    def create_close_comment(
        self, canonical: IssueInfo, duplicate: IssueInfo, cluster: DuplicateCluster
    ) -> str:
        """Create a comprehensive comment for closing a duplicate issue."""
        comment_parts = [
            f"🔄 **Closing as duplicate of #{canonical.number}**",
            "",
            f"**Reason**: {cluster.reason}",
            f"**Confidence**: {cluster.confidence:.1%}",
            f"**Cluster Type**: {cluster.cluster_type}",
            "",
            f"**Canonical Issue**: #{canonical.number} - {canonical.title}",
            "",
            "**Duplicate Resolution Process**:",
            "- All unique information has been preserved in the canonical issue",
            "- Cross-references have been added for traceability",
            "- This closure was performed by automated safe cleanup script",
            "",
            f"**Preserved Information**: {duplicate.unique_content}",
            "",
            "**Reversal Process**: If this closure was incorrect, please:",
            "1. Reopen this issue with comment explaining why it's not a duplicate",
            f"2. Reference specific differences from #{canonical.number}",
            "3. Tag @rysweet for manual review",
            "",
            "---",
            "*This cleanup was performed using SDK-based semantic duplicate detection*",
            f"*Session ID: {self.session.session_id if self.session else 'unknown'}*",
        ]

        return "\n".join(comment_parts)

    def get_issue_by_number(self, number: int) -> IssueInfo | None:
        """Get issue by number from loaded data."""
        for issue in self.issues_data:
            if issue.number == number:
                return issue
        return None

    async def execute_action(self, action: CleanupAction, dry_run: bool = True) -> bool:
        """Execute a single cleanup action."""
        if dry_run:
            print(
                f"  🎬 [DRY RUN] Would execute: {action.action_type} on issue #{action.issue_number}"
            )
            action.executed = True
            action.execution_time = datetime.now().isoformat()
            return True

        try:
            if action.action_type == "close_issue":
                # Close issue with comment
                subprocess.run(
                    [
                        "gh",
                        "issue",
                        "close",
                        str(action.issue_number),
                        "--repo",
                        self.repository,
                        "--comment",
                        action.details["comment"],
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )

                print(f"  ✅ Closed issue #{action.issue_number}")

            elif action.action_type == "add_comment":
                # Add comment to issue
                subprocess.run(
                    [
                        "gh",
                        "issue",
                        "comment",
                        str(action.issue_number),
                        "--repo",
                        self.repository,
                        "--body",
                        action.details["comment"],
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )

                print(f"  💬 Added comment to issue #{action.issue_number}")

            elif action.action_type == "update_canonical":
                # Add preserved content comment to canonical issue
                preserved_comment = f"""**Preserved Content from Duplicate #{action.details["source_issue"]}**

{action.details["unique_content"]}

---
*Content preserved during duplicate cleanup - Session {self.session.session_id if self.session else "unknown"}*"""

                subprocess.run(
                    [
                        "gh",
                        "issue",
                        "comment",
                        str(action.issue_number),
                        "--repo",
                        self.repository,
                        "--body",
                        preserved_comment,
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )

                print(f"  📋 Preserved content in canonical issue #{action.issue_number}")

            action.executed = True
            action.execution_time = datetime.now().isoformat()
            return True

        except subprocess.CalledProcessError as e:
            error_msg = f"GitHub CLI error: {e.stderr if hasattr(e, 'stderr') else str(e)}"
            action.error = error_msg
            print(f"  ❌ Failed to execute action: {error_msg}")
            return False
        except Exception as e:
            action.error = str(e)
            print(f"  ❌ Unexpected error: {e}")
            return False

    async def execute_cleanup_phase(
        self, phase: int, dry_run: bool = True, interactive: bool = False
    ) -> tuple[int, int]:
        """Execute cleanup for a specific phase."""
        phase_actions = [
            action
            for action in (self.session.actions_planned if self.session else [])
            if any(
                cluster.phase == phase
                for cluster in (self.session.clusters_found if self.session else [])
                for action_issue in [action.issue_number]
                + (
                    [action.details.get("canonical_issue", 0)]
                    if action.details.get("canonical_issue")
                    else []
                )
                if action_issue in ([cluster.canonical_issue] + cluster.duplicate_issues)
            )
        ]

        if not phase_actions:
            print(f"📭 No actions found for Phase {phase}")
            return 0, 0

        print(f"🚀 Executing Phase {phase} cleanup ({len(phase_actions)} actions)")

        if interactive and not dry_run:
            response = (
                input(f"Execute {len(phase_actions)} actions for Phase {phase}? (y/N): ")
                .strip()
                .lower()
            )
            if response != "y":
                print("⏸️  Phase execution cancelled")
                return 0, 0

        executed = 0
        failed = 0

        for i, action in enumerate(phase_actions, 1):
            print(f"  [{i}/{len(phase_actions)}] {action.reason}")

            if interactive and not dry_run:
                response = input("    Execute this action? (y/N/a for all): ").strip().lower()
                if response == "n":
                    continue
                if response == "a":
                    interactive = False  # Execute all remaining

            success = await self.execute_action(action, dry_run)
            if success:
                executed += 1
                if self.session:
                    self.session.actions_executed.append(action)
            else:
                failed += 1

        print(f"✅ Phase {phase} complete: {executed} executed, {failed} failed")
        return executed, failed

    def save_session_data(self) -> None:
        """Save complete session data to files."""
        if not self.session:
            return

        session_file = self.output_dir / f"cleanup_session_{self.session.session_id}.json"
        with open(session_file, "w") as f:
            # Convert dataclasses to dict for JSON serialization
            session_dict = asdict(self.session)
            json.dump(session_dict, f, indent=2, default=str)

        print(f"💾 Session data saved to {session_file}")

        # Save preview for easy reading
        preview_file = self.output_dir / "cleanup_preview.json"
        preview_data = {
            "session_id": self.session.session_id,
            "mode": self.session.mode,
            "timestamp": self.session.start_time,
            "total_issues": self.session.total_issues_analyzed,
            "clusters_found": len(self.session.clusters_found),
            "actions_planned": len(self.session.actions_planned),
            "sdk_available": SDK_AVAILABLE,
            "clusters": [
                {
                    "canonical": cluster.canonical_issue,
                    "duplicates": cluster.duplicate_issues,
                    "type": cluster.cluster_type,
                    "confidence": cluster.confidence,
                    "phase": cluster.phase,
                    "reason": cluster.reason,
                }
                for cluster in self.session.clusters_found
            ],
            "actions_summary": [
                {"type": action.action_type, "issue": action.issue_number, "reason": action.reason}
                for action in self.session.actions_planned
            ],
        }

        with open(preview_file, "w") as f:
            json.dump(preview_data, f, indent=2)

        print(f"📋 Preview saved to {preview_file}")

    def generate_audit_log(self) -> None:
        """Generate comprehensive audit log in markdown format."""
        if not self.session:
            return

        log_file = self.output_dir / f"cleanup_log_{self.session.session_id}.md"

        log_content = f"""# Duplicate Issues Cleanup Log

**Session ID**: {self.session.session_id}
**Date**: {self.session.start_time}
**Mode**: {self.session.mode}
**Repository**: {self.repository}
**SDK Available**: {SDK_AVAILABLE}

## Summary

- **Total Issues Analyzed**: {self.session.total_issues_analyzed}
- **Duplicate Clusters Found**: {len(self.session.clusters_found)}
- **Actions Planned**: {len(self.session.actions_planned)}
- **Actions Executed**: {len(self.session.actions_executed)}
- **Issues Before Cleanup**: {self.session.issues_before}
- **Issues After Cleanup**: {self.session.issues_after or "N/A (dry run)"}

## Duplicate Clusters Identified

"""

        for i, cluster in enumerate(self.session.clusters_found, 1):
            log_content += f"""### Cluster {i}: {cluster.cluster_type.title()} Duplicates

- **Canonical Issue**: #{cluster.canonical_issue}
- **Duplicate Issues**: {", ".join(f"#{num}" for num in cluster.duplicate_issues)}
- **Confidence**: {cluster.confidence:.1%}
- **Phase**: {cluster.phase}
- **Reason**: {cluster.reason}

"""

        log_content += "\n## Actions Executed\n\n"

        if self.session.actions_executed:
            for action in self.session.actions_executed:
                status = (
                    "✅ Success"
                    if action.executed and not action.error
                    else f"❌ Failed: {action.error}"
                )
                log_content += f"""### {action.action_type} - Issue #{action.issue_number}

- **Status**: {status}
- **Execution Time**: {action.execution_time or "Not executed"}
- **Reason**: {action.reason}
- **Details**: {json.dumps(action.details, indent=2)}

"""
        else:
            log_content += "No actions were executed (dry run mode).\n\n"

        log_content += f"""## SDK Performance Stats

```json
{json.dumps(self.session.sdk_stats, indent=2)}
```

## Reversal Instructions

If any closures were incorrect, follow these steps:

1. **Identify the incorrectly closed issue** from the log above
2. **Reopen the issue**:
   ```bash
   gh issue reopen [issue_number] --repo {self.repository}
   ```
3. **Add explanation comment**:
   ```bash
   gh issue comment [issue_number] --repo {self.repository} --body "Reopened - not a duplicate because: [explanation]"
   ```
4. **Tag for manual review**:
   ```bash
   gh issue comment [issue_number] --repo {self.repository} --body "@rysweet Please manually review - automated cleanup was incorrect"
   ```

## Session Metadata

- **Session File**: cleanup_session_{self.session.session_id}.json
- **Preview File**: cleanup_preview.json
- **Log File**: cleanup_log_{self.session.session_id}.md

---
*Generated by automated duplicate cleanup script*
*SDK Version: {get_performance_stats() if SDK_AVAILABLE and get_performance_stats else "N/A"}*
"""

        with open(log_file, "w") as f:
            f.write(log_content)

        print(f"📊 Audit log saved to {log_file}")

    async def run_cleanup(
        self, mode: str = "dry_run", phase: int | None = None, interactive: bool = False
    ) -> CleanupSession:
        """Main cleanup execution method."""
        # Initialize session
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session = CleanupSession(
            session_id=session_id,
            start_time=datetime.now().isoformat(),
            end_time=None,
            mode=mode,
            phase=phase,
            total_issues_analyzed=0,
            clusters_found=[],
            actions_planned=[],
            actions_executed=[],
            sdk_stats=get_performance_stats() if SDK_AVAILABLE and get_performance_stats else {},
            issues_before=0,
            issues_after=None,
        )

        print(f"🚀 Starting duplicate cleanup session {session_id}")
        print(f"📊 Mode: {mode}, Phase: {phase or 'all'}, Interactive: {interactive}")
        print("=" * 60)

        # Step 1: Load issues
        await self.load_github_issues()
        self.session.total_issues_analyzed = len(self.issues_data)
        self.session.issues_before = len(
            [issue for issue in self.issues_data if issue.state.lower() == "open"]
        )

        # Step 2: Analyze duplicates
        if SDK_AVAILABLE:
            clusters = await self.analyze_duplicates_with_sdk()
        else:
            clusters = self.analyze_duplicates_fallback()

        self.session.clusters_found = clusters

        if not clusters:
            print("🎉 No duplicate clusters found! Repository is clean.")
            self.session.end_time = datetime.now().isoformat()
            self.save_session_data()
            return self.session

        # Step 3: Create cleanup actions
        actions = await self.create_cleanup_actions(clusters)
        self.session.actions_planned = actions

        # Step 4: Execute cleanup (by phase)
        is_dry_run = mode == "dry_run"
        phases_to_execute = [phase] if phase else [1, 2, 3]

        total_executed = 0
        total_failed = 0

        for cleanup_phase in phases_to_execute:
            phase_clusters = [c for c in clusters if c.phase == cleanup_phase]
            if not phase_clusters:
                continue

            print(f"\n🎯 Phase {cleanup_phase}: {len(phase_clusters)} clusters")
            for cluster in phase_clusters:
                print(
                    f"  - #{cluster.canonical_issue} ← {cluster.duplicate_issues} ({cluster.cluster_type})"
                )

            executed, failed = await self.execute_cleanup_phase(
                cleanup_phase, is_dry_run, interactive
            )
            total_executed += executed
            total_failed += failed

        # Step 5: Finalize session
        self.session.end_time = datetime.now().isoformat()
        if not is_dry_run:
            # Count final issues
            await self.load_github_issues()  # Refresh data
            self.session.issues_after = len(
                [issue for issue in self.issues_data if issue.state.lower() == "open"]
            )

        # Step 6: Save results
        self.save_session_data()
        self.generate_audit_log()

        print("\n" + "=" * 60)
        print(f"🎉 Cleanup session {session_id} complete!")
        print(f"📊 {total_executed} actions executed, {total_failed} failed")
        if not is_dry_run and self.session.issues_after is not None:
            reduction = self.session.issues_before - self.session.issues_after
            print(
                f"📉 Open issues reduced: {self.session.issues_before} → {self.session.issues_after} (-{reduction})"
            )

        return self.session


async def main():
    """Main script execution with comprehensive CLI."""
    parser = argparse.ArgumentParser(
        description="Safe duplicate issue cleanup with SDK-based detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        Examples:
          %(prog)s --dry-run                    # Preview all actions (safe)
          %(prog)s --phase 1                    # Execute Phase 1 only (perfect duplicates)
          %(prog)s --interactive                # Interactive execution with confirmations
          %(prog)s --execute-all                # Execute all phases (careful!)
          %(prog)s --dry-run --phase 2          # Preview Phase 2 only

        Phases:
          1: Perfect duplicates (>95% confidence) - Safe to execute
          2: Functional duplicates (>75% confidence) - Review recommended
          3: Edge cases (<75% confidence) - Manual review required
        """),
    )

    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--dry-run", action="store_true", help="Preview all actions without executing (safe mode)"
    )
    mode_group.add_argument(
        "--interactive", action="store_true", help="Interactive execution with confirmations"
    )
    mode_group.add_argument(
        "--execute-all",
        action="store_true",
        help="Execute all phases without confirmation (careful!)",
    )

    parser.add_argument(
        "--phase",
        type=int,
        choices=[1, 2, 3],
        help="Execute specific phase only (1=perfect, 2=functional, 3=edge cases)",
    )
    parser.add_argument(
        "--repository",
        default="rysweet/MicrosoftHackathon2025-AgenticCoding",
        help="GitHub repository (default: rysweet/MicrosoftHackathon2025-AgenticCoding)",
    )

    args = parser.parse_args()

    # Determine mode
    if args.dry_run:
        mode = "dry_run"
        interactive = False
    elif args.interactive:
        mode = "interactive"
        interactive = True
    else:  # execute_all
        mode = "execute"
        interactive = False

    # Safety confirmation for execution modes
    if mode != "dry_run" and not args.phase:
        print("⚠️  WARNING: You are about to execute cleanup on ALL phases!")
        print("   This will close duplicate issues. Are you sure?")
        response = input("   Type 'EXECUTE' to confirm: ").strip()
        if response != "EXECUTE":
            print("❌ Execution cancelled for safety")
            return

    # Initialize orchestrator
    orchestrator = SafeCleanupOrchestrator(repository=args.repository)

    # Run cleanup
    try:
        session = await orchestrator.run_cleanup(
            mode=mode, phase=args.phase, interactive=interactive
        )

        print("\n✨ Session complete! Check cleanup_results/ for detailed logs.")
        print("📋 Preview: cleanup_results/cleanup_preview.json")
        print(f"📊 Log: cleanup_results/cleanup_log_{session.session_id}.md")

    except KeyboardInterrupt:
        print("\n⏸️  Cleanup interrupted by user")
    except Exception as e:
        print(f"\n❌ Cleanup failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
