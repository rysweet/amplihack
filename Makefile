# Developer Makefile
# Run 'make setup' after cloning the repository

.PHONY: setup install test lint format clean help

# Default target
help:
	@echo "Available commands:"
	@echo "  make setup    - Set up development environment (run this first!)"
	@echo "  make install  - Install project dependencies"
	@echo "  make lint     - Run pre-commit checks on all files"
	@echo "  make format   - Auto-format all files"
	@echo "  make test     - Run tests"
	@echo "  make clean    - Remove generated files and caches"

# First-time setup for developers
setup:
	@echo "Setting up development environment..."
	@python3 setup_dev.py

# Install dependencies
install:
	pip install -e .
	pip install pre-commit

# Run all pre-commit checks
lint:
	pre-commit run --all-files

# Auto-format code
format:
	pre-commit run --all-files || true
	@echo "Formatting complete. Review changes with 'git diff'"

# Run tests
test:
	@if [ -f "pytest.ini" ] || [ -f "setup.cfg" ] || [ -f "pyproject.toml" ]; then \
		pytest; \
	else \
		echo "No pytest configuration found. Skipping tests."; \
	fi

# Clean up generated files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
