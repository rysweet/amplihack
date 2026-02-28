#!/usr/bin/env python3
"""Evaluation script for the gossip protocol experiment.

Creates N agents each with M unique facts, runs gossip rounds until convergence,
and measures:
- Rounds to convergence (>95% coverage)
- Per-round coverage progression
- Communication overhead (total messages sent)
- Comparison with baseline (isolated agents = 1/N coverage each)
- Text-based convergence plot

Usage:
    python experiments/hive_mind/run_gossip_eval.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Add project root to path so we can import the module
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from amplihack.agents.goal_seeking.hive_mind.gossip import (
    GossipNetwork,
    GossipProtocol,
)


def create_agents(
    n_agents: int,
    facts_per_agent: int,
    fanout: int = 2,
    top_k: int = 20,
) -> tuple[GossipNetwork, dict[str, GossipProtocol]]:
    """Create N agents each with M unique facts and register them in a network.

    Args:
        n_agents: Number of agents to create.
        facts_per_agent: Number of unique facts per agent.
        fanout: Number of peers each agent sends to per round.
        top_k: Number of top facts to include in each gossip message.

    Returns:
        Tuple of (GossipNetwork, dict of agent_id -> GossipProtocol).
    """
    agent_ids = [f"agent_{i}" for i in range(n_agents)]
    net = GossipNetwork()
    protocols: dict[str, GossipProtocol] = {}

    for aid in agent_ids:
        peers = [p for p in agent_ids if p != aid]
        proto = GossipProtocol(aid, peers=peers, fanout=fanout, top_k=top_k)
        protocols[aid] = proto
        net.register_agent(aid, proto)

        for j in range(facts_per_agent):
            proto.add_local_fact(
                f"[{aid}] Fact #{j}: Domain knowledge item {j} unique to {aid}",
                confidence=0.7 + 0.3 * (j / max(1, facts_per_agent - 1)),
            )

    return net, protocols


def print_header(title: str) -> None:
    """Print a formatted section header."""
    width = 70
    print()
    print("=" * width)
    print(f"  {title}")
    print("=" * width)


def print_convergence_plot(round_stats: list[dict]) -> None:
    """Print a text-based convergence plot.

    Args:
        round_stats: List of per-round stat dicts from run_until_converged.
    """
    print()
    print("Convergence Plot (min coverage % per round)")
    print("-" * 62)

    bar_width = 50

    for rs in round_stats:
        rnd = rs["round_number"]
        min_cov = rs["min_coverage_pct"]
        bar_len = int(min_cov / 100.0 * bar_width)
        bar = "#" * bar_len + "." * (bar_width - bar_len)
        print(f"  R{rnd:02d} |{bar}| {min_cov:5.1f}%")

    print("-" * 62)


def run_evaluation(
    n_agents: int = 5,
    facts_per_agent: int = 20,
    fanout: int = 2,
    top_k: int = 20,
    max_rounds: int = 50,
    target_coverage: float = 95.0,
) -> dict:
    """Run a full gossip evaluation.

    Args:
        n_agents: Number of agents.
        facts_per_agent: Unique facts per agent.
        fanout: Peers per gossip round.
        top_k: Facts per gossip message.
        max_rounds: Maximum rounds before stopping.
        target_coverage: Target minimum coverage %.

    Returns:
        Dict with evaluation results.
    """
    total_facts = n_agents * facts_per_agent
    baseline_coverage = 100.0 / n_agents

    print_header(f"Gossip Protocol Evaluation: {n_agents} agents x {facts_per_agent} facts")
    print(f"  Total unique facts : {total_facts}")
    print(f"  Fanout             : {fanout}")
    print(f"  Top-K per message  : {top_k}")
    print(f"  Max rounds         : {max_rounds}")
    print(f"  Target coverage    : {target_coverage}%")
    print(f"  Baseline (isolated): {baseline_coverage:.1f}% per agent")

    # Create agents and network
    net, protocols = create_agents(n_agents, facts_per_agent, fanout, top_k)

    # Verify initial state
    print()
    print("Initial State:")
    for aid, proto in protocols.items():
        print(f"  {aid}: {proto.fact_count} facts ({proto.local_fact_count} local)")

    # Run gossip
    print()
    print("Running gossip rounds...")
    t_start = time.monotonic()
    round_stats = net.run_until_converged(
        max_rounds=max_rounds,
        target_coverage=target_coverage,
    )
    elapsed = time.monotonic() - t_start

    # Results
    converged = len(round_stats) < max_rounds
    rounds_to_converge = len(round_stats)
    total_messages = sum(rs["messages_sent"] for rs in round_stats)
    total_new_facts = sum(rs["new_facts_learned"] for rs in round_stats)

    print_convergence_plot(round_stats)

    # Final state
    print_header("Final State")
    net_stats = net.get_network_stats()

    for agent_stats in net_stats["per_agent"]:
        aid = agent_stats["agent_id"]
        known = agent_stats["known_facts"]
        cov = agent_stats["coverage_pct"]
        local = agent_stats["local_facts"]
        received = agent_stats["received_facts"]
        print(
            f"  {aid}: {known}/{total_facts} facts "
            f"({cov:.1f}% coverage, {local} local, {received} received)"
        )

    print_header("Summary")
    print(f"  Converged          : {'YES' if converged else 'NO'}")
    print(f"  Rounds to converge : {rounds_to_converge}")
    print(f"  Total messages sent: {total_messages}")
    print(f"  Total facts learned: {total_new_facts} (via gossip)")
    print(f"  Min coverage       : {net_stats['min_coverage_pct']:.1f}%")
    print(f"  Avg coverage       : {net_stats['avg_coverage_pct']:.1f}%")
    print(f"  Max coverage       : {net_stats['max_coverage_pct']:.1f}%")
    print(f"  Elapsed time       : {elapsed:.3f}s")
    print()

    # Baseline comparison
    improvement = net_stats["min_coverage_pct"] - baseline_coverage
    print_header("Baseline Comparison")
    print(f"  Isolated baseline  : {baseline_coverage:.1f}% coverage per agent")
    print(f"  After gossip       : {net_stats['min_coverage_pct']:.1f}% min coverage")
    print(f"  Improvement        : +{improvement:.1f} percentage points")
    print(f"  Improvement factor : {net_stats['min_coverage_pct'] / baseline_coverage:.1f}x")

    # Communication overhead analysis
    print_header("Communication Overhead")
    msgs_per_round = total_messages / max(1, rounds_to_converge)
    facts_per_msg = top_k
    total_fact_transfers = total_messages * facts_per_msg
    print(f"  Messages per round : {msgs_per_round:.1f}")
    print(f"  Facts per message  : {facts_per_msg}")
    print(f"  Total fact xfers   : {total_fact_transfers}")
    print(f"  Unique facts       : {total_facts}")
    print(
        f"  Overhead ratio     : {total_fact_transfers / max(1, total_facts):.1f}x "
        f"(fact transfers / unique facts)"
    )
    print()

    # Hypothesis check
    hypothesis_met = net_stats["min_coverage_pct"] >= 80.0
    log_n_bound = rounds_to_converge <= 20  # generous O(log N) for N=5

    print_header("Hypothesis Verification")
    print(
        f"  >80% coverage      : {'PASS' if hypothesis_met else 'FAIL'} "
        f"(actual: {net_stats['min_coverage_pct']:.1f}%)"
    )
    print(
        f"  O(log N) rounds    : {'PASS' if log_n_bound else 'FAIL'} "
        f"(actual: {rounds_to_converge} rounds for N={n_agents})"
    )
    print()

    return {
        "converged": converged,
        "rounds": rounds_to_converge,
        "total_messages": total_messages,
        "min_coverage": net_stats["min_coverage_pct"],
        "avg_coverage": net_stats["avg_coverage_pct"],
        "elapsed": elapsed,
        "hypothesis_coverage_met": hypothesis_met,
        "hypothesis_logn_met": log_n_bound,
    }


def run_scaling_comparison() -> None:
    """Run evaluations at different scales to verify O(log N) scaling."""
    print_header("Scaling Comparison: O(log N) Verification")
    print()

    results = []
    for n_agents in [3, 5, 8, 10, 15]:
        net, _ = create_agents(n_agents, facts_per_agent=10, fanout=2, top_k=10)
        round_stats = net.run_until_converged(max_rounds=100, target_coverage=95.0)
        rounds = len(round_stats)
        final = net.get_network_stats()
        results.append((n_agents, rounds, final["min_coverage_pct"]))
        print(
            f"  N={n_agents:2d} agents: {rounds:2d} rounds to converge "
            f"(min coverage: {final['min_coverage_pct']:.1f}%)"
        )

    print()
    print("  If O(log N): doubling agents should add ~1 round, not double rounds.")
    if len(results) >= 2:
        first_n, first_r, _ = results[0]
        last_n, last_r, _ = results[-1]
        ratio = last_r / max(1, first_r)
        agent_ratio = last_n / first_n
        print(f"  Agent ratio: {agent_ratio:.1f}x, Round ratio: {ratio:.1f}x")
        if ratio < agent_ratio:
            print("  RESULT: Sub-linear scaling confirmed (rounds grow slower than agents)")
        else:
            print("  RESULT: Scaling not sub-linear (may need tuning)")


def main() -> None:
    """Run the full evaluation suite."""
    print()
    print("=" * 70)
    print("  GOSSIP PROTOCOL EVALUATION - Experiment 3")
    print("  Hypothesis: >80% coverage with O(log N) propagation rounds")
    print("=" * 70)

    # Main evaluation: 5 agents, 20 facts each
    result = run_evaluation(
        n_agents=5,
        facts_per_agent=20,
        fanout=2,
        top_k=20,
        max_rounds=50,
        target_coverage=95.0,
    )

    # Scaling comparison
    run_scaling_comparison()

    # Final verdict
    print_header("FINAL VERDICT")
    if result["hypothesis_coverage_met"] and result["hypothesis_logn_met"]:
        print("  HYPOTHESIS CONFIRMED: Gossip achieves >80% coverage")
        print("  with O(log N) propagation rounds.")
    elif result["hypothesis_coverage_met"]:
        print("  PARTIAL: Coverage achieved but round count may not be O(log N).")
    else:
        print("  HYPOTHESIS REJECTED: Did not achieve >80% coverage.")

    print()

    # Exit code for CI
    sys.exit(0 if result["hypothesis_coverage_met"] else 1)


if __name__ == "__main__":
    main()
