from typing import Dict, List, Optional
from adk_app.tools.summarize_metrics import summarize_metrics
from adk_app.tools.suggest_fixes import suggest_fixes
from adk_app.llm.base import LLM, NoopLLM

REPORT_SYSTEM = (
    "You are a senior data engineering assistant specialized in Spark tuning. "
    "Be concise, actionable, and justify each recommendation with the provided metrics."
)

def _build_prompt(metrics: Dict, recs: List[Dict], thresholds: Dict) -> str:
    return f"""
Context:
- Metrics: {metrics}
- Heuristic thresholds (current): {thresholds}
- Draft recommendations (rule-based): {recs}

Tasks:
1) Produce a prioritized, succinct action plan (bullet points).
2) For each recommendation, explain WHY (based on the metrics) and add concrete HOW-TO (Spark conf/SQL).
3) Propose BETTER threshold values for this job (skew_threshold, small_file_mb, shuffle_heavy_mb, files_per_partition_threshold).
4) Suggest one safe experiment to validate improvements in the next run.

Output: keep it short and structured.
"""

def analyze_eventlog_with_agent(
    eventlog_path: str,
    *,
    llm: Optional[LLM] = None,
    skew_threshold: float = 3.0,
    small_file_mb: float = 32.0,
    shuffle_heavy_mb: float = 2048.0,
    files_per_partition_threshold: float = 2.0,
) -> Dict:
    # 1) Perceive
    metrics = summarize_metrics(eventlog_path)
    # 2) Draft with tools
    recs = suggest_fixes(
        metrics,
        skew_threshold=skew_threshold,
        small_file_mb=small_file_mb,
        shuffle_heavy_mb=shuffle_heavy_mb,
        files_per_partition_threshold=files_per_partition_threshold,
    )
    # 3) Reason with LLM
    llm = llm or NoopLLM()
    thresholds = {
        "skew_threshold": skew_threshold,
        "small_file_mb": small_file_mb,
        "shuffle_heavy_mb": shuffle_heavy_mb,
        "files_per_partition_threshold": files_per_partition_threshold,
    }
    prompt = _build_prompt(metrics, recs, thresholds)
    report = llm.generate(prompt, system=REPORT_SYSTEM)

    return {"metrics": metrics, "recommendations": recs, "report": report}