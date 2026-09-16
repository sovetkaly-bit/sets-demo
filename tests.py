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
from verification import InvalidTransitionError


def assert_raises(exc, fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except exc:
        return
    raise AssertionError(f'Expected {exc.__name__}')


def fresh():
    return reset_db(Path(tempfile.mkdtemp())/'t.db')


def run():
    # E1/E6: unknown evidence type fails loudly.
    assert_raises(UnknownEvidenceTypeError, evidence_category, 'not_registered')

    # E2/E3: multiple evidence records/types in same category count once.
    conn=fresh()
    sid=record_signal(conn,'guest','visits','V1',6,3,-0.5,'length_of_stay')
    add_signal_evidence(conn,sid,'guest_los_change','V1','corroborates','Derived')
    add_signal_evidence(conn,sid,'guest_service_usage_change','V1','corroborates','Derived')
    assert corroborating_source_categories_for_signal(conn,sid)=={'guest_behavior'}

    # E4/E7: second category changes derived count and severity after refresh.
    add_signal_evidence(conn,sid,'targeted_question_confirms','F1','corroborates','Guest-reported')
    assert len(corroborating_source_categories_for_signal(conn,sid))==2
    status=refresh_signal_state(conn,sid,{'length_of_stay'})
    assert status=='RED_FLAG',status

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

    print('ALL TESTS PASSED')

if __name__=='__main__':
    run()
