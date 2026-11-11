"""Service layer between the Streamlit UI (app.py) and the SETDS rule modules.

The UI never re-implements a rule. Every classification, evidence update and implementation decision made on
screen is computed by the same modules the tests cover: guest_longitudinal / signals / red_flags (Eq. 2),
hypotheses (Eq. 3 and the Section 6 episode rule) and verification (Eq. 7).
"""
from __future__ import annotations
import json, sqlite3
from database import init_schema
from guest_longitudinal import build_guest_los_signal
from signals import add_signal_evidence, refresh_signal_state, review_queue
from hypotheses import create_hypotheses, apply_evidence
from actions import create_action, record_owner_decision
from verification import (request_transition, record_pilot_outcome, set_critical_gate, implementation_blockers,
                          InvalidTransitionError, AutomationBiasGuardError, IntegrityError)

STATUS_LABEL = {
    'NONE': 'Заметного сигнала нет',
    'WATCH': 'Наблюдение (WATCH)',
    'WARNING': 'Предупреждение (WARNING)',
    'RED_FLAG': 'Красный флаг (RED_FLAG)',
    'CRITICAL': 'Критический (CRITICAL)',
}

# Hypotheses offered in the form, with the multiplier a guest-reported problem gives them (Eq. 3).
HYPOTHESES = {
    'H1': 'Проблема с номером или качеством сна',
    'H2': 'Перегруженность spa или неудобное время услуги',
    'H3': 'Проблема с обслуживанием или персоналом',
    'H4': 'Проблема с другой услугой',
    'H5': 'Ценовая чувствительность гостя',
    'H6': 'Более сильное предложение конкурента',
    'H7': 'Личные обстоятельства гостя',
}
FLAG_TO_HYPOTHESIS = {
    'room_problem': ('H1', 3.0, 'В последнем визите отмечена проблема с номером или комфортом.'),
    'spa_problem': ('H2', 3.0, 'Гость сообщил о проблеме со spa или временем услуги.'),
    'staff_problem': ('H3', 3.0, 'Есть жалобы на очередь, задержки или обслуживание.'),
    'service_problem': ('H4', 2.5, 'Есть проблема с дополнительной услугой.'),
    'price_problem': ('H5', 3.0, 'Есть признаки ценовой чувствительности.'),
    'competitor_problem': ('H6', 3.0, 'Есть признаки усиления предложения конкурента.'),
}
# Independent source types that can confirm the shortened stay itself (S in Eq. 2). PMS is always present.
SIGNAL_SOURCE_OPTIONS = {
    'operational_data_confirms': 'Оперативный журнал (брони, загрузка) подтверждает сокращение проживания',
    'employee_data_confirms': 'Данные смен персонала подтверждают сокращение проживания',
    'competitor_signal_aligned': 'Данные о конкуренте подтверждают сокращение проживания',
}
STAFF_LOG_MULTIPLIER = 2.0


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(':memory:', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    init_schema(conn)
    return conn


def analyze_visits(visits, owner_priority: bool = False, signal_sources=(), staff_log_confirms_spa: bool = False) -> dict | None:
    """Run the rule modules over one guest's visit history and return what the UI shows.

    visits: rows with visit_date, nights and the problem flags entered in the UI.
    owner_priority: the owner marks length of stay as a priority; it only affects review order.
    signal_sources: evidence types of additional independent sources confirming the shortened stay (raise S).
    staff_log_confirms_spa: a staff log is an independent episode supporting the spa hypothesis (Section 6).
    """
    if len(visits) < 2:
        return None
    conn = _connect()
    conn.execute('INSERT INTO guests VALUES (?,?,?,?)', ('G', visits[0]['visit_date'], '[]', ''))
    for i, v in enumerate(visits):
        conn.execute('INSERT INTO visits VALUES (?,?,?,?,?,?,?,?)',
                     (f'V{i}', 'G', v['visit_date'], v['visit_date'], float(v['nights']), '[]', None, None))
    conn.commit()
    prio = {'length_of_stay'} if owner_priority else set()
    sid = build_guest_los_signal(conn, 'G', prio)

    latest = visits[-1]
    nights = [float(v['nights']) for v in visits]
    base = sum(nights[:-1]) / (len(nights) - 1)
    latest_dev = 0 if base == 0 else (nights[-1] - base) / base

    result = {'conn': conn, 'signal_id': sid, 'latest_deviation': latest_dev, 'owner_priority': owner_priority}
    if sid is None:
        result.update(status='NONE', persistence=0, source_types=0, signal_level=STATUS_LABEL['NONE'],
                      negative_transitions=0, leading_hypothesis=None, leading_confidence=None,
                      reasons=[], ranking=[], recommendation='Собрать ещё один независимый источник данных перед изменением процесса.',
                      review_position=None)
        return result

    for et in signal_sources:
        if et not in SIGNAL_SOURCE_OPTIONS:
            raise ValueError(f'unsupported signal source {et!r}')
        add_signal_evidence(conn, sid, et, f'signal-source:{et}', 'corroborates', 'Observed')
    status = refresh_signal_state(conn, sid, prio)

    create_hypotheses(conn, sid, {k: (v, 1.0) for k, v in HYPOTHESES.items()})
    reasons, mult = [], {}
    for flag, (hid, m, text) in FLAG_TO_HYPOTHESIS.items():
        if latest[flag]:
            mult[hid] = m
            reasons.append(text)
    # All problems entered for the latest visit are one guest-reported record, hence one episode.
    if mult:
        apply_evidence(conn, sid, 'targeted_question_confirms', mult, f'visit-{len(visits) - 1}', 'Guest-reported',
                       episode_id=f'guest-visit-{len(visits) - 1}')
    if staff_log_confirms_spa:
        apply_evidence(conn, sid, 'operational_data_confirms', {'H2': STAFF_LOG_MULTIPLIER}, 'staff-log', 'Observed',
                       episode_id='staff-log')
        reasons.append('Журнал персонала независимо подтверждает проблему со spa.')
    if latest['free_text']:
        reasons.append('Комментарий: ' + latest['free_text'])

    rows = conn.execute('SELECT hypothesis_id,description,cause_confidence FROM hypotheses ORDER BY cause_confidence DESC, hypothesis_id').fetchall()
    ranking = [(r['description'], r['cause_confidence']) for r in rows]
    row = conn.execute('SELECT * FROM signals WHERE signal_id=?', (sid,)).fetchone()
    lead = rows[0]
    recommendation = ('Проверить небольшое и обратимое решение, не меняя весь процесс сразу.'
                      if lead['cause_confidence'] >= 0.30 and reasons
                      else 'Собрать ещё один независимый источник данных перед изменением процесса.')
    queue = [r['signal_id'] for r in review_queue(conn, prio)]
    result.update(status=status, persistence=row['persistence_count'], source_types=row['corroborating_source_types_count'],
                  signal_level=STATUS_LABEL[status], negative_transitions=row['persistence_count'],
                  leading_hypothesis=lead['description'], leading_hypothesis_id=lead['hypothesis_id'],
                  leading_confidence=lead['cause_confidence'], reasons=reasons, ranking=ranking,
                  recommendation=recommendation, review_position=queue.index(sid) + 1,
                  hypothesis_rows=[dict(r) for r in rows])
    return result


# ---------------------------------------------------------------------------------------------------------------
# Implementation admission (Eq. 7)
# ---------------------------------------------------------------------------------------------------------------
ACTION_OPTIONS = {
    'spa_priority_booking': ('Пилот: приоритетные слоты spa для повторных гостей', 'Test'),
    'courtesy_late_checkout': ('Жест: позднее выселение', 'Implement'),
    'no_action': ('Ничего не менять, продолжить наблюдение', 'Observe'),
}


def create_case_action(case: dict, action_family: str) -> str:
    desc, nxt = ACTION_OPTIONS[action_family]
    hid = case['leading_hypothesis_id']
    return create_action(case['conn'], hid, desc, action_family, {}, 'high', 'low', nxt)


def _attempt(fn, *args, **kwargs) -> tuple[bool, str]:
    try:
        fn(*args, **kwargs)
        return True, 'ok'
    except (InvalidTransitionError, AutomationBiasGuardError, IntegrityError, ValueError) as e:
        return False, str(e)


def select_action(case, action_id, rationale):
    return _attempt(record_owner_decision, case['conn'], action_id, rationale, 'owner')


def move(case, action_id, status):
    hid = case['conn'].execute('SELECT hypothesis_id FROM actions WHERE action_id=?', (action_id,)).fetchone()['hypothesis_id']
    return _attempt(request_transition, case['conn'], hid, action_id, status, 'owner', cost_of_error='low')


def pilot_outcome(case, action_id, outcome):
    return _attempt(record_pilot_outcome, case['conn'], action_id, outcome, 'pilot result entered by owner')


def critical_gate(case, action_id, gate, basis):
    return _attempt(set_critical_gate, case['conn'], action_id, gate, 'owner', basis)


def action_state(case, action_id) -> dict:
    conn = case['conn']
    a = conn.execute('SELECT description,action_family,lifecycle_status,critical_gate,critical_gate_basis FROM actions WHERE action_id=?', (action_id,)).fetchone()
    m = conn.execute('SELECT outcome_status FROM decision_memory WHERE action_id=?', (action_id,)).fetchone()
    return {'description': a['description'], 'family': a['action_family'], 'status': a['lifecycle_status'],
            'gate': a['critical_gate'], 'gate_basis': a['critical_gate_basis'],
            'pilot_outcome': m['outcome_status'] if m else None,
            'blockers': implementation_blockers(conn, action_id)}
