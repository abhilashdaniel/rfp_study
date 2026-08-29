"""
Validation Tool
Checks the raw LLM scorecard against the active criteria schema, fills in
any missing criteria, clips out-of-range scores, and records every
correction as a warning so the final result stays fully explainable.

This is deterministic Python only - the LLM's arithmetic is never trusted.
"""
from typing import Any


def validate_and_normalize(
    raw_result: dict[str, Any],
    supplier_name: str,
    active_criteria: list[dict],
) -> dict[str, Any]:
    """
    Returns a dict:
        {
          "supplier_name": str,
          "criteria": [ { criterion_id, name, weight, max_score, score, justification, evidence } ... ],
          "risks": [...],
          "overall_summary": str,
          "warnings": [ "..." ],
        }
    Guaranteed to contain exactly one entry per active criterion, in
    active_criteria order, with a numeric score clipped to [0, max_score].
    """
    warnings: list[str] = []

    if not isinstance(raw_result, dict):
        warnings.append("LLM response was not a JSON object; using empty result.")
        raw_result = {}

    raw_criteria_list = raw_result.get("criteria", [])
    if not isinstance(raw_criteria_list, list):
        warnings.append("`criteria` field missing or not a list; treating as empty.")
        raw_criteria_list = []

    raw_by_id = {}
    for item in raw_criteria_list:
        if isinstance(item, dict) and "criterion_id" in item:
            try:
                cid = int(item["criterion_id"])
                raw_by_id[cid] = item
            except (TypeError, ValueError):
                warnings.append(f"Skipped a criterion entry with non-numeric criterion_id: {item.get('criterion_id')!r}")

    normalized_criteria = []
    for crit in active_criteria:
        cid = crit["criterion_id"]
        max_score = crit["max_score"]
        entry = raw_by_id.get(cid)

        if entry is None:
            warnings.append(f"Missing score for criterion '{crit['name']}' (id={cid}); defaulted to 0.")
            score = 0
            justification = "No score returned by LLM; defaulted to 0."
            evidence = ""
        else:
            score_raw = entry.get("score", 0)
            try:
                score = float(score_raw)
            except (TypeError, ValueError):
                warnings.append(f"Non-numeric score for criterion '{crit['name']}' ({score_raw!r}); defaulted to 0.")
                score = 0.0

            if score < 0:
                warnings.append(f"Score for '{crit['name']}' was negative ({score}); clipped to 0.")
                score = 0.0
            elif score > max_score:
                warnings.append(f"Score for '{crit['name']}' exceeded max ({score} > {max_score}); clipped to {max_score}.")
                score = float(max_score)

            justification = str(entry.get("justification", "")).strip() or "No justification provided."
            evidence = str(entry.get("evidence", "")).strip()

        normalized_criteria.append(
            {
                "criterion_id": cid,
                "name": crit["name"],
                "weight": crit["weight"],
                "max_score": max_score,
                "score": score,
                "justification": justification,
                "evidence": evidence,
            }
        )

    risks = raw_result.get("risks", [])
    if not isinstance(risks, list):
        warnings.append("`risks` field missing or not a list; treating as empty.")
        risks = []

    overall_summary = str(raw_result.get("overall_summary", "")).strip() or "No summary provided."

    active_weight_total = sum(c["weight"] for c in active_criteria)
    if abs(active_weight_total - 100) > 0.01:
        warnings.append(
            f"Active criteria weights total {active_weight_total}%, not 100%. "
            "Scores will be computed against the configured weights as-is."
        )

    return {
        "supplier_name": raw_result.get("supplier_name", supplier_name) or supplier_name,
        "criteria": normalized_criteria,
        "risks": risks,
        "overall_summary": overall_summary,
        "warnings": warnings,
    }
