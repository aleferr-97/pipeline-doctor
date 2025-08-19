from adk_app.tools.summarize_metrics import summarize_metrics
from pathlib import Path

SAMPLE = """\
{"type":"task","duration_ms":1000,"shuffleRead_mb":10,"stage_id":1}
{"type":"task","duration_ms":1200,"shuffleRead_mb":12,"stage_id":1}
{"type":"task","duration_ms":9000,"shuffleRead_mb":100,"stage_id":2}
{"type":"output_file","partition_id":0,"size_mb":6}
{"type":"output_file","partition_id":1,"size_mb":7}
"""


def test_summarize(tmp_path: Path):
    p = tmp_path / "log.jsonl"
    p.write_text(SAMPLE)
    m = summarize_metrics(str(p), skew_threshold=3.0, small_file_threshold_mb=32.0)
    assert m["num_tasks"] == 3
    assert m["is_skew_suspect"] is True
    assert m["is_small_files_problem"] is True
