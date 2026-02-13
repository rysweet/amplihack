"""Blarify code graph integration for session lifecycle.

Handles: staleness detection, indexing dispatch, context injection.
Called from session_start hook. All errors caught - never blocks session.
"""

import os
import shutil
import sys
from collections.abc import Callable
from pathlib import Path


def setup_blarify_indexing(
    project_root: Path,
    log: Callable,
    save_metric: Callable,
) -> None:
    """Check if blarify indexing is needed and dispatch it.

    Args:
        project_root: Project root directory
        log: Logger function (message, level)
        save_metric: Metric saving function (key, value)
    """
    src_path = project_root / "src"
    if src_path.exists():
        sys.path.insert(0, str(src_path))

    from amplihack.memory.kuzu.indexing.staleness_detector import check_index_status

    status = check_index_status(project_root)

    if not status.needs_indexing:
        log("Blarify index is fresh - no indexing needed")
        save_metric("blarify_index_fresh", True)
        return

    log(f"Blarify indexing needed: {status.reason}")

    if not shutil.which("scip-python"):
        log("scip-python not found - skipping blarify indexing", "WARNING")
        print(
            "\n  Blarify: scip-python not installed. "
            "Install with: npm install -g @sourcegraph/scip-python",
            file=sys.stderr,
        )
        save_metric("blarify_missing_scip", True)
        return

    mode = os.environ.get("AMPLIHACK_BLARIFY_MODE", "background").lower()

    print(f"\n  Blarify: indexing needed ({status.reason})", file=sys.stderr)
    if status.estimated_files > 0:
        print(f"  Files: ~{status.estimated_files}", file=sys.stderr)

    if mode == "skip":
        log("User skipped blarify indexing (AMPLIHACK_BLARIFY_MODE=skip)")
        save_metric("blarify_indexing_skipped", True)
    elif mode == "sync":
        print("  Mode: synchronous (AMPLIHACK_BLARIFY_MODE=sync)", file=sys.stderr)
        _run_sync(project_root, log, save_metric)
    else:
        print("  Mode: background indexing", file=sys.stderr)
        _run_background(project_root, log, save_metric)


def inject_code_graph_context(
    project_root: Path,
    context_parts: list[str],
    log: Callable,
    save_metric: Callable,
) -> None:
    """Inject code graph summary into session context for agents.

    Only runs if a Kuzu database already exists on disk.

    Args:
        project_root: Project root directory
        context_parts: List to append context strings to
        log: Logger function
        save_metric: Metric saving function
    """
    db_path = project_root / ".amplihack" / "kuzu_db"
    if not db_path.exists():
        return

    src_path = project_root / "src"
    if src_path.exists():
        sys.path.insert(0, str(src_path))

    from amplihack.memory.kuzu.connector import KuzuConnector

    conn = KuzuConnector(str(db_path))
    conn.connect()

    stats = {}
    for label, query in [
        ("files", "MATCH (cf:CodeFile) RETURN count(cf) as cnt"),
        ("classes", "MATCH (c:CodeClass) RETURN count(c) as cnt"),
        ("functions", "MATCH (f:CodeFunction) RETURN count(f) as cnt"),
    ]:
        try:
            result = conn.execute_query(query)
            stats[label] = result[0]["cnt"] if result else 0
        except Exception as e:
            log(f"Code graph query failed for {label}: {e}", "WARNING")
            stats[label] = 0

    total = stats.get("files", 0) + stats.get("classes", 0) + stats.get("functions", 0)
    if total == 0:
        return

    context_parts.append("\n## Code Graph (Blarify)")
    context_parts.append(
        f"A code graph is available with {stats['files']} files, "
        f"{stats['classes']} classes, and {stats['functions']} functions indexed."
    )
    context_parts.append(
        "To query the code graph, use:\n"
        "```bash\n"
        "python -m amplihack.memory.kuzu.query_code_graph stats\n"
        "python -m amplihack.memory.kuzu.query_code_graph search <name>\n"
        "python -m amplihack.memory.kuzu.query_code_graph functions --file <path>\n"
        "python -m amplihack.memory.kuzu.query_code_graph classes --file <path>\n"
        "python -m amplihack.memory.kuzu.query_code_graph files --pattern <pattern>\n"
        "python -m amplihack.memory.kuzu.query_code_graph callers <function_name>\n"
        "python -m amplihack.memory.kuzu.query_code_graph callees <function_name>\n"
        "```"
    )
    context_parts.append(
        "Use `--json` flag for machine-readable output. Use `--limit N` to control result count."
    )

    log(f"Injected code graph context: {stats}")
    save_metric("code_graph_available", True)
    save_metric("code_graph_files", stats["files"])


def _run_sync(project_root: Path, log: Callable, save_metric: Callable) -> None:
    """Run synchronous blarify indexing."""
    from amplihack.memory.kuzu.connector import KuzuConnector
    from amplihack.memory.kuzu.indexing.orchestrator import IndexingConfig, Orchestrator

    try:
        print("\n  Indexing codebase...", file=sys.stderr, flush=True)

        db_path = project_root / ".amplihack" / "kuzu_db"
        db_path.parent.mkdir(parents=True, exist_ok=True)

        connector = KuzuConnector(str(db_path))
        connector.connect()

        result = Orchestrator(connector=connector).run(
            codebase_path=project_root,
            languages=["python", "javascript", "typescript"],
            background=False,
            config=IndexingConfig(max_retries=2),
        )

        if result.success:
            print(
                f"\n  Done! Indexed {result.total_files} files, "
                f"{result.total_functions} functions\n",
                file=sys.stderr,
            )
            save_metric("blarify_indexing_success", True)
            save_metric("blarify_files_indexed", result.total_files)

            try:
                from amplihack.memory.kuzu.code_graph import KuzuCodeGraph

                link_count = KuzuCodeGraph(connector).link_code_to_memories()
                if link_count > 0:
                    log(f"Linked {link_count} memories to code")
            except Exception as e:
                log(f"Memory-code linking failed: {e}", "WARNING")
        else:
            failed = ", ".join(result.failed_languages) if result.failed_languages else "unknown"
            print(f"\n  Indexing completed with errors (failed: {failed})\n", file=sys.stderr)
            save_metric("blarify_indexing_partial", True)

    except Exception as e:
        print(f"\n  Indexing failed: {e}\n  Continuing without code graph.\n", file=sys.stderr)
        log(f"Blarify indexing failed: {e}", "WARNING")
        save_metric("blarify_indexing_error", True)


def _run_background(project_root: Path, log: Callable, save_metric: Callable) -> None:
    """Start background blarify indexing."""
    try:
        from amplihack.memory.kuzu.indexing.background_indexer import BackgroundIndexer

        job = BackgroundIndexer().start_background_job(
            codebase_path=project_root,
            languages=["python", "javascript", "typescript"],
            timeout=300,
        )

        print(f"\n  Background indexing started (job {job.job_id})\n", file=sys.stderr)
        save_metric("blarify_indexing_background", True)

    except Exception as e:
        print(f"\n  Background indexing failed: {e}\n", file=sys.stderr)
        log(f"Background indexing failed: {e}", "WARNING")
