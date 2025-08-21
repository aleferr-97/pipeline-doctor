# Load .env file if present
ifneq (,$(wildcard .env))
    include .env
    export $(shell sed 's/=.*//' .env)
endif

.DEFAULT_GOAL := help
BENCH_MODELS ?= mistral:7b qwen2.5:7b-instruct llama3:8b
EVENTLOG ?= data/samples/spark_eventlog.jsonl

.PHONY: install test fmt lint typecheck clean help
.PHONY: up down pull-model wait-ollama agent-sample
.PHONY: bench

# --- Dockerized Ollama (for local LLM) ---
up:
	# Start Ollama via Docker in the background
	docker compose up -d

down:
	# Stop and remove the Docker stack
	docker compose down

pull-model:
	# Pull an Ollama model
	curl -fsS -X POST $(OLLAMA_HOST)/api/pull -d '{"name":"$(OLLAMA_MODEL)"}' -H "Content-Type: application/json"

wait-ollama:
	@echo "Waiting for Ollama at $(OLLAMA_HOST)..."
	@for i in $$(seq 1 30); do \
	  curl -fsS $(OLLAMA_HOST)/api/tags >/dev/null 2>&1 && { echo "Ollama is up!"; exit 0; }; \
	  sleep 1; \
	done; \
	echo "Ollama not responding on $(OLLAMA_HOST)"; exit 1

# --- Benchmarks ---

bench: up wait-ollama
	@mkdir -p eval/runs
	@echo "Benchmarking models: $(BENCH_MODELS)"
	@for m in $(BENCH_MODELS); do \
	  echo "=== $$m ==="; \
	  OLLAMA_MODEL=$$m $(MAKE) --no-print-directory pull-model; \
	  OLLAMA_MODEL=$$m python ui/agent_cli.py --eventlog $(EVENTLOG) --json >/dev/null || exit 1; \
	done
	@echo "Done. Check eval/runs/*-<model>.json (each file has meta.duration_s)."

# --- Project tasks ---
install:
	pip install -e ".[dev]"

test:
	pytest -q

fmt:
	black .

lint:
	ruff check .

typecheck:
	mypy adk_app

agent-sample: up wait-ollama pull-model
	@echo "Running agent with OLLAMA_HOST=$(OLLAMA_HOST) OLLAMA_MODEL=$(OLLAMA_MODEL)"
	python ui/agent_cli.py --eventlog data/samples/spark_eventlog.jsonl

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .ruff_cache *.egg-info build dist

help:
	@echo "Available commands:"
	@echo "  make up            - Start Ollama (Docker)"
	@echo "  make wait-ollama   - Wait until Ollama API is ready"
	@echo "  make pull-model    - Pull Ollama model (OLLAMA_MODEL=$(OLLAMA_MODEL))"
	@echo "  make agent-sample  - Start stack, pull model, and run CLI on the sample eventlog"
	@echo "  make down          - Stop Docker stack"
	@echo "  make install       - Install the package in editable mode"
	@echo "  make test          - Run tests"
	@echo "  make fmt           - Format code with Black"
	@echo "  make lint          - Lint with Ruff"
	@echo "  make typecheck     - Type-check with mypy"
	@echo "  make clean         - Clean caches and build artifacts"
	@echo "  make help          - Show this help"