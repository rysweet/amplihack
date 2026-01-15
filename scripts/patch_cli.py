#!/usr/bin/env python3
"""Patch CLI to add command handlers."""

from pathlib import Path

# Find the insertion point (before "else:")
cli_path = Path("src/amplihack/cli.py")
content = cli_path.read_text()

# Find the last "else:" clause that handles unrecognized commands
lines = content.split('\n')

# Find the line with "    else:" that's at the end (before if __name__)
else_index = None
for i in range(len(lines) - 1, -1, -1):
    if lines[i] == "    else:":
        # Check if this is followed by create_parser().print_help()
        if i + 1 < len(lines) and "create_parser().print_help()" in lines[i + 1]:
            else_index = i
            break

if else_index is None:
    print("Could not find insertion point")
    exit(1)

print(f"Found insertion point at line {else_index + 1}")

# Insert the new handlers before the else clause
new_handlers = '''    elif args.command == "sync-commands":
        from pathlib import Path
        from .adapters.copilot_command_converter import convert_commands

        if args.dry_run:
            print("Dry-run mode: No files will be modified\\n")

        try:
            report = convert_commands(
                source_dir=Path(".claude/commands"),
                target_dir=Path(".github/commands"),
                force=args.force
            )

            print(f"\\nCommand Conversion Summary:")
            print(f"  Total commands: {report.total}")
            print(f"  {EMOJI['check']} Succeeded: {report.succeeded}")
            if report.failed > 0:
                print(f"  ✗ Failed: {report.failed}")
            if report.skipped > 0:
                print(f"  ⊘ Skipped: {report.skipped}")

            if report.errors:
                print(f"\\nErrors:")
                for error in report.errors:
                    print(f"  {error}")

            if args.verbose:
                print(f"\\nDetailed Results:")
                for conversion in report.conversions:
                    status_icon = {
                        "success": EMOJI['check'],
                        "failed": "✗",
                        "skipped": "⊘"
                    }[conversion.status]
                    print(f"  {status_icon} {conversion.command_name} - {conversion.status}")
                    if conversion.reason:
                        print(f"     Reason: {conversion.reason}")

            if report.succeeded > 0:
                print(f"\\nNext steps:")
                print(f"  1. Review converted commands in .github/commands/")
                print(f"  2. Check .github/commands/COMMANDS_REGISTRY.json")
                print(f"  3. Use: amplihack copilot-command amplihack/ultrathink 'task'")

            return 0 if report.failed == 0 else 1

        except (FileNotFoundError, PermissionError) as e:
            print(f"Error: {str(e)}")
            return 1
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            return 1

    elif args.command == "copilot-command":
        from .copilot.command_wrapper import invoke_copilot_command

        try:
            result = invoke_copilot_command(
                command_name=args.command_name,
                args=args.args,
                timeout=args.timeout
            )

            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)

            return result.returncode

        except FileNotFoundError as e:
            print(f"Error: {str(e)}")
            return 1
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return 1

    elif args.command == "list-commands":
        from pathlib import Path
        from .copilot.command_wrapper import list_available_commands
        import json

        try:
            commands = list_available_commands()

            if not commands:
                print("No commands found. Run 'amplihack sync-commands' first.")
                return 1

            registry_path = Path(".github/commands/COMMANDS_REGISTRY.json")
            registry = {}
            if registry_path.exists():
                registry_data = json.loads(registry_path.read_text())
                registry = {cmd['name']: cmd for cmd in registry_data['commands']}

            if args.category:
                commands = [
                    cmd for cmd in commands
                    if registry.get(cmd, {}).get('category') == args.category
                ]

            print(f"\\nAvailable Copilot Commands ({len(commands)} total):")
            print("=" * 70)

            by_category = {}
            for cmd in commands:
                cmd_data = registry.get(cmd, {})
                category = cmd_data.get('category', 'unknown')
                if category not in by_category:
                    by_category[category] = []
                by_category[category].append((cmd, cmd_data.get('description', '')))

            for category in sorted(by_category.keys()):
                print(f"\\n{category.upper()}:")
                for cmd, desc in sorted(by_category[category]):
                    print(f"  {cmd}")
                    if desc:
                        print(f"    {desc}")

            print("\\nUsage:")
            print("  amplihack copilot-command <command-name> [args...]")
            print("\\nExample:")
            print("  amplihack copilot-command amplihack/ultrathink 'analyze code'")

            return 0

        except Exception as e:
            print(f"Error: {str(e)}")
            return 1

'''

# Insert the new handlers
lines.insert(else_index, new_handlers)

# Write the patched file
cli_path.write_text('\n'.join(lines))

print("Successfully patched cli.py")
print("Added 3 command handlers: sync-commands, copilot-command, list-commands")
