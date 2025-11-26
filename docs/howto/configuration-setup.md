# How to Set Up Configuration Management

Step-by-step guide to configuring the ConfigManager in your amplihack project.

## Goal

Set up centralized configuration management for your amplihack application using YAML files and environment variable overrides.

## Prerequisites

- amplihack installed (`pip install amplihack`)
- Python 3.8 or later
- Write access to create config files

## Steps

### 1. Create Configuration Directory

```bash
mkdir -p config
```

### 2. Create Default Configuration

Create `config/default.yaml` with your application settings:

```yaml
# config/default.yaml
debug: false

database:
  host: localhost
  port: 5432
  name: amplihack_dev
  user: developer
  pool_size: 10
  timeout: 30

server:
  host: 0.0.0.0
  port: 8000
  workers: 4
  reload: false

cache:
  enabled: true
  ttl: 3600
  max_size: 1000

logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  handlers:
    - console
```

### 3. Initialize ConfigManager in Your Application

```python
# src/main.py
from amplihack.config import ConfigManager

def main():
    # Initialize configuration
    config = ConfigManager("config/default.yaml")

    # Use configuration values
    db_host = config.get("database.host")
    db_port = config.get("database.port")

    print(f"Connecting to database at {db_host}:{db_port}")

if __name__ == "__main__":
    main()
```

### 4. Create Environment-Specific Configurations

Create separate config files for different environments:

```bash
# Development
config/default.yaml

# Production
config/production.yaml

# Testing
config/test.yaml
```

**Production config** (`config/production.yaml`):

```yaml
debug: false

database:
  host: prod-db.example.com
  port: 5432
  name: amplihack_prod
  user: app_user
  pool_size: 50

server:
  host: 0.0.0.0
  port: 443
  workers: 16

logging:
  level: WARNING
  handlers:
    - file
    - sentry
```

### 5. Select Configuration by Environment

```python
import os
from amplihack.config import ConfigManager

def get_config():
    env = os.getenv("ENVIRONMENT", "default")
    config_file = f"config/{env}.yaml"

    return ConfigManager(config_file)

config = get_config()
```

### 6. Override with Environment Variables

Set environment variables for sensitive or deployment-specific values:

```bash
# Set database credentials
export AMPLIHACK_DATABASE__HOST=secure-db.example.com
export AMPLIHACK_DATABASE__USER=secure_user
export AMPLIHACK_DATABASE__PASSWORD=secret123

# Override server settings
export AMPLIHACK_SERVER__PORT=9000
export AMPLIHACK_DEBUG=true

# Run application
python src/main.py
```

### 7. Access Configuration Values

```python
from amplihack.config import ConfigManager

config = ConfigManager("config/default.yaml")

# Simple values
debug = config.get("debug")

# Nested values with dot notation
db_host = config.get("database.host")
db_timeout = config.get("database.timeout", default=30)

# Get entire sections
db_config = config.get("database")
# Returns: {'host': '...', 'port': 5432, ...}
```

### 8. Validate Configuration

```python
from amplihack.config import ConfigManager, ConfigValidationError

config = ConfigManager("config/default.yaml")

try:
    config.validate()
    print("Configuration is valid")
except ConfigValidationError as e:
    print(f"Invalid configuration: {e}")
    exit(1)
```

## Common Patterns

### Pattern: Lazy Configuration Loading

```python
# config.py
_config = None

def get_config():
    global _config
    if _config is None:
        _config = ConfigManager("config/default.yaml")
    return _config

# Use throughout your application
from config import get_config

config = get_config()
db_host = config.get("database.host")
```

### Pattern: Configuration with Secrets

Keep secrets out of YAML files:

```yaml
# config/default.yaml
database:
  host: localhost
  port: 5432
  name: amplihack
  # No password in YAML!

api:
  endpoint: https://api.example.com
  # No API key in YAML!
```

Set secrets via environment variables:

```bash
export AMPLIHACK_DATABASE__PASSWORD=secret123
export AMPLIHACK_API__KEY=api-key-here
```

```python
config = ConfigManager("config/default.yaml")

# Password comes from environment
db_password = config.get("database.password")

# API key comes from environment
api_key = config.get("api.key")
```

### Pattern: Dynamic Configuration Updates

```python
from amplihack.config import ConfigManager

config = ConfigManager("config/default.yaml")

# Runtime configuration changes
config.set("cache.enabled", False)
config.set("server.workers", 8)

# Changes are immediate
cache_enabled = config.get("cache.enabled")  # False

# Reload to reset
config.reload()
cache_enabled = config.get("cache.enabled")  # Back to YAML value
```

### Pattern: Feature Flags

```yaml
# config/default.yaml
features:
  new_ui: false
  beta_api: false
  experimental_cache: false
```

```python
config = ConfigManager("config/default.yaml")

def is_feature_enabled(feature_name):
    return config.get(f"features.{feature_name}", default=False)

# Use in code
if is_feature_enabled("new_ui"):
    render_new_ui()
else:
    render_old_ui()
```

Enable features via environment:

```bash
export AMPLIHACK_FEATURES__NEW_UI=true
```

## Troubleshooting

### Configuration file not found

**Problem**: `ConfigFileError: Configuration file not found: config/default.yaml`

**Solution**: Ensure the file path is relative to where you run the script:

```python
import os
from pathlib import Path

# Use absolute path
config_dir = Path(__file__).parent / "config"
config_file = config_dir / "default.yaml"

config = ConfigManager(str(config_file))
```

### Environment variables not working

**Problem**: Environment variable overrides not taking effect.

**Solution**: Check the naming convention:

- Prefix must be `AMPLIHACK_`
- Use double underscore `__` for nesting
- Keys are case-insensitive

```bash
# Wrong
export DATABASE_HOST=localhost

# Correct
export AMPLIHACK_DATABASE__HOST=localhost
```

### Type parsing issues

**Problem**: Environment variable parsed as wrong type.

**Solution**: Check the value format:

```bash
# Integer
export AMPLIHACK_SERVER__PORT=8000  # Correct
export AMPLIHACK_SERVER__PORT="8000"  # Also works

# Boolean
export AMPLIHACK_DEBUG=true  # Correct
export AMPLIHACK_DEBUG=True  # Also works
export AMPLIHACK_DEBUG=1  # Also works

# String
export AMPLIHACK_DATABASE__HOST=localhost  # Correct

# List (use JSON)
export AMPLIHACK_LOGGING__HANDLERS='["console", "file"]'
```

### Thread safety concerns

**Problem**: Concurrent access to configuration.

**Solution**: ConfigManager is thread-safe by default. No additional locking needed:

```python
import threading
from amplihack.config import ConfigManager

config = ConfigManager("config/default.yaml")

def worker():
    # Safe: Multiple threads can read
    value = config.get("database.host")

    # Safe: Multiple threads can write
    config.set("thread.status", "active")

threads = [threading.Thread(target=worker) for _ in range(10)]
for t in threads:
    t.start()
```

## Next Steps

- [ConfigManager API Reference](../reference/config-manager.md) - Complete API documentation
- [Environment Variables Guide](./environment-variables.md) - Advanced override patterns
- [Thread Safety Concepts](../concepts/config-thread-safety.md) - Understanding the locking
