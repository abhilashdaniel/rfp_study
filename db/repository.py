"""
Small data-access layer over the SQLite database. Keeps SQL out of the
Streamlit UI and orchestrator code.
"""
import json
import sqlite3
import uuid
from datetime import datetime, timezone

from db.init_db import DB_PATH, init_db


def get_connection():
    init_db()  # no-op if already initialized; ensures DB exists on first run
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_active_criteria() -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM evaluation_criteria WHERE is_active = 1 ORDER BY criterion_id"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_criteria() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM evaluation_criteria ORDER BY criterion_id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_run() -> str:
    run_id = str(uuid.uuid4())
    conn = get_connection()
    conn.execute(
        "INSERT INTO rfp_runs (rfp_run_id, created_at, status) VALUES (?, ?, ?)",
        (run_id, datetime.now(timezone.utc).isoformat(), "running"),
    )
    conn.commit()
    conn.close()
    return run_id


def update_run_status(run_id: str, status: str) -> None:
    conn = get_connection()
    conn.execute("UPDATE rfp_runs SET status = ? WHERE rfp_run_id = ?", (status, run_id))
    conn.commit()
    conn.close()


def save_supplier_result(run_id: str, supplier: dict) -> None:
    conn = get_connection()
    conn.execute(
        """INSERT INTO supplier_results
           (rfp_run_id, supplier_name, submission_date, experience_rating,
            absolute_score, ppi, final_rank, result_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            run_id,
            supplier["supplier_name"],
            supplier["submission_date"],
            supplier["experience_rating"],
            supplier["absolute_score"],
            supplier["ppi"],
            supplier["final_rank"],
            json.dumps(supplier),
        ),
    )
    conn.commit()
    conn.close()


def get_run_results(run_id: str) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM supplier_results WHERE rfp_run_id = ? ORDER BY final_rank",
        (run_id,),
    ).fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        d["result_json"] = json.loads(d["result_json"])
        results.append(d)
    return results


def get_all_runs() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM rfp_runs ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]
