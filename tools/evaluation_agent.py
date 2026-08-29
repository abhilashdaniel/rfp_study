"""
Evaluation Agent
Builds a grounded, evidence-only scoring prompt for a single supplier and
asks the LLM to return one JSON scorecard against the active criteria.

The LLM is only ever allowed to judge proposal content. It never sees
peer suppliers, never computes weighted scores, benchmarks, or ranks -
that is enforced entirely in deterministic Python (validation_tool /
ranking_tool).
"""
import json

from utils.llm_client import call_llm_for_scoring

PROMPT_TEMPLATE = """You are an impartial procurement evaluator. Score the supplier proposal below
against the given criteria using ONLY evidence found in the proposal text. Do not invent facts.
If evidence for a criterion is weak or missing, give a low score and say so explicitly.

Supplier name: {supplier_name}

CRITERIA:
{criteria_json}

Instructions:
- Return exactly one result for every criterion listed above, using its criterion_id.
- Each score must be an integer between 0 and that criterion's max_score (inclusive).
- "justification" should be 1-2 sentences explaining the score.
- "evidence" should quote or closely paraphrase the specific part of the proposal that supports the score.
- Also return a short list of "risks" you noticed in the proposal (empty list if none) and a 2-3 sentence "overall_summary".
- Output VALID JSON ONLY. No markdown, no commentary, no code fences. Match this exact shape:

{{
  "supplier_name": "{supplier_name}",
  "criteria": [
    {{"criterion_id": 1, "score": 8, "max_score": 10, "justification": "...", "evidence": "..."}}
  ],
  "risks": ["..."],
  "overall_summary": "..."
}}

PROPOSAL TEXT:
\"\"\"
{proposal_text}
\"\"\"
"""


def build_prompt(supplier_name: str, proposal_text: str, active_criteria: list[dict]) -> str:
    criteria_json = json.dumps(
        [
            {
                "criterion_id": c["criterion_id"],
                "name": c["name"],
                "description": c["description"],
                "max_score": c["max_score"],
            }
            for c in active_criteria
        ],
        indent=2,
    )
    # Truncate very long documents to keep prompts reasonable
    truncated_text = proposal_text[:15000]
    return PROMPT_TEMPLATE.format(
        supplier_name=supplier_name,
        criteria_json=criteria_json,
        proposal_text=truncated_text,
    )


def evaluate_supplier(supplier_name: str, proposal_text: str, active_criteria: list[dict], model: str) -> dict:
    """Returns the raw (unvalidated) LLM scorecard dict for one supplier."""
    prompt = build_prompt(supplier_name, proposal_text, active_criteria)
    raw_result = call_llm_for_scoring(prompt, model=model)
    return raw_result
