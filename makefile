.DEFAULT_GOAL := help
.PHONY: install test fmt lint typecheck clean help

# Installing
install:
	pip install -e ".[dev]"

# Test
test:
	pytest -q

# Format con black
fmt:
	black .

# Lint
lint:
	ruff check .

# Type-check
typecheck:
	mypy adk_app

# Cache cleaning
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .ruff_cache *.egg-info build dist

# Show alla available commands
help:
	@echo "Available commands:"
	@echo "  make install     - Installe the package"
	@echo "  make test        - Execute tests"
	@echo "  make fmt         - Format the code"
	@echo "  make lint        - Lint"
	@echo "  make typecheck   - Type checking with mypy"
	@echo "  make clean       - Clean cache and build"
	@echo "  make help        - Show this message"