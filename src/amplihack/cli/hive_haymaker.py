"""amplihack haymaker CLI extensions for the hive-mind workload.

Registers two sub-commands under the ``haymaker hive`` group:

    haymaker hive feed --deployment-id ID --turns N
        Publishes N LEARN_CONTENT events then a FEED_COMPLETE sentinel.
        Replaces: python feed_content.py --turns N

    haymaker hive eval --deployment-id ID --repeats N [--wait-for-ready M]
        Waits for M AGENT_READY events (event-driven, no sleep timers), then
        runs N question rounds and prints answers.
        Replaces: python query_hive.py

These commands are registered as a Click plugin via the entry-point:
    [project.entry-points."agent_haymaker.cli_extensions"]
    hive = "amplihack.cli.hive_haymaker:hive_group"

The ``haymaker`` CLI auto-discovers extensions via this entry-point group,
adding them as sub-groups of the top-level ``haymaker`` command.
"""

from __future__ import annotations

import asyncio
import json
import sys

try:
    import click
except ImportError:  # pragma: no cover
    click = None  # type: ignore[assignment]


def _require_click() -> None:
    if click is None:
        raise RuntimeError("click is required. Install with: pip install click")


# ---------------------------------------------------------------------------
# hive group
# ---------------------------------------------------------------------------

if click is not None:

    @click.group("hive")
    def hive_group() -> None:
        """Hive-mind workload commands (feed content, run eval)."""

    @hive_group.command("feed")
    @click.option("--deployment-id", required=True, help="Hive deployment ID.")
    @click.option("--turns", default=100, show_default=True, type=int, help="Number of LEARN_CONTENT events to send.")
    @click.option("--topic", default=None, help="Override Service Bus topic name.")
    @click.option("--sb-conn-str", envvar="AMPLIHACK_MEMORY_CONNECTION_STRING", default="", help="Service Bus connection string (env: AMPLIHACK_MEMORY_CONNECTION_STRING).")
    def hive_feed(deployment_id: str, turns: int, topic: str | None, sb_conn_str: str) -> None:
        """Feed learning content into the hive.

        Publishes TURNS LEARN_CONTENT events followed by a FEED_COMPLETE
        sentinel to the Service Bus topic.  Agents subscribed to the topic
        will ingest and learn the content.

        Replaces: python deploy/azure_hive/feed_content.py --turns N
        """
        import os

        from amplihack.workloads.hive._feed import run_feed

        resolved_topic = topic or os.environ.get("AMPLIHACK_TOPIC_NAME", "hive-graph")

        click.echo(f"Feeding {turns} turns into deployment {deployment_id} (topic={resolved_topic})")
        try:
            asyncio.run(
                run_feed(
                    deployment_id=deployment_id,
                    turns=turns,
                    topic_name=resolved_topic,
                    sb_conn_str=sb_conn_str,
                )
            )
            click.echo(f"Done. {turns} LEARN_CONTENT + 1 FEED_COMPLETE sent.")
        except KeyboardInterrupt:
            click.echo("Interrupted.")
            sys.exit(0)
        except Exception as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

    @hive_group.command("eval")
    @click.option("--deployment-id", required=True, help="Hive deployment ID.")
    @click.option("--repeats", default=3, show_default=True, type=int, help="Number of question rounds.")
    @click.option("--wait-for-ready", default=0, show_default=True, type=int, help="Number of AGENT_READY events to wait for before starting eval (0 = skip wait).")
    @click.option("--timeout", default=600, show_default=True, type=int, help="Max seconds to wait for agents to become ready.")
    @click.option("--topic", default=None, help="Override Service Bus topic name.")
    @click.option("--sb-conn-str", envvar="AMPLIHACK_MEMORY_CONNECTION_STRING", default="", help="Service Bus connection string (env: AMPLIHACK_MEMORY_CONNECTION_STRING).")
    @click.option("--output", default="text", type=click.Choice(["text", "json"]), help="Output format.")
    def hive_eval(
        deployment_id: str,
        repeats: int,
        wait_for_ready: int,
        timeout: int,
        topic: str | None,
        sb_conn_str: str,
        output: str,
    ) -> None:
        """Evaluate hive agent knowledge.

        Optionally waits for WAIT_FOR_READY AGENT_READY events (event-driven,
        no sleep timers), then runs REPEATS question rounds and prints results.

        Replaces: python experiments/hive_mind/query_hive.py

        Examples:

            # Wait for all 100 agents, then run 5 question rounds
            haymaker hive eval --deployment-id abc123 --repeats 5 --wait-for-ready 100

            # Skip the wait and run 3 rounds immediately
            haymaker hive eval --deployment-id abc123 --repeats 3
        """
        import os

        from amplihack.workloads.hive._eval import run_eval

        resolved_topic = topic or os.environ.get("AMPLIHACK_TOPIC_NAME", "hive-graph")

        if wait_for_ready > 0:
            click.echo(
                f"Waiting for {wait_for_ready} agents to signal AGENT_READY "
                f"(timeout={timeout}s)..."
            )
        click.echo(f"Running {repeats} eval rounds against deployment {deployment_id}")

        try:
            results = asyncio.run(
                run_eval(
                    deployment_id=deployment_id,
                    repeats=repeats,
                    wait_for_ready=wait_for_ready,
                    timeout_seconds=timeout,
                    sb_conn_str=sb_conn_str,
                    topic_name=resolved_topic,
                )
            )
        except KeyboardInterrupt:
            click.echo("Interrupted.")
            sys.exit(0)
        except Exception as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

        if output == "json":
            click.echo(json.dumps(results, indent=2))
        else:
            for i, result in enumerate(results, 1):
                click.echo(f"\n--- Round {i} ---")
                click.echo(f"Q: {result['question']}")
                answers = result.get("answers", [])
                if answers:
                    for ans in answers:
                        click.echo(f"  [{ans['agent']}] {ans['answer']}")
                else:
                    click.echo("  (no responses received)")

else:
    # click not available — define stub so imports don't fail at load time
    class hive_group:  # type: ignore[no-redef]
        """Stub when click is not installed."""

        @staticmethod
        def main() -> None:
            print("click is required: pip install click", file=sys.stderr)
            sys.exit(1)


__all__ = ["hive_group"]
