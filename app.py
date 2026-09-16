import sqlite3
import hashlib
import statistics
from datetime import datetime
from pathlib import Path

import streamlit as st


# =========================================================
# НАСТРОЙКИ ПРИЛОЖЕНИЯ
# =========================================================

DB_PATH = Path(__file__).with_name("setds_app.db")

st.set_page_config(
    page_title="SETDS",
    page_icon="◈",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        display: none;
    }

    .block-container {
        max-width: 860px;
        padding-top: 1rem;
        padding-bottom: 3rem;
    }

    .stButton > button {
        min-height: 3rem;
        border-radius: 12px;
        font-weight: 700;
    }

    div[data-testid="stMetric"] {
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 10px;
        background: white;
    }

    @media (max-width: 700px) {
        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# БАЗА ДАННЫХ
# =========================================================

def db():
    conn = sqlite3.connect(
        DB_PATH,
        check_same_thread=False,
    )

    conn.row_factory = sqlite3.Row

    return conn


def init_db():
    conn = db()

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            organization TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'owner',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS guests (
            guest_id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_user_id INTEGER NOT NULL,
            guest_code TEXT NOT NULL,
            guest_name TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(owner_user_id, guest_code)
        );

        CREATE TABLE IF NOT EXISTS visits (
            visit_id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_user_id INTEGER NOT NULL,
            guest_id INTEGER NOT NULL,
            visit_date TEXT NOT NULL,
            nights INTEGER NOT NULL,
            rating INTEGER,
            spa_used INTEGER DEFAULT 0,
            room_problem INTEGER DEFAULT 0,
            spa_problem INTEGER DEFAULT 0,
            service_problem INTEGER DEFAULT 0,
            staff_problem INTEGER DEFAULT 0,
            price_problem INTEGER DEFAULT 0,
            competitor_problem INTEGER DEFAULT 0,
            free_text TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS decisions (
            decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_user_id INTEGER NOT NULL,
            guest_id INTEGER,
            created_at TEXT NOT NULL,
            signal_level TEXT,
            leading_hypothesis TEXT,
            recommendation TEXT,
            result_feedback TEXT
        );
        """
    )

    conn.commit()

    conn.close()


init_db()


# =========================================================
# АВТОРИЗАЦИЯ
# =========================================================

def hash_password(password):
    return hashlib.sha256(
        password.encode("utf-8")
    ).hexdigest()


def register_user(
    email,
    password,
    organization,
):
    conn = db()

    try:
        conn.execute(
            """
            INSERT INTO users(
                email,
                password_hash,
                organization,
                role,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                email.strip().lower(),
                hash_password(password),
                organization.strip(),
                "owner",
                datetime.now().isoformat(),
            ),
        )

        conn.commit()

        return True, "Аккаунт создан."

    except sqlite3.IntegrityError:

        return (
            False,
            "Такой email уже зарегистрирован.",
        )

    finally:
        conn.close()


def login_user(
    email,
    password,
):
    conn = db()

    row = conn.execute(
        """
        SELECT *
        FROM users
        WHERE email=?
        AND password_hash=?
        """,
        (
            email.strip().lower(),
            hash_password(password),
        ),
    ).fetchone()

    conn.close()

    if row:
        return dict(row)

    return None


def logout():
    for key in [
        "user",
        "page",
    ]:
        st.session_state.pop(
            key,
            None,
        )

    st.rerun()


# =========================================================
# РАБОТА С ГОСТЯМИ
# =========================================================

def get_guests(user_id):
    conn = db()

    rows = conn.execute(
        """
        SELECT *
        FROM guests
        WHERE owner_user_id=?
        ORDER BY guest_code
        """,
        (user_id,),
    ).fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]


def create_guest(
    user_id,
    guest_code,
    guest_name,
    notes,
):
    conn = db()

    try:
        conn.execute(
            """
            INSERT INTO guests(
                owner_user_id,
                guest_code,
                guest_name,
                notes,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                guest_code.strip(),
                guest_name.strip(),
                notes.strip(),
                datetime.now().isoformat(),
            ),
        )

        conn.commit()

        return (
            True,
            "Гость добавлен.",
        )

    except sqlite3.IntegrityError:

        return (
            False,
            "Такой код гостя уже существует.",
        )

    finally:
        conn.close()


# =========================================================
# РАБОТА С ВИЗИТАМИ
# =========================================================

def add_visit(
    user_id,
    guest_id,
    visit_date,
    nights,
    rating,
    facts,
    free_text,
):
    conn = db()

    conn.execute(
        """
        INSERT INTO visits(
            owner_user_id,
            guest_id,
            visit_date,
            nights,
            rating,
            spa_used,
            room_problem,
            spa_problem,
            service_problem,
            staff_problem,
            price_problem,
            competitor_problem,
            free_text,
            created_at
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """,
        (
            user_id,
            guest_id,
            str(visit_date),
            int(nights),
            int(rating)
            if rating is not None
            else None,
            int(
                facts.get(
                    "spa_used",
                    False,
                )
            ),
            int(
                facts.get(
                    "room_problem",
                    False,
                )
            ),
            int(
                facts.get(
                    "spa_problem",
                    False,
                )
            ),
            int(
                facts.get(
                    "service_problem",
                    False,
                )
            ),
            int(
                facts.get(
                    "staff_problem",
                    False,
                )
            ),
            int(
                facts.get(
                    "price_problem",
                    False,
                )
            ),
            int(
                facts.get(
                    "competitor_problem",
                    False,
                )
            ),
            free_text.strip(),
            datetime.now().isoformat(),
        ),
    )

    conn.commit()

    conn.close()


def get_visits(
    user_id,
    guest_id=None,
):
    conn = db()

    if guest_id is None:

        rows = conn.execute(
            """
            SELECT
                v.*,
                g.guest_code,
                g.guest_name
            FROM visits v

            JOIN guests g
            ON g.guest_id=v.guest_id

            WHERE v.owner_user_id=?

            ORDER BY visit_date
            """,
            (user_id,),
        ).fetchall()

    else:

        rows = conn.execute(
            """
            SELECT *
            FROM visits
            WHERE owner_user_id=?
            AND guest_id=?
            ORDER BY visit_date
            """,
            (
                user_id,
                guest_id,
            ),
        ).fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]


# =========================================================
# DECISION MEMORY
# =========================================================

def save_decision(
    user_id,
    guest_id,
    signal_level,
    leading_hypothesis,
    recommendation,
):
    conn = db()

    conn.execute(
        """
        INSERT INTO decisions(
            owner_user_id,
            guest_id,
            created_at,
            signal_level,
            leading_hypothesis,
            recommendation,
            result_feedback
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            guest_id,
            datetime.now().isoformat(),
            signal_level,
            leading_hypothesis,
            recommendation,
            None,
        ),
    )

    conn.commit()

    decision_id = conn.execute(
        "SELECT last_insert_rowid()"
    ).fetchone()[0]

    conn.close()

    return decision_id


def update_decision_feedback(
    decision_id,
    feedback,
):
    conn = db()

    conn.execute(
        """
        UPDATE decisions
        SET result_feedback=?
        WHERE decision_id=?
        """,
        (
            feedback,
            decision_id,
        ),
    )

    conn.commit()

    conn.close()


# =========================================================
# АНАЛИЗ ОДНОГО ГОСТЯ
# =========================================================

def analyze_guest(visits):

    if len(visits) < 2:
        return None

    nights = [
        float(v["nights"])
        for v in visits
    ]

    latest = nights[-1]

    baseline = statistics.mean(
        nights[:-1]
    )

    latest_deviation = (
        0
        if baseline == 0
        else (
            latest - baseline
        ) / baseline
    )

    negative_transitions = 0

    for i in range(
        1,
        len(nights),
    ):

        previous_mean = statistics.mean(
            nights[:i]
        )

        if previous_mean == 0:
            continue

        deviation = (
            nights[i] - previous_mean
        ) / previous_mean

        if deviation <= -0.30:
            negative_transitions += 1


    latest_visit = visits[-1]


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


    if latest_visit[
        "room_problem"
    ]:

        hypotheses[
            "Проблема с номером или качеством сна"
        ] *= 3.0

        reasons.append(
            "В последнем визите отмечена проблема с номером или комфортом."
        )


    if latest_visit[
        "spa_problem"
    ]:

        hypotheses[
            "Перегруженность spa или неудобное время услуги"
        ] *= 3.0

        reasons.append(
            "Гость сообщил о проблеме со spa или временем услуги."
        )


    if latest_visit[
        "staff_problem"
    ]:

        hypotheses[
            "Проблема с обслуживанием или персоналом"
        ] *= 3.0

        reasons.append(
            "Есть жалобы на очередь, задержки или обслуживание."
        )


    if latest_visit[
        "service_problem"
    ]:

        hypotheses[
            "Проблема с другой услугой"
        ] *= 2.5

        reasons.append(
            "Есть проблема с дополнительной услугой."
        )


    if latest_visit[
        "price_problem"
    ]:

        hypotheses[
            "Ценовая чувствительность гостя"
        ] *= 3.0

        reasons.append(
            "Есть признаки ценовой чувствительности."
        )


    if latest_visit[
        "competitor_problem"
    ]:

        hypotheses[
            "Более сильное предложение конкурента"
        ] *= 3.0

        reasons.append(
            "Есть признаки усиления предложения конкурента."
        )


    if latest_visit[
        "free_text"
    ]:

        reasons.append(
            "Комментарий: "
            + latest_visit[
                "free_text"
            ]
        )


    total = sum(
        hypotheses.values()
    )


    posterior = {
        key:
        value / total

        for key, value
        in hypotheses.items()
    }


    ranking = sorted(
        posterior.items(),
        key=lambda x: x[1],
        reverse=True,
    )


    leading_hypothesis = (
        ranking[0][0]
    )


    leading_confidence = (
        ranking[0][1]
    )


    if negative_transitions >= 3:

        signal_level = (
            "Сильный сигнал"
        )


    elif negative_transitions >= 2:

        signal_level = (
            "Средний сигнал"
        )


    elif abs(
        latest_deviation
    ) >= 0.30:

        signal_level = (
            "Слабый сигнал"
        )


    else:

        signal_level = (
            "Заметного сигнала нет"
        )


    if (
        leading_confidence >= 0.30
        and len(reasons) >= 1
    ):

        recommendation = (
            "Проверить небольшое и обратимое решение, "
            "не меняя весь процесс сразу."
        )


    else:

        recommendation = (
            "Собрать ещё один независимый источник данных "
            "перед изменением процесса."
        )


    return {
        "signal_level":
        signal_level,

        "latest_deviation":
        latest_deviation,

        "negative_transitions":
        negative_transitions,

        "leading_hypothesis":
        leading_hypothesis,

        "leading_confidence":
        leading_confidence,

        "reasons":
        reasons,

        "ranking":
        ranking,

        "recommendation":
        recommendation,
    }


# =========================================================
# ОБЩАЯ СВОДКА ПО ПРЕДПРИЯТИЮ
# =========================================================

def portfolio_summary(
    all_visits,
):

    if not all_visits:

        return {
            "guests": 0,
            "visits": 0,
            "room_problems": 0,
            "spa_problems": 0,
            "staff_problems": 0,
            "price_problems": 0,
        }


    guest_ids = {
        v["guest_id"]
        for v in all_visits
    }


    return {
        "guests":
        len(
            guest_ids
        ),

        "visits":
        len(
            all_visits
        ),

        "room_problems":
        sum(
            v[
                "room_problem"
            ]
            for v in all_visits
        ),

        "spa_problems":
        sum(
            v[
                "spa_problem"
            ]
            for v in all_visits
        ),

        "staff_problems":
        sum(
            v[
                "staff_problem"
            ]
            for v in all_visits
        ),

        "price_problems":
        sum(
            v[
                "price_problem"
            ]
            for v in all_visits
        ),
    }


# =========================================================
# ВХОД / РЕГИСТРАЦИЯ
# =========================================================

if "user" not in st.session_state:

    st.title(
        "◈ SETDS"
    )

    st.write(
        "Войдите в систему "
        "или создайте аккаунт предприятия."
    )


    tab_login, tab_register = st.tabs(
        [
            "Войти",
            "Создать аккаунт",
        ]
    )


    with tab_login:

        login_email = st.text_input(
            "Email",
            key="login_email",
        )

        login_password = st.text_input(
            "Пароль",
            type="password",
            key="login_password",
        )


        if st.button(
            "Войти",
            type="primary",
            use_container_width=True,
        ):

            user = login_user(
                login_email,
                login_password,
            )

            if user:

                st.session_state.user = user

                st.session_state.page = (
                    "Главная"
                )

                st.rerun()

            else:

                st.error(
                    "Неверный email или пароль."
                )


    with tab_register:

        reg_org = st.text_input(
            "Предприятие",
            key="reg_org",
        )

        reg_email = st.text_input(
            "Email",
            key="reg_email",
        )

        reg_password = st.text_input(
            "Пароль",
            type="password",
            key="reg_password",
        )


        if st.button(
            "Создать аккаунт",
            use_container_width=True,
        ):

            if (
                not reg_org.strip()
                or not reg_email.strip()
                or len(
                    reg_password
                ) < 4
            ):

                st.error(
                    "Заполните все поля. "
                    "Пароль — минимум 4 символа."
                )

            else:

                ok, message = register_user(
                    reg_email,
                    reg_password,
                    reg_org,
                )

                if ok:

                    st.success(
                        message
                        + " Теперь войдите."
                    )

                else:

                    st.error(
                        message
                    )


    st.stop()


# =========================================================
# ПОЛЬЗОВАТЕЛЬ ВОШЁЛ
# =========================================================

user = st.session_state.user

user_id = user[
    "user_id"
]


st.title(
    "◈ SETDS"
)


st.caption(
    f"{user['organization']} · "
    f"{user['email']} · "
    f"роль: {user['role']}"
)


navigation = st.radio(
    "Раздел",
    [
        "Главная",
        "Гости",
        "Добавить данные",
        "Анализ",
    ],
    horizontal=True,
)


st.session_state.page = (
    navigation
)


if st.button(
    "Выйти",
):
    logout()


st.divider()


page = st.session_state.page


# =========================================================
# ГЛАВНАЯ
# =========================================================

if page == "Главная":

    all_visits = get_visits(
        user_id
    )


    summary = portfolio_summary(
        all_visits
    )


    st.header(
        "Главная"
    )


    col1, col2 = st.columns(
        2
    )


    col1.metric(
        "Гостей в базе",
        summary[
            "guests"
        ],
    )


    col2.metric(
        "Всего визитов",
        summary[
            "visits"
        ],
    )


    col3, col4 = st.columns(
        2
    )


    col3.metric(
        "Проблемы с номером",
        summary[
            "room_problems"
        ],
    )


    col4.metric(
        "Проблемы со spa",
        summary[
            "spa_problems"
        ],
    )


    col5, col6 = st.columns(
        2
    )


    col5.metric(
        "Проблемы с персоналом",
        summary[
            "staff_problems"
        ],
    )


    col6.metric(
        "Проблемы с ценой",
        summary[
            "price_problems"
        ],
    )


    st.subheader(
        "Что делает система"
    )


    st.write(
        "SETDS сохраняет историю гостей и визитов. "
        "Каждая новая запись становится частью "
        "следующего анализа."
    )


    if not all_visits:

        st.info(
            "Пока данных нет. "
            "Добавьте первого гостя и его визит."
        )


# =========================================================
# ГОСТИ
# =========================================================

elif page == "Гости":

    st.header(
        "Гости"
    )


    guests = get_guests(
        user_id
    )


    if guests:

        for guest in guests:

            visits = get_visits(
                user_id,
                guest[
                    "guest_id"
                ],
            )


            title = (
                f"{guest['guest_code']} — "
                f"{guest['guest_name'] or 'без имени'} "
                f"· визитов: {len(visits)}"
            )


            with st.expander(
                title
            ):

                if guest[
                    "notes"
                ]:

                    st.write(
                        guest[
                            "notes"
                        ]
                    )


                if visits:

                    for visit in visits:

                        rating = (
                            visit[
                                "rating"
                            ]
                            if visit[
                                "rating"
                            ]
                            is not None
                            else "—"
                        )


                        st.write(
                            f"• {visit['visit_date']} "
                            f"· {visit['nights']} ноч. "
                            f"· оценка: {rating}"
                        )


                else:

                    st.caption(
                        "Визитов пока нет."
                    )


    else:

        st.info(
            "Гостей пока нет."
        )


# =========================================================
# ДОБАВИТЬ ДАННЫЕ
# =========================================================

elif page == "Добавить данные":

    st.header(
        "Добавить данные"
    )


    st.subheader(
        "Новый гость"
    )


    guest_code = st.text_input(
        "Код гостя",
        placeholder=(
            "Например: G-105"
        ),
    )


    guest_name = st.text_input(
        "Имя / обозначение",
        placeholder=(
            "Необязательно"
        ),
    )


    guest_notes = st.text_area(
        "Заметка",
        placeholder=(
            "Необязательно"
        ),
    )


    if st.button(
        "Сохранить гостя",
        use_container_width=True,
    ):

        if not guest_code.strip():

            st.error(
                "Введите код гостя."
            )

        else:

            ok, message = create_guest(
                user_id,
                guest_code,
                guest_name,
                guest_notes,
            )

            if ok:

                st.success(
                    message
                )

                st.rerun()

            else:

                st.error(
                    message
                )


    st.divider()


    st.subheader(
        "Новый визит"
    )


    guests = get_guests(
        user_id
    )


    if not guests:

        st.info(
            "Сначала добавьте хотя бы одного гостя."
        )


    else:

        guest_map = {
            (
                f"{guest['guest_code']} — "
                f"{guest['guest_name'] or 'без имени'}"
            ):
            guest[
                "guest_id"
            ]

            for guest
            in guests
        }


        selected_label = st.selectbox(
            "Гость",
            list(
                guest_map.keys()
            ),
        )


        selected_guest_id = guest_map[
            selected_label
        ]


        visit_date = st.date_input(
            "Дата визита"
        )


        nights = st.number_input(
            "Ночей",
            min_value=1,
            value=1,
            step=1,
        )


        rating = st.number_input(
            "Оценка 0–10",
            min_value=0,
            max_value=10,
            value=8,
            step=1,
        )


        st.subheader(
            "Что известно по этому визиту?"
        )


        spa_used = st.checkbox(
            "Использовал spa"
        )


        room_problem = st.checkbox(
            "Проблема с номером / сном"
        )


        spa_problem = st.checkbox(
            "Проблема со spa / временем услуги"
        )


        service_problem = st.checkbox(
            "Проблема с другой услугой"
        )


        staff_problem = st.checkbox(
            "Проблема с обслуживанием / персоналом"
        )


        price_problem = st.checkbox(
            "Проблема с ценой"
        )


        competitor_problem = st.checkbox(
            "Есть конкурентный фактор"
        )


        free_text = st.text_area(
            "Комментарий / отзыв / другой факт",
            placeholder=(
                "Например: ночью было шумно "
                "и гость плохо спал"
            ),
        )


        facts = {
            "spa_used":
            spa_used,

            "room_problem":
            room_problem,

            "spa_problem":
            spa_problem,

            "service_problem":
            service_problem,

            "staff_problem":
            staff_problem,

            "price_problem":
            price_problem,

            "competitor_problem":
            competitor_problem,
        }


        if st.button(
            "Сохранить визит",
            type="primary",
            use_container_width=True,
        ):

            add_visit(
                user_id,
                selected_guest_id,
                visit_date,
                nights,
                rating,
                facts,
                free_text,
            )


            st.success(
                "Визит сохранён. "
                "Он уже участвует в анализе."
            )


# =========================================================
# АНАЛИЗ
# =========================================================

elif page == "Анализ":

    st.header(
        "Анализ"
    )


    guests = get_guests(
        user_id
    )


    if not guests:

        st.info(
            "Сначала добавьте гостей и визиты."
        )


    else:

        guest_map = {
            (
                f"{guest['guest_code']} — "
                f"{guest['guest_name'] or 'без имени'}"
            ):
            guest

            for guest
            in guests
        }


        selected_label = st.selectbox(
            "Выберите гостя",
            list(
                guest_map.keys()
            ),
        )


        guest = guest_map[
            selected_label
        ]


        visits = get_visits(
            user_id,
            guest[
                "guest_id"
            ],
        )


        st.write(
            f"Визитов в истории: "
            f"**{len(visits)}**"
        )


        if len(
            visits
        ) < 2:

            st.info(
                "Для анализа динамики "
                "нужно минимум два визита."
            )


        else:

            result = analyze_guest(
                visits
            )


            st.subheader(
                "Что произошло"
            )


            st.metric(
                "Сила сигнала",
                result[
                    "signal_level"
                ],
            )


            st.metric(
                "Последнее изменение длительности",
                f"{result['latest_deviation']:.0%}",
            )


            st.subheader(
                "Наиболее вероятное объяснение"
            )


            st.info(
                result[
                    "leading_hypothesis"
                ]
            )


            st.write(
                "Условная поддержка: "
                f"**{result['leading_confidence']:.0%}**"
            )


            st.caption(
                "Это не доказанная причина, "
                "а версия, лучше всего "
                "соответствующая текущим данным."
            )


            st.subheader(
                "Почему"
            )


            if result[
                "reasons"
            ]:

                for reason in result[
                    "reasons"
                ]:

                    st.write(
                        "• "
                        + reason
                    )


            else:

                st.write(
                    "Дополнительных подтверждений пока нет."
                )


            st.subheader(
                "Что делать сейчас"
            )


            st.success(
                result[
                    "recommendation"
                ]
            )


            with st.expander(
                "Другие возможные причины"
            ):

                for (
                    hypothesis,
                    confidence,
                ) in result[
                    "ranking"
                ]:

                    st.write(
                        f"**{hypothesis}** — "
                        f"{confidence:.0%}"
                    )


            if st.button(
                "Сохранить этот вывод",
                use_container_width=True,
            ):

                decision_id = save_decision(
                    user_id,
                    guest[
                        "guest_id"
                    ],
                    result[
                        "signal_level"
                    ],
                    result[
                        "leading_hypothesis"
                    ],
                    result[
                        "recommendation"
                    ],
                )


                st.session_state.last_decision_id = (
                    decision_id
                )


                st.success(
                    "Вывод сохранён в истории решений."
                )


            st.subheader(
                "Вы уже попробовали предложенный вариант?"
            )


            if st.button(
                "Помогло",
                use_container_width=True,
            ):

                if (
                    "last_decision_id"
                    in st.session_state
                ):

                    update_decision_feedback(
                        st.session_state.last_decision_id,
                        "helped",
                    )


                st.success(
                    "Результат сохранён: помогло."
                )


            if st.button(
                "Не помогло",
                use_container_width=True,
            ):

                if (
                    "last_decision_id"
                    in st.session_state
                ):

                    update_decision_feedback(
                        st.session_state.last_decision_id,
                        "failed",
                    )


                st.error(
                    "Результат сохранён: не помогло."
                )


            if st.button(
                "Пока непонятно",
                use_container_width=True,
            ):

                if (
                    "last_decision_id"
                    in st.session_state
                ):

                    update_decision_feedback(
                        st.session_state.last_decision_id,
                        "unclear",
                    )


                st.warning(
                    "Результат сохранён: пока непонятно."
                )


# =========================================================
# ПОДВАЛ
# =========================================================

st.divider()

st.caption(
    "SETDS MVP: "
    "аккаунт → накопление данных → "
    "история гостей → анализ → "
    "сохранение решений"
)
