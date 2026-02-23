"""Backfill TRANSITIONED_TO edges for existing memory databases.

Scans all SemanticMemory nodes in a Kuzu database, groups by entity_name,
detects update patterns in fact content, and creates TRANSITIONED_TO edges
between old-value and new-value facts.

This is needed for databases built before the temporal transitions feature
was added (e.g., the 5000-turn eval DB).

Usage:
    python -m amplihack.eval.backfill_transitions \
        --db-path eval_data/5000t_harder_eval/memory_db \
        --agent-name long_horizon_5000t_harder

    # Dry-run (no edges created, just report):
    python -m amplihack.eval.backfill_transitions \
        --db-path eval_data/5000t_harder_eval/memory_db \
        --agent-name long_horizon_5000t_harder \
        --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)

# Transition detection patterns (same as learning_agent.py)
_TRANSITION_PATTERNS = [
    r"changed\s+from\s+(.+?)\s+to\s+(.+?)(?:\s*[;,.]|\s+(?:due|because|after|when)|\s*$)",
    r"(?:increased|decreased|grew|dropped|rose|fell|jumped|shifted)\s+from\s+(.+?)\s+to\s+(.+?)(?:\s*[;,.]|\s+(?:due|because|after|when)|\s*$)",
    r"was\s+(.+?)\s*,?\s*(?:but\s+)?now\s+(.+?)(?:\s*[;,.]|\s*$)",
    r"moved\s+from\s+(.+?)\s+to\s+(.+?)(?:\s*[;,.]|\s+(?:due|because|after|when)|\s*$)",
    r"revised\s+from\s+(.+?)\s+to\s+(.+?)(?:\s*[;,.]|\s+(?:due|because|after|when)|\s*$)",
    r"updated\s+to\s+(.+?)\s+\(?(?:was|from)\s+(.+?)\)?(?:\s*[;,.]|\s*$)",
    r"replaced\s+(.+?)\s+with\s+(.+?)(?:\s*[;,.]|\s+(?:due|because|after|when)|\s*$)",
    r"(\S+(?:\s+\S+){0,3})\s+was\s+(?:extended|pushed|delayed|advanced|moved)\s+to\s+(.+?)(?:\s*[;,.]|\s+(?:due|because|after|when)|\s*$)",
]


def _extract_field(content: str, concept: str) -> str:
    """Extract field name from content and concept text."""
    text = f"{concept} {content}".lower()
    for field_name in [
        "deadline",
        "budget",
        "team_size",
        "team size",
        "scope",
        "priority",
        "status",
        "phase",
        "timeline",
        "schedule",
        "target",
        "goal",
        "estimate",
        "cost",
        "revenue",
        "headcount",
        "capacity",
        "duration",
        "release_date",
        "launch_date",
        "completion_date",
        "start_date",
    ]:
        if field_name.replace("_", " ") in text:
            return field_name.replace(" ", "_")

    field_match = re.search(
        r"(\w+(?:\s+\w+)?)\s+(?:changed|increased|decreased|moved|revised|updated|shifted|was extended|was pushed)",
        content,
        re.IGNORECASE,
    )
    if field_match:
        return field_match.group(1).strip().lower().replace(" ", "_")

    return concept.lower().replace(" ", "_")[:50] if concept else "value"


def _extract_reason(content: str, match_end: int) -> str:
    """Extract reason for transition from text after the match."""
    remaining = content[match_end:].strip()
    if not remaining:
        return ""
    reason_match = re.search(
        r"(?:due to|because of?|after|following|as a result of|caused by)\s+(.+?)(?:[;.]|$)",
        remaining,
        re.IGNORECASE,
    )
    if reason_match:
        return reason_match.group(1).strip()[:200]
    return ""


def backfill_transitions(
    db_path: str,
    agent_name: str,
    dry_run: bool = False,
) -> dict:
    """Scan existing facts and create TRANSITIONED_TO edges.

    Algorithm:
    1. Load all SemanticMemory nodes grouped by entity_name
    2. For each entity group, sort by temporal_index
    3. Scan fact content for transition patterns
    4. When pattern found, find the old-value fact in the same entity group
    5. Create TRANSITIONED_TO edge from old to new

    Args:
        db_path: Path to Kuzu database
        agent_name: Agent name to filter by
        dry_run: If True, don't create edges, just report

    Returns:
        Dict with statistics about edges found/created
    """
    import kuzu  # type: ignore[import-not-found]

    # Open Kuzu DB directly (handles both HierarchicalMemory and CognitiveMemory schemas)
    db_resolved = Path(db_path)
    if db_resolved.is_dir() and (db_resolved / "kuzu_db").exists():
        kuzu_path = db_resolved / "kuzu_db"
    elif db_resolved.is_dir():
        kuzu_path = db_resolved
    else:
        kuzu_path = db_resolved

    database = kuzu.Database(str(kuzu_path))
    conn = kuzu.Connection(database)

    stats = {
        "total_nodes_scanned": 0,
        "entities_with_transitions": 0,
        "transitions_detected": 0,
        "edges_created": 0,
        "edges_failed": 0,
        "transition_details": [],
    }

    # Auto-detect schema: check if the PK is memory_id or node_id
    pk_col = "memory_id"  # default for HierarchicalMemory
    try:
        table_info = conn.execute('CALL table_info("SemanticMemory") RETURN *')
        while table_info.has_next():
            row = table_info.get_next()
            if row[3] is True or (isinstance(row[3], str) and row[3] == "True"):
                # This is the primary key column
                pk_col = row[1]
                break
            # Check if column 0 is 'node_id'
            if row[1] == "node_id":
                pk_col = "node_id"
    except Exception:
        pass

    print(f"Using PK column: {pk_col}")

    # Ensure TRANSITIONED_TO table exists
    try:
        conn.execute("""
            CREATE REL TABLE IF NOT EXISTS TRANSITIONED_TO(
                FROM SemanticMemory TO SemanticMemory,
                field STRING,
                old_value STRING,
                new_value STRING,
                reason STRING,
                turn_number INT64
            )
        """)
    except Exception as e:
        logger.debug("TRANSITIONED_TO table may already exist: %s", e)

    # Load all semantic nodes
    result = conn.execute(
        f"""
        MATCH (m:SemanticMemory)
        WHERE m.agent_id = $aid
        RETURN m.{pk_col}, m.concept, m.content, m.entity_name,
               m.metadata, m.created_at
        ORDER BY m.created_at ASC
        """,
        {"aid": agent_name},
    )

    all_nodes = []
    while result.has_next():
        row = result.get_next()
        meta = (
            json.loads(row[4])
            if row[4] and isinstance(row[4], str)
            else (row[4] if isinstance(row[4], dict) else {})
        )
        all_nodes.append(
            {
                "memory_id": row[0],
                "concept": row[1],
                "content": row[2],
                "entity_name": row[3] or "",
                "metadata": meta,
                "created_at": row[5] or "",
                "temporal_index": meta.get("temporal_index", 0),
            }
        )

    stats["total_nodes_scanned"] = len(all_nodes)
    print(f"Scanned {len(all_nodes)} nodes for agent '{agent_name}'")

    # Group by entity_name
    entity_groups: dict[str, list[dict]] = defaultdict(list)
    for node in all_nodes:
        if node["entity_name"]:
            entity_groups[node["entity_name"]].append(node)

    # Also group by concept for broader matching
    concept_groups: dict[str, list[dict]] = defaultdict(list)
    for node in all_nodes:
        if node["concept"]:
            concept_groups[node["concept"].lower()].append(node)

    print(f"Found {len(entity_groups)} distinct entities, {len(concept_groups)} concepts")

    # Track created edges to avoid duplicates (key = old_value + new_value + field)
    created_edge_keys: set[str] = set()

    # For each node, check if it contains a transition pattern
    for node in all_nodes:
        content = node["content"]
        content_lower = content.lower()
        concept = node["concept"]

        for pattern in _TRANSITION_PATTERNS:
            matches = list(re.finditer(pattern, content_lower, re.IGNORECASE))
            if not matches:
                continue

            for match in matches:
                groups = match.groups()
                if len(groups) < 2:
                    continue

                if "updated" in pattern:
                    new_value = groups[0].strip()
                    old_value = groups[1].strip()
                elif "replaced" in pattern:
                    old_value = groups[0].strip()
                    new_value = groups[1].strip()
                else:
                    old_value = groups[0].strip()
                    new_value = groups[1].strip()

                if len(old_value) < 1 or len(new_value) < 1 or old_value == new_value:
                    continue

                field = _extract_field(content, concept)
                reason = _extract_reason(content, match.end())

                # Search for old-value fact in same entity group or concept group
                old_node_id = None
                entity = node["entity_name"]
                old_val_lower = old_value.lower()

                # Search in entity group first
                if entity and entity in entity_groups:
                    for candidate in entity_groups[entity]:
                        if candidate["memory_id"] == node["memory_id"]:
                            continue
                        if old_val_lower in candidate["content"].lower():
                            # Prefer older facts
                            if candidate["temporal_index"] < node["temporal_index"]:
                                old_node_id = candidate["memory_id"]
                                break

                # Fall back to concept group
                if not old_node_id and concept:
                    concept_lower = concept.lower()
                    if concept_lower in concept_groups:
                        for candidate in concept_groups[concept_lower]:
                            if candidate["memory_id"] == node["memory_id"]:
                                continue
                            if old_val_lower in candidate["content"].lower():
                                if candidate["temporal_index"] < node["temporal_index"]:
                                    old_node_id = candidate["memory_id"]
                                    break

                # Broader search: any node with old value and overlapping concept words
                if not old_node_id:
                    concept_words = set(concept.lower().split()) if concept else set()
                    for candidate in all_nodes:
                        if candidate["memory_id"] == node["memory_id"]:
                            continue
                        if old_val_lower not in candidate["content"].lower():
                            continue
                        cand_words = (
                            set(candidate["concept"].lower().split())
                            if candidate["concept"]
                            else set()
                        )
                        if concept_words & cand_words:
                            if candidate["temporal_index"] <= node["temporal_index"]:
                                old_node_id = candidate["memory_id"]
                                break

                if old_node_id:
                    # Deduplicate: skip if we already created this exact transition
                    edge_key = f"{old_node_id}:{node['memory_id']}:{field}:{old_value}:{new_value}"
                    if edge_key in created_edge_keys:
                        continue
                    created_edge_keys.add(edge_key)

                    stats["transitions_detected"] += 1
                    turn = node["temporal_index"] or node.get("created_at", 0)
                    if isinstance(turn, str):
                        turn = 0

                    detail = {
                        "field": field,
                        "old_value": old_value[:50],
                        "new_value": new_value[:50],
                        "reason": reason[:100],
                        "turn": turn,
                        "entity": entity,
                    }
                    stats["transition_details"].append(detail)

                    if not dry_run:
                        try:
                            conn.execute(
                                f"""
                                MATCH (old_m:SemanticMemory {{{pk_col}: $old_id}})
                                MATCH (new_m:SemanticMemory {{{pk_col}: $new_id}})
                                CREATE (old_m)-[:TRANSITIONED_TO {{
                                    field: $field,
                                    old_value: $old_value,
                                    new_value: $new_value,
                                    reason: $reason,
                                    turn_number: $turn_number
                                }}]->(new_m)
                                """,
                                {
                                    "old_id": old_node_id,
                                    "new_id": node["memory_id"],
                                    "field": field,
                                    "old_value": old_value,
                                    "new_value": new_value,
                                    "reason": reason,
                                    "turn_number": turn,
                                },
                            )
                            stats["edges_created"] += 1
                        except Exception as e:
                            logger.debug("Failed to create edge: %s", e)
                            stats["edges_failed"] += 1
                    else:
                        print(
                            f"  [DRY-RUN] Would create edge: {field} "
                            f"'{old_value[:30]}' -> '{new_value[:30]}' "
                            f"(turn {turn}, entity={entity})"
                        )

                break  # Only first pattern match per node

    # Count entities with transitions
    entities_with = set()
    for detail in stats["transition_details"]:
        if detail["entity"]:
            entities_with.add(detail["entity"])
    stats["entities_with_transitions"] = len(entities_with)

    # Print summary
    print("\n--- Backfill Summary ---")
    print(f"Total nodes scanned: {stats['total_nodes_scanned']}")
    print(f"Transitions detected: {stats['transitions_detected']}")
    print(f"Entities with transitions: {stats['entities_with_transitions']}")
    if not dry_run:
        print(f"Edges created: {stats['edges_created']}")
        print(f"Edges failed: {stats['edges_failed']}")
    else:
        print("[DRY-RUN mode - no edges created]")

    # Print sample transitions
    if stats["transition_details"]:
        print("\nSample transitions (first 20):")
        for d in stats["transition_details"][:20]:
            print(
                f"  {d['entity']}: {d['field']} "
                f"'{d['old_value']}' -> '{d['new_value']}' "
                f"(turn {d['turn']})"
            )

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Backfill TRANSITIONED_TO edges for existing memory databases"
    )
    parser.add_argument(
        "--db-path",
        required=True,
        help="Path to Kuzu memory database",
    )
    parser.add_argument(
        "--agent-name",
        required=True,
        help="Agent name to filter by",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report transitions without creating edges",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    db_path = Path(args.db_path)
    if not db_path.exists():
        print(f"ERROR: Database path does not exist: {db_path}", file=sys.stderr)
        sys.exit(1)

    stats = backfill_transitions(
        db_path=str(db_path),
        agent_name=args.agent_name,
        dry_run=args.dry_run,
    )

    # Exit with error if no transitions found
    if stats["transitions_detected"] == 0:
        print("\nWARNING: No transitions detected. This may indicate:")
        print("  - The facts don't contain transition patterns")
        print("  - The agent_name doesn't match any nodes")
        sys.exit(0)


if __name__ == "__main__":
    main()
