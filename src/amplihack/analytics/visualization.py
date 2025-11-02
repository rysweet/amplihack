"""
Visualization engine for subagent execution maps.

Generates ASCII art trees, performance reports, and pattern detection.
"""

from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
from dataclasses import dataclass

from .metrics_reader import SubagentExecution, MetricsReader


@dataclass
class AgentNode:
    """Node in the agent execution tree."""
    name: str
    parent: Optional[str]
    invocation_count: int
    total_duration_ms: float
    children: List["AgentNode"]

    def add_child(self, child: "AgentNode") -> None:
        """Add a child node."""
        self.children.append(child)

    def total_duration_seconds(self) -> float:
        """Get total duration in seconds."""
        return self.total_duration_ms / 1000.0


@dataclass
class Pattern:
    """Detected execution pattern."""
    pattern_type: str  # "correlation", "bottleneck", "sequence"
    description: str
    confidence: float  # 0.0 to 1.0
    agents: List[str]
    metadata: Dict


class ExecutionTreeBuilder:
    """Build agent execution tree from executions."""

    def __init__(self, executions: List[SubagentExecution]):
        self.executions = executions
        self.tree: Dict[str, AgentNode] = {}

    def build(self) -> Dict[str, AgentNode]:
        """
        Build execution tree from executions.

        Returns:
            Dictionary mapping agent names to AgentNode objects.
            Root agents (no parent) are top-level entries.
        """
        # First pass: collect stats per agent
        agent_stats: Dict[str, Dict] = defaultdict(
            lambda: {"count": 0, "duration": 0.0, "parents": set()}
        )

        for execution in self.executions:
            stats = agent_stats[execution.agent_name]
            stats["count"] += 1
            stats["duration"] += execution.duration_ms or 0.0
            if execution.parent_agent:
                stats["parents"].add(execution.parent_agent)

        # Second pass: build nodes
        nodes: Dict[str, AgentNode] = {}
        for agent_name, stats in agent_stats.items():
            # For simplicity, use the first parent if multiple exist
            parent = list(stats["parents"])[0] if stats["parents"] else None

            node = AgentNode(
                name=agent_name,
                parent=parent,
                invocation_count=stats["count"],
                total_duration_ms=stats["duration"],
                children=[]
            )
            nodes[agent_name] = node

        # Third pass: build tree structure
        root_nodes: Dict[str, AgentNode] = {}
        for agent_name, node in nodes.items():
            if node.parent and node.parent in nodes:
                # Add to parent's children
                nodes[node.parent].add_child(node)
            else:
                # Root node
                root_nodes[agent_name] = node

        self.tree = root_nodes
        return root_nodes


class AsciiTreeRenderer:
    """Render agent execution tree as ASCII art."""

    def __init__(self):
        self.lines: List[str] = []

    def render(self, tree: Dict[str, AgentNode]) -> str:
        """
        Render tree as ASCII art.

        Args:
            tree: Dictionary of root agent nodes.

        Returns:
            Multi-line ASCII art string.
        """
        self.lines = []

        # Render each root node
        root_names = sorted(tree.keys())
        for i, root_name in enumerate(root_names):
            node = tree[root_name]
            is_last_root = (i == len(root_names) - 1)
            self._render_node(node, prefix="", is_last=is_last_root)

        return "\n".join(self.lines)

    def _render_node(self, node: AgentNode, prefix: str, is_last: bool) -> None:
        """Recursively render a node and its children."""
        # Determine connector
        connector = "└─" if is_last else "├─"

        # Format node info
        duration_str = f"{node.total_duration_seconds():.1f}s"
        node_str = f"{node.name} ({node.invocation_count} invocations, {duration_str} total)"

        # Add node line
        if prefix:
            self.lines.append(f"{prefix}{connector} {node_str}")
        else:
            # Root node
            self.lines.append(node_str)

        # Determine prefix for children
        if prefix:
            child_prefix = prefix + ("   " if is_last else "│  ")
        else:
            child_prefix = "  "

        # Render children
        sorted_children = sorted(node.children, key=lambda n: n.name)
        for i, child in enumerate(sorted_children):
            is_last_child = (i == len(sorted_children) - 1)
            self._render_node(child, child_prefix, is_last_child)


class PatternDetector:
    """Detect patterns in agent executions."""

    def __init__(self, executions: List[SubagentExecution]):
        self.executions = executions

    def detect_all(self) -> List[Pattern]:
        """
        Detect all patterns.

        Returns:
            List of detected Pattern objects.
        """
        patterns = []
        patterns.extend(self._detect_correlations())
        patterns.extend(self._detect_bottlenecks())
        patterns.extend(self._detect_sequences())
        return patterns

    def _detect_correlations(self) -> List[Pattern]:
        """Detect agent pairs that always appear together."""
        patterns = []

        # Build parent-child relationships
        parent_child_counts: Dict[Tuple[str, str], int] = defaultdict(int)
        parent_counts: Dict[str, int] = defaultdict(int)

        for execution in self.executions:
            if execution.parent_agent:
                pair = (execution.parent_agent, execution.agent_name)
                parent_child_counts[pair] += 1
                parent_counts[execution.parent_agent] += 1

        # Find high-correlation pairs (>= 80%)
        for (parent, child), count in parent_child_counts.items():
            total_parent = parent_counts[parent]
            correlation = count / total_parent if total_parent > 0 else 0.0

            if correlation >= 0.8 and count >= 2:
                patterns.append(Pattern(
                    pattern_type="correlation",
                    description=f"{parent} → {child} ({correlation*100:.0f}% correlation)",
                    confidence=correlation,
                    agents=[parent, child],
                    metadata={"count": count, "total": total_parent}
                ))

        return patterns

    def _detect_bottlenecks(self) -> List[Pattern]:
        """Detect agents with unusually long execution times."""
        patterns = []

        # Calculate mean and std dev of durations
        durations = [e.duration_seconds for e in self.executions if e.duration_seconds > 0]
        if not durations:
            return patterns

        mean_duration = sum(durations) / len(durations)

        # Find agents with duration > 2x mean
        agent_durations: Dict[str, List[float]] = defaultdict(list)
        for execution in self.executions:
            if execution.duration_seconds > 0:
                agent_durations[execution.agent_name].append(execution.duration_seconds)

        for agent_name, agent_durs in agent_durations.items():
            avg_agent_dur = sum(agent_durs) / len(agent_durs)

            if avg_agent_dur > mean_duration * 2 and len(agent_durs) >= 2:
                severity = avg_agent_dur / mean_duration
                patterns.append(Pattern(
                    pattern_type="bottleneck",
                    description=f"{agent_name} averages {avg_agent_dur:.1f}s ({severity:.1f}x slower than mean)",
                    confidence=min(severity / 5.0, 1.0),
                    agents=[agent_name],
                    metadata={"avg_duration": avg_agent_dur, "mean_duration": mean_duration}
                ))

        return patterns

    def _detect_sequences(self) -> List[Pattern]:
        """Detect common agent execution sequences."""
        patterns = []

        # Build sequences (parent -> child chains)
        sequences: Dict[Tuple[str, str, str], int] = defaultdict(int)

        # Group by parent
        children_by_parent: Dict[str, List[str]] = defaultdict(list)
        for execution in self.executions:
            if execution.parent_agent:
                children_by_parent[execution.parent_agent].append(execution.agent_name)

        # Find parent -> child1, child2 patterns
        for parent, children in children_by_parent.items():
            if len(children) >= 2:
                # Sort children to normalize sequence
                sorted_children = sorted(set(children))
                if len(sorted_children) >= 2:
                    # Create sequence key (limit to first 3 agents)
                    seq_key = tuple([parent] + sorted_children[:2])
                    sequences[seq_key] += 1

        # Report sequences that appear multiple times
        for seq, count in sequences.items():
            if count >= 2:
                seq_str = " → ".join(seq)
                patterns.append(Pattern(
                    pattern_type="sequence",
                    description=f"Common sequence: {seq_str} (appears {count} times)",
                    confidence=min(count / 5.0, 1.0),
                    agents=list(seq),
                    metadata={"count": count}
                ))

        return patterns


class ReportGenerator:
    """Generate execution reports."""

    def __init__(self, reader: MetricsReader):
        self.reader = reader

    def generate_text_report(
        self,
        session_id: Optional[str] = None,
        agent_filter: Optional[str] = None
    ) -> str:
        """
        Generate comprehensive text report.

        Args:
            session_id: Filter by session ID. If None, uses latest session.
            agent_filter: Filter by agent name. If None, includes all agents.

        Returns:
            Multi-line text report.
        """
        # Determine session
        if session_id is None:
            session_id = self.reader.get_latest_session_id()
            if session_id is None:
                return "No sessions found in metrics."

        # Get executions
        executions = self.reader.build_executions(session_id=session_id)
        if agent_filter:
            executions = [e for e in executions if e.agent_name == agent_filter]

        if not executions:
            return f"No executions found for session: {session_id}"

        # Build sections
        sections = []

        # Header
        sections.append(f"Subagent Execution Map - Session: {session_id}")
        sections.append("=" * 64)
        sections.append("")

        # Agent Invocation Tree
        tree_builder = ExecutionTreeBuilder(executions)
        tree = tree_builder.build()
        renderer = AsciiTreeRenderer()
        tree_str = renderer.render(tree)

        sections.append("Agent Invocation Tree:")
        sections.append(tree_str)
        sections.append("")

        # Performance Summary
        stats = self.reader.get_agent_stats(session_id=session_id, agent_name=agent_filter)

        sections.append("Performance Summary:")
        sections.append(f"  Total agents invoked: {len(stats['agents'])}")
        sections.append(f"  Total execution time: {stats['total_duration_ms']/1000:.1f}s")

        if stats['agents']:
            most_used = max(stats['agents'].items(), key=lambda x: x[1])
            sections.append(f"  Most used agent: {most_used[0]} ({most_used[1]} times)")

        if stats['avg_duration_ms'] > 0:
            sections.append(f"  Average execution time: {stats['avg_duration_ms']/1000:.1f}s")

        sections.append("")

        # Patterns Detected
        detector = PatternDetector(executions)
        patterns = detector.detect_all()

        if patterns:
            sections.append("Patterns Detected:")
            for pattern in patterns:
                sections.append(f"  - {pattern.description}")
        else:
            sections.append("Patterns Detected:")
            sections.append("  - No significant patterns detected")

        sections.append("")

        return "\n".join(sections)

    def generate_json_report(
        self,
        session_id: Optional[str] = None,
        agent_filter: Optional[str] = None
    ) -> Dict:
        """
        Generate JSON report.

        Args:
            session_id: Filter by session ID. If None, uses latest session.
            agent_filter: Filter by agent name. If None, includes all agents.

        Returns:
            Dictionary with report data.
        """
        # Determine session
        if session_id is None:
            session_id = self.reader.get_latest_session_id()
            if session_id is None:
                return {"error": "No sessions found"}

        # Get executions
        executions = self.reader.build_executions(session_id=session_id)
        if agent_filter:
            executions = [e for e in executions if e.agent_name == agent_filter]

        if not executions:
            return {"error": f"No executions found for session: {session_id}"}

        # Build tree
        tree_builder = ExecutionTreeBuilder(executions)
        tree = tree_builder.build()

        # Get stats
        stats = self.reader.get_agent_stats(session_id=session_id, agent_name=agent_filter)

        # Detect patterns
        detector = PatternDetector(executions)
        patterns = detector.detect_all()

        return {
            "session_id": session_id,
            "executions": [
                {
                    "agent_name": e.agent_name,
                    "parent_agent": e.parent_agent,
                    "start_time": e.start_time.isoformat(),
                    "duration_seconds": e.duration_seconds,
                    "execution_id": e.execution_id
                }
                for e in executions
            ],
            "tree": self._tree_to_dict(tree),
            "stats": stats,
            "patterns": [
                {
                    "type": p.pattern_type,
                    "description": p.description,
                    "confidence": p.confidence,
                    "agents": p.agents
                }
                for p in patterns
            ]
        }

    def _tree_to_dict(self, tree: Dict[str, AgentNode]) -> List[Dict]:
        """Convert tree to dictionary representation."""
        result = []
        for node in tree.values():
            result.append(self._node_to_dict(node))
        return result

    def _node_to_dict(self, node: AgentNode) -> Dict:
        """Convert node to dictionary representation."""
        return {
            "name": node.name,
            "invocation_count": node.invocation_count,
            "total_duration_seconds": node.total_duration_seconds(),
            "children": [self._node_to_dict(child) for child in node.children]
        }
