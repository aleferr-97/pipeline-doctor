from typing import Dict, List, Optional, Any, Tuple
import json
from adk_app.llm.base import LLM

# ---- Output formatters ----------------------------------------------------------

def format_report_from_agent_json(agent_obj: Dict) -> str:
    """Render a compact markdown report from the structured agent JSON."""
    lines: List[str] = []
    ap = agent_obj.get("action_plan", []) or []
    tu = agent_obj.get("threshold_updates", {}) or {}
    se = agent_obj.get("safe_experiment", {}) or {}
    rf = agent_obj.get("risk_flags", []) or []

    if ap:
        for i, item in enumerate(ap[:3], 1):
            title = item.get("title", "Action")
            why = item.get("why", "")
            how = item.get("how", []) or []
            gain = item.get("expected_gain", "")
            # Single‑line per action, compact
            line = f"{i}. {title} — {why}."
            if how:
                line += f" [how: {'; '.join(how)}]"
            if gain:
                line += f" (expected: {gain})"
            lines.append(line)
        lines.append("")

    if tu:
        lines.append("Threshold updates:")
        for k, v in tu.items():
            if isinstance(v, dict):
                old = v.get("old")
                new = v.get("new")
                rationale = v.get("rationale", "")
                lines.append(f"- {k}: {old} → {new} ({rationale})")
        lines.append("")

    if se:
        steps = se.get("steps", []) or []
        guards = se.get("guardrails", []) or []
        sc = se.get("success_criteria")
        if steps:
            lines.append("Experiment steps: " + "; ".join(steps))
        if guards:
            lines.append("Guardrails: " + "; ".join(guards))
        if sc:
            lines.append("Success: " + sc)

    if rf and rf != ["none"]:
        lines.append("")
        lines.append("Risk flags:")
        for r in rf:
            lines.append(f"- {r}")

    return "\n".join(lines).strip()

# ---- Output helpers ----------------------------------------------------------

def try_load_json(text: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(text)
    except Exception:
        return None


def clean_threshold_updates(agent_obj: Dict) -> None:
    """Remove threshold updates that are no-ops or lack rationale."""
    tu = agent_obj.get("threshold_updates") or {}
    clean: Dict[str, Dict[str, Any]] = {}
    for k, v in tu.items():
        if not isinstance(v, dict):
            continue
        old = v.get("old")
        new = v.get("new")
        rationale = (v.get("rationale") or "").strip()
        if old is None or new is None:
            continue
        if new == old:
            continue
        if not rationale:
            continue
        clean[k] = {"old": old, "new": new, "rationale": rationale}
    agent_obj["threshold_updates"] = clean


def llm_to_json(llm: LLM, system: str, prompt: str) -> Tuple[Optional[Dict[str, Any]], str]:
    """Call the LLM once and try to parse JSON. Returns (obj_or_none, raw_text)."""
    raw = llm.generate(prompt, system=system)
    obj = try_load_json(raw)
    if obj is None:
        # common cleanup for models that wrap JSON in backticks
        cleaned = raw.strip().strip("`")
        obj = try_load_json(cleaned)
    return obj, raw
