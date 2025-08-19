import json
import argparse
import pprint
from typing import List, Dict, Any


def _percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    k = (len(values) - 1) * pct
    f = int(k)
    c = min(f + 1, len(values) - 1)
    if f == c:
        return float(values[f])
    return float(values[f] * (c - k) + values[c] * (k - f))


def summarize_metrics(
    eventlog_path: str, skew_threshold: float = 3.0, small_file_threshold_mb: float = 32.0
) -> Dict[str, Any]:
    """
    Legge un JSONL 'semplificato' con record tipo:
      {"type":"task","duration_ms":1234,"shuffleRead_mb":12.3,"stage_id":1}
      {"type":"output_file","partition_id":0,"size_mb":5.7}
    Restituisce metriche base utili per le diagnosi.

    Thresholds for heuristics are configurable:
    - skew_threshold: ratio of p95 to median task duration above which skew is suspected.
    - small_file_threshold_mb: average file size below which small files problem is suspected.
    """
    durations_ms: List[float] = []
    shuffle_reads_mb: List[float] = []
    files_per_partition: Dict[int, int] = {}
    file_sizes_mb: List[float] = []

    with open(eventlog_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            t = obj.get("type")
            if t == "task":
                durations_ms.append(float(obj.get("duration_ms", 0)))
                shuffle_reads_mb.append(float(obj.get("shuffleRead_mb", 0)))
            elif t == "output_file":
                pid = int(obj.get("partition_id", -1))
                files_per_partition[pid] = files_per_partition.get(pid, 0) + 1
                file_sizes_mb.append(float(obj.get("size_mb", 0)))

    median = _percentile(durations_ms, 0.5) if durations_ms else 0.0
    p95 = _percentile(durations_ms, 0.95) if durations_ms else 0.0
    skew_ratio = (p95 / median) if median > 0 else 0.0

    total_shuffle_read_mb = sum(shuffle_reads_mb)
    avg_file_mb = (sum(file_sizes_mb) / len(file_sizes_mb)) if file_sizes_mb else 0.0
    avg_files_per_partition = (
        (sum(files_per_partition.values()) / len(files_per_partition))
        if files_per_partition
        else 0.0
    )

    # Heuristic: suspect skew if p95/median ratio exceeds skew_threshold.
    # Reference: p95/median > 3 is a common empirical threshold seen in Spark AQE/skew join discussions
    # (see e.g. Databricks/Spark docs and community forums).
    is_skew_suspect = skew_ratio > skew_threshold

    # Heuristic: suspect small files problem if average file size is below small_file_threshold_mb.
    # Reference: <32MB is a conservative threshold based on Delta Lake file sizing best practices,
    # with typical target file size ~128MB (see Delta Lake docs and Databricks recommendations).
    is_small_files_problem = avg_file_mb < small_file_threshold_mb

    return {
        "num_tasks": len(durations_ms),
        "median_task_ms": round(median, 2),
        "p95_task_ms": round(p95, 2),
        "skew_ratio": round(skew_ratio, 2),
        "shuffle_read_mb": round(total_shuffle_read_mb, 2),
        "avg_file_mb": round(avg_file_mb, 2),
        "avg_files_per_partition": round(avg_files_per_partition, 2),
        "is_skew_suspect": is_skew_suspect,
        "is_small_files_problem": is_small_files_problem,
    }


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Summarize MiniSpark JSONL log")
    parser.add_argument("eventlog", help="Path al JSONL event log")
    parser.add_argument("--skew-th", type=float, default=3.0, help="Soglia skew ratio (p95/median)")
    parser.add_argument("--small-file-mb", type=float, default=32.0, help="Soglia small files (MB)")
    args = parser.parse_args()

    metrics = summarize_metrics(
        args.eventlog, skew_threshold=args.skew_th, small_file_threshold_mb=args.small_file_mb
    )
    pprint.pp(metrics)
