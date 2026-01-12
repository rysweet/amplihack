"""CLI command fer memory backend evaluation.

Usage:
    amplihack memory evaluate               # Compare all backends
    amplihack memory evaluate --backend kuzu # Evaluate specific backend
    amplihack memory evaluate --output report.md # Save to file

Philosophy:
- Simple CLI: Easy to run evaluations
- Comprehensive: All three evaluation dimensions
- Actionable: Clear recommendations

Public API:
    main(): CLI entry point
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from .evaluation import run_evaluation

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    """CLI entry point fer memory evaluation."""
    parser = argparse.ArgumentParser(
        description="Evaluate memory backend quality and performance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compare all backends
  amplihack memory evaluate

  # Evaluate specific backend
  amplihack memory evaluate --backend sqlite

  # Save report to file
  amplihack memory evaluate --output report.md

  # Evaluate with custom database path
  amplihack memory evaluate --backend sqlite --db-path /tmp/memory.db
        """,
    )

    parser.add_argument(
        "--backend",
        choices=["sqlite", "kuzu", "neo4j"],
        help="Specific backend to evaluate (default: all)",
    )

    parser.add_argument("--output", "-o", type=str, help="Output file for report (default: stdout)")

    parser.add_argument("--db-path", type=str, help="Database path for backend (backend-specific)")

    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Build backend config
    backend_config = {}
    if args.db_path:
        backend_config["db_path"] = args.db_path

    # Run evaluation
    try:
        logger.info("Starting memory backend evaluation...")

        report = asyncio.run(run_evaluation(backend_type=args.backend, **backend_config))

        # Output report
        if args.output:
            output_path = Path(args.output)
            output_path.write_text(report)
            logger.info(f"Report saved to {output_path}")
        else:
            print("\n" + report)

        logger.info("Evaluation complete!")
        return 0

    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        if args.verbose:
            raise
        return 1


if __name__ == "__main__":
    sys.exit(main())
