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

ALLOWED_ACTIONS = [
  "spark.sql.adaptive.enabled=true",
  "spark.sql.adaptive.skewJoin.enabled=true",
  "spark.sql.shuffle.partitions=<N>",
  "Delta OPTIMIZE",
  "coalesce before writing",
]

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
- Do not include threshold_updates entries where new == old (and omit the key entirely if there are no changes). If a change is proposed, include a non-empty rationale.
- For each issue in heuristic_issues, pick **exactly one** action (no duplicates). For data skew choose **one** among: `spark.sql.adaptive.enabled=true`, `spark.sql.adaptive.skewJoin.enabled=true`, or salting/repartition (not both AQE and skewJoin).
- Each `how` must be a concrete Spark/Delta setting or operation (exact key/value or command). **Never** output placeholders like `N`, `<value>`, or examples verbatim.
- `expected_gain` must be **numeric and derived from the input metrics/thresholds**, and must explicitly show both current and target values with units, e.g. `"p95: 13620 ms → 9500 ms (~-30%)"`, `"avg file size: 6.27 MB → ≥ 32 MB"`.
- When estimating targets, use simple proportional reasoning based on the metrics provided:
  - If `is_skew_suspect` is true and `p95_task_ms` is present, assume skew mitigation can reduce p95 by **20%–35%**. Pick a concrete target in that range and round to integers.
  - If `is_small_files_problem` is true and `avg_file_mb` < `small_file_mb`, set target `avg file size` to **≥ small_file_mb** (use the threshold value).
- Risk flags must be grounded in the chosen action (e.g. for broadcast joins mention OOM risk; for compaction mention temporary storage growth). If no risks are identified, return `["no material risks identified for the proposed actions"]`.
- Each `how` must be one of: {ALLOWED_ACTIONS} (numeric values must be explicit, e.g. `spark.sql.shuffle.partitions=400`). Reject generic or incomplete keys.
- Output **STRICT JSON** only; no prose, no markdown, no headings.
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
- expected_gain must be measurable and use concrete numeric targets derived from metrics/thresholds (e.g., "-20–30% p95 task ms", "avg file ≥ {thresholds.get('small_file_mb')} MB"). Never output placeholders like N, "<value>", or examples verbatim.
- Keep at most 1 action per issue and only for issues listed in heuristic_issues; remove or merge duplicates.
- risk_flags must contain potential side effects or risks of the suggested actions (e.g., "Broadcast join may cause OOM", "Compaction may increase temporary storage").
- If no risks are identified, output a list with something says that there are no risk if you take the suggested actions.
- Each how must be one of: {ALLOWED_ACTIONS} (numeric values must be explicit, e.g. spark.sql.shuffle.partitions=400). Reject generic or incomplete keys.
- Keep **exactly one action per issue**; if multiple actions address the same issue (e.g., AQE and skewJoin for skew), keep the most impactful single action and remove the others.
- Ensure `expected_gain` is numeric and comparative (current → target with units) using the provided metrics/thresholds; do not accept placeholders or template text.
"""