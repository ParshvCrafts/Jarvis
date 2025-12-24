# =============================================================================
# JARVIS Makefile
# Common development commands
# =============================================================================

.PHONY: help install install-dev test lint format check run run-text clean docs

# Default target
help:
	@echo "JARVIS Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install      - Install production dependencies"
	@echo "  make install-dev  - Install development dependencies"
	@echo ""
	@echo "Running:"
	@echo "  make run          - Run JARVIS (voice mode)"
	@echo "  make run-text     - Run JARVIS (text mode)"
	@echo "  make run-check    - Check configuration"
	@echo "  make run-mobile   - Start mobile PWA dev server"
	@echo ""
	@echo "Testing:"
	@echo "  make test         - Run all tests"
	@echo "  make test-cov     - Run tests with coverage"
	@echo "  make verify       - Verify all imports"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint         - Run linters"
	@echo "  make format       - Format code"
	@echo "  make check        - Run all checks"
	@echo ""
	@echo "Other:"
	@echo "  make clean        - Clean cache files"
	@echo "  make docs         - Build documentation"

# =============================================================================
# Setup
# =============================================================================

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt
	cd mobile && npm install

# =============================================================================
# Running
# =============================================================================

run:
	python run.py

run-text:
	python run.py --text

run-check:
	python run.py --check-config

run-mobile:
	cd mobile && npm run dev

# =============================================================================
# Testing
# =============================================================================

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term

verify:
	python scripts/verify_imports.py

# =============================================================================
# Code Quality
# =============================================================================

lint:
	flake8 src/ --max-line-length=100 --ignore=E501,W503
	mypy src/ --ignore-missing-imports

format:
	black src/ --line-length=100
	isort src/ --profile=black

check: lint verify
	@echo "All checks passed!"

# =============================================================================
# Other
# =============================================================================

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf htmlcov/ .coverage 2>/dev/null || true
	@echo "Cleaned cache files"

docs:
	mkdocs build

docs-serve:
	mkdocs serve
