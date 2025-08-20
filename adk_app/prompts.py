import json
from typing import Dict, List

# --- System messages ---
DRAFT_SYSTEM = (
    "You are a senior Spark performance engineer. Be surgical and practical. "
    "Return STRICT JSON only (no prose). "
    "Respond with raw JSON only, no markdown"
)

REFINE_SYSTEM = (
    "You are a careful reviewer. You must output STRICT JSON only (no prose). "
    "Ensure the JSON matches the requested schema and is compact and consistent."
)

# --- Prompt builders ---
def build_draft_prompt(metrics: Dict, recs: List[Dict], thresholds: Dict) -> str:
    ref_actions = {r["issue"]: r.get("actions", []) for r in recs if r.get("actions")}
    issues_only = [{k: v for k, v in r.items() if k != "actions"} for r in recs]

    return f"""
Context:
- metrics: {metrics}
- heuristic_issues: {issues_only}
- reference_actions: {ref_actions}
- thresholds: {thresholds}

Constraints:
- No preamble, no headings.
- Max 3 items in action_plan.
- Prefer reference_actions when relevant; avoid risky/unsupported steps.
- Use only supported Spark/Delta features.

Additional rules:
- Do not include threshold_updates entries where new == old.
- Rationale must be non-empty; if no change, omit the key.
- Each how must be a concrete Spark/Delta conf or operation (e.g., exact spark.sql.* key or Delta command).
- expected_gain must be measurable (e.g., "-20–30% p95 task ms", "small files < N").

Return STRICT JSON that matches this schema exactly:
{{
  "action_plan": [
    {{"title": "string", "why": "string", "how": ["string", "..."], "expected_gain": "string"}}
  ],
  "threshold_updates": {{
    "skew_threshold": {{"old": {thresholds.get('skew_threshold')}, "new": 5.0, "rationale": "string"}},
    "small_file_mb": {{"old": {thresholds.get('small_file_mb')}, "new": 32.0, "rationale": "string"}},
    "shuffle_heavy_mb": {{"old": {thresholds.get('shuffle_heavy_mb')}, "new": 2048.0, "rationale": "string"}},
    "files_per_partition_threshold": {{"old": {thresholds.get('files_per_partition_threshold')}, "new": 2.0, "rationale": "string"}}
  }},
  "safe_experiment": {{
    "steps": ["string", "..."],
    "guardrails": ["string", "..."],
    "success_criteria": "string"
  }},
  "risk_flags": ["string", "..."]
}}

Do not add any extra keys. Output JSON only.
"""

def build_refine_prompt(metrics: Dict, recs: List[Dict], thresholds: Dict, draft: Dict) -> str:
    return f"""
You are refining an assistant's draft JSON. Make it concise, valid to the schema, with at most 3 actions.

Context:
- metrics: {metrics}
- heuristic_issues: {[{k: v for k, v in r.items() if k != "actions"} for r in recs]}
- thresholds: {thresholds}

Draft to refine (JSON):
{json.dumps(draft, ensure_ascii=False)}

Requirements:
- Keep only fields from the schema (action_plan, threshold_updates, safe_experiment, risk_flags).
- Max 3 items in action_plan. Each item must have title, why, how[], expected_gain.
- Prefer reference actions implicitly if present in the draft; do not invent risky steps.
- Output STRICT JSON only, no extra keys, no prose.
- Do not include threshold_updates entries where new == old.
- Rationale must be non-empty; if no change, omit the key.
- Each how must be a concrete Spark/Delta conf or operation.
- expected_gain must be measurable.
"""