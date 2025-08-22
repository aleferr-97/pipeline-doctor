# Pipeline Doctor

MVP project: an AI-assisted tool (agent-ready) that inspects pipeline runs
(starting with Apache Spark) to detect bottlenecks and propose actionable fixes.

## Setup

Create a `.env` file in the project root to configure environment variables required for the application.

Example `.env` file:
```
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
```

## 💡 RAG (local knowledge)

This repo now supports a **minimal RAG** flow (no external services). Put your internal notes,
Spark/Delta best practices, and runbooks into:

```
docs/knowledge/
  ├─ spark_aqe.md
  ├─ delta_compaction.md
  └─ troubleshooting.txt
```

The agent will:
1) build a short query from current metrics/issues,
2) retrieve top‑K snippets from those files,
3) inject them into the LLM prompt as background knowledge.

> No extra dependencies. Retrieval is a tiny token‑overlap ranker; feel free to replace it later with BM25/FAISS.

Logs will show how many snippets were injected: `RAG: injected N snippet(s) into prompt`

## Roadmap

**Sprint 1 — Solidify MVP (done ✅)**  
- Structured agent output (`--json` flag, results saved in `eval/runs/`).  
- Threshold profiles (`profiles/<appName>.yaml`, auto-loaded on reruns).  
- Heuristics cleanup (all-English, consistent threshold naming, stable issue IDs).  

**Sprint 2 — Model benchmarking (in progress 🚀)**  
- Parametric pytest comparing multiple models (`llama3:8b`, `mistral:7b`, `qwen2.5`, `codellama`, …).  
- Evaluate: response time, JSON validity, completeness, stability.  
- Save results in `eval/model_runs/`.  
- Document results in README with a comparison table (pros/cons).  

**Sprint 3 — Auto-ingest Spark conf (planned)**  
- Extract Spark properties from event log (`SparkListenerEnvironmentUpdate`).  
- Optionally fetch Spark conf from Spark History Server (`/api/v1/applications/<id>/environment`).  

**Sprint 4 — Service mode (planned)**  
- FastAPI endpoints:  
  - `POST /analyze-eventlog`  
  - `POST /analyze-shs?appId=...`  
  - `POST /events` (real-time from SparkListener).  
- Integrations: filesystem/object storage watcher, SparkListener → HTTP, optional Kafka sink.  

**Sprint 5 — Reliability & UX (planned)**  
- LLM caching and rate-limiting.  
- Configurable timeout/retry via `.env`.  
- Prompt guardrails: always inject `spark_conf` + reference actions.  
- Integration tests (skip if no Ollama running).  

**Sprint 6 — Advanced heuristics (future)**  
- New rules: long GC time, executor kill rate, missing ZORDER, oversized broadcast joins, shuffle spill ratio.  
- Explainability: include key evidence per issue (numbers, metrics).  
- Config suggestions mapped to each heuristic. 