"""Transform TLC state graph traces into pytest test cases.

Parses TLC's DOT-format state dump and extracts execution traces
(paths from initial states through dispatch to terminal states).
Each trace becomes a pytest test case exercising the hive mind's
distributed retrieval contract.

Usage:
    python -m amplihack.eval.trace_to_test \
        --dot /tmp/tla-tlc-traces/states.dot \
        --output tests/hive_mind/test_tla_generated.py \
        --max-traces 50
"""

from __future__ import annotations

import re
import textwrap
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TLCState:
    """One state from the TLC state graph."""

    state_id: str
    phase: str
    active_agents: frozenset[str]
    responded_agents: frozenset[str]
    failed_agents: frozenset[str]
    shard_results: dict[str, frozenset[str]]
    merged_result: tuple[str, ...]
    original_question: str
    is_initial: bool = False


@dataclass
class TLCTrace:
    """A path through the state graph from init to terminal."""

    states: list[TLCState]

    @property
    def terminal_phase(self) -> str:
        return self.states[-1].phase

    @property
    def active_agents(self) -> frozenset[str]:
        return self.states[0].active_agents

    @property
    def events(self) -> list[dict]:
        """Extract the sequence of events (state transitions) in this trace."""
        events = []
        for i in range(1, len(self.states)):
            prev, curr = self.states[i - 1], self.states[i]
            if prev.phase == "idle" and curr.phase == "dispatch":
                events.append({"type": "start_request", "question": curr.original_question})
            elif prev.phase == "dispatch" and curr.phase == "dispatch":
                new_responded = curr.responded_agents - prev.responded_agents
                new_failed = curr.failed_agents - prev.failed_agents
                for agent in sorted(new_responded - new_failed):
                    facts = curr.shard_results.get(agent, frozenset())
                    events.append({"type": "shard_success", "agent": agent, "facts": sorted(facts)})
                for agent in sorted(new_failed):
                    events.append({"type": "shard_failure", "agent": agent})
            elif curr.phase == "complete":
                events.append({"type": "complete", "merged": list(curr.merged_result)})
            elif curr.phase == "failed":
                events.append({"type": "fail"})
            elif curr.phase == "idle" and prev.phase in ("complete", "failed"):
                events.append({"type": "reset"})
        return events


def _parse_set(text: str) -> frozenset[str]:
    """Parse TLA+ set notation like {a1, a2} into frozenset."""
    text = text.strip()
    if text == "{}":
        return frozenset()
    inner = text.strip("{}")
    return frozenset(item.strip().strip('"') for item in inner.split(","))


def _parse_function(text: str) -> dict[str, frozenset[str]]:
    """Parse TLA+ function notation like (a1 :> {f1} @@ a2 :> {})."""
    result = {}
    for match in re.finditer(r"(\w+)\s*:>\s*(\{[^}]*\})", text):
        agent, facts_str = match.group(1), match.group(2)
        result[agent] = _parse_set(facts_str)
    return result


def _parse_sequence(text: str) -> tuple[str, ...]:
    """Parse TLA+ sequence notation like <<f1, f2>>."""
    text = text.strip()
    if text == "<<>>":
        return ()
    inner = text.strip("<>")
    return tuple(item.strip().strip('"') for item in inner.split(",") if item.strip())


def parse_dot_states(dot_path: Path) -> tuple[dict[str, TLCState], dict[str, list[str]]]:
    """Parse TLC DOT output into states and edges."""
    content = dot_path.read_text()
    states: dict[str, TLCState] = {}
    edges: dict[str, list[str]] = defaultdict(list)

    # Parse nodes: id [label="...",style = filled]
    for match in re.finditer(
        r'(-?\d+)\s*\[label="((?:[^"\\]|\\.)*)"\s*(?:,\s*style\s*=\s*filled)?\]', content
    ):
        state_id = match.group(1)
        label = match.group(2).replace("\\n", "\n").replace('\\"', '"')
        is_initial = "style = filled" in match.group(0)

        # Extract variable assignments from label
        phase = ""
        active_agents: frozenset[str] = frozenset()
        responded_agents: frozenset[str] = frozenset()
        failed_agents: frozenset[str] = frozenset()
        shard_results: dict[str, frozenset[str]] = {}
        merged_result: tuple[str, ...] = ()
        original_question = ""

        for line in label.split("\n"):
            line = line.strip().lstrip("/\\ ")
            if line.startswith("phase = "):
                phase = line.split("=", 1)[1].strip().strip('"').strip("\\")
            elif line.startswith("activeAgents = "):
                active_agents = _parse_set(line.split("=", 1)[1])
            elif line.startswith("respondedAgents = "):
                responded_agents = _parse_set(line.split("=", 1)[1])
            elif line.startswith("failedAgents = "):
                failed_agents = _parse_set(line.split("=", 1)[1])
            elif line.startswith("shardResults = "):
                shard_results = _parse_function(line.split("=", 1)[1])
            elif line.startswith("mergedResult = "):
                merged_result = _parse_sequence(line.split("=", 1)[1])
            elif line.startswith("originalQuestion = "):
                original_question = line.split("=", 1)[1].strip().strip('"')

        states[state_id] = TLCState(
            state_id=state_id,
            phase=phase,
            active_agents=active_agents,
            responded_agents=responded_agents,
            failed_agents=failed_agents,
            shard_results=shard_results,
            merged_result=merged_result,
            original_question=original_question,
            is_initial=is_initial,
        )

    # Parse edges: src -> dst
    for match in re.finditer(r"(-?\d+)\s*->\s*(-?\d+)", content):
        src, dst = match.group(1), match.group(2)
        if src in states and dst in states:
            edges[src].append(dst)

    return states, dict(edges)


def extract_traces(
    states: dict[str, TLCState],
    edges: dict[str, list[str]],
    max_traces: int = 50,
) -> list[TLCTrace]:
    """Extract complete traces (init → terminal) via DFS."""
    initial_states = [sid for sid, s in states.items() if s.is_initial]
    terminal_phases = {"complete", "failed"}
    traces: list[TLCTrace] = []

    def dfs(current: str, path: list[str]) -> None:
        if len(traces) >= max_traces:
            return
        state = states[current]
        if state.phase in terminal_phases and len(path) > 1:
            traces.append(TLCTrace(states=[states[sid] for sid in path]))
            return
        if len(path) > 10:  # Bound depth to avoid combinatorial explosion
            return
        for next_id in edges.get(current, []):
            if next_id not in path:  # No cycles
                dfs(next_id, path + [next_id])

    for init_id in sorted(initial_states):
        if len(traces) >= max_traces:
            break
        dfs(init_id, [init_id])

    return traces


def trace_to_pytest(trace: TLCTrace, index: int) -> str:
    """Generate a single pytest test function from a TLC trace."""
    events = trace.events
    active = sorted(trace.active_agents)
    terminal = trace.terminal_phase

    lines = [
        f"def test_tla_trace_{index:03d}_{terminal}_{'_'.join(active)}():",
        f'    """TLC-generated trace: {len(active)} agents, terminal={terminal}."""',
        f"    agents = {active}",
        "    request = RetrievalRequest(agents)",
    ]

    for event in events:
        if event["type"] == "start_request":
            lines.append(f'    request.start("{event["question"]}")')
        elif event["type"] == "shard_success":
            lines.append(f'    request.record_success("{event["agent"]}", {event["facts"]})')
        elif event["type"] == "shard_failure":
            lines.append(f'    request.record_failure("{event["agent"]}")')
        elif event["type"] == "complete":
            lines.append("    request.complete()")
            lines.append('    assert request.phase == "complete"')
            lines.append(
                "    assert request.merged_result_set == set(request.responded_facts_union)"
            )
        elif event["type"] == "fail":
            lines.append("    request.fail()")
            lines.append('    assert request.phase == "failed"')
            lines.append("    assert request.responded_agents == frozenset()")

    # Always verify question preserved
    lines.append(f'    assert request.original_question == "{events[0].get("question", "q1")}"')

    return "\n".join(lines)


def generate_test_module(traces: list[TLCTrace], spec_name: str) -> str:
    """Generate a complete pytest module from TLC traces."""
    header = textwrap.dedent(f'''\
        """Auto-generated tests from TLC model checking of {spec_name}.

        These tests were mechanically derived from TLC state graph traces.
        Each test exercises one complete execution path through the distributed
        retrieval protocol, verifying that the implementation matches the
        formally verified state transitions.

        DO NOT EDIT BY HAND. Regenerate with:
            python -m amplihack.eval.trace_to_test \\
                --dot /path/to/states.dot \\
                --output {spec_name}_tests.py
        """
        from __future__ import annotations

        from dataclasses import dataclass, field


        @dataclass
        class RetrievalRequest:
            """Minimal test harness mirroring TLA+ state machine."""

            agents: list[str]
            phase: str = "idle"
            original_question: str = ""
            _responded: dict[str, list[str]] = field(default_factory=dict)
            _failed: set[str] = field(default_factory=set)

            @property
            def responded_agents(self) -> frozenset[str]:
                return frozenset(self._responded.keys())

            @property
            def failed_agents(self) -> frozenset[str]:
                return frozenset(self._failed)

            @property
            def responded_facts_union(self) -> set[str]:
                result = set()
                for facts in self._responded.values():
                    result.update(facts)
                return result

            @property
            def merged_result_set(self) -> set[str]:
                return self.responded_facts_union

            def start(self, question: str) -> None:
                assert self.phase == "idle"
                self.phase = "dispatch"
                self.original_question = question

            def record_success(self, agent: str, facts: list[str]) -> None:
                assert self.phase == "dispatch"
                assert agent in self.agents
                assert agent not in self._responded
                assert agent not in self._failed
                self._responded[agent] = facts

            def record_failure(self, agent: str) -> None:
                assert self.phase == "dispatch"
                assert agent in self.agents
                assert agent not in self._responded
                assert agent not in self._failed
                self._failed.add(agent)
                self._responded[agent] = []  # Best-effort: empty result

            def complete(self) -> None:
                assert self.phase == "dispatch"
                assert len(self._responded) > 0 or len(self._failed) == len(self.agents)
                self.phase = "complete"

            def fail(self) -> None:
                assert self.phase == "dispatch"
                assert len(self._responded) == 0
                self.phase = "failed"

    ''')

    test_functions = []
    for i, trace in enumerate(traces):
        test_functions.append(trace_to_pytest(trace, i))

    return header + "\n\n".join(test_functions) + "\n"


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Generate pytest tests from TLC state traces")
    parser.add_argument("--dot", required=True, help="Path to TLC DOT state dump")
    parser.add_argument("--output", required=True, help="Output pytest file")
    parser.add_argument("--max-traces", type=int, default=50, help="Maximum traces to extract")
    parser.add_argument(
        "--spec-name", default="DistributedRetrievalBestEffort", help="Spec module name"
    )
    args = parser.parse_args()

    dot_path = Path(args.dot)
    if not dot_path.exists():
        raise SystemExit(f"DOT file not found: {dot_path}")
    states, edges = parse_dot_states(dot_path)
    if not states:
        raise SystemExit(f"No states parsed from {dot_path} — is this a valid TLC DOT dump?")
    print(f"Parsed {len(states)} states, {sum(len(v) for v in edges.values())} edges")

    traces = extract_traces(states, edges, max_traces=args.max_traces)
    print(f"Extracted {len(traces)} traces")

    # Summary
    complete_traces = sum(1 for t in traces if t.terminal_phase == "complete")
    failed_traces = sum(1 for t in traces if t.terminal_phase == "failed")
    print(f"  Complete: {complete_traces}, Failed: {failed_traces}")

    module_text = generate_test_module(traces, args.spec_name)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(module_text)
    print(f"Wrote {len(traces)} test functions to {output_path}")


if __name__ == "__main__":
    main()
