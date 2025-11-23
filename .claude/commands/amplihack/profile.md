# Profile Management

Manage amplihack profiles (collections of commands, context, agents, and skills).

## Usage

`/amplihack:profile <command> [options]`

## Commands

### list
List all available built-in profiles.

```bash
/amplihack:profile list
```

### show [uri]
Show details of a specific profile (or current profile if URI not provided).

```bash
/amplihack:profile show
/amplihack:profile show amplihack://profiles/coding
/amplihack:profile show file:///path/to/custom.yaml
```

### current
Show currently active profile.

```bash
/amplihack:profile current
```

### switch <uri>
Switch to a different profile.

```bash
/amplihack:profile switch amplihack://profiles/coding
/amplihack:profile switch amplihack://profiles/research
/amplihack:profile switch file:///path/to/custom.yaml
```

### validate <uri>
Validate a profile configuration.

```bash
/amplihack:profile validate amplihack://profiles/coding
/amplihack:profile validate file:///path/to/custom.yaml
```

## Built-in Profiles

- **all**: Complete environment (all components)
- **coding**: Development-focused (builder, reviewer, tester agents)
- **research**: Investigation-focused (analyzer, knowledge-archaeologist)

## Environment Variable

Set `AMPLIHACK_PROFILE` to override the current profile:

```bash
export AMPLIHACK_PROFILE=amplihack://profiles/coding
amplihack
```

## Examples

```bash
# List available profiles
/amplihack:profile list

# Switch to coding profile
/amplihack:profile switch amplihack://profiles/coding

# Show current profile
/amplihack:profile current

# Validate custom profile
/amplihack:profile validate file:///path/to/my-profile.yaml
```

## Implementation

Execute profile management commands using the ProfileCLI class:

```python
import sys
sys.path.insert(0, str(Path(".claude/tools/amplihack")))

from profile_management.cli import ProfileCLI

cli = ProfileCLI()

# Parse command from user input
# The user's input after /amplihack:profile should be parsed as command and arguments
```
