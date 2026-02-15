#!/usr/bin/env python3
"""
Documentation Analyzer CLI

Simple command-line interface for testing the agent.
"""

import argparse
import sys
import time
from pathlib import Path

from agent import DocumentationAnalyzer
from metrics import MetricsTracker
from mslearn_fetcher import MSLearnFetcher, get_sample_markdown


def analyze_file(filepath: str, analyzer: DocumentationAnalyzer, tracker: MetricsTracker):
    """Analyze a local markdown file."""
    path = Path(filepath)
    if not path.exists():
        print(f"Error: File not found: {filepath}")
        return

    content = path.read_text()
    url = f"file://{path.absolute()}"

    print(f"\nAnalyzing: {filepath}")
    start = time.time()
    result = analyzer.analyze_document(content, url=url)
    runtime = (time.time() - start) * 1000

    print_results(result)

    tracker.record_analysis(
        url=url,
        structure_score=result.structure_score,
        completeness_score=result.completeness_score,
        clarity_score=result.clarity_score,
        overall_score=result.overall_score,
        pattern_matches=sum(result.pattern_matches.values()),
        runtime_ms=runtime,
    )
    print(f"\nAnalysis completed in {runtime:.1f}ms")


def analyze_url(url: str, analyzer: DocumentationAnalyzer, tracker: MetricsTracker):
    """Analyze a remote URL."""
    fetcher = MSLearnFetcher()

    print(f"\nFetching: {url}")
    content = fetcher.fetch_document(url)

    if not content:
        print("Error: Could not fetch document")
        return

    print("Analyzing...")
    start = time.time()
    result = analyzer.analyze_document(content, url=url)
    runtime = (time.time() - start) * 1000

    print_results(result)

    tracker.record_analysis(
        url=url,
        structure_score=result.structure_score,
        completeness_score=result.completeness_score,
        clarity_score=result.clarity_score,
        overall_score=result.overall_score,
        pattern_matches=sum(result.pattern_matches.values()),
        runtime_ms=runtime,
    )
    print(f"\nAnalysis completed in {runtime:.1f}ms")


def analyze_sample(analyzer: DocumentationAnalyzer, tracker: MetricsTracker):
    """Analyze the built-in sample document."""
    content = get_sample_markdown()

    print("\nAnalyzing sample MS Learn document...")
    start = time.time()
    result = analyzer.analyze_document(content, url="sample://azure-architecture")
    runtime = (time.time() - start) * 1000

    print_results(result)

    tracker.record_analysis(
        url="sample://azure-architecture",
        structure_score=result.structure_score,
        completeness_score=result.completeness_score,
        clarity_score=result.clarity_score,
        overall_score=result.overall_score,
        pattern_matches=sum(result.pattern_matches.values()),
        runtime_ms=runtime,
    )
    print(f"\nAnalysis completed in {runtime:.1f}ms")


def print_results(result):
    """Print analysis results."""
    print(f"\n{'=' * 60}")
    print("ANALYSIS RESULTS")
    print(f"{'=' * 60}")
    print(f"\nDocument: {result.title}")
    print(f"URL: {result.url}")

    print(f"\n{'─' * 60}")
    print("QUALITY SCORES")
    print(f"{'─' * 60}")
    print(
        f"  Overall:      {result.overall_score:>5.1f}/100  {'█' * int(result.overall_score / 5)}"
    )
    print(
        f"  Structure:    {result.structure_score:>5.1f}/100  {'█' * int(result.structure_score / 5)}"
    )
    print(
        f"  Completeness: {result.completeness_score:>5.1f}/100  {'█' * int(result.completeness_score / 5)}"
    )
    print(
        f"  Clarity:      {result.clarity_score:>5.1f}/100  {'█' * int(result.clarity_score / 5)}"
    )

    print(f"\n{'─' * 60}")
    print("DOCUMENT STRUCTURE")
    print(f"{'─' * 60}")
    print(f"  Sections:        {result.section_count}")
    print(f"  Max Depth:       {result.max_depth}")
    print(f"  Total Words:     {result.total_words}")
    print(f"  Code Examples:   {result.code_examples_count}")
    print(f"  Links:           {result.links_count}")

    print(f"\n{'─' * 60}")
    print("PATTERNS DETECTED")
    print(f"{'─' * 60}")
    for pattern, matched in result.pattern_matches.items():
        status = "✓" if matched else "✗"
        print(f"  {status} {pattern.replace('_', ' ').title()}")

    if result.learned_insights:
        print(f"\n{'─' * 60}")
        print("LEARNED INSIGHTS")
        print(f"{'─' * 60}")
        for insight in result.learned_insights:
            print(f"  • {insight}")

    print(f"\n{'=' * 60}\n")


def show_stats(analyzer: DocumentationAnalyzer, tracker: MetricsTracker):
    """Show learning statistics."""
    print(f"\n{'=' * 60}")
    print("LEARNING STATISTICS")
    print(f"{'=' * 60}")

    # From agent memory
    agent_stats = analyzer.get_learning_stats()
    print("\nAgent Memory:")
    print(f"  Total Analyses: {agent_stats.get('total_analyses', 0)}")
    print(f"  Average Quality: {agent_stats.get('avg_quality', 0):.1f}/100")
    print(f"  Trend: {agent_stats.get('trend', 'unknown').upper()}")
    if "improvement" in agent_stats:
        print(f"  Improvement: {agent_stats['improvement']:+.1f} points")

    # From tracker
    progress = tracker.get_learning_progress()
    if progress:
        print("\nCurrent Session:")
        print(f"  Analyses: {progress.total_analyses}")
        print(f"  First Score: {progress.first_analysis_score:.1f}")
        print(f"  Latest Score: {progress.latest_analysis_score:.1f}")
        print(
            f"  Improvement: {progress.score_improvement:+.1f} ({progress.improvement_rate:+.1f}%)"
        )
        print(f"  Trend: {progress.trend.upper()}")

        if tracker.demonstrate_learning():
            print("\n  ✓ AGENT DEMONSTRATES MEASURABLE LEARNING (>=15% improvement)")
    else:
        print("\n  No analyses in current session")

    print(f"\n{'=' * 60}\n")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Documentation Analyzer - Learning agent for analyzing documentation quality",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze sample document
  python cli.py --sample

  # Analyze local file
  python cli.py --file README.md

  # Analyze remote URL
  python cli.py --url https://learn.microsoft.com/en-us/azure/architecture/guide/

  # Analyze multiple files and show learning
  python cli.py --file doc1.md --file doc2.md --file doc3.md --stats

  # Show learning statistics
  python cli.py --stats
        """,
    )

    parser.add_argument("--file", "-f", action="append", help="Analyze local markdown file")
    parser.add_argument("--url", "-u", action="append", help="Analyze remote URL")
    parser.add_argument("--sample", "-s", action="store_true", help="Analyze built-in sample")
    parser.add_argument("--stats", action="store_true", help="Show learning statistics")
    parser.add_argument("--export", "-e", help="Export metrics to JSON file")

    args = parser.parse_args()

    if not (args.file or args.url or args.sample or args.stats):
        parser.print_help()
        return 1

    # Initialize agent and tracker
    analyzer = DocumentationAnalyzer()
    tracker = MetricsTracker()

    try:
        # Analyze files
        if args.file:
            for filepath in args.file:
                analyze_file(filepath, analyzer, tracker)

        # Analyze URLs
        if args.url:
            for url in args.url:
                analyze_url(url, analyzer, tracker)

        # Analyze sample
        if args.sample:
            analyze_sample(analyzer, tracker)

        # Show statistics
        if args.stats:
            show_stats(analyzer, tracker)

        # Export metrics
        if args.export:
            tracker.export_metrics(args.export)
            print(f"Metrics exported to: {args.export}")

        return 0

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 130
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
