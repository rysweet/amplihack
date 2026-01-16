"""CLI command handlers for Copilot agent integration.

This module provides command handlers that can be called from cli.py's main() function.
"""

from .agent_wrapper import invoke_copilot_agent, list_agents
from .formatters import OutputFormatter


def handle_copilot_agent(args) -> int:
    """Handle the copilot-agent command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    formatter = OutputFormatter()

    # Handle --list flag
    if args.list:
        try:
            agents = list_agents()

            if not agents:
                print(formatter.warning("No agents found. Run 'amplihack sync-agents' first."))
                return 1

            print(formatter.info(f"Available Copilot Agents ({len(agents)} total):"))
            print("=" * 70)

            if args.verbose:
                # Detailed view
                for agent in agents:
                    print(f"\n{formatter.success(agent.name)}")
                    print(f"  Path: {agent.path}")
                    if agent.description:
                        print(f"  Description: {agent.description}")
                    if agent.tags:
                        print(f"  Tags: {', '.join(agent.tags)}")
            else:
                # Simple list
                for agent in agents:
                    desc = agent.description[:60] + "..." if len(agent.description) > 60 else agent.description
                    print(f"  {agent.name:<25} {desc}")

            print("\nUsage:")
            print("  amplihack copilot-agent <agent-name> 'task description'")
            print("\nExample:")
            print("  amplihack copilot-agent architect 'Design authentication system'")

            return 0

        except Exception as e:
            print(formatter.error(f"Error listing agents: {str(e)}"))
            return 1

    # Validate arguments
    if not args.agent_name or not args.task:
        print(formatter.error("Error: Both agent_name and task are required"))
        print("Usage: amplihack copilot-agent <agent-name> 'task description'")
        print("   Or: amplihack copilot-agent --list")
        return 1

    # Invoke agent
    try:
        print(formatter.progress(f"Invoking {args.agent_name} agent..."))

        result = invoke_copilot_agent(
            args.agent_name,
            args.task,
            additional_files=args.files,
            verbose=args.verbose,
        )

        if result.success:
            print(formatter.success(f"Agent {args.agent_name} completed successfully"))
            print("\nOutput:")
            print("-" * 70)
            print(result.output)
            return 0
        else:
            print(formatter.error(f"Agent {args.agent_name} failed (exit code {result.exit_code})"))
            if result.error:
                print("\nError output:")
                print(result.error)
            return result.exit_code

    except Exception as e:
        print(formatter.error(f"Error invoking agent: {str(e)}"))
        return 1


def handle_list_copilot_agents(args) -> int:
    """Handle the list-copilot-agents command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    formatter = OutputFormatter()

    try:
        agents = list_agents()

        if not agents:
            print(formatter.warning("No agents found. Run 'amplihack sync-agents' first."))
            return 1

        print(formatter.info(f"Available Copilot Agents ({len(agents)} total):"))
        print("=" * 70)

        if args.verbose:
            # Detailed view with all metadata
            for agent in agents:
                print(f"\n{formatter.success(agent.name)}")
                print(f"  Path: {agent.path}")
                if agent.description:
                    print(f"  Description: {agent.description}")
                if agent.tags:
                    print(f"  Tags: {', '.join(agent.tags)}")
        else:
            # Simple list with descriptions
            for agent in agents:
                desc = agent.description[:60] + "..." if len(agent.description) > 60 else agent.description
                print(f"  {agent.name:<25} {desc}")

        print("\nUsage:")
        print("  amplihack copilot-agent <agent-name> 'task description'")
        print("\nExample:")
        print("  amplihack copilot-agent architect 'Design authentication system'")

        return 0

    except Exception as e:
        print(formatter.error(f"Error listing agents: {str(e)}"))
        return 1


__all__ = ["handle_copilot_agent", "handle_list_copilot_agents"]
