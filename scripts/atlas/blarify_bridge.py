"""Bridge between blarify's code graph and atlas layer extraction.

Builds a blarify graph for a given directory, extracts definitions (classes,
functions, methods) across ALL supported languages, and returns data in the
same JSON schema format as the existing Python-only ast_bindings layer.

Supported languages: Python, JavaScript, TypeScript, Ruby, C#, Go, PHP, Java.

Public API:
    BlarifyBridge: Main bridge class
    EXTENSION_TO_LANGUAGE: Extension-to-language mapping
"""

import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))
sys.path.insert(0, str(_REPO_ROOT))

__all__ = ["BlarifyBridge", "EXTENSION_TO_LANGUAGE"]

# Extension -> human-readable language name
EXTENSION_TO_LANGUAGE: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".rb": "ruby",
    ".cs": "csharp",
    ".go": "go",
    ".php": "php",
    ".java": "java",
}


class BlarifyBridge:
    """Thin wrapper that builds a blarify graph and extracts atlas-compatible data.

    Usage::

        bridge = BlarifyBridge(Path("/path/to/project"))
        bridge.build()
        defs = bridge.get_all_definitions()
    """

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.graph = None

    def build(self, hierarchy_only: bool = False) -> "BlarifyBridge":
        """Build the blarify graph for the project.

        Args:
            hierarchy_only: If False (default), full build with LSP reference
                resolution. Gives CALLS, IMPORTS, INSTANTIATES, USES, INHERITS
                relationships. Slower (minutes for large codebases) but much richer.
                If True, fast build with definitions only (1-2s).

        Returns:
            self, for chaining.
        """
        from amplihack.vendor.blarify.project_file_explorer import ProjectFilesIterator
        from amplihack.vendor.blarify.code_references.hybrid_resolver import HybridReferenceResolver
        from amplihack.vendor.blarify.project_graph_creator import ProjectGraphCreator

        # Skip common non-source directories
        names_to_skip = [
            "node_modules", "__pycache__", ".git", ".venv", "venv",
            ".tox", ".mypy_cache", ".pytest_cache", "target", "dist",
            "build", ".next", ".nuxt", "vendor",
        ]

        iterator = ProjectFilesIterator(
            root_path=str(self.root),
            names_to_skip=names_to_skip,
        )
        resolver = HybridReferenceResolver(f"file://{self.root}")
        creator = ProjectGraphCreator(
            root_path=str(self.root),
            reference_query_helper=resolver,
            project_files_iterator=iterator,
        )

        if hierarchy_only:
            self.graph = creator.build_hierarchy_only()
        else:
            self.graph = creator.build()

        return self

    def get_all_definitions(self) -> list[dict]:
        """Get all class/function/method definitions across all languages.

        Returns:
            List of definition dicts with keys: name, type, file, lineno,
            end_lineno, language, is_exported, is_private.
        """
        if self.graph is None:
            raise RuntimeError("Call build() before get_all_definitions()")

        defs = []

        # Extract CLASS nodes
        for node in self.graph.get_nodes_by_label("CLASS"):
            defn = self._node_to_definition(node, "class")
            if defn:
                defs.append(defn)

        # Extract FUNCTION nodes (top-level functions AND methods)
        for node in self.graph.get_nodes_by_label("FUNCTION"):
            # Determine if this is a method (parent is a class) or a function
            defn_type = "method" if self._parent_is_class(node) else "function"
            defn = self._node_to_definition(node, defn_type)
            if defn:
                defs.append(defn)

        # Extract METHOD nodes if blarify labels them separately
        for node in self.graph.get_nodes_by_label("METHOD"):
            defn = self._node_to_definition(node, "method")
            if defn:
                defs.append(defn)

        return defs

    def get_file_definitions(self, file_path: str) -> list[dict]:
        """Get definitions in a specific file.

        Args:
            file_path: Absolute path to the file.

        Returns:
            List of definition dicts for that file only.
        """
        all_defs = self.get_all_definitions()
        return [d for d in all_defs if d["file"] == file_path]

    def get_relationships(self) -> list[dict]:
        """Extract all relationships from the graph as JSON-serializable dicts.

        Each relationship has: type, source_file, source_name, target_file,
        target_name. For code-reference types (CALLS, IMPORTS, INSTANTIATES,
        USES, INHERITS), source/target are definition nodes. For hierarchy
        types (CONTAINS, etc.), they are structural nodes.

        Returns:
            List of relationship dicts.
        """
        if self.graph is None:
            raise RuntimeError("Call build() before get_relationships()")

        # Use raw relationship objects for richer node info
        code_ref_types = {"CALLS", "IMPORTS", "INSTANTIATES", "USES", "INHERITS",
                          "TYPES", "ASSIGNS"}
        results = []

        for rel in self.graph.get_relationships_from_nodes():
            rel_type = rel.rel_type.name
            start = rel.start_node
            end = rel.end_node
            entry = {
                "type": rel_type,
                "source_file": start.path.replace("file://", "") if start.path.startswith("file://") else start.path,
                "source_name": start.name,
                "target_file": end.path.replace("file://", "") if end.path.startswith("file://") else end.path,
                "target_name": end.name,
            }
            if rel.start_line is not None:
                entry["lineno"] = rel.start_line
            results.append(entry)

        # Also include reference relationships (from LSP resolution)
        for rel in self.graph._Graph__references_relationships:
            rel_type = rel.rel_type.name
            start = rel.start_node
            end = rel.end_node
            entry = {
                "type": rel_type,
                "source_file": start.path.replace("file://", "") if start.path.startswith("file://") else start.path,
                "source_name": start.name,
                "target_file": end.path.replace("file://", "") if end.path.startswith("file://") else end.path,
                "target_name": end.name,
            }
            if rel.start_line is not None:
                entry["lineno"] = rel.start_line
            results.append(entry)

        return results

    def get_call_graph(self) -> dict:
        """Extract CALLS relationships as a directed graph.

        Returns:
            {"nodes": [...], "edges": [{"from": "file::func", "to": "file::func", "type": "CALLS"}]}
        """
        if self.graph is None:
            raise RuntimeError("Call build() before get_call_graph()")

        rels = self.get_relationships()
        calls = [r for r in rels if r["type"] == "CALLS"]

        nodes_set: set[str] = set()
        edges = []
        for c in calls:
            src_key = f"{c['source_file']}::{c['source_name']}"
            tgt_key = f"{c['target_file']}::{c['target_name']}"
            nodes_set.add(src_key)
            nodes_set.add(tgt_key)
            edges.append({"from": src_key, "to": tgt_key, "type": "CALLS"})

        return {"nodes": sorted(nodes_set), "edges": edges}

    def get_imports(self) -> list[dict]:
        """Extract IMPORTS relationships.

        Returns:
            List of dicts with source_file, target_file, source_name, target_name.
        """
        if self.graph is None:
            raise RuntimeError("Call build() before get_imports()")

        rels = self.get_relationships()
        return [
            {
                "source_file": r["source_file"],
                "target_file": r["target_file"],
                "source_name": r["source_name"],
                "target_name": r["target_name"],
            }
            for r in rels if r["type"] == "IMPORTS"
        ]

    def get_relationship_summary(self) -> dict[str, int]:
        """Count relationships by type.

        Returns:
            Dict mapping relationship type to count, plus "total".
        """
        if self.graph is None:
            raise RuntimeError("Call build() before get_relationship_summary()")

        rels = self.get_relationships()
        counts: dict[str, int] = {}
        for r in rels:
            rtype = r["type"]
            counts[rtype] = counts.get(rtype, 0) + 1
        counts["total"] = len(rels)
        return counts

    def get_language_stats(self) -> dict[str, int]:
        """Count definitions per language from the graph.

        Returns:
            Dict mapping language name to definition count.
        """
        defs = self.get_all_definitions()
        stats: dict[str, int] = {}
        for d in defs:
            lang = d["language"]
            stats[lang] = stats.get(lang, 0) + 1
        return stats

    def get_file_count_by_language(self) -> dict[str, int]:
        """Count files per language from the graph.

        Returns:
            Dict mapping language name to file count.
        """
        if self.graph is None:
            raise RuntimeError("Call build() before get_file_count_by_language()")

        stats: dict[str, int] = {}
        for node in self.graph.get_nodes_by_label("FILE"):
            ext = os.path.splitext(node.name)[1]
            lang = EXTENSION_TO_LANGUAGE.get(ext)
            if lang:
                stats[lang] = stats.get(lang, 0) + 1
        return stats

    def to_layer2_definitions(self) -> list[dict]:
        """Convert graph definitions to layer 2 (ast-bindings) schema.

        Returns definitions in the same format as ast_bindings.py's output:
        each dict has file, name, type, lineno, is_private, is_exported,
        references (empty -- cross-ref is done by ast_bindings), reference_count.
        """
        defs = self.get_all_definitions()
        out = []
        for d in defs:
            out.append({
                "file": d["file"],
                "name": d["name"],
                "type": d["type"],
                "lineno": d["lineno"],
                "is_private": d["is_private"],
                "is_exported": d.get("is_exported", False),
                "references": [],
                "reference_count": 0,
                "language": d["language"],
            })
        return out

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _node_to_definition(self, node, defn_type: str) -> dict | None:
        """Convert a blarify graph node to an atlas definition dict."""
        obj = node.as_object()
        attrs = obj.get("attributes", {})

        # Get the file path from the node's path attribute
        # Blarify stores paths as file:// URIs
        raw_path = attrs.get("path", "")
        file_path = raw_path.replace("file://", "") if raw_path.startswith("file://") else raw_path

        if not file_path:
            return None

        # Determine language from file extension
        ext = os.path.splitext(file_path)[1]
        language = EXTENSION_TO_LANGUAGE.get(ext, "unknown")

        # Line numbers: blarify stores start_line/end_line on definition nodes
        start_line = attrs.get("start_line", 0)
        end_line = attrs.get("end_line", 0)

        # Blarify uses 0-based line numbers; atlas uses 1-based
        lineno = start_line + 1 if isinstance(start_line, int) else 1
        end_lineno = end_line + 1 if isinstance(end_line, int) else lineno

        name = attrs.get("name", node.name)
        is_private = name.startswith("_")

        return {
            "name": name,
            "type": defn_type,
            "file": file_path,
            "lineno": lineno,
            "end_lineno": end_lineno,
            "language": language,
            "is_exported": False,
            "is_private": is_private,
        }

    def _parent_is_class(self, node) -> bool:
        """Check if a node's parent is a CLASS node."""
        if node.parent is None:
            return False
        try:
            return node.parent.label.value == "CLASS"
        except AttributeError:
            return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Blarify bridge: extract definitions from code")
    parser.add_argument("root", help="Project root directory")
    parser.add_argument("--full", action="store_true", help="Full build (with LSP references)")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"ERROR: {root} is not a directory", file=sys.stderr)
        sys.exit(1)

    mode = "full (with LSP)" if args.full else "hierarchy only"
    print(f"Building blarify graph for {root} ({mode})...")
    bridge = BlarifyBridge(root)
    bridge.build(hierarchy_only=not args.full)

    defs = bridge.get_all_definitions()
    print(f"Total definitions: {len(defs)}")

    # Count by language
    from collections import Counter
    langs = Counter(d["language"] for d in defs)
    for lang, count in langs.most_common():
        print(f"  {lang}: {count}")

    # Count by type
    types = Counter(d["type"] for d in defs)
    for typ, count in types.most_common():
        print(f"  {typ}: {count}")

    # File counts
    file_stats = bridge.get_file_count_by_language()
    print(f"\nFiles by language:")
    for lang, count in sorted(file_stats.items(), key=lambda x: -x[1]):
        print(f"  {lang}: {count}")

    # Relationship summary (meaningful for full builds)
    rel_summary = bridge.get_relationship_summary()
    if rel_summary.get("total", 0) > 0:
        print(f"\nRelationships ({rel_summary['total']} total):")
        for rtype, count in sorted(rel_summary.items(), key=lambda x: -x[1]):
            if rtype != "total":
                print(f"  {rtype}: {count}")
