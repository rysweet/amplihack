#!/usr/bin/env python3
"""
Analyze Trace Logs

Analyze claude-trace JSONL logs to extract user prompt and response patterns.
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


class TraceLogAnalyzer:
    """Analyzes claude-trace JSONL logs for user patterns."""

    def __init__(self):
        """Initialize analyzer."""
        self.system_patterns = [
            "<system-reminder>",
            "SessionStart:",
            "Command: ",
            "<policy_spec>",
            "# Claude Code Code Bash",
            "Files modified by user:",
        ]
        self.system_messages = ["foo", "test", "ping", "hello", "quota"]

    def parse_jsonl_file(self, file_path: Path) -> list[dict[str, Any]]:
        """Parse a JSONL file and return list of conversation entries."""
        entries = []
        try:
            with open(file_path, encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        entries.append(entry)
                    except json.JSONDecodeError as e:
                        print(
                            f"  Warning: Skipping malformed JSON at line {line_num} in {file_path.name}: {e}",
                            file=sys.stderr,
                        )
                        continue
        except Exception as e:
            print(f"  Error reading {file_path.name}: {e}", file=sys.stderr)
        return entries

    def is_system_generated(self, message: str) -> bool:
        """Determine if a message is system-generated rather than user-input."""
        for pattern in self.system_patterns:
            if pattern in message:
                return True
        if message in self.system_messages:
            return True
        return False

    def extract_user_messages(self, entries: list[dict[str, Any]]) -> list[str]:
        """Extract user messages from conversation entries."""
        user_messages = []
        for entry in entries:
            try:
                # Handle claude-trace format: request.body.messages
                if "request" in entry and "body" in entry["request"]:
                    messages = entry["request"]["body"].get("messages", [])
                elif "request" in entry:
                    messages = entry.get("request", {}).get("messages", [])
                elif "messages" in entry:
                    messages = entry.get("messages", [])
                else:
                    continue

                for msg in messages:
                    if isinstance(msg, dict) and msg.get("role") == "user":
                        content = msg.get("content", "")
                        if isinstance(content, str) and content.strip():
                            if not self.is_system_generated(content):
                                user_messages.append(content.strip())
                        elif isinstance(content, list):
                            # Handle content blocks
                            text_parts = []
                            for block in content:
                                if isinstance(block, dict) and block.get("type") == "text":
                                    text_parts.append(block.get("text", ""))
                            if text_parts:
                                combined = " ".join(text_parts).strip()
                                if combined and not self.is_system_generated(combined):
                                    user_messages.append(combined)
            except Exception:
                # Skip malformed entries
                continue

        return user_messages

    def categorize_request(self, message: str) -> list[str]:
        """Categorize a user request into multiple categories."""
        message_lower = message.lower()
        categories = []

        # Command patterns
        if message.startswith("/"):
            categories.append("slash_command")

        # Development tasks
        if any(word in message_lower for word in ["fix", "debug", "error", "failing", "broken"]):
            categories.append("fix_debug")
        if any(word in message_lower for word in ["implement", "add", "create", "build"]):
            categories.append("implement")
        if any(word in message_lower for word in ["test", "testing", "pytest", "unittest"]):
            categories.append("testing")
        if any(word in message_lower for word in ["refactor", "improve", "optimize", "clean"]):
            categories.append("refactor")
        if any(word in message_lower for word in ["analyze", "review", "check", "examine"]):
            categories.append("analyze")
        if any(word in message_lower for word in ["document", "docs", "readme", "comment"]):
            categories.append("documentation")

        # CI/CD and workflow
        if any(word in message_lower for word in ["ci", "github actions", "workflow", "pipeline"]):
            categories.append("ci_cd")
        if any(word in message_lower for word in ["commit", "push", "pull request", "pr", "merge"]):
            categories.append("git_operations")

        # Communication patterns
        if message_lower.startswith(("yes", "no", "ok", "sure", "correct", "exactly")):
            categories.append("confirmation")
        if "?" in message:
            categories.append("question")

        # Decision making
        if any(
            word in message_lower for word in ["prefer", "choose", "option", "should we", "what if"]
        ):
            categories.append("decision_request")

        if not categories:
            categories.append("other")

        return categories

    def extract_key_phrases(
        self, messages: list[str], min_length: int = 10, max_length: int = 100
    ) -> Counter:
        """Extract common key phrases from messages."""
        phrases = []

        for msg in messages:
            # Extract sentences or phrases
            sentences = re.split(r"[.!?\n]+", msg)
            for sentence in sentences:
                sentence = sentence.strip()
                if min_length <= len(sentence) <= max_length:
                    # Normalize whitespace
                    sentence = " ".join(sentence.split())
                    phrases.append(sentence)

        return Counter(phrases)

    def extract_task_verbs(self, message: str) -> list[str]:
        """Extract action verbs from user messages."""
        verbs = []
        msg_lower = message.lower()

        verb_patterns = [
            "fix",
            "debug",
            "implement",
            "add",
            "create",
            "build",
            "test",
            "refactor",
            "improve",
            "optimize",
            "clean",
            "analyze",
            "review",
            "check",
            "examine",
            "document",
            "update",
            "remove",
            "delete",
            "merge",
            "commit",
            "push",
            "deploy",
            "run",
            "execute",
            "investigate",
            "explore",
            "research",
            "explain",
            "clarify",
            "validate",
            "verify",
        ]

        for verb in verb_patterns:
            if verb in msg_lower:
                verbs.append(verb)

        return verbs

    def identify_decision_patterns(self, messages: list[str]) -> dict[str, list[str]]:
        """Identify patterns in user decisions and preferences."""
        patterns = defaultdict(list)

        for msg in messages:
            msg_lower = msg.lower()

            # Skip very short messages
            if len(msg) < 5:
                continue

            # Completeness preference
            if any(
                phrase in msg_lower
                for phrase in [
                    "do it all",
                    "everything",
                    "complete",
                    "all files",
                    "full implementation",
                ]
            ):
                patterns["completeness_required"].append(msg[:200])
            elif any(phrase in msg_lower for phrase in ["minimal", "just", "only", "simple"]):
                patterns["minimal_scope"].append(msg[:200])

            # Autonomy preference
            if any(
                phrase in msg_lower
                for phrase in [
                    "autonomously",
                    "independently",
                    "don't ask",
                    "just do it",
                    "go ahead",
                ]
            ):
                patterns["high_autonomy"].append(msg[:200])
            elif any(
                phrase in msg_lower
                for phrase in ["ask me", "check with me", "confirm", "wait for approval"]
            ):
                patterns["low_autonomy"].append(msg[:200])

            # Merge/completion preferences
            if any(
                phrase in msg_lower
                for phrase in ["merge it", "merge the pr", "merge when", "auto-merge"]
            ):
                patterns["merge_instructions"].append(msg[:200])

            # Quality/thoroughness
            if any(
                phrase in msg_lower for phrase in ["make sure", "ensure", "verify", "double check"]
            ):
                patterns["quality_emphasis"].append(msg[:200])

            # Specific instructions
            if any(
                phrase in msg_lower for phrase in ["please", "can you", "could you", "would you"]
            ):
                patterns["polite_requests"].append(msg[:200])

        return patterns

    def analyze(self, log_dir: Path, sample_size: int = 15, options: dict = None) -> dict[str, Any]:
        """
        Analyze a sample of log files and extract patterns.

        Args:
            log_dir: Directory containing JSONL trace logs
            sample_size: Number of recent files to analyze
            options: Additional analysis options

        Returns:
            Analysis results with patterns and insights
        """
        options = options or {}

        # Get all JSONL files sorted by modification time (newest first)
        jsonl_files = sorted(
            [f for f in log_dir.glob("*.jsonl") if f.stat().st_size > 0],
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )

        print(f"Found {len(jsonl_files)} non-empty JSONL files")
        print(f"Sampling {min(sample_size, len(jsonl_files))} most recent files...\n")

        all_user_messages = []
        category_counter = Counter()
        file_stats = []

        for i, log_file in enumerate(jsonl_files[:sample_size], 1):
            print(f"Processing {i}/{min(sample_size, len(jsonl_files))}: {log_file.name}...")

            entries = self.parse_jsonl_file(log_file)
            user_messages = self.extract_user_messages(entries)

            file_stats.append(
                {
                    "file": log_file.name,
                    "total_entries": len(entries),
                    "user_messages": len(user_messages),
                    "size_mb": log_file.stat().st_size / (1024 * 1024),
                }
            )

            # Categorize each message
            for msg in user_messages:
                categories = self.categorize_request(msg)
                for cat in categories:
                    category_counter[cat] += 1

            all_user_messages.extend(user_messages)

        print(f"\nTotal user messages collected: {len(all_user_messages)}\n")

        # Analyze patterns
        decision_patterns = self.identify_decision_patterns(all_user_messages)
        key_phrases = self.extract_key_phrases(all_user_messages, min_length=15, max_length=150)

        # Extract task verbs
        all_verbs = []
        for msg in all_user_messages:
            all_verbs.extend(self.extract_task_verbs(msg))
        verb_counter = Counter(all_verbs)

        # Extract common short requests
        short_requests = [msg for msg in all_user_messages if len(msg) < 100]
        short_request_counter = Counter(short_requests)

        # Extract slash commands
        slash_commands = [msg for msg in all_user_messages if msg.startswith("/")]
        slash_command_counter = Counter(slash_commands)

        return {
            "file_stats": file_stats,
            "total_messages": len(all_user_messages),
            "categories": category_counter,
            "task_verbs": verb_counter,
            "top_short_requests": short_request_counter.most_common(30),
            "top_key_phrases": key_phrases.most_common(30),
            "slash_commands": slash_command_counter.most_common(20),
            "decision_patterns": decision_patterns,
            "sample_messages": {
                "all": all_user_messages[:50],
                "long": [msg for msg in all_user_messages if len(msg) > 300][:10],
                "short": short_requests[:30],
            },
        }

    def generate_report(self, analysis: dict[str, Any], output_path: Path):
        """Generate a comprehensive markdown report."""

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# Claude-Trace Log Analysis Report\n\n")
            f.write("## Executive Summary\n\n")
            f.write(f"- **Total Messages Analyzed**: {analysis['total_messages']}\n")
            f.write(f"- **Files Processed**: {len(analysis['file_stats'])}\n")
            f.write(f"- **Analysis Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # File statistics
            f.write("## File Statistics\n\n")
            f.write("| File | Entries | User Messages | Size (MB) |\n")
            f.write("|------|---------|---------------|----------|\n")
            for stat in analysis["file_stats"][:10]:
                f.write(
                    f"| {stat['file']} | {stat['total_entries']} | {stat['user_messages']} | {stat['size_mb']:.2f} |\n"
                )
            f.write("\n")

            # Request categories
            f.write("## Request Categories\n\n")
            f.write("Distribution of user request types:\n\n")
            for category, count in analysis["categories"].most_common():
                percentage = (count / analysis["total_messages"]) * 100
                f.write(f"- **{category}**: {count} ({percentage:.1f}%)\n")
            f.write("\n")

            # Task verbs
            f.write("## Most Common Task Verbs\n\n")
            f.write("Action verbs found in user requests:\n\n")
            for i, (verb, count) in enumerate(analysis["task_verbs"].most_common(20), 1):
                percentage = (count / analysis["total_messages"]) * 100
                f.write(f"{i}. **{verb}**: {count} times ({percentage:.1f}%)\n")
            f.write("\n")

            # Top slash commands
            f.write("## Top Slash Commands\n\n")
            if analysis["slash_commands"]:
                for i, (cmd, count) in enumerate(analysis["slash_commands"], 1):
                    f.write(f"{i}. `{cmd}` - {count} occurrences\n")
            else:
                f.write("No slash commands found in sample.\n")
            f.write("\n")

            # Top short requests
            f.write("## Top 20 Common User Requests\n\n")
            f.write("Most frequent short-form requests (< 100 characters):\n\n")
            for i, (request, count) in enumerate(analysis["top_short_requests"][:20], 1):
                request_escaped = request.replace("|", "\\|").replace("\n", " ")
                f.write(f'{i}. "{request_escaped}" - {count} times\n')
            f.write("\n")

            # Key phrases
            f.write("## Common Key Phrases\n\n")
            f.write("Frequently occurring phrases (15-150 characters):\n\n")
            for i, (phrase, count) in enumerate(analysis["top_key_phrases"][:20], 1):
                phrase_escaped = phrase.replace("|", "\\|").replace("\n", " ")
                if count > 1:
                    f.write(f'{i}. "{phrase_escaped}" - {count} times\n')
            f.write("\n")

            # Decision patterns
            f.write("## Decision Patterns\n\n")
            for pattern_type, examples in analysis["decision_patterns"].items():
                if examples:
                    f.write(f"### {pattern_type.replace('_', ' ').title()}\n\n")
                    f.write(f"Found {len(examples)} instances:\n\n")
                    for i, example in enumerate(examples[:5], 1):
                        example_escaped = example.replace("|", "\\|").replace("\n", " ")
                        f.write(f'{i}. "{example_escaped}"\n')
                    f.write("\n")

            # Workflow preferences
            f.write("## Workflow Preferences\n\n")

            completeness = len(analysis["decision_patterns"].get("completeness_required", []))
            minimal = len(analysis["decision_patterns"].get("minimal_scope", []))
            high_autonomy = len(analysis["decision_patterns"].get("high_autonomy", []))
            low_autonomy = len(analysis["decision_patterns"].get("low_autonomy", []))
            merge_instr = len(analysis["decision_patterns"].get("merge_instructions", []))
            quality = len(analysis["decision_patterns"].get("quality_emphasis", []))
            polite = len(analysis["decision_patterns"].get("polite_requests", []))

            f.write(f"- **Completeness required**: {completeness}\n")
            f.write(f"- **Minimal scope**: {minimal}\n")
            f.write(f"- **High autonomy requests**: {high_autonomy}\n")
            f.write(f"- **Low autonomy requests**: {low_autonomy}\n")
            f.write(f"- **Merge instructions given**: {merge_instr}\n")
            f.write(f"- **Quality emphasis**: {quality}\n")
            f.write(f"- **Polite requests**: {polite}\n\n")

            # Key insights
            f.write("## Key Insights\n\n")

            if completeness > minimal * 2:
                f.write(
                    "- User strongly emphasizes **completeness** - prefers 'do it all' over minimal solutions\n"
                )
            elif minimal > completeness * 2:
                f.write("- User prefers **minimal scope** - focused, targeted changes\n")

            if high_autonomy > low_autonomy * 2:
                f.write(
                    "- User strongly prefers **autonomous execution** without frequent check-ins\n"
                )
            elif low_autonomy > high_autonomy * 2:
                f.write("- User prefers **guided execution** with regular confirmation\n")

            if merge_instr > 10:
                f.write(
                    f"- User frequently provides **merge instructions** ({merge_instr} instances)\n"
                )

            if quality > 20:
                f.write(f"- User emphasizes **quality and verification** ({quality} instances)\n")

            fix_count = analysis["categories"].get("fix_debug", 0)
            implement_count = analysis["categories"].get("implement", 0)
            if fix_count > implement_count:
                f.write("- Primary focus is on **debugging and fixes** rather than new features\n")
            else:
                f.write("- Primary focus is on **implementing new features** and building\n")

            top_verbs = analysis["task_verbs"].most_common(3)
            if top_verbs:
                verb_str = ", ".join([f"'{v}'" for v, _ in top_verbs])
                f.write(f"- Most common action verbs: {verb_str}\n")

            f.write("\n")

            f.write("## Recommendations for PM Architect\n\n")
            f.write("Based on the analysis:\n\n")
            f.write(
                "1. **Autonomy Level**: Calibrate agent autonomy based on detected preference\n"
            )
            f.write("2. **Communication Style**: Match user's concise or detailed style\n")
            f.write(
                "3. **Scope Decisions**: Align with user's aggressive vs. conservative tendencies\n"
            )
            f.write("4. **Workflow Type**: Prefer parallel or sequential based on user patterns\n")
            f.write("5. **Task Focus**: Prioritize fix/debug vs. implementation based on usage\n")
            f.write("\n")


def main():
    """Main entry point for trace log analysis."""
    parser = argparse.ArgumentParser(
        description="Analyze claude-trace JSONL logs for user patterns"
    )
    parser.add_argument(
        "log_dir",
        nargs="?",
        default=None,
        help="Directory containing trace logs (default: .claude-trace in project root)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output file path (default: .claude/runtime/TRACE_LOG_ANALYSIS.md)",
    )
    parser.add_argument(
        "--sample-size",
        "-n",
        type=int,
        default=15,
        help="Number of recent files to analyze (default: 15)",
    )

    args = parser.parse_args()

    # Determine log directory
    if args.log_dir:
        log_dir = Path(args.log_dir).resolve()
    else:
        # Find project root and use .claude-trace
        project_root = Path(__file__).parent.parent.parent.parent
        log_dir = project_root / ".claude-trace"

    # Determine output path
    if args.output:
        output_path = Path(args.output).resolve()
    else:
        project_root = Path(__file__).parent.parent.parent.parent
        output_path = project_root / ".claude" / "runtime" / "TRACE_LOG_ANALYSIS.md"

    if not log_dir.exists():
        print(f"Error: Log directory not found: {log_dir}")
        return 1

    print("=" * 80)
    print("Claude-Trace Log Analysis")
    print("=" * 80)
    print()

    analyzer = TraceLogAnalyzer()
    analysis = analyzer.analyze(log_dir, sample_size=args.sample_size)

    print("=" * 80)
    print("Generating report...")
    print("=" * 80)
    print()

    analyzer.generate_report(analysis, output_path)

    print("Analysis complete!")
    print(f"Report saved to: {output_path}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
