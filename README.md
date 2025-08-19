# Pipeline Doctor

MVP project: an AI-assisted tool (agent-ready) that inspects pipeline runs
(starting with Apache Spark) to detect bottlenecks and propose actionable fixes.

## Setup

Create a `.env` file in the project root to configure environment variables required for the application.

Example `.env` file:
```
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3:8b
```

## Models

- `llama3.2:3b`: A smaller model suitable for local development and testing due to its lower resource requirements.
- `llama3:8b`: A larger, more powerful model recommended for cloud deployments or environments with sufficient computational resources.

Choose the model based on your deployment environment and performance needs.

## Roadmap
- [ ] MVP parser Spark JSON log
- [ ] Heuristics (skew, shuffle, small files)
- [ ] CLI demo
- [ ] Evaluation suite
- [ ] Integration with ADK (Google Agent Development Kit)