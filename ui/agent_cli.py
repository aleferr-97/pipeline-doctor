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
from time import perf_counter

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO), format="%(asctime)s [%(levelname)s] %(message)s")

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

    # Read optional decoding parameters from env
    def _env_float(name: str):
        val = os.getenv(name)
        try:
            return float(val) if val not in (None, "",) else None
        except Exception:
            logging.warning(f"Ignoring non-float value for {name}={val!r}")
            return None

    def _env_int(name: str):
        val = os.getenv(name)
        try:
            return int(val) if val not in (None, "",) else None
        except Exception:
            logging.warning(f"Ignoring non-int value for {name}={val!r}")
            return None

    temperature = _env_float("OLLAMA_TEMPERATURE")
    top_p = _env_float("OLLAMA_TOP_P")
    repeat_penalty = _env_float("OLLAMA_REPEAT_PENALTY")
    num_predict = _env_int("OLLAMA_NUM_PREDICT")
    num_ctx = _env_int("OLLAMA_NUM_CTX")
    response_format = os.getenv("OLLAMA_FORMAT")
    logging.info(
        "LLM options: temperature=%s top_p=%s repeat_penalty=%s num_predict=%s num_ctx=%s format=%s",
        temperature, top_p, repeat_penalty, num_predict, num_ctx, response_format
    )

    t0 = perf_counter()
    started_iso = datetime.now().isoformat(timespec="seconds")

    res = analyze_eventlog_with_agent(
        args.eventlog,
        llm=OllamaLLM(
            model=model,
            host=host,
            temperature=temperature,
            top_p=top_p,
            repeat_penalty=repeat_penalty,
            num_predict=num_predict,
            num_ctx=num_ctx,
            response_format=response_format,
        ),
        skew_threshold=args.skew_th,
        small_file_mb=args.small_file_mb,
        shuffle_heavy_mb=args.shuffle_heavy_mb,
        files_per_partition_threshold=args.files_per_part_th,
    )
    duration_s = round(perf_counter() - t0, 3)

    thresholds = {
        "skew_threshold": args.skew_th,
        "small_file_mb": args.small_file_mb,
        "shuffle_heavy_mb": args.shuffle_heavy_mb,
        "files_per_partition_threshold": args.files_per_part_th,
    }
    # Only include options that were actually set
    _llm_options = {}
    if temperature is not None: _llm_options["temperature"] = temperature
    if top_p is not None: _llm_options["top_p"] = top_p
    if repeat_penalty is not None: _llm_options["repeat_penalty"] = repeat_penalty
    if num_predict is not None: _llm_options["num_predict"] = num_predict
    if num_ctx is not None: _llm_options["num_ctx"] = num_ctx
    if response_format: _llm_options["format"] = response_format

    payload = {
        "metrics": res.get("metrics", {}),
        "issues": res.get("recommendations", []),
        "report": res.get("report", ""),
        "draft_raw": res.get("draft_raw", ""),
        "refined_raw": res.get("refined_raw", ""),
        "thresholds": thresholds,
        "llm": {"provider": "ollama", "model": model, "host": host, "options": _llm_options},
        "source": {"eventlog": args.eventlog},
        "meta": {"started_at": started_iso, "duration_s": duration_s},
    }

    runs_dir = Path(__file__).resolve().parents[1] / "eval" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    safe_model = model.replace(":", "_").replace("/", "_")
    out_path = runs_dir / f"{started_iso}-{safe_model}.json"
    with out_path.open("w", encoding="utf-8") as f:
        clean_payload = payload.copy()
        clean_payload["report"] = [line.lstrip("\t") for line in payload["report"].splitlines()]
        clean_payload["draft_raw"] = payload.get("draft_raw", "")
        clean_payload["refined_raw"] = payload.get("refined_raw", "")
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
    _rep = payload.get("report", "")
    if isinstance(_rep, list):
        print("\n".join(_rep))
    else:
        print(_rep)

if __name__ == "__main__":
    main()