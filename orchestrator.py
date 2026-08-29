"""
Orchestrator Agent
Controls the workflow end-to-end and calls each tool in the required
order (per brief section 3 & 4). This is the only place that sequences
LLM calls with deterministic Python tools - it never lets the LLM decide
arithmetic, benchmarks, tie-breaks, or rank.

    Setup -> Input -> Batch -> Evaluate -> Validate -> Score -> Benchmark
    -> Rank -> Persist -> Present
"""
from db import repository
from tools.document_tool import extract_text_from_pdf
from tools.evaluation_agent import evaluate_supplier
from tools.validation_tool import validate_and_normalize
from tools.ranking_tool import run_ranking_pipeline


def run_evaluation_batch(supplier_inputs: list[dict], model: str, progress_callback=None) -> dict:
    """
    supplier_inputs: list of dicts, each:
        {
          "supplier_name": str,
          "submission_date": "YYYY-MM-DD",
          "experience_rating": float,
          "file_bytes": bytes,
        }

    Returns:
        {
          "rfp_run_id": str,
          "suppliers": [ ... fully validated, scored, ranked supplier dicts ... ]
        }
    """
    # 1. Setup: reload active criteria fresh for this run.
    active_criteria = repository.get_active_criteria()
    if not active_criteria:
        raise ValueError("No active evaluation criteria found. Configure criteria in the database first.")

    # 2. Batch: create a run identifier.
    run_id = repository.create_run()

    validated_suppliers = []
    total = len(supplier_inputs)

    for idx, supplier_input in enumerate(supplier_inputs, start=1):
        name = supplier_input["supplier_name"]
        if progress_callback:
            progress_callback(idx, total, f"Extracting text for {name}...")

        # 3. Evaluate step (a): extract text
        proposal_text = extract_text_from_pdf(supplier_input["file_bytes"])

        if progress_callback:
            progress_callback(idx, total, f"Scoring {name} with LLM...")

        # 3. Evaluate step (b): LLM scoring
        raw_result = evaluate_supplier(name, proposal_text, active_criteria, model=model)

        # 4. Validate: schema + normalization
        validated = validate_and_normalize(raw_result, name, active_criteria)
        validated["submission_date"] = supplier_input["submission_date"]
        validated["experience_rating"] = supplier_input["experience_rating"]

        validated_suppliers.append(validated)

    if progress_callback:
        progress_callback(total, total, "Scoring, benchmarking, and ranking suppliers...")

    # 5. Score, 6. Benchmark, 7. Rank - all deterministic
    ranked_suppliers = run_ranking_pipeline(validated_suppliers)

    # 8. Persist: write results under one RFP_RUN_ID
    for supplier in ranked_suppliers:
        repository.save_supplier_result(run_id, supplier)

    repository.update_run_status(run_id, "completed")

    return {"rfp_run_id": run_id, "suppliers": ranked_suppliers}
