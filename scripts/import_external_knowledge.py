#!/usr/bin/env python3
"""CLI tool for importing external knowledge into Neo4j memory system.

Supports importing:
- Python official documentation
- MS Learn content
- Library documentation
- GitHub examples

Usage:
    # Import Python 3.10 docs
    python scripts/import_external_knowledge.py python --version 3.10

    # Import MS Learn articles
    python scripts/import_external_knowledge.py ms-learn --topic azure

    # Import library docs
    python scripts/import_external_knowledge.py library --name requests

    # Import from custom URL
    python scripts/import_external_knowledge.py custom --url https://example.com/docs
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from amplihack.memory.neo4j import (
    Neo4jConnector,
    ExternalKnowledgeManager,
    KnowledgeSource,
    ensure_neo4j_running,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Well-known documentation URLs
PYTHON_DOCS_URLS = {
    "3.10": "https://docs.python.org/3.10/",
    "3.11": "https://docs.python.org/3.11/",
    "3.12": "https://docs.python.org/3.12/",
    "latest": "https://docs.python.org/3/",
}

MS_LEARN_BASE = "https://learn.microsoft.com/en-us/"

LIBRARY_DOCS = {
    "requests": "https://requests.readthedocs.io/en/latest/",
    "flask": "https://flask.palletsprojects.com/",
    "django": "https://docs.djangoproject.com/",
    "fastapi": "https://fastapi.tiangolo.com/",
    "numpy": "https://numpy.org/doc/stable/",
    "pandas": "https://pandas.pydata.org/docs/",
    "pytest": "https://docs.pytest.org/",
    "sqlalchemy": "https://docs.sqlalchemy.org/",
}


def import_python_docs(
    manager: ExternalKnowledgeManager,
    version: str = "latest",
    pages: Optional[List[str]] = None,
) -> int:
    """Import Python official documentation.

    Args:
        manager: External knowledge manager
        version: Python version (3.10, 3.11, 3.12, latest)
        pages: Specific pages to import (None = import common pages)

    Returns:
        Number of documents imported
    """
    logger.info("Importing Python %s documentation", version)

    base_url = PYTHON_DOCS_URLS.get(version, PYTHON_DOCS_URLS["latest"])

    # Default important pages
    if pages is None:
        pages = [
            "library/index.html",
            "library/functions.html",
            "library/stdtypes.html",
            "library/exceptions.html",
            "reference/datamodel.html",
            "tutorial/index.html",
        ]

    count = 0

    for page in pages:
        url = f"{base_url}{page}"

        doc = manager.fetch_api_docs(
            url=url,
            source=KnowledgeSource.PYTHON_DOCS,
            version=version,
            trust_score=0.95,  # Official docs = high trust
        )

        if doc:
            if manager.cache_external_doc(doc):
                logger.info("Imported: %s", url)
                count += 1
            else:
                logger.error("Failed to cache: %s", url)
        else:
            logger.error("Failed to fetch: %s", url)

    logger.info("Imported %d Python docs", count)
    return count


def import_ms_learn(
    manager: ExternalKnowledgeManager,
    topic: str,
    articles: Optional[List[str]] = None,
) -> int:
    """Import MS Learn content.

    Args:
        manager: External knowledge manager
        topic: Topic area (azure, dotnet, python, etc.)
        articles: Specific article paths (None = import topic overview)

    Returns:
        Number of documents imported
    """
    logger.info("Importing MS Learn content: %s", topic)

    base_url = f"{MS_LEARN_BASE}{topic}/"

    # Default to overview if no specific articles
    if articles is None:
        articles = [""]

    count = 0

    for article in articles:
        url = f"{base_url}{article}"

        doc = manager.fetch_api_docs(
            url=url,
            source=KnowledgeSource.MS_LEARN,
            version="latest",
            trust_score=0.9,  # MS Learn = high trust
        )

        if doc:
            if manager.cache_external_doc(doc):
                logger.info("Imported: %s", url)
                count += 1
            else:
                logger.error("Failed to cache: %s", url)
        else:
            logger.error("Failed to fetch: %s", url)

    logger.info("Imported %d MS Learn docs", count)
    return count


def import_library_docs(
    manager: ExternalKnowledgeManager,
    library_name: str,
    pages: Optional[List[str]] = None,
) -> int:
    """Import library documentation.

    Args:
        manager: External knowledge manager
        library_name: Library name (requests, flask, etc.)
        pages: Specific pages to import (None = import main page)

    Returns:
        Number of documents imported
    """
    logger.info("Importing %s documentation", library_name)

    base_url = LIBRARY_DOCS.get(library_name.lower())

    if not base_url:
        logger.error("Unknown library: %s", library_name)
        logger.info("Known libraries: %s", ", ".join(LIBRARY_DOCS.keys()))
        return 0

    # Default to main page if no specific pages
    if pages is None:
        pages = [""]

    count = 0

    for page in pages:
        url = f"{base_url}{page}".rstrip("/")

        doc = manager.fetch_api_docs(
            url=url,
            source=KnowledgeSource.LIBRARY_DOCS,
            version="latest",
            trust_score=0.85,  # Library docs = good trust
        )

        if doc:
            if manager.cache_external_doc(doc):
                logger.info("Imported: %s", url)
                count += 1
            else:
                logger.error("Failed to cache: %s", url)
        else:
            logger.error("Failed to fetch: %s", url)

    logger.info("Imported %d library docs", count)
    return count


def import_custom_url(
    manager: ExternalKnowledgeManager,
    url: str,
    source: str = "custom",
    version: str = "latest",
    trust_score: float = 0.7,
) -> int:
    """Import documentation from custom URL.

    Args:
        manager: External knowledge manager
        url: Documentation URL
        source: Source type
        version: Version identifier
        trust_score: Trust score (0.0-1.0)

    Returns:
        Number of documents imported
    """
    logger.info("Importing custom URL: %s", url)

    # Map source string to enum
    source_enum = KnowledgeSource.CUSTOM
    if source.lower() == "github":
        source_enum = KnowledgeSource.GITHUB

    doc = manager.fetch_api_docs(
        url=url,
        source=source_enum,
        version=version,
        trust_score=trust_score,
    )

    if doc:
        if manager.cache_external_doc(doc):
            logger.info("Imported: %s", url)
            return 1
        logger.error("Failed to cache: %s", url)
    else:
        logger.error("Failed to fetch: %s", url)

    return 0


def import_from_json(
    manager: ExternalKnowledgeManager,
    json_path: Path,
) -> int:
    """Import documents from JSON file.

    Expected JSON format:
    [
        {
            "url": "https://example.com/doc",
            "source": "custom",
            "version": "latest",
            "trust_score": 0.8
        },
        ...
    ]

    Args:
        manager: External knowledge manager
        json_path: Path to JSON file

    Returns:
        Number of documents imported
    """
    logger.info("Importing from JSON: %s", json_path)

    if not json_path.exists():
        logger.error("JSON file not found: %s", json_path)
        return 0

    try:
        with open(json_path) as f:
            docs = json.load(f)

        count = 0

        for doc_spec in docs:
            url = doc_spec.get("url")
            if not url:
                logger.warning("Skipping entry without URL: %s", doc_spec)
                continue

            source = doc_spec.get("source", "custom")
            version = doc_spec.get("version", "latest")
            trust_score = doc_spec.get("trust_score", 0.7)

            imported = import_custom_url(
                manager=manager,
                url=url,
                source=source,
                version=version,
                trust_score=trust_score,
            )

            count += imported

        logger.info("Imported %d docs from JSON", count)
        return count

    except json.JSONDecodeError as e:
        logger.error("Invalid JSON: %s", e)
        return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Import external knowledge into Neo4j memory system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    subparsers = parser.add_subparsers(dest="command", help="Import source")

    # Python docs
    python_parser = subparsers.add_parser("python", help="Import Python documentation")
    python_parser.add_argument(
        "--version",
        default="latest",
        choices=list(PYTHON_DOCS_URLS.keys()),
        help="Python version",
    )
    python_parser.add_argument(
        "--pages",
        nargs="+",
        help="Specific pages to import",
    )

    # MS Learn
    ms_learn_parser = subparsers.add_parser("ms-learn", help="Import MS Learn content")
    ms_learn_parser.add_argument(
        "--topic",
        required=True,
        help="Topic area (azure, dotnet, python, etc.)",
    )
    ms_learn_parser.add_argument(
        "--articles",
        nargs="+",
        help="Specific article paths",
    )

    # Library docs
    library_parser = subparsers.add_parser("library", help="Import library documentation")
    library_parser.add_argument(
        "--name",
        required=True,
        help=f"Library name ({', '.join(LIBRARY_DOCS.keys())})",
    )
    library_parser.add_argument(
        "--pages",
        nargs="+",
        help="Specific pages to import",
    )

    # Custom URL
    custom_parser = subparsers.add_parser("custom", help="Import from custom URL")
    custom_parser.add_argument(
        "--url",
        required=True,
        help="Documentation URL",
    )
    custom_parser.add_argument(
        "--source",
        default="custom",
        choices=["custom", "github"],
        help="Source type",
    )
    custom_parser.add_argument(
        "--version",
        default="latest",
        help="Version identifier",
    )
    custom_parser.add_argument(
        "--trust-score",
        type=float,
        default=0.7,
        help="Trust score (0.0-1.0)",
    )

    # JSON import
    json_parser = subparsers.add_parser("json", help="Import from JSON file")
    json_parser.add_argument(
        "--file",
        required=True,
        type=Path,
        help="Path to JSON file",
    )

    # Stats
    subparsers.add_parser("stats", help="Show knowledge statistics")

    # Cleanup
    subparsers.add_parser("cleanup", help="Remove expired documents")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Ensure Neo4j is running
    logger.info("Ensuring Neo4j is running...")
    if not ensure_neo4j_running(blocking=True):
        logger.error("Neo4j is not running. Start it first.")
        return 1

    # Connect to Neo4j
    with Neo4jConnector() as conn:
        manager = ExternalKnowledgeManager(conn)

        # Initialize schema
        logger.info("Initializing external knowledge schema...")
        manager.initialize_knowledge_schema()

        # Execute command
        if args.command == "python":
            count = import_python_docs(
                manager=manager,
                version=args.version,
                pages=args.pages,
            )
            logger.info("Successfully imported %d Python docs", count)

        elif args.command == "ms-learn":
            count = import_ms_learn(
                manager=manager,
                topic=args.topic,
                articles=args.articles,
            )
            logger.info("Successfully imported %d MS Learn docs", count)

        elif args.command == "library":
            count = import_library_docs(
                manager=manager,
                library_name=args.name,
                pages=args.pages,
            )
            logger.info("Successfully imported %d library docs", count)

        elif args.command == "custom":
            count = import_custom_url(
                manager=manager,
                url=args.url,
                source=args.source,
                version=args.version,
                trust_score=args.trust_score,
            )
            logger.info("Successfully imported %d custom docs", count)

        elif args.command == "json":
            count = import_from_json(
                manager=manager,
                json_path=args.file,
            )
            logger.info("Successfully imported %d docs from JSON", count)

        elif args.command == "stats":
            stats = manager.get_knowledge_stats()
            logger.info("Knowledge Statistics:")
            logger.info("  Total documents: %d", stats.get("total_docs", 0))
            logger.info("  Sources: %d", stats.get("sources", 0))
            logger.info("  Average trust: %.2f", stats.get("avg_trust_score", 0.0))
            logger.info("  Total links: %d", stats.get("total_links", 0))

        elif args.command == "cleanup":
            count = manager.cleanup_expired_docs()
            logger.info("Removed %d expired documents", count)

    return 0


if __name__ == "__main__":
    sys.exit(main())
