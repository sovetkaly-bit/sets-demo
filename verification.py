from __future__ import annotations
import sqlite3, json
from dataclasses import dataclass
from datetime import datetime

ALLOWED_TRANSITIONS = {
    'Proposed': {'Owner_selected'},
    'Owner_selected': {'Observe','Verify','Test','Superseded','Stopped'},
    'Observe': {'Verify','Test','Reassess','Superseded','Stopped'},
    'Verify': {'Test','Observe','Superseded','Stopped'},
    'Test': {'Pilot_validated','Pilot_failed','Reassess','Superseded','Stopped'},
    'Pilot_validated': {'Implement','Superseded','Stopped'},
    'Pilot_failed': {'Reassess','Superseded','Stopped'},
    'Implement': {'Monitor'},
    'Monitor': {'Reassess'},
    'Reassess': {'Observe','Verify','Test','Superseded','Stopped'},
}
REQUIRES_OWNER_SELECTION = {'Verify','Test','Pilot_validated','Pilot_failed','Implement'}
FAST_TRACK_TRANSITION=('Owner_selected','Implement')
FAST_TRACK_ELIGIBLE_ACTION_FAMILIES={'welcome_amenity_gesture','courtesy_late_checkout','no_action'}
VALID_PILOT_OUTCOMES={'validated','failed','inconclusive'}
RISK_TIERS={('low','high'):(0.30,False),('low','medium'):(0.40,False),('medium','high'):(0.45,False),('medium','medium'):(0.55,True),('medium','low'):(0.65,True),('high','medium'):(0.70,True),('high','low'):(0.80,True)}
DEFAULT_TIER=(0.60,True)

class InvalidTransitionError(ValueError): pass
class AutomationBiasGuardError(ValueError): pass
class IntegrityError(ValueError): pass

@dataclass(frozen=True)
class TransitionResult:
    hypothesis_id:str; action_id:str; from_status:str; requested_status:str; pathway:str
    required_confidence:float|None; actual_confidence:float|None; reason:str

def required_threshold(cost_of_error,reversibility):
    return RISK_TIERS.get((cost_of_error,reversibility),DEFAULT_TIER)

def _load_action(conn,hypothesis_id,action_id):
    r=conn.execute('''SELECT hypothesis_id,reversibility,cost_of_test,action_family,lifecycle_status,is_owner_selected
    FROM actions WHERE action_id=?''',(action_id,)).fetchone()
    if r is None: raise IntegrityError(f'action {action_id} not found')
    if r['hypothesis_id']!=hypothesis_id: raise IntegrityError('action does not belong to hypothesis')
    return r

def _evaluate(conn,hypothesis_id,action_id,requested_status,cost_of_error,is_compliance_risk,sample_too_small):
    a=_load_action(conn,hypothesis_id,action_id); current=a['lifecycle_status']; pathway='default_pathway'
    low_risk=(a['action_family'] in FAST_TRACK_ELIGIBLE_ACTION_FAMILIES and a['reversibility']=='high' and a['cost_of_test']=='low')
    if is_compliance_risk: pathway='hard_block'
    elif sample_too_small: pathway='capped_at_observe'
    elif cost_of_error=='low' and low_risk: pathway='fast_track_to_implement'
    def result(ok,reason,req=None,actual=None): return {'allowed':ok,'reason':reason,'from_status':current,'pathway':pathway,'required_confidence':req,'actual_confidence':actual}
    if requested_status in REQUIRES_OWNER_SELECTION and not a['is_owner_selected']: return result(False,'owner selection required')
    if pathway=='hard_block': return result(False,'hard block: external safety/legal/compliance verification required')
    if pathway=='capped_at_observe':
        if requested_status=='Observe' and requested_status in ALLOWED_TRANSITIONS.get(current,set()): return result(True,'sample too small: capped at Observe')
        return result(False,'sample too small to move beyond Observe')
    if pathway=='fast_track_to_implement' and (current,requested_status)==FAST_TRACK_TRANSITION: return result(True,'eligible low-risk factual fast-track')
    if requested_status not in ALLOWED_TRANSITIONS.get(current,set()): return result(False,f'{current}->{requested_status} not allowed')
    if requested_status=='Test':
        threshold,verify_required=required_threshold(cost_of_error,a['reversibility'])
        h=conn.execute('SELECT cause_confidence FROM hypotheses WHERE hypothesis_id=?',(hypothesis_id,)).fetchone(); actual=h['cause_confidence']
        if actual<threshold: return result(False,'cause confidence below adaptive threshold',threshold,actual)
        if verify_required and current=='Owner_selected': return result(False,'Verify required before Test',threshold,actual)
        return result(True,'threshold met',threshold,actual)
    if current=='Test' and requested_status in {'Pilot_validated','Pilot_failed','Reassess'}:
        r=conn.execute('SELECT outcome_status FROM decision_memory WHERE action_id=?',(action_id,)).fetchone(); outcome=r['outcome_status'] if r else None
        required={'Pilot_validated':'validated','Pilot_failed':'failed','Reassess':'inconclusive'}[requested_status]
        if outcome!=required: return result(False,f'{requested_status} requires outcome_status={required!r}')
    return result(True,'ok')

def request_transition(conn,hypothesis_id,action_id,requested_status,confirmed_by,cost_of_error='medium',is_compliance_risk=False,sample_too_small=False,rejected_alternatives=None,note=None):
    if confirmed_by.strip().lower()=='system': raise AutomationBiasGuardError('system cannot confirm a human transition')
    d=_evaluate(conn,hypothesis_id,action_id,requested_status,cost_of_error,is_compliance_risk,sample_too_small)
    if not d['allowed']: raise InvalidTransitionError(d['reason'])
    now=datetime.now().isoformat(); conn.execute('UPDATE actions SET lifecycle_status=?,last_status_at=? WHERE action_id=?',(requested_status,now,action_id))
    mem=conn.execute('SELECT memory_id,status_history FROM decision_memory WHERE action_id=?',(action_id,)).fetchone()
    entry={'status':requested_status,'timestamp':now,'confirmed_by':confirmed_by,'pathway':d['pathway'],'reason':d['reason']}
    if note: entry['note']=note
    if mem is None:
        conn.execute('''INSERT INTO decision_memory
        (memory_id,hypothesis_id,action_id,status_history,rejected_alternatives,actual_outcome,outcome_status,outcome_recorded_at,reassess_refs)
        VALUES (?,?,?,?,?,?,?,?,?)''',(f'MEM-{action_id}',hypothesis_id,action_id,json.dumps([entry]),json.dumps(rejected_alternatives or []),None,None,None,json.dumps([])))
    else:
        hist=json.loads(mem['status_history']); hist.append(entry); conn.execute('UPDATE decision_memory SET status_history=? WHERE memory_id=?',(json.dumps(hist),mem['memory_id']))
    conn.commit(); return TransitionResult(hypothesis_id,action_id,d['from_status'],requested_status,d['pathway'],d['required_confidence'],d['actual_confidence'],d['reason'])

def stop_action(conn,hypothesis_id,action_id,confirmed_by,reason):
    if not reason.strip(): raise ValueError('reason required')
    return request_transition(conn,hypothesis_id,action_id,'Stopped',confirmed_by,note=reason)

def record_pilot_outcome(conn,action_id,outcome_status,actual_outcome_text):
    if outcome_status not in VALID_PILOT_OUTCOMES: raise ValueError('invalid outcome_status')
    a=conn.execute('SELECT lifecycle_status,is_owner_selected FROM actions WHERE action_id=?',(action_id,)).fetchone()
    if a is None: raise ValueError('action not found')
    if a['lifecycle_status']!='Test': raise InvalidTransitionError('pilot outcome can only be recorded in Test')
    if not a['is_owner_selected']: raise InvalidTransitionError('pilot outcome requires owner-selected action')
    cur=conn.execute('UPDATE decision_memory SET actual_outcome=?,outcome_status=?,outcome_recorded_at=? WHERE action_id=?',(actual_outcome_text,outcome_status,datetime.now().isoformat(),action_id))
    if cur.rowcount==0: raise ValueError('decision_memory missing')
    conn.commit()
