-- Agentic RFP Evaluation & Supplier Ranking
-- Minimum SQLite schema per project brief section 6

CREATE TABLE IF NOT EXISTS evaluation_criteria (
    criterion_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    description     TEXT NOT NULL,
    weight          REAL NOT NULL,        -- percentage, active weights must total 100
    max_score       INTEGER NOT NULL DEFAULT 10,
    is_active       INTEGER NOT NULL DEFAULT 1  -- 1 = active, 0 = inactive
);

CREATE TABLE IF NOT EXISTS rfp_runs (
    rfp_run_id      TEXT PRIMARY KEY,      -- UUID
    created_at      TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending'  -- pending / running / completed / failed
);

CREATE TABLE IF NOT EXISTS supplier_results (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    rfp_run_id          TEXT NOT NULL,
    supplier_name       TEXT NOT NULL,
    submission_date     TEXT NOT NULL,
    experience_rating   REAL NOT NULL,
    absolute_score      REAL,
    ppi                 REAL,
    final_rank          INTEGER,
    result_json         TEXT,           -- full per-supplier detail (criteria, evidence, warnings, etc.)
    FOREIGN KEY (rfp_run_id) REFERENCES rfp_runs (rfp_run_id)
);
