# Infrastructure as Code and Deployment Automation

Comprehensive guide for infrastructure automation, containerization, and deployment pipelines.

## When to Use

- Setting up new project infrastructure
- Automating deployments with CI/CD
- Containerizing applications
- Managing cloud resources
- Handling secrets and configuration
- Creating reproducible environments

## Terraform Basics

### Project Structure

```
infrastructure/
├── main.tf           # Primary configuration
├── variables.tf      # Input variables
├── outputs.tf        # Output values
├── providers.tf      # Provider configuration
├── versions.tf       # Version constraints
├── terraform.tfvars  # Variable values (gitignored)
└── modules/
    ├── networking/
    ├── compute/
    └── storage/
```

### Provider Configuration

```hcl
# providers.tf
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  backend "azurerm" {
    resource_group_name  = "tfstate-rg"
    storage_account_name = "tfstatestorage"
    container_name       = "tfstate"
    key                  = "terraform.tfstate"
  }
}

provider "azurerm" {
  features {}
}

provider "aws" {
  region = var.aws_region
}
```

### Variables and Outputs

```hcl
# variables.tf
variable "environment" {
  type        = string
  description = "Deployment environment (dev, staging, prod)"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "instance_count" {
  type        = number
  default     = 2
  description = "Number of instances to create"
}

variable "tags" {
  type = map(string)
  default = {
    managed_by = "terraform"
  }
}

# outputs.tf
output "instance_ips" {
  value       = aws_instance.app[*].public_ip
  description = "Public IPs of application instances"
}

output "load_balancer_dns" {
  value       = aws_lb.main.dns_name
  description = "DNS name of the load balancer"
  sensitive   = false
}
```

### Resource Patterns

```hcl
# Conditional creation
resource "aws_instance" "bastion" {
  count = var.enable_bastion ? 1 : 0
  
  ami           = var.ami_id
  instance_type = "t3.micro"
  
  tags = merge(var.tags, {
    Name = "${var.environment}-bastion"
  })
}

# For each with map
resource "aws_security_group_rule" "ingress" {
  for_each = var.ingress_rules
  
  type              = "ingress"
  from_port         = each.value.from_port
  to_port           = each.value.to_port
  protocol          = each.value.protocol
  cidr_blocks       = each.value.cidr_blocks
  security_group_id = aws_security_group.main.id
}

# Dynamic blocks
resource "aws_security_group" "main" {
  name = "${var.environment}-sg"
  
  dynamic "ingress" {
    for_each = var.ingress_ports
    content {
      from_port   = ingress.value
      to_port     = ingress.value
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
    }
  }
}
```

### Terraform Workflow

```bash
# Initialize (download providers, setup backend)
terraform init

# Format code
terraform fmt -recursive

# Validate configuration
terraform validate

# Plan changes
terraform plan -out=tfplan

# Apply changes
terraform apply tfplan

# Destroy resources
terraform destroy

# Import existing resources
terraform import aws_instance.example i-1234567890abcdef0
```

## Bicep/ARM Templates

### Bicep Structure

```bicep
// main.bicep
targetScope = 'resourceGroup'

@description('Environment name')
@allowed(['dev', 'staging', 'prod'])
param environment string

@description('Location for resources')
param location string = resourceGroup().location

@secure()
@description('Database password')
param dbPassword string

// Variables
var appName = 'myapp-${environment}'
var tags = {
  environment: environment
  managedBy: 'bicep'
}

// Modules
module networking 'modules/networking.bicep' = {
  name: 'networking'
  params: {
    location: location
    environment: environment
  }
}

module compute 'modules/compute.bicep' = {
  name: 'compute'
  params: {
    location: location
    subnetId: networking.outputs.subnetId
    tags: tags
  }
}

// Resources
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: '${appName}storage'
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  tags: tags
  properties: {
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
  }
}

// Outputs
output storageAccountName string = storageAccount.name
output storagePrimaryEndpoint string = storageAccount.properties.primaryEndpoints.blob
```

### Module Pattern

```bicep
// modules/app-service.bicep
@description('App name')
param appName string

@description('Location')
param location string

@description('App Service Plan SKU')
@allowed(['F1', 'B1', 'S1', 'P1v3'])
param sku string = 'S1'

resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: '${appName}-plan'
  location: location
  sku: {
    name: sku
  }
  properties: {
    reserved: true  // Linux
  }
}

resource webApp 'Microsoft.Web/sites@2023-01-01' = {
  name: appName
  location: location
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'
      alwaysOn: sku != 'F1'
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
    }
    httpsOnly: true
  }
}

output appUrl string = 'https://${webApp.properties.defaultHostName}'
output appId string = webApp.id
```

### Deployment Commands

```bash
# Validate template
az bicep build --file main.bicep

# What-if deployment (preview changes)
az deployment group what-if \
  --resource-group myapp-rg \
  --template-file main.bicep \
  --parameters environment=dev

# Deploy
az deployment group create \
  --resource-group myapp-rg \
  --template-file main.bicep \
  --parameters environment=dev dbPassword=$DB_PASSWORD

# Deploy with parameter file
az deployment group create \
  --resource-group myapp-rg \
  --template-file main.bicep \
  --parameters @parameters.dev.json
```

## Docker/Containerization

### Production Dockerfile

```dockerfile
# Multi-stage build for Python application
# Stage 1: Build dependencies
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim as runtime

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Install runtime dependencies only
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
      target: runtime
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/app
      - REDIS_URL=redis://redis:6379
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: app
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d app"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### Container Best Practices

```dockerfile
# DO: Use specific versions
FROM python:3.11.7-slim

# DON'T: Use latest
FROM python:latest

# DO: Combine RUN commands
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# DON'T: Separate RUN commands (creates extra layers)
RUN apt-get update
RUN apt-get install -y curl

# DO: Copy requirements first (layer caching)
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

# DON'T: Copy everything first (breaks cache)
COPY . .
RUN pip install -r requirements.txt
```

## CI/CD Pipeline Setup

### GitHub Actions

```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: '3.11'
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Run linting
        run: |
          ruff check .
          ruff format --check .
      
      - name: Run type checking
        run: pyright
      
      - name: Run tests
        run: pytest --cov=app --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml

  build:
    needs: test
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Login to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=sha,prefix=
            type=raw,value=latest,enable=${{ github.ref == 'refs/heads/main' }}
      
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  deploy:
    needs: build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to Azure
        uses: azure/webapps-deploy@v3
        with:
          app-name: ${{ secrets.AZURE_WEBAPP_NAME }}
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest
```

### Azure DevOps Pipeline

```yaml
# azure-pipelines.yml
trigger:
  branches:
    include:
      - main
      - develop

pool:
  vmImage: 'ubuntu-latest'

variables:
  pythonVersion: '3.11'
  imageName: 'myapp'

stages:
  - stage: Test
    jobs:
      - job: TestJob
        steps:
          - task: UsePythonVersion@0
            inputs:
              versionSpec: '$(pythonVersion)'
          
          - script: |
              pip install -r requirements.txt
              pip install -r requirements-dev.txt
            displayName: 'Install dependencies'
          
          - script: pytest --junitxml=junit/test-results.xml
            displayName: 'Run tests'
          
          - task: PublishTestResults@2
            inputs:
              testResultsFormat: 'JUnit'
              testResultsFiles: '**/test-results.xml'

  - stage: Build
    dependsOn: Test
    jobs:
      - job: BuildJob
        steps:
          - task: Docker@2
            inputs:
              containerRegistry: 'myacr'
              repository: '$(imageName)'
              command: 'buildAndPush'
              Dockerfile: '**/Dockerfile'
              tags: |
                $(Build.BuildId)
                latest

  - stage: Deploy
    dependsOn: Build
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
    jobs:
      - deployment: DeployJob
        environment: 'production'
        strategy:
          runOnce:
            deploy:
              steps:
                - task: AzureWebAppContainer@1
                  inputs:
                    azureSubscription: 'MySubscription'
                    appName: 'myapp-prod'
                    containers: 'myacr.azurecr.io/$(imageName):$(Build.BuildId)'
```

## Environment Management

### Environment Strategy

```
┌─────────────────────────────────────────────────────────────┐
│                    Environment Promotion                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│   ┌─────┐     ┌─────────┐     ┌─────────┐     ┌──────┐     │
│   │ Dev │ ──► │ Staging │ ──► │   QA    │ ──► │ Prod │     │
│   └─────┘     └─────────┘     └─────────┘     └──────┘     │
│                                                               │
│   Feature     Integration     Acceptance      Live           │
│   branches    testing         testing         traffic        │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Environment-Specific Configuration

```yaml
# config/base.yaml
app:
  name: myapp
  log_level: INFO
  
database:
  pool_size: 5
  timeout: 30

# config/dev.yaml
app:
  log_level: DEBUG
  
database:
  host: localhost
  pool_size: 2

# config/prod.yaml
app:
  log_level: WARNING
  
database:
  host: ${DATABASE_HOST}
  pool_size: 20
  ssl_mode: require
```

### Loading Configuration

```python
import os
from pathlib import Path
import yaml
from pydantic import BaseSettings

class Settings(BaseSettings):
    environment: str = "dev"
    database_url: str
    redis_url: str
    secret_key: str
    
    class Config:
        env_file = ".env"

def load_config(env: str = None) -> dict:
    """Load environment-specific configuration."""
    env = env or os.getenv("ENVIRONMENT", "dev")
    config_dir = Path("config")
    
    # Load base config
    with open(config_dir / "base.yaml") as f:
        config = yaml.safe_load(f)
    
    # Override with environment config
    env_file = config_dir / f"{env}.yaml"
    if env_file.exists():
        with open(env_file) as f:
            env_config = yaml.safe_load(f)
            deep_merge(config, env_config)
    
    # Substitute environment variables
    return substitute_env_vars(config)
```

## Secret Handling

### Secret Management Patterns

#### Environment Variables (Development)

```bash
# .env (gitignored)
DATABASE_URL=postgresql://user:pass@localhost/db
SECRET_KEY=dev-secret-key-not-for-prod
API_KEY=sk-test-key
```

#### Azure Key Vault

```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

def get_secret(secret_name: str) -> str:
    """Retrieve secret from Azure Key Vault."""
    vault_url = os.getenv("AZURE_KEYVAULT_URL")
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=vault_url, credential=credential)
    return client.get_secret(secret_name).value
```

#### AWS Secrets Manager

```python
import boto3
import json

def get_secret(secret_name: str) -> dict:
    """Retrieve secret from AWS Secrets Manager."""
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])
```

### Secret Rotation

```python
# Automated secret rotation pattern
class SecretManager:
    def __init__(self, cache_ttl: int = 300):
        self.cache = {}
        self.cache_ttl = cache_ttl
    
    def get_secret(self, name: str) -> str:
        """Get secret with caching and auto-refresh."""
        now = time.time()
        
        if name in self.cache:
            value, timestamp = self.cache[name]
            if now - timestamp < self.cache_ttl:
                return value
        
        # Refresh from source
        value = self._fetch_secret(name)
        self.cache[name] = (value, now)
        return value
    
    def _fetch_secret(self, name: str) -> str:
        """Fetch from secret store (implement per provider)."""
        raise NotImplementedError
```

### Security Checklist

- [ ] Secrets never in source code or git history
- [ ] Use secret management service in production
- [ ] Enable secret rotation where possible
- [ ] Audit secret access logs
- [ ] Use least-privilege access for secrets
- [ ] Encrypt secrets at rest and in transit

## Infrastructure Checklist

### Terraform
- [ ] Remote state backend configured
- [ ] State locking enabled
- [ ] Variables validated
- [ ] Sensitive outputs marked
- [ ] Modules versioned

### Docker
- [ ] Multi-stage build used
- [ ] Non-root user configured
- [ ] Health checks defined
- [ ] Image size optimized
- [ ] Security scanning enabled

### CI/CD
- [ ] Tests run before deploy
- [ ] Secrets managed securely
- [ ] Environment promotion gates
- [ ] Rollback strategy defined
- [ ] Monitoring alerts configured

### Environments
- [ ] Environment parity maintained
- [ ] Configuration externalized
- [ ] Secrets per environment
- [ ] Access controls defined
- [ ] Backup strategy in place
