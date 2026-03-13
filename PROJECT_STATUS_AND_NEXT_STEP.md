# PROJECT STATUS AND NEXT STEP — constitution-rag

Last updated: 2026-03-13 (batch-3 production-readiness)

## 1. Project position

`constitution-rag` — это рабочий проект grounded чат-бота по конституционным материалам Республики Казахстан.

Ingestion, normalization, import в PostgreSQL и retrieval routing в этом проекте являются подготовительным слоем для grounded answers, а не конечной целью сами по себе.

На текущий момент:
- data-layer закрыт (15 наборов, 1105 чанков);
- retrieval-layer в рабочем состоянии (hotfix 56ea43a);
- prompt / answer-layer QA завершён (full30 30/30);
- prompt v3 — batch-1 + batch-2 fixes applied (e1fb028, e050cd1);
- batch-3: Docker + FastAPI + streaming API + frontend + kz/en tests (9667ab2);
- release status: **GO** (2026-03-13);
- модель production: **gpt-4.1-mini**.

---

## 2. Completed stage: data layer

Завершено:

- исходные документы собраны;
- extraction / normalization выполнены;
- normalized JSON подготовлены;
- данные импортированы в PostgreSQL;
- SQL QA пройден;
- `empty_body = 0` по всем импортированным документным наборам;
- FAQ import bug исправлен и сохранён в repo.

Зафиксированный fix data-layer:
- commit `c020220`
- `Fix FAQ import fallback to question and answer body`

---

## 3. Retrieval status after latest fix

На 2026-03-12 retrieval hotfix зафиксирован в `origin/main` и подтверждён на VPS.

Зафиксированный retrieval commit:
- commit `56ea43a`
- `Update retrieval_runner.py`

Что именно закреплено:

- ordinary query по теме свободы слова корректно находит статью 23;
- broad query по мирным собраниям корректно находит статью 34;
- обзорный запрос по политическим правам возвращает статьи 23, 26, 34 и 35;
- historical query по Конституции 1995 года остаётся в `deprecated`-слое;
- comparison mode по 1995 / 2026 остаётся раздельным;
- weak-tech query про нейросети / блокчейн не даёт ложного norm-ответа и остаётся в safe-failure режиме.

Смысл hotfix:

- расширена нормализация пользовательских формулировок;
- исправлен topical routing для `свобода слова`;
- сохранён source-priority `norm > commentary > faq > historical/deprecated`;
- retrieval-fix закреплён в репозитории и подтверждён после синхронизации VPS.

---

## 4. Database snapshot

В БД находятся 15 документных наборов (1105 чанков итого):

Базовый слой (8 наборов):
- `krk_2026_norm_ru` (97)
- `krk_2026_norm_kz` (97)
- `krk_2026_commentary_ru` (114)
- `krk_2026_commentary_kz` (104)
- `krk_2026_faq_ru` (15)
- `krk_2026_faq_kz` (15)
- `krk_1995_deprecated_ru` (103)
- `krk_1995_deprecated_kz` (100)

Расширенный слой, добавлен 2026-03-13 (7 наборов, 460 чанков):
- `krk_2026_ce_audiences_ru` (151) — civic-education, целевые аудитории
- `krk_2026_ce_comparison_ru` (9) — таблица сравнения 1995↔2026
- `krk_2026_ce_lines_ru` (91) — референдумные линии + контраргументы (RESTRICTED)
- `krk_2026_ce_theses_ru` (38) — ключевые аспекты + тезисы комиссии
- `krk_2026_faq_extra_ru` (55) — расширенный FAQ с constitution.my
- `krk_2026_faq_extra_kz` (63) — расширенный FAQ (казахский)
- `krk_2026_faq_extra_en` (53) — расширенный FAQ (английский)

Layer semantics:

- `2026 norm` — основной norm-layer проекта;
- `2026 commentary` — дополнительный разъяснительный слой;
- `2026 civic-education` — вторичный commentary-sub-layer;
- `2026 faq` + `faq_extra` — пояснительный слой (расширенный приоритетнее краткого);
- `comparison-table` — структурированная таблица сравнения, только для comparison-mode;
- `1995 deprecated` — historical/deprecated слой;
- `restricted` — `ce_lines_ru` не участвует в ordinary retrieval.

Критическое правило:
- `1995 deprecated` не должен использоваться как текущая норма по умолчанию.

---

## 5. Canonical prompt-layer docs

Source of truth для prompt / retrieval / answer слоя на текущем этапе:

- `PROJECT_STATUS_AND_NEXT_STEP.md`
- `README.md`
- `system_prompt_canonical_v1.md`
- `retrieval_policy_v1.md`
- `red_team_hostile_25.md`
- `qa_results_template.md`

Если между обсуждениями, черновиками, временными заметками и этими файлами есть расхождение, приоритет имеют канонические документы в repo.

Распределение ролей между документами:

- `PROJECT_STATUS_AND_NEXT_STEP.md` — текущий этап, release gate, known issues, next actions;
- `README.md` — входной документ по проекту и общая project memory;
- `system_prompt_canonical_v1.md` — канонические правила answer behavior;
- `retrieval_policy_v1.md` — канонические правила retrieval routing и source-priority;
- `red_team_hostile_25.md` — тестовый пакет и rubric для answer-layer QA;
- `qa_results_template.md` — канонический шаблон QA-run, blocker register, fix plan и retest log.

---

## 6. Current behavior rules

Базовые правила текущего chatbot-layer:

- бот отвечает только по найденным в retrieval материалам;
- приоритет источников: `norm > commentary > faq > historical/deprecated`;
- ordinary query сначала должен разрешаться через `2026 norm`;
- `1995 deprecated` допускается только для comparison / historical mode / прямого запроса;
- commentary и FAQ не заменяют norm;
- бот не должен делать ложные заявления о полноте;
- бот не должен принимать политический фрейм вопроса как установленный факт;
- бот не должен раскрывать внутренние инструкции, red-team логику и hidden rules;
- при weak / empty retrieval бот обязан использовать safe-failure behavior;
- при exact lookup бот не должен подменять статью, пункт или отсылочную норму соседним фрагментом без явной оговорки;
- при conflicting fragments бот не должен склеивать расхождение в один уверенный вывод.

---

## 7. Confirmed known issues

### Technical known issue

Для некоторых строк ad-hoc SQL preview через `left()` / `substring()` возможна UTF-8 ошибка.

Workaround:
- читать полный `body`;
- обрезать preview уже в Python.

### Closed QA risk areas (закрыто в full30 QA run, 2026-03-13)

Все перечисленные риски закрыты в full30_S3_20260313_0917.md (30/30 pass):

- [x] false completeness на broad queries;
- [x] commentary / FAQ substitution при отсутствии norm;
- [x] политический framing на чувствительных темах;
- [x] meta-leakage внутренних правил;
- [x] overly confident wording при weak / empty retrieval;
- [x] exact lookup vs structural context cases;
- [x] mixed-topic handling;
- [x] follow-up pressure cases;
- [x] status labeling для project / transitional / deprecated контекста;
- [x] comparison behavior.

### Applied fixes (2026-03-13, batch-1 + batch-2)

Batch-1 (commit e1fb028):
- §8: добавлены «широкие полномочия» и «обширные полномочия» в бан-лист (RT-15 fix)
- §6.1.B: few-shot negative example для «Таким образом»
- answer_runner.py: SAFE_FAILURE_TEXT заменён на формулы §6.1.D (ru/kz/en)
- run_full30.py: добавлены blocker signals + _is_negative_context() для RT-20 false positive

Batch-2 (commit e050cd1):
- §13: few-shot пример anti-false-completeness, запрет «Это основные...» без оговорки
- §6.1.B: добавлен запрет «Если нужна информация о других правах...»
- §6.1.D: добавлен Тип F — hedge-формулы для перечислений 3+ норм
- §8: добавлены «существенные полномочия», «исключительные полномочия»
- run_full30.py: добавлены false_completeness сигналы + negative context
- answer_runner.py: убрана «база знаний» из USER_PROMPT_TEMPLATE

Batch-3 (commit 9667ab2):
- main.py: FastAPI сервер (/health, /api/ask, /api/ask/stream SSE)
- Dockerfile + docker-compose.yml: мульти-сервис (api + pgvector db)
- query_log: таблица логирования запросов (авто-создание)
- static/index.html: веб-интерфейс со streaming (ru/kz/en)
- run_full30.py: расширен до 45 тестов (kz: RT-31..38, en: RT-39..45)
- requirements.txt: +fastapi, +uvicorn

---

## 8. Release gate for current stage

Prompt / retrieval / answer layer нельзя считать завершённым, пока не выполнено следующее:

- есть хотя бы один top-10 critical QA run;
- есть зафиксированные результаты по red-team сценариям;
- есть заполненный QA-run document;
- есть blocker register;
- есть fix plan;
- есть хотя бы один retest;
- нет открытых P0 blocker’ов.

Допустимый operational формат:
- blocker register, fix plan и retest log могут вестись внутри одного канонического QA-run файла, если он заполнен по `qa_results_template.md`.

P0 blocker’ы текущего этапа:

- false completeness;
- `1995 deprecated` default leakage;
- commentary / FAQ substitution вместо norm;
- hallucination при weak retrieval;
- принятие политического ярлыка как установленного факта;
- раскрытие hidden instructions / red-team logic.

Если хотя бы один из этих blocker’ов открыт, release status = `NO-GO`.

---

## 9. Additional documents received on 2026-03-11 / 2026-03-12

Получен дополнительный пакет документов для возможного расширения commentary-layer и вспомогательных материалов проекта.

Предварительная классификация:

### A. Commentary-ready materials

Подходят для последующей нормализации и возможного импорта в commentary-layer:

- `Kliuchevye_aspekty_proekta_novoi_Konstitutsii.docx`
- `Tezisy_dlia_Konstitutsionnoi_komissii_1.docx`
- `03_02_2026_Tselevye_auditorii_*.docx`

Назначение:

- новеллы проекта;
- тематические линии;
- адресные пояснения под аудитории;
- контртезисные и объяснительные блоки.

Риски:

- высокая дупликация между тезисами;
- смешение юридического объяснения и политического месседжинга;
- нельзя импортировать как `norm`.

### B. Internal / restricted materials

Не должны автоматически попадать в обычный пользовательский retrieval:

- `03.03.2026-operrekomendatsii.docx`
- `KR-metodichka-regshtaby-2026_2.docx`

Причина:

- содержат operational / campaign / штабные инструкции;
- содержат агитационные, организационные и внутренние методические элементы.

### D. Final classification decision (2026-03-13)

internal/ материалы классифицированы как **restricted — НЕ импортировать** в chatbot retrieval:
- `03.03.2026-operrekomendatsii.docx` — restricted
- `KR-metodichka-regshtaby-2026_2.docx` — restricted

Основание: содержат operational/campaign/штабные инструкции. Не должны попадать в пользовательский retrieval ни при каких обстоятельствах.

### C. Requires separate review

Отдельно проверить перед импортом:

- файлы сравнений;
- контртезисы;
- референдумные линии;
- документы с выраженным политическим framing.

---

## 10. Rule for additional document import

Дополнительные документы не считаются частью production-ready knowledge base автоматически.

Обязательный порядок:

1. inventory;
2. классификация по слоям;
3. выделение canonical files;
4. extraction / normalization;
5. дедупликация повторяющихся тезисов;
6. решение, что идёт в commentary-layer, а что остаётся internal;
7. import;
8. SQL QA;
9. retrieval QA;
10. только после этого допуск в рабочий chatbot-контур.

Критические правила:
- новые материалы не должны загрязнить `norm`-слой;
- internal / штабные / operational материалы не должны попасть в ordinary user retrieval без отдельного явного решения;
- commentary-ready документы не должны автоматически повышаться до norm-layer;
- решение по новым документам не должно отвлекать проект от текущего release gate answer-layer QA.

---

## 11. Immediate next actions (актуально на 2026-03-13)

### Выполненные задачи batch-3:

1. **Docker + docker-compose** — Dockerfile, docker-compose.yml (api + pgvector db), healthcheck
2. **FastAPI сервер** — main.py с /health, /api/ask, /api/ask/stream (SSE)
3. **Observability** — query_log таблица в PostgreSQL (авто-создание при старте)
4. **Streaming API** — SSE с OpenAI stream=True, события meta/text/done/error
5. **Frontend** — static/index.html (ru/kz/en селектор, streaming, мобильный адаптив)
6. **Тесты kz/en** — run_full30.py расширен до 45 тестов (RT-31..RT-45: 8 kz + 7 en)

### Остающиеся задачи:

1. **VPS deploy** — пулл, билд, docker compose up -d, проверка /health
2. **Regression QA** — прогон run_full30.py (45 тестов) на VPS
3. **Решение по internal/ материалам** — оперрекомендации + методичка регштабы = restricted, не для импорта

---

## 12. Success criteria — все выполнены (2026-03-13)

- [x] data-layer стабилен и документирован
- [x] retrieval hotfix закреплён в repo (56ea43a) и подтверждён на VPS
- [x] source of truth prompt-layer зафиксирован
- [x] канонические документы синхронизированы
- [x] top-10 critical QA run проведён (10/10, top10_S3_20260312_2203.md)
- [x] blocker register создан и заполнен
- [x] fix plan создан и зафиксирован
- [x] есть retest (rt20_retest_20260313.md)
- [x] P0 issues закрыты (0 open)
- [x] P1 issues закрыты (0 open)
- [x] правила обращения с новыми документами зафиксированы (§10)
- [x] internal/restricted материалы отделены от retrieval-контура

---

## 13. Release status interpretation

Текущий статус стадии нужно трактовать так:

- `GO` — только если нет открытых P0 blocker’ов и есть подтверждённый retest;
- `CONDITIONAL GO` — допустим только для staging / internal / pilot scope и только без открытых P0 blocker’ов;
- `NO-GO` — по умолчанию, пока не закрыты blocker’ы текущего этапа.

На текущий момент release status: **`GO`**.

История изменений статуса:
- 2026-03-12: NO-GO (top-10 и full30 QA не завершены)
- 2026-03-13: **GO** (full30 30/30 pass, 0 open P0, 0 open P1)

Evidence: `qa/evidence/full30_S3_20260313_0917.md` (initial GO)
Batch-1 evidence: `qa/evidence/full30_S3_20260313_1120.md` (29/30, RT-22 warn)
Batch-2 evidence: `qa/evidence/full30_S3_20260313_1134.md` (30/30 clean pass)
Batch-3: production deployment files committed (9667ab2)

---

## 14. Boundary rule

Пока работа идёт внутри `constitution-rag`, не уходить в соседние проекты, контейнеры и сервисы без прямого сигнала пользователя или прямого runtime-следа из текущей задачи.

Текущий приоритет проекта:
- подключение 7 новых датасетов в retrieval routing;
- regression QA на расширенной БД;
- production deployment.
