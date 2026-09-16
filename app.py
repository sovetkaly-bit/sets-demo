import statistics
import streamlit as st

st.set_page_config(
    page_title="SETDS — интерактивная демонстрация",
    page_icon="◈",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {display:none;}
    .block-container {
        max-width:760px;
        padding-top:1rem;
        padding-bottom:3rem;
    }
    .stButton > button {
        min-height:3rem;
        border-radius:12px;
        font-weight:700;
    }
    div[data-testid="stMetric"] {
        border:1px solid #e5e7eb;
        border-radius:14px;
        padding:10px;
        background:white;
    }
    @media (max-width:700px) {
        .block-container {
            padding-left:1rem;
            padding-right:1rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

DEFAULTS = {
    "enterprise": "Altair (demo)",
    "visit1": 6,
    "visit2": 3,
    "visit3": 2,
    "rating1": 9,
    "rating2": 7,
    "rating3": 7,
    "spa_problem": False,
    "spa_confirmed": False,
    "room_problem": False,
    "service_problem": False,
    "staff_problem": False,
    "price_problem": False,
    "competitor_problem": False,
    "custom_fact": "",
    "analysis": None,
    "solution_result": None,
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

st.title("◈ SETDS")
st.write(
    "Введите несколько данных о ситуации. Система покажет, что изменилось, "
    "какие причины сейчас наиболее вероятны и что разумно сделать дальше."
)
st.caption("Интерактивная исследовательская демонстрация")
st.divider()

st.header("1. Введите данные")

st.session_state.enterprise = st.text_input(
    "Объект / предприятие",
    value=st.session_state.enterprise,
)

st.subheader("Длительность трёх визитов одного повторного гостя")

st.session_state.visit1 = st.number_input(
    "Первый визит, ночей",
    min_value=1,
    value=int(st.session_state.visit1),
    step=1,
)

st.session_state.visit2 = st.number_input(
    "Второй визит, ночей",
    min_value=1,
    value=int(st.session_state.visit2),
    step=1,
)

st.session_state.visit3 = st.number_input(
    "Последний визит, ночей",
    min_value=1,
    value=int(st.session_state.visit3),
    step=1,
)

with st.expander("Дополнительно: оценки гостя", expanded=False):
    st.session_state.rating1 = st.number_input(
        "Оценка после первого визита",
        min_value=0,
        max_value=10,
        value=int(st.session_state.rating1),
        step=1,
    )

    st.session_state.rating2 = st.number_input(
        "Оценка после второго визита",
        min_value=0,
        max_value=10,
        value=int(st.session_state.rating2),
        step=1,
    )

    st.session_state.rating3 = st.number_input(
        "Оценка после последнего визита",
        min_value=0,
        max_value=10,
        value=int(st.session_state.rating3),
        step=1,
    )

st.subheader("Что известно о ситуации?")

st.session_state.room_problem = st.checkbox(
    "Есть проблема с номером / спальней: шум, кровать, температура, чистота или комфорт",
    value=st.session_state.room_problem,
)

st.session_state.spa_problem = st.checkbox(
    "Гость сообщил о проблеме со spa или не смог выбрать удобное время",
    value=st.session_state.spa_problem,
)

st.session_state.spa_confirmed = st.checkbox(
    "Журнал или персонал подтверждает, что spa / услуга действительно была перегружена",
    value=st.session_state.spa_confirmed,
)

st.session_state.service_problem = st.checkbox(
    "Есть проблема с другой услугой: питание, Wi-Fi, бассейн, трансфер, парковка или другое",
    value=st.session_state.service_problem,
)

st.session_state.staff_problem = st.checkbox(
    "Есть жалобы на обслуживание, очередь, задержки или нехватку персонала",
    value=st.session_state.staff_problem,
)

st.session_state.price_problem = st.checkbox(
    "Есть признаки того, что гостя не устраивает цена",
    value=st.session_state.price_problem,
)

st.session_state.competitor_problem = st.checkbox(
    "У конкурента появилось более сильное предложение: ниже цена, выше рейтинг или новая услуга",
    value=st.session_state.competitor_problem,
)

st.session_state.custom_fact = st.text_area(
    "Другой известный факт",
    value=st.session_state.custom_fact,
    placeholder="Например: гость написал, что ночью было шумно и плохо спал",
    height=90,
)

def analyze():
    visits = [
        float(st.session_state.visit1),
        float(st.session_state.visit2),
        float(st.session_state.visit3),
    ]

    ratings = [
        float(st.session_state.rating1),
        float(st.session_state.rating2),
        float(st.session_state.rating3),
    ]

    change_second = (visits[1] - visits[0]) / visits[0]

    previous_mean = statistics.mean(visits[:2])

    change_latest = (visits[2] - previous_mean) / previous_mean

    persistence = 0

    if change_second <= -0.30:
        persistence += 1

    if change_latest <= -0.30:
        persistence += 1

    worsening = (
        change_second < 0
        and change_latest < 0
        and abs(change_latest) > abs(change_second)
    )

    rating_change = ratings[-1] - ratings[0]

    rating_decline = rating_change <= -2

    supporting_facts = 0

    if persistence >= 1:
        supporting_facts += 1

    if persistence >= 2:
        supporting_facts += 1

    if worsening:
        supporting_facts += 1

    if rating_decline:
        supporting_facts += 1

    if st.session_state.room_problem:
        supporting_facts += 1

    if st.session_state.spa_problem:
        supporting_facts += 1

    if st.session_state.service_problem:
        supporting_facts += 1

    if st.session_state.staff_problem:
        supporting_facts += 1

    if supporting_facts >= 5:
        signal_level = "Сильный сигнал"

    elif supporting_facts >= 3:
        signal_level = "Средний сигнал"

    elif supporting_facts >= 1:
        signal_level = "Слабый сигнал"

    else:
        signal_level = "Заметного сигнала нет"

    hypotheses = {
        "Проблема с номером или качеством сна": 1.0,
        "Перегруженность spa или неудобное время услуги": 1.0,
        "Проблема с обслуживанием или персоналом": 1.0,
        "Проблема с другой услугой": 1.0,
        "Ценовая чувствительность гостя": 1.0,
        "Более сильное предложение конкурента": 1.0,
        "Личные обстоятельства гостя": 1.0,
    }

    reasons = []

    if st.session_state.room_problem:
        hypotheses["Проблема с номером или качеством сна"] *= 3.0
        reasons.append(
            "Указана проблема с номером, спальней или качеством сна."
        )

    if st.session_state.spa_problem:
        hypotheses["Перегруженность spa или неудобное время услуги"] *= 2.5
        reasons.append(
            "Гость сообщил о проблеме с доступностью spa или временем услуги."
        )

    if st.session_state.spa_confirmed:
        hypotheses["Перегруженность spa или неудобное время услуги"] *= 2.0
        reasons.append(
            "Операционные данные подтверждают перегруженность услуги."
        )

    if st.session_state.staff_problem:
        hypotheses["Проблема с обслуживанием или персоналом"] *= 3.0
        reasons.append(
            "Есть информация об очередях, задержках или нехватке персонала."
        )

    if st.session_state.service_problem:
        hypotheses["Проблема с другой услугой"] *= 2.5
        reasons.append(
            "Есть зафиксированная проблема с одной из дополнительных услуг."
        )

    if st.session_state.price_problem:
        hypotheses["Ценовая чувствительность гостя"] *= 3.0
        reasons.append(
            "Есть признаки того, что цена влияет на решение гостя."
        )

    if st.session_state.competitor_problem:
        hypotheses["Более сильное предложение конкурента"] *= 3.0
        reasons.append(
            "Есть признаки усиления предложения конкурента."
        )

    if rating_decline:
        reasons.append(
            f"Оценка гостя снизилась с {int(ratings[0])} до {int(ratings[-1])}."
        )

    if st.session_state.custom_fact.strip():
        reasons.append(
            "Дополнительный факт: "
            + st.session_state.custom_fact.strip()
        )

    total_weight = sum(hypotheses.values())

    confidence = {
        name: weight / total_weight
        for name, weight in hypotheses.items()
    }

    sorted_hypotheses = sorted(
        confidence.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    leading_hypothesis = sorted_hypotheses[0][0]

    leading_confidence = sorted_hypotheses[0][1]

    evidence_count = len(reasons)

    if leading_confidence >= 0.30 and evidence_count >= 2:
        recommendation_title = "Проверить решение на небольшом масштабе"

        recommendation = (
            "Не менять весь процесс сразу. "
            "Попробовать ограниченное и обратимое решение, "
            "после чего сравнить результат."
        )

    elif evidence_count >= 1:
        recommendation_title = "Собрать ещё одно подтверждение"

        recommendation = (
            "Причина выглядит возможной, но данных пока мало. "
            "Лучше проверить ещё один независимый источник."
        )

    else:
        recommendation_title = "Пока наблюдать"

        recommendation = (
            "Данных недостаточно для уверенного решения. "
            "Пока не менять процесс и продолжить наблюдение."
        )

    return {
        "change_second": change_second,
        "change_latest": change_latest,
        "persistence": persistence,
        "worsening": worsening,
        "rating_change": rating_change,
        "signal_level": signal_level,
        "hypotheses": sorted_hypotheses,
        "leading_hypothesis": leading_hypothesis,
        "leading_confidence": leading_confidence,
        "reasons": reasons,
        "recommendation_title": recommendation_title,
        "recommendation": recommendation,
    }

if st.button(
    "АНАЛИЗИРОВАТЬ",
    type="primary",
    use_container_width=True,
):
    st.session_state.analysis = analyze()
    st.session_state.solution_result = None

if st.session_state.analysis:
    result = st.session_state.analysis

    st.divider()

    st.header("2. Результат")

    col1, col2 = st.columns(2)

    col1.metric(
        "Сила сигнала",
        result["signal_level"],
    )

    col2.metric(
        "Повторяемость ухудшения",
        result["persistence"],
    )

    st.subheader("Что произошло")

    st.write(
        f"Длительность визитов изменилась: "
        f"**{st.session_state.visit1} → "
        f"{st.session_state.visit2} → "
        f"{st.session_state.visit3} ночей**."
    )

    if result["worsening"]:
        st.warning(
            "Отрицательная динамика повторяется "
            "и последнее отклонение стало сильнее."
        )

    if result["rating_change"] < 0:
        st.write(
            f"Оценка гостя также изменилась: "
            f"**{st.session_state.rating1} → "
            f"{st.session_state.rating3}**."
        )

    st.subheader("Наиболее вероятное объяснение")

    st.info(
        result["leading_hypothesis"]
    )

    st.write(
        "Условная поддержка этой версии: "
        f"**{result['leading_confidence']:.0%}**"
    )

    st.caption(
        "Это не доказанная причина. "
        "Это версия, которая сейчас лучше всего "
        "соответствует введённым данным."
    )

    st.subheader(
        "Почему система так считает"
    )

    if result["reasons"]:
        for reason in result["reasons"]:
            st.write("• " + reason)

    else:
        st.write(
            "Дополнительных подтверждений пока нет."
        )

    st.subheader(
        "Что делать сейчас"
    )

    st.success(
        result["recommendation_title"]
        + "\n\n"
        + result["recommendation"]
    )

    with st.expander(
        "Показать другие возможные причины"
    ):
        for hypothesis, confidence in result["hypotheses"]:
            st.write(
                f"**{hypothesis}** — "
                f"{confidence:.0%}"
            )

        st.caption(
            "Проценты используются только "
            "для демонстрации логики сравнения гипотез "
            "и не являются эмпирически "
            "калиброванными вероятностями."
        )

    st.divider()

    st.header(
        "3. Вы уже попробовали предложенный вариант?"
    )

    st.write(
        "Если да — просто укажите, "
        "что получилось."
    )

    if st.button(
        "Помогло",
        use_container_width=True,
    ):
        st.session_state.solution_result = "helped"

    if st.button(
        "Не помогло",
        use_container_width=True,
    ):
        st.session_state.solution_result = "failed"

    if st.button(
        "Пока непонятно",
        use_container_width=True,
    ):
        st.session_state.solution_result = "unclear"

    if st.session_state.solution_result == "helped":
        st.success(
            "Решение помогло.\n\n"
            "Можно рассматривать более широкое применение, "
            "но расширять его лучше постепенно "
            "и продолжать наблюдать за результатом."
        )

    elif st.session_state.solution_result == "failed":
        st.error(
            "Решение не помогло.\n\n"
            "Не стоит внедрять его шире. "
            "Нужно вернуться к другим возможным причинам "
            "и вариантам действий."
        )

    elif st.session_state.solution_result == "unclear":
        st.warning(
            "Результат пока неясный.\n\n"
            "Лучше собрать ещё немного данных "
            "или повторить проверку."
        )

    st.divider()

    if st.button(
        "Очистить и попробовать другой пример",
        use_container_width=True,
    ):
        for key in list(st.session_state.keys()):
            del st.session_state[key]

        st.rerun()

st.caption(
    "SETDS — исследовательская демонстрация: "
    "ввод данных → анализ → объяснение → следующий шаг"
)
