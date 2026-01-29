# Shadow Testing Skill

Test local uncommitted changes in isolated container environments before pushing to remote repositories.

## What This Skill Provides

This skill teaches **shadow testing** - a methodology for testing local changes (including uncommitted work) in clean, isolated container environments that mirror CI/CD conditions.

**Key Benefits**:
- Test exactly what's on your machine (uncommitted changes and all)
- Clean-state validation ("does it work on a fresh machine?")
- Multi-repo coordination (test changes across multiple repositories)
- CI parity (catch issues before pushing)

## Quick Start

### For Amplifier Users

Shadow tool is built-in - just use it:

```python
# Create shadow with local changes
shadow.create(local_sources=["~/repos/my-lib:org/my-lib"])

# Run tests
shadow.exec(shadow_id, "pytest")

# Cleanup
shadow.destroy(shadow_id)
```

### For Other Agents (Claude Code, GitHub Copilot, etc.)

Install standalone CLI:

```bash
# Via uvx (recommended)
uvx amplifier-shadow --version

# Or via pip
pip install amplifier-bundle-shadow

# Create shadow
amplifier-shadow create --local ~/repos/my-lib:org/my-lib --name test

# Run tests
amplifier-shadow exec test "pytest"

# Cleanup
amplifier-shadow destroy test
```

## What's Included

### Core Documentation

- **SKILL.md** - Complete skill with progressive disclosure (Levels 1-4)
  - Level 1: Fundamentals and quick start
  - Level 2: Common patterns and verification
  - Level 3: Advanced topics and DIY setup
  - Includes philosophy alignment and troubleshooting

### Generalizable Shell Scripts

Located in `scripts/`:

- **create-bundle.sh** - Creates git bundle snapshots from any local repo
- **setup-shadow.sh** - Starts container with Gitea and configures URL rewriting
- **test-shadow.sh** - Verifies shadow environment is working correctly

These scripts work without Amplifier - pure bash, git, and Docker.

### Docker Compose Examples

Located in `docker-compose/`:

- **single-repo.yml** - Basic single repository shadow
- **multi-repo.yml** - Multiple coordinated repositories
- **ci-shadow.yml** - CI-optimized automated testing
- **README.md** - Complete Docker Compose usage guide

Includes GitHub Actions and GitLab CI integration examples.

## Key Features

### 1. Exact Working Tree Snapshots

Captures your local state **exactly as-is**:
- New/untracked files included
- Modified files with current changes
- Deleted files properly removed
- **No staging required** - what you see is what gets tested

### 2. Selective Git URL Rewriting

Only your specified repos are local; everything else uses real GitHub:

```bash
# github.com/org/my-lib → Your local snapshot
# github.com/org/other-repo → Real GitHub
```

Uses git `insteadOf` rules with boundary markers to prevent prefix collisions.

### 3. Package Manager Cache Isolation

Automatic cache isolation prevents stale packages:
- Python UV: `/tmp/uv-cache`
- Python pip: `/tmp/pip-cache`
- Node npm: `/tmp/npm-cache`
- Rust cargo: `/tmp/cargo-home`
- Go modules: `/tmp/go-mod-cache`

### 4. Pre-Cloned Workspace

Local sources automatically cloned to `/workspace/{org}/{repo}` for convenience.

### 5. Multi-Language Support

Works with any language/ecosystem:
- Python (uv, pip, poetry)
- Node.js (npm, yarn, pnpm)
- Rust (cargo)
- Go (go modules)
- Any git-based dependency

## Integration with Outside-In Testing

Combine shadow environments with agentic outside-in tests for complete pre-push validation:

```bash
# Create shadow with local changes
amplifier-shadow create --local ~/repos/lib:org/lib --name test

# Run outside-in test scenarios inside shadow
amplifier-shadow exec test "gadugi-agentic-test run test-scenario.yaml"

# Extract evidence
amplifier-shadow extract test /evidence ./test-evidence
```

See the `outside-in-testing` skill Level 4 for complete integration examples.

## Use Cases

### Library Development

Test library changes with dependent projects before publishing:

```bash
amplifier-shadow create --local ~/repos/my-lib:org/my-lib --name lib-test
amplifier-shadow exec lib-test "
  git clone https://github.com/org/dependent-app &&
  cd dependent-app &&
  pip install git+https://github.com/org/my-lib &&
  pytest
"
```

### Multi-Repo Coordination

Validate changes across multiple repositories work together:

```bash
amplifier-shadow create \
  --local ~/repos/core:org/core \
  --local ~/repos/cli:org/cli \
  --name multi-test

amplifier-shadow exec multi-test "pip install git+https://github.com/org/cli"
```

### Pre-Push CI Validation

Run your CI script in shadow before pushing:

```bash
amplifier-shadow create --local ~/repos/project:org/project --name ci-check
amplifier-shadow exec ci-check "./scripts/ci.sh"
```

## Philosophy Alignment

This skill follows amplihack's core principles:

- **Ruthless Simplicity**: Minimal abstraction (container + gitea + URL rewriting)
- **Modular Design**: Self-contained, composable with other testing tools
- **Zero-BS Implementation**: Every script works completely, no stubs
- **Outside-In Thinking**: Test what users see, not implementation details

## Agent Compatibility

| Agent | Support | Method |
|-------|---------|--------|
| Amplifier | ✅ Native | Built-in `shadow` tool |
| Claude Code | ✅ Standalone | `amplifier-shadow` CLI via bash |
| GitHub Copilot | ✅ Standalone | `amplifier-shadow` CLI via bash |
| Manual/DIY | ✅ Scripts | Shell scripts + Docker Compose |

## Architecture

Shadow environments use this architecture:

```
┌─────────────────────────────────────────────┐
│  Shadow Container                           │
│  ┌───────────────────────────────────────┐  │
│  │  Gitea (localhost:3000)               │  │
│  │  - Your local snapshots               │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  Git URL Rewriting:                         │
│  github.com/org/my-lib → Gitea (local)     │
│  github.com/org/* → Real GitHub             │
│                                             │
│  /workspace (pre-cloned local sources)      │
└─────────────────────────────────────────────┘
```

## Related Skills

- **outside-in-testing** - Agentic behavior-driven tests (enhanced with Level 4 shadow integration)
- **test-gap-analyzer** - Find untested code paths
- **philosophy-guardian** - Verify scripts follow ruthless simplicity

## Resources

- **Amplifier Shadow Bundle**: https://github.com/microsoft/amplifier-bundle-shadow
- **Skill Documentation**: `SKILL.md` (this directory)
- **Shell Scripts**: `scripts/` (this directory)
- **Docker Compose Examples**: `docker-compose/` (this directory)

## Version

**1.0.0** (2026-01-29)

- Initial skill release
- Complete documentation with progressive disclosure (Levels 1-3)
- Generalizable shell scripts for DIY setup
- Docker Compose examples for all use cases
- Multi-language support (Python, Node, Rust, Go)
- Integration patterns with outside-in-testing
- Philosophy alignment with ruthless simplicity

## Contributing

This skill is part of the amplihack bundle. For issues or improvements:

1. Test scripts work standalone (without Amplifier)
2. Follow philosophy: ruthless simplicity, zero-BS implementation
3. Maintain agent-agnostic approach (works for all coding agents)
4. Update examples and troubleshooting as needed

---

**Remember**: Shadow environments let you test **exactly** what's on your machine in a **clean, isolated environment** that mirrors CI. Use them before every significant push to catch issues early.
