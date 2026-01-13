# Configuration Fix Template

> **Coverage**: ~12% of all fixes
> **Target Time**: 30-60 seconds assessment, 2-5 minutes resolution

## Problem Pattern Recognition

### Trigger Indicators

```
Error patterns:
- "config", "configuration", "settings"
- "environment variable", "env", "ENV"
- "YAML", "JSON", "TOML" parse errors
- "KeyError", "missing key", "not found"
- "invalid value", "validation error"
- ".env", "config.yaml", "settings.py"
```

### Error Categories

| Category | Frequency | Indicators |
|----------|-----------|------------|
| Environment Variables | 35% | KeyError, os.environ, missing env |
| YAML/JSON Syntax | 25% | parse error, unexpected token, indentation |
| Settings Mismatch | 25% | wrong type, invalid value, schema error |
| Secret Management | 15% | authentication, credential, token |

## Quick Assessment (30-60 sec)

### Step 1: Identify Configuration Type

```bash
# What kind of config?
# - Environment variables (.env, os.environ)
# - YAML files (config.yaml, docker-compose.yml)
# - JSON files (package.json, tsconfig.json)
# - TOML files (pyproject.toml, Cargo.toml)
# - Python settings (settings.py, config.py)
```

### Step 2: Locate the Error Source

```bash
# Check for config files
ls -la *.yaml *.yml *.json *.toml .env* 2>/dev/null

# Search for config references
grep -r "config\|settings\|environ" --include="*.py" | head -20
```

## Solution Steps by Category

### Environment Variables

**Missing Environment Variable**
```python
# Bad: Will crash if not set
api_key = os.environ["API_KEY"]

# Better: Default value
api_key = os.environ.get("API_KEY", "default-key")

# Best: Required with clear error
api_key = os.environ.get("API_KEY")
if not api_key:
    raise ValueError("API_KEY environment variable is required")
```

**Setting Environment Variables**
```bash
# Local development (.env file)
echo "API_KEY=your-key-here" >> .env

# Shell session
export API_KEY="your-key-here"

# In Python (for testing)
os.environ["API_KEY"] = "test-value"
```

**Loading .env Files**
```python
# Using python-dotenv
from dotenv import load_dotenv
load_dotenv()  # Load from .env file

# Load specific file
load_dotenv(".env.local")

# Override existing
load_dotenv(override=True)
```

**Environment-Specific Files**
```bash
# Pattern: .env.{environment}
.env              # Base/default
.env.local        # Local overrides (gitignored)
.env.development  # Dev settings
.env.production   # Prod settings
.env.test         # Test settings
```

### YAML/JSON Syntax Errors

**Common YAML Mistakes**
```yaml
# Wrong: Tabs instead of spaces
key:
	value  # TAB - will fail

# Right: Use spaces (2 or 4)
key:
  value  # SPACES

# Wrong: Missing quotes on special chars
message: @user said: hello

# Right: Quote special values
message: "@user said: hello"

# Wrong: Incorrect list syntax
items: item1, item2

# Right: Proper list
items:
  - item1
  - item2

# Wrong: Anchors/references issue
base: &base
  key: value
derived:
  <<: *undefined  # Reference doesn't exist
```

**Validate YAML**
```bash
# Python validation
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# Using yq
yq eval '.' config.yaml

# Online: yamllint.com
```

**Common JSON Mistakes**
```json
// Wrong: Trailing comma
{
  "key": "value",
}

// Wrong: Single quotes
{
  'key': 'value'
}

// Wrong: Unquoted keys
{
  key: "value"
}

// Wrong: Comments (not valid JSON)
{
  "key": "value"  // comment
}
```

**Validate JSON**
```bash
# Python validation
python -c "import json; json.load(open('config.json'))"

# Using jq
jq '.' config.json

# Prettier format
npx prettier --write config.json
```

### Settings Mismatches

**Type Mismatches**
```python
# Error: Expected int, got str
port = os.environ.get("PORT")  # Returns string "8080"
server.listen(port)  # Expects int

# Fix: Convert types
port = int(os.environ.get("PORT", "8080"))

# Better: Use pydantic for validation
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    port: int = 8080
    debug: bool = False
    
    class Config:
        env_file = ".env"
```

**Schema Validation**
```python
# Using pydantic for config validation
from pydantic import BaseModel, validator

class DatabaseConfig(BaseModel):
    host: str
    port: int
    name: str
    
    @validator('port')
    def port_must_be_valid(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError('Port must be between 1 and 65535')
        return v
```

**Configuration Hierarchy**
```python
# Priority: CLI args > env vars > config file > defaults
import os
from dataclasses import dataclass

@dataclass
class Config:
    debug: bool = False
    port: int = 8080
    
    @classmethod
    def load(cls, config_file=None, **overrides):
        # Start with defaults
        config = cls()
        
        # Load from file if exists
        if config_file:
            config = cls(**load_yaml(config_file))
        
        # Override from environment
        if os.environ.get("DEBUG"):
            config.debug = os.environ["DEBUG"].lower() == "true"
        
        # Override from explicit args
        for key, value in overrides.items():
            setattr(config, key, value)
        
        return config
```

### Secret Management Issues

**Common Secret Problems**
```bash
# Problem: Secret in code
API_KEY = "sk-abc123..."  # Never do this!

# Problem: Secret in git
git add .env  # Don't commit secrets!

# Solution: Use .gitignore
echo ".env" >> .gitignore
echo ".env.local" >> .gitignore
echo "*.secret" >> .gitignore
```

**Secret Sources**
```python
# Environment variable (simplest)
secret = os.environ["API_KEY"]

# AWS Secrets Manager
import boto3
client = boto3.client('secretsmanager')
secret = client.get_secret_value(SecretId='my-secret')

# Azure Key Vault
from azure.keyvault.secrets import SecretClient
secret = client.get_secret("my-secret")

# HashiCorp Vault
import hvac
client = hvac.Client()
secret = client.secrets.kv.read_secret("my-secret")
```

**Secret Rotation Handling**
```python
# Cache with expiration
from functools import lru_cache
import time

@lru_cache(maxsize=1)
def get_secret_cached(cache_key=None):
    # cache_key changes every hour, forcing refresh
    return fetch_secret_from_vault()

def get_secret():
    cache_key = int(time.time() / 3600)  # Changes hourly
    return get_secret_cached(cache_key)
```

## Environment-Specific Debugging

### Local Development

```bash
# Check what's loaded
python -c "import os; print(dict(os.environ))" | grep -i api

# Verify .env is loaded
python -c "from dotenv import dotenv_values; print(dotenv_values('.env'))"

# Debug config loading
DEBUG=true python -c "from myapp.config import settings; print(settings)"
```

### Docker/Container

```bash
# Check env in container
docker exec container_name env | grep API

# Pass env file
docker run --env-file .env myimage

# Check compose env
docker compose config  # Shows resolved config
```

### CI/CD (GitHub Actions)

```yaml
# Set secret in workflow
env:
  API_KEY: ${{ secrets.API_KEY }}

# Debug (don't print actual secrets!)
- run: |
    if [ -z "$API_KEY" ]; then
      echo "API_KEY is not set!"
      exit 1
    fi
    echo "API_KEY is set (length: ${#API_KEY})"
```

## Configuration Validation

### Pre-Runtime Validation

```python
# Validate on startup
def validate_config(config):
    errors = []
    
    if not config.api_key:
        errors.append("API_KEY is required")
    
    if config.port < 1 or config.port > 65535:
        errors.append(f"Invalid port: {config.port}")
    
    if config.environment not in ["dev", "staging", "prod"]:
        errors.append(f"Unknown environment: {config.environment}")
    
    if errors:
        raise ValueError(f"Configuration errors: {'; '.join(errors)}")
```

### Schema-Based Validation

```python
# Using pydantic-settings
from pydantic_settings import BaseSettings
from pydantic import Field, validator

class Settings(BaseSettings):
    api_key: str = Field(..., min_length=10)
    port: int = Field(8080, ge=1, le=65535)
    debug: bool = False
    environment: str = "development"
    
    @validator('environment')
    def validate_env(cls, v):
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"Must be one of: {allowed}")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Will raise ValidationError on invalid config
settings = Settings()
```

## Validation Steps

### Quick Config Check

```bash
# 1. Verify file syntax
python -c "import yaml; yaml.safe_load(open('config.yaml'))"
python -c "import json; json.load(open('config.json'))"
python -c "import tomllib; tomllib.load(open('pyproject.toml', 'rb'))"

# 2. Check environment
env | grep -E "^(API|DB|SECRET|CONFIG)" | head

# 3. Test config loading
python -c "from myapp.config import settings; print(settings)"
```

### Post-Fix Validation

```bash
# 1. Restart application
python main.py

# 2. Check health endpoint
curl localhost:8080/health

# 3. Verify feature works
curl localhost:8080/api/test
```

## Escalation Criteria

### Escalate When

- Secrets need rotation or re-provisioning
- Configuration requires infrastructure changes
- Schema changes affect multiple services
- Unclear which environment is being used
- Configuration from external service (Vault, SSM)

### Information to Gather

```
1. Which config file/variable is problematic
2. Expected value type and format
3. Where the config should come from
4. Environment (local, CI, staging, prod)
5. Recent changes to config or deployment
```

## Quick Reference

### Common Config Patterns

```python
# Simple with defaults
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///local.db")

# Required with clear error
def require_env(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise RuntimeError(f"Required environment variable {key} is not set")
    return value

# Type-safe with pydantic
from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    database_url: str
    class Config:
        env_file = ".env"
```

### Config File Locations (Priority Order)

```
1. Command line arguments
2. Environment variables
3. .env.local (gitignored)
4. .env.{environment}
5. .env
6. config.yaml / settings.py defaults
```

### Debug Checklist

```
[ ] Is the .env file in the right directory?
[ ] Is python-dotenv installed and load_dotenv() called?
[ ] Are variable names exactly matching (case-sensitive)?
[ ] Is the file readable (permissions)?
[ ] Is there a typo in the variable name?
[ ] Is the value the right type?
```
