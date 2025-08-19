import math
from adk_app.tools.suggest_fixes import suggest_fixes

def _mk_metrics(**overrides):
    base = {
        "num_tasks": 100,
        "median_task_ms": 1200.0,
        "p95_task_ms": 4800.0,
        "skew_ratio": 1.0,
        "shuffle_read_mb": 100.0,
        "avg_file_mb": 64.0,
        "avg_files_per_partition": 1.0,
    }
    base.update(overrides)
    return base

def test_skew_triggers_high_priority_rec():
    m = _mk_metrics(skew_ratio=4.2)
    recs = suggest_fixes(m, skew_threshold=3.0)
    assert any(r["issue"] == "Data skew" and r["impact"] == "high" for r in recs)

def test_small_files_triggers_high_priority_rec():
    m = _mk_metrics(avg_file_mb=16.0)
    recs = suggest_fixes(m, small_file_mb=32.0)
    assert any(r["issue"] == "Small files" and r["impact"] == "high" for r in recs)

def test_shuffle_heavy_triggers_medium_rec():
    m = _mk_metrics(shuffle_read_mb=4096.0)
    recs = suggest_fixes(m, shuffle_heavy_mb=2048.0)
    assert any(r["issue"] == "Heavy shuffle" and r["impact"] == "medium" for r in recs)

def test_too_many_files_per_partition_triggers_medium_rec():
    m = _mk_metrics(avg_files_per_partition=3.5)
    recs = suggest_fixes(m, files_per_partition_threshold=2.0)
    assert any(r["issue"] == "Too many files per partition" and r["impact"] == "medium" for r in recs)

def test_parametric_thresholds_change_behavior():
    m = _mk_metrics(skew_ratio=2.8, avg_file_mb=40.0)
    # With strict thresholds we still trigger issues
    recs_strict = suggest_fixes(m, skew_threshold=2.5, small_file_mb=48.0)
    assert any(r["issue"] == "Data skew" for r in recs_strict)
    assert any(r["issue"] == "Small files" for r in recs_strict)

    # With loose thresholds we don't
    recs_loose = suggest_fixes(m, skew_threshold=3.5, small_file_mb=32.0)
    assert all(r["issue"] != "Data skew" for r in recs_loose)
    assert all(r["issue"] != "Small files" for r in recs_loose)

def test_recommendations_are_sorted_by_impact():
    m = _mk_metrics(skew_ratio=4.0, shuffle_read_mb=4096.0)
    recs = suggest_fixes(m)
    # 'high' issues should come before 'medium'
    impacts = [r["impact"] for r in recs]
    assert impacts == sorted(impacts, key=lambda x: {"high":0, "medium":1, "low":2}[x])