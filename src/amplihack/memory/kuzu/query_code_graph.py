#!/usr/bin/env python3
"""CLI tool for querying the Kuzu code graph.

Agents and users can call this to look up functions, classes, files,
and relationships in the indexed codebase.

Schema: CodeFile (file_id, file_path, language, size_bytes)
        CodeClass (class_id, class_name, fully_qualified_name, file_path, ...)
        CodeFunction (function_id, function_name, fully_qualified_name, file_path, ...)
        Relationships: DEFINED_IN, CLASS_DEFINED_IN, CALLS, IMPORTS, METHOD_OF

Usage:
    python -m amplihack.memory.kuzu.query_code_graph stats
    python -m amplihack.memory.kuzu.query_code_graph files [--pattern "*.py"]
    python -m amplihack.memory.kuzu.query_code_graph functions [--file path]
    python -m amplihack.memory.kuzu.query_code_graph classes [--file path]
    python -m amplihack.memory.kuzu.query_code_graph search <name>
    python -m amplihack.memory.kuzu.query_code_graph callers <function_name>
    python -m amplihack.memory.kuzu.query_code_graph callees <function_name>
"""

import argparse
import json
import sys


def get_connector(db_path: str | None = None):
    """Get a KuzuConnector, finding the database automatically."""
    from amplihack.memory.kuzu.connector import KuzuConnector

    conn = KuzuConnector(db_path) if db_path else KuzuConnector()
    conn.connect()
    return conn


def cmd_stats(args):
    """Show code graph statistics."""
    conn = get_connector(args.db)
    results = {}

    queries = {
        "files": "MATCH (cf:CodeFile) RETURN count(cf) as cnt",
        "classes": "MATCH (c:CodeClass) RETURN count(c) as cnt",
        "functions": "MATCH (f:CodeFunction) RETURN count(f) as cnt",
    }

    for name, query in queries.items():
        try:
            result = conn.execute_query(query)
            results[name] = result[0]["cnt"] if result else 0
        except Exception:
            results[name] = 0

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print("Code Graph Statistics:")
        print(f"  Files:     {results['files']}")
        print(f"  Classes:   {results['classes']}")
        print(f"  Functions: {results['functions']}")


def cmd_files(args):
    """List indexed files."""
    conn = get_connector(args.db)

    if args.pattern:
        query = (
            "MATCH (cf:CodeFile) WHERE cf.file_path CONTAINS $pattern "
            "RETURN cf.file_path as path ORDER BY cf.file_path LIMIT $lim"
        )
        results = conn.execute_query(query, {"pattern": args.pattern, "lim": args.limit})
    else:
        query = "MATCH (cf:CodeFile) RETURN cf.file_path as path ORDER BY cf.file_path LIMIT $lim"
        results = conn.execute_query(query, {"lim": args.limit})

    if args.json:
        print(json.dumps([r["path"] for r in results], indent=2))
    else:
        for r in results:
            print(r["path"])
        if len(results) == args.limit:
            print(f"... (showing first {args.limit}, use --limit to see more)")


def cmd_functions(args):
    """List functions, optionally filtered by file."""
    conn = get_connector(args.db)

    # Filter out parameter entries like "run().(self)"
    param_filter = "AND NOT f.function_name CONTAINS '().(' "
    if args.file:
        query = (
            "MATCH (f:CodeFunction)-[:DEFINED_IN]->(cf:CodeFile) "
            "WHERE cf.file_path CONTAINS $file "
            + param_filter
            + "RETURN f.function_name as name, cf.file_path as file "
            "ORDER BY cf.file_path, f.function_name LIMIT $lim"
        )
        results = conn.execute_query(query, {"file": args.file, "lim": args.limit})
    else:
        query = (
            "MATCH (f:CodeFunction) "
            "WHERE NOT f.function_name CONTAINS '().(' "
            "RETURN f.function_name as name "
            "ORDER BY f.function_name LIMIT $lim"
        )
        results = conn.execute_query(query, {"lim": args.limit})

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            if "file" in r:
                print(f"  {r['file']}::{r['name']}")
            else:
                print(f"  {r['name']}")
        if len(results) == args.limit:
            print(f"... (showing first {args.limit}, use --limit to see more)")


def cmd_classes(args):
    """List classes, optionally filtered by file."""
    conn = get_connector(args.db)

    if args.file:
        query = (
            "MATCH (c:CodeClass)-[:CLASS_DEFINED_IN]->(cf:CodeFile) "
            "WHERE cf.file_path CONTAINS $file "
            "RETURN c.class_name as name, cf.file_path as file "
            "ORDER BY cf.file_path, c.class_name LIMIT $lim"
        )
        results = conn.execute_query(query, {"file": args.file, "lim": args.limit})
    else:
        query = "MATCH (c:CodeClass) RETURN c.class_name as name ORDER BY c.class_name LIMIT $lim"
        results = conn.execute_query(query, {"lim": args.limit})

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            if "file" in r:
                print(f"  {r['file']}::{r['name']}")
            else:
                print(f"  {r['name']}")
        if len(results) == args.limit:
            print(f"... (showing first {args.limit}, use --limit to see more)")


def cmd_search(args):
    """Search for a symbol by name (functions, classes, files)."""
    conn = get_connector(args.db)
    all_results = []

    # Filter out parameter entries like "run().(self)" which clutter results
    searches = [
        (
            "MATCH (f:CodeFunction) WHERE f.function_name CONTAINS $name "
            "AND NOT f.function_name CONTAINS '().(' "
            "RETURN 'function' as type, f.function_name as name LIMIT $lim",
        ),
        (
            "MATCH (c:CodeClass) WHERE c.class_name CONTAINS $name "
            "RETURN 'class' as type, c.class_name as name LIMIT $lim",
        ),
        (
            "MATCH (cf:CodeFile) WHERE cf.file_path CONTAINS $name "
            "RETURN 'file' as type, cf.file_path as name LIMIT $lim",
        ),
    ]

    params = {"name": args.name, "lim": args.limit}
    for (query,) in searches:
        try:
            results = conn.execute_query(query, params)
            all_results.extend(results)
        except Exception:
            pass

    if args.json:
        print(json.dumps(all_results, indent=2))
    else:
        if not all_results:
            print(f"No results for '{args.name}'")
        else:
            for r in all_results:
                print(f"  [{r['type']}] {r['name']}")


def cmd_callers(args):
    """Find functions that call a given function."""
    conn = get_connector(args.db)

    query = (
        "MATCH (caller:CodeFunction)-[:CALLS]->(callee:CodeFunction) "
        "WHERE callee.function_name CONTAINS $name "
        "RETURN caller.function_name as caller, callee.function_name as callee "
        "LIMIT $lim"
    )

    try:
        results = conn.execute_query(query, {"name": args.name, "lim": args.limit})
        if args.json:
            print(json.dumps(results, indent=2))
        elif not results:
            print(f"No callers found for '{args.name}'")
        else:
            print(f"Functions calling '{args.name}':")
            for r in results:
                print(f"  {r['caller']} -> {r['callee']}")
    except Exception as e:
        print(f"Error querying callers: {e}", file=sys.stderr)


def cmd_callees(args):
    """Find functions called by a given function."""
    conn = get_connector(args.db)

    query = (
        "MATCH (caller:CodeFunction)-[:CALLS]->(callee:CodeFunction) "
        "WHERE caller.function_name CONTAINS $name "
        "RETURN caller.function_name as caller, callee.function_name as callee "
        "LIMIT $lim"
    )

    try:
        results = conn.execute_query(query, {"name": args.name, "lim": args.limit})
        if args.json:
            print(json.dumps(results, indent=2))
        elif not results:
            print(f"No callees found for '{args.name}'")
        else:
            print(f"Functions called by '{args.name}':")
            for r in results:
                print(f"  {r['caller']} -> {r['callee']}")
    except Exception as e:
        print(f"Error querying callees: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Query the Kuzu code graph for code intelligence",
        prog="query_code_graph",
    )
    # Global args work before subcommand: --db X --json stats
    parser.add_argument("--db", help="Path to Kuzu database directory")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--limit", type=int, default=50, help="Max results (default: 50)")

    sub = parser.add_subparsers(dest="command", help="Command to run")

    # Common args also on subparsers so they work after: stats --json
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", dest="sub_json", help=argparse.SUPPRESS)
    common.add_argument("--limit", type=int, default=None, dest="sub_limit", help=argparse.SUPPRESS)
    common.add_argument("--db", dest="sub_db", help=argparse.SUPPRESS)

    sub.add_parser("stats", help="Show code graph statistics", parents=[common])

    p = sub.add_parser("files", help="List indexed files", parents=[common])
    p.add_argument("--pattern", help="Filter files by path pattern")

    p = sub.add_parser("functions", help="List indexed functions", parents=[common])
    p.add_argument("--file", help="Filter by file path")

    p = sub.add_parser("classes", help="List indexed classes", parents=[common])
    p.add_argument("--file", help="Filter by file path")

    p = sub.add_parser("search", help="Search for a symbol by name", parents=[common])
    p.add_argument("name", help="Symbol name to search for")

    p = sub.add_parser("callers", help="Find callers of a function", parents=[common])
    p.add_argument("name", help="Function name")

    p = sub.add_parser("callees", help="Find functions called by a function", parents=[common])
    p.add_argument("name", help="Function name")

    args = parser.parse_args()

    # Merge sub-parser args into main args (so --json works in both positions)
    if getattr(args, "sub_json", False):
        args.json = True
    if getattr(args, "sub_limit", None) is not None:
        args.limit = args.sub_limit
    if getattr(args, "sub_db", None) is not None:
        args.db = args.sub_db

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "stats": cmd_stats,
        "files": cmd_files,
        "functions": cmd_functions,
        "classes": cmd_classes,
        "search": cmd_search,
        "callers": cmd_callers,
        "callees": cmd_callees,
    }

    try:
        commands[args.command](args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
