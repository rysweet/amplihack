# Architecture Diagram: Config Conflict Handling

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interface                            │
│  (CLI Commands: amplihack install, amplihack config ...)        │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │   Installation Orchestrator            │
        │   (Workflow Coordination)              │
        └───────────────────┬───────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   Conflict   │   │  Namespace   │   │  CLAUDE.md   │
│   Detector   │   │  Installer   │   │  Integrator  │
└──────────────┘   └──────────────┘   └──────────────┘
        │                   │                   │
        └───────────────────┴───────────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │  Filesystem  │
                    │  .claude/    │
                    └──────────────┘
```

## Module Dependency Graph

```
┌──────────────────────────────────────────────────────────┐
│ Layer 3: User Interface                                  │
│                                                           │
│  ┌─────────────────┐         ┌────────────────┐         │
│  │  CLI: install   │         │  CLI: config   │         │
│  │  command        │         │  commands      │         │
│  └────────┬────────┘         └────────┬───────┘         │
└───────────┼──────────────────────────┼──────────────────┘
            │                          │
            │                          │
┌───────────┼──────────────────────────┼──────────────────┐
│ Layer 2: Orchestration               │                  │
│           │                          │                  │
│  ┌────────▼──────────────────────────▼──────┐           │
│  │   InstallationOrchestrator              │           │
│  │   - Workflow logic                       │           │
│  │   - User interaction                     │           │
│  │   - Mode handling (install/uvx)          │           │
│  └────────┬─────────┬──────────┬────────────┘           │
└───────────┼─────────┼──────────┼────────────────────────┘
            │         │          │
            │         │          │
┌───────────┼─────────┼──────────┼────────────────────────┐
│ Layer 1: Core Modules│          │                        │
│           │         │          │                        │
│  ┌────────▼───┐ ┌──▼──────┐ ┌─▼────────────┐           │
│  │ Conflict   │ │Namespace│ │  CLAUDE.md   │           │
│  │ Detector   │ │Installer│ │  Integrator  │           │
│  │            │ │         │ │              │           │
│  │ - Detect   │ │ - Copy  │ │ - Add import │           │
│  │ - Report   │ │ - Force │ │ - Remove     │           │
│  │ - Analyze  │ │ - Verify│ │ - Backup     │           │
│  └────────────┘ └─────────┘ └──────────────┘           │
└─────────────────────────────────────────────────────────┘
            │         │          │
            └─────────┴──────────┘
                      │
                      ▼
            ┌─────────────────┐
            │   Filesystem    │
            │   Operations    │
            └─────────────────┘
```

## Data Flow: Fresh Installation

```
User runs: amplihack install
        │
        ▼
┌──────────────────────────────────────┐
│ 1. Detect Conflicts                  │
│    ConfigConflictDetector            │
│                                      │
│    Input: .claude/ directory         │
│    Output: ConflictReport            │
│      - has_conflicts: false          │
│      - existing_claude_md: false     │
│      - safe_to_namespace: true       │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ 2. Install to Namespace              │
│    NamespaceInstaller                │
│                                      │
│    Input: source files               │
│    Output: InstallResult             │
│      - success: true                 │
│      - installed_path: amplihack/    │
│      - files_installed: [...]        │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ 3. Prompt User                       │
│    InstallationOrchestrator          │
│                                      │
│    "Add import to CLAUDE.md? [Y/n]"  │
│                                      │
│    User: Y                           │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ 4. Integrate Config                  │
│    ClaudeMdIntegrator                │
│                                      │
│    Input: .claude/CLAUDE.md          │
│    Output: IntegrationResult         │
│      - action_taken: "created_new"   │
│      - backup_path: None (new file)  │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ 5. Report Success                    │
│    InstallationOrchestrator          │
│                                      │
│    ✓ Amplihack installed!            │
│      Installation: amplihack/        │
│      Integration: Created CLAUDE.md  │
└──────────────────────────────────────┘
```

## Data Flow: Installation with Conflicts

```
User runs: amplihack install
        │
        ▼
┌──────────────────────────────────────┐
│ 1. Detect Conflicts                  │
│    ConfigConflictDetector            │
│                                      │
│    Input: .claude/ directory         │
│    Output: ConflictReport            │
│      - has_conflicts: true           │
│      - existing_claude_md: true      │
│      - existing_agents: []           │
│      - safe_to_namespace: true       │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ 2. Install to Namespace              │
│    NamespaceInstaller                │
│                                      │
│    Install to amplihack/ subdirectory│
│    (avoids overwriting user files)   │
│                                      │
│    Output: InstallResult             │
│      - success: true                 │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ 3. Prompt for Integration            │
│    InstallationOrchestrator          │
│                                      │
│    Show preview:                     │
│    + @.claude/amplihack/CLAUDE.md    │
│                                      │
│    "Add import? [Y/n]"               │
│    User: Y                           │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ 4. Backup Existing File              │
│    ClaudeMdIntegrator                │
│                                      │
│    Backup: CLAUDE.md.backup.{time}   │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ 5. Add Import Statement              │
│    ClaudeMdIntegrator                │
│                                      │
│    Prepend to existing CLAUDE.md:    │
│    @.claude/amplihack/CLAUDE.md      │
│                                      │
│    Output: IntegrationResult         │
│      - action_taken: "added"         │
│      - backup_path: {...}            │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ 6. Report Success                    │
│    InstallationOrchestrator          │
│                                      │
│    ✓ Amplihack installed!            │
│      Integration: Added to CLAUDE.md │
│      Backup: {...}                   │
└──────────────────────────────────────┘
```

## File System State Transitions

### Before Installation (Empty Project)

```
project/
└── .claude/
    └── (empty)
```

### After Installation (Fresh)

```
project/
└── .claude/
    ├── CLAUDE.md                    ← Created by integrator
    │   Content: @.claude/amplihack/CLAUDE.md
    │
    └── amplihack/                   ← Created by installer
        ├── CLAUDE.md                ← Amplihack's config
        ├── agents/
        │   ├── architect.md
        │   ├── builder.md
        │   └── fixer.md
        ├── context/
        │   └── *.md
        └── commands/
            └── *.md
```

### Before Installation (Existing Config)

```
project/
└── .claude/
    ├── CLAUDE.md                    ← User's existing file
    │   Content: User's custom config (125 lines)
    │
    └── agents/
        └── custom.md                ← User's agent
```

### After Installation (With Conflicts)

```
project/
└── .claude/
    ├── CLAUDE.md                    ← Modified by integrator
    │   Content:
    │     @.claude/amplihack/CLAUDE.md    ← Added
    │     User's custom config (125 lines) ← Preserved
    │
    ├── CLAUDE.md.backup.20250110_143022  ← Backup
    │
    ├── agents/
    │   └── custom.md                ← User's agent (untouched)
    │
    └── amplihack/                   ← Created by installer
        ├── CLAUDE.md
        ├── agents/
        │   ├── architect.md         ← No conflict!
        │   ├── builder.md
        │   └── fixer.md
        ├── context/
        └── commands/
```

## Config CLI Command Flow

### `amplihack config show`

```
User runs: amplihack config show
        │
        ▼
┌──────────────────────────────────────┐
│ 1. Detect Installation               │
│    ConfigConflictDetector            │
│                                      │
│    Check: .claude/amplihack/ exists? │
│    Check: CLAUDE.md has import?      │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ 2. Format Status Report              │
│                                      │
│    Installation: Installed           │
│    Integration: Present              │
│    Files: 15                         │
└──────────────┬───────────────────────┘
               │
               ▼
        Display to user
```

### `amplihack config integrate`

```
User runs: amplihack config integrate
        │
        ▼
┌──────────────────────────────────────┐
│ 1. Check Current State               │
│                                      │
│    - Is amplihack installed?         │
│    - Is import already present?      │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ 2. Preview Changes                   │
│    ClaudeMdIntegrator (dry_run)      │
│                                      │
│    Show: What will be added          │
│    Show: Backup location             │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ 3. Prompt User                       │
│                                      │
│    "Continue? [y/N]"                 │
│                                      │
│    User: y                           │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ 4. Apply Changes                     │
│    ClaudeMdIntegrator                │
│                                      │
│    - Create backup                   │
│    - Add import                      │
│    - Report success                  │
└──────────────────────────────────────┘
```

### `amplihack config remove`

```
User runs: amplihack config remove
        │
        ▼
┌──────────────────────────────────────┐
│ 1. Preview Removal                   │
│                                      │
│    Show: Import will be removed      │
│    Show: amplihack/ will be deleted  │
│    Show: Backup location             │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ 2. Prompt User                       │
│                                      │
│    "Continue? [y/N]"                 │
│                                      │
│    User: y                           │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ 3. Remove Integration                │
│    ClaudeMdIntegrator                │
│                                      │
│    - Create backup                   │
│    - Remove import line              │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ 4. Delete Namespace                  │
│    (if not --keep-files)             │
│                                      │
│    - Delete .claude/amplihack/       │
│    - Report success                  │
└──────────────────────────────────────┘
```

## Mode Handling: Install vs UVX

```
                    ┌─────────────┐
                    │ Entry Point │
                    └──────┬──────┘
                           │
                    ┌──────▼──────────┐
                    │  Detect Mode    │
                    │                 │
                    │ - ENV vars?     │
                    │ - Temp path?    │
                    │ - Flag set?     │
                    └──────┬──────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
    ┌─────────▼──────────┐   ┌─────────▼──────────┐
    │   Install Mode     │   │     UVX Mode       │
    │   (Persistent)     │   │   (Ephemeral)      │
    └─────────┬──────────┘   └─────────┬──────────┘
              │                         │
              │                         │
    ┌─────────▼──────────┐   ┌─────────▼──────────┐
    │ 1. Install to      │   │ 1. Install to      │
    │    namespace       │   │    namespace       │
    │                    │   │    (temporary)     │
    └─────────┬──────────┘   └─────────┬──────────┘
              │                         │
              │                         │
    ┌─────────▼──────────┐   ┌─────────▼──────────┐
    │ 2. Offer to        │   │ 2. Skip            │
    │    integrate       │   │    integration     │
    │    with CLAUDE.md  │   │    (temporary)     │
    └─────────┬──────────┘   └─────────┬──────────┘
              │                         │
              │                         │
    ┌─────────▼──────────┐   ┌─────────▼──────────┐
    │ 3. Show persistent │   │ 3. Show temporary  │
    │    install message │   │    session message │
    └────────────────────┘   └────────────────────┘
```

## Error Handling Flow

```
┌────────────────────────────────────────────────┐
│              Any Operation                     │
└───────────────────┬────────────────────────────┘
                    │
         ┌──────────┴──────────┐
         │                     │
    Success Path          Error Occurs
         │                     │
         ▼                     ▼
┌─────────────────┐   ┌──────────────────────────┐
│  Return Result  │   │    Error Classification  │
└─────────────────┘   └───────────┬──────────────┘
                                  │
                     ┌────────────┼────────────┐
                     │            │            │
                PermissionError FileNotFound Others
                     │            │            │
                     ▼            ▼            ▼
          ┌───────────────┐ ┌─────────┐ ┌─────────┐
          │ Show fix with │ │ Show    │ │ Show    │
          │ sudo command  │ │ path    │ │ generic │
          └───────────────┘ └─────────┘ └─────────┘
                     │            │            │
                     └────────────┼────────────┘
                                  │
                                  ▼
                     ┌────────────────────────┐
                     │  Offer Rollback        │
                     │  (if partial operation)│
                     └────────────────────────┘
```

## Backup Strategy

```
┌─────────────────────────────────────────┐
│  Before any file modification           │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│  Create timestamped backup              │
│                                         │
│  CLAUDE.md                              │
│    → CLAUDE.md.backup.20250110_143022   │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│  Perform modification                   │
│                                         │
│  - If success: Keep backup              │
│  - If failure: Can restore from backup  │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│  Rotate old backups                     │
│                                         │
│  Keep last 3 backups, delete older      │
│                                         │
│  ✓ .backup.20250110_143022              │
│  ✓ .backup.20250109_120000              │
│  ✓ .backup.20250108_090000              │
│  ✗ .backup.20250107_080000 (deleted)    │
└─────────────────────────────────────────┘
```

## Key Design Patterns

### 1. Dependency Injection
```
InstallationOrchestrator
    ↓ (injects dependencies)
ConfigConflictDetector
NamespaceInstaller
ClaudeMdIntegrator
```

### 2. Result Objects
```
Operation → Result Object (success/failure + data)
    - Success: Result with data
    - Failure: Result with error info
    - Always structured, never throws
```

### 3. Idempotent Operations
```
Run N times → Same result as running once
    - Check current state first
    - Only modify if needed
    - Safe to retry on failure
```

### 4. Atomic Operations
```
Modify File:
    1. Create temp file
    2. Write new content
    3. Atomic rename
    4. Original untouched until success
```

### 5. Preview Before Apply
```
1. Dry run (preview=True)
2. Show user what will change
3. Get confirmation
4. Apply changes (preview=False)
```

---

This architecture provides:
- **Clear separation of concerns**
- **Simple composition**
- **Testable components**
- **Safe operations**
- **User control**

Each module is regeneratable from its specification and can be tested independently.
