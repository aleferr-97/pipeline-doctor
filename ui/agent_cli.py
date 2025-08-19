import argparse
from adk_app.agent import analyze_eventlog_with_agent
from adk_app.llm.ollama import OllamaLLM
import os
import sys
import requests

def _assert_ollama_up(host: str):
    try:
        r = requests.get(f"{host.rstrip('/')}/api/tags", timeout=3)
        r.raise_for_status()
    except Exception as e:
        sys.exit(f"Ollama not reachable at {host}. Start it with `make up && make wait-ollama` and ensure a model is pulled.")


def main():
    p = argparse.ArgumentParser(description="Pipeline Doctor — Agent CLI")
    p.add_argument("--eventlog", required=True)
    p.add_argument("--skew-th", type=float, default=3.0)
    p.add_argument("--small-file-mb", type=float, default=32.0)
    p.add_argument("--shuffle-heavy-mb", type=float, default=2048.0)
    p.add_argument("--files-per-part-th", type=float, default=2.0)
    args = p.parse_args()

    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "llama3:8b")
    _assert_ollama_up(host)

    res = analyze_eventlog_with_agent(
        args.eventlog,
        llm=OllamaLLM(model=model, host=host),
        skew_threshold=args.skew_th,
        small_file_mb=args.small_file_mb,
        shuffle_heavy_mb=args.shuffle_heavy_mb,
        files_per_partition_threshold=args.files_per_part_th,
    )

    print("\n=== METRICS ===")
    for k, v in res["metrics"].items():
        print(f"{k}: {v}")
    print("\n=== RULE-BASED ISSUES ===")
    for r in res["recommendations"]:
        print(f"- [{r['impact']}] {r['issue']} — {r['why']}")
    print("\n=== AGENT REPORT ===")
    print(res["report"])

if __name__ == "__main__":
    main()