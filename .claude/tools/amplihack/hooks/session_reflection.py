#!/usr/bin/env python3
"""
Session Reflection Orchestrator

Coordinates end-of-session reflection analysis, user approval workflow,
and GitHub issue creation for improvement opportunities.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Clean import structure
sys.path.insert(0, str(Path(__file__).parent))

# Import SessionReflector and utilities from the hooks directory
try:
    from reflection import SessionReflector, find_claude_trace_logs
except ImportError:
    raise ImportError("SessionReflector not found in hooks directory")

# Import GitHub issue creator
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
try:
    from github_issue import create_issue
except ImportError:
    raise ImportError("github_issue module not found")


class ReflectionOrchestrator:
    """Orchestrates session reflection analysis and GitHub issue creation."""

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize orchestrator with project root.

        Args:
            project_root: Project root directory. Auto-detected if not provided.
        """
        if project_root is None:
            project_root = self._find_project_root()

        self.project_root = project_root
        self.runtime_dir = project_root / ".claude" / "runtime"
        self.logs_dir = self.runtime_dir / "logs"
        self.reflection_dir = self.runtime_dir / "reflection"

        # Ensure directories exist
        self.reflection_dir.mkdir(parents=True, exist_ok=True)

        # Initialize reflector
        self.reflector = SessionReflector()

    def _find_project_root(self) -> Path:
        """Find project root by looking for .claude directory."""
        current = Path(__file__).resolve().parent
        for _ in range(10):  # Max 10 levels up
            if (current / ".claude").exists():
                return current
            if current == current.parent:
                break
            current = current.parent

        raise ValueError("Could not find project root with .claude directory")

    def analyze_session(self, session_id: str) -> Dict[str, Any]:
        """Analyze a session using SessionReflector.

        Args:
            session_id: Session identifier or path to session log directory

        Returns:
            Analysis results from SessionReflector

        Raises:
            FileNotFoundError: If session log not found
            ValueError: If session data is invalid
        """
        # Find session directory
        session_dir = self._resolve_session_dir(session_id)
        if not session_dir.exists():
            raise FileNotFoundError(f"Session directory not found: {session_dir}")

        # Load session messages
        messages = self._load_session_messages(session_dir)
        if not messages:
            raise ValueError(f"No messages found in session: {session_id}")

        # Find claude-trace logs
        trace_logs = find_claude_trace_logs(session_dir, self.project_root)

        # Run reflection analysis with trace logs
        findings = self.reflector.analyze_session(messages, trace_logs=trace_logs)

        return findings

    def _resolve_session_dir(self, session_id: str) -> Path:
        """Resolve session directory from ID or path.

        Args:
            session_id: Session ID (e.g., '20251020_153045') or full path

        Returns:
            Path to session directory
        """
        # Check if it's already a path
        session_path = Path(session_id)
        if session_path.is_absolute() and session_path.exists():
            return session_path

        # Try as session ID under logs directory
        session_dir = self.logs_dir / session_id
        if session_dir.exists():
            return session_dir

        # Try with common prefixes
        for candidate in self.logs_dir.glob(f"*{session_id}*"):
            if candidate.is_dir():
                return candidate

        # Return the expected path even if it doesn't exist yet
        return session_dir

    def _load_session_messages(self, session_dir: Path) -> List[Dict]:
        """Load session messages from various possible formats.

        Args:
            session_dir: Path to session log directory

        Returns:
            List of message dictionaries
        """
        messages = []

        # Try common file names
        for filename in ["messages.json", "session.json", "DECISIONS.md", "analysis.json"]:
            file_path = session_dir / filename
            if not file_path.exists():
                continue

            if filename.endswith(".json"):
                try:
                    with open(file_path) as f:
                        data = json.load(f)

                    # Handle different data structures
                    if isinstance(data, list):
                        messages.extend(data)
                    elif isinstance(data, dict):
                        if "messages" in data:
                            messages.extend(data["messages"])
                        elif "content" in data:
                            messages.append(data)
                        else:
                            # Create a synthetic message from the data
                            messages.append({"role": "system", "content": json.dumps(data)})

                except (OSError, json.JSONDecodeError) as e:
                    print(f"Warning: Could not parse {filename}: {e}", file=sys.stderr)
                    continue

            elif filename.endswith(".md"):
                try:
                    with open(file_path) as f:
                        content = f.read()
                    # Create a message from markdown content
                    messages.append({"role": "assistant", "content": content})
                except OSError as e:
                    print(f"Warning: Could not read {filename}: {e}", file=sys.stderr)
                    continue

        return messages

    def present_findings(self, findings: Dict[str, Any]) -> None:
        """Present findings to user in a clear, formatted way.

        Args:
            findings: Analysis results from SessionReflector
        """
        print("\n" + "=" * 70)
        print("SESSION REFLECTION ANALYSIS")
        print("=" * 70)

        # Skip message if reflection was disabled
        if findings.get("skipped"):
            print(f"\nReflection skipped: {findings.get('reason', 'unknown')}")
            return

        # Show metrics
        metrics = findings.get("metrics", {})
        print("\nSession Metrics:")
        print(f"  Total messages: {metrics.get('total_messages', 0)}")
        print(f"  Tool uses: {metrics.get('tool_uses', 0)}")

        # Show claude-trace analysis if present
        trace_analysis = findings.get("trace_analysis")
        if trace_analysis:
            print("\nClaude-Trace Analysis:")
            token_usage = trace_analysis.get("token_usage", {})
            if token_usage.get("total_input") or token_usage.get("total_output"):
                print(
                    f"  Token usage: {token_usage.get('total_input', 0)} input, {token_usage.get('total_output', 0)} output"
                )
            if trace_analysis.get("api_errors"):
                print(f"  API errors: {len(trace_analysis['api_errors'])}")
            if trace_analysis.get("rate_limits"):
                print(f"  Rate limit hits: {len(trace_analysis['rate_limits'])}")
            if trace_analysis.get("slow_requests"):
                print(f"  Slow requests (>30s): {len(trace_analysis['slow_requests'])}")

        # Show patterns found
        patterns = findings.get("patterns", [])
        print(f"\nPatterns Detected: {len(patterns)}")

        for i, pattern in enumerate(patterns, 1):
            print(f"\n  {i}. {pattern['type'].upper()}")
            if "suggestion" in pattern:
                print(f"     → {pattern['suggestion']}")
            # Show pattern-specific details
            for key, value in pattern.items():
                if key not in ["type", "suggestion"]:
                    print(f"     {key}: {value}")

        # Show suggestions
        suggestions = findings.get("suggestions", [])
        if suggestions:
            print("\nSuggestions:")
            for i, suggestion in enumerate(suggestions, 1):
                print(f"  {i}. {suggestion}")

        print("\n" + "=" * 70 + "\n")

    def get_user_approval(self, suggestions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get user approval for creating GitHub issues.

        Args:
            suggestions: List of pattern dictionaries with suggestions

        Returns:
            List of approved suggestions to create issues for
        """
        if not suggestions:
            return []

        print("\nCreate GitHub issues for these improvements? (y/n/select)")
        print("  y - Create issues for all suggestions")
        print("  n - Skip issue creation")
        print("  select - Choose specific suggestions")
        print()

        try:
            response = input("Your choice: ").strip().lower()

            if response == "y":
                return suggestions

            if response == "n":
                return []

            if response == "select":
                approved = []
                for i, suggestion in enumerate(suggestions, 1):
                    print(f"\n{i}. {suggestion.get('type', 'unknown').upper()}")
                    print(f"   {suggestion.get('suggestion', 'No suggestion')}")
                    choice = input("   Create issue? (y/n): ").strip().lower()
                    if choice == "y":
                        approved.append(suggestion)

                return approved

            print("Invalid choice. Skipping issue creation.")
            return []

        except (KeyboardInterrupt, EOFError):
            print("\n\nInterrupted. Skipping issue creation.")
            return []

    def create_github_issues(self, approved: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create GitHub issues for approved suggestions.

        Args:
            approved: List of approved pattern dictionaries

        Returns:
            List of created issue results
        """
        from .reflection_issue_template import generate_issue

        created_issues = []

        for pattern in approved:
            try:
                # Generate issue content
                issue_data = generate_issue(pattern, session_id="current")

                # Create the issue
                result = create_issue(
                    title=issue_data["title"],
                    body=issue_data["body"],
                    labels=issue_data.get("labels", []),
                )

                if result.get("success"):
                    print(f"✓ Created issue #{result['issue_number']}: {issue_data['title']}")
                    created_issues.append(
                        {
                            "pattern": pattern,
                            "issue_number": result["issue_number"],
                            "issue_url": result["issue_url"],
                        }
                    )
                else:
                    print(f"✗ Failed to create issue: {result.get('error')}")

            except Exception as e:
                print(f"✗ Error creating issue for {pattern.get('type')}: {e}")
                continue

        return created_issues

    def save_reflection_summary(self, session_id: str, results: Dict[str, Any]) -> Path:
        """Save reflection summary to session log directory.

        Args:
            session_id: Session identifier
            results: Complete reflection results including findings and created issues

        Returns:
            Path to saved summary file
        """
        session_dir = self._resolve_session_dir(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)

        summary_file = session_dir / "reflection_summary.json"

        with open(summary_file, "w") as f:
            json.dump(results, f, indent=2)

        print(f"\n✓ Reflection summary saved to: {summary_file}")

        return summary_file

    def run_reflection(self, session_id: str, auto_create_issues: bool = False) -> Dict[str, Any]:
        """Run complete reflection workflow.

        Args:
            session_id: Session identifier
            auto_create_issues: If True, create issues without user approval

        Returns:
            Complete reflection results
        """
        results = {"session_id": session_id, "findings": None, "issues_created": []}

        try:
            # Step 1: Analyze session
            print(f"\nAnalyzing session: {session_id}")
            findings = self.analyze_session(session_id)
            results["findings"] = findings

            # Step 2: Present findings
            self.present_findings(findings)

            # Skip if no patterns found
            patterns = findings.get("patterns", [])
            if not patterns:
                print("No improvement patterns detected.")
                return results

            # Step 3: Get approval (unless auto mode)
            if auto_create_issues:
                approved = patterns
            else:
                approved = self.get_user_approval(patterns)

            if not approved:
                print("No issues will be created.")
                return results

            # Step 4: Create GitHub issues
            print(f"\nCreating {len(approved)} GitHub issue(s)...")
            created_issues = self.create_github_issues(approved)
            results["issues_created"] = created_issues

            # Step 5: Save summary
            self.save_reflection_summary(session_id, results)

            return results

        except Exception as e:
            print(f"Error during reflection: {e}", file=sys.stderr)
            results["error"] = str(e)
            return results


def main():
    """CLI interface for testing reflection orchestrator."""
    import argparse

    parser = argparse.ArgumentParser(description="Run session reflection analysis")
    parser.add_argument("session_id", help="Session ID or path to session directory")
    parser.add_argument(
        "--auto", action="store_true", help="Automatically create issues without approval"
    )

    args = parser.parse_args()

    orchestrator = ReflectionOrchestrator()
    results = orchestrator.run_reflection(args.session_id, auto_create_issues=args.auto)

    # Exit with appropriate code
    if results.get("error"):
        sys.exit(1)

    if results.get("issues_created"):
        print(f"\n✓ Created {len(results['issues_created'])} issue(s)")
        sys.exit(0)

    print("\n✓ Reflection complete (no issues created)")
    sys.exit(0)


if __name__ == "__main__":
    main()
