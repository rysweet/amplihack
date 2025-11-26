#!/usr/bin/env python3
"""CLI tool to import markdown documentation into Neo4j knowledge graph.

Usage:
    python scripts/import_docs_to_neo4j.py [OPTIONS] PATHS...

Examples:
    # Import all docs from docs/ directory
    python scripts/import_docs_to_neo4j.py docs/

    # Import specific directories
    python scripts/import_docs_to_neo4j.py docs/ .claude/context/

    # Import with project ID
    python scripts/import_docs_to_neo4j.py --project my-project docs/

    # Import and link to code
    python scripts/import_docs_to_neo4j.py --link-code docs/

    # Dry run to see what would be imported
    python scripts/import_docs_to_neo4j.py --dry-run docs/
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from amplihack.memory.neo4j import (
    Neo4jConnector,
    ensure_neo4j_running,
    get_config,
)
from amplihack.memory.neo4j.doc_graph import DocGraphIntegration


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def find_markdown_files(paths: list[Path], recursive: bool = True) -> list[Path]:
    """Find all markdown files in given paths.

    Args:
        paths: List of file or directory paths
        recursive: Whether to search recursively

    Returns:
        List of markdown file paths
    """
    markdown_files = []

    for path in paths:
        if path.is_file():
            if path.suffix.lower() in [".md", ".markdown"]:
                markdown_files.append(path)
        elif path.is_dir():
            pattern = "**/*.md" if recursive else "*.md"
            markdown_files.extend(path.glob(pattern))

    return sorted(markdown_files)


def import_documentation(
    file_paths: list[Path],
    project_id: str = None,
    link_code: bool = False,
    link_memory: bool = False,
    dry_run: bool = False,
) -> dict:
    """Import documentation files into Neo4j.

    Args:
        file_paths: List of markdown files to import
        project_id: Optional project ID
        link_code: Whether to link docs to code
        link_memory: Whether to link docs to memories
        dry_run: If True, show what would be imported without importing

    Returns:
        Dictionary with import statistics
    """
    logger = logging.getLogger(__name__)

    if dry_run:
        logger.info("DRY RUN - No changes will be made")
        for file_path in file_paths:
            logger.info("Would import: %s", file_path)
        return {
            "dry_run": True,
            "files_found": len(file_paths),
        }

    # Ensure Neo4j is running
    logger.info("Ensuring Neo4j is running...")
    if not ensure_neo4j_running(blocking=True):
        logger.error("Failed to start Neo4j")
        return {"error": "Neo4j not available"}

    # Connect to Neo4j
    config = get_config()
    connector = Neo4jConnector(
        uri=config.uri,
        auth=(config.username, config.password),
    )

    if not connector.connect():
        logger.error("Failed to connect to Neo4j")
        return {"error": "Connection failed"}

    try:
        # Initialize documentation graph integration
        doc_integration = DocGraphIntegration(connector)

        # Initialize schema
        logger.info("Initializing documentation schema...")
        if not doc_integration.initialize_doc_schema():
            logger.error("Failed to initialize schema")
            return {"error": "Schema initialization failed"}

        # Import all files
        total_stats = {
            "files_imported": 0,
            "doc_files": 0,
            "sections": 0,
            "concepts": 0,
            "code_refs": 0,
            "errors": 0,
        }

        for file_path in file_paths:
            logger.info("Importing: %s", file_path)

            try:
                stats = doc_integration.import_documentation(
                    file_path=file_path,
                    project_id=project_id,
                )

                total_stats["files_imported"] += 1
                total_stats["doc_files"] += stats.get("doc_files", 0)
                total_stats["sections"] += stats.get("sections", 0)
                total_stats["concepts"] += stats.get("concepts", 0)
                total_stats["code_refs"] += stats.get("code_refs", 0)

                logger.info("Imported successfully: %s", stats)

            except Exception as e:
                logger.error("Failed to import %s: %s", file_path, e)
                total_stats["errors"] += 1

        # Link to code if requested
        if link_code:
            logger.info("Linking documentation to code...")
            code_links = doc_integration.link_docs_to_code(project_id)
            total_stats["code_links"] = code_links
            logger.info("Created %d doc-code links", code_links)

        # Link to memories if requested
        if link_memory:
            logger.info("Linking documentation to memories...")
            memory_links = doc_integration.link_docs_to_memories(project_id)
            total_stats["memory_links"] = memory_links
            logger.info("Created %d doc-memory links", memory_links)

        # Get final stats
        doc_stats = doc_integration.get_doc_stats(project_id)
        total_stats["total_docs"] = doc_stats["doc_count"]
        total_stats["total_concepts"] = doc_stats["concept_count"]
        total_stats["total_sections"] = doc_stats["section_count"]

        return total_stats

    finally:
        connector.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Import markdown documentation into Neo4j knowledge graph",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="Paths to markdown files or directories",
    )

    parser.add_argument(
        "--project",
        "-p",
        type=str,
        help="Project ID to associate documentation with",
    )

    parser.add_argument(
        "--link-code",
        action="store_true",
        help="Link documentation to code nodes",
    )

    parser.add_argument(
        "--link-memory",
        action="store_true",
        help="Link documentation to memory nodes",
    )

    parser.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        default=True,
        help="Search directories recursively (default: True)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be imported without importing",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Find markdown files
    logger.info("Finding markdown files...")
    markdown_files = find_markdown_files(args.paths, args.recursive)

    if not markdown_files:
        logger.error("No markdown files found in: %s", args.paths)
        return 1

    logger.info("Found %d markdown files", len(markdown_files))

    # Import documentation
    stats = import_documentation(
        file_paths=markdown_files,
        project_id=args.project,
        link_code=args.link_code,
        link_memory=args.link_memory,
        dry_run=args.dry_run,
    )

    # Print summary
    print("\n" + "=" * 60)
    print("DOCUMENTATION IMPORT SUMMARY")
    print("=" * 60)

    if stats.get("error"):
        print(f"ERROR: {stats['error']}")
        return 1

    if stats.get("dry_run"):
        print(f"Files found: {stats['files_found']}")
        print("\nThis was a dry run. Use without --dry-run to import.")
        return 0

    print(f"Files processed: {stats['files_imported']}")
    print(f"Errors: {stats['errors']}")
    print("\nNodes created:")
    print(f"  DocFiles: {stats['doc_files']}")
    print(f"  Sections: {stats['sections']}")
    print(f"  Concepts: {stats['concepts']}")
    print(f"  Code references: {stats['code_refs']}")

    if "code_links" in stats:
        print(f"\nDoc-Code links: {stats['code_links']}")

    if "memory_links" in stats:
        print(f"Doc-Memory links: {stats['memory_links']}")

    print("\nFinal graph stats:")
    print(f"  Total documents: {stats.get('total_docs', 0)}")
    print(f"  Total concepts: {stats.get('total_concepts', 0)}")
    print(f"  Total sections: {stats.get('total_sections', 0)}")

    print("=" * 60)

    return 0 if stats["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
