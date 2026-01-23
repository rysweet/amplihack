# Enabling amplihack to use GitHub Copilot Copilot

This repository is a dev framework that currently uses Claude Code to provide a text based agentic ai development environment.

We would lke to enahce it to also be able to use GitHub Copilot CLI.

First, You should learn about how Claude Code works - in particular it has use of valuable feature called subagents, hooks, and commands. You should read about them in detail here: @https://docs.claude.com/en/docs/claude-code/overview and the pages that it links to for those topics.

The power of this project lies in its instructions in @CLAUDE.md, and the various subagents (in @~/.amplihack/.claude/agents/_/_.md), commands (in @~/.amplihack/.claude/commands/\*), hooks (configured in .claude/settings.json and run from .claude/tools/)

The CLAUDE.md and other files reference context in the @~/.amplihack/.claude/context directory, especially the @~/.amplihack/.claude/context/PHILOSOPHY.md. This is a very important document for guiding code generation and planning.

All code changes must follow specific workflows. The default workflow is in @~/.amplihack/.claude/workflows/DEFAULT_WORKFLOW.md.

This project is run using a cli "amplihack" which is in @src/

`amplihack launch` launches the interactive text ui.

`amplihack launch -- -p <prompt>` passes a prompt to claude code.

Our objective in this session is to adapt these tools to work with The GitHub Copilot CLI (@https://docs.github.com/en/copilot/how-tos/use-copilot-agents/use-copilot-cli - these docs mostly cover the interactive use - run `coplot --help` to see the non-interactive use).

What we will do is create prompts and automation that let us leverage amplihack to drive the GH Copilot CLI. We are also going to create a special "copilot --auto" mode that creates and agentic loop around copilot cli prompts.

## New amplihack commands

You will build thee new commands:

`amplihack claude` - launch claude code - exactly as dos today with "amplihack launch" -

`amplihack copilot` launch copilot interactively (`copilot --allow-all-tools`) - you will need to install copilot if it is not available (npm install -g @github/copilot
)

`amplihack copilot -- -p <prompt>` - launch copilot with a specific prompt - also any other args you pass after -- will be treated as copilot args

`amplihack copilot --auto -- -p <prompt>` invokes the auto mode with the specified prompt - this will run copilot in an agentic loop (described below).

`amplihack claude --auto -- -p <prompt>` invokes claude code with the agentic loop.

`amplihack copilot --auto --max-turns <int> -- -p <prompt>` auto mode with a set number of max turns (default is 10)

## Auto mode

### Auto mode sdk choices

- if auto mode is started with "copilot" it will run prompts with `copilot --allow-all-tools -p <prompt>`
- if auto mode is started with "claude: it will run prompts with `claude --dangerously-skip-permissions -p <prompt>`
- in the rest of this set of instructions we will use "copilot" but we want the same to work with claude

The auto mode will start a new turn agentic loop that does the following:

- Invokes copilot with a prompt that turns the user's prompt into a concrete objective, with clear natural language evaluation criteria to determine if the objective has been acheived.
- Invokes copilot with the output of the previous step with a prompt that encourages thinking deeply to make a plan for acheiving the objective, with instructions to think carefully about which parts of the plan can be achieved in parallel.
- Invokes copilot to process the outout of the plan to create an agentic loop that will autonomously follow the plan, step by step, in parallel where possible by invoking subprocesses with copilot and prompts to instruct it for each set of steps in the plan. This might include making sub plans as needed. Copilot must setup orchestration of the context coming out of each invocation so that the correct context is held and passed on to further invocations as needed.
- When a sub process invocation of copilot stops, the auto mode should invoke copilot with a prompt to evaluate the output of the session and determine if a new session is needed to answer a question, continue, or correct the work.
- If a session stop has a question or an unresolved concern, the agentic loop should reason over the session and the overall objective and then come up with a new prompt to continue the session (with "--continue" to preserve context)
- The agentic loop should invoke copiot to evaluate when all of the tasks have been completed by doing a natural language evaluation of the original objective. If the objective is not yet achieved then auto mode must start a new turn, summarizing the current state and framing the steps necessary to achieve the objective
- If max-turns is reached (default is ten) then auto-mode will invoke copilot with context to summarize the current state and stop.
- If the objective is achieved then auto-mode will invoke copiot to summarize the entire auto mode sesson and stop.

## Instructions for launching subagents with copilot cli

As the github copilot cli, you have a new super-power - you can launch subagents. You do this by selecting (or being told) a subagent to use from @~/.amplihack/.claude/agents/_.md or @~/.amplihack/.claude/agents/_/\*.md etc (any md file under .claude/agents/) from the descriptions in the frontmatter of each md. Then you craft a prompt with the specfic context and instructions, including the .md file, and then invoke copilot with that prompt as a subprocess.
eg:

````copilot --allow-all-tools -p "Include @~/.amplihack/.claude/agents/amplichack/prompt-writer.md -- Take the user's prompt and improve it: <user-prompt>" etc.

You will need to structure comprehensive instructions for how to invoke subagents for github copilot cli somewhere in the .claude/context directory and ensure it is referenced from AGENTS.md

## Instructions for running commands with copilot cli

As the github copilot cli, you have new capabilities that are AI commands defined in @~/.amplihack/.claude/commands/* (any .md file underneath that directory structure). Each command is a prompt that you can use to structure a particular operation.
To invoke a command run a copilot subprocess ```copilot --allow-all-tools -p "Include @~/.amplihack/.claude/commands/<some_path_to_command>.md <args> <any additional instructions>"```

You will need to structure comprehensive instructionsfor running commands somewhere in the .claude/context/ dir and ensure that they are referenced from AGENTS.md

## Hooks for Github Copilot

Auto mode should attempt to honor the hooks that are configured - before a session run the start hook, when a session invocation stos, run the stop hook. Tool use hooks won't work with github copilot cli.
Auto mode should not run hooks when invoking claude - claude wil do it automatically.

## Supporting github copilot cli

You will need to create an AGENTS.md that instructs github copilot CLI appropriately - basically directly translateing the existing CLAUDE.md but noting the above instructions for subagents and commands etc.

## docs and examples

When you build auto mode, build out good documentation of the feature and provide several examples. Test the examples.
````
