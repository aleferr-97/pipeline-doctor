# Makefile per pipeline-doctor

.DEFAULT_GOAL := help
.PHONY: install test fmt lint typecheck clean help

# Installazione in editable con deps dev
install:
	pip install -e ".[dev]"

# Esegui i test con pytest
test:
	pytest -q

# Format con black
fmt:
	black .

# Lint con ruff
lint:
	ruff check .

# Type-check con mypy
typecheck:
	mypy adk_app

# Pulizia cache varie
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .ruff_cache *.egg-info build dist

# Mostra la lista dei comandi disponibili
help:
	@echo "Available commands:"
	@echo "  make install     - installa pacchetto in editable mode con deps dev"
	@echo "  make test        - esegue i test con pytest"
	@echo "  make fmt         - formatta il codice con black"
	@echo "  make lint        - lint con ruff"
	@echo "  make typecheck   - controlla i tipi con mypy"
	@echo "  make clean       - pulisce cache e build"
	@echo "  make help        - mostra questo messaggio"