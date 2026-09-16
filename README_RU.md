# SETDS Streamlit v10 — рабочая интерактивная demo-программа

## Самый простой запуск

### Windows
1. Распакуйте архив.
2. Дважды нажмите `START_SETDS_WINDOWS.bat`.
3. При первом запуске Python сам установит `streamlit` и `pandas`.
4. Откроется браузер на `http://localhost:8501`.

### macOS
1. Распакуйте архив.
2. Откройте Terminal в папке или дважды нажмите `START_SETDS_MAC.command`.
3. Если macOS блокирует файл: правой кнопкой → Open.
4. Откроется `http://localhost:8501`.

### Универсально
```bash
python launch_setds.py
```

## Что реально работает

- навигация по разделам;
- reset demo;
- guest trajectory 6 → 3 → 2;
- evidence log и causal hypotheses;
- employee context;
- интерактивный Relative Competitive Gap;
- выбор владельцем действия;
- Verify → Test;
- запись validated / failed / inconclusive pilot outcome;
- Pilot_validated / Pilot_failed / Reassess;
- Implement только после допустимой цепочки;
- stop action;
- Decision Memory;
- сценарии 0–1 / 1–3 / 3–5 / 5–10 лет.

## Важно

Это демонстрационный научный прототип. Seed-данные и вероятности иллюстративные и не являются эмпирическими оценками Altair.
