import statistics
import streamlit as st

st.set_page_config(
    page_title="SETDS — Simple Interactive Demo",
    page_icon="◈",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    [data-testid="stSidebar"]{display:none}
    .block-container{
        max-width:760px;
        padding-top:1.1rem;
        padding-bottom:3rem;
    }
    h1{
        font-size:2rem!important;
        letter-spacing:-.03em;
        margin-bottom:.2rem;
    }
    h2{
        font-size:1.25rem!important;
    }
    .small{
        color:#667085;
        font-size:.86rem;
    }
    .hero{
        padding:18px;
        border-radius:18px;
        background:linear-gradient(135deg,#eef4ff,#f8f7ff);
        border:1px solid #dce5ff;
        margin-bottom:16px;
    }
    .card{
        background:#fff;
        border:1px solid #e5eaf1;
        border-radius:16px;
        padding:16px;
        margin:10px 0;
        box-shadow:0 8px 22px rgba(16,24,40,.04);
    }
    .callout{
        padding:14px 15px;
        border-radius:14px;
        background:#eef4ff;
        border-left:4px solid #3157d5;
        margin:10px 0;
    }
    .good{
        background:#ecfdf3;
        border-left-color:#12b76a;
    }
    .warn{
        background:#fff8e8;
        border-left-color:#f59e0b;
    }
    .bad{
        background:#fff1f3;
        border-left-color:#f04438;
    }
    .pill{
        display:inline-block;
        padding:4px 9px;
        border-radius:999px;
        font-size:.74rem;
        font-weight:800;
        margin-right:5px;
    }
    .purple{
        background:#ede9fe;
        color:#6d28d9;
    }
    .stButton>button{
        border-radius:12px;
        min-height:3rem;
        font-weight:800;
    }
    div[data-testid="stMetric"]{
        background:#fff;
        border:1px solid #e5eaf1;
        border-radius:15px;
        padding:12px;
    }
    @media(max-width:700px){
        .block-container{
            padding-left:1rem;
            padding-right:1rem;
        }
        h1{
            font-size:1.6rem!important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

def init():
    defaults = {
        "enterprise": "Altair (demo)",
        "visit1": 6,
        "visit2": 3,
        "visit3": 2,
        "rating1": 9,
        "rating2": 7,
        "rating3": 7,
        "spa_feedback": True,
        "ops_confirm": True,
        "analysis": None,
        "pilot_answer": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init()

st.markdown(
    """
    <div class="hero">
        <div class="small"><b>Interactive research demo</b></div>
        <h1>◈ SETDS</h1>
        <div class="small">
            Введите несколько значений. Нажмите одну кнопку.
            Получите объяснение и следующий шаг.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.subheader("1. Введите данные")

st.session_state.enterprise = st.text_input(
    "Объект / предприятие",
    st.session_state.enterprise,
)

st.markdown("**Длительность трёх визитов одного повторного гостя**")

v1 = st.number_input(
    "Первый визит, ночей",
    min_value=1,
    value=int(st.session_state.visit1),
    step=1,
)

v2 = st.number_input(
    "Второй визит, ночей",
    min_value=1,
    value=int(st.session_state.visit2),
    step=1,
)

v3 = st.number_input(
    "Последний визит, ночей",
    min_value=1,
    value=int(st.session_state.visit3),
    step=1,
)

st.session_state.visit1 = v1
st.session_state.visit2 = v2
st.session_state.visit3 = v3

with st.expander("Дополнительно: рейтинги", expanded=False):

    r1 = st.number_input(
        "Рейтинг первого визита",
        min_value=0,
        max_value=10,
        value=int(st.session_state.rating1),
        step=1,
    )

    r2 = st.number_input(
        "Рейтинг второго визита",
        min_value=0,
        max_value=10,
        value=int(st.session_state.rating2),
        step=1,
    )

    r3 = st.number_input(
        "Рейтинг последнего визита",
        min_value=0,
        max_value=10,
        value=int(st.session_state.rating3),
        step=1,
    )

    st.session_state.rating1 = r1
    st.session_state.rating2 = r2
    st.session_state.rating3 = r3


st.markdown("**Что ещё известно?**")

st.session_state.spa_feedback = st.checkbox(
    "Гость сказал, что хотел spa, но не было удобного времени",
    value=st.session_state.spa_feedback,
)

st.session_state.ops_confirm = st.checkbox(
    "Журнал или персонал подтверждает высокую загрузку spa",
    value=st.session_state.ops_confirm,
)


def analyze():

    values = [
        float(st.session_state.visit1),
        float(st.session_state.visit2),
        float(st.session_state.visit3),
    ]

    deviation_2 = (values[1] - values[0]) / values[0]

    baseline_3 = statistics.mean(values[:2])

    deviation_3 = (values[2] - baseline_3) / baseline_3

    persistence = (
        int(deviation_2 < -0.30)
        + int(deviation_3 < -0.30)
    )

    worsening = (
        deviation_2 < 0
        and deviation_3 < 0
        and abs(deviation_3) > abs(deviation_2)
    )

    source_types = {"guest_behavior"}

    if st.session_state.spa_feedback:
        source_types.add("guest_feedback")

    if (
        persistence >= 2
        and len(source_types) >= 2
        and worsening
    ):
        severity = "RED FLAG"

    elif persistence >= 2 or len(source_types) >= 2:
        severity = "WARNING"

    elif abs(deviation_3) >= 0.30:
        severity = "WATCH"

    else:
        severity = "NONE"

    priors = {
        "Spa capacity / schedule mismatch": 0.25,
        "Price sensitivity": 0.25,
        "Changed personal context": 0.25,
        "Competitor pull": 0.25,
    }

    weights = {
        key: 1.0
        for key in priors
    }

    reasons = []

    if st.session_state.spa_feedback:

        weights["Spa capacity / schedule mismatch"] *= 2.0

        weights["Price sensitivity"] *= 0.4

        weights["Changed personal context"] *= 0.4

        reasons.append(
            "Гость сообщил о неудобных или недоступных spa-слотах."
        )

    if st.session_state.ops_confirm:

        weights["Spa capacity / schedule mismatch"] *= 1.8

        reasons.append(
            "Операционный источник подтверждает высокую загрузку spa."
        )

    unnormalized = {
        key: priors[key] * weights[key]
        for key in priors
    }

    denominator = sum(
        unnormalized.values()
    )

    posterior = {
        key: value / denominator
        for key, value in unnormalized.items()
    }

    leading_hypothesis = max(
        posterior,
        key=posterior.get,
    )

    leading_confidence = posterior[
        leading_hypothesis
    ]

    if (
        leading_confidence >= 0.60
        and st.session_state.ops_confirm
    ):

        action = (
            "Провести небольшой обратимый pilot: "
            "выделить ограниченное число приоритетных "
            "spa-слотов для повторных гостей."
        )

        disposition = "PILOT"

    elif leading_confidence >= 0.45:

        action = (
            "Проверить ещё один независимый источник "
            "данных перед тестом."
        )

        disposition = "VERIFY"

    else:

        action = (
            "Пока наблюдать и собрать больше данных."
        )

        disposition = "OBSERVE"

    return {
        "severity": severity,
        "deviation_2": deviation_2,
        "deviation_3": deviation_3,
        "persistence": persistence,
        "worsening": worsening,
        "source_types": sorted(source_types),
        "posterior": posterior,
        "leading_hypothesis": leading_hypothesis,
        "leading_confidence": leading_confidence,
        "reasons": reasons,
        "action": action,
        "disposition": disposition,
    }


if st.button(
    "АНАЛИЗИРОВАТЬ",
    type="primary",
    use_container_width=True,
):

    st.session_state.analysis = analyze()

    st.session_state.pilot_answer = None


if st.session_state.analysis:

    result = st.session_state.analysis

    st.markdown("---")

    st.subheader("2. Результат")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Сигнал",
        result["severity"],
    )

    col2.metric(
        "Persistence",
        result["persistence"],
    )

    col3.metric(
        "Последнее отклонение",
        f"{result['deviation_3']:.1%}",
    )

    st.markdown(
        f"""
        <div class="card">
            <b>Что изменилось</b><br>
            Длительность визитов:
            {st.session_state.visit1}
            →
            {st.session_state.visit2}
            →
            {st.session_state.visit3}
            ночей.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="card">
            <b>Наиболее вероятная причина</b><br>
            {result['leading_hypothesis']}
            —
            <b>{result['leading_confidence']:.1%}</b>
            <br>
            <span class="pill purple">
                Inferred
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if result["reasons"]:

        reasons_html = "<br>".join(
            "• " + item
            for item in result["reasons"]
        )

        st.markdown(
            f"""
            <div class="card">
                <b>Почему система так считает</b><br>
                {reasons_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        f"""
        <div class="callout good">
            <b>{result['disposition']}</b><br>
            {result['action']}
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander(
        "Показать другие гипотезы",
        expanded=False,
    ):

        sorted_hypotheses = sorted(
            result["posterior"].items(),
            key=lambda item: item[1],
            reverse=True,
        )

        for hypothesis, confidence in sorted_hypotheses:

            st.write(
                f"**{hypothesis}:** "
                f"{confidence:.1%}"
            )

        st.caption(
            "Demo confidence — иллюстративная "
            "evidence-weighted оценка, "
            "а не эмпирически калиброванная вероятность."
        )

    st.subheader(
        "3. Если pilot уже провели — что получилось?"
    )

    c1, c2, c3 = st.columns(3)

    if c1.button(
        "Сработало",
        use_container_width=True,
    ):
        st.session_state.pilot_answer = "validated"

    if c2.button(
        "Не сработало",
        use_container_width=True,
    ):
        st.session_state.pilot_answer = "failed"

    if c3.button(
        "Непонятно",
        use_container_width=True,
    ):
        st.session_state.pilot_answer = "inconclusive"

    answer = st.session_state.pilot_answer

    if answer == "validated":

        st.markdown(
            """
            <div class="callout good">
                <b>Можно рассматривать внедрение.</b><br>
                Pilot подтвердил действие.
                Масштабировать постепенно
                и продолжать monitoring.
            </div>
            """,
            unsafe_allow_html=True,
        )

    elif answer == "failed":

        st.markdown(
            """
            <div class="callout bad">
                <b>Не внедрять.</b><br>
                Pilot не подтвердил действие.
                Вернуться к другим гипотезам
                и альтернативам.
            </div>
            """,
            unsafe_allow_html=True,
        )

    elif answer == "inconclusive":

        st.markdown(
            """
            <div class="callout warn">
                <b>Отложить решение.</b><br>
                Результат неубедителен.
                Нужна повторная проверка
                или дополнительное evidence.
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    if st.button(
        "Очистить и попробовать другой пример",
        use_container_width=True,
    ):

        for key in list(
            st.session_state.keys()
        ):
            del st.session_state[key]

        st.rerun()


st.caption(
    "SETDS research demonstrator · "
    "simple input → transparent analysis → "
    "one-step pilot feedback"
)
