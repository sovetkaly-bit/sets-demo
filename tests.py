import tempfile
from pathlib import Path
from database import reset_db
from seed_demo import seed
from evidence_registry import evidence_category, UnknownEvidenceTypeError
from signals import record_signal, add_signal_evidence, corroborating_source_categories_for_signal, refresh_signal_state
from hypotheses import create_hypotheses, apply_evidence, evidence_convergence
from guest_longitudinal import calculate_visit_deviations, directional_persistence, latest_worsening
from competitor import relative_competitive_gap
from actions import record_owner_decision
from verification import (InvalidTransitionError, AutomationBiasGuardError, request_transition,
                          record_pilot_outcome, set_critical_gate, implementation_blockers)
from red_flags import classify
from signals import review_queue
from guest_longitudinal import negative_persistence
from actions import create_action, generate_guest_capacity_alternatives


def assert_raises(exc, fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except exc:
        return
    raise AssertionError(f'Expected {exc.__name__}')


def fresh():
    return reset_db(Path(tempfile.mkdtemp())/'t.db')


def _scenario_a(conn, owner_priority=None):
    """Scenario A: stays 6 -> 3 -> 2 nights, PMS is the only confirming source type (S=1)."""
    from guest_longitudinal import build_guest_los_signal
    conn.execute('INSERT INTO guests VALUES (?,?,?,?)',('GA','2028-06-01','[]','t'))
    for i,(n,y) in enumerate([(6,2028),(3,2029),(2,2030)]):
        conn.execute('INSERT INTO visits VALUES (?,?,?,?,?,?,?,?)',(f'VA{i}','GA',f'{y}-07-10',f'{y}-07-1{n}',n,'[]',1000,'direct'))
    conn.commit()
    return build_guest_los_signal(conn,'GA',owner_priority or set())

def test_eq2():
    # D = -50.0% and -55.6% -> P=2; delta=30%
    assert negative_persistence(calculate_visit_deviations([6,3,2]))==2
    # non-consecutive drops do not accumulate
    assert negative_persistence(calculate_visit_deviations([6,3,8,2]))==1
    # direct classifier checks
    assert classify(-0.556,2,1,'length_of_stay',None,False,'guest')=='WARNING'
    assert classify(-0.556,2,1,'length_of_stay',{'length_of_stay'},False,'guest')=='WARNING'
    assert classify(-0.556,1,1,'length_of_stay',{'length_of_stay'},False,'guest')=='WATCH'
    assert classify(-0.556,2,2,'length_of_stay',None,False,'guest')=='RED_FLAG'
    assert classify(-0.556,3,1,'length_of_stay',{'length_of_stay'},False,'guest')=='WARNING'   # P>=3 alone is not enough
    assert classify(-0.10,2,2,'length_of_stay',None,False,'guest')=='NONE'                      # below threshold
    assert classify(+0.60,2,2,'length_of_stay',None,False,'guest')=='NONE'                      # wrong direction for guest
    # Scenario A through the stored signal, with and without owner priority
    for prio in (set(),{'length_of_stay'}):
        conn=fresh(); sid=_scenario_a(conn,prio)
        row=conn.execute('SELECT * FROM signals WHERE signal_id=?',(sid,)).fetchone()
        assert row['persistence_count']==2 and row['corroborating_source_types_count']==1, dict(row)
        assert row['status'] in {'WATCH','WARNING'} and row['status']!='RED_FLAG', row['status']
        # complaint and staff log are hypothesis evidence: they must not raise S
        create_hypotheses(conn,sid,{'H1':('p',0.25),'H2':('c',0.25),'H3':('access',0.25),'H4':('comp',0.25)})
        apply_evidence(conn,sid,'targeted_question_confirms',{'H3':3.0},'C1','Guest-reported',episode_id='EP1')
        apply_evidence(conn,sid,'operational_data_confirms',{'H3':2.0},'L1','Observed',episode_id='EP2')
        assert refresh_signal_state(conn,sid,prio)!='RED_FLAG'
        assert conn.execute('SELECT corroborating_source_types_count FROM signals WHERE signal_id=?',(sid,)).fetchone()[0]==1
    # owner priority affects review order only
    conn=fresh(); a=record_signal(conn,'guest','visits','x',6,2,-0.6,'length_of_stay',2); b=record_signal(conn,'guest','visits','y',6,2,-0.6,'service_quality',2)
    refresh_signal_state(conn,a); refresh_signal_state(conn,b)
    assert [r['signal_id'] for r in review_queue(conn,{'service_quality'})][0]==b
    assert [r['signal_id'] for r in review_queue(conn,{'length_of_stay'})][0]==a
    assert conn.execute('SELECT status FROM signals WHERE signal_id=?',(a,)).fetchone()[0]==conn.execute('SELECT status FROM signals WHERE signal_id=?',(b,)).fetchone()[0]

def _h3(conn,sid): return conn.execute("SELECT cause_confidence FROM hypotheses WHERE hypothesis_id='H3'").fetchone()[0]

def test_section6_episodes():
    four={'H1':('p',0.25),'H2':('c',0.25),'H3':('access',0.25),'H4':('comp',0.25)}
    def setup():
        conn=fresh(); sid=record_signal(conn,'guest','visits','V',6,2,-0.6,'length_of_stay',2); create_hypotheses(conn,sid,four); return conn,sid
    # one record -> 0.50
    conn,sid=setup(); apply_evidence(conn,sid,'targeted_question_confirms',{'H3':3.0},'C1','Guest-reported',episode_id='EP1')
    assert abs(_h3(conn,sid)-0.5)<1e-9
    # two records of ONE episode (different record ids / evidence types) -> still 0.50
    conn,sid=setup()
    apply_evidence(conn,sid,'targeted_question_confirms',{'H3':3.0},'C1','Guest-reported',episode_id='EP1')
    apply_evidence(conn,sid,'operational_data_confirms',{'H3':2.0},'L1','Observed',episode_id='EP1')
    assert abs(_h3(conn,sid)-0.5)<1e-9, _h3(conn,sid)
    assert conn.execute("SELECT COUNT(*) FROM evidence_log WHERE hypothesis_id='H3' AND applied=1").fetchone()[0]==1
    assert conn.execute("SELECT COUNT(*) FROM evidence_log WHERE hypothesis_id='H3' AND applied=0").fetchone()[0]==1
    # identical record resubmitted (no episode id) -> unchanged
    conn,sid=setup()
    for _ in range(3): apply_evidence(conn,sid,'targeted_question_confirms',{'H3':3.0},'C1','Guest-reported')
    assert abs(_h3(conn,sid)-0.5)<1e-9
    # two independent episodes -> 0.6667, in either order
    for order in (('EP1','EP2'),('EP2','EP1')):
        conn,sid=setup(); mult={'EP1':('targeted_question_confirms',3.0,'C1','Guest-reported'),'EP2':('operational_data_confirms',2.0,'L1','Observed')}
        for ep in order:
            t,m,ref,prov=mult[ep]; apply_evidence(conn,sid,t,{'H3':m},ref,prov,episode_id=ep)
        assert abs(_h3(conn,sid)-2/3)<1e-9,_h3(conn,sid)
    # posteriors stay normalised
    assert abs(sum(r[0] for r in conn.execute('SELECT cause_confidence FROM hypotheses'))-1)<1e-9
    # evidence-convergence counts do not include suppressed repeats
    conn,sid=setup()
    apply_evidence(conn,sid,'targeted_question_confirms',{'H3':3.0},'C1','Guest-reported',episode_id='EP1')
    apply_evidence(conn,sid,'operational_data_confirms',{'H3':2.0},'L1','Observed',episode_id='EP1')
    assert evidence_convergence(conn,'H3')['supporting_source_types_count']==1

def _impl_action(gate, outcome, family='spa_priority_booking', fresh_conn=None):
    """Build an owner-selected action in Test with a recorded pilot outcome; gate/outcome may be None."""
    conn=fresh_conn or fresh(); sid=record_signal(conn,'guest','visits','V',6,2,-0.6,'length_of_stay',2)
    create_hypotheses(conn,sid,{'H3':('access',1.0)})
    aid=create_action(conn,'H3','x',family,{}, 'high','low','Test')
    record_owner_decision(conn,aid,'owner picks')
    conn.execute("UPDATE hypotheses SET cause_confidence=0.9"); conn.commit()
    request_transition(conn,'H3',aid,'Test','owner',cost_of_error='low')
    if outcome:
        record_pilot_outcome(conn,aid,outcome,'result')
        if outcome=='validated': request_transition(conn,'H3',aid,'Pilot_validated','owner')
    if gate: set_critical_gate(conn,aid,gate,'owner','reviewed legal/safety/brand')
    return conn,aid

def test_eq7():
    # Missing Gate is not PASS even with a validated pilot.
    conn,aid=_impl_action(None,'validated')
    assert_raises(InvalidTransitionError,request_transition,conn,'H3',aid,'Implement','owner')
    assert any('Critical Gate' in b for b in implementation_blockers(conn,aid))
    # All four PASS / not-PASS x VALIDATED / not-VALIDATED combinations.
    for gate in ('PASS','FAIL'):
        for outcome in ('validated','failed'):
            conn,aid=_impl_action(gate,outcome)
            expected=(gate=='PASS' and outcome=='validated')
            if expected:
                request_transition(conn,'H3',aid,'Implement','owner')
                assert conn.execute('SELECT lifecycle_status FROM actions WHERE action_id=?',(aid,)).fetchone()[0]=='Implement'
            else:
                assert_raises(InvalidTransitionError,request_transition,conn,'H3',aid,'Implement','owner')
                assert conn.execute('SELECT lifecycle_status FROM actions WHERE action_id=?',(aid,)).fetchone()[0]!='Implement'
    # Gate PASS but pilot not yet run (still in Test): blocked.
    conn,aid=_impl_action('PASS',None)
    assert_raises(InvalidTransitionError,request_transition,conn,'H3',aid,'Implement','owner')
    # Old fast-track closed: courtesy_late_checkout, low risk, Owner_selected -> Implement is blocked even with Gate PASS.
    conn=fresh(); sid=record_signal(conn,'guest','visits','V',6,2,-0.6,'length_of_stay',2); create_hypotheses(conn,sid,{'H3':('a',1.0)})
    aid=create_action(conn,'H3','late checkout','courtesy_late_checkout',{},'high','low','Implement'); record_owner_decision(conn,aid,'owner picks')
    set_critical_gate(conn,aid,'PASS','owner','ok')
    assert_raises(InvalidTransitionError,request_transition,conn,'H3',aid,'Implement','owner',cost_of_error='low')
    # no_action is an observation, never Implement (even with Gate PASS and validated outcome recorded).
    conn=fresh(); sid=record_signal(conn,'guest','visits','V',6,2,-0.6,'length_of_stay',2); create_hypotheses(conn,sid,{'H3':('a',1.0)})
    aid=create_action(conn,'H3','observe','no_action',{},'high','low','Observe'); record_owner_decision(conn,aid,'owner picks')
    set_critical_gate(conn,aid,'PASS','owner','ok')
    assert_raises(InvalidTransitionError,request_transition,conn,'H3',aid,'Implement','owner',cost_of_error='low')
    request_transition(conn,'H3',aid,'Observe','owner')
    # the generated alternatives mark no_action as Observe
    ids=generate_guest_capacity_alternatives(conn,'H3')
    assert conn.execute('SELECT recommended_next_status FROM actions WHERE action_id=?',(ids[0],)).fetchone()[0]=='Observe'
    # The Gate cannot be recorded by the system and PASS needs a basis.
    assert_raises(AutomationBiasGuardError,set_critical_gate,conn,ids[1],'PASS','system','x')
    assert_raises(ValueError,set_critical_gate,conn,ids[1],'PASS','owner','  ')
    # Hard compliance block still wins over everything.
    conn,aid=_impl_action('PASS','validated')
    assert_raises(InvalidTransitionError,request_transition,conn,'H3',aid,'Implement','owner',is_compliance_risk=True)

def test_old_db_migration():
    import sqlite3
    path=Path(tempfile.mkdtemp())/'old.db'
    c=sqlite3.connect(path); c.execute('CREATE TABLE evidence_log(evidence_id TEXT)'); c.execute('CREATE TABLE actions(action_id TEXT)'); c.commit(); c.close()
    from database import get_connection, init_schema
    conn=get_connection(path); init_schema(conn)
    cols={r[1] for r in conn.execute('PRAGMA table_info(actions)')}
    assert {'critical_gate','critical_gate_basis','critical_gate_by','critical_gate_at'}<=cols


def run():
    # E1/E6: unknown evidence type fails loudly.
    assert_raises(UnknownEvidenceTypeError, evidence_category, 'not_registered')

    # E2/E3: multiple evidence records/types in same category count once.
    conn=fresh()
    sid=record_signal(conn,'guest','visits','V1',6,3,-0.5,'length_of_stay')
    add_signal_evidence(conn,sid,'guest_los_change','V1','corroborates','Derived')
    add_signal_evidence(conn,sid,'guest_service_usage_change','V1','corroborates','Derived')
    assert corroborating_source_categories_for_signal(conn,sid)=={'guest_behavior'}

    # E4/E7 (changed rule, Eq. 2): a second source category corroborating the same signal raises S to 2, but a
    # RED_FLAG additionally needs P>=2 and a current negative threshold crossing. This signal has P=1, so it is
    # a WARNING (the old prototype returned RED_FLAG here because owner priority substituted for persistence).
    add_signal_evidence(conn,sid,'targeted_question_confirms','F1','corroborates','Guest-reported')
    assert len(corroborating_source_categories_for_signal(conn,sid))==2
    status=refresh_signal_state(conn,sid,{'length_of_stay'})
    assert status=='WARNING',status

    # E5: neutral evidence does not count as supporting convergence.
    create_hypotheses(conn,sid,{'H1':('a',0.5),'H2':('b',0.5)})
    apply_evidence(conn,sid,'targeted_question_confirms',{'H1':2.0},'F1','Guest-reported')
    assert evidence_convergence(conn,'H2')['supporting_source_types_count']==0
    assert evidence_convergence(conn,'H1')['supporting_source_types_count']==1

    # G4: 6->3->2 = two negative threshold-crossing deviations, not three.
    devs=calculate_visit_deviations([6,3,2])
    assert directional_persistence(devs)==2,devs
    assert latest_worsening(devs) is True

    # G3: alternating direction resets current streak.
    devs2=calculate_visit_deviations([6,3,8])
    assert directional_persistence(devs2)==1

    # Competitor RCG.
    rcg=relative_competitive_gap(0.2,[0.6,0.3,0.4])
    assert abs(rcg['gap']+0.2)<1e-9 and rcg['relative_erosion']

    # Full demo seed including Employee layer.
    p=Path(tempfile.mkdtemp())/'demo.db'
    conn2,sid2,actions,emp_sid=seed(p)
    assert emp_sid is not None
    assert conn2.execute('SELECT evidence_tag FROM hypotheses WHERE hypothesis_id=?',('H3',)).fetchone()[0]=='Inferred'

    # v7 terminal re-selection guard remains intact.
    pilot=actions[2]; other=actions[1]
    record_owner_decision(conn2,pilot,'reversible demo pilot')
    record_owner_decision(conn2,other,'prepare first')
    assert conn2.execute('SELECT lifecycle_status FROM actions WHERE action_id=?',(pilot,)).fetchone()[0]=='Superseded'
    assert_raises(InvalidTransitionError,record_owner_decision,conn2,pilot,'try to revive')

    test_eq2(); test_section6_episodes(); test_eq7(); test_old_db_migration()
    # Seeded demo is Scenario A: WATCH/WARNING (not RED_FLAG), H3 = 0.667 from two independent episodes.
    sig=conn2.execute("SELECT status,persistence_count,corroborating_source_types_count FROM signals WHERE signal_type='guest'").fetchone()
    assert sig['persistence_count']==2 and sig['corroborating_source_types_count']==1 and sig['status'] in {'WATCH','WARNING'}, dict(sig)
    assert abs(conn2.execute("SELECT cause_confidence FROM hypotheses WHERE hypothesis_id='H3'").fetchone()[0]-2/3)<1e-9

    print('ALL TESTS PASSED')

if __name__=='__main__':
    run()
