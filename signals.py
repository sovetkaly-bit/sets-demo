from __future__ import annotations
import sqlite3, uuid
from datetime import datetime
from evidence_registry import evidence_category, validate_provenance, validate_signal_relation
from red_flags import classify

RULE_VERSION = 'signals-v8'

def record_signal(conn: sqlite3.Connection, signal_type: str, source_table: str,
                  source_id: str, baseline_value: float, observed_value: float,
                  deviation_score: float, impact_dimension: str,
                  persistence_count: int = 1, trend_direction: str | None = None,
                  worsening: bool = False) -> str:
    signal_id = f'SIG-{uuid.uuid4().hex[:10]}'
    conn.execute('''INSERT INTO signals
      (signal_id,signal_type,source_table,source_id,detected_date,baseline_value,
       observed_value,deviation_score,persistence_count,corroborating_source_types_count,
       impact_dimension,status,trend_direction,worsening,detected_by_rule_version)
      VALUES (?,?,?,?,?,?,?,?,?,0,?,'NONE',?,?,?)''',
      (signal_id,signal_type,source_table,source_id,datetime.now().isoformat(),
       baseline_value,observed_value,deviation_score,persistence_count,impact_dimension,
       trend_direction,int(worsening),RULE_VERSION))
    conn.commit()
    return signal_id

def add_signal_evidence(conn: sqlite3.Connection, signal_id: str, evidence_type: str,
                        source_ref: str, relation: str, provenance: str) -> str:
    category = evidence_category(evidence_type)
    validate_signal_relation(relation)
    validate_provenance(provenance)
    eid = f'SEV-{uuid.uuid4().hex[:10]}'
    conn.execute('''INSERT INTO signal_evidence
      (signal_evidence_id,signal_id,evidence_type,source_type,source_ref,relation,provenance,recorded_at)
      VALUES (?,?,?,?,?,?,?,?)''',
      (eid,signal_id,evidence_type,category,source_ref,relation,provenance,datetime.now().isoformat()))
    conn.commit()
    return eid

def corroborating_source_categories_for_signal(conn: sqlite3.Connection, signal_id: str) -> set[str]:
    rows = conn.execute("SELECT DISTINCT source_type FROM signal_evidence WHERE signal_id=? AND relation='corroborates'",(signal_id,)).fetchall()
    return {r['source_type'] for r in rows}

def refresh_signal_state(conn: sqlite3.Connection, signal_id: str,
                         owner_priority_set: set[str] | None = None,
                         hard_gate_triggered: bool = False) -> str:
    row = conn.execute('SELECT * FROM signals WHERE signal_id=?',(signal_id,)).fetchone()
    if row is None: raise ValueError(f'signal {signal_id} not found')
    cats = corroborating_source_categories_for_signal(conn,signal_id)
    status = classify(row['deviation_score'],row['persistence_count'],len(cats),
                      row['impact_dimension'],owner_priority_set,hard_gate_triggered,
                      row['signal_type'],bool(row['worsening']))
    conn.execute('UPDATE signals SET corroborating_source_types_count=?,status=? WHERE signal_id=?',(len(cats),status,signal_id))
    conn.commit()
    return status
