# Delta Lake Compaction & Small Files
Small files (<32–128MB) hurt scan performance and metadata ops. Use compaction:
- `OPTIMIZE table` (Databricks/Delta, z-order optional)
- `coalesce(repartition)` before write for batch jobs

Targets:
- Per-file size: 32–128MB
- Partitions aligned with query predicates

Risks: temporary storage growth during rewrite; consider scheduling compaction off-peak.