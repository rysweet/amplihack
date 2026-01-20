# Preference System Template

## When to Use This Template

Use this template when investigating or explaining:

- User preference systems
- Configuration management
- Settings storage and loading
- Profile management
- Environment variables and config files
- Feature flags and toggles

**Trigger Conditions:**

- System loads and applies user/system settings
- Configuration flows from storage to application
- Settings are validated and enforced
- Preferences persist across sessions

**Examples:**

- User preferences in applications
- Application configuration files (.env, config.yaml)
- Browser settings and cookies
- IDE preferences and workspaces
- Feature flag systems
- Environment-specific configurations

## Template Diagram

```mermaid
graph LR
    A[Storage<br/>File/Database/API] -->|Load| B[Loader<br/>Reader/Fetcher]
    B -->|Parse| C[Parser<br/>JSON/YAML/Format]
    C -->|Validate| D[Validator<br/>Schema Check]
    D -->|Inject| E[Context<br/>Application State]
    E -->|Apply| F[Behavior<br/>Runtime Enforcement]

    G[Defaults<br/>Fallback Values] -.->|Merge with| D
    H[Error Handler<br/>Invalid Config] -.->|On Failure| D

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style D fill:#bbf,stroke:#333,stroke-width:2px
    style F fill:#bfb,stroke:#333,stroke-width:2px
    style H fill:#fbb,stroke:#333,stroke-width:2px
```

## Customization Guide

Replace these placeholders with your specific system components:

1. **Storage** → Your storage mechanism (e.g., "USER_PREFERENCES.md", "PostgreSQL", "localStorage")
2. **Loader** → Your loading logic (e.g., "FileReader", "ConfigService", "APIClient")
3. **Parser** → Your parsing logic (e.g., "MarkdownParser", "JSONParser", "YAMLParser")
4. **Validator** → Your validation logic (e.g., "SchemaValidator", "TypeChecker", "RulesEngine")
5. **Context** → Where preferences live (e.g., "SessionContext", "ApplicationState", "UserSession")
6. **Behavior** → How preferences are applied (e.g., "CommunicationStyle", "Theme", "FeatureFlags")

**Optional Components:**

- **Defaults** → If system provides fallback values (dotted line)
- **Error Handler** → If validation failures are handled (dotted line)

### Example: Claude Code User Preferences

```mermaid
graph LR
    A[USER_PREFERENCES.md<br/>Markdown File] -->|Load| B[FrameworkPathResolver<br/>File Reader]
    B -->|Parse| C[Regex Extraction<br/>YAML Frontmatter]
    C -->|Validate| D[Preference Validator<br/>Check Valid Options]
    D -->|Inject| E[additionalContext<br/>Session Context]
    E -->|Apply| F[Pirate Style<br/>Communication Mode]

    G[Default Preferences<br/>Formal/Balanced] -.->|Fallback| D
    H[Error Logger<br/>Invalid Preference] -.->|On Failure| D

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style D fill:#bbf,stroke:#333,stroke-width:2px
    style F fill:#bfb,stroke:#333,stroke-width:2px
    style H fill:#fbb,stroke:#333,stroke-width:2px
```

## Two-Layer Preference System Variation

For systems with multiple loading stages (initial load + updates):

```mermaid
graph TD
    A[Storage<br/>Preference File] -->|Initial Load| B[SessionStart<br/>Full Load]
    B -->|Complete Preferences| C[Session Context]

    A -->|Periodic Check| D[Update Monitor<br/>File Watcher]
    D -->|Changed| E[Reload Trigger]
    E -->|Refresh Preferences| C

    C -->|Enforce| F[Application Behavior]

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style B fill:#bbf,stroke:#333,stroke-width:2px
    style D fill:#bbf,stroke:#333,stroke-width:2px
    style C fill:#bfb,stroke:#333,stroke-width:2px
```

## Multi-Source Configuration Variation

For systems that merge preferences from multiple sources:

```mermaid
graph TD
    A[Global Config<br/>System Defaults] -->|Merge| E[Config Merger]
    B[User Config<br/>User Overrides] -->|Merge| E
    C[Environment Variables<br/>Runtime Overrides] -->|Merge| E
    D[Command Line Args<br/>Highest Priority] -->|Merge| E

    E -->|Priority Resolution| F[Final Config]
    F -->|Apply| G[Application]

    style A fill:#f9f,stroke:#333
    style B fill:#f9f,stroke:#333
    style C fill:#f9f,stroke:#333
    style D fill:#f9f,stroke:#333,stroke-width:2px
    style E fill:#bbf,stroke:#333
    style F fill:#bfb,stroke:#333,stroke-width:2px
```

**Priority Order:** Command Line > Environment > User > Global

## Quality Checklist

Before using this diagram, verify:

- [ ] **Storage is clear** - Where are preferences stored?
- [ ] **Loading mechanism shown** - How are preferences read?
- [ ] **Parsing is described** - What format are preferences in?
- [ ] **Validation is explicit** - How are invalid preferences handled?
- [ ] **Application is shown** - Where/how are preferences used?
- [ ] **Defaults shown** (if applicable) - What happens if no preferences exist?
- [ ] **Error handling visible** - What happens with invalid config?
- [ ] **Labels are specific** - Use actual component names

## Common Variations

### Variation 1: Simple Load and Apply

```mermaid
graph LR
    A[Config File] -->|Read| B[Parser]
    B -->|Apply| C[Application]

    style A fill:#f9f,stroke:#333
    style B fill:#bbf,stroke:#333
    style C fill:#bfb,stroke:#333
```

### Variation 2: Cached Preferences

```mermaid
graph TD
    A[Storage] -->|First Load| B[Cache]
    B -->|Serve| C[Application]

    D[Update Event] -->|Clear| B
    B -->|Cache Miss| A

    style A fill:#f9f,stroke:#333
    style B fill:#ff9,stroke:#333
    style C fill:#bfb,stroke:#333
```

### Variation 3: Preference Hierarchy

```mermaid
graph TD
    A[User Preference] -->|Override| D{Exists?}
    D -->|Yes| E[Use User Value]
    D -->|No| B[Team Preference]
    B -->|Override| F{Exists?}
    F -->|Yes| G[Use Team Value]
    F -->|No| C[System Default]
    C -->|Always| H[Use Default]

    E -->|Apply| I[Final Value]
    G -->|Apply| I
    H -->|Apply| I

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style B fill:#f9f,stroke:#333
    style C fill:#f9f,stroke:#333
    style D fill:#ff9,stroke:#333
    style F fill:#ff9,stroke:#333
    style I fill:#bfb,stroke:#333,stroke-width:2px
```

## Usage Tips

**When to use this template:**

- User asks "how are preferences loaded?"
- Explaining configuration systems
- Documenting settings architecture
- Showing preference precedence/hierarchy

**What to emphasize:**

- Storage location (where preferences live)
- Loading order (if multi-source)
- Validation rules (what's allowed)
- Default behavior (fallback values)
- Application points (where preferences take effect)

**What to avoid:**

- Internal parsing implementation (keep high-level)
- Every possible configuration option (show pattern, not exhaustive list)
- File format details (unless critical to understanding)

## Real-World Example: Two-Layer User Preference Enforcement

```mermaid
graph TD
    A[USER_PREFERENCES.md<br/>Storage File] -->|Read by| B[SessionStart Hook<br/>Initial Load]
    B -->|Full Content| C[hookSpecificOutput<br/>Complete Preferences]
    C -->|Inject| D[Claude Code Session<br/>additionalContext]

    A -->|Also Read by| E[UserPromptSubmit Hook<br/>Per-Message Check]
    E -->|Concise Reminder| F[Per-Message Context<br/>Key Preferences]
    F -->|Re-inject| D

    D -->|Enforces| G[Communication Style<br/>Pirate Mode]
    D -->|Enforces| H[Verbosity Level<br/>Balanced]
    D -->|Enforces| I[Collaboration Style<br/>Interactive]

    G -->|Applied to| J[Every Response]
    H -->|Applied to| J
    I -->|Applied to| J

    K[FrameworkPathResolver<br/>Path Handler] -.->|Resolve Path| B
    K -.->|Resolve Path| E

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style D fill:#bbf,stroke:#333,stroke-width:2px
    style J fill:#bfb,stroke:#333,stroke-width:2px
```

**Caption:** This diagram shows Claude Code's two-layer preference enforcement. Layer 1 (SessionStart) loads full preferences once at initialization. Layer 2 (UserPromptSubmit) re-injects concise reminders on every message. Both layers read from the same USER_PREFERENCES.md file and inject into Claude's session context, where preferences enforce behavior like pirate communication style.

## Related Templates

- **HOOK_SYSTEM_FLOW.md** - For showing how preferences integrate with hooks
- **DATA_FLOW.md** - For showing preference data transformations
- **COMPONENT_RELATIONSHIPS.md** - For showing preference system within larger architecture

## Anti-Patterns

**Too Simple:**

```
File → App
```

(Not helpful - no context about loading, parsing, validation)

**Too Detailed:**

```
File → Open → Read → Close → Parse Line 1 → Parse Line 2 → Validate Field 1 → Validate Field 2 → Store → Apply
```

(Too granular - combine related steps)

**Unclear Precedence:**

```
Source A → Merge
Source B → Merge
Merge → App
```

(Which source has priority? Add labels or ordering)

**Better:**

```
Source A (Low Priority) → Merge
Source B (High Priority) → Merge
Merge → Final Config → App
```

## Advanced Pattern: Dynamic Preference Updates

For systems where preferences can change during runtime:

```mermaid
graph TD
    A[Preference Storage] -->|Initial Load| B[Config Service]
    B -->|Apply| C[Application State]

    D[User Action<br/>Change Setting] -->|Update| A
    A -->|Notify| E[Change Listener]
    E -->|Trigger Reload| B
    B -->|Re-apply| C

    C -->|Reflects| F[Updated Behavior]

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style B fill:#bbf,stroke:#333
    style C fill:#bfb,stroke:#333
    style E fill:#ff9,stroke:#333
```

**Use Case:** Live preference updates without restart (theme switching, language changes)

## Caching and Performance Optimization

For systems with expensive preference loading:

```mermaid
graph LR
    A[Storage<br/>Slow/Remote] -->|First Load| B[Cache<br/>Fast/Local]
    B -->|Serve| C[Application]

    D[TTL Expired] -.->|Invalidate| B
    E[Update Event] -.->|Invalidate| B
    B -.->|Cache Miss| A

    style A fill:#f9f,stroke:#333
    style B fill:#ff9,stroke:#333,stroke-width:2px
    style C fill:#bfb,stroke:#333
```

**Use Case:** Remote config services, database-backed preferences, API-fetched settings
