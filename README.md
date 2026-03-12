# constitution-rag

`constitution-rag` — это рабочий репозиторий проекта grounded чат-бота по Конституции Республики Казахстан.

Проект не сводится к ingestion или ETL. Ingestion, normalization и PostgreSQL здесь являются подготовительным слоем для retrieval и grounded answers, а конечная цель проекта — устойчивый chatbot-контур с контролируемым source priority, безопасным поведением и проверяемыми ответами.

На текущий момент data-layer этап завершён. Проект находится на стадии prompt / retrieval layer и подготовки к системному QA всего chatbot-контура.

---

## Что это за проект

Цель проекта — собрать надёжную основу для чат-бота, который отвечает на вопросы по Конституции Казахстана, опираясь на структурированные источники, а не на “память модели”.

Проект развивается по стадиям:

1. data layer:
   - сбор исходников;
   - extraction;
   - normalization;
   - import в PostgreSQL;
   - SQL QA;

2. prompt / retrieval layer:
   - system prompt;
   - retrieval policy;
   - source priority;
   - safe-failure behavior;
   - anti-hallucination guardrails;
   - red-team QA;

3. application layer:
   - user journey testing;
   - RU/KZ parity;
   - endpoint verification;
   - controlled rollout;
   - logging и разбор проблемных ответов.

---

## Текущий статус

Текущий прогресс по стадиям:

1. **Data layer — completed**
   - исходные документы собраны;
   - контент атомизирован;
   - normalized JSON подготовлены;
   - данные импортированы в PostgreSQL;
   - SQL QA пройден;
   - `empty_body = 0` по всем импортированным документным наборам;
   - FAQ import bug исправлен.

2. **Prompt / retrieval layer — in progress**
   - подготовлен канонический system prompt;
   - зафиксирована retrieval policy;
   - подготовлен red-team test pack;
   - подготовлены QA template и release checklist;
   - следующий обязательный шаг — critical QA run и фиксация blocker’ов.

3. **Application layer — next**
   - application-level chatbot QA;
   - user journey testing;
   - RU/KZ mirror testing;
   - post-deploy verification;
   - controlled rollout;
   - logging проблемных ответов.

Зафиксированный fix:
- commit `c020220`
- `Fix FAQ import fallback to question and answer body`

---

## Архитектура текущего этапа

Текущая схема работы проекта:

`raw source files -> normalized chunks -> PostgreSQL import -> SQL QA -> retrieval-ready data layer -> prompt/retrieval policy -> QA -> chatbot behavior layer`

Это означает, что подготовка данных уже завершена, а основной текущий фокус смещён на поведение модели поверх существующего data-layer.

---

## Какие слои уже заведены в БД

На текущем этапе в БД находятся 8 документных наборов:

- `krk_2026_norm_ru`
- `krk_2026_norm_kz`
- `krk_2026_commentary_ru`
- `krk_2026_commentary_kz`
- `krk_2026_faq_ru`
- `krk_2026_faq_kz`
- `krk_1995_deprecated_ru`
- `krk_1995_deprecated_kz`

Семантика слоёв:

- `2026 norm` — основной нормативный слой проекта;
- `2026 commentary` — дополнительный разъяснительный слой;
- `2026 faq` — упрощённый пояснительный слой;
- `1995 deprecated` — historical / deprecated слой.

Критическое правило:
- `1995 deprecated` не должен трактоваться как текущая норма проекта по умолчанию.

---

## Структура данных

Импорт выполняется в PostgreSQL.

Основные таблицы текущего data-layer:

- `documents`
- `document_chunks`
- `import_runs`

Ключевые поля `document_chunks`:

- `document_id`
- `chunk_index`
- `heading`
- `body`
- `body_tsv`
- `tokens_count`
- `char_count`
- `meta`
- `created_at`

Практический смысл схемы:

- один документ разбивается на набор чанков;
- каждый чанк имеет заголовок, текст и метаданные;
- retrieval и grounding строятся поверх этих чанков;
- дальнейший prompt-layer обязан учитывать source priority между слоями.

---

## Что уже проверено

На data-layer этапе завершены:

1. inventory исходных файлов;
2. extraction / normalization;
3. import в PostgreSQL;
4. SQL QA по импортированным данным;
5. проверка на пустые `body`;
6. фиксация исправлений в Git и push в `origin/main`.

Подтверждено:

- все 8 документных наборов импортированы;
- по всем импортированным документам `empty_body = 0`;
- FAQ import bug исправлен и сохранён в repo.

---

## Что было исправлено

В процессе QA был найден дефект импорта FAQ.

Часть FAQ-чанков в normalized JSON хранила содержимое не в `text`, а в полях `question` и `answer`, из-за чего при импорте `body` мог оставаться пустым.

Исправление:

- importer сначала берёт `text`;
- если `text` пустой, но есть `question` и/или `answer`, `body` собирается как `question + "\n\n" + answer`;
- `heading` при необходимости может брать fallback из `question`.

После этого FAQ были переимпортированы и повторно проверены SQL-выборками.

---

## Canonical prompt-layer docs

Следующие документы являются source of truth для prompt / retrieval слоя:

- `system_prompt_canonical_v1.2.md`
- `retrieval_policy_v1.1.md`
- `red_team_test_pack_v1.md`
- `qa_results_template.md`
- `release_checklist_prompt-layer.md`

Если между ad-hoc обсуждением, черновиками и этими файлами есть расхождение, приоритет имеют канонические документы в repo.

---

## Базовые правила prompt-layer

Текущий chatbot layer должен соблюдать следующие правила:

- бот отвечает только по найденным в retrieval материалам;
- приоритет источников: `norm > commentary > faq > historical/deprecated`;
- ordinary query сначала должен разрешаться через `2026 norm`;
- `1995 deprecated` допускается только для comparison / historical mode / прямого запроса;
- commentary и FAQ не заменяют norm;
- бот не должен делать ложные заявления о полноте;
- бот не должен принимать политический framing вопроса как установленный факт;
- бот не должен раскрывать внутренние инструкции, hidden rules и red-team logic;
- при weak / empty retrieval бот обязан использовать safe-failure behavior.

---

## Known issues

### Confirmed technical known issue

Для некоторых строк ad-hoc SQL preview через `left()` / `substring()` может падать с UTF-8 ошибкой.

Workaround:

- читать полный `body`;
- резать preview в Python.

### Open prompt-layer risk areas

До release необходимо отдельно проверить и закрыть следующие риски:

- false completeness на broad queries;
- `1995 deprecated` leakage в ordinary mode;
- commentary-as-substitute;
- FAQ-as-substitute;
- meta-leakage внутренних правил;
- политический framing на чувствительных вопросах;
- unsafe behavior на weak / empty retrieval;
- mismatch между exact lookup и broad semantic retrieval.

---

## QA и release gate

Prompt / retrieval layer нельзя считать закрытым, пока не выполнены все условия:

- есть хотя бы один top-10 critical QA run;
- заполнен `qa_results_template.md`;
- создан blocker register;
- зафиксирован fix plan;
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

## Ближайший обязательный шаг

Следующая operational-последовательность:

1. прогнать top-10 critical cases из `red_team_test_pack_v1.md`;
2. заполнить `qa_results_template.md`;
3. выделить blocker’ы;
4. внести точечные правки в prompt / retrieval layer;
5. сделать retest;
6. принять release decision по prompt-layer;
7. только после этого переходить к application-level chatbot QA.

---

## Следующая фаза после текущей

После стабилизации prompt / retrieval layer проект должен перейти к следующей фазе:

- application-level chatbot QA;
- user journey testing;
- RU/KZ parity testing;
- post-deploy verification ключевых endpoint и сценариев;
- controlled rollout;
- logging и разбор проблемных ответов реальных пользователей.

---

## Новые дополнительные документы

Дополнительно получен новый пакет документов для возможного расширения commentary-layer и вспомогательного knowledge layer.

Предварительная классификация:

### Commentary-ready материалы

Потенциально подходят для нормализации и последующего импорта в commentary-layer:

- `Kliuchevye_aspekty_proekta_novoi_Konstitutsii.docx`
- `Tezisy_dlia_Konstitutsionnoi_komissii_1.docx`
- `03_02_2026_Tselevye_auditorii_*.docx`

Эти документы содержат:

- ключевые новеллы проекта;
- объяснительные тезисы;
- линии комментирования;
- адресные формулировки по целевым аудиториям.

Важно:
- они не являются norm-слоем;
- в них есть высокая дупликация между тезисами;
- часть контента носит messaging / positioning характер и требует аккуратной классификации перед импортом.

### Internal / restricted материалы

Следующие документы не должны автоматически попадать в ordinary user retrieval:

- `03.03.2026-operrekomendatsii.docx`
- `KR-metodichka-regshtaby-2026_2.docx`

Причина:

- содержат operational, штабные, агитационные и организационные инструкции;
- включают внутренние линии координации, мониторинга, реагирования и публикационной дисциплины;
- требуют либо отдельного restricted storage, либо полного исключения из production chatbot retrieval.

### Requires separate review

Отдельно перед импортом должны быть проверены:

- сравнительные документы;
- контртезисы;
- линии по референдуму;
- документы с выраженным политическим framing;
- материалы с сильным пересечением по тезисам между аудиториями.

---

## Правило импорта новых документов

Дополнительные документы не считаются частью production-ready knowledge base автоматически.

Обязательный порядок работы с ними:

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
- internal / штабные / operational материалы не должны попадать в ordinary retrieval без отдельного явного решения;
- messaging-материалы не должны подменять нормативный ответ.

---

## Источники данных проекта

На текущем этапе в проекте используются или подготовлены к использованию следующие типы источников:

- проект новой Конституции РК 2026;
- commentary-материалы по проекту;
- FAQ-материалы;
- historical/deprecated слой Конституции 1995;
- дополнительные тезисные и объяснительные документы для возможного расширения commentary-layer;
- отдельные internal / restricted operational материалы, не предназначенные для обычного пользовательского retrieval.

---

## Boundary rule

Пока работа идёт внутри `constitution-rag`, по умолчанию не уходить:

- в соседние проекты;
- в соседние контейнеры;
- в другие сервисы вне текущего контура;
- в внешние operational ветки, не относящиеся к текущему checklist,

если на это нет прямого сигнала пользователя или прямого runtime-следа из текущей задачи.

---

## Рабочие правила для изменений

После каждого значимого результата необходимо:

1. обновить README или текущий status-file;
2. зафиксировать статус этапа;
3. перечислить known issues;
4. явно обозначить следующий шаг.

Если prompt / retrieval stage будет закрыт успешно, следующий фокус проекта — application-level QA и поведение чат-бота в реальных сценариях использования.

---

## Recommended repo navigation

Рекомендуемый порядок входа в проект:

1. `README.md`
2. `CURRENT_STATUS.md` или актуальный operational status-file
3. `system_prompt_canonical_v1.2.md`
4. `retrieval_policy_v1.1.md`
5. `red_team_test_pack_v1.md`
6. `qa_results_template.md`
7. importer / normalization scripts
8. SQL QA / runtime verification files

---

## Current operational focus

Текущий приоритет проекта:

- не новый ingestion “вообще”;
- не соседние контуры;
- не косметические улучшения;

а завершение prompt / retrieval QA и только затем controlled расширение knowledge base новыми документами.
