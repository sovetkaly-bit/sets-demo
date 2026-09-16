from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from database import get_connection
from seed_demo import seed
from guest_longitudinal import (
    get_guest_visit_history,
    calculate_visit_deviations,
    service_usage_changes,
    revisit_intervals_days,
)
from hypotheses import evidence_convergence
from actions import record_owner_decision
from verification import (
    request_transition,
    record_pilot_outcome,
    stop_action,
)
from competitor import relative_competitive_gap
from scenario import build_bounded_scenarios

DB = Path(__file__).with_name("setds_demo.db")

st.set_page_config(
    page_title="SETDS — Tourism Decision Support",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSS = r"""
<style>
:root{
 --setds-ink:#182230;
 --setds-muted:#667085;
 --setds-line:#e6eaf0;
 --setds-blue:#2859d8;
 --setds-navy:#0f172a;
 --setds-bg:#f6f8fb;
}
[data-testid="stAppViewContainer"]{
 background:linear-gradient(180deg,#f8fafc 0%,#f4f7fb 100%);
}
[data-testid="stSidebar"]{
 background:linear-gradient(180deg,#111827 0%,#0b1220 100%);
}
[data-testid="stSidebar"] *{color:#eef2f7}
.block-container{padding-top:1.6rem;padding-bottom:3rem;max-width:1450px}
h1,h2,h3{letter-spacing:-.02em}
.setds-kicker{
 text-transform:uppercase;letter-spacing:.14em;font-size:.72rem;
 font-weight:800;color:#2859d8;margin-bottom:.3rem;
}
.setds-subtitle{color:#667085;font-size:.95rem;margin-top:-.35rem;margin-bottom:1rem}
.setds-card{
 background:white;border:1px solid #e6eaf0;border-radius:18px;padding:18px 19px;
 box-shadow:0 10px 28px rgba(16,24,40,.055);height:100%;
}
.setds-card h4{margin:0 0 .35rem 0;font-size:.82rem;color:#667085;font-weight:700}
.setds-metric{font-size:1.72rem;font-weight:850;color:#182230;line-height:1.1}
.setds-pill{display:inline-block;border-radius:999px;padding:4px 8px;font-size:.72rem;font-weight:800;margin-top:8px}
.red{background:#fee4e2;color:#b42318}.amber{background:#fef0c7;color:#b54708}
.green{background:#dcfae6;color:#067647}.blue{background:#dbeafe;color:#1d4ed8}
.purple{background:#ede9fe;color:#6d28d9}.gray{background:#f2f4f7;color:#475467}
.setds-callout{
 padding:13px 15px;border-radius:13px;background:#eef4ff;border-left:4px solid #2859d8;
 margin:.5rem 0 1rem 0;
}
.setds-warn{background:#fffaeb;border-left-color:#f79009}
.setds-danger{background:#fff1f3;border-left-color:#f04438}
.setds-success{background:#ecfdf3;border-left-color:#12b76a}
.small-note{font-size:.79rem;color:#667085}
div[data-testid="stMetric"]{
 background:white;border:1px solid #e6eaf0;border-radius:16px;padding:14px 16px;
 box-shadow:0 8px 20px rgba(16,24,40,.045);
}
div[data-testid="stDataFrame"]{border:1px solid #e6eaf0;border-radius:14px;overflow:hidden}
.stButton>button{
 border-radius:11px;font-weight:700;min-height:2.55rem;border:1px solid #d0d5dd;
}
.stButton>button[kind="primary"]{background:#2859d8;border-color:#2859d8}
hr{border-color:#eaecf0}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

def reset_demo():
    try:
        if DB.exists():
            DB.unlink()
    except Exception:
        pass
    seed(DB)
    for k in ["selected_action", "owner_rationale_ui"]:
        if k in st.session_state:
            del st.session_state[k]

if "booted" not in st.session_state:
    reset_demo()
    st.session_state.booted = True

conn = get_connection(DB)

def qdf(sql: str, params=None):
    return pd.read_sql_query(sql, conn, params=params or ())

def pill(text, cls="gray"):
    return f'<span class="setds-pill {cls}">{text}</span>'

def card(label, value, pill_text="", pill_cls="gray"):
    st.markdown(
        f"""<div class="setds-card">
        <h4>{label}</h4>
        <div class="setds-metric">{value}</div>
        {pill(pill_text,pill_cls) if pill_text else ""}
        </div>""",
        unsafe_allow_html=True,
    )

def page_header(kicker, title, subtitle):
    st.markdown(f'<div class="setds-kicker">{kicker}</div>', unsafe_allow_html=True)
    st.title(title)
    st.markdown(f'<div class="setds-subtitle">{subtitle}</div>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## ◈ SETDS")
    st.caption("Self-Evolving Tourism Decision System")
    st.markdown("---")
    page = st.radio(
        "Навигация",
        [
            "Обзор",
            "Гость: динамика",
            "Evidence & причины",
            "Персонал",
            "Конкуренты",
            "Решение & пилот",
            "Decision Memory",
            "Сценарии",
        ],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.caption("Демонстрационный режим")
    st.caption("Значения и вероятности в seed-кейсе иллюстративные, а не эмпирические оценки Altair.")
    if st.button("↻ Сбросить demo", use_container_width=True):
        reset_demo()
        st.success("Demo восстановлено.")
        st.rerun()

# ---- Overview
if page == "Обзор":
    page_header(
        "Interactive research prototype",
        "SETDS — обзор предприятия",
        "Наблюдаемый сигнал → конкурирующие причины → альтернативы → выбор владельца → проверка → память результата.",
    )
    sigs = qdf(
        """SELECT signal_type, impact_dimension, deviation_score, persistence_count,
                  corroborating_source_types_count, status, worsening
           FROM signals ORDER BY detected_date"""
    )
    h3 = conn.execute(
        "SELECT cause_confidence FROM hypotheses WHERE hypothesis_id='H3'"
    ).fetchone()
    selected = conn.execute(
        """SELECT description,lifecycle_status FROM actions
           WHERE is_owner_selected=1 ORDER BY selected_at DESC LIMIT 1"""
    ).fetchone()

    cols = st.columns(4)
    with cols[0]:
        guest = sigs[sigs["signal_type"] == "guest"]
        status = guest.iloc[0]["status"] if len(guest) else "NONE"
        card("Главный сигнал", status, "Guest LOS", "red" if status == "RED_FLAG" else "amber")
    with cols[1]:
        val = f"{(h3['cause_confidence']*100):.1f}%" if h3 else "—"
        card("Ведущая гипотеза H3", val, "Inferred", "purple")
    with cols[2]:
        emp = sigs[sigs["signal_type"] == "employee"]
        est = emp.iloc[0]["status"] if len(emp) else "NONE"
        card("Контекст персонала", est, "Peak-load context", "amber")
    with cols[3]:
        if selected:
            card("Текущее действие", selected["lifecycle_status"], "Owner selected", "blue")
        else:
            card("Текущее действие", "Не выбрано", "Proposed", "gray")

    st.write("")
    c1, c2 = st.columns([1.05, .95])
    with c1:
        st.markdown(
            """<div class="setds-card">
            <h3 style="margin-top:0">Что изменилось?</h3>
            <div class="setds-callout setds-danger">
            <b>Repeat guest G-104:</b> длительность визита снизилась 6 → 3 → 2 ночи.
            Это два последовательных отрицательных отклонения; второе отклонение по модулю сильнее.
            </div>
            <b>Что это означает:</b> существует повторяющийся behavioural signal.<br>
            <b>Чего это не означает:</b> причина ещё не доказана.
            </div>""",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            """<div class="setds-card">
            <h3 style="margin-top:0">Текущее системное предложение</h3>
            <div class="setds-callout">
            Не переходить сразу к полному внедрению. Проверить обратимый вариант через ограниченный pilot.
            </div>
            <b>Логика:</b> cause confidence и action confidence — разные величины.
            Даже правдоподобная причина не доказывает, что конкретное действие сработает.
            </div>""",
            unsafe_allow_html=True,
        )
    st.subheader("Активные сигналы")
    st.dataframe(sigs, use_container_width=True, hide_index=True)

# ---- Guest
elif page == "Гость: динамика":
    page_header(
        "Longitudinal relationship",
        "Гость G-104 — история, а не один визит",
        "SETDS анализирует изменение поведения во времени, но не превращает сам факт изменения в причинный вывод.",
    )
    hist = get_guest_visit_history(conn, "G-104")
    df = pd.DataFrame(hist)
    left, right = st.columns([1.15, .85])
    with left:
        st.subheader("Длительность пребывания")
        chart = df[["start_date", "length_of_stay_nights"]].copy()
        chart["start_date"] = pd.to_datetime(chart["start_date"])
        st.line_chart(chart.set_index("start_date"), height=300)
        st.dataframe(
            df[["start_date","length_of_stay_nights","services","price_paid"]],
            use_container_width=True, hide_index=True
        )
    with right:
        vals = df["length_of_stay_nights"].tolist()
        devs = pd.DataFrame(calculate_visit_deviations(vals))
        st.subheader("Derived deviations")
        st.dataframe(devs, use_container_width=True, hide_index=True)
        st.markdown(
            """<div class="setds-callout setds-warn">
            <b>6 → 3 → 2</b> даёт persistence = 2, а не 3:
            считаются два последовательных падения между тремя визитами.
            </div>""", unsafe_allow_html=True
        )
        st.write("**Изменение услуг:**", service_usage_changes(hist))
        st.write("**Интервалы возврата, дни:**", revisit_intervals_days(hist))
    st.markdown(
        """<div class="setds-callout">
        <b>Важно:</b> “spa перестал использоваться” — наблюдаемый сигнал.
        “гость сократил stay из-за spa” — причинная гипотеза, которая остаётся Inferred.
        </div>""", unsafe_allow_html=True
    )

# ---- Evidence
elif page == "Evidence & причины":
    page_header(
        "Epistemic layer",
        "Evidence & конкурирующие причинные гипотезы",
        "Supporting, refuting и neutral evidence хранятся отдельно. Neutral evidence не увеличивает convergence.",
    )
    hs = qdf(
        """SELECT hypothesis_id,description,cause_confidence,evidence_tag
           FROM hypotheses ORDER BY cause_confidence DESC"""
    )
    st.dataframe(
        hs.style.format({"cause_confidence":"{:.1%}"}),
        use_container_width=True, hide_index=True
    )
    hid = st.selectbox("Разобрать гипотезу", hs["hypothesis_id"].tolist())
    conv = evidence_convergence(conn, hid)
    a,b,c = st.columns(3)
    a.metric("Cause confidence", f"{conv['cause_confidence']:.1%}")
    b.metric("Supporting source types", conv["supporting_source_types_count"])
    c.metric("Evidence tag", conv["evidence_tag"])
    st.json(conv, expanded=False)
    ev = qdf(
        """SELECT hypothesis_id,evidence_type,provenance,effect,multiplier,
                  posterior_before,posterior_after
           FROM evidence_log ORDER BY date"""
    )
    st.subheader("Evidence log")
    st.dataframe(ev, use_container_width=True, hide_index=True)
    st.markdown(
        """<div class="setds-callout">
        <b>Known observation ≠ Known cause.</b>
        Например, запись “гость сообщил, что удобных spa-слотов не было” может быть достоверно зафиксированным фактом высказывания,
        но causal claim остаётся Inferred.
        </div>""", unsafe_allow_html=True
    )

# ---- Employee
elif page == "Персонал":
    page_header(
        "Service context",
        "Персонал — сначала условия, потом вывод о человеке",
        "Жалобы рассматриваются вместе с нагрузкой, очередями, overtime и staffing level.",
    )
    emp = qdf(
        """SELECT shift_date,employee_id,shift_hours,overtime_minutes,
                  staff_on_shift,expected_staff,guest_contacts,complaint_count,
                  praise_count,avg_queue_minutes,self_reported_load
           FROM employee_shift_observations ORDER BY shift_date"""
    )
    st.dataframe(emp, use_container_width=True, hide_index=True)
    c1,c2,c3,c4 = st.columns(4)
    latest = emp.iloc[-1]
    c1.metric("Staff on shift", f"{int(latest.staff_on_shift)}/{int(latest.expected_staff)}")
    c2.metric("Overtime", f"{int(latest.overtime_minutes)} мин")
    c3.metric("Queue", f"{latest.avg_queue_minutes:.0f} мин")
    c4.metric("Complaints", int(latest.complaint_count))
    st.markdown(
        """<div class="setds-callout setds-warn">
        <b>Guardrail:</b> рост жалоб сам по себе не является доказательством individual-performance problem.
        Система сначала проверяет overload / understaffing / schedule / process.
        </div>""", unsafe_allow_html=True
    )
    st.subheader("Рабочая интерпретация demo")
    st.write("**Поддерживаются:** overload, understaffing.")
    st.write("**Недостаточно данных:** individual performance.")
    st.write("**Следующее действие:** организационная проверка / pilot перераспределения нагрузки, а не автоматическое кадровое решение.")

# ---- Competitor
elif page == "Конкуренты":
    page_header(
        "Market context",
        "Конкурентная позиция",
        "Абсолютное улучшение не гарантирует относительного улучшения: рынок может изменяться быстрее.",
    )
    l,r = st.columns([.8,1.2])
    with l:
        own = st.number_input("Изменение нашего показателя", value=0.20, step=0.05, format="%.2f")
        c1 = st.number_input("Конкурент A", value=0.60, step=0.05, format="%.2f")
        c2 = st.number_input("Конкурент B", value=0.30, step=0.05, format="%.2f")
        c3 = st.number_input("Конкурент C", value=0.40, step=0.05, format="%.2f")
    rcg = relative_competitive_gap(own, [c1,c2,c3])
    with r:
        m1,m2 = st.columns(2)
        m1.metric("Median benchmark Δ", f"{rcg['benchmark_delta']:+.2f}")
        m2.metric("Relative Competitive Gap", f"{rcg['gap']:+.2f}")
        if rcg["relative_erosion"]:
            st.markdown(
                """<div class="setds-callout setds-warn">
                <b>Relative erosion:</b> предприятие улучшилось, но медианный конкурентный benchmark улучшился быстрее.
                </div>""", unsafe_allow_html=True
            )
        else:
            st.markdown(
                """<div class="setds-callout setds-success">
                Темп изменения предприятия не ниже медианного benchmark.
                </div>""", unsafe_allow_html=True
            )
        st.caption("MVP formula: RCG = ΔOwn − median(ΔCompetitors).")

# ---- Decision
elif page == "Решение & пилот":
    page_header(
        "Human-in-the-loop",
        "Решение владельца и проверка действия",
        "Здесь можно реально пройти state machine: выбрать действие, Verify, Test, записать pilot outcome и перейти к Implement.",
    )
    acts = qdf(
        """SELECT action_id,description,action_family,action_confidence,
                  is_system_preferred,is_owner_selected,lifecycle_status,
                  pilot_success_rule,pilot_stop_rule
           FROM actions WHERE hypothesis_id='H3'
           ORDER BY is_system_preferred DESC, description"""
    )
    display = acts.copy()
    display["system_preferred"] = display["is_system_preferred"].map({1:"✓",0:""})
    display["owner_selected"] = display["is_owner_selected"].map({1:"✓",0:""})
    display["action_confidence"] = display["action_confidence"].map(
        lambda x: "Unknown" if pd.isna(x) else f"{x:.0%}"
    )
    st.dataframe(
        display[["action_id","description","action_confidence","system_preferred","owner_selected","lifecycle_status"]],
        use_container_width=True, hide_index=True
    )

    options = dict(zip(acts["action_id"], acts["description"]))
    current_ids = acts["action_id"].tolist()
    default_ix = 0
    preferred = acts[acts["is_system_preferred"] == 1]
    if len(preferred):
        default_ix = current_ids.index(preferred.iloc[0]["action_id"])
    aid = st.selectbox(
        "Действие",
        current_ids,
        index=default_ix,
        format_func=lambda x: f"{x} — {options[x]}",
    )
    chosen = acts[acts["action_id"] == aid].iloc[0]
    st.markdown(f"**Текущий lifecycle:** `{chosen['lifecycle_status']}`")
    if chosen["pilot_success_rule"]:
        st.caption(f"Success rule: {chosen['pilot_success_rule']}")
    if chosen["pilot_stop_rule"]:
        st.caption(f"Stop rule: {chosen['pilot_stop_rule']}")

    rationale = st.text_area(
        "Обоснование владельца",
        value="Ограниченный обратимый тест перед масштабированием.",
        height=85,
    )

    r1 = st.columns(4)
    if r1[0].button("1 · Выбрать владельцем", type="primary", use_container_width=True):
        try:
            record_owner_decision(conn, aid, rationale)
            st.success("Owner selection записан.")
            st.rerun()
        except Exception as e:
            st.error(str(e))
    if r1[1].button("2 · Verify", use_container_width=True):
        try:
            request_transition(conn, "H3", aid, "Verify", "owner")
            st.success("Переведено в Verify.")
            st.rerun()
        except Exception as e:
            st.error(str(e))
    if r1[2].button("3 · Test", use_container_width=True):
        try:
            request_transition(conn, "H3", aid, "Test", "owner")
            st.success("Pilot начат: статус Test.")
            st.rerun()
        except Exception as e:
            st.error(str(e))
    outcome_choice = r1[3].selectbox("Pilot outcome", ["validated","failed","inconclusive"], label_visibility="collapsed")

    r2 = st.columns(4)
    if r2[0].button("4 · Записать outcome", use_container_width=True):
        try:
            record_pilot_outcome(conn, aid, outcome_choice, f"Demo pilot outcome: {outcome_choice}.")
            st.success(f"Outcome {outcome_choice} записан.")
            st.rerun()
        except Exception as e:
            st.error(str(e))
    target = {
        "validated":"Pilot_validated",
        "failed":"Pilot_failed",
        "inconclusive":"Reassess",
    }[outcome_choice]
    if r2[1].button(f"5 · → {target}", use_container_width=True):
        try:
            request_transition(conn, "H3", aid, target, "owner")
            st.success(f"Статус: {target}")
            st.rerun()
        except Exception as e:
            st.error(str(e))
    if r2[2].button("6 · Implement", use_container_width=True):
        try:
            request_transition(conn, "H3", aid, "Implement", "owner")
            st.success("Разрешён переход в Implement.")
            st.rerun()
        except Exception as e:
            st.error(str(e))
    if r2[3].button("Остановить действие", use_container_width=True):
        try:
            stop_action(conn, "H3", aid, "owner", "Остановлено владельцем в demo.")
            st.success("Действие остановлено.")
            st.rerun()
        except Exception as e:
            st.error(str(e))

    st.markdown(
        """<div class="setds-callout">
        Попробуйте специально нарушить порядок — например, нажать <b>Implement</b> до validated pilot.
        SETDS должна заблокировать переход и показать причину.
        </div>""", unsafe_allow_html=True
    )

# ---- Memory
elif page == "Decision Memory":
    page_header(
        "Longitudinal governance",
        "Decision Memory",
        "Система помнит не только рекомендацию, но и выбор владельца, переходы, исход пилота и причины остановки/замены.",
    )
    mem = qdf(
        """SELECT dm.memory_id,dm.hypothesis_id,dm.action_id,a.description,
                  dm.outcome_status,dm.actual_outcome,dm.outcome_recorded_at,
                  dm.status_history
           FROM decision_memory dm JOIN actions a ON a.action_id=dm.action_id
           ORDER BY dm.memory_id"""
    )
    if mem.empty:
        st.info("Память пока пустая. Сначала пройдите хотя бы один переход в разделе «Решение & пилот».")
    else:
        st.dataframe(
            mem[["memory_id","hypothesis_id","action_id","description","outcome_status","outcome_recorded_at"]],
            use_container_width=True, hide_index=True
        )
        row_ix = st.selectbox("Открыть запись", range(len(mem)), format_func=lambda i: mem.iloc[i]["memory_id"])
        row = mem.iloc[row_ix]
        st.write("**Action:**", row["description"])
        try:
            hist = json.loads(row["status_history"])
        except Exception:
            hist = row["status_history"]
        st.json(hist, expanded=True)
        if row["actual_outcome"]:
            st.write("**Actual outcome:**", row["actual_outcome"])

# ---- Scenarios
elif page == "Сценарии":
    page_header(
        "Bounded foresight",
        "Scenario Explorer",
        "Не миллион ветвей, а 2–3 управленческие траектории. После 1 года точность уступает место условным сценариям.",
    )
    scenarios = build_bounded_scenarios(
        {
            "0–1 год":"capacity unchanged",
            "1–3 года":"repeat-stay risk persists",
            "3–5 лет":"possible service erosion",
            "5–10 лет":"stagnation scenario",
        },
        {
            "0–1 год":"reversible priority-slot pilot",
            "1–3 года":"scale only if validated",
            "3–5 лет":"adaptive retention process",
            "5–10 лет":"resilient service scenario",
        },
        {
            "0–1 год":"prepare staffing/process",
            "1–3 года":"reassess after more evidence",
            "3–5 лет":"conditional expansion",
            "5–10 лет":"moderate adaptation scenario",
        },
    )
    cols = st.columns(len(scenarios))
    for col, sc in zip(cols, scenarios):
        with col:
            st.markdown(f"### {sc['name']}")
            for horizon, text in sc["path"].items():
                st.markdown(f"**{horizon}**")
                st.write(text)
    st.markdown(
        """<div class="setds-callout">
        <b>Trigger-based future:</b> долгосрочная траектория должна меняться при новых фактах,
        а не выдаваться как фиксированный прогноз на 2036 год.
        </div>""", unsafe_allow_html=True
    )

st.markdown("---")
st.caption("SETDS research demonstrator · SQLite + Python + Streamlit · demo seed values are illustrative.")
