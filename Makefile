# MicrosoftHackathon2025 AgenticCoding Tools Makefile

.PHONY: help install test extract-requirements clean

# Default target
help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  make %-20s %s\n", $$1, $$2}'

install: ## Install dependencies
	@echo "Installing dependencies..."
	@if command -v pip >/dev/null; then \
		pip install -r requirements.txt 2>/dev/null || echo "No requirements.txt found"; \
	fi
	@echo "✅ Installation complete"

test: ## Run tests
	@echo "Running tests..."
	@python -m pytest tools/tests/ -v || echo "Tests require pytest: pip install pytest"

extract-requirements: ## Extract requirements from a project. Usage: make extract-requirements PATH=/path/to/project
	@if [ -z "$(PATH)" ]; then \
		echo "Error: Please provide a PATH. Usage: make extract-requirements PATH=/path/to/project"; \
		exit 1; \
	fi
	@echo "Extracting requirements from $(PATH)..."
	@python -m tools.requirement_extractor "$(PATH)" $(OPTIONS)

extract-requirements-resume: ## Resume interrupted extraction. Usage: make extract-requirements-resume PATH=/path/to/project
	@if [ -z "$(PATH)" ]; then \
		echo "Error: Please provide a PATH. Usage: make extract-requirements-resume PATH=/path/to/project"; \
		exit 1; \
	fi
	@echo "Resuming extraction for $(PATH)..."
	@python -m tools.requirement_extractor "$(PATH)" --resume $(OPTIONS)

extract-requirements-compare: ## Extract and compare with existing. Usage: make extract-requirements-compare PATH=/path/to/project COMPARE=existing.md
	@if [ -z "$(PATH)" ] || [ -z "$(COMPARE)" ]; then \
		echo "Error: Please provide PATH and COMPARE. Usage: make extract-requirements-compare PATH=/path/to/project COMPARE=existing.md"; \
		exit 1; \
	fi
	@echo "Extracting and comparing requirements..."
	@python -m tools.requirement_extractor "$(PATH)" --compare "$(COMPARE)" $(OPTIONS)

test-extraction: ## Test extraction on sample project
	@echo "Testing extraction on sample Python project..."
	@mkdir -p test_sample_project
	@echo "def authenticate(username, password):\n    '''Authenticate user'''\n    pass" > test_sample_project/auth.py
	@echo "def get_users():\n    '''Get all users'''\n    pass" > test_sample_project/users.py
	@python -m tools.requirement_extractor test_sample_project --output test_requirements.md
	@echo "✅ Test extraction complete. Check test_requirements.md"

clean: ## Clean temporary files and cache
	@echo "Cleaning temporary files..."
	@rm -rf __pycache__ .pytest_cache
	@rm -rf tools/__pycache__ tools/*/__pycache__
	@rm -rf .test_state.json test_state.json
	@rm -rf test_sample_project test_requirements.md
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleanup complete"