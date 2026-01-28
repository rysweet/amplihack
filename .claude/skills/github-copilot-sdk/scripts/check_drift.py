#!/usr/bin/env python3
"""
GitHub Copilot SDK Skill - Drift Detection and Validation Script

Checks for updates to official SDK documentation and validates skill content.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# Optional imports - graceful degradation if not available
try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    import tiktoken

    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False


# Configuration
SKILL_DIR = Path(__file__).parent.parent
SOURCE_URLS = {
    "sdk_repo": "https://api.github.com/repos/github/copilot-sdk/commits",
    "readme": "https://api.github.com/repos/github/copilot-sdk/commits?path=README.md",
    "getting_started": "https://api.github.com/repos/github/copilot-sdk/commits?path=docs/getting-started.md",
}
LAST_UPDATED = "2025-01-25"
TOKEN_BUDGET = 2000


def check_drift() -> dict:
    """Check if source documentation has changed since last update."""
    if not HAS_REQUESTS:
        return {"status": "ERROR", "message": "requests library not installed"}

    results = {"status": "CURRENT", "sources": {}}
    last_update = datetime.strptime(LAST_UPDATED, "%Y-%m-%d")

    for name, url in SOURCE_URLS.items():
        try:
            response = requests.get(url, headers={"Accept": "application/vnd.github.v3+json"})
            if response.status_code == 200:
                commits = response.json()
                if commits:
                    latest = commits[0]
                    commit_date = datetime.strptime(
                        latest["commit"]["committer"]["date"][:10], "%Y-%m-%d"
                    )
                    if commit_date > last_update:
                        results["status"] = "DRIFT DETECTED"
                        results["sources"][name] = {
                            "changed": True,
                            "latest_commit": latest["sha"][:7],
                            "date": commit_date.strftime("%Y-%m-%d"),
                            "message": latest["commit"]["message"].split("\n")[0][:50],
                        }
                    else:
                        results["sources"][name] = {"changed": False}
            else:
                results["sources"][name] = {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            results["sources"][name] = {"error": str(e)}

    return results


def count_tokens(file_path: Path) -> int | None:
    """Count tokens in a markdown file."""
    if not HAS_TIKTOKEN:
        return None

    try:
        encoding = tiktoken.encoding_for_model("gpt-4")
        content = file_path.read_text()
        return len(encoding.encode(content))
    except Exception:
        return None


def validate_yaml_frontmatter(file_path: Path) -> dict:
    """Validate YAML frontmatter in a skill file."""
    content = file_path.read_text()

    # Check for frontmatter
    if not content.startswith("---"):
        return {"valid": False, "error": "No YAML frontmatter found"}

    # Extract frontmatter
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {"valid": False, "error": "Invalid frontmatter structure"}

    frontmatter = parts[1].strip()

    # Check required fields
    required = ["name", "description"]
    missing = []
    for field in required:
        if f"{field}:" not in frontmatter:
            missing.append(field)

    if missing:
        return {"valid": False, "error": f"Missing required fields: {missing}"}

    return {"valid": True}


def check_example_syntax(file_path: Path) -> dict:
    """Basic syntax check on code examples."""
    content = file_path.read_text()
    results = {"valid": True, "issues": []}

    # Extract code blocks
    code_blocks = re.findall(r"```(\w+)\n(.*?)```", content, re.DOTALL)

    for lang, code in code_blocks:
        # Basic checks
        if lang in ["typescript", "javascript"]:
            # Check for unclosed braces
            if code.count("{") != code.count("}"):
                results["issues"].append(f"{lang}: Unbalanced braces")
            if code.count("(") != code.count(")"):
                results["issues"].append(f"{lang}: Unbalanced parentheses")

        elif lang == "python":
            # Check for obvious issues
            if "import" in code and code.count("import") > code.count("\n") + 1:
                results["issues"].append("Python: Multiple imports on same line")

        elif lang in ["go", "golang"]:
            if code.count("{") != code.count("}"):
                results["issues"].append("Go: Unbalanced braces")

        elif lang == "csharp":
            if code.count("{") != code.count("}"):
                results["issues"].append("C#: Unbalanced braces")

    if results["issues"]:
        results["valid"] = False

    return results


def check_links() -> dict:
    """Verify source URLs are accessible."""
    if not HAS_REQUESTS:
        return {"status": "ERROR", "message": "requests library not installed"}

    urls_to_check = [
        "https://github.com/github/copilot-sdk",
        "https://github.com/github/awesome-copilot",
    ]

    results = {"all_valid": True, "urls": {}}

    for url in urls_to_check:
        try:
            response = requests.head(url, allow_redirects=True, timeout=10)
            valid = response.status_code == 200
            results["urls"][url] = {"valid": valid, "status": response.status_code}
            if not valid:
                results["all_valid"] = False
        except Exception as e:
            results["urls"][url] = {"valid": False, "error": str(e)}
            results["all_valid"] = False

    return results


def generate_report() -> str:
    """Generate a full validation report."""
    lines = [
        "# GitHub Copilot SDK Skill - Validation Report",
        f"\n**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Last Updated**: {LAST_UPDATED}",
        "\n## Drift Detection\n",
    ]

    drift = check_drift()
    lines.append(f"**Status**: {drift['status']}\n")

    if drift.get("sources"):
        for name, info in drift["sources"].items():
            if info.get("changed"):
                lines.append(f"- ⚠️ **{name}**: Changed on {info['date']} - {info['message']}")
            elif info.get("error"):
                lines.append(f"- ❌ **{name}**: Error - {info['error']}")
            else:
                lines.append(f"- ✅ **{name}**: No changes")

    lines.append("\n## Token Counts\n")

    skill_files = [
        "SKILL.md",
        "reference.md",
        "examples.md",
        "patterns.md",
    ]

    for filename in skill_files:
        file_path = SKILL_DIR / filename
        if file_path.exists():
            tokens = count_tokens(file_path)
            if tokens is not None:
                status = "✅" if filename != "SKILL.md" or tokens < TOKEN_BUDGET else "⚠️"
                lines.append(f"- {status} **{filename}**: {tokens} tokens")
            else:
                lines.append(f"- ⚪ **{filename}**: Token counting unavailable")

    lines.append("\n## YAML Validation\n")

    skill_md = SKILL_DIR / "SKILL.md"
    if skill_md.exists():
        yaml_result = validate_yaml_frontmatter(skill_md)
        if yaml_result["valid"]:
            lines.append("- ✅ SKILL.md frontmatter is valid")
        else:
            lines.append(f"- ❌ SKILL.md frontmatter error: {yaml_result['error']}")

    lines.append("\n## Example Syntax\n")

    examples_md = SKILL_DIR / "examples.md"
    if examples_md.exists():
        syntax_result = check_example_syntax(examples_md)
        if syntax_result["valid"]:
            lines.append("- ✅ All code examples pass basic syntax checks")
        else:
            for issue in syntax_result["issues"]:
                lines.append(f"- ⚠️ {issue}")

    lines.append("\n## Link Validation\n")

    link_result = check_links()
    if link_result.get("all_valid"):
        lines.append("- ✅ All source links are accessible")
    elif link_result.get("urls"):
        for url, info in link_result["urls"].items():
            if info.get("valid"):
                lines.append(f"- ✅ {url}")
            else:
                lines.append(f"- ❌ {url}: {info.get('error', info.get('status'))}")

    lines.append("\n## Recommendations\n")

    if drift["status"] == "DRIFT DETECTED":
        lines.append("- 🔄 **UPDATE REQUIRED**: Source documentation has changed")
        lines.append("  - Review changes in the SDK repository")
        lines.append("  - Update skill files as needed")
        lines.append("  - Update LAST_UPDATED in this script")
    else:
        lines.append("- ✅ Skill is current with source documentation")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="GitHub Copilot SDK Skill Drift Detection")
    parser.add_argument("--check", action="store_true", help="Check for drift")
    parser.add_argument("--validate-yaml", action="store_true", help="Validate YAML frontmatter")
    parser.add_argument("--count-tokens", metavar="FILE", help="Count tokens in a file")
    parser.add_argument("--check-examples", metavar="FILE", help="Check example syntax")
    parser.add_argument("--check-links", action="store_true", help="Verify source links")
    parser.add_argument("--report", action="store_true", help="Generate full report")

    args = parser.parse_args()

    if args.check:
        result = check_drift()
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["status"] == "CURRENT" else 1)

    elif args.validate_yaml:
        result = validate_yaml_frontmatter(SKILL_DIR / "SKILL.md")
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["valid"] else 1)

    elif args.count_tokens:
        file_path = (
            SKILL_DIR / args.count_tokens
            if not os.path.isabs(args.count_tokens)
            else Path(args.count_tokens)
        )
        tokens = count_tokens(file_path)
        if tokens is not None:
            print(f"{file_path.name}: {tokens} tokens")
            budget_status = "UNDER" if tokens < TOKEN_BUDGET else "OVER"
            print(f"Budget ({TOKEN_BUDGET}): {budget_status}")
        else:
            print("Token counting unavailable (install tiktoken)")
        sys.exit(0)

    elif args.check_examples:
        file_path = (
            SKILL_DIR / args.check_examples
            if not os.path.isabs(args.check_examples)
            else Path(args.check_examples)
        )
        result = check_example_syntax(file_path)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["valid"] else 1)

    elif args.check_links:
        result = check_links()
        print(json.dumps(result, indent=2))
        sys.exit(0 if result.get("all_valid") else 1)

    elif args.report:
        print(generate_report())
        sys.exit(0)

    else:
        # Default: quick status check
        drift = check_drift()
        print(f"Drift Status: {drift['status']}")
        if drift["status"] == "DRIFT DETECTED":
            print("\nChanged sources:")
            for name, info in drift.get("sources", {}).items():
                if info.get("changed"):
                    print(f"  - {name}: {info['date']} - {info['message']}")
        sys.exit(0 if drift["status"] == "CURRENT" else 1)


if __name__ == "__main__":
    main()
