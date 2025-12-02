# Configuration Fix Template

**Usage**: 12% of all fixes - Environment variables, config file syntax, missing settings, version conflicts

## Problem Pattern Recognition

### Triggers

- Environment variable not set
- Configuration file syntax errors
- Missing configuration values
- Invalid configuration format
- Version mismatch in configs
- Default configuration issues

### Error Indicators

```bash
# Common config error patterns
"environment variable not set"
"configuration file not found"
"invalid syntax in config"
"missing required setting"
"unknown configuration option"
"permission denied reading config"
"YAML/JSON parsing error"
```

## Quick Assessment (30 seconds)

### Step 1: Config Type Identification

```bash
# What type of configuration?
# - Environment variables (.env, shell)
# - Config files (JSON, YAML, TOML, INI)
# - Application settings
# - Build configuration
# - CI/CD configuration
```

### Step 2: Error Location

```bash
# Where is the error occurring?
grep -r "config\|setting\|environment" error_log
find . -name "*.env*" -o -name "config.*" -o -name "*.config.*"
```

### Step 3: Scope Assessment

- **Local**: Development environment only
- **CI/CD**: Build/deployment environment
- **Production**: Runtime configuration
- **Global**: System-wide settings

## Solution Steps by Config Type

### Environment Variables

```bash
# Step 1: Identify missing variables
printenv | grep -i app_name
env | sort

# Step 2: Check .env files
ls -la .env*
cat .env.example  # Template file

# Step 3: Set missing variables
export MISSING_VAR="value"
echo "MISSING_VAR=value" >> .env

# Step 4: Verify loading
python -c "import os; print(os.getenv('MISSING_VAR'))"
```

### JSON Configuration Fixes

```json
// Before (syntax error)
{
  "setting1": "value1",
  "setting2": "value2",  // Trailing comma
}

// After (valid JSON)
{
  "setting1": "value1",
  "setting2": "value2"
}

// Validation
cat config.json | python -m json.tool
```

### YAML Configuration Fixes

```yaml
# Before (indentation error)
database:
  host: localhost
   port: 5432  # Wrong indentation

# After (correct YAML)
database:
  host: localhost
  port: 5432

# Validation
python -c "import yaml; yaml.safe_load(open('config.yaml'))"
```

### Application Configuration

```python
# Before (missing settings)
config = {
    "database_url": os.getenv("DATABASE_URL")  # Could be None
}

# After (with defaults and validation)
config = {
    "database_url": os.getenv("DATABASE_URL", "sqlite:///default.db"),
    "debug": os.getenv("DEBUG", "false").lower() == "true",
    "port": int(os.getenv("PORT", "8000"))
}

# Validation
required_settings = ["database_url", "secret_key"]
for setting in required_settings:
    if not config.get(setting):
        raise ValueError(f"Missing required setting: {setting}")
```

## Validation Steps

### 1. Syntax Validation

```bash
# JSON validation
cat config.json | python -m json.tool > /dev/null
jq . config.json > /dev/null

# YAML validation
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# TOML validation
python -c "import tomli; tomli.load(open('config.toml', 'rb'))"
```

### 2. Content Validation

```bash
# Check required settings present
python -c "
import json
config = json.load(open('config.json'))
required = ['database_url', 'secret_key']
missing = [k for k in required if k not in config]
if missing: print(f'Missing: {missing}')
else: print('All required settings present')
"
```

### 3. Application Integration Test

```bash
# Test config loading in application
python -c "from app import load_config; print(load_config())"
npm run config:validate
```

## Common Fix Patterns

### Pattern 1: Environment Variable Template

```bash
# Create .env from template
cp .env.example .env

# Fill in missing values
sed -i 's/YOUR_SECRET_KEY/actual_secret_key/' .env
sed -i 's/YOUR_DATABASE_URL/actual_db_url/' .env
```

### Pattern 2: Config Hierarchy

```python
# Proper config loading order
import os
import json

def load_config():
    # 1. Default config
    config = {
        "debug": False,
        "port": 8000,
        "database_url": "sqlite:///default.db"
    }

    # 2. Config file override
    try:
        with open("config.json") as f:
            config.update(json.load(f))
    except FileNotFoundError:
        pass

    # 3. Environment variable override
    if os.getenv("DEBUG"):
        config["debug"] = os.getenv("DEBUG").lower() == "true"
    if os.getenv("PORT"):
        config["port"] = int(os.getenv("PORT"))
    if os.getenv("DATABASE_URL"):
        config["database_url"] = os.getenv("DATABASE_URL")

    return config
```

### Pattern 3: Config Validation

```python
# Add configuration validation
from pydantic import BaseModel, validator
from typing import Optional

class AppConfig(BaseModel):
    database_url: str
    debug: bool = False
    port: int = 8000
    secret_key: str

    @validator('port')
    def port_must_be_valid(cls, v):
        if not 1024 <= v <= 65535:
            raise ValueError('Port must be between 1024 and 65535')
        return v

    @validator('secret_key')
    def secret_key_must_be_long(cls, v):
        if len(v) < 32:
            raise ValueError('Secret key must be at least 32 characters')
        return v

# Usage
config_dict = load_config()
config = AppConfig(**config_dict)  # Validates automatically
```

### Pattern 4: Development vs Production

```python
# Environment-aware configuration
import os

def get_config():
    env = os.getenv("ENVIRONMENT", "development")

    if env == "production":
        return {
            "database_url": os.getenv("DATABASE_URL"),
            "debug": False,
            "secret_key": os.getenv("SECRET_KEY"),
        }
    elif env == "testing":
        return {
            "database_url": "sqlite:///test.db",
            "debug": True,
            "secret_key": "test_secret",  # pragma: allowlist secret
        }
    else:  # development
        return {
            "database_url": "sqlite:///dev.db",
            "debug": True,
            "secret_key": "dev_secret",  # pragma: allowlist secret
        }
```

## Tool-Specific Solutions

### Docker Configuration

```dockerfile
# Environment variables in Dockerfile
ENV APP_ENV=production
ENV PORT=8000

# Multi-stage for different environments
FROM base as development
ENV DEBUG=true
COPY config/dev.json /app/config.json

FROM base as production
ENV DEBUG=false
COPY config/prod.json /app/config.json
```

### Docker Compose

```yaml
# Environment-specific compose files
# docker-compose.yml (base)
version: '3.8'
services:
  app:
    environment:
      - DATABASE_URL=${DATABASE_URL}

# docker-compose.override.yml (development)
version: '3.8'
services:
  app:
    environment:
      - DEBUG=true
      - DATABASE_URL=sqlite:///dev.db
```

### CI/CD Configuration

```yaml
# GitHub Actions environment-specific configs
name: Deploy
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production
    env:
      DATABASE_URL: ${{ secrets.DATABASE_URL }}
      SECRET_KEY: ${{ secrets.SECRET_KEY }}
```

## Integration Points

### With Fix Agent

- Use QUICK mode for syntax errors
- Use DIAGNOSTIC mode for complex config issues
- Escalate environment setup to COMPREHENSIVE

### With Main Workflow

- Apply during Step 3 (Setup environment)
- Use in Step 5 (Implementation)
- Integrate with Step 7 (Pre-commit hooks)

### With CI Diagnostic Workflow

- Hand off CI-specific configuration issues
- Use for deployment configuration problems
- Integrate with environment setup fixes

## Quick Reference

### 3-Minute Fix Checklist

- [ ] Identify config type and location
- [ ] Check syntax and format
- [ ] Verify required values present
- [ ] Test config loading
- [ ] Validate in application context

### Emergency Commands

```bash
# Quick syntax check
python -m json.tool config.json
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# Quick environment check
printenv | grep -i app_name
env | sort

# Quick file permissions
chmod 644 config.json
chmod 600 .env  # Sensitive files
```

## Success Patterns

### High-Success Scenarios

- JSON/YAML syntax errors (98% success)
- Missing environment variables (95% success)
- File permission issues (90% success)
- Default value settings (88% success)

### Challenging Scenarios

- Complex configuration hierarchies (60% success)
- Environment-specific differences (55% success)
- Security configuration issues (45% success)
- Multi-service configuration sync (50% success)

## Security Considerations

### Sensitive Configuration

```bash
# Never commit sensitive values
echo ".env" >> .gitignore
echo "config/production.json" >> .gitignore

# Use environment variables for secrets
export SECRET_KEY=$(openssl rand -hex 32)

# Validate file permissions
find . -name "*.env" -exec chmod 600 {} \;
```

### Configuration Encryption

```python
# Encrypt sensitive config values
from cryptography.fernet import Fernet

def encrypt_config(config, key):
    f = Fernet(key)
    encrypted = {}
    for k, v in config.items():
        if k in ['secret_key', 'password', 'api_key']:
            encrypted[k] = f.encrypt(v.encode()).decode()
        else:
            encrypted[k] = v
    return encrypted
```

## Prevention Strategies

### Development Practices

- Always provide .env.example
- Document all configuration options
- Use configuration validation
- Test with minimal configuration

### Deployment Practices

- Environment-specific config files
- Configuration management tools
- Automated configuration validation
- Configuration change monitoring

## Advanced Scenarios

### Dynamic Configuration

```python
# Configuration that can be updated at runtime
import json
import threading
import time

class DynamicConfig:
    def __init__(self, config_file):
        self.config_file = config_file
        self.config = {}
        self.lock = threading.Lock()
        self.load_config()

    def load_config(self):
        with self.lock:
            with open(self.config_file) as f:
                self.config = json.load(f)

    def get(self, key, default=None):
        with self.lock:
            return self.config.get(key, default)
```

### Configuration Testing

```python
# Test configuration in different scenarios
import pytest

def test_config_validation():
    # Test valid configuration
    config = {"port": 8000, "debug": False}
    assert validate_config(config) == True

    # Test invalid configuration
    config = {"port": "invalid"}
    with pytest.raises(ValueError):
        validate_config(config)
```

Remember: Configuration issues often indicate missing documentation or setup instructions. Fix the immediate problem but consider improving the setup experience.
