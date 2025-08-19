import argparse
from adk_app.agent import analyze_eventlog_with_agent
from adk_app.llm.base import NoopLLM

def main():
    p = argparse.ArgumentParser(description="Pipeline Doctor — Agent CLI")
    p.add_argument("--eventlog", required=True)
    p.add_argument("--skew-th", type=float, default=3.0)
    p.add_argument("--small-file-mb", type=float, default=32.0)
    p.add_argument("--shuffle-heavy-mb", type=float, default=2048.0)
    p.add_argument("--files-per-part-th", type=float, default=2.0)
    args = p.parse_args()

    res = analyze_eventlog_with_agent(
        args.eventlog,
        llm=NoopLLM(),  # qui poi: OllamaLLM() o VertexLLM()
        skew_threshold=args.skew_th,
        small_file_mb=args.small_file_mb,
        shuffle_heavy_mb=args.shuffle_heavy_mb,
        files_per_partition_threshold=args.files_per_part_th,
    )

    print("\n=== METRICS ===")
    for k, v in res["metrics"].items():
        print(f"{k}: {v}")
    print("\n=== RULE-BASED RECS ===")
    for i, r in enumerate(res["recommendations"], 1):
        print(f"{i}. [{r['impact']}] {r['issue']} — {r['why']}")
        for a in r["actions"]:
            print(f"   - {a}")
    print("\n=== AGENT REPORT ===")
    print(res["report"])

if __name__ == "__main__":
    main()