from typing import Dict, List

def suggest_fixes(
    m: Dict[str, float],
    *,
    skew_threshold: float = 3.0,
    small_file_mb: float = 32.0,
    shuffle_heavy_mb: float = 2048.0,           # ~2GB -> conservative warning
    files_per_partition_threshold: float = 2.0
) -> List[dict]:
    """
    Produce actionable recommendations (with rationale) from the metrics computed by `summarize_metrics`.

    References (heuristics):
    - Skew: there is no official universal threshold; using p95/median > ~3 as a trigger is a common empirical rule.
      In Spark it is generally recommended to enable AQE and skew-join handling.
    - Small files: typical target sizes for columnar formats (Parquet/Delta) are around ~128MB; <32MB is a conservative
      threshold to flag very small files relative to the target. Compaction/OPTIMIZE/coalesce help.
    - Heavy shuffle: the proper threshold depends on cluster/dataset; 2GB is a cautious default to suggest
      AQE/broadcast/coalescing.
    - Files per partition: values >2 often indicate over-partitioning / fragmented writes.
    All thresholds are **parametric** and should be adapted to the specific environment.
    """
    recs: List[dict] = []

    def add(impact: str, issue: str, why: str, actions: List[str]):
        recs.append({"impact": impact, "issue": issue, "why": why, "actions": actions})

    # 1) Skew
    if m.get("skew_ratio", 0) > skew_threshold:
        add(
            "high", "Data skew",
            f"Skew ratio {m['skew_ratio']} > treshold {skew_threshold}.",
            [
                "Enable AQE: spark.sql.adaptive.enabled=true",
                "Enable skew join: spark.sql.adaptive.skewJoin.enabled=true",
                "Salting/repartition on the uneven key",
                "Evaluate broadcast join if one side is small (≈<= 512MB)",
            ],
        )

    # 2) Shuffle heavy
    if m.get("shuffle_read_mb", 0) > shuffle_heavy_mb:
        add(
            "medium", "Heavy shuffle",
            f"Shuffle totale {m['shuffle_read_mb']} MB > treshold {shuffle_heavy_mb} MB.",
            [
                "Rivedi strategie di join; riduci stage con shuffle",
                "Imposta spark.sql.autoBroadcastJoinThreshold in modo adeguato",
                "AQE coalesce: spark.sql.adaptive.coalescePartitions.enabled=true",
            ],
        )

    # 3) Small files
    avg_file = m.get("avg_file_mb", 0)
    if 0 < avg_file < small_file_mb:
        add(
            "high", "Small files",
            f"File medi {avg_file} MB < treshold {small_file_mb} MB.",
            [
                "Compaction (Delta OPTIMIZE / coalesce before writing)",
                "Tuning partitioning - target 32-128MB/file",
                "Compaction on hot tables",
            ],
        )

    # 4) Too many files per partition
    if m.get("avg_files_per_partition", 0) > files_per_partition_threshold:
        add(
            "medium", 
            "Too many files per partition",
            f"Average files/partition = {m['avg_files_per_partition']} > threshold {files_per_partition_threshold}.",
            [
                "Reduce parallelism in write or enable AQE partition coalescing",
                "Review partitioning strategy (avoid over-partitioning)",
            ],
        )

    order = {"high": 0, "medium": 1, "low": 2}
    recs.sort(key=lambda r: order.get(r["impact"], 9))
    return recs