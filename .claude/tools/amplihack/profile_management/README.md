# Profile Management System

Profile management for amplihack - collections of commands, context, agents, and skills.

## Table of Contents

- [Features](#features)
- [Usage](#usage)
  - [Load a Profile](#load-a-profile)
  - [Discover Components](#discover-components)
  - [Filter Components](#filter-components)
- [Built-in Profiles](#built-in-profiles)
- [Security](#security)
- [Testing](#testing)
- [Architecture](#architecture)

## Features

- **YAML-based profiles**: Human-readable configuration
- **URI support**: file:// scheme for local profiles
- **Component filtering**: Pattern-based with wildcards
- **Category filtering**: Scalable to 100k+ skills
- **CLI commands**: list, show, switch, validate, current
- **Persistent config**: ~/.amplihack/config.yaml
- **Environment override**: AMPLIHACK_PROFILE variable

## Usage

### Load a Profile

```python
from profile_management import ProfileLoader, ProfileParser

loader = ProfileLoader()
parser = ProfileParser()

# Load with relative path
yaml_content = loader.load("file://.claude/profiles/coding.yaml")
profile = parser.parse(yaml_content)

# Or load with absolute path
yaml_content = loader.load("file:///home/user/.amplihack/profiles/coding.yaml")
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

Built-in profiles are located in `.claude/profiles/` and can be loaded using file:// URIs:

- **all**: Complete environment (default) - `file://.claude/profiles/all.yaml`
- **coding**: Development-focused - `file://.claude/profiles/coding.yaml`
- **research**: Investigation-focused - `file://.claude/profiles/research.yaml`

## Security

- Path traversal protection for all file:// URIs
- YAML bomb protection (size + depth limits)
- Version validation before parsing
- Pattern complexity limits

## Testing

```bash
python -m pytest tests/ -v
```

141 comprehensive tests covering all functionality.

## Architecture

- **models.py**: Pydantic data models (Profile, ComponentSet)
- **loader.py**: URI-based loading (file://)
- **parser.py**: YAML parsing + validation
- **discovery.py**: Component discovery (filesystem scanning)
- **filter.py**: Pattern matching (wildcards)
- **index.py**: Skill indexing (category-based)
- **config.py**: Configuration persistence (~/.amplihack)
- **cli.py**: Rich console interface (list, show, switch)
