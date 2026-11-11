"""Headless Streamlit UI checks (streamlit.testing.v1.AppTest). Run: python tests_ui.py
The app is copied to a temporary directory so the checks never touch a real setds_app.db."""
import shutil, sqlite3, sys, tempfile
from pathlib import Path
from streamlit.testing.v1 import AppTest

HERE = Path(__file__).resolve().parent
FILES = [p.name for p in HERE.glob('*.py') if p.name not in {'tests.py', 'tests_ui.py'}]


def make_app(nights, flags_last=None):
    tmp = Path(tempfile.mkdtemp())
    for f in FILES: shutil.copy(HERE / f, tmp / f)
    at = AppTest.from_file(str(tmp / 'app.py'), default_timeout=30); at.run()       # creates the DB schema
    db = sqlite3.connect(tmp / 'setds_app.db'); now = '2030-01-01T00:00:00'
    db.execute("INSERT INTO users(email,password_hash,organization,role,created_at) VALUES ('t@t','x','Org','owner',?)", (now,))
    db.execute("INSERT INTO guests(owner_user_id,guest_code,guest_name,notes,created_at) VALUES (1,'G-104','Test','',?)", (now,))
    for i, n in enumerate(nights):
        f = flags_last if (i == len(nights) - 1 and flags_last) else {}
        db.execute('''INSERT INTO visits(owner_user_id,guest_id,visit_date,nights,rating,spa_used,room_problem,spa_problem,
            service_problem,staff_problem,price_problem,competitor_problem,free_text,created_at) VALUES (1,1,?,?,7,0,?,?,?,?,?,?,?,?)''',
            (f'{2028 + i}-07-10', n, f.get('room', 0), f.get('spa', 0), 0, 0, 0, 0, '', now))
    db.commit(); db.close()
    at.session_state['user'] = {'user_id': 1, 'email': 't@t', 'organization': 'Org', 'role': 'owner'}
    at.run(); at.radio[0].set_value('Анализ'); at.run()
    return at


def metric(at, label):
    return next(m.value for m in at.metric if m.label.startswith(label))


def click(at, key):
    at.button(key=key).click(); at.run()
    assert not at.exception, [e.value for e in at.exception]


def errors(at): return ' | '.join(e.value for e in at.error)


def path_a(owner_priority):
    at = make_app([6, 3, 2], {'spa': 1})
    assert not at.exception, [e.value for e in at.exception]
    if owner_priority:
        at.checkbox(key='opt_owner_priority').set_value(True); at.run()
    assert metric(at, 'Сила сигнала') == 'Предупреждение (WARNING)', metric(at, 'Сила сигнала')
    assert metric(at, 'P:') == '2' and metric(at, 'S:') == '1', (metric(at, 'P:'), metric(at, 'S:'))
    assert metric(at, 'Последнее') == '-56%', metric(at, 'Последнее')
    # a second independent source confirming the shortened stay raises S -> RED_FLAG (P>=2, S>=2, D<=-30%)
    at.multiselect(key='opt_signal_sources').set_value(['operational_data_confirms']); at.run()
    assert metric(at, 'S:') == '2' and metric(at, 'Сила сигнала') == 'Красный флаг (RED_FLAG)'
    at.multiselect(key='opt_signal_sources').set_value([]); at.run()
    assert metric(at, 'Сила сигнала') == 'Предупреждение (WARNING)'
    print(f'PATH A (owner_priority={owner_priority}): WARNING, P=2, S=1, D=-56% -> OK')


def path_b():
    at = make_app([6, 3, 2], {'spa': 1})
    at.selectbox(key='adm_family').set_value('spa_priority_booking'); at.run()
    # implementation is blocked before anything is done, and the screen says why
    click(at, 'adm_implement'); msg = errors(at); print('  blocked #1:', msg)
    assert 'Отказ' in msg and 'owner selection' in msg, msg
    click(at, 'adm_select'); click(at, 'adm_test')
    click(at, 'adm_implement'); msg = errors(at); print('  blocked #2:', msg)
    assert 'Отказ' in msg and 'Implement' in msg, msg
    at.selectbox(key='adm_pilot_choice').set_value('validated'); at.run()
    click(at, 'adm_pilot'); click(at, 'adm_pilot_status')
    click(at, 'adm_implement'); msg = errors(at); print('  blocked #3 (pilot VALIDATED, Gate not recorded):', msg)
    assert 'Critical Gate is not PASS (not recorded)' in msg, msg
    assert any('Внедрение пока заблокировано' in w.value and 'Critical Gate' in w.value for w in at.warning)
    at.radio(key='adm_gate_choice').set_value('PASS'); at.text_input(key='adm_gate_basis').set_value('юридическая и бренд-проверка пройдены'); at.run()
    click(at, 'adm_gate'); click(at, 'adm_implement')
    assert not at.error, errors(at)
    assert any('Внедрение разрешено' in s.value for s in at.success), [s.value for s in at.success]
    print('PATH B: blocked x3 with reasons, then Gate=PASS + VALIDATED pilot -> Implement allowed -> OK')


def path_b_no_action_and_fasttrack():
    at = make_app([6, 3, 2], {'spa': 1})
    for fam in ('courtesy_late_checkout', 'no_action'):
        at.selectbox(key='adm_family').set_value(fam); at.run()
        click(at, 'adm_select')
        at.radio(key='adm_gate_choice').set_value('PASS'); at.text_input(key='adm_gate_basis').set_value('ok'); at.run()
        click(at, 'adm_gate'); click(at, 'adm_implement')
        assert 'Отказ' in errors(at), (fam, errors(at))
        print(f'  {fam}: Implement refused even with Gate=PASS ->', errors(at)[:110])
    print('PATH B2: fast-track action and no_action refused -> OK')


if __name__ == '__main__':
    path_a(False); path_a(True); path_b(); path_b_no_action_and_fasttrack()
    print('ALL UI CHECKS PASSED')
