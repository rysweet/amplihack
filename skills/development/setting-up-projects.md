# Setting Up Projects

Project setup automation for consistent, well-structured development environments.

## When to Use

- Starting a new project from scratch
- Standardizing existing project structure
- Adding CI/CD to a project
- Setting up development tooling
- Onboarding new team members

## Python Project Structure

### Modern Python Layout (src layout)

```
project-name/
├── pyproject.toml          # Project metadata and dependencies
├── README.md               # Project documentation
├── LICENSE                 # License file
├── .gitignore              # Git ignore patterns
├── .pre-commit-config.yaml # Pre-commit hooks
├── src/
│   └── package_name/       # Your package (importable)
│       ├── __init__.py
│       ├── main.py
│       └── utils.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py         # Pytest fixtures
│   └── test_main.py
└── .github/
    └── workflows/
        └── ci.yml          # GitHub Actions CI
```

### pyproject.toml Template

```toml
[project]
name = "package-name"
version = "0.1.0"
description = "A brief description of the project"
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.11"
authors = [
    {name = "Your Name", email = "you@example.com"}
]
dependencies = [
    # Core dependencies here
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=4.0",
    "ruff>=0.4",
    "pyright>=1.1",
    "pre-commit>=3.0",
]

[project.scripts]
package-name = "package_name.main:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/package_name"]

[tool.ruff]
line-length = 100
target-version = "py311"
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM"]

[tool.pyright]
pythonVersion = "3.11"
typeCheckingMode = "standard"
venvPath = "."
venv = ".venv"

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --cov=src --cov-report=term-missing"
```

### Python Setup Commands

```bash
# Create project structure
mkdir -p project-name/{src/package_name,tests,.github/workflows}
cd project-name

# Initialize git
git init

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Initialize pre-commit
pre-commit install
```

## TypeScript/Node Project Setup

### Project Structure

```
project-name/
├── package.json            # Project metadata and dependencies
├── tsconfig.json           # TypeScript configuration
├── README.md
├── LICENSE
├── .gitignore
├── .eslintrc.json          # ESLint configuration
├── .prettierrc             # Prettier configuration
├── .pre-commit-config.yaml
├── src/
│   ├── index.ts            # Entry point
│   └── utils/
│       └── helpers.ts
├── tests/
│   └── index.test.ts
└── .github/
    └── workflows/
        └── ci.yml
```

### package.json Template

```json
{
  "name": "package-name",
  "version": "0.1.0",
  "description": "A brief description",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "type": "module",
  "scripts": {
    "build": "tsc",
    "dev": "tsx watch src/index.ts",
    "start": "node dist/index.js",
    "test": "vitest",
    "test:coverage": "vitest --coverage",
    "lint": "eslint src tests",
    "lint:fix": "eslint src tests --fix",
    "format": "prettier --write .",
    "typecheck": "tsc --noEmit",
    "check": "npm run lint && npm run typecheck && npm test"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "typescript": "^5.4.0",
    "tsx": "^4.0.0",
    "vitest": "^1.0.0",
    "@vitest/coverage-v8": "^1.0.0",
    "eslint": "^8.0.0",
    "@typescript-eslint/eslint-plugin": "^7.0.0",
    "@typescript-eslint/parser": "^7.0.0",
    "prettier": "^3.0.0"
  },
  "engines": {
    "node": ">=20.0.0"
  }
}
```

### tsconfig.json Template

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "lib": ["ES2022"],
    "outDir": "dist",
    "rootDir": "src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist", "tests"]
}
```

### Node Setup Commands

```bash
# Create project structure
mkdir -p project-name/{src,tests,.github/workflows}
cd project-name

# Initialize git and npm
git init
npm init -y

# Install dependencies
npm install -D typescript tsx vitest @vitest/coverage-v8
npm install -D eslint @typescript-eslint/eslint-plugin @typescript-eslint/parser
npm install -D prettier @types/node

# Initialize TypeScript
npx tsc --init
```

## Git Initialization

### Comprehensive .gitignore

```gitignore
# Dependencies
node_modules/
.venv/
venv/
__pycache__/
*.py[cod]
*$py.class

# Build outputs
dist/
build/
*.egg-info/
.eggs/

# IDE
.idea/
.vscode/
*.swp
*.swo
*~

# Environment
.env
.env.local
.env.*.local
*.local

# Testing
.coverage
htmlcov/
.pytest_cache/
.tox/
coverage/

# Logs
*.log
npm-debug.log*

# OS
.DS_Store
Thumbs.db

# Project specific
# Add your patterns here
```

### Git Configuration

```bash
# Initialize repository
git init

# Configure user (if not global)
git config user.name "Your Name"
git config user.email "you@example.com"

# Create initial commit
git add .
git commit -m "Initial project setup"

# Set default branch
git branch -M main

# Add remote (if applicable)
git remote add origin git@github.com:org/repo.git
```

## Pre-commit Hooks Setup

### .pre-commit-config.yaml (Python)

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-added-large-files
        args: ['--maxkb=1000']
      - id: check-merge-conflict
      - id: detect-private-key

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/RobertCraiworethite/pyright-python
    rev: v1.1.350
    hooks:
      - id: pyright
```

### .pre-commit-config.yaml (TypeScript)

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-added-large-files
      - id: check-merge-conflict

  - repo: local
    hooks:
      - id: eslint
        name: eslint
        entry: npm run lint
        language: system
        types: [typescript]
        pass_filenames: false

      - id: typecheck
        name: typecheck
        entry: npm run typecheck
        language: system
        types: [typescript]
        pass_filenames: false

      - id: prettier
        name: prettier
        entry: npx prettier --check .
        language: system
        pass_filenames: false
```

### Pre-commit Commands

```bash
# Install pre-commit
pip install pre-commit  # or: brew install pre-commit

# Install hooks
pre-commit install

# Run on all files (first time)
pre-commit run --all-files

# Update hooks to latest versions
pre-commit autoupdate
```

## CI/CD Templates

### GitHub Actions - Python

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Lint with ruff
        run: |
          ruff check .
          ruff format --check .

      - name: Type check with pyright
        run: pyright

      - name: Test with pytest
        run: pytest --cov --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: coverage.xml
```

### GitHub Actions - TypeScript

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node-version: ["20", "22"]

    steps:
      - uses: actions/checkout@v4

      - name: Use Node.js ${{ matrix.node-version }}
        uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Lint
        run: npm run lint

      - name: Type check
        run: npm run typecheck

      - name: Test
        run: npm run test:coverage

      - name: Build
        run: npm run build
```

## Project Setup Checklist

### Initial Setup

```
[ ] Create project directory structure
[ ] Initialize git repository
[ ] Create .gitignore with comprehensive patterns
[ ] Set up package manager (pyproject.toml / package.json)
[ ] Configure development dependencies
[ ] Set up linting (ruff / eslint)
[ ] Set up formatting (ruff / prettier)
[ ] Set up type checking (pyright / typescript)
[ ] Configure testing framework (pytest / vitest)
```

### Quality Assurance

```
[ ] Install pre-commit hooks
[ ] Configure CI/CD pipeline
[ ] Add test coverage reporting
[ ] Set up code quality checks
[ ] Add security scanning (optional)
```

### Documentation

```
[ ] Create README.md with setup instructions
[ ] Add LICENSE file
[ ] Document development workflow
[ ] Add CONTRIBUTING.md (for open source)
```

### First Commit

```bash
# Verify everything works
pre-commit run --all-files
pytest  # or: npm test

# Create initial commit
git add .
git commit -m "Initial project setup

- Project structure with src layout
- Development tooling (lint, format, typecheck)
- Testing framework with coverage
- Pre-commit hooks
- CI/CD pipeline"
```

## Quick Setup Scripts

### Python Quick Start

```bash
#!/bin/bash
PROJECT_NAME=$1
PACKAGE_NAME=${PROJECT_NAME//-/_}

mkdir -p "$PROJECT_NAME"/{src/"$PACKAGE_NAME",tests,.github/workflows}
cd "$PROJECT_NAME"

# Create __init__.py files
touch src/"$PACKAGE_NAME"/__init__.py
touch tests/__init__.py

# Initialize git
git init
echo "# $PROJECT_NAME" > README.md

echo "Project $PROJECT_NAME created. Next steps:
1. Create pyproject.toml
2. Create .gitignore
3. Set up virtual environment
4. Install pre-commit hooks"
```

### Node Quick Start

```bash
#!/bin/bash
PROJECT_NAME=$1

mkdir -p "$PROJECT_NAME"/{src,tests,.github/workflows}
cd "$PROJECT_NAME"

npm init -y
git init

echo "# $PROJECT_NAME" > README.md

echo "Project $PROJECT_NAME created. Next steps:
1. Install TypeScript and dev dependencies
2. Create tsconfig.json
3. Create .gitignore
4. Install pre-commit hooks"
```
