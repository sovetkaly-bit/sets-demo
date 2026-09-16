from __future__ import annotations
import sqlite3, uuid
from datetime import datetime
from evidence_registry import validate_provenance
from signals import record_signal, add_signal_evidence, refresh_signal_state


def record_shift_observation(conn: sqlite3.Connection, employee_id: str, shift_date: str,
                             role: str, shift_hours: float, overtime_minutes: int,
                             guest_contacts: int, checkins: int, service_requests: int,
                             staff_on_shift: int, expected_staff: int,
                             complaint_count: int, praise_count: int,
                             avg_queue_minutes: float, self_reported_load: float,
                             provenance: str='Observed') -> str:
    validate_provenance(provenance)
    oid=f'ESH-{uuid.uuid4().hex[:10]}'
    conn.execute('''INSERT INTO employee_shift_observations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                 (oid,employee_id,shift_date,role,shift_hours,overtime_minutes,guest_contacts,checkins,
                  service_requests,staff_on_shift,expected_staff,complaint_count,praise_count,avg_queue_minutes,
                  self_reported_load,provenance,datetime.now().isoformat()))
    conn.commit(); return oid


def derive_shift_pressure_score(row) -> float:
    staffing_gap=max(0,(row['expected_staff'] or 0)-(row['staff_on_shift'] or 0))
    queue=(row['avg_queue_minutes'] or 0)/10.0
    overtime=(row['overtime_minutes'] or 0)/60.0
    load=(row['self_reported_load'] or 0)/5.0
    # Demo heuristic only; not a validated employee-health or HR scale.
    return staffing_gap+queue+overtime+load


def build_employee_pressure_signal(conn: sqlite3.Connection, employee_id: str,
                                   owner_priority_set: set[str] | None=None) -> str | None:
    rows=conn.execute('SELECT * FROM employee_shift_observations WHERE employee_id=? ORDER BY shift_date',(employee_id,)).fetchall()
    if len(rows)<2: return None
    scores=[derive_shift_pressure_score(r) for r in rows]
    baseline=sum(scores[:-1])/len(scores[:-1]); observed=scores[-1]
    deviation=0 if baseline==0 else (observed-baseline)/baseline
    if abs(deviation)<0.30: return None
    sid=record_signal(conn,'employee','employee_shift_observations',rows[-1]['observation_id'],baseline,observed,deviation,'staff_load',1,'up' if deviation>0 else 'down')
    add_signal_evidence(conn,sid,'shift_workload_data',rows[-1]['observation_id'],'corroborates',rows[-1]['provenance'])
    if rows[-1]['staff_on_shift']<rows[-1]['expected_staff']:
        add_signal_evidence(conn,sid,'shift_staffing_data',rows[-1]['observation_id'],'corroborates',rows[-1]['provenance'])
    refresh_signal_state(conn,sid,owner_priority_set)
    return sid
