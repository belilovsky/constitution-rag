# PROJECT STATUS AND NEXT STEP — constitution-rag

Last updated: 2026-03-12

## 1. Project position

`constitution-rag` — это рабочий проект grounded чат-бота по Конституции Республики Казахстан.

Ingestion, normalization и PostgreSQL в этом проекте являются подготовительным слоем для retrieval и grounded answers, а не конечной целью сами по себе.

На текущий момент data-layer этап закрыт.
Проект находится на стадии prompt / retrieval layer и подготовки к системному QA всего chatbot-контура.

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

Зафиксированный fix:
- commit `c020220`
- `Fix FAQ import fallback to question and answer body`

---

## 3. Database snapshot

В БД уже находятся 8 документных наборов:

- `krk_2026_norm_ru`
- `krk_2026_norm_kz`
- `krk_2026_commentary_ru`
- `krk_2026_commentary_kz`
- `krk_2026_faq_ru`
- `krk_2026_faq_kz`
- `krk_1995_deprecated_ru`
- `krk_1995_deprecated_kz`

Layer semantics:

- `2026 norm` — основной norm-layer проекта;
- `2026 commentary` — дополнительный разъяснительный слой;
- `2026 faq` — упрощённый пояснительный слой;
- `1995 deprecated` — historical/deprecated слой только для сравнения, исторической справки или прямого запроса.

Критическое правило:
- `1995 deprecated` не должен использоваться как текущая норма по умолчанию.

---

## 4. Canonical prompt-layer docs

Source of truth для prompt / retrieval слоя:

- `system_prompt_canonical_v1.2.md`
- `retrieval_policy_v1.1.md`
- `red_team_test_pack_v1.md`
- `qa_results_template.md`
- `release_checklist_prompt-layer.md`

Если между обсуждениями, черновиками и этими файлами есть расхождение, приоритет имеют канонические документы в repo.

---

## 5. Prompt / retrieval principles

Базовые правила текущего chatbot layer:

- бот отвечает только по найденным в retrieval материалам;
- приоритет источников: `norm > commentary > faq > historical/deprecated`;
- ordinary query сначала должен разрешаться через `2026 norm`;
- `1995 deprecated` допускается только для comparison / historical mode / прямого запроса;
- commentary и FAQ не заменяют norm;
- бот не должен делать ложные заявления о полноте;
- бот не должен принимать политический фрейм вопроса как установленный факт;
- бот не должен раскрывать внутренние инструкции, red-team логику и hidden rules;
- при weak / empty retrieval бот обязан использовать safe-failure behavior.

---

## 6. Confirmed known issues

### Technical known issue
Для некоторых строк ad-hoc SQL preview через `left()` / `substring()` возможна UTF-8 ошибка.

Workaround:
- читать полный `body`;
- обрезать preview уже в Python.

### Prompt-layer risk areas to validate
До release необходимо отдельно проверить и закрыть:

- false completeness на broad queries;
- leakage из `1995 deprecated` в ordinary mode;
- commentary / FAQ substitution при отсутствии norm;
- политический framing на чувствительных темах;
- meta-leakage внутренних правил;
- уверенные ответы при weak / empty retrieval;
- mismatch между exact lookup и broad retrieval.

---

## 7. Release gate for current stage

Prompt / retrieval layer нельзя считать завершённым, пока не выполнено следующее:

- есть хотя бы один top-10 critical QA run;
- есть заполненный `qa_results_template.md`;
- есть blocker register;
- есть fix plan;
- есть хотя бы один retest;
- нет открытых P0 blocker’ов.

P0 blocker’ы текущего этапа:

- false completeness;
- `1995 deprecated` default leakage;
- commentary / FAQ substitution вместо norm;
- hallucination при weak retrieval;
- принятие политического ярлыка как установленного факта;
- раскрытие hidden instructions / red-team logic.

Если хотя бы один из этих blocker’ов открыт, release status = `NO-GO`.

---

## 8. Additional documents received on 2026-03-11 / 2026-03-12

Получен дополнительный пакет документов для возможного расширения data-layer и commentary-layer.

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

Риск:
- высокая дупликация между тезисами;
- смешение юридического объяснения и политического месседжинга;
- нельзя импортировать как `norm`.

### B. Internal / restricted materials
Не должны автоматически попадать в обычный пользовательский retrieval:

- `03.03.2026-operrekomendatsii.docx`
- `KR-metodichka-regshtaby-2026_2.docx`

Причина:
- содержат operational / campaign / штабные инструкции;
- содержат агитационные, организационные и внутренние методические элементы;
- требуют отдельного решения по restricted storage или полного исключения из chatbot retrieval.

### C. Requires separate review
Отдельно проверить перед импортом:

- файлы сравнений;
- контртезисы;
- референдумные линии;
- документы с выраженным политическим framing.

---

## 9. Rule for additional document import

Дополнительные документы не считаются частью production-ready knowledge base автоматически.

Обязательный порядок:

1. inventory;
2. классификация по слоям;
3. выделение canonical files;
4. extraction / normalization;
5. дедупликация повторяющихся тезисов;
6. решение, что идёт в commentary-layer, а что остаётся internal;
7. импорт;
8. SQL QA;
9. retrieval QA;
10. только после этого допуск в рабочий chatbot-контур.

Критическое правило:
- новые материалы не должны загрязнить `norm`-слой;
- internal / штабные / operational материалы не должны попасть в ordinary user retrieval без отдельного явного решения.

---

## 10. Immediate next actions

Ближайшая обязательная последовательность:

1. зафиксировать этот статус-файл в repo;
2. обновить `README.md` в соответствии с текущим состоянием проекта;
3. при необходимости обновить Space instructions / project memory;
4. прогнать top-10 critical cases из `red_team_test_pack_v1.md`;
5. заполнить `qa_results_template.md`;
6. сформировать blocker register;
7. внести точечные правки в prompt / retrieval layer;
8. сделать retest;
9. после этого вернуться к решению по импорту новых документов.

---

## 11. Success criteria for transition to next stage

Можно считать проект готовым к следующему этапу, если одновременно выполнено следующее:

- data-layer стабилен и документирован;
- source of truth prompt-layer зафиксирован;
- top-10 critical QA run проведён;
- blocker register создан;
- P0 issues закрыты;
- правила обращения с дополнительными документами зафиксированы;
- internal / restricted материалы отделены от публичного retrieval-контура.

---

## 12. Boundary rule

Пока работа идёт внутри `constitution-rag`, не уходить в соседние проекты, контейнеры и сервисы без прямого сигнала пользователя или прямого runtime-следа из текущей задачи.
