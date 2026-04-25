"""Mermaid renderer: converts a normalized Graph into mermaid syntax.

Language-blind: only inspects Node/Edge/Graph dataclasses, never branches on
the `language` field for syntax decisions.
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_HERE = _Path(__file__).resolve().parent
if str(_HERE) not in _sys.path:
    _sys.path.insert(0, str(_HERE))

import re

from graph import Graph

_SAFE_ID = re.compile(r"[^A-Za-z0-9_]")


def _sanitize_id(raw: str) -> str:
    """Mermaid identifier: alnum + underscore, must not start with digit."""
    cleaned = _SAFE_ID.sub("_", raw)
    if not cleaned:
        cleaned = "n"
    if cleaned[0].isdigit():
        cleaned = "n_" + cleaned
    return cleaned


def _escape_label(raw: str) -> str:
    return raw.replace('"', '\\"').replace("\n", " ")


def _node_ids_for(graph: Graph) -> tuple[dict[str, str], list[tuple[str, str, str]]]:
    """Return (raw_id -> safe_id, list of (safe_id, label, raw_id) for declarations)."""
    raw_ids: list[str] = []
    seen: set[str] = set()
    for n in graph.nodes:
        if n.id not in seen:
            raw_ids.append(n.id)
            seen.add(n.id)
    for e in graph.edges:
        for rid in (e.src, e.dst):
            if rid not in seen:
                raw_ids.append(rid)
                seen.add(rid)

    mapping: dict[str, str] = {}
    used: set[str] = set()
    decls: list[tuple[str, str, str]] = []
    for raw in raw_ids:
        safe = _sanitize_id(raw)
        base = safe
        i = 1
        while safe in used:
            i += 1
            safe = f"{base}_{i}"
        used.add(safe)
        mapping[raw] = safe
        decls.append((safe, raw, raw))  # safe_id, label, original_raw
    return mapping, decls


def render(graph: Graph) -> str:
    """Render a single-language Graph as a mermaid `graph LR` diagram."""
    lines: list[str] = ["graph LR"]
    mapping, decls = _node_ids_for(graph)

    if not decls:
        # Always emit at least one comment so output is non-empty/parseable.
        lines.append(f"    %% no nodes for language={graph.language}")
        return "\n".join(lines) + "\n"

    for safe, label, _raw in decls:
        lines.append(f'    {safe}["{_escape_label(label)}"]')

    for e in graph.edges:
        s = mapping.get(e.src) or _sanitize_id(e.src)
        d = mapping.get(e.dst) or _sanitize_id(e.dst)
        lines.append(f"    {s} --> {d}")

    return "\n".join(lines) + "\n"


def render_combined(graphs: dict[str, Graph]) -> str:
    """Render multiple language graphs as one mermaid diagram with subgraphs."""
    lines: list[str] = ["graph LR"]
    if not graphs:
        lines.append("    %% no graphs to render")
        return "\n".join(lines) + "\n"

    # Per-language id namespacing to avoid collisions across languages.
    for lang, graph in graphs.items():
        safe_lang = _sanitize_id(lang)
        lines.append(f'    subgraph {safe_lang} ["{_escape_label(lang)}"]')
        mapping, decls = _node_ids_for(graph)
        prefixed: dict[str, str] = {}
        for safe, label, raw in decls:
            ns_safe = f"{safe_lang}_{safe}"
            prefixed[raw] = ns_safe
            lines.append(f'        {ns_safe}["{_escape_label(label)}"]')
        for e in graph.edges:
            s = prefixed.get(e.src) or f"{safe_lang}_{_sanitize_id(e.src)}"
            d = prefixed.get(e.dst) or f"{safe_lang}_{_sanitize_id(e.dst)}"
            lines.append(f"        {s} --> {d}")
        lines.append("    end")

    return "\n".join(lines) + "\n"
