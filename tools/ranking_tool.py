"""
Ranking Tool
Pure, deterministic Python. Given validated per-supplier scorecards it:
  1. Computes each supplier's absolute weighted score.
  2. Benchmarks every criterion across suppliers (best score wins).
  3. Computes criterion gap and relative performance % per supplier.
  4. Computes the weighted Peer Performance Index (PPI).
  5. Ranks suppliers with the mandatory stable tie-break order.

The LLM never touches any of this arithmetic.
"""
from datetime import datetime


def compute_absolute_scores(validated_suppliers: list[dict]) -> None:
    """Mutates each supplier dict in-place, adding 'absolute_score' (0-100 scale)."""
    for supplier in validated_suppliers:
        total = 0.0
        for c in supplier["criteria"]:
            if c["max_score"] > 0:
                total += (c["score"] / c["max_score"]) * c["weight"]
        supplier["absolute_score"] = round(total, 2)


def compute_benchmarks_and_ppi(validated_suppliers: list[dict]) -> None:
    """
    Mutates each supplier's criteria in-place to add 'benchmark', 'gap',
    and 'relative_pct', and adds a top-level 'ppi' to each supplier.
    """
    if not validated_suppliers:
        return

    criterion_ids = [c["criterion_id"] for c in validated_suppliers[0]["criteria"]]

    # 1. Find the benchmark (highest valid score) per criterion across all suppliers.
    benchmarks: dict[int, float] = {}
    for cid in criterion_ids:
        best = 0.0
        for supplier in validated_suppliers:
            for c in supplier["criteria"]:
                if c["criterion_id"] == cid:
                    best = max(best, c["score"])
        benchmarks[cid] = best

    # 2. Apply gap / relative % per supplier per criterion, then weighted PPI.
    for supplier in validated_suppliers:
        ppi_total = 0.0
        for c in supplier["criteria"]:
            benchmark = benchmarks[c["criterion_id"]]
            c["benchmark"] = benchmark
            c["gap"] = round(c["score"] - benchmark, 2)

            if benchmark == 0:
                # Safe handling: no one scored above zero on this criterion.
                relative_pct = 100.0 if c["score"] == 0 else 100.0
            else:
                relative_pct = (c["score"] / benchmark) * 100.0
            c["relative_pct"] = round(relative_pct, 2)

            ppi_total += relative_pct * (c["weight"] / 100.0)

        supplier["ppi"] = round(ppi_total, 2)


def _parse_date(date_str: str):
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except (ValueError, TypeError):
            continue
    return datetime.max  # unparseable dates sort last


def rank_suppliers(validated_suppliers: list[dict]) -> list[dict]:
    """
    Applies the mandatory tie-break order and assigns sequential final_rank:
      1) Higher PPI first
      2) Earlier submission date
      3) Higher historical experience rating
      4) Supplier name ascending
    Returns a NEW list, sorted, with 'final_rank' and 'tie_break_reason' set.
    """
    def sort_key(supplier):
        return (
            -supplier["ppi"],
            _parse_date(supplier["submission_date"]),
            -supplier["experience_rating"],
            supplier["supplier_name"].lower(),
        )

    ranked = sorted(validated_suppliers, key=sort_key)

    for idx, supplier in enumerate(ranked, start=1):
        supplier["final_rank"] = idx

    # Explain ties for transparency
    for i, supplier in enumerate(ranked):
        if i == 0:
            supplier["tie_break_reason"] = "Highest PPI."
            continue
        prev = ranked[i - 1]
        if supplier["ppi"] == prev["ppi"]:
            if _parse_date(supplier["submission_date"]) == _parse_date(prev["submission_date"]):
                if supplier["experience_rating"] == prev["experience_rating"]:
                    supplier["tie_break_reason"] = "Tied on PPI, date, and experience; resolved alphabetically by name."
                else:
                    supplier["tie_break_reason"] = "Tied on PPI and date; resolved by higher experience rating."
            else:
                supplier["tie_break_reason"] = "Tied on PPI; resolved by earlier submission date."
        else:
            supplier["tie_break_reason"] = "Ranked by PPI."

    return ranked


def run_ranking_pipeline(validated_suppliers: list[dict]) -> list[dict]:
    """Full deterministic pipeline: absolute score -> benchmark/PPI -> rank."""
    compute_absolute_scores(validated_suppliers)
    compute_benchmarks_and_ppi(validated_suppliers)
    return rank_suppliers(validated_suppliers)
