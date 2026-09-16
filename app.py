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
    [data-testid="stSidebar"]{
        display:none;
    }

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
        "room_problem": False,
        "service_problem": False,
        "staff_problem": False,
        "price_problem": False,
        "competitor_problem": False,
        "custom_fact": "",
        "analysis": None,
        "solution_answer": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init()


st.markdown(
    """
    <div class="hero">
        <div class="small">
            <b>Interactive research demo</b>
        </div>

        <h1>◈ SETDS</h1>

        <div class="small">
            Введите несколько значений, отметьте известные факты
            и нажмите одну кнопку.
            Система покажет, что изменилось, почему это могло произойти
            и что разумно сделать дальше.
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

st.markdown(
    "**Длительность трёх визитов одного повторного гостя**"
)

visit1 = st.number_input(
    "Первый визит, ночей",
    min_value=1,
    value=int(st.session_state.visit1),
    step=1,
)

visit2 = st.number_input(
    "Второй визит, ночей",
    min_value=1,
    value=int(st.session_state.visit2),
    step=1,
)

visit3 = st.number_input(
    "Последний визит, ночей",
    min_value=1,
    value=int(st.session_state.visit3),
    step=1,
)

st.session_state.visit1 = visit1
st.session_state.visit2 = visit2
st.session_state.visit3 = visit3


with st.expander(
    "Дополнительно: рейтинги",
    expanded=False,
):

    rating1 = st.number_input(
        "Рейтинг первого визита",
        min_value=0,
        max_value=10,
        value=int(st.session_state.rating1),
        step=1,
    )

    rating2 = st.number_input(
        "Рейтинг второго визита",
        min_value=0,
        max_value=10,
        value=int(st.session_state.rating2),
        step=1,
    )

    rating3 = st.number_input(
        "Рейтинг последнего визита",
        min_value=0,
        max_value=10,
        value=int(st.session_state.rating3),
        step=1,
    )

    st.session_state.rating1 = rating1
    st.session_state.rating2 = rating2
    st.session_state.rating3 = rating3


st.markdown("**Что известно о ситуации?**")

st.session_state.spa_feedback = st.checkbox(
    "Гость сообщил о проблеме со spa или неудобном времени",
    value=st.session_state.spa_feedback,
)

st.session_state.ops_confirm = st.checkbox(
    "Журнал или персонал подтверждает высокую загрузку услуги",
    value=st.session_state.ops_confirm,
)

st.session_state.room_problem = st.checkbox(
    "Есть проблема с номером / спальней: шум, кровать, температура, чистота или комфорт",
    value=st.session_state.room_problem,
)

st.session_state.service_problem = st.checkbox(
    "Есть проблема с другой услугой: питание, Wi-Fi, парковка, трансфер, бассейн или другое",
    value=st.session_state.service_problem,
)

st.session_state.staff_problem = st.checkbox(
    "Есть жалобы на обслуживание, очередь или нехватку персонала",
    value=st.session_state.staff_problem,
)

st.session_state.price_problem = st.checkbox(
    "Гость считает цену высокой или у конкурентов предложение выгоднее",
    value=st.session_state.price_problem,
)

st.session_state.competitor_problem = st.checkbox(
    "У конкурента появилась новая услуга, выше рейтинг или более сильное предложение",
    value=st.session_state.competitor_problem,
)

st.session_state.custom_fact = st.text_input(
    "Другой известный факт",
    value=st.session_state.custom_fact,
    placeholder="Например: в номере было шумно ночью",
)


def analyze():

    values = [
        float(st.session_state.visit1),
        float(st.session_state.visit2),
        float(st.session_state.visit3),
    ]

    deviation_2 = (
        values[1] - values[0]
    ) / values[0]

    baseline_3 = statistics.mean(
        values[:2]
    )

    deviation_3 = (
        values[2] - baseline_3
    ) / baseline_3

    persistence = (
        int(deviation_2 < -0.30)
        + int(deviation_3 < -0.30)
    )

    worsening = (
        deviation_2 < 0
        and deviation_3 < 0
        and abs(deviation_3)
        > abs(deviation_2)
    )

    source_types = {
        "guest_behavior"
    }

    if st.session_state.spa_feedback:
        source_types.add(
            "guest_feedback"
        )

    if st.session_state.room_problem:
        source_types.add(
            "room_feedback"
        )

    if st.session_state.service_problem:
        source_types.add(
            "service_feedback"
        )

    if st.session_state.staff_problem:
        source_types.add(
            "service_operation"
        )

    if st.session_state.price_problem:
        source_types.add(
            "price_signal"
        )

    if st.session_state.competitor_problem:
        source_types.add(
            "competitor_signal"
        )

    if (
        persistence >= 2
        and len(source_types) >= 2
        and worsening
    ):
        severity = "RED FLAG"

    elif (
        persistence >= 2
        or len(source_types) >= 2
    ):
        severity = "WARNING"

    elif abs(deviation_3) >= 0.30:
        severity = "WATCH"

    else:
        severity = "NONE"


    priors = {
        "Spa capacity / schedule mismatch": 0.20,
        "Room / sleep comfort problem": 0.20,
        "Price sensitivity": 0.20,
        "Service / staff issue": 0.20,
        "Competitor pull": 0.20,
    }

    weights = {
        key: 1.0
        for key in priors
    }

    reasons = []


    if st.session_state.spa_feedback:

        weights[
            "Spa capacity / schedule mismatch"
        ] *= 2.0

        weights[
            "Price sensitivity"
        ] *= 0.7

        reasons.append(
            "Гость сообщил о неудобных или недоступных spa-слотах."
        )


    if st.session_state.ops_confirm:

        weights[
            "Spa capacity / schedule mismatch"
        ] *= 1.8

        reasons.append(
            "Операционный источник подтверждает высокую загрузку услуги."
        )


    if st.session_state.room_problem:

        weights[
            "Room / sleep comfort problem"
        ] *= 2.0

        reasons.append(
            "Есть зафиксированная проблема с номером, спальней или качеством сна."
        )


    if st.session_state.service_problem:

        weights[
            "Service / staff issue"
        ] *= 1.6

        reasons.append(
            "Есть проблема с дополнительной услугой."
        )


    if st.session_state.staff_problem:

        weights[
            "Service / staff issue"
        ] *= 1.8

        reasons.append(
            "Есть признаки очередей, перегрузки или нехватки персонала."
        )


    if st.session_state.price_problem:

        weights[
            "Price sensitivity"
        ] *= 1.8

        reasons.append(
            "Есть признаки ценовой чувствительности или более выгодного предложения."
        )


    if st.session_state.competitor_problem:

        weights[
            "Competitor pull"
        ] *= 1.8

        reasons.append(
            "Есть признаки усиления предложения конкурента."
        )


    if st.session_state.custom_fact.strip():

        reasons.append(
            "Дополнительный факт: "
            + st.session_state.custom_fact.strip()
        )


    unnormalized = {
        key:
        priors[key]
        * weights[key]

        for key in priors
    }

    denominator = sum(
        unnormalized.values()
    )

    posterior = {
        key:
        value / denominator

        for key, value
        in unnormalized.items()
    }

    leading_hypothesis = max(
        posterior,
        key=posterior.get,
    )

    leading_confidence = posterior[
        leading_hypothesis
    ]


    if (
        leading_confidence >= 0.45
        and len(reasons) >= 2
    ):

        disposition = (
            "ПРОВЕРИТЬ РЕШЕНИЕ"
        )

        action = (
            "Попробовать небольшой, обратимый вариант решения "
            "на ограниченном числе гостей или смен, "
            "а затем посмотреть, помогло ли это."
        )

    elif (
        leading_confidence >= 0.35
    ):

        disposition = (
            "СОБРАТЬ ЕЩЁ ДАННЫЕ"
        )

        action = (
            "Проверить ещё один независимый источник "
            "перед изменением процесса."
        )

    else:

        disposition = (
            "НАБЛЮДАТЬ"
        )

        action = (
            "Пока не менять процесс. "
            "Собрать больше информации."
        )


    return {
        "severity":
        severity,

        "deviation_2":
        deviation_2,

        "deviation_3":
        deviation_3,

        "persistence":
        persistence,

        "worsening":
        worsening,

        "source_types":
        sorted(source_types),

        "posterior":
        posterior,

        "leading_hypothesis":
        leading_hypothesis,

        "leading_confidence":
        leading_confidence,

        "reasons":
        reasons,

        "action":
        action,

        "disposition":
        disposition,
    }


if st.button(
    "АНАЛИЗИРОВАТЬ",
    type="primary",
    use_container_width=True,
):

    st.session_state.analysis = (
        analyze()
    )

    st.session_state.solution_answer = None


if st.session_state.analysis:

    result = (
        st.session_state.analysis
    )

    st.markdown("---")

    st.subheader(
        "2. Что показывает SETDS"
    )

    col1, col2, col3 = (
        st.columns(3)
    )

    col1.metric(
        "Сигнал",
        result["severity"],
    )

    col2.metric(
        "Повторяемость",
        result["persistence"],
    )

    col3.metric(
        "Последнее изменение",
        f"{result['deviation_3']:.1%}",
    )


    st.markdown(
        f"""
        <div class="card">

            <b>
                Что изменилось
            </b>

            <br>

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

            <b>
                Ведущая возможная причина
            </b>

            <br>

            {result['leading_hypothesis']}

            —

            <b>
                {result['leading_confidence']:.1%}
            </b>

            <br>

            <span class="pill purple">
                Возможная причина
            </span>

        </div>
        """,
        unsafe_allow_html=True,
    )


    if result["reasons"]:

        reasons_html = "<br>".join(
            "• " + item
            for item
            in result["reasons"]
        )

        st.markdown(
            f"""
            <div class="card">

                <b>
                    Почему система так считает
                </b>

                <br>

                {reasons_html}

            </div>
            """,
            unsafe_allow_html=True,
        )


    st.markdown(
        f"""
        <div class="callout good">

            <b>
                {result['disposition']}
            </b>

            <br>

            {result['action']}

        </div>
        """,
        unsafe_allow_html=True,
    )


    with st.expander(
        "Показать другие возможные причины",
        expanded=False,
    ):

        sorted_hypotheses = sorted(
            result["posterior"].items(),
            key=lambda item:
            item[1],
            reverse=True,
        )

        for (
            hypothesis,
            confidence,
        ) in sorted_hypotheses:

            st.write(
                f"**{hypothesis}:** "
                f"{confidence:.1%}"
            )

        st.caption(
            "Эти значения являются "
            "иллюстративной оценкой для демонстрации работы системы, "
            "а не эмпирически калиброванной вероятностью."
        )


    st.subheader(
        "3. Вы уже попробовали предложенный вариант?"
    )

    st.caption(
        "Если да — просто укажите, что получилось."
    )


    col1, col2, col3 = (
        st.columns(3)
    )


    if col1.button(
        "Помогло",
        use_container_width=True,
    ):

        st.session_state.solution_answer = (
            "validated"
        )


    if col2.button(
        "Не помогло",
        use_container_width=True,
    ):

        st.session_state.solution_answer = (
            "failed"
        )


    if col3.button(
        "Пока непонятно",
        use_container_width=True,
    ):

        st.session_state.solution_answer = (
            "inconclusive"
        )


    answer = (
        st.session_state.solution_answer
    )


    if answer == "validated":

        st.markdown(
            """
            <div class="callout good">

                <b>
                    Можно рассматривать более широкое применение.
                </b>

                <br>

                Пробное решение помогло.
                Расширять его лучше постепенно
                и продолжать наблюдать за результатом.

            </div>
            """,
            unsafe_allow_html=True,
        )


    elif answer == "failed":

        st.markdown(
            """
            <div class="callout bad">

                <b>
                    Не внедрять шире.
                </b>

                <br>

                Пробное решение не помогло.
                Нужно вернуться к другим возможным причинам
                и вариантам действий.

            </div>
            """,
            unsafe_allow_html=True,
        )


    elif answer == "inconclusive":

        st.markdown(
            """
            <div class="callout warn">

                <b>
                    Пока рано принимать решение.
                </b>

                <br>

                Результат неясный.
                Нужно ещё немного данных
                или повторная проверка.

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

            del st.session_state[
                key
            ]

        st.rerun()


st.caption(
    "SETDS research demonstrator · "
    "simple input → transparent analysis → "
    "simple feedback on the proposed solution"
)
