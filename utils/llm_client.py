"""
Thin wrapper around the LLM API so the rest of the app never has to think
about SDK details. Supports two providers, selected via the RFP_LLM_PROVIDER
environment variable (default: "anthropic"):

    RFP_LLM_PROVIDER=anthropic   – uses Anthropic Claude (ANTHROPIC_API_KEY)
    RFP_LLM_PROVIDER=cohere      – uses Cohere Command (COHERE_API_KEY)

Also provides a deterministic MOCK mode (no API key required) so the full
pipeline can be demoed / graded offline.
"""
import json
import os
import re
import hashlib

MOCK_MODE_ENV = "RFP_MOCK_LLM"
PROVIDER_ENV = "RFP_LLM_PROVIDER"   # "anthropic" | "cohere"


# ---------------------------------------------------------------------------
# Provider helpers
# ---------------------------------------------------------------------------

def get_provider() -> str:
    """Returns the active provider name, lower-cased. Defaults to 'anthropic'."""
    return os.environ.get(PROVIDER_ENV, "anthropic").lower()


def _get_api_key() -> str | None:
    """Returns the API key for the active provider, or None if not set."""
    if get_provider() == "cohere":
        return os.environ.get("COHERE_API_KEY")
    return os.environ.get("ANTHROPIC_API_KEY")


def is_mock_mode() -> bool:
    if os.environ.get(MOCK_MODE_ENV, "").lower() in ("1", "true", "yes"):
        return True
    return _get_api_key() is None


# ---------------------------------------------------------------------------
# JSON extraction helper (shared by both providers)
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> str:
    """Pulls a JSON object out of a model response, stripping markdown fences."""
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"```$", "", text.strip()).strip()
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        return match.group(0)
    return text


# ---------------------------------------------------------------------------
# Anthropic backend
# ---------------------------------------------------------------------------

def _call_anthropic(prompt: str, model: str, max_tokens: int) -> dict:
    from anthropic import Anthropic

    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
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


# ---------------------------------------------------------------------------
# Cohere backend
# ---------------------------------------------------------------------------

def _call_cohere(prompt: str, model: str, max_tokens: int) -> dict:
    import cohere

    co = cohere.ClientV2(api_key=os.environ.get("COHERE_API_KEY"))
    response = co.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,   # low temperature for deterministic scoring
    )
    # Cohere ClientV2: response.message.content[0] is a typed block or plain dict
    content_block = response.message.content[0]
    raw_text = (
        content_block.text
        if hasattr(content_block, "text")
        else content_block["text"]
    ).strip()

    json_str = _extract_json(raw_text)
    return json.loads(json_str)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def call_llm_for_scoring(
    prompt: str,
    model: str = "claude-3-5-sonnet-20241022",
    max_tokens: int = 2000,
) -> dict:
    """
    Sends the scoring prompt to the configured LLM provider and returns the
    parsed JSON dict.

    Provider routing:
        RFP_LLM_PROVIDER=anthropic  →  Anthropic Claude  (default model: claude-3-5-sonnet-20241022)
        RFP_LLM_PROVIDER=cohere     →  Cohere Command    (default model: command-r7b-12-2024)

    Falls back to a deterministic mock response if no API key is configured
    for the active provider, so the full pipeline can be run and tested offline.
    """
    if is_mock_mode():
        return _mock_response(prompt)

    provider = get_provider()
    try:
        if provider == "cohere":
            return _call_cohere(prompt, model, max_tokens)
        else:
            return _call_anthropic(prompt, model, max_tokens)
    except json.JSONDecodeError as exc:
        # Return a sentinel that validate_and_normalize will log as a warning
        return {"_error": f"JSON parse failed: {exc}", "criteria": []}
    except Exception as exc:
        return {"_error": str(exc), "criteria": []}


# ---------------------------------------------------------------------------
# Deterministic mock (no API key needed)
# ---------------------------------------------------------------------------

def _mock_response(prompt: str) -> dict:
    """
    Deterministic 'fake LLM' used when no API key is set.
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
                "evidence": "[MOCK] Derived from supplier document text (no live LLM call; set an API key to enable real scoring).",
            }
        )

    return {
        "supplier_name": supplier_name,
        "criteria": results,
        "risks": ["[MOCK] No live LLM configured; risks not analyzed."],
        "overall_summary": f"[MOCK] Deterministic placeholder evaluation for {supplier_name}.",
    }
