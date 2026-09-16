from __future__ import annotations
import sqlite3, uuid
from datetime import datetime
from evidence_registry import evidence_category, validate_effect, validate_provenance

CAUSAL_HYPOTHESIS_EVIDENCE_TAG = 'Inferred'

def create_hypotheses(conn: sqlite3.Connection, signal_id: str,
                      candidates: dict[str, tuple[str, float]]) -> None:
    total = sum(prior for _, prior in candidates.values())
    if total <= 0: raise ValueError('Priors must sum to a positive value')
    now = datetime.now().isoformat()
    for hid,(desc,prior) in candidates.items():
        conn.execute('''INSERT INTO hypotheses
        (hypothesis_id,signal_id,description,cause_confidence,evidence_tag,created_date,updated_date)
        VALUES (?,?,?,?,?,?,?)''',(hid,signal_id,desc,prior/total,CAUSAL_HYPOTHESIS_EVIDENCE_TAG,now,now))
    conn.commit()

def apply_evidence(conn: sqlite3.Connection, signal_id: str, evidence_type: str,
                   multiplier_by_hypothesis: dict[str,float], source_ref: str,
                   provenance: str, effect_by_hypothesis: dict[str,str] | None = None) -> dict[str,float]:
    evidence_category(evidence_type)
    validate_provenance(provenance)
    rows = conn.execute('SELECT hypothesis_id,cause_confidence FROM hypotheses WHERE signal_id=?',(signal_id,)).fetchall()
    if not rows: raise ValueError(f'No hypotheses for signal {signal_id}')
    current = {r['hypothesis_id']:r['cause_confidence'] for r in rows}
    unknown = set(multiplier_by_hypothesis)-set(current)
    if unknown: raise ValueError(f'Unknown hypotheses in evidence: {sorted(unknown)}')
    for m in multiplier_by_hypothesis.values():
        if m <= 0: raise ValueError('Evidence multipliers must be >0')
    unnorm = {h:p*multiplier_by_hypothesis.get(h,1.0) for h,p in current.items()}
    denom = sum(unnorm.values())
    posterior = {h:v/denom for h,v in unnorm.items()}
    now = datetime.now().isoformat()
    effect_by_hypothesis = effect_by_hypothesis or {}
    for h in current:
        mult = multiplier_by_hypothesis.get(h,1.0)
        effect = effect_by_hypothesis.get(h,'supports' if mult>1 else ('refutes' if mult<1 else 'neutral'))
        validate_effect(effect)
        conn.execute('''INSERT INTO evidence_log
        (evidence_id,hypothesis_id,date,evidence_type,source_ref,provenance,effect,multiplier,posterior_before,posterior_after)
        VALUES (?,?,?,?,?,?,?,?,?,?)''',
        (f'EVL-{uuid.uuid4().hex[:10]}',h,now,evidence_type,source_ref,provenance,effect,mult,current[h],posterior[h]))
        conn.execute('UPDATE hypotheses SET cause_confidence=?,updated_date=? WHERE hypothesis_id=?',(posterior[h],now,h))
    conn.commit()
    return posterior

def evidence_convergence(conn: sqlite3.Connection, hypothesis_id: str) -> dict:
    hyp = conn.execute('SELECT cause_confidence,evidence_tag FROM hypotheses WHERE hypothesis_id=?',(hypothesis_id,)).fetchone()
    if hyp is None: raise ValueError(f'Hypothesis {hypothesis_id} not found')
    rows = conn.execute('SELECT evidence_type,effect FROM evidence_log WHERE hypothesis_id=?',(hypothesis_id,)).fetchall()
    by = {'supports':set(),'refutes':set(),'neutral':set()}
    for r in rows: by[r['effect']].add(evidence_category(r['evidence_type']))
    return {
        'evidence_tag':hyp['evidence_tag'],
        'cause_confidence':hyp['cause_confidence'],
        'supporting_source_types':sorted(by['supports']),
        'refuting_source_types':sorted(by['refutes']),
        'neutral_source_types':sorted(by['neutral']),
        'supporting_source_types_count':len(by['supports'])
    }

def action_confidence_for(conn: sqlite3.Connection, action_family: str) -> float | None:
    row = conn.execute('''SELECT dm.outcome_status FROM decision_memory dm
    JOIN actions a ON dm.action_id=a.action_id
    WHERE a.action_family=? AND dm.outcome_status IS NOT NULL
    ORDER BY dm.outcome_recorded_at DESC LIMIT 1''',(action_family,)).fetchone()
    if row is None: return None
    return {'validated':0.7,'failed':0.2,'inconclusive':0.4}.get(row['outcome_status'])
