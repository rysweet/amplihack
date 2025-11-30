# REST API Client Test Makefile

.PHONY: help install test test-unit test-integration test-e2e test-all coverage clean lint type-check

help:
	@echo "Available commands:"
	@echo "  make install         - Install test dependencies"
	@echo "  make test           - Run all tests"
	@echo "  make test-unit      - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make test-e2e       - Run end-to-end tests only"
	@echo "  make test-all       - Run all tests in parallel"
	@echo "  make coverage       - Generate coverage report"
	@echo "  make lint           - Run linters"
	@echo "  make type-check     - Run type checking"
	@echo "  make clean          - Clean test artifacts"

install:
	pip install -r requirements-test.txt
	pip install -e .

test:
	pytest tests/

test-unit:
	pytest tests/ -m unit

test-integration:
	pytest tests/ -m integration

test-e2e:
	pytest tests/ -m e2e

test-all:
	pytest tests/ -n auto  # Run in parallel

coverage:
	pytest tests/ --cov=rest_api_client --cov-report=html --cov-report=term
	@echo "Coverage report generated in htmlcov/index.html"

lint:
	ruff check rest_api_client/ tests/
	black --check rest_api_client/ tests/
	isort --check-only rest_api_client/ tests/
	pydocstyle rest_api_client/

type-check:
	mypy rest_api_client/ --strict

clean:
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
