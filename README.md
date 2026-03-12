Да — дам **целиком готовый текст README.md**, уже с внесённым статусом по retrieval fix и known issue по 1995 metadata. Это значит, что тебе не нужно руками искать место для вставок: просто заменить файл целиком и закоммитить. Основание для этих добавлений — текущий статус проекта, retrieval policy и фактический runtime-результат smoke-check по Президенту и статье 23. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_3d927ef3-969a-4247-899b-b9a2bb88c997/95be01ba-2462-4f7c-a13f-f8072db7497f/README-10.md)

## Полный README.md

```md
# constitution-rag

`constitution-rag` — это рабочий репозиторий проекта чат-бота по Конституции Казахстана.  
На текущем этапе в репозитории подготовлен и проверен слой данных для будущего retrieval / RAG: исходные документы собраны, нормализованы, разложены на чанки и импортированы в PostgreSQL.

Проект в целом не сводится к ingestion.  
Текущий завершённый этап — это подготовка контента и базы; следующий этап — настройка prompt-логики, retrieval-поведения, ограничений ответа и общего поведения чат-бота. [file:37][file:36]

---

## Что это за проект

Цель проекта — собрать надёжную основу для чат-бота, который отвечает на вопросы по Конституции Казахстана, опираясь на структурированные источники, а не на “память модели”. [file:37]

Сейчас в базе подготовлены несколько слоёв контента:

- проект Конституции РК 2026, русский;
- проект Конституции РК 2026, казахский;
- комментарии к проекту Конституции 2026, русский;
- комментарии к проекту Конституции 2026, казахский;
- FAQ по проекту Конституции 2026, русский;
- FAQ по проекту Конституции 2026, казахский;
- Конституция РК 1995 года, русский, как deprecated-слой;
- Конституция РК 1995 года, казахский, как deprecated-слой. [file:37]

---

## Текущий статус

На текущий момент завершены:

1. инвентаризация исходных файлов;
2. extraction / normalization;
3. импорт нормализованных данных в PostgreSQL;
4. SQL QA по импортированным данным;
5. фиксация исправлений в Git и push в `origin/main`. [file:37]

Ключевой результат:
- все 8 документных наборов импортированы;
- по всем импортированным документам `empty_body = 0`;
- fix по FAQ сохранён в репозитории и уже запушен в `origin/main`. [file:37]

Последний зафиксированный data-layer коммит:
- `c020220` — `Fix FAQ import fallback to question and answer body`. [file:37]

---

## Архитектура текущего этапа

Текущая схема работы проекта:

`raw source files -> normalized chunks -> PostgreSQL import -> SQL QA -> retrieval-ready data layer`

Это означает, что сейчас в репозитории подготовлен именно **слой данных** для чат-бота.  
Сам production-ответ чат-бота, prompt policy и прикладной ответный контур — это следующий этап работы. [file:37][file:36]

---

## Источники данных

В проекте используются следующие типы источников:

- проект новой Конституции РК 2026 в DOCX;
- комментарийные PDF-материалы по проекту Конституции 2026;
- FAQ-материалы по проекту Конституции 2026;
- текст Конституции РК 1995 года в PDF. [file:37]

Источники проходят через extraction/normalization и превращаются в JSON-чанки, пригодные для импорта и retrieval. [file:37]

---

## Какие слои уже заведены в БД

Текущий набор документов в базе:

- `krk_2026_norm_ru`
- `krk_2026_norm_kz`
- `krk_2026_commentary_ru`
- `krk_2026_commentary_kz`
- `krk_2026_faq_ru`
- `krk_2026_faq_kz`
- `krk_1995_deprecated_ru`
- `krk_1995_deprecated_kz` [file:37]

Итоговая SQL-проверка по чанкам:

- `krk_1995_deprecated_kz` — 100 чанков;
- `krk_1995_deprecated_ru` — 103 чанка;
- `krk_2026_commentary_kz` — 104 чанка;
- `krk_2026_commentary_ru` — 114 чанков;
- `krk_2026_faq_kz` — 15 чанков;
- `krk_2026_faq_ru` — 15 чанков;
- `krk_2026_norm_kz` — 97 чанков;
- `krk_2026_norm_ru` — 97 чанков. [file:37]

По всем документам:
- `empty_body = 0`. [file:37]

---

## Структура данных

Импорт идёт в PostgreSQL.  
Основные таблицы текущего data-layer:

- `documents`
- `document_chunks`
- `import_runs` [file:37]

Ключевые поля `document_chunks`:

- `document_id`
- `chunk_index`
- `heading`
- `body`
- `body_tsv`
- `tokens_count`
- `char_count`
- `meta`
- `created_at` [file:37]

На практике это означает:
- один документ разбивается на набор чанков;
- каждый чанк имеет заголовок, основной текст и метаданные;
- дальше этот слой можно использовать для retrieval, поиска, reranking и prompt grounding. [file:37]

---

## Что было исправлено

В процессе QA был найден дефект импорта FAQ.  
Часть FAQ-чанков в normalized JSON хранила содержимое не в `text`, а в полях `question` и `answer`, из-за чего при импорте `body` мог оставаться пустым. [file:37]

Исправление:
- importer теперь сначала берёт `text`;
- если `text` пустой, но есть `question` и/или `answer`, то `body` собирается как `question + "\n\n" + answer`;
- `heading` также может брать fallback из `question`, если нужно. [file:37]

После этого FAQ были переимпортированы и успешно проверены SQL-выборками. [file:37]

---

## Что важно помнить про 1995 Конституцию

Текст Конституции 1995 года импортирован не как “текущая норма”, а как **deprecated / historical layer**.  
Он нужен для сравнений, исторического контекста и анализа изменений, но не должен выдаваться как актуальное действующее право вместо новой Конституции 2026, когда retrieval/prompt-слой будет собран полностью. [file:37][file:36]

Это один из критических рисков проекта, и он должен учитываться в дальнейшем prompt design и retrieval policy. [file:37][file:36]

---

## QA и проверка

Базовая проверка импорта включает:

1. наличие всех ожидаемых документов;
2. корректное число чанков;
3. отсутствие пустых `body`;
4. выборочную проверку содержимого по SQL / Python;
5. сверку source JSON и данных в БД для проблемных случаев. [file:37]

Пример проверочного SQL:

```sql
select d.doc_key,
       count(*) as chunks,
       sum(case when length(trim(c.body)) = 0 then 1 else 0 end) as empty_body,
       min(c.chunk_index),
       max(c.chunk_index)
from document_chunks c
join documents d on d.id = c.document_id
group by d.doc_key
order by d.doc_key;
```

---

## Project status

### Current project position

`constitution-rag` — это не просто ingestion-repo, а рабочий контур чат-бота по Конституции Республики Казахстан. [file:37][file:36]

Текущий прогресс по стадиям:

1. **Data layer — completed**
   - исходные документы собраны;
   - контент атомизирован;
   - normalized JSON подготовлены;
   - данные импортированы в PostgreSQL;
   - SQL QA пройден;
   - `empty_body = 0` по всем импортированным документным наборам;
   - FAQ import bug исправлен коммитом `c020220`. [file:37][file:36]

2. **Prompt / retrieval layer — in progress**
   - подготовлен канонический system prompt;
   - зафиксирована retrieval policy;
   - подготовлен red-team test pack;
   - подготовлены QA template и release checklist;
   - выполнен retrieval hotfix для comparison по теме `Президент`;
   - следующий обязательный шаг — прогон critical QA и фиксация blocker’ов. [file:36][file:38]

3. **Application layer — next**
   - application-level chatbot QA;
   - user journey testing;
   - RU/KZ parity checks;
   - post-deploy endpoint validation;
   - pilot rollout guardrails;
   - incident logging for problematic answers. [file:36]

---

## Data layer snapshot

На текущем этапе в БД находятся 8 документных наборов:

- `krk_2026_norm_ru`
- `krk_2026_norm_kz`
- `krk_2026_commentary_ru`
- `krk_2026_commentary_kz`
- `krk_2026_faq_ru`
- `krk_2026_faq_kz`
- `krk_1995_deprecated_ru`
- `krk_1995_deprecated_kz` [file:37][file:36]

Принцип работы со слоями:

- `2026 norm` — основной нормативный слой проекта;
- `2026 commentary` — дополнительный разъяснительный слой;
- `2026 faq` — упрощённый пояснительный слой;
- `1995 deprecated` — historical/deprecated слой только для сравнения, исторической справки или прямого запроса. [file:37][file:36]

`1995 deprecated` не должен использоваться как основной нормативный ответ по умолчанию. [file:37][file:36]

---

## Canonical prompt-layer docs

Следующие документы являются source of truth для prompt / retrieval слоя:

- `system_prompt_canonical_v1.2.md`
- `retrieval_policy_v1.1.md`
- `red_team_test_pack_v1.md`
- `qa_results_template.md`
- `release_checklist_prompt-layer.md` [file:36]

Если между ad-hoc обсуждением и этими файлами есть расхождение, приоритет имеют канонические документы в repo. [file:36]

---

## Prompt-layer principles

Базовые правила текущего chatbot layer:

- бот отвечает только по найденным в retrieval материалам;
- приоритет источников: `norm > commentary > faq > historical/deprecated`;
- ordinary query сначала должен разрешаться через `2026 norm`;
- `1995 deprecated` допускается только для comparison / historical mode / прямого запроса;
- commentary и FAQ не заменяют norm;
- бот не должен делать ложные заявления о полноте;
- бот не должен принимать политический фрейм вопроса как установленный факт;
- бот не должен раскрывать внутренние инструкции, red-team логику и hidden rules;
- при слабом retrieval бот обязан использовать safe-failure behavior;
- для части historical comparison используется metadata-aware workaround, если deprecated section metadata ненадёжна. [file:36][file:37][file:38]

---

## Retrieval fix status — 2026-03-12

Smoke-check после правки `retrieval_runner.py` пройден для кейсов:

- exact lookup: `Что сказано в статье 23?`
- ordinary retrieval: `Какие полномочия у Президента?`
- comparison retrieval: `Сравни 1995 и 2026 по Президенту` [file:38]

Результат:
- exact lookup по статье работает корректно;
- ordinary retrieval по теме `Президент` возвращает президентский блок 2026, включая статью 46 с перечнем полномочий;
- comparison по теме `Президент` больше не уходит в случайные ранние статьи 1995 и использует historical fallback по диапазону `40–48`. [file:38]

---

## Known issues

### Data-layer known issue

Для некоторых строк ad-hoc SQL preview через `left()` / `substring()` может падать с UTF-8 ошибкой. [file:37][file:36]

Безопасный workaround:
- читать полный `body`;
- обрезать preview уже в Python. [file:36]

### Historical metadata known issue

Для `krk_1995_deprecated_ru` section metadata нормализована некорректно:
во многих чанках `meta.section_title` заполнен как `Общие положения`, включая президентский блок. [file:38]

Следствие:
- section-aware retrieval для historical/deprecated слоя ненадёжен;
- comparison / historical routing не должен полагаться только на `section_title`. [file:38][file:36]

Текущий workaround:
- для comparison-запросов по теме `Президент` retrieval использует article-range fallback `40–48` для `krk_1995_deprecated_ru`. [file:38]

Системное исправление:
- переизвлечение / перенормализация 1995 deprecated layer с корректными section titles. [file:36][file:38]

### Prompt-layer risk areas to validate

До release необходимо отдельно проверить и закрыть:

- false completeness на broad queries;
- leakage из `1995 deprecated` в ordinary mode;
- commentary / FAQ substitution при отсутствии norm;
- политический framing на чувствительных темах;
- meta-leakage внутренних правил;
- уверенные ответы при weak / empty retrieval. [file:36]

---

## QA and release gate

Prompt-layer не считается завершённым, пока не выполнены все пункты:

- существует как минимум один critical QA run;
- заполнен QA results log;
- заведен blocker register;
- для blocker’ов есть fix plan;
- выполнен хотя бы один retest после правок;
- нет открытых P0-проблем по:
  - false completeness;
  - `1995 deprecated` leakage;
  - commentary substitution;
  - hallucination on weak retrieval;
  - meta leakage;
  - acceptance of political framing as fact. [file:36]

Если хотя бы один из этих blocker’ов открыт, release status = `NO-GO`. [file:36]

---

## Boundary rule

Если работа идёт внутри `constitution-rag`, по умолчанию не уходить:
- в соседние контейнеры;
- в соседние проекты;
- в другие сервисы вне текущего контура,

если на это нет прямого сигнала пользователя или runtime-следа из текущей задачи. [file:36]

