# CLI Integration Guide for Copilot Agent Commands

This guide shows how to integrate the new copilot-agent commands into cli.py's main() function.

## Integration Required

The command parsers have already been added to `create_parser()` in cli.py (lines 502-551).

You need to add the command handlers to the `main()` function.

## Step 1: Add Import (if not already present)

No additional imports needed - handlers are in `copilot/cli_handlers.py`.

## Step 2: Add Command Handlers to main()

Add these handlers to the `main()` function in cli.py, **before the final `else:` block**:

```python
    elif args.command == "copilot-agent":
        from .copilot.cli_handlers import handle_copilot_agent
        return handle_copilot_agent(args)

    elif args.command == "list-copilot-agents":
        from .copilot.cli_handlers import handle_list_copilot_agents
        return handle_list_copilot_agents(args)

    else:
        create_parser().print_help()
        return 1
```

## Complete Example

Here's how the end of main() should look:

```python
def main(argv: list[str] | None = None) -> int:
    # ... existing code ...

    elif args.command == "list-commands":
        # ... existing list-commands handler ...

    elif args.command == "copilot-agent":
        from .copilot.cli_handlers import handle_copilot_agent
        return handle_copilot_agent(args)

    elif args.command == "list-copilot-agents":
        from .copilot.cli_handlers import handle_list_copilot_agents
        return handle_list_copilot_agents(args)

    else:
        create_parser().print_help()
        return 1
```

## Verification

After integration, test with:

```bash
# Test help
amplihack copilot-agent --help
amplihack list-copilot-agents --help

# Test list functionality
amplihack list-copilot-agents

# Test agent invocation (requires sync-agents first)
amplihack sync-agents
amplihack copilot-agent architect "Design test system"
```

## Location in File

Add the handlers around line 1236 in cli.py, just before the final `else:` block.

## Files Involved

- `src/amplihack/cli.py` - Add command handlers to main()
- `src/amplihack/copilot/cli_handlers.py` - Handler implementations (already created)
- `src/amplihack/copilot/agent_wrapper.py` - Core logic (already created)

## Notes

- The command parsers are already added to `create_parser()` (lines 502-551)
- The handlers are already implemented in `copilot/cli_handlers.py`
- Just need to wire them up in `main()`
