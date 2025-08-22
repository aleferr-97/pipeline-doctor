# Adaptive Query Execution (AQE) in Spark
Enabling AQE (`spark.sql.adaptive.enabled=true`) lets Spark coalesce shuffle partitions and mitigate skew at runtime.
Skew join can be enabled with `spark.sql.adaptive.skewJoin.enabled=true`. Effective when the skew ratio (p95/median) is high (e.g. >3).
Expected impact: reduce tail latency (p95 task time) by ~20–35% in skewed joins.
Risks: adds planning overhead; may interact with broadcast thresholds.

Key knobs:
- spark.sql.adaptive.enabled=true
- spark.sql.adaptive.skewJoin.enabled=true
- spark.sql.adaptive.coalescePartitions.enabled=true