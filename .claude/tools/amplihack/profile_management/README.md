# Profile Management System

Comprehensive profile management for amplihack - organize and customize collections of commands, context, agents, and skills.

## Features

- **YAML-based profiles**: Human-readable configuration
- **URI support**: file://, amplihack:// schemes
- **Component filtering**: Pattern-based with wildcards
- **Category filtering**: Scalable to 100k+ skills
- **CLI commands**: list, show, switch, validate, current
- **Persistent config**: Saved to ~/.amplihack/config.yaml
- **Environment override**: AMPLIHACK_PROFILE variable

## Usage

### Load a Profile

```python
from profile_management import ProfileLoader, ProfileParser

loader = ProfileLoader()
parser = ProfileParser()

yaml_content = loader.load("amplihack://profiles/coding")
profile = parser.parse(yaml_content)
```

### Discover Components

```python
from profile_management import ComponentDiscovery

discovery = ComponentDiscovery()
inventory = discovery.discover_all()

# Returns: commands, context, agents, skills, skill_categories
```

### Filter Components

```python
from profile_management import ComponentFilter

filter_obj = ComponentFilter()
filtered = filter_obj.filter(profile, inventory)

# Result: ComponentSet with filtered components
print(f"Token estimate: {filtered.token_count_estimate()} tokens")
```

## Built-in Profiles

- **all**: Complete environment (default)
- **coding**: Development-focused
- **research**: Investigation-focused

## CLI Commands

```bash
/amplihack:profile list              # List available profiles
/amplihack:profile show [uri]        # Show profile details
/amplihack:profile current           # Show active profile
/amplihack:profile switch <uri>      # Switch profile
/amplihack:profile validate <uri>    # Validate profile
```

## Security

- Path traversal protection for file:// URIs
- YAML bomb protection (size + depth limits)
- Version validation before parsing
- Pattern complexity limits

## Testing

```bash
python -m pytest tests/ -v
```

141 comprehensive tests covering all functionality.

## Architecture

- **models.py**: Pydantic data models
- **loader.py**: URI-based loading
- **parser.py**: YAML parsing + validation
- **discovery.py**: Component discovery
- **filter.py**: Pattern matching
- **index.py**: Skill indexing
- **config.py**: Configuration persistence
- **cli.py**: Rich console interface
