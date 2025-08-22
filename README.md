# Pipeline Doctor

> ⚠️ **Work in Progress** — This project is still under active development.

Pipeline Doctor is an AI-assisted tool designed to analyze Apache Spark pipeline runs, identify performance bottlenecks, and suggest actionable improvements. It helps optimize Spark jobs by providing clear diagnostics and recommendations.

## Requirements

- Python 3.10 or higher  
- Docker  
- Ollama (local LLM server)

## Quick Start

Run the following commands to get started quickly:

```bash
make up
make wait-ollama
make pull-model
make agent-sample
```

## Local RAG (Retrieval-Augmented Generation)

Pipeline Doctor supports a minimal local RAG workflow to enhance LLM prompts with internal knowledge. Place your documentation and best practices in the `docs/knowledge/` directory:

```
docs/knowledge/
  ├─ spark_aqe.md
  ├─ delta_compaction.md
```

Example snippet contents:

- **spark_aqe.md**  
  - Adaptive Query Execution improves performance by dynamically optimizing query plans.  
  - Enable AQE via `spark.sql.adaptive.enabled=true`.

- **delta_compaction.md**  
  - Delta Lake compaction reduces small files to improve read efficiency.  
  - Use `OPTIMIZE` commands and configure compaction thresholds.

The agent extracts relevant snippets from these files based on the current Spark metrics and injects them into the prompt to provide context-aware recommendations.

## Benchmarking

Use the following commands to benchmark models and evaluate performance:

- `make bench` — runs benchmarks on selected models and saves results.  
- `make bench-grid` — runs a grid of model and parameter combinations for detailed comparison.

Benchmark results, including latency and output quality metrics, are stored in the `eval/model_runs/` directory. You can inspect `meta.duration_s` in the JSON output to analyze inference times.

## LLM Tuning

You can customize the LLM behavior using environment variables:

| Variable              | Description                       | Default |
|-----------------------|---------------------------------|---------|
| `OLLAMA_TEMPERATURE`  | Sampling temperature             | 0.2     |
| `OLLAMA_TOP_P`        | Nucleus sampling probability     | 0.9     |
| `OLLAMA_REPEAT_PENALTY` | Repetition penalty             | 1.1     |
| `OLLAMA_NUM_PREDICT`  | Max tokens to predict            | 768     |
| `OLLAMA_NUM_CTX`      | Context window size              | 4096    |
| `OLLAMA_FORMAT`       | Output format (e.g., `json`)     | `json`  |

Set these variables in your `.env` file or shell environment to tune model responses.

## Sample Inputs

Sample Spark event log inputs are available under `data/samples/`:

- `skew.jsonl` — workloads with data skew issues  
- `small_files.jsonl` — jobs suffering from small file problems  
- `shuffle_heavy.jsonl` — shuffle-intensive workloads

Use these for testing and development.

## Sample Output

Example JSON output from the agent:

```json
{
  "metrics": {
    "duration_s": 120,
    "shuffle_read_gb": 15.3,
    "gc_time_s": 5.2
  },
  "issues": [
    {
      "id": "small_files_01",
      "description": "Detected excessive small files causing overhead.",
      "severity": "medium"
    }
  ],
  "draft_raw": "The job has many small files affecting performance. Consider compaction.",
  "refined_raw": "Small files detected; recommend running Delta Lake OPTIMIZE to improve read efficiency.",
  "rag": {
    "snippets": [
      "Delta Lake compaction reduces small files to improve read efficiency.",
      "Use OPTIMIZE commands and configure compaction thresholds."
    ]
  }
}
```

## Logging

To enable detailed logging, run the agent CLI with:

```bash
LOG_LEVEL=DEBUG python ui/agent_cli.py ...
```

Optionally, suppress Python warnings by adding:

```bash
PYTHONWARNINGS=ignore
```