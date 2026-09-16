from __future__ import annotations
import sqlite3
from pathlib import Path

DEFAULT_DB = Path(__file__).with_name('setds_demo.db')

SCHEMA = r'''
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS guests (
    guest_id TEXT PRIMARY KEY,
    first_seen_date TEXT,
    segment_tags TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS visits (
    visit_id TEXT PRIMARY KEY,
    guest_id TEXT NOT NULL REFERENCES guests(guest_id),
    start_date TEXT NOT NULL,
    end_date TEXT,
    length_of_stay_nights INTEGER,
    services TEXT,
    price_paid REAL,
    channel TEXT
);

CREATE TABLE IF NOT EXISTS feedback (
    feedback_id TEXT PRIMARY KEY,
    visit_id TEXT REFERENCES visits(visit_id),
    guest_id TEXT REFERENCES guests(guest_id),
    rating REAL,
    text TEXT,
    sentiment_score REAL,
    return_intention REAL,
    date TEXT
);

CREATE TABLE IF NOT EXISTS employees (
    employee_id TEXT PRIMARY KEY,
    role TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS employee_shift_observations (
    observation_id TEXT PRIMARY KEY,
    employee_id TEXT NOT NULL REFERENCES employees(employee_id),
    shift_date TEXT NOT NULL,
    role TEXT,
    shift_hours REAL,
    overtime_minutes INTEGER,
    guest_contacts INTEGER,
    checkins INTEGER,
    service_requests INTEGER,
    staff_on_shift INTEGER,
    expected_staff INTEGER,
    complaint_count INTEGER,
    praise_count INTEGER,
    avg_queue_minutes REAL,
    self_reported_load REAL,
    provenance TEXT NOT NULL,
    recorded_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS signals (
    signal_id TEXT PRIMARY KEY,
    signal_type TEXT NOT NULL,
    source_table TEXT,
    source_id TEXT,
    detected_date TEXT NOT NULL,
    baseline_value REAL,
    observed_value REAL,
    deviation_score REAL,
    persistence_count INTEGER NOT NULL DEFAULT 1,
    corroborating_source_types_count INTEGER NOT NULL DEFAULT 0,
    impact_dimension TEXT,
    status TEXT NOT NULL DEFAULT 'NONE',
    trend_direction TEXT,
    worsening INTEGER NOT NULL DEFAULT 0,
    detected_by_rule_version TEXT
);

CREATE TABLE IF NOT EXISTS signal_evidence (
    signal_evidence_id TEXT PRIMARY KEY,
    signal_id TEXT NOT NULL REFERENCES signals(signal_id),
    evidence_type TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_ref TEXT,
    relation TEXT NOT NULL,
    provenance TEXT NOT NULL,
    recorded_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS hypotheses (
    hypothesis_id TEXT PRIMARY KEY,
    signal_id TEXT NOT NULL REFERENCES signals(signal_id),
    description TEXT NOT NULL,
    cause_confidence REAL NOT NULL,
    evidence_tag TEXT NOT NULL DEFAULT 'Inferred',
    created_date TEXT NOT NULL,
    updated_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence_log (
    evidence_id TEXT PRIMARY KEY,
    hypothesis_id TEXT NOT NULL REFERENCES hypotheses(hypothesis_id),
    date TEXT NOT NULL,
    evidence_type TEXT NOT NULL,
    source_ref TEXT,
    provenance TEXT NOT NULL,
    effect TEXT NOT NULL,
    multiplier REAL NOT NULL,
    posterior_before REAL NOT NULL,
    posterior_after REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS actions (
    action_id TEXT PRIMARY KEY,
    hypothesis_id TEXT NOT NULL REFERENCES hypotheses(hypothesis_id),
    description TEXT NOT NULL,
    action_family TEXT NOT NULL,
    action_confidence REAL,
    outcome_vector TEXT NOT NULL,
    reversibility TEXT NOT NULL,
    cost_of_test TEXT NOT NULL,
    recommended_next_status TEXT,
    is_system_preferred INTEGER NOT NULL DEFAULT 0,
    is_owner_selected INTEGER NOT NULL DEFAULT 0,
    owner_rationale TEXT,
    pilot_success_rule TEXT,
    pilot_stop_rule TEXT,
    lifecycle_status TEXT NOT NULL DEFAULT 'Proposed',
    selected_at TEXT,
    last_status_at TEXT
);

CREATE TABLE IF NOT EXISTS decision_memory (
    memory_id TEXT PRIMARY KEY,
    hypothesis_id TEXT NOT NULL REFERENCES hypotheses(hypothesis_id),
    action_id TEXT NOT NULL REFERENCES actions(action_id),
    status_history TEXT NOT NULL,
    rejected_alternatives TEXT NOT NULL,
    actual_outcome TEXT,
    outcome_status TEXT,
    outcome_recorded_at TEXT,
    reassess_refs TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS competitors (
    competitor_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    location TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS competitor_observations (
    observation_id TEXT PRIMARY KEY,
    competitor_id TEXT NOT NULL REFERENCES competitors(competitor_id),
    observation_date TEXT NOT NULL,
    reference_price REAL,
    rating REAL,
    review_count INTEGER,
    key_services TEXT,
    family_score REAL,
    loyalty_offer TEXT,
    season_status TEXT,
    source_ref TEXT,
    provenance TEXT NOT NULL
);
'''

def get_connection(path: str | Path = DEFAULT_DB) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn

def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()

def reset_db(path: str | Path = DEFAULT_DB) -> sqlite3.Connection:
    p = Path(path)
    if p.exists(): p.unlink()
    conn = get_connection(p)
    init_schema(conn)
    return conn
