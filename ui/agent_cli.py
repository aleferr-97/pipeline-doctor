import argparse
from adk_app.agent import analyze_eventlog_with_agent
from adk_app.llm.ollama import OllamaLLM
import os
import sys
import requests
import json
from datetime import datetime
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Minimal .env loader (no external deps). It does not override already-set env vars.
def _load_env_file_if_present(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    logging.info(f"Loading environment variables from {env_path}")
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        # do not override if already provided by the shell/CI
        if key and key not in os.environ:
            os.environ[key] = value

def _assert_ollama_up(host: str):
    logging.info(f"Checking Ollama at {host}")
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
    p.add_argument("--json", action="store_true", help="Print structured JSON output instead of human-readable text")
    args = p.parse_args()

    # Load .env if present so running the CLI directly behaves like `make` targets
    _load_env_file_if_present()

    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    logging.info(f"Analyzing eventlog {args.eventlog} with model {model} at {host}")
    _assert_ollama_up(host)

    res = analyze_eventlog_with_agent(
        args.eventlog,
        llm=OllamaLLM(model=model, host=host),
        skew_threshold=args.skew_th,
        small_file_mb=args.small_file_mb,
        shuffle_heavy_mb=args.shuffle_heavy_mb,
        files_per_partition_threshold=args.files_per_part_th,
    )

    thresholds = {
        "skew_threshold": args.skew_th,
        "small_file_mb": args.small_file_mb,
        "shuffle_heavy_mb": args.shuffle_heavy_mb,
        "files_per_partition_threshold": args.files_per_part_th,
    }
    payload = {
        "metrics": res.get("metrics", {}),
        "issues": res.get("recommendations", []),
        "report": res.get("report", ""),
        "thresholds": thresholds,
        "llm": {"provider": "ollama", "model": model, "host": host},
        "source": {"eventlog": args.eventlog},
    }

    runs_dir = Path(__file__).resolve().parents[1] / "eval" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = runs_dir / f"{ts}.json"
    with out_path.open("w", encoding="utf-8") as f:
        clean_payload = payload.copy()
        clean_payload["report"] = [line.lstrip("\t") for line in payload["report"].splitlines()]
        json.dump(clean_payload, f, ensure_ascii=False, indent=2)

    logging.info(f"Run results saved to {out_path}")

    print(f"Saved run to {out_path}")

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    print("\n=== METRICS ===")
    for k, v in payload["metrics"].items():
        print(f"{k}: {v}")
    print("\n=== RULE-BASED ISSUES ===")
    for r in payload["issues"]:
        print(f"- [{r['impact']}] {r['issue']} — {r['why']}")
    print("\n=== AGENT REPORT ===")
    print(payload["report"])

if __name__ == "__main__":
    main()