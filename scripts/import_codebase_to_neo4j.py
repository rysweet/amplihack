#!/usr/bin/env python3
"""Import codebase to Neo4j via blarify code graph.

This script:
1. Runs blarify on the codebase to generate code graph
2. Imports the graph into Neo4j
3. Links code nodes to existing memories
4. Provides statistics on import

Usage:
    # Import entire codebase
    python scripts/import_codebase_to_neo4j.py

    # Import specific directory
    python scripts/import_codebase_to_neo4j.py --path ./src/amplihack/memory

    # Specify languages
    python scripts/import_codebase_to_neo4j.py --languages python,javascript

    # Use existing blarify output
    python scripts/import_codebase_to_neo4j.py --blarify-json /path/to/output.json

    # Incremental update (skip if no changes)
    python scripts/import_codebase_to_neo4j.py --incremental
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from amplihack.memory.neo4j.connector import Neo4jConnector
from amplihack.memory.neo4j.code_graph import BlarifyIntegration, run_blarify
from amplihack.memory.neo4j.schema import SchemaManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Import codebase to Neo4j via blarify",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=Path.cwd() / "src",
        help="Path to codebase to analyze (default: ./src)",
    )
    parser.add_argument(
        "--blarify-json",
        type=Path,
        help="Path to existing blarify JSON output (skip blarify run)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path.cwd() / ".amplihack" / "blarify_output.json",
        help="Path to save blarify output (default: .amplihack/blarify_output.json)",
    )
    parser.add_argument(
        "--languages",
        type=str,
        help="Comma-separated list of languages (e.g., python,javascript)",
    )
    parser.add_argument(
        "--project-id",
        type=str,
        help="Optional project ID to link code to",
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Incremental update (only changed files)",
    )
    parser.add_argument(
        "--skip-link",
        action="store_true",
        help="Skip linking code to memories",
    )
    parser.add_argument(
        "--neo4j-uri",
        type=str,
        help="Neo4j URI (default from config)",
    )
    parser.add_argument(
        "--neo4j-user",
        type=str,
        help="Neo4j username (default from config)",
    )
    parser.add_argument(
        "--neo4j-password",
        type=str,
        help="Neo4j password (default from config)",
    )

    args = parser.parse_args()

    # Determine blarify output path
    blarify_json_path = args.blarify_json or args.output

    # Step 1: Run blarify if needed
    if not args.blarify_json:
        logger.info("=" * 60)
        logger.info("Step 1: Running blarify on %s", args.path)
        logger.info("=" * 60)

        if not args.path.exists():
            logger.error("Path does not exist: %s", args.path)
            return 1

        # Ensure output directory exists
        args.output.parent.mkdir(parents=True, exist_ok=True)

        languages = args.languages.split(",") if args.languages else None

        success = run_blarify(args.path, args.output, languages)

        if not success:
            logger.error("Blarify failed. Exiting.")
            return 1

        logger.info("Blarify output saved to: %s", args.output)
    else:
        logger.info("Using existing blarify output: %s", args.blarify_json)

    # Step 2: Connect to Neo4j
    logger.info("=" * 60)
    logger.info("Step 2: Connecting to Neo4j")
    logger.info("=" * 60)

    try:
        conn_kwargs = {}
        if args.neo4j_uri:
            conn_kwargs["uri"] = args.neo4j_uri
        if args.neo4j_user:
            conn_kwargs["user"] = args.neo4j_user
        if args.neo4j_password:
            conn_kwargs["password"] = args.neo4j_password

        with Neo4jConnector(**conn_kwargs) as conn:
            # Verify connectivity
            if not conn.verify_connectivity():
                logger.error("Cannot connect to Neo4j")
                return 1

            logger.info("Connected to Neo4j successfully")

            # Step 3: Initialize schema
            logger.info("=" * 60)
            logger.info("Step 3: Initializing code graph schema")
            logger.info("=" * 60)

            integration = BlarifyIntegration(conn)

            if not integration.initialize_code_schema():
                logger.error("Schema initialization failed")
                return 1

            logger.info("Schema initialized successfully")

            # Step 4: Import blarify output
            logger.info("=" * 60)
            logger.info("Step 4: Importing blarify output to Neo4j")
            logger.info("=" * 60)

            if args.incremental:
                counts = integration.incremental_update(blarify_json_path, args.project_id)
            else:
                counts = integration.import_blarify_output(blarify_json_path, args.project_id)

            logger.info("Import complete:")
            logger.info("  - Files:         %d", counts["files"])
            logger.info("  - Classes:       %d", counts["classes"])
            logger.info("  - Functions:     %d", counts["functions"])
            logger.info("  - Imports:       %d", counts["imports"])
            logger.info("  - Relationships: %d", counts["relationships"])

            # Step 5: Link code to memories
            if not args.skip_link:
                logger.info("=" * 60)
                logger.info("Step 5: Linking code to memories")
                logger.info("=" * 60)

                link_count = integration.link_code_to_memories(args.project_id)
                logger.info("Created %d code-memory relationships", link_count)

            # Step 6: Display statistics
            logger.info("=" * 60)
            logger.info("Step 6: Code graph statistics")
            logger.info("=" * 60)

            stats = integration.get_code_stats(args.project_id)
            logger.info("Code graph statistics:")
            logger.info("  - Total files:     %d", stats["file_count"])
            logger.info("  - Total classes:   %d", stats["class_count"])
            logger.info("  - Total functions: %d", stats["function_count"])
            logger.info("  - Total lines:     %d", stats["total_lines"])

            logger.info("=" * 60)
            logger.info("Import complete! Code graph integrated with Neo4j memory system.")
            logger.info("=" * 60)

    except Exception as e:
        logger.error("Import failed: %s", e, exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
