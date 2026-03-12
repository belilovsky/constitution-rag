# PROJECT STATUS AND NEXT STEP — constitution-rag

Last updated: 2026-03-12

## 1. Project position

`constitution-rag` — это рабочий проект grounded чат-бота по конституционным материалам Республики Казахстан.

Ingestion, normalization, import в PostgreSQL и retrieval routing в этом проекте являются подготовительным слоем для grounded answers, а не конечной целью сами по себе.

На текущий момент:
- data-layer этап закрыт;
- retrieval-layer находится в рабочем состоянии после зафиксированного hotfix;
- проект переходит в стадию prompt / answer-layer QA и системной проверки поведения chatbot-контура.

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

В БД находятся 8 документных наборов:

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

## 5. Canonical prompt-layer docs

Source of truth для prompt / retrieval / answer слоя на текущем этапе:

- `PROJECT_STATUS_AND_NEXT_STEP.md`
- `README.md`
- `system_prompt_canonical_v1-4.md`
- `retrieval_policy_v1.md`
- `red_team_hostile_25.md`
- `qa_results_template.md`

Если между обсуждениями, черновиками, временными заметками и этими файлами есть расхождение, приоритет имеют канонические документы в repo.

Распределение ролей между документами:

- `PROJECT_STATUS_AND_NEXT_STEP.md` — текущий этап, release gate, known issues, next actions;
- `README.md` — входной документ по проекту и общая project memory;
- `system_prompt_canonical_v1-4.md` — канонические правила answer behavior;
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

### Open QA risk areas

После retrieval hotfix всё ещё нужно отдельно проверить и закрыть на уровне answer behavior:

- false completeness на broad queries;
- commentary / FAQ substitution при отсутствии norm;
- политический framing на чувствительных темах;
- meta-leakage внутренних правил;
- overly confident wording при weak / empty retrieval;
- exact lookup vs structural context cases;
- mixed-topic handling;
- follow-up pressure cases, где модель могут подталкивать к категоричности;
- status labeling для project / transitional / deprecated контекста;
- comparison behavior, где модель может смешивать 1995 и 2026 в один слой.

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
- содержат агитационные, организационные и внутренние методические элементы;
- требуют отдельного решения по restricted storage или полного исключения из chatbot retrieval.

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

## 11. Immediate next actions

Ближайшая обязательная последовательность:

1. зафиксировать этот статус-файл в repo;
2. обновить `README.md` в соответствии с текущим состоянием проекта;
3. синхронизировать `qa_results_template.md` с текущими каноническими документами;
4. прогнать top-10 critical cases из `red_team_hostile_25.md`;
5. сохранить QA-лог по каждому прогону через `qa_results_template.md`;
6. зафиксировать blocker register и fix plan;
7. исправить answer-layer / prompt behavior по найденным провалам;
8. сделать retest;
9. только после этого переходить к full 30-case run;
10. только после закрытия P0 возвращаться к решению по импорту новых документов.

---

## 12. Success criteria for transition to next stage

Можно считать проект готовым к следующему этапу, если одновременно выполнено следующее:

- data-layer стабилен и документирован;
- retrieval hotfix закреплён в repo и подтверждён на VPS;
- source of truth prompt-layer зафиксирован;
- канонические документы синхронизированы между собой;
- top-10 critical QA run проведён;
- blocker register создан и заполнен;
- fix plan создан и зафиксирован;
- есть хотя бы один retest;
- P0 issues закрыты;
- правила обращения с дополнительными документами зафиксированы;
- internal / restricted материалы отделены от публичного retrieval-контура.

---

## 13. Release status interpretation

Текущий статус стадии нужно трактовать так:

- `GO` — только если нет открытых P0 blocker’ов и есть подтверждённый retest;
- `CONDITIONAL GO` — допустим только для staging / internal / pilot scope и только без открытых P0 blocker’ов;
- `NO-GO` — по умолчанию, пока не закрыты blocker’ы текущего этапа.

На текущий момент release status этого этапа: `NO-GO until top-10 QA run and blocker closure`.

---

## 14. Boundary rule

Пока работа идёт внутри `constitution-rag`, не уходить в соседние проекты, контейнеры и сервисы без прямого сигнала пользователя или прямого runtime-следа из текущей задачи.

Текущий приоритет проекта:
- не новый ingestion;
- не расширение соседних контуров;
- не косметические правки документации ради документации;
- а закрытие prompt / retrieval / answer-layer QA до воспроизводимого и проверяемого состояния.
