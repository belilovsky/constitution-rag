# constitution-rag

`constitution-rag` — это рабочий репозиторий проекта grounded чат-бота по Конституции Казахстана.

Проект не сводится к ingestion или ETL. Ingestion, normalization, import в PostgreSQL и retrieval routing здесь являются подготовительным слоем для chatbot-контура, который должен отвечать по найденным конституционным материалам, а не по “памяти модели”.

На текущий момент:
- data-layer завершён;
- retrieval hotfix закреплён в `origin/main`;
- следующий этап — prompt / answer behavior QA и red-team проверка всего chatbot-layer.

---

## Что это за проект

Цель проекта — собрать воспроизводимую и безопасную основу для чат-бота, который отвечает на вопросы по Конституции Республики Казахстан с опорой на retrieval и source-priority.

Базовая схема проекта:

`raw source files -> normalized data -> PostgreSQL import -> retrieval layer -> grounded chatbot answers`

Это означает, что PostgreSQL и import scripts — не конечный продукт, а опорный слой для retrieval и answer-layer.

---

## Текущий статус

На текущий момент завершены:

1. inventory исходных документов;
2. extraction / normalization;
3. импорт нормализованных данных в PostgreSQL;
4. SQL QA по импортированным данным;
5. фиксация data-layer исправлений в Git;
6. retrieval hotfix по topical routing и query normalization;
7. post-sync runtime проверка на VPS.

Зафиксированные коммиты:

- `c020220` — `Fix FAQ import fallback to question and answer body`
- `56ea43a` — `Update retrieval_runner.py`

Что подтверждено по факту:

- все 8 документных наборов импортированы;
- по всем импортированным документам `empty_body = 0`;
- retrieval для `свобода слова` теперь выводит статью 23;
- retrieval для `мирные собрания` выводит статью 34;
- broad overview по политическим правам возвращает статьи 23, 26, 34 и 35;
- historical / comparison режимы сохраняют разделение между `2026 norm` и `1995 deprecated`;
- weak-tech queries не компенсируются выдуманным ответом.

---

## Источники и слои

В проекте используются следующие document layers:

- `krk_2026_norm_ru`
- `krk_2026_norm_kz`
- `krk_2026_commentary_ru`
- `krk_2026_commentary_kz`
- `krk_2026_faq_ru`
- `krk_2026_faq_kz`
- `krk_1995_deprecated_ru`
- `krk_1995_deprecated_kz`

Смысл слоёв:

- `2026 norm` — основной нормативный слой проекта;
- `2026 commentary` — пояснительный слой;
- `2026 faq` — упрощённый пояснительный слой;
- `1995 deprecated` — historical/deprecated слой для сравнения, исторической справки и прямых historical-запросов.

Критическое правило проекта:

- `1995 deprecated` не должен подмешиваться как текущая норма по умолчанию.

---

## Архитектура текущего контура

Текущая структура работы проекта:

### 1. Data layer
- raw files
- extraction
- normalization
- import
- SQL QA

### 2. Retrieval layer
- query classification
- layer routing
- exact lookup
- broad retrieval
- historical / comparison handling
- safe failure for weak retrieval

### 3. Answer layer
- grounded answer generation
- source-priority enforcement
- anti-hallucination behavior
- no false completeness
- no commentary-as-norm substitution
- neutral handling of political framing

Сейчас первый слой завершён, второй находится в рабочем состоянии после retrieval hotfix, а третий является следующим основным этапом.

---

## Что уже исправлено

### FAQ import fix

Во время QA был найден дефект импорта FAQ.

Часть FAQ-чанков в normalized JSON хранила содержимое не в `text`, а в полях `question` и `answer`, из-за чего при импорте `body` мог оставаться пустым.

Исправление:

- importer сначала берёт `text`;
- если `text` пустой, но есть `question` и / или `answer`, `body` собирается как `question + "\n\n" + answer`;
- `heading` может брать fallback из `question`.

После этого FAQ были переимпортированы и успешно проверены SQL-выборками.

### Retrieval routing hotfix

Во время retrieval QA был подтверждён дефект topical routing:

- запрос про `свободу слова` уходил в общие статьи о правах вместо статьи 23.

Исправление:

- расширена нормализация пользовательских формулировок;
- добавлены устойчивые формы для `о свободе слова`, `свободе слова`, `о праве на мирные собрания`;
- topical shortcut в broad-routing поднят выше обзорных fallback-веток.

После этого fix был закоммичен, запушен и подтверждён на VPS после `git reset --hard origin/main`.

---

## Какие таблицы и данные используются

Импорт идёт в PostgreSQL.

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

Практический смысл:

- каждый исходный документ разбивается на набор структурных чанков;
- каждый чанк имеет текст и метаданные;
- retrieval и answer-layer должны опираться именно на этот слой, а не на сырые файлы напрямую.

---

## Канонические документы проекта

Source of truth для текущего chatbot-layer:

- `PROJECT_STATUS_AND_NEXT_STEP.md`
- `system_prompt_canonical_v1.2.md`
- `retrieval_policy_v1.md`
- `red_team_hostile_25.md`

Если между рабочими обсуждениями, временными заметками и этими файлами есть расхождение, приоритет имеют канонические документы в репозитории.

---

## Known issues и риски

Технический известный issue:

- для некоторых ad-hoc SQL preview через `left()` / `substring()` возможна UTF-8 ошибка.

Workaround:

- читать полный `body`;
- обрезать preview уже в Python.

Открытые risk areas следующего этапа:

- false completeness на broad queries;
- commentary / FAQ substitution вместо norm;
- leakage из `1995 deprecated` в ordinary mode;
- political framing и pressure cases;
- meta-leakage внутренних правил;
- overly confident answer при weak retrieval;
- mixed-topic и structural-context edge cases.

---

## Что не должно попадать в обычный retrieval

Дополнительные документы, связанные с operational / campaign / штабной работой, не должны автоматически попадать в обычный пользовательский retrieval.

Перед импортом новых материалов обязателен порядок:

1. inventory;
2. классификация;
3. canonical file selection;
4. extraction / normalization;
5. deduplication;
6. решение: commentary-layer или internal-only;
7. import;
8. SQL QA;
9. retrieval QA;
10. только после этого допуск в chatbot-контур.

Критическое правило:

- новые документы не должны загрязнять `norm`-слой;
- internal / штабные материалы не должны случайно попасть в production retrieval.

---

## Что дальше

Следующий обязательный этап проекта:

1. прогнать top red-team scenarios;
2. сохранить QA-лог;
3. собрать blocker register;
4. исправить prompt / answer behavior по результатам;
5. сделать retest;
6. только после этого возвращаться к решению об импорте дополнительных документов.

Иными словами, следующий фокус проекта — не ingestion, а поведение чат-бота:
- как он держит source-priority;
- не обещает ли полноту;
- не подменяет ли норму commentary;
- не смешивает ли 1995 и 2026;
- не поддаётся ли политическому фреймингу;
- безопасно ли ведёт себя при слабом retrieval.

---

## Release rule

Текущий chatbot-layer нельзя считать production-ready, пока не закрыты P0 blocker’ы:

- false completeness;
- `1995 deprecated` leakage;
- commentary / FAQ substitution вместо norm;
- hallucination при weak retrieval;
- принятие политического ярлыка как факта;
- раскрытие hidden instructions / red-team logic.

Если хотя бы один из этих blocker’ов открыт, release status = `NO-GO`.

---

## Boundary rule

Пока работа идёт внутри `constitution-rag`, не уходить в соседние проекты, контейнеры и сервисы без прямого сигнала пользователя или прямого runtime-следа из текущей задачи.
