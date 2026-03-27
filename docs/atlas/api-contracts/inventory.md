# API Contracts Inventory

## CLI Commands (amplihack <command>)

| Command          | Subcommand  | Handler                                           | Key Arguments                                                 |
| ---------------- | ----------- | ------------------------------------------------- | ------------------------------------------------------------- |
| (none)           | -           | `launch_command`                                  | Default launch                                                |
| `install`        | -           | `install.copytree_manifest`                       | -                                                             |
| `uninstall`      | -           | `uninstall.uninstall`                             | -                                                             |
| `update`         | -           | `auto_update.update`                              | Delegates to Rust CLI                                         |
| `version`        | -           | prints `__version__`                              | -                                                             |
| `launch`         | -           | `launch_command`                                  | `--docker`, `--checkout-repo`                                 |
| `launch`         | (auto)      | `launcher.auto_mode.AutoMode.run`                 | `--auto`, `--max-turns N`, `--append PROMPT`, `--ui`          |
| `claude`         | -           | `launch_command` (alias)                          | Same as launch                                                |
| `RustyClawd`     | -           | `launch_command` (Rust path)                      | Same as launch                                                |
| `copilot`        | -           | `launcher.copilot.launch_copilot`                 | `--auto`, `--max-turns`                                       |
| `codex`          | -           | `launcher.codex.launch_codex`                     | `--auto`, `--max-turns`                                       |
| `amplifier`      | -           | `launcher.amplifier.launch_amplifier`             | `--auto`, `--max-turns`                                       |
| `plugin`         | `install`   | `plugin_cli.plugin_install_command`               | `<source>`, `--force`                                         |
| `plugin`         | `uninstall` | `plugin_cli.plugin_uninstall_command`             | `<plugin_name>`                                               |
| `plugin`         | `link`      | `plugin_cli.plugin_link_command`                  | `[plugin_name]`                                               |
| `plugin`         | `verify`    | `plugin_cli.plugin_verify_command`                | `[plugin_name]`                                               |
| `memory`         | `tree`      | `memory.cli_visualize`                            | `--session`, `--type`, `--depth`                              |
| `memory`         | `export`    | `agents.goal_seeking.memory_export.export_memory` | `--agent`, `--output`, `--format`, `--storage-path`           |
| `memory`         | `import`    | `agents.goal_seeking.memory_export.import_memory` | `--agent`, `--input`, `--format`, `--merge`, `--storage-path` |
| `recipe`         | `run`       | `recipes.rust_runner`                             | `<path>`, `-c KEY=VALUE`, `--dry-run`, `-w DIR`               |
| `recipe`         | `list`      | `recipes.discovery`                               | `[dir]`, `-t TAG`, `-f FORMAT`                                |
| `recipe`         | `validate`  | `recipes.parser`                                  | `<path>`                                                      |
| `recipe`         | `show`      | `recipes.parser`                                  | `<path>`, `--no-steps`, `--no-context`                        |
| `new`            | -           | `goal_agent_generator.cli`                        | `-f FILE`, `-o DIR`, `--sdk TYPE`, `--multi-agent`            |
| `mode`           | `detect`    | `mode_detector`                                   | -                                                             |
| `mode`           | `to-plugin` | `mode_detector`                                   | -                                                             |
| `mode`           | `to-local`  | `mode_detector`                                   | -                                                             |
| `fleet`          | (various)   | `fleet.fleet_cli` (Click)                         | Delegates to Click CLI                                        |
| `uvx-help`       | -           | inline                                            | `--find-path`, `--info`                                       |
| `_local_install` | -           | `install._local_install`                          | `<repo_root>` (hidden)                                        |

## Hook Events

| Hook           | Trigger     | Handler                           | Purpose                  |
| -------------- | ----------- | --------------------------------- | ------------------------ |
| `stop`         | Session end | `hooks.manager.execute_stop_hook` | Cleanup, reflection      |
| `XPIA defense` | Web fetch   | `security.xpia_hooks.xpia_hook`   | Injection attack defense |

## Common SDK Arguments (shared across launch/claude/copilot/codex/amplifier)

| Argument            | Type   | Default | Description                                |
| ------------------- | ------ | ------- | ------------------------------------------ |
| `--auto`            | flag   | false   | Autonomous agentic mode                    |
| `--max-turns`       | int    | 10      | Max turns for auto mode                    |
| `--append`          | string | -       | Inject instructions into running auto mode |
| `--ui`              | flag   | false   | Interactive UI for auto mode               |
| `--no-reflection`   | flag   | false   | Disable post-session reflection            |
| `--subprocess-safe` | flag   | false   | Skip staging/env mutations                 |

## Claude-Specific Arguments (launch/claude/RustyClawd only)

| Argument          | Type | Description                      |
| ----------------- | ---- | -------------------------------- |
| `--checkout-repo` | URI  | Clone GitHub repo as working dir |
| `--docker`        | flag | Run in Docker container          |
