# Adaptive Hook System - Design Specification

See the architect agent's complete design specification from agent afb564f.

This system enables hooks to detect which launcher (Claude Code, Copilot CLI, Codex)
is calling them and adapt behavior accordingly.

**Key Components**:

1. LauncherDetector - Detect launcher from launcher_context.json
2. Strategy Pattern - Platform-specific implementations
3. Copilot Workarounds - AGENTS.md injection, subprocess power-steering
4. Cleanup - Session end removes generated files

**Implementation Priority**: Phase 1 (Foundation) first, then Phases 2-4.

Complete design provided by architect agent afb564f.
