"""
Agentic RFP Evaluation and Supplier Ranking - Streamlit UI

Screens:
  - Criteria            : active criteria, weights, max score
  - Supplier Input      : multi-PDF upload + metadata + Evaluate button
  - Leaderboard         : rank, supplier, absolute score, PPI, date, experience
  - Detailed Scorecard  : per-criterion score, benchmark, gap, relative %, evidence
  - Run Details         : RFP_RUN_ID, warnings, tie-break explanation, JSON download
"""
import json
import os

import pandas as pd
import streamlit as st

from db import repository
from orchestrator import run_evaluation_batch
from utils.llm_client import is_mock_mode

st.set_page_config(page_title="Agentic RFP Evaluation", layout="wide")

# ---------------------------------------------------------------------------
# Sidebar: LLM configuration
# ---------------------------------------------------------------------------
_COHERE_MODELS = [
    "command-r7b-12-2024",
    "command-r-plus-08-2024",
    "command-r-08-2024",
]
_OPENROUTER_MODELS = [
    "google/gemini-2.0-flash-001",
    "meta-llama/llama-3.3-70b-instruct",
    "mistralai/mistral-small-3.1-24b-instruct",
    "qwen/qwen3-14b",
]

with st.sidebar:
    st.header("⚙️ Configuration")

    provider = st.radio(
        "LLM Provider",
        ["Cohere", "OpenRouter"],   # Cohere is default (first item)
        horizontal=True,
        help="Select which LLM provider to use for scoring.",
    )
    os.environ["RFP_LLM_PROVIDER"] = provider.lower()

    if provider == "OpenRouter":
        api_key_input = st.text_input(
            "OpenRouter API key",
            type="password",
            help="Get a free key at openrouter.ai. Leave blank for MOCK mode.",
        )
        if api_key_input:
            os.environ["OPENROUTER_API_KEY"] = api_key_input
        model_choice = st.selectbox("Model", _OPENROUTER_MODELS, index=0)
    else:
        api_key_input = st.text_input(
            "Cohere API key",
            type="password",
            help="Leave blank to run in offline MOCK mode.",
        )
        if api_key_input:
            os.environ["COHERE_API_KEY"] = api_key_input
        model_choice = st.selectbox("Model", _COHERE_MODELS, index=0)

    if is_mock_mode():
        st.warning("Running in MOCK mode — no API key detected. Scores are deterministic placeholders.")
    else:
        st.success(f"Live LLM scoring enabled ({provider}).")

    st.divider()
    st.caption("Agentic RFP Evaluation & Supplier Ranking — classroom mini project")

st.title("📋 Agentic RFP Evaluation & Supplier Ranking")

tab_criteria, tab_input, tab_leaderboard, tab_scorecards, tab_run = st.tabs(
    ["Criteria", "Supplier Input & Evaluate", "Leaderboard", "Detailed Scorecards", "Run Details"]
)

# ---------------------------------------------------------------------------
# Screen: Criteria
# ---------------------------------------------------------------------------
with tab_criteria:
    st.subheader("Active Evaluation Criteria")
    all_criteria = repository.get_all_criteria()
    if not all_criteria:
        st.error("No criteria found in the database. Run `python db/init_db.py` to seed defaults.")
    else:
        df = pd.DataFrame(all_criteria)
        active_df = df[df["is_active"] == 1]
        total_weight = active_df["weight"].sum()

        st.dataframe(
            df[["criterion_id", "name", "description", "weight", "max_score", "is_active"]],
            width="stretch",
            hide_index=True,
        )

        if abs(total_weight - 100) > 0.01:
            st.warning(f"Active criteria weights currently total **{total_weight}%**, not 100%.")
        else:
            st.success(f"Active criteria weights total **{total_weight}%**. ✅")

        st.caption("To activate, deactivate, or reweight criteria, edit the `evaluation_criteria` table directly "
                    "(e.g. via a SQLite browser or a small admin script) — no code changes needed.")

# ---------------------------------------------------------------------------
# Screen: Supplier Input & Evaluate
# ---------------------------------------------------------------------------
with tab_input:
    st.subheader("Upload Supplier Proposals")

    if "num_suppliers" not in st.session_state:
        st.session_state.num_suppliers = 4

    num_suppliers = st.number_input(
        "Number of suppliers to evaluate in this batch", min_value=1, max_value=10,
        value=st.session_state.num_suppliers, step=1,
    )
    st.session_state.num_suppliers = num_suppliers

    supplier_inputs = []
    validation_messages = []

    cols_per_row = 2
    rows = (num_suppliers + cols_per_row - 1) // cols_per_row

    idx = 0
    for _ in range(rows):
        cols = st.columns(cols_per_row)
        for col in cols:
            idx += 1
            if idx > num_suppliers:
                break
            with col:
                st.markdown(f"**Supplier {idx}**")
                name = st.text_input(f"Supplier name #{idx}", key=f"name_{idx}")
                date = st.date_input(f"Submission date #{idx}", key=f"date_{idx}")
                experience = st.slider(f"Historical experience rating #{idx} (0-10)", 0.0, 10.0, 5.0, key=f"exp_{idx}")
                pdf_file = st.file_uploader(f"Proposal PDF #{idx}", type=["pdf"], key=f"file_{idx}")

                if name and pdf_file is not None:
                    supplier_inputs.append(
                        {
                            "supplier_name": name.strip(),
                            "submission_date": date.isoformat(),
                            "experience_rating": experience,
                            "file_bytes": pdf_file.read(),
                        }
                    )
                elif name or pdf_file is not None:
                    validation_messages.append(f"Supplier {idx}: both a name and a PDF are required to include it in the batch.")

    if validation_messages:
        for msg in validation_messages:
            st.info(msg)

    st.divider()
    ready = len(supplier_inputs) >= 1
    if not ready:
        st.info("Add at least one supplier (name + PDF) to enable evaluation.")

    if st.button("🚀 Evaluate Batch", type="primary", disabled=not ready):
        progress_bar = st.progress(0.0, text="Starting evaluation...")

        def progress_callback(current, total, message):
            progress_bar.progress(current / total, text=message)

        try:
            with st.spinner("Running agentic evaluation pipeline..."):
                result = run_evaluation_batch(supplier_inputs, model=model_choice, progress_callback=progress_callback)
            st.session_state["last_run_id"] = result["rfp_run_id"]
            st.session_state["last_run_suppliers"] = result["suppliers"]
            progress_bar.progress(1.0, text="Done.")
            st.success(f"Batch complete. RFP_RUN_ID: `{result['rfp_run_id']}`. See the Leaderboard tab.")
        except Exception as e:
            st.error(f"Evaluation failed: {e}")

# ---------------------------------------------------------------------------
# Screen: Leaderboard
# ---------------------------------------------------------------------------
with tab_leaderboard:
    st.subheader("Leaderboard")

    all_runs = repository.get_all_runs()
    if not all_runs:
        st.info("No runs yet. Evaluate a batch first.")
    else:
        run_options = {f"{r['created_at']} — {r['rfp_run_id']} ({r['status']})": r["rfp_run_id"] for r in all_runs}
        default_idx = 0
        if "last_run_id" in st.session_state:
            for i, (_, rid) in enumerate(run_options.items()):
                if rid == st.session_state["last_run_id"]:
                    default_idx = i
                    break

        selected_label = st.selectbox("Select a run", list(run_options.keys()), index=default_idx)
        selected_run_id = run_options[selected_label]
        st.session_state["selected_run_id"] = selected_run_id

        results = repository.get_run_results(selected_run_id)
        if results:
            board = pd.DataFrame(
                [
                    {
                        "Rank": r["final_rank"],
                        "Supplier": r["supplier_name"],
                        "Absolute Score": r["absolute_score"],
                        "PPI": r["ppi"],
                        "Submission Date": r["submission_date"],
                        "Experience Rating": r["experience_rating"],
                    }
                    for r in results
                ]
            ).sort_values("Rank")
            st.dataframe(board, width="stretch", hide_index=True)
        else:
            st.info("This run has no results yet.")

# ---------------------------------------------------------------------------
# Screen: Detailed Scorecards
# ---------------------------------------------------------------------------
with tab_scorecards:
    st.subheader("Detailed Scorecards")

    selected_run_id = st.session_state.get("selected_run_id")
    if not selected_run_id:
        st.info("Select a run in the Leaderboard tab first.")
    else:
        results = repository.get_run_results(selected_run_id)
        supplier_names = [r["supplier_name"] for r in results]
        if supplier_names:
            chosen = st.selectbox("Select supplier", supplier_names)
            supplier = next(r for r in results if r["supplier_name"] == chosen)["result_json"]

            c1, c2, c3 = st.columns(3)
            c1.metric("Absolute Score", supplier["absolute_score"])
            c2.metric("PPI", supplier["ppi"])
            c3.metric("Final Rank", supplier["final_rank"])

            st.caption(f"Tie-break reasoning: {supplier.get('tie_break_reason', 'n/a')}")
            st.markdown(f"**Overall summary:** {supplier.get('overall_summary', '')}")

            crit_df = pd.DataFrame(
                [
                    {
                        "Criterion": c["name"],
                        "Weight %": c["weight"],
                        "Score": c["score"],
                        "Max": c["max_score"],
                        "Benchmark": c["benchmark"],
                        "Gap": c["gap"],
                        "Relative %": c["relative_pct"],
                    }
                    for c in supplier["criteria"]
                ]
            )
            st.dataframe(crit_df, width="stretch", hide_index=True)

            with st.expander("Evidence & justification per criterion"):
                for c in supplier["criteria"]:
                    st.markdown(f"**{c['name']}** — score {c['score']}/{c['max_score']}")
                    st.write(f"*Justification:* {c['justification']}")
                    if c.get("evidence"):
                        st.write(f"*Evidence:* {c['evidence']}")
                    st.markdown("---")

            if supplier.get("risks"):
                with st.expander("Identified risks"):
                    for risk in supplier["risks"]:
                        st.write(f"- {risk}")
        else:
            st.info("No suppliers found for this run.")

# ---------------------------------------------------------------------------
# Screen: Run Details
# ---------------------------------------------------------------------------
with tab_run:
    st.subheader("Run Details")

    selected_run_id = st.session_state.get("selected_run_id")
    if not selected_run_id:
        st.info("Select a run in the Leaderboard tab first.")
    else:
        st.code(selected_run_id, language=None)
        results = repository.get_run_results(selected_run_id)

        all_warnings = []
        for r in results:
            supplier_json = r["result_json"]
            for w in supplier_json.get("warnings", []):
                all_warnings.append(f"**{r['supplier_name']}**: {w}")

        st.markdown("**Validation / warnings log**")
        if all_warnings:
            for w in all_warnings:
                st.warning(w)
        else:
            st.success("No validation warnings for this run.")

        st.markdown("**Tie-break explanation per supplier**")
        for r in sorted(results, key=lambda x: x["final_rank"]):
            st.write(f"#{r['final_rank']} {r['supplier_name']}: {r['result_json'].get('tie_break_reason', 'n/a')}")

        full_export = {"rfp_run_id": selected_run_id, "suppliers": [r["result_json"] for r in results]}
        st.download_button(
            "⬇️ Download complete run as JSON",
            data=json.dumps(full_export, indent=2),
            file_name=f"rfp_run_{selected_run_id}.json",
            mime="application/json",
        )
