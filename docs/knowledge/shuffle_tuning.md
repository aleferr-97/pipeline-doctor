# Shuffle Tuning
`spark.sql.shuffle.partitions` controls the number of reduce partitions. Too high → many tiny files; too low → large tasks.
Typical starting points: 200–400 for medium jobs; tune based on task time and output file size targets.
Combine with AQE coalesce to downsize partitions automatically.