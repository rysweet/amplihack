#!/usr/bin/env python3
"""Aggregate priorities across GitHub accounts into a strict Top 5 ranked list.

Queries GitHub issues and PRs across configured accounts/repos, scores them
by priority labels, staleness, blocking status, and roadmap alignment.

Falls back to .pm/ YAML state if GitHub is unavailable or for enrichment.

Usage:
    python generate_top5.py [--project-root PATH] [--sources PATH]

Returns JSON with top 5 priorities.
"""

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml


# Aggregation weights
WEIGHT_ISSUES = 0.40
WEIGHT_PRS = 0.30
WEIGHT_ROADMAP = 0.20
WEIGHT_LOCAL = 0.10  # .pm/ overrides

TOP_N = 5

# Label-to-priority mapping
PRIORITY_LABELS = {
    "critical": 1.0,
    "priority:critical": 1.0,
    "high": 0.9,
    "priority:high": 0.9,
    "bug": 0.8,
    "medium": 0.6,
    "priority:medium": 0.6,
    "enhancement": 0.5,
    "feature": 0.5,
    "low": 0.3,
    "priority:low": 0.3,
}


def load_yaml(path: Path) -> dict[str, Any]:
    """Load YAML file safely."""
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_sources(sources_path: Path) -> list[dict]:
    """Load GitHub source configuration."""
    data = load_yaml(sources_path)
    return data.get("github", [])


def run_gh(args: list[str], account: str | None = None) -> str | None:
    """Run a gh CLI command, optionally switching account first.

    Returns stdout on success, None on failure.
    """
    if account:
        switch = subprocess.run(
            ["gh", "auth", "switch", "--user", account],
            capture_output=True, text=True, timeout=10,
        )
        if switch.returncode != 0:
            return None

    try:
        result = subprocess.run(
            ["gh"] + args,
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def get_current_gh_account() -> str | None:
    """Get the currently active gh account."""
    try:
        result = subprocess.run(
            ["gh", "api", "user", "--jq", ".login"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def fetch_github_issues(account: str, repos: list[str]) -> list[dict]:
    """Fetch open issues for an account's repos from GitHub."""
    candidates = []

    # Use search API to get all issues at once
    repo_qualifiers = " ".join(f"repo:{r}" if "/" in r else f"repo:{account}/{r}" for r in repos)
    query = f"is:open is:issue {repo_qualifiers}"

    jq_filter = (
        '.items[] | {'
        'repo: (.repository_url | split("/") | .[-2:] | join("/")),'
        'title: .title,'
        'labels: [.labels[].name],'
        'created: .created_at,'
        'updated: .updated_at,'
        'number: .number,'
        'comments: .comments'
        '}'
    )

    output = run_gh(
        ["api", "search/issues", "--method", "GET",
         "-f", f"q={query}", "-f", "per_page=50",
         "--jq", jq_filter],
        account=account,
    )

    if not output:
        return []

    now = datetime.now(UTC)

    for line in output.strip().splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue

        # Score by labels
        labels = [lbl.lower() for lbl in item.get("labels", [])]
        priority_score = 0.5  # default
        for label in labels:
            if label in PRIORITY_LABELS:
                priority_score = max(priority_score, PRIORITY_LABELS[label])

        # Staleness boost: older updated = needs attention
        try:
            updated = datetime.fromisoformat(item["updated"].replace("Z", "+00:00"))
            days_stale = (now - updated).total_seconds() / 86400
        except (ValueError, KeyError):
            days_stale = 0

        staleness_score = min(days_stale / 14.0, 1.0)  # Max at 2 weeks

        # Comment activity: more comments = more discussion = potentially blocked
        comments = item.get("comments", 0)
        activity_score = min(comments / 10.0, 1.0)

        raw_score = (priority_score * 0.50 + staleness_score * 0.30 + activity_score * 0.20) * 100

        # Rationale
        reasons = []
        if priority_score >= 0.8:
            reasons.append(f"labeled {', '.join(lbl for lbl in labels if lbl in PRIORITY_LABELS)}")
        if days_stale > 7:
            reasons.append(f"stale {days_stale:.0f}d")
        if comments > 3:
            reasons.append(f"{comments} comments")
        if not reasons:
            reasons.append("open issue")

        repo = item.get("repo", "")
        candidates.append({
            "title": item["title"],
            "source": "github_issue",
            "raw_score": round(raw_score, 1),
            "score_breakdown": {
                "label_priority": round(priority_score, 2),
                "staleness": round(staleness_score, 2),
                "activity": round(activity_score, 2),
            },
            "rationale": ", ".join(reasons),
            "item_id": f"{repo}#{item['number']}",
            "priority": "HIGH" if priority_score >= 0.8 else "MEDIUM" if priority_score >= 0.5 else "LOW",
            "repo": repo,
            "account": account,
            "url": f"https://github.com/{repo}/issues/{item['number']}",
            "labels": item.get("labels", []),
            "created": item.get("created", ""),
            "updated": item.get("updated", ""),
            "days_stale": round(days_stale, 1),
            "comments": comments,
        })

    return candidates


def fetch_github_prs(account: str, repos: list[str]) -> list[dict]:
    """Fetch open PRs for an account's repos from GitHub."""
    candidates = []

    repo_qualifiers = " ".join(f"repo:{r}" if "/" in r else f"repo:{account}/{r}" for r in repos)
    query = f"is:open is:pr {repo_qualifiers}"

    jq_filter = (
        '.items[] | {'
        'repo: (.repository_url | split("/") | .[-2:] | join("/")),'
        'title: .title,'
        'labels: [.labels[].name],'
        'created: .created_at,'
        'updated: .updated_at,'
        'number: .number,'
        'draft: .draft,'
        'comments: .comments'
        '}'
    )

    output = run_gh(
        ["api", "search/issues", "--method", "GET",
         "-f", f"q={query}", "-f", "per_page=50",
         "--jq", jq_filter],
        account=account,
    )

    if not output:
        return []

    now = datetime.now(UTC)

    for line in output.strip().splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue

        is_draft = item.get("draft", False)

        # PRs waiting for review are higher priority than drafts
        base_score = 0.4 if is_draft else 0.7

        # Labels boost
        labels = [lbl.lower() for lbl in item.get("labels", [])]
        for label in labels:
            if label in PRIORITY_LABELS:
                base_score = max(base_score, PRIORITY_LABELS[label])

        # Staleness: PRs waiting for review get more urgent over time
        try:
            updated = datetime.fromisoformat(item["updated"].replace("Z", "+00:00"))
            days_stale = (now - updated).total_seconds() / 86400
        except (ValueError, KeyError):
            days_stale = 0

        staleness_score = min(days_stale / 7.0, 1.0)  # PRs stale faster (1 week max)

        raw_score = (base_score * 0.60 + staleness_score * 0.40) * 100

        reasons = []
        if is_draft:
            reasons.append("draft PR")
        else:
            reasons.append("awaiting review")
        if days_stale > 3:
            reasons.append(f"stale {days_stale:.0f}d")
        if labels:
            relevant = [lbl for lbl in labels if lbl in PRIORITY_LABELS]
            if relevant:
                reasons.append(f"labeled {', '.join(relevant)}")

        repo = item.get("repo", "")
        candidates.append({
            "title": item["title"],
            "source": "github_pr",
            "raw_score": round(raw_score, 1),
            "score_breakdown": {
                "base_priority": round(base_score, 2),
                "staleness": round(staleness_score, 2),
            },
            "rationale": ", ".join(reasons),
            "item_id": f"{repo}#{item['number']}",
            "priority": "HIGH" if base_score >= 0.8 else "MEDIUM",
            "repo": repo,
            "account": account,
            "url": f"https://github.com/{repo}/pull/{item['number']}",
            "labels": item.get("labels", []),
            "created": item.get("created", ""),
            "updated": item.get("updated", ""),
            "days_stale": round(days_stale, 1),
            "is_draft": is_draft,
        })

    return candidates


def load_local_overrides(pm_dir: Path) -> list[dict]:
    """Load manually-added items from .pm/backlog for local enrichment."""
    backlog_data = load_yaml(pm_dir / "backlog" / "items.yaml")
    items = backlog_data.get("items", [])
    ready_items = [item for item in items if item.get("status") == "READY"]

    candidates = []
    priority_map = {"HIGH": 1.0, "MEDIUM": 0.6, "LOW": 0.3}

    for item in ready_items:
        priority = item.get("priority", "MEDIUM")
        priority_score = priority_map.get(priority, 0.5)
        hours = item.get("estimated_hours", 4)
        ease_score = 1.0 if hours < 2 else 0.6 if hours <= 6 else 0.3

        raw_score = (priority_score * 0.60 + ease_score * 0.40) * 100

        reasons = []
        if priority == "HIGH":
            reasons.append("HIGH priority")
        if hours < 2:
            reasons.append("quick win")
        if not reasons:
            reasons.append("local backlog item")

        candidates.append({
            "title": item.get("title", item["id"]),
            "source": "local",
            "raw_score": round(raw_score, 1),
            "rationale": ", ".join(reasons),
            "item_id": item["id"],
            "priority": priority,
        })

    return candidates


def extract_roadmap_goals(pm_dir: Path) -> list[str]:
    """Extract strategic goals from roadmap markdown."""
    roadmap_path = pm_dir / "roadmap.md"
    if not roadmap_path.exists():
        return []

    text = roadmap_path.read_text()
    goals = []

    for line in text.splitlines():
        line = line.strip()
        if line.startswith("## ") or line.startswith("### "):
            goals.append(line.lstrip("#").strip())
        elif line.startswith("- "):
            goals.append(line.removeprefix("- ").strip())
        elif line.startswith("* "):
            goals.append(line.removeprefix("* ").strip())

    return goals


def score_roadmap_alignment(candidate: dict, goals: list[str]) -> float:
    """Score how well a candidate aligns with roadmap goals. Returns 0.0-1.0."""
    if not goals:
        return 0.5

    title_lower = candidate["title"].lower()
    max_alignment = 0.0

    for goal in goals:
        goal_words = set(goal.lower().split())
        goal_words -= {"the", "a", "an", "and", "or", "to", "for", "in", "of", "is", "with"}
        if not goal_words:
            continue

        matching = sum(1 for word in goal_words if word in title_lower)
        alignment = matching / len(goal_words) if goal_words else 0.0
        max_alignment = max(max_alignment, alignment)

    return min(max_alignment, 1.0)


def suggest_action(candidate: dict) -> str:
    """Suggest a concrete next action for a candidate."""
    source = candidate["source"]
    days_stale = candidate.get("days_stale", 0)
    labels = candidate.get("labels", [])

    if source == "github_pr":
        if candidate.get("is_draft"):
            return "Finish draft or close if abandoned"
        if days_stale > 14:
            return "Merge, close, or rebase — stale >2 weeks"
        if days_stale > 7:
            return "Review and merge or request changes"
        return "Review PR"
    elif source == "github_issue":
        if any(lbl in ("critical", "priority:critical") for lbl in labels):
            return "Fix immediately — critical severity"
        if any(lbl in ("bug",) for lbl in labels):
            return "Investigate and fix bug"
        if days_stale > 30:
            return "Triage: still relevant? Close or reprioritize"
        return "Work on issue or delegate"
    elif source == "local":
        return "Pick up from local backlog"
    return "Review"


def aggregate_and_rank(
    issues: list[dict],
    prs: list[dict],
    local: list[dict],
    goals: list[str],
    top_n: int = TOP_N,
) -> tuple[list[dict], list[dict]]:
    """Aggregate candidates from all sources and rank by weighted score.

    Returns (top_n items, next 5 near-misses).
    """
    scored = []

    source_weights = {
        "github_issue": WEIGHT_ISSUES,
        "github_pr": WEIGHT_PRS,
        "local": WEIGHT_LOCAL,
    }

    all_candidates = issues + prs + local

    for candidate in all_candidates:
        source = candidate["source"]
        source_weight = source_weights.get(source, 0.25)
        raw = candidate["raw_score"]

        alignment = score_roadmap_alignment(candidate, goals)
        final_score = (source_weight * raw) + (WEIGHT_ROADMAP * alignment * 100)

        entry = {
            "title": candidate["title"],
            "source": candidate["source"],
            "score": round(final_score, 1),
            "raw_score": candidate["raw_score"],
            "source_weight": source_weight,
            "rationale": candidate["rationale"],
            "item_id": candidate.get("item_id", ""),
            "priority": candidate.get("priority", "MEDIUM"),
            "alignment": round(alignment, 2),
            "action": suggest_action(candidate),
        }
        # Preserve all metadata from the candidate
        for key in ("url", "repo", "account", "labels", "created", "updated",
                     "days_stale", "comments", "is_draft", "score_breakdown"):
            if key in candidate:
                entry[key] = candidate[key]

        scored.append(entry)

    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    scored.sort(key=lambda x: (-x["score"], priority_order.get(x["priority"], 1)))

    top = scored[:top_n]
    for i, item in enumerate(top):
        item["rank"] = i + 1

    near_misses = scored[top_n:top_n + 5]
    for i, item in enumerate(near_misses):
        item["rank"] = top_n + i + 1

    return top, near_misses


def build_repo_summary(all_candidates: list[dict]) -> dict:
    """Build a per-repo, per-account summary of open work."""
    repos: dict[str, dict] = {}
    accounts: dict[str, dict] = {}

    for c in all_candidates:
        repo = c.get("repo", "local")
        account = c.get("account", "local")

        if repo not in repos:
            repos[repo] = {"issues": 0, "prs": 0, "high_priority": 0}
        if account not in accounts:
            accounts[account] = {"issues": 0, "prs": 0, "repos": set()}

        if c["source"] == "github_issue":
            repos[repo]["issues"] += 1
            accounts[account]["issues"] += 1
        elif c["source"] == "github_pr":
            repos[repo]["prs"] += 1
            accounts[account]["prs"] += 1

        if c.get("priority") == "HIGH":
            repos[repo]["high_priority"] += 1

        accounts[account]["repos"].add(repo)

    # Convert sets to lists for JSON serialization
    for a in accounts.values():
        a["repos"] = sorted(a["repos"])

    # Sort repos by total open items descending
    sorted_repos = dict(sorted(repos.items(), key=lambda x: -(x[1]["issues"] + x[1]["prs"])))

    return {"by_repo": sorted_repos, "by_account": accounts}


def generate_top5(project_root: Path, sources_path: Path | None = None) -> dict:
    """Generate the Top 5 priority list from GitHub + local state."""
    pm_dir = project_root / ".pm"

    if sources_path is None:
        sources_path = pm_dir / "sources.yaml"

    # Load GitHub sources config
    sources = load_sources(sources_path)

    # Remember original account to restore after
    original_account = get_current_gh_account()

    # Fetch from GitHub
    all_issues = []
    all_prs = []
    accounts_queried = []

    for source in sources:
        account = source.get("account", "")
        repos = source.get("repos", [])
        if not account or not repos:
            continue

        accounts_queried.append(account)
        all_issues.extend(fetch_github_issues(account, repos))
        all_prs.extend(fetch_github_prs(account, repos))

    # Restore original account
    if original_account and accounts_queried:
        run_gh(["auth", "switch", "--user", original_account])

    # Load local overrides
    local = []
    if pm_dir.exists():
        local = load_local_overrides(pm_dir)

    # Load roadmap goals
    goals = extract_roadmap_goals(pm_dir) if pm_dir.exists() else []

    # Aggregate and rank
    all_candidates = all_issues + all_prs + local
    top5, near_misses = aggregate_and_rank(all_issues, all_prs, local, goals)
    summary = build_repo_summary(all_candidates)

    return {
        "top5": top5,
        "near_misses": near_misses,
        "summary": summary,
        "sources": {
            "github_issues": len(all_issues),
            "github_prs": len(all_prs),
            "local_items": len(local),
            "roadmap_goals": len(goals),
            "accounts": accounts_queried,
        },
        "total_candidates": len(all_candidates),
    }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate Top 5 priorities from GitHub + local state")
    parser.add_argument(
        "--project-root", type=Path, default=Path.cwd(), help="Project root directory"
    )
    parser.add_argument(
        "--sources", type=Path, default=None, help="Path to sources.yaml (default: .pm/sources.yaml)"
    )

    args = parser.parse_args()

    try:
        result = generate_top5(args.project_root, args.sources)
        print(json.dumps(result, indent=2))
        return 0
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
