# Contributing to amplihack

**Welcome!** We appreciate your interest in improving amplihack.

## Table of Contents
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Where to Contribute](#where-to-contribute)
- [Testing](#testing)
- [Code Standards](#code-standards)
- [Need Help?](#need-help)

## Getting Started

### Prerequisites
- **Python**: 3.12 or higher
- **Node.js**: 18 or higher
- **Git**: For version control

### Installation

1. **Fork the repository** on GitHub
2. **Clone your fork**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/amplihack.git
   cd amplihack
   ```

3. **Install development dependencies**:
   ```bash
   uv pip install -e .[dev]
   ```
   Or using pip:
   ```bash
   pip install -e .[dev]
   ```

4. **Read our philosophy**:
   - Review [PHILOSOPHY.md](docs/PHILOSOPHY.md) to understand design principles

## Development Workflow

### 1. Create a Branch
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

### 2. Make Changes
- Follow our [Code Standards](#code-standards)
- Keep changes focused and atomic
- Write clear commit messages

### 3. Test Your Changes
```bash
pytest tests/
```

### 4. Commit
```bash
git add .
git commit -m "feat: add new feature description"
```

**Commit message format**:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `refactor:` Code refactoring
- `test:` Test additions/changes

### 5. Push and Create PR
```bash
git push origin feature/your-feature-name
```

Then open a Pull Request on GitHub with:
- Clear title and description
- Reference to related issues (e.g., "Fixes #123")
- Screenshots/examples if applicable

## Where to Contribute

### Add Agents
- Location: `~/.amplihack/.claude/agents/`
- Create new agent definitions following existing patterns

### Add Patterns
- Location: `~/.amplihack/.claude/context/PATTERNS.md`
- Document reusable code patterns and best practices

### Fix Bugs
- Check [issues labeled "good-first-issue"](../../labels/good-first-issue)
- Check [issues labeled "bug"](../../labels/bug)

### Improve Documentation
- Any `.md` file in the repository
- Focus on clarity for beginners
- Update outdated information

### Add Features
- Discuss major changes in [Discussions](../../discussions) first
- Follow the existing architecture patterns

## Testing

### Run All Tests
```bash
pytest tests/
```

### Run Unit Tests Only
```bash
pytest tests/unit/
```

### Run Integration Tests
```bash
pytest tests/integration/
```

### Run with Coverage
```bash
pytest tests/ --cov=amplihack --cov-report=html
```

## Code Standards

### Python
- Follow [PEP 8](https://pep8.org/) style guide
- Use type hints where applicable
- Maximum line length: 100 characters

### Functions
- Keep functions small (< 50 lines when possible)
- Single responsibility principle
- Clear function names (verb + noun)

### Documentation
- Add docstrings for public functions
- Use Google-style docstrings:
  ```python
  def function_name(param: str) -> bool:
      """Short description.
      
      Args:
          param: Description of parameter
          
      Returns:
          Description of return value
      """
  ```

### Design Principles
- See [PHILOSOPHY.md](docs/PHILOSOPHY.md) for detailed design principles
- Prefer simplicity over complexity
- Write code for humans first

## Need Help?

### Ask Questions
- Use [GitHub Discussions](../../discussions) for questions
- Tag issues with `question` label
- Be specific and provide context

### Documentation
- [Technical Reference](docs/DEVELOPING_AMPLIHACK.md) - API and module documentation
- [PHILOSOPHY.md](docs/PHILOSOPHY.md) - Design principles and philosophy
- [README.md](README.md) - Project overview

### Community
- Be respectful and constructive
- Help others when you can
- Share your experiences

## Recognition

Contributors will be:
- Listed in the project README
- Mentioned in release notes for significant contributions
- Invited to join the organization for sustained contributions

## License

By contributing to amplihack, you agree that your contributions will be licensed under the same license as the project.

---

**Thank you for contributing!** 🎉

*For detailed API documentation, see [DEVELOPING_AMPLIHACK.md](docs/DEVELOPING_AMPLIHACK.md).*