from __future__ import annotations
import sqlite3, json, uuid
from datetime import datetime
from hypotheses import action_confidence_for
from verification import request_transition, InvalidTransitionError

OUTCOME_DIMENSIONS=['guest_satisfaction','repeat_probability','length_of_stay','service_quality','staff_load','product_attractiveness','operational_readiness','competitive_position','season_extension_potential']
VALID_BASES={'Illustrative','Historical','Pilot-derived','Model-estimated'}

def make_outcome_vector(effects:dict)->dict:
    vector={}
    for dim in OUTCOME_DIMENSIONS:
        if dim not in effects:
            vector[dim]={'direction':None,'magnitude':None,'probability':None,'probability_basis':'Illustrative'}; continue
        e=dict(effects[dim]); basis=e.get('probability_basis','Illustrative')
        if basis not in VALID_BASES: raise ValueError(f'invalid probability_basis {basis}')
        p=e.get('probability')
        if p is not None and not (0<=p<=1): raise ValueError('probability must be in [0,1]')
        e['probability_basis']=basis; vector[dim]=e
    return vector

def create_action(conn,hypothesis_id,description,action_family,outcome_effects,reversibility,cost_of_test,recommended_next_status,pilot_success_rule=None,pilot_stop_rule=None,is_system_preferred=False):
    aid=f'ACT-{uuid.uuid4().hex[:10]}'; conf=action_confidence_for(conn,action_family)
    conn.execute('''INSERT INTO actions
    (action_id,hypothesis_id,description,action_family,action_confidence,outcome_vector,reversibility,cost_of_test,recommended_next_status,is_system_preferred,is_owner_selected,owner_rationale,pilot_success_rule,pilot_stop_rule,lifecycle_status,selected_at,last_status_at)
    VALUES (?,?,?,?,?,?,?,?,?,?,0,'',?,?, 'Proposed',NULL,NULL)''',
    (aid,hypothesis_id,description,action_family,conf,json.dumps(make_outcome_vector(outcome_effects)),reversibility,cost_of_test,recommended_next_status,int(is_system_preferred),pilot_success_rule,pilot_stop_rule))
    conn.commit(); return aid

def record_owner_decision(conn,action_id,owner_rationale,confirmed_by='owner'):
    if not owner_rationale.strip(): raise ValueError('owner_rationale required')
    row=conn.execute('SELECT hypothesis_id,lifecycle_status,description FROM actions WHERE action_id=?',(action_id,)).fetchone()
    if row is None: raise ValueError('action not found')
    if row['lifecycle_status'] in {'Superseded','Stopped'}: raise InvalidTransitionError('terminal action cannot be reselected; create a new action')
    hid=row['hypothesis_id']
    others=conn.execute('''SELECT action_id FROM actions WHERE hypothesis_id=? AND action_id<>? AND lifecycle_status IN
    ('Owner_selected','Observe','Verify','Test','Pilot_validated','Pilot_failed','Reassess')''',(hid,action_id)).fetchall()
    for o in others: request_transition(conn,hid,o['action_id'],'Superseded',confirmed_by,note=f"superseded by owner selection: {row['description']}")
    conn.execute('UPDATE actions SET is_owner_selected=0 WHERE hypothesis_id=?',(hid,)); now=datetime.now().isoformat()
    if row['lifecycle_status']=='Proposed': conn.execute("UPDATE actions SET is_owner_selected=1,owner_rationale=?,selected_at=?,lifecycle_status='Owner_selected',last_status_at=? WHERE action_id=?",(owner_rationale,now,now,action_id))
    else: conn.execute('UPDATE actions SET is_owner_selected=1,owner_rationale=?,selected_at=? WHERE action_id=?',(owner_rationale,now,action_id))
    conn.commit()

def generate_guest_capacity_alternatives(conn,hypothesis_id):
    return [
      create_action(conn,hypothesis_id,'Status quo / observe','no_action',{'repeat_probability':{'direction':'down','magnitude':'small','probability':0.4,'probability_basis':'Illustrative'}},'high','low','Monitor'),
      create_action(conn,hypothesis_id,'Prepare priority-booking process','spa_priority_prepare',{'operational_readiness':{'direction':'up','magnitude':'medium','probability':0.7,'probability_basis':'Illustrative'}},'high','low','Prepare'),
      create_action(conn,hypothesis_id,'Pilot priority spa slots for repeat guests','spa_priority_booking',{'guest_satisfaction':{'direction':'up','magnitude':'medium','probability':0.65,'probability_basis':'Illustrative'},'staff_load':{'direction':'up','magnitude':'small','probability':0.45,'probability_basis':'Illustrative'}},'high','low','Test',pilot_success_rule='>=60% offered slots used and no material queue deterioration',pilot_stop_rule='queue time or staff complaints worsen materially',is_system_preferred=True),
      create_action(conn,hypothesis_id,'Full priority-slot rollout','spa_priority_full',{'guest_satisfaction':{'direction':'up','magnitude':'medium','probability':0.65,'probability_basis':'Illustrative'},'staff_load':{'direction':'up','magnitude':'medium','probability':0.6,'probability_basis':'Illustrative'}},'medium','medium','Verify')
    ]
