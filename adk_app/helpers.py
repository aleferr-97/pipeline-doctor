from typing import Dict, List, Optional, Any, Tuple
import json
import re
from adk_app.llm.base import LLM

# ---- Output formatters ----------------------------------------------------------

def _extract_json_substring(text: str) -> Optional[str]:
    """
    Best-effort extraction of a JSON object/array from a messy LLM string.
    - Strips code fences and surrounding backticks.
    - Finds the largest {...} or [...] span and returns that substring.
    """
    if not text:
        return None
    s = text.strip().strip("`")
    # Remove common code fences like ```json ... ```
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s, flags=re.IGNORECASE | re.DOTALL).strip()
    # Try to find an object
    obj_span = None
    stack = []
    for i, ch in enumerate(s):
        if ch == "{":
            stack.append(i)
        elif ch == "}":
            if stack:
                start = stack.pop(0)
                obj_span = (start, i)
    if obj_span:
        start, end = obj_span
        return s[start : end + 1]
    # Fallback: find array
    arr_span = None
    stack = []
    for i, ch in enumerate(s):
        if ch == "[":
            stack.append(i)
        elif ch == "]":
            if stack:
                start = stack.pop(0)
                arr_span = (start, i)
    if arr_span:
        start, end = arr_span
        return s[start : end + 1]
    return None

def format_report_from_agent_json(agent_obj: Any) -> str:
    """Render a compact markdown report from the structured agent JSON (robust to lists/strings)."""
    agent_obj = coerce_agent_obj(agent_obj)
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

def try_load_json(text: str) -> Optional[Any]:
    """
    Best-effort JSON loader tolerant to:
    - leading/trailing prose
    - code fences
    - JSON wrapped in backticks
    Returns a Python object (dict/list/etc.) or None.
    """
    if text is None:
        return None
    # Fast path
    try:
        return json.loads(text)
    except Exception:
        pass
    # Strip common wrappers
    s = (text or "").strip().strip("`")
    try:
        return json.loads(s)
    except Exception:
        pass
    # Try to extract the largest JSON-looking substring
    candidate = _extract_json_substring(s)
    if candidate:
        try:
            return json.loads(candidate)
        except Exception:
            return None
    return None

def coerce_agent_obj(agent_obj: Any) -> Dict[str, Any]:
    """
    Normalize various possible shapes from the LLM into a dict that uses the expected schema keys.
    - If it's a dict, return as-is.
    - If it's a string, attempt to JSON-decode it.
    - If it's a list, assume it's an action_plan list and wrap it.
    - Otherwise, return an empty schema.
    """
    if isinstance(agent_obj, dict):
        return agent_obj
    if isinstance(agent_obj, str):
            parsed = try_load_json(agent_obj)
            if isinstance(parsed, dict):
                return parsed
            if isinstance(parsed, list):
                return {"action_plan": parsed}
            return {}
    if isinstance(agent_obj, list):
        return {"action_plan": agent_obj}
    return {}

def clean_threshold_updates(agent_obj: Any) -> None:
    """Remove threshold updates that are no-ops or lack rationale (robust to wrong shapes)."""
    if not isinstance(agent_obj, dict):
        return
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
    """
    Call the LLM once and try to parse JSON. Returns (dict_or_none, raw_text).
    If the parsed top-level is a list, wrap it under {"action_plan": ...}.
    """
    raw = llm.generate(prompt, system=system)
    parsed = try_load_json(raw)
    if isinstance(parsed, list):
        return {"action_plan": parsed}, raw
    if isinstance(parsed, dict):
        return parsed, raw
    # common cleanup for models that wrap JSON in backticks already handled in try_load_json
    return None, raw
