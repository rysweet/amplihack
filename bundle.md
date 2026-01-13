---
bundle:
  name: amplihack
  version: 1.0.0
  description: |
    Amplihack development framework - systematic AI-powered development workflows
    with specialized agents, workflow orchestration, and philosophy-driven design.

includes:
  # Inherit foundation capabilities (tools, hooks, core agents)
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
  # Include recipes behavior for workflow execution
  - bundle: git+https://github.com/microsoft/amplifier-bundle-recipes@main
  # Amplihack-specific behavior (agents, context)
  - bundle: amplihack:behaviors/amplihack

# Spawn configuration for sub-agents
spawn:
  exclude_tools: [tool-task]  # Prevent recursive spawning
---

# Amplihack Development Framework

You are configured with the Amplihack development framework - a systematic approach to AI-powered software development that emphasizes ruthless simplicity, modular design, and autonomous execution.

## Core Philosophy

@amplihack:context/philosophy.md

## Instructions

@amplihack:context/instructions.md

---

@foundation:context/shared/common-system-base.md
