"""
Creates (or resets) the SQLite database and seeds it with the default
evaluation criteria described in the project brief (section 4).

Run directly:
    python db/init_db.py
    python db/init_db.py --reset      # drops and recreates all tables
"""
import argparse
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "rfp_evaluation.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")

DEFAULT_CRITERIA = [
    # name, description, weight, max_score, is_active
    ("Technical Capability", "Architecture, integrations, scalability, technical fit", 30, 10, 1),
    ("Implementation Plan", "Timeline, milestones, staffing, risk plan", 20, 10, 1),
    ("Commercial Value", "Pricing clarity, total cost, assumptions", 20, 10, 1),
    ("Security & Compliance", "Controls, certifications, privacy, auditability", 20, 10, 1),
    ("Support & Experience", "Support model, similar projects, references", 10, 10, 1),
]


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(reset: bool = False):
    conn = get_connection()
    cur = conn.cursor()

    if reset:
        cur.executescript(
            """
            DROP TABLE IF EXISTS supplier_results;
            DROP TABLE IF EXISTS rfp_runs;
            DROP TABLE IF EXISTS evaluation_criteria;
            """
        )

    with open(SCHEMA_PATH, "r") as f:
        cur.executescript(f.read())

    cur.execute("SELECT COUNT(*) AS c FROM evaluation_criteria")
    count = cur.fetchone()["c"]

    if count == 0:
        cur.executemany(
            """INSERT INTO evaluation_criteria (name, description, weight, max_score, is_active)
               VALUES (?, ?, ?, ?, ?)""",
            DEFAULT_CRITERIA,
        )
        print(f"Seeded {len(DEFAULT_CRITERIA)} default evaluation criteria.")
    else:
        print(f"evaluation_criteria already has {count} row(s); skipped seeding.")

    conn.commit()
    conn.close()
    print(f"Database ready at: {DB_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Drop and recreate all tables before seeding")
    args = parser.parse_args()
    init_db(reset=args.reset)
