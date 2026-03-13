# constitution-rag

`constitution-rag` — это рабочий репозиторий проекта grounded чат-бота по конституционным материалам Республики Казахстан.

Проект не сводится к ingestion или ETL. Ingestion, normalization, import в PostgreSQL и retrieval routing здесь являются подготовительным слоем для chatbot-контура, который должен отвечать по найденным конституционным материалам, а не по "памяти модели".

---

## Текущий статус: GO

**Release gate: GO** — все P0 blockers закрыты, P1 RT-20 (neutrality drift) закрыт.

### Пройденные этапы

| Этап | Статус | Evidence |
|------|--------|----------|
| Data ingestion (extraction, normalization, import, SQL QA, empty_body=0) | done | — |
| Retrieval hotfix (topical routing, source-priority) | done | commit 56ea43a |
| System prompt canonical v1 (4 P0 fixes) | done | system_prompt_canonical_v1.md |
| answer_runner.py FIX-3 RT-30 (empty-retrieval shortcut removed) | done | commit fda0d68 |
| Top-10 critical QA: 10/10 pass | done | qa/evidence/top10_S3_20260312_2203.md |
| Full 30-test red-team QA: 29/30 auto-pass, 1 P1 | done | qa/evidence/full30_S3_20260312_2223.md |
| P1 RT-20 fix (anti-indirect-interpretation rule + few-shot in §8) | done | commit 9aaaffc |
| P1 RT-20 retest: PASS | done | qa/evidence/rt20_retest_20260313.md |

### QA summary

- **Top-10 critical**: 10/10 pass
- **Full 30 red-team**: 30/30 pass (29 auto-pass + 1 retest pass)
- **Open P0**: 0
- **Open P1**: 0

---

## Что это за проект

Цель проекта — собрать воспроизводимую и безопасную основу для чат-бота, который отвечает на вопросы по Конституции Республики Казахстан с опорой на retrieval, source-priority и answer discipline.

Базовая схема проекта:

`raw source files -> normalized data -> PostgreSQL import -> retrieval layer -> grounded chatbot answers`

Это означает, что PostgreSQL, import scripts и retrieval routing — не конечный продукт, а опорный слой для answer-layer и прикладочного поведения чат-бота.

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

Базовый приоритет источников:

- `norm > commentary > faq > historical/deprecated`

Это правило должно соблюдаться и в retrieval, и в answer-layer.

---

## Архитектура контура

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
- anti-indirect-interpretation (few-shot hardened)
- no hidden-rules leakage

Все три слоя завершены и прошли QA.

---

## Ключевые файлы

| Файл | Назначение |
|------|-----------|
| `app/answer_runner.py` | Entry point: generate_answer, flatten_payload |
| `app/retrieval_runner.py` | Retrieval routing и query classification |
| `docs/system_prompt_canonical_v1.md` | Канонический system prompt (18 секций) |
| `docs/retrieval_policy_v1.md` | Retrieval routing и source-priority policy |
| `qa/run_top10.py` | Top-10 critical QA run script |
| `qa/run_full30.py` | Full 30-test red-team QA run script |
| `qa/evidence/` | Все QA evidence файлы |

---

## Канонические документы

Source of truth для текущего chatbot-layer:

- `system_prompt_canonical_v1.md` — канонические правила answer behavior;
- `retrieval_policy_v1.md` — канонические правила retrieval routing и source-priority;
- `red_team_hostile_25.md` — тестовый пакет и rubric;
- `qa_results_template.md` — канонический шаблон QA-run, blocker register, fix plan и retest log.

Если между рабочими обсуждениями, временными заметками и этими файлами есть расхождение, приоритет имеют канонические документы в репозитории.

---

## Что уже исправлено

### FAQ import fix

Часть FAQ-чанков в normalized JSON хранила содержимое не в `text`, а в полях `question` и `answer`, из-за чего при импорте `body` мог оставаться пустым. Исправлено: importer берёт fallback из `question + answer`.

### Retrieval routing hotfix (56ea43a)

Запрос про `свободу слова` уходил в общие статьи вместо статьи 23. Исправлено: расширена нормализация, topical shortcut поднят выше обзорных fallback-веток.

### System prompt P0 fixes

4 P0-фикса в system prompt canonical v1:
- RT-03: false completeness
- RT-05: effective_date
- RT-08: 1995 leakage
- RT-15: political framing

### answer_runner.py FIX-3 (fda0d68)

RT-30: убран empty-retrieval shortcut, LLM вызывается всегда для safe failure и meta-question handling.

### P1 RT-20 neutrality drift fix (9aaaffc)

Бот подыгрывал навязанной политической рамке через косвенные формулы («может свидетельствовать о значительных полномочиях»). Исправлено:
- запрет косвенно-оценочных формул (квалификатор + оценочное существительное);
- правило anti-indirect-interpretation;
- few-shot пример правильной реакции на навязывание ярлыка.

---

## Следующая фаза

Prompt / answer QA завершён. Возможные направления:

1. **Prompt design** — расширение prompt для edge cases
2. **Chatbot behavior QA** — расширенный тестовый пакет
3. **Semantic cache** — кэширование embeddings для ускорения
4. **Production deployment** — Docker, API endpoint, frontend
5. **Knowledge base expansion** — дополнительные документы

---

## Данные и таблицы

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

---

## Boundary rule

Пока работа идёт внутри `constitution-rag`, не уходить в соседние проекты, контейнеры и сервисы без прямого сигнала пользователя или прямого runtime-следа из текущей задачи.

---

## Fresh-dialog handoff

Если работа переносится в новый диалог, стартовая точка:

1. Подтвердить доступ к VPS / GitHub.
2. `git log --oneline -5` — подтвердить текущий коммит.
3. Проверить release status в этом README.
4. Решить направление следующей фазы.
