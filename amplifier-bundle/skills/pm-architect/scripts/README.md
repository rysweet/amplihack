# PM Architect Utility Scripts

These scripts implement complex logic for PM Architect operations. They are called by Claude when using the pm-architect skill or by GitHub Actions workflows.

## Agent SDK Scripts (AI-Powered)

These scripts use the Claude Agent SDK for intelligent analysis and generation.

### generate_daily_status.py

Generate comprehensive daily status reports using Claude Agent SDK.

**Usage:**

```bash
python generate_daily_status.py [--project-root PATH] [--output FILE]
```

**Environment Variables:**

- `ANTHROPIC_API_KEY` - Required for Claude SDK

**Returns:** Markdown status report with project health, workstream status, blockers, and recommendations.

**Example:**

```bash
export ANTHROPIC_API_KEY=sk-...
python generate_daily_status.py --output status.md
```

**Used by:** `.github/workflows/pm-daily-status.yml`

### generate_roadmap_review.py

Generate strategic weekly roadmap reviews using Claude Agent SDK.

**Usage:**

```bash
python generate_roadmap_review.py [--project-root PATH] [--output FILE]
```

**Environment Variables:**

- `ANTHROPIC_API_KEY` - Required for Claude SDK

**Returns:** Markdown roadmap review with goal progress, velocity analysis, and strategic recommendations.

**Example:**

```bash
export ANTHROPIC_API_KEY=sk-...
python generate_roadmap_review.py --output roadmap.md
```

**Used by:** `.github/workflows/pm-roadmap-review.yml`

### triage_pr.py

Intelligent PR triage using Claude Agent SDK.

**Usage:**

```bash
python triage_pr.py PR_NUMBER [--project-root PATH] [--output FILE]
```

**Environment Variables:**

- `ANTHROPIC_API_KEY` - Required for Claude SDK

**Returns:** Markdown triage analysis with priority, complexity, suggested reviewers, and risks.

**Example:**

```bash
export ANTHROPIC_API_KEY=sk-...
python triage_pr.py 123 --output triage.md
```

**Used by:** `.github/workflows/pm-pr-triage.yml`

## Heuristic Scripts (Rule-Based)

These scripts use Python heuristics for deterministic operations.

### analyze_backlog.py

Analyze backlog items and generate recommendations using multi-criteria scoring.

**Usage:**

```bash
python analyze_backlog.py [--project-root PATH] [--max-recommendations N]
```

**Returns:** JSON with top N recommendations, scores, and rationale.

**Example:**

```bash
cd my-project
python analyze_backlog.py --max-recommendations 3
```

### create_delegation.py

Create rich delegation package for a backlog item with comprehensive context.

**Usage:**

```bash
python create_delegation.py BACKLOG_ID [--project-root PATH] [--agent AGENT]
```

**Returns:** JSON delegation package with project context, relevant files, test requirements, architectural notes.

**Example:**

```bash
python create_delegation.py BL-001 --agent builder
```

### coordinate.py

Coordinate multiple workstreams, detect conflicts and stalls.

**Usage:**

```bash
python coordinate.py [--project-root PATH]
```

**Returns:** JSON with workstream status, stall detection, dependency conflicts, capacity analysis.

**Example:**

```bash
python coordinate.py
```

### manage_state.py

Manage PM state files - utility for common state operations.

**Usage:**

```bash
# Initialize PM
python manage_state.py init --project-name NAME --project-type TYPE --goals "goal1,goal2" --quality-bar LEVEL

# Add backlog item
python manage_state.py add-item --title TITLE --priority PRIORITY [--description DESC]

# Update backlog item
python manage_state.py update-item ITEM_ID --status STATUS

# Create workstream
python manage_state.py create-workstream ITEM_ID --agent AGENT

# Update workstream
python manage_state.py update-workstream WS_ID --status STATUS [--note NOTE]

# List backlog
python manage_state.py list-backlog [--status STATUS]

# List workstreams
python manage_state.py list-workstreams [--status STATUS]
```

**Examples:**

```bash
# Initialize PM for project
python manage_state.py init \
  --project-name my-cli-tool \
  --project-type cli-tool \
  --goals "Implement config system,Build CLI interface,Achieve 80% coverage" \
  --quality-bar balanced

# Add HIGH priority item
python manage_state.py add-item \
  --title "Implement config parser" \
  --priority HIGH \
  --description "Parse YAML/JSON config files" \
  --estimated-hours 4

# Create workstream for item
python manage_state.py create-workstream BL-001 --agent builder

# Update workstream with progress note
python manage_state.py update-workstream ws-001 --note "Config loading working"

# List all READY backlog items
python manage_state.py list-backlog --status READY

# List active workstreams
python manage_state.py list-workstreams --status RUNNING
```

## Dependencies

All scripts require:

- Python 3.9+
- PyYAML (`pip install pyyaml`)

No other external dependencies - standard library only.

## Integration with PM Architect Skill

When Claude uses the pm-architect skill, it calls these scripts via the Bash tool:

```python
# Example: Claude analyzes backlog
result = bash("python .claude/skills/pm-architect/scripts/analyze_backlog.py")
recommendations = json.loads(result)

# Example: Claude creates delegation package
result = bash("python .claude/skills/pm-architect/scripts/create_delegation.py BL-001 --agent builder")
package = json.loads(result)

# Example: Claude coordinates workstreams
result = bash("python .claude/skills/pm-architect/scripts/coordinate.py")
status = json.loads(result)
```

## Philosophy Compliance

These scripts follow Amplihack philosophy:

- **Ruthless Simplicity**: Standard library + PyYAML only, no complex dependencies
- **Zero-BS Implementation**: All functions work completely, no stubs
- **Single Responsibility**: Each script has one clear purpose
- **File-Based State**: YAML files for human readability, no database

## Testing

Each script can be tested independently:

```bash
# Create test project
cd /tmp/test-pm
python .../manage_state.py init --project-name test --project-type cli-tool --goals "Test" --quality-bar balanced

# Add items
python .../manage_state.py add-item --title "Test feature" --priority HIGH
python .../manage_state.py add-item --title "Another feature" --priority MEDIUM

# Analyze
python .../analyze_backlog.py

# Create delegation
python .../create_delegation.py BL-001

# Create workstream
python .../manage_state.py create-workstream BL-001

# Coordinate
python .../coordinate.py
```

## Error Handling

All scripts return:

- Exit code 0 on success
- Exit code 1 on error
- JSON error message to stderr on failure

```bash
# Success
python analyze_backlog.py && echo "Success"

# Error handling
python analyze_backlog.py || echo "Failed"
```

## Contributing

When adding new scripts:

1. Follow existing patterns (argparse, JSON output, YAML state)
2. Keep dependencies minimal (stdlib + PyYAML)
3. Write complete, working code (no stubs)
4. Document usage in this README
5. Test independently before integration
