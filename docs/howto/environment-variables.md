# Advanced Environment Variable Configuration

Guide to using environment variables for configuration overrides in amplihack applications.

## Goal

Master environment variable configuration patterns for different deployment scenarios, from local development to production deployments.

## Prerequisites

- ConfigManager set up (see [Configuration Setup Guide](./configuration-setup.md))
- Basic understanding of environment variables
- Shell access (bash, zsh, or equivalent)

## Basic Syntax

### Standard Format

```bash
AMPLIHACK_KEY=value
AMPLIHACK_SECTION__KEY=value
AMPLIHACK_SECTION__SUBSECTION__KEY=value
```

**Rules**:

- Prefix: `AMPLIHACK_` (required)
- Separator: Double underscore `__` (not single `_`)
- Nesting: Each `__` represents one level deeper

### Examples

```bash
# Top-level key
export AMPLIHACK_DEBUG=true

# One level deep
export AMPLIHACK_DATABASE__HOST=localhost

# Two levels deep
export AMPLIHACK_CACHE__REDIS__HOST=localhost

# Three levels deep
export AMPLIHACK_LOGGING__HANDLERS__FILE__PATH=/var/log/app.log
```

## Type Parsing

Environment variables are automatically parsed to appropriate types.

### String Values

```bash
# Plain strings
export AMPLIHACK_DATABASE__NAME=amplihack_prod
export AMPLIHACK_API__ENDPOINT=https://api.example.com
```

```python
config.get("database.name")  # "amplihack_prod" (str)
config.get("api.endpoint")   # "https://api.example.com" (str)
```

### Integer Values

```bash
# Numeric values without decimal point
export AMPLIHACK_SERVER__PORT=8000
export AMPLIHACK_DATABASE__POOL_SIZE=50
export AMPLIHACK_CACHE__MAX_SIZE=1000
```

```python
config.get("server.port")         # 8000 (int)
config.get("database.pool_size")  # 50 (int)
config.get("cache.max_size")      # 1000 (int)
```

### Float Values

```bash
# Numeric values with decimal point
export AMPLIHACK_CACHE__TTL=3600.5
export AMPLIHACK_API__TIMEOUT=30.0
export AMPLIHACK_RATE__LIMIT=0.5
```

```python
config.get("cache.ttl")     # 3600.5 (float)
config.get("api.timeout")   # 30.0 (float)
config.get("rate.limit")    # 0.5 (float)
```

### Boolean Values

```bash
# Multiple accepted formats
export AMPLIHACK_DEBUG=true     # Lowercase
export AMPLIHACK_CACHE__ENABLED=True    # Capitalized
export AMPLIHACK_LOGGING__VERBOSE=yes   # Yes/no
export AMPLIHACK_FEATURES__BETA=1       # 1/0
```

All of these work:

- `true`, `True`, `TRUE`
- `false`, `False`, `FALSE`
- `yes`, `Yes`, `YES`
- `no`, `No`, `NO`
- `1` (true), `0` (false)

```python
config.get("debug")                # True (bool)
config.get("cache.enabled")        # True (bool)
config.get("logging.verbose")      # True (bool)
config.get("features.beta")        # True (bool)
```

### List Values

```bash
# Use JSON array format (must quote)
export AMPLIHACK_LOGGING__HANDLERS='["console", "file"]'
export AMPLIHACK_ALLOWED__IPS='["10.0.0.1", "10.0.0.2"]'
export AMPLIHACK_PORTS='[8000, 8001, 8002]'
```

```python
config.get("logging.handlers")  # ["console", "file"] (list)
config.get("allowed.ips")       # ["10.0.0.1", "10.0.0.2"] (list)
config.get("ports")             # [8000, 8001, 8002] (list)
```

### Dictionary Values

```bash
# Use JSON object format (must quote)
export AMPLIHACK_REDIS='{"host": "localhost", "port": 6379}'
```

```python
config.get("redis")  # {"host": "localhost", "port": 6379} (dict)
```

## Deployment Patterns

### Local Development

Create `.env` file for local overrides:

```bash
# .env (add to .gitignore)
AMPLIHACK_DEBUG=true
AMPLIHACK_DATABASE__HOST=localhost
AMPLIHACK_DATABASE__PORT=5432
AMPLIHACK_LOG__LEVEL=DEBUG
```

Load in application:

```python
from pathlib import Path
from amplihack.config import ConfigManager

# Load .env file
env_file = Path(".env")
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line and not line.startswith("#"):
            key, value = line.split("=", 1)
            os.environ[key] = value

config = ConfigManager("config/default.yaml")
```

### Docker Containers

Use Docker environment variables:

```dockerfile
# Dockerfile
FROM python:3.11

# Set build-time config
ENV AMPLIHACK_DEBUG=false
ENV AMPLIHACK_SERVER__PORT=8000

COPY . /app
WORKDIR /app

CMD ["python", "main.py"]
```

Override at runtime:

```bash
docker run \
  -e AMPLIHACK_DATABASE__HOST=db.example.com \
  -e AMPLIHACK_DATABASE__PORT=5432 \
  -e AMPLIHACK_LOG__LEVEL=INFO \
  myapp:latest
```

### Docker Compose

```yaml
# docker-compose.yml
version: "3.8"

services:
  app:
    build: .
    environment:
      AMPLIHACK_DEBUG: "false"
      AMPLIHACK_DATABASE__HOST: db
      AMPLIHACK_DATABASE__PORT: "5432"
      AMPLIHACK_CACHE__REDIS__HOST: redis
    depends_on:
      - db
      - redis

  db:
    image: postgres:15

  redis:
    image: redis:7
```

### Kubernetes

Use ConfigMaps and Secrets:

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  AMPLIHACK_DEBUG: "false"
  AMPLIHACK_SERVER__PORT: "8000"
  AMPLIHACK_DATABASE__HOST: postgres-service
  AMPLIHACK_CACHE__REDIS__HOST: redis-service
---
# secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
type: Opaque
stringData:
  AMPLIHACK_DATABASE__PASSWORD: super-secret
  AMPLIHACK_API__KEY: api-key-here
---
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  template:
    spec:
      containers:
        - name: app
          image: myapp:latest
          envFrom:
            - configMapRef:
                name: app-config
            - secretRef:
                name: app-secrets
```

### CI/CD Pipelines

#### GitHub Actions

```yaml
# .github/workflows/test.yml
name: Test

on: [push]

jobs:
  test:
    runs-on: ubuntu-latest
    env:
      AMPLIHACK_DEBUG: true
      AMPLIHACK_DATABASE__HOST: localhost
      AMPLIHACK_DATABASE__PORT: 5432

    steps:
      - uses: actions/checkout@v3

      - name: Run tests
        env:
          AMPLIHACK_API__KEY: ${{ secrets.API_KEY }}
        run: pytest
```

#### GitLab CI

```yaml
# .gitlab-ci.yml
test:
  stage: test
  variables:
    AMPLIHACK_DEBUG: "true"
    AMPLIHACK_DATABASE__HOST: localhost
  script:
    - export AMPLIHACK_API__KEY=$API_KEY_SECRET
    - pytest
```

## Security Patterns

### Secrets Management

**Never commit secrets to version control:**

```yaml
# config/default.yaml
# ❌ WRONG - Secret in YAML
database:
  host: localhost
  password: super-secret  # Don't do this!

# ✅ RIGHT - No secret in YAML
database:
  host: localhost
  # password loaded from environment
```

**Always use environment variables for secrets:**

```bash
export AMPLIHACK_DATABASE__PASSWORD=super-secret
export AMPLIHACK_API__KEY=api-key-here
export AMPLIHACK_JWT__SECRET=jwt-secret-key
```

### AWS Secrets Manager

```python
import boto3
import json
from amplihack.config import ConfigManager

def load_secrets_from_aws():
    """Load secrets from AWS Secrets Manager"""
    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId="prod/amplihack/db")

    secrets = json.loads(response["SecretString"])

    # Set as environment variables
    os.environ["AMPLIHACK_DATABASE__PASSWORD"] = secrets["password"]
    os.environ["AMPLIHACK_DATABASE__USER"] = secrets["username"]

# Load secrets before initializing config
load_secrets_from_aws()
config = ConfigManager("config/production.yaml")
```

### Azure Key Vault

```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

def load_secrets_from_azure():
    """Load secrets from Azure Key Vault"""
    credential = DefaultAzureCredential()
    client = SecretClient(
        vault_url="https://myvault.vault.azure.net/",
        credential=credential
    )

    # Load secrets
    db_password = client.get_secret("database-password").value
    api_key = client.get_secret("api-key").value

    os.environ["AMPLIHACK_DATABASE__PASSWORD"] = db_password
    os.environ["AMPLIHACK_API__KEY"] = api_key

load_secrets_from_azure()
config = ConfigManager("config/production.yaml")
```

### HashiCorp Vault

```python
import hvac

def load_secrets_from_vault():
    """Load secrets from HashiCorp Vault"""
    client = hvac.Client(url="http://vault:8200")
    client.token = os.getenv("VAULT_TOKEN")

    # Read secrets
    secrets = client.secrets.kv.v2.read_secret_version(
        path="amplihack/prod"
    )

    data = secrets["data"]["data"]
    os.environ["AMPLIHACK_DATABASE__PASSWORD"] = data["db_password"]
    os.environ["AMPLIHACK_API__KEY"] = data["api_key"]

load_secrets_from_vault()
config = ConfigManager("config/production.yaml")
```

## Advanced Patterns

### Multi-Environment Configuration

```python
import os
from amplihack.config import ConfigManager

def get_environment():
    """Determine current environment"""
    return os.getenv("ENVIRONMENT", "development")

def load_config():
    """Load config for current environment"""
    env = get_environment()

    # Base config
    config = ConfigManager(f"config/{env}.yaml")

    # Environment-specific overrides via env vars
    # AMPLIHACK_* variables automatically applied

    return config

config = load_config()
```

Run with different environments:

```bash
# Development
ENVIRONMENT=development python main.py

# Production
ENVIRONMENT=production \
  AMPLIHACK_DATABASE__HOST=prod.db.com \
  AMPLIHACK_LOG__LEVEL=WARNING \
  python main.py
```

### Feature Flags

```bash
# Enable/disable features via environment
export AMPLIHACK_FEATURES__NEW_UI=true
export AMPLIHACK_FEATURES__BETA_API=false
export AMPLIHACK_FEATURES__EXPERIMENTAL=true
```

```python
from amplihack.config import ConfigManager

config = ConfigManager("config/default.yaml")

def is_feature_enabled(feature):
    """Check if feature is enabled"""
    return config.get(f"features.{feature}", default=False)

# Usage
if is_feature_enabled("new_ui"):
    render_new_ui()
else:
    render_legacy_ui()
```

### Dynamic Configuration Reloading

```python
import signal
from amplihack.config import ConfigManager

config = ConfigManager("config/default.yaml")

def reload_config_handler(signum, frame):
    """Reload config on SIGHUP"""
    print("Reloading configuration...")
    config.reload()
    print("Configuration reloaded")

# Register signal handler
signal.signal(signal.SIGHUP, reload_config_handler)

# Send SIGHUP to reload: kill -HUP <pid>
```

### Validation After Environment Load

```python
from amplihack.config import ConfigManager, ConfigValidationError

config = ConfigManager("config/production.yaml")

# Validate after environment variables applied
try:
    config.validate()
except ConfigValidationError as e:
    print(f"Configuration invalid: {e}")
    print("Required environment variables:")
    print("  - AMPLIHACK_DATABASE__PASSWORD")
    print("  - AMPLIHACK_API__KEY")
    exit(1)
```

## Troubleshooting

### Environment variable not taking effect

**Problem**: Set environment variable but config still shows old value.

**Check**:

```python
import os
from amplihack.config import ConfigManager

# Verify environment variable is set
print(os.getenv("AMPLIHACK_DATABASE__HOST"))

# Verify config sees it
config = ConfigManager("config/default.yaml")
print(config.get("database.host"))
```

**Common causes**:

- Wrong prefix (must be `AMPLIHACK_`)
- Wrong separator (must be `__` not `_`)
- Variable not exported (`export` required in bash)
- Variable set after process started

### Type parsing incorrect

**Problem**: Boolean parsed as string or vice versa.

```bash
# Wrong
export AMPLIHACK_DEBUG="true"  # Parsed as string "true"

# Right
export AMPLIHACK_DEBUG=true    # Parsed as boolean True
```

### Complex structures not working

**Problem**: Nested structures don't parse correctly.

```bash
# Wrong - shell interprets braces
export AMPLIHACK_CONFIG={"key": "value"}

# Right - quoted JSON
export AMPLIHACK_CONFIG='{"key": "value"}'
```

### Environment precedence confusion

Remember the order:

1. Environment variables (highest)
2. `config.set()` calls
3. YAML file
4. Default in `get()`

```python
# YAML: debug = false
# ENV: AMPLIHACK_DEBUG=true

config.get("debug")  # Returns: True (env wins)

config.set("debug", False)
config.get("debug")  # Returns: False (set wins)

config.reload()
config.get("debug")  # Returns: True (env wins again)
```

## Best Practices

1. **Use `.env` for local development** - Never commit to git
2. **Use secrets managers for production** - Never hardcode secrets
3. **Validate after loading** - Catch configuration errors early
4. **Document required variables** - Make deployment easier
5. **Use typed parsing** - Let ConfigManager handle type conversion
6. **Prefix everything with AMPLIHACK\_** - Avoid naming conflicts
7. **Use double underscores for nesting** - Stay consistent

## See Also

- [Configuration Setup Guide](./configuration-setup.md) - Initial setup
- [ConfigManager API Reference](../reference/config-manager.md) - Complete API
- [Thread Safety Concepts](../concepts/config-thread-safety.md) - Understanding locks
