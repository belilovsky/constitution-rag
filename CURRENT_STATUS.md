# CURRENT STATUS — constitution-rag

Last updated: 2026-03-11

## 1. Project position

`constitution-rag` — это проект grounded чат-бота по Конституции Республики Казахстан.

Ingestion и PostgreSQL в этом проекте являются подготовительным слоем для retrieval и grounded answers, а не конечной целью сами по себе.

На текущий момент data-layer этап закрыт.
Проект перешёл в стадию prompt design, retrieval policy, system instructions и red-team QA ответов чат-бота.

---

## 2. Completed stage: data layer

Завершено:

- исходные документы собраны;
- контент атомизирован;
- normalized JSON подготовлены;
- данные импортированы в PostgreSQL;
- SQL QA пройден;
- `empty_body = 0` по всем документным наборам;
- FAQ import bug исправлен.

Зафиксированный fix:
- commit `c020220`
- `Fix FAQ import fallback to question and answer body`

---

## 3. Database snapshot

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
- `1995 deprecated` — historical/deprecated слой.

Критическое правило:
- `1995 deprecated` не должен трактоваться как текущая норма проекта по умолчанию.

---

## 4. Current stage: prompt / retrieval layer

На текущем этапе подготовлены следующие артефакты:

- `system_prompt_canonical_v1.2.md`
- `retrieval_policy_v1.1.md`
- `red_team_test_pack_v1.md`
- `qa_results_template.md`
- `release_checklist_prompt-layer.md`

Назначение этапа:
- убрать внутренние противоречия в системной инструкции;
- синхронизировать поведение модели с реальным retrieval/data-layer;
- зафиксировать source priority;
- исключить false completeness;
- исключить leakage из historical/deprecated слоя;
- исключить commentary / FAQ substitution;
- провести red-team QA по чувствительным кейсам.

---

## 5. Source of truth for prompt layer

Если возникает конфликт между обсуждениями, черновиками и operational decisions, ориентироваться в следующем порядке:

1. канонические документы prompt-layer в repo;
2. фактический QA log;
3. blocker register и fix plan;
4. runtime output текущего chatbot контура;
5. старые обсуждения и промежуточные черновики.

---

## 6. Known issues

### Confirmed technical known issue

Для некоторых строк ad-hoc SQL preview через `left()` / `substring()` может падать с UTF-8 ошибкой.

Workaround:
- читать полный `body`;
- резать preview в Python.

### Open prompt-layer risk areas

До release остаются открытыми для проверки следующие риски:

- false completeness на широких вопросах;
- `1995 deprecated` leakage в ordinary mode;
- commentary-as-substitute;
- FAQ-as-substitute;
- meta-leakage внутренних правил;
- политический framing на чувствительных вопросах;
- unsafe behavior на weak / empty retrieval;
- potential mismatch между exact lookup и broad semantic retrieval.

---

## 7. Release rule for current stage

Prompt / retrieval layer нельзя считать закрытым, пока не выполнено следующее:

- есть хотя бы один top-10 critical QA run;
- есть заполненный `qa_results_template.md`;
- есть blocker register;
- есть fix plan;
- есть хотя бы один retest;
- нет открытых P0 blocker’ов.

P0 blocker’ы для текущего этапа:

- false completeness;
- `1995 deprecated` default leakage;
- commentary / FAQ substitution вместо norm;
- hallucination при weak retrieval;
- принятие политического ярлыка как установленного факта;
- раскрытие hidden instructions / red-team logic.

---

## 8. Next required actions

Обязательная ближайшая последовательность:

1. прогнать top-10 critical cases;
2. заполнить QA log;
3. выделить blocker’ы;
4. внести точечные правки в prompt / retrieval;
5. сделать retest;
6. принять release decision по prompt-layer.

---

## 9. Next phase after current stage

После стабилизации prompt / retrieval layer проект должен перейти к следующей фазе:

- application-level chatbot QA;
- user journey testing;
- RU/KZ parity testing;
- post-deploy verification ключевых endpoint и сценариев;
- controlled rollout;
- logging и разбор проблемных ответов реальных пользователей.

---

## 10. Boundary rule

Пока работа идёт внутри `constitution-rag`, не выходить в соседние проекты, контейнеры и сервисы без прямого сигнала пользователя или прямого runtime-указания из текущей задачи.
