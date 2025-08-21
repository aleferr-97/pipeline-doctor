import logging
from typing import Dict, Optional

from adk_app.helpers import (
    format_report_from_agent_json,
    clean_threshold_updates,
    llm_to_json
)
from adk_app.llm.base import LLM, NoopLLM
from adk_app.prompts import (
    DRAFT_SYSTEM,
    REFINE_SYSTEM,
    build_draft_prompt,
    build_refine_prompt,
)
from adk_app.tools.suggest_fixes import suggest_fixes
from adk_app.tools.summarize_metrics import summarize_metrics

logger = logging.getLogger(__name__)

# ---- Public API --------------------------------------------------------------

def analyze_eventlog_with_agent(
    eventlog_path: str,
    *,
    llm: Optional[LLM] = None,
    skew_threshold: float = 3.0,
    small_file_mb: float = 32.0,
    shuffle_heavy_mb: float = 2048.0,
    files_per_partition_threshold: float = 2.0,
) -> Dict:
    """Analyze an eventlog with heuristics + LLM (draft→refine)."""
    # 1) Perceive
    metrics = summarize_metrics(eventlog_path)
    logger.debug(f"Summarized metrics: {metrics}")

    # 2) Draft with tools
    recs = suggest_fixes(
        metrics,
        skew_threshold=skew_threshold,
        small_file_mb=small_file_mb,
        shuffle_heavy_mb=shuffle_heavy_mb,
        files_per_partition_threshold=files_per_partition_threshold,
    )
    logger.debug(f"Generated recommendations: {recs}")

    # 3) Reason (LLM)
    llm = llm or NoopLLM()
    thresholds = {
        "skew_threshold": skew_threshold,
        "small_file_mb": small_file_mb,
        "shuffle_heavy_mb": shuffle_heavy_mb,
        "files_per_partition_threshold": files_per_partition_threshold,
    }

    # Draft
    draft_prompt = build_draft_prompt(metrics, recs, thresholds)
    draft_obj, draft_raw = llm_to_json(llm, DRAFT_SYSTEM, draft_prompt)
    logger.debug(f"Draft parsed: {draft_obj is not None}")

    if not draft_obj:
        # No valid JSON → return textual draft
        logger.info("Draft JSON parse failed; returning textual draft.")
        return {
            "metrics": metrics,
            "recommendations": recs,
            "report": draft_raw,
            "agent": None,
            "draft_raw": draft_raw,
            "refined_raw": "",
        }

    # Refine
    refine_prompt = build_refine_prompt(metrics, recs, thresholds, draft_obj)
    refined_obj, refined_raw = llm_to_json(llm, REFINE_SYSTEM, refine_prompt)
    logger.debug(f"Refined parsed: {refined_obj is not None}")

    agent_structured = refined_obj or draft_obj

    # Guard: some models may return a top-level list (e.g., list of lines or actions).
    # Normalize to a dict schema so downstream utils never crash.
    if isinstance(agent_structured, list):
        logger.debug("Normalizing LLM output: wrapping top-level list under 'action_plan'.")
        agent_structured = {"action_plan": agent_structured}

    clean_threshold_updates(agent_structured)
    formatted_report = format_report_from_agent_json(agent_structured)

    return {
        "metrics": metrics,
        "recommendations": recs,
        "report": formatted_report,
        "agent": agent_structured,
        "draft_raw": draft_obj,
        "refined_raw": refined_obj,
    }