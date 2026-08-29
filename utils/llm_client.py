"""
Thin wrapper around the Anthropic API so the rest of the app never has
to think about SDK details. Also provides a deterministic MOCK mode
(no API key required) so the app can be demoed / graded offline.
"""
import json
import os
import re
import hashlib

MOCK_MODE_ENV = "RFP_MOCK_LLM"


def _get_api_key():
    return os.environ.get("ANTHROPIC_API_KEY")


def is_mock_mode() -> bool:
    if os.environ.get(MOCK_MODE_ENV, "").lower() in ("1", "true", "yes"):
        return True
    return _get_api_key() is None


def _extract_json(text: str) -> str:
    """Pulls a JSON object out of a model response, stripping markdown fences."""
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text.strip(), flags=re.IGNORECASE).strip()
    text = re.sub(r"```$", "", text.strip()).strip()
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        return match.group(0)
    return text


def call_llm_for_scoring(prompt: str, model: str = "claude-sonnet-4-6", max_tokens: int = 2000) -> dict:
    """
    Sends the scoring prompt to Claude and returns the parsed JSON dict.
    Falls back to a deterministic mock response if no API key is configured,
    so the pipeline (validation/scoring/ranking) can still be run and tested.
    """
    if is_mock_mode():
        return _mock_response(prompt)

    from anthropic import Anthropic

    client = Anthropic(api_key=_get_api_key())
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    raw_text = "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    )
    json_str = _extract_json(raw_text)
    return json.loads(json_str)


def _mock_response(prompt: str) -> dict:
    """
    Deterministic 'fake LLM' used when no ANTHROPIC_API_KEY is set.
    Derives stable pseudo-random-but-repeatable scores from a hash of the
    prompt so re-running the same supplier/criteria always yields the same
    output (useful for demoing reproducibility).
    """
    supplier_match = re.search(r"Supplier name:\s*(.+)", prompt)
    supplier_name = supplier_match.group(1).strip() if supplier_match else "Unknown Supplier"

    criteria_block_match = re.search(r"CRITERIA:\s*(\[.*?\])", prompt, re.DOTALL)
    criteria = []
    if criteria_block_match:
        try:
            criteria = json.loads(criteria_block_match.group(1))
        except json.JSONDecodeError:
            criteria = []

    results = []
    for c in criteria:
        seed = f"{supplier_name}-{c.get('name')}"
        h = int(hashlib.sha256(seed.encode()).hexdigest(), 16)
        max_score = c.get("max_score", 10)
        score = 4 + (h % (max_score - 3))  # spread scores between 4 and max_score
        results.append(
            {
                "criterion_id": c.get("criterion_id"),
                "score": score,
                "max_score": max_score,
                "justification": f"[MOCK] Proposal shows {'strong' if score >= max_score * 0.7 else 'moderate'} "
                                  f"alignment on {c.get('name')}.",
                "evidence": f"[MOCK] Derived from supplier document text (no live LLM call; set ANTHROPIC_API_KEY to enable real scoring).",
            }
        )

    return {
        "supplier_name": supplier_name,
        "criteria": results,
        "risks": ["[MOCK] No live LLM configured; risks not analyzed."],
        "overall_summary": f"[MOCK] Deterministic placeholder evaluation for {supplier_name}.",
    }
