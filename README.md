# constitution-rag

`constitution-rag` — это рабочий репозиторий проекта grounded чат-бота по конституционным материалам Республики Казахстан.

Проект не сводится к ingestion или ETL. Ingestion, normalization, import в PostgreSQL и retrieval routing здесь являются подготовительным слоем для chatbot-контура, который должен отвечать по найденным конституционным материалам, а не по "памяти модели".

---

## ⚠️ КРИТИЧЕСКАЯ ИНФОРМАЦИЯ ДЛЯ НОВОГО ДИАЛОГА / АССИСТЕНТА

> **Прочитай этот блок ЦЕЛИКОМ перед любыми действиями.**
> Здесь собраны все факты, которые терялись между сессиями.

### Инфраструктура VPS (srv1380923.hstgr.cloud)

| Компонент | Путь на VPS | Docker-контейнер | Порт | Сеть |
|---|---|---|---|---|
| **PostgreSQL 16** (pgvector) | `/opt/constitution-rag/` | `constitution_rag_db` | `127.0.0.1:55432` | Docker bridge |
| **FastAPI API** | `/root/constitution-rag/` | `constitution_api` | `8000` | `--network host` |
| **Nginx proxy** | — | `constitution_nginx` | `8080` → `localhost:8000` | Bridge |

### Правила управления контейнерами

```
⛔ НИКОГДА не запускать `docker compose up` из `/root/constitution-rag/`
   → docker-compose.yml там для FRESH deployment (создаёт и API, и DB)
   → на VPS БД уже живёт отдельно в /opt/constitution-rag/

✅ База данных:
   cd /opt/constitution-rag && docker compose up -d

✅ API (standalone):
   cd /root/constitution-rag
   docker rm -f constitution_api
   docker build --no-cache -t constitution_api .
   docker run -d --name constitution_api \
     --restart unless-stopped --network host --env-file .env constitution_api

⚠️ docker build --no-cache ОБЯЗАТЕЛЕН:
   имя образа constitution_api ранее использовалось другим проектом на VPS.
   Без --no-cache Docker может подхватить кэш чужого образа.
```

### .env файлы

| Файл | Для чего | Ключевые переменные |
|---|---|---|
| `/root/constitution-rag/.env` | API-контейнер (`--env-file`) | `OPENAI_API_KEY`, `OPENAI_MODEL=gpt-4.1-mini`, `DB_HOST=127.0.0.1`, `DB_PORT=55432`, `DB_PASSWORD=...` |
| `/opt/constitution-rag/.env` | DB-контейнер (docker-compose) | `DATABASE_URL`, `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD` |

DB password: `ConstitutionRag_2026_Strong_Pass_Change_This`

### Зачем `--network host` для API?

PostgreSQL слушает на `127.0.0.1:55432` хоста. Если API в Docker bridge — он не видит localhost хоста. С `--network host` контейнер видит все порты хоста напрямую.

### Файлы, ОБЯЗАТЕЛЬНЫЕ внутри Docker-образа

- `app/` — весь Python-код
- `main.py` — FastAPI entry point
- `requirements.txt` — зависимости
- `docs/system_prompt_canonical_v1.md` — загружается `answer_runner.py` при старте
- `static/index.html` — фронтенд

**НЕ нужны** внутри образа (исключены `.dockerignore`):
`.venv/`, `.git/`, `raw/`, `normalized/`, `qa/evidence/`, `scripts/`, `importers/`, `manifests/`, `sql/`

### Проверка после деплоя

```bash
# 1. Файлы внутри контейнера — должны быть НАШИ
docker exec constitution_api ls /app/app/
# Ожидаем: answer_runner.py  ask_cli.py  db.py  retrieval_runner.py

# 2. Health
curl http://localhost:8000/health
# Ожидаем: {"status":"ok","db":"ok","uptime_s":...,"model":"gpt-4.1-mini"}

# 3. Тест API
curl -s -X POST http://localhost:8000/api/ask \
  -H 'Content-Type: application/json' \
  -d '{"query":"Что говорится о свободе слова?"}' | python3 -m json.tool
```

### Типичные грабли (уже наступали)

1. **`docker exec` показывает чужие файлы** → забыл `--no-cache` при build
2. **`/api/ask` возвращает 500, а venv работает** → внутри контейнера чужой main.py
3. **DB connection refused** → `constitution_rag_db` не запущен, проверь: `cd /opt/constitution-rag && docker compose up -d`
4. **`docker compose down` из `/root/` убил что-то** → этот compose создаёт свой DB-контейнер, не связан с `/opt/`, но путает Docker

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
| Full 30-test red-team QA: 30/30 pass (expanded DB, gpt-4.1-mini) | done | qa/evidence/full30_S3_20260313_0917.md |
| P1 RT-20 fix (anti-indirect-interpretation rule + few-shot in §8) | done | commit 9aaaffc |
| P1 RT-20 retest: PASS | done | qa/evidence/rt20_retest_20260313.md |
| Model comparison: gpt-4o-mini vs gpt-4.1-mini vs gpt-4.1 | done | qa/evidence/full30_S3_20260313_*.md |
| Switch to gpt-4.1-mini (30/30 pass, 22% faster) | done | commit 3e19a9e |
| Batch-1: prompt v3, RT-15 blocker, SAFE_FAILURE_TEXT | done | commit e1fb028 |
| Batch-2: anti-false-completeness, hedge, ban-list | done | commit e050cd1 |
| Batch-3: Docker, FastAPI, streaming, frontend, kz/en tests | done | commit 9667ab2 |
| .dockerignore | done | commit 7f68d6c |

### QA summary

- **Top-10 critical**: 10/10 pass
- **Full 30 red-team**: 30/30 pass — latest: full30_S3_20260313_0917.md (expanded DB, 15 sets, 1105 chunks)
- **Open P0**: 0
- **Open P1**: 0

### Model comparison (2026-03-13)

| Metric | gpt-4o-mini | gpt-4.1-mini | gpt-4.1 |
|---|---|---|---|
| Auto-pass | 29/30 | **30/30** | 9/30 (rate limit) |
| Total time | 134s (4.5s avg) | **105s (3.5s avg)** | n/a |
| RT-15 (political framing) | FAIL | **PASS** | n/a |
| RT-20 (neutrality drift) | PASS | **PASS** | n/a |
| Input / 1M tokens | $0.15 | $0.40 | $2.00 |
| Output / 1M tokens | $0.60 | $1.60 | $8.00 |

**Production model: gpt-4.1-mini** — best balance of constraint-following, speed, and cost.

---

## Что это за проект

Цель проекта — собрать воспроизводимую и безопасную основу для чат-бота, который отвечает на вопросы по Конституции Республики Казахстан с опорой на retrieval, source-priority и answer discipline.

Базовая схема проекта:

`raw source files -> normalized data -> PostgreSQL import -> retrieval layer -> grounded chatbot answers`

Это означает, что PostgreSQL, import scripts и retrieval routing — не конечный продукт, а опорный слой для answer-layer и прикладочного поведения чат-бота.

---

## База данных

### Состояние (2026-03-13)

- **15 датасетов**, **1105 чанков**, `empty_body = 0`
- PostgreSQL 16 + pgvector
- Данные в Docker volume: `/opt/constitution-rag/data/postgres/`

### Датасеты

| doc_key | chunks | Язык | Слой | Routing |
|---|---|---|---|---|
| `krk_2026_norm_ru` | 97 | ru | Norm | Основной |
| `krk_2026_norm_kz` | 97 | kz | Norm | Основной |
| `krk_2026_commentary_ru` | 114 | ru | Commentary | Основной |
| `krk_2026_commentary_kz` | 104 | kz | Commentary | Основной |
| `krk_2026_ce_theses_ru` | 38 | ru | CE sub-layer | Вторичный |
| `krk_2026_ce_audiences_ru` | 151 | ru | CE sub-layer | Вторичный |
| `krk_2026_ce_comparison_ru` | 9 | ru | Comparison | Только comparison mode |
| `krk_2026_faq_ru` | 15 | ru | FAQ | Основной |
| `krk_2026_faq_kz` | 15 | kz | FAQ | Основной |
| `krk_2026_faq_extra_ru` | 55 | ru | FAQ Extra | Расширенный (приоритетнее краткого) |
| `krk_2026_faq_extra_kz` | 63 | kz | FAQ Extra | Расширенный |
| `krk_2026_faq_extra_en` | 53 | en | FAQ Extra | Расширенный |
| `krk_1995_deprecated_ru` | 103 | ru | Historical | Только по запросу / comparison |
| `krk_1995_deprecated_kz` | 100 | kz | Historical | Только по запросу / comparison |
| `krk_2026_ce_lines_ru` | 91 | ru | RESTRICTED | **НЕ используется** в обычном retrieval |

### Таблицы PostgreSQL

| Таблица | Назначение |
|---|---|
| `documents` | Метаданные документов (doc_key, title, language_code, status) |
| `document_chunks` | Чанки: body, body_tsv, heading, meta, pgvector embedding |
| `import_runs` | Лог импортов (run_type, status, stats) |
| `query_log` | Лог API-запросов (auto-created при старте FastAPI) |

### Приоритет источников

```
norm > commentary > faq > historical/deprecated
```

Критическое правило: `1995 deprecated` **не должен** подмешиваться как текущая норма.

---

## Структура репозитория

```
constitution-rag/
├── app/
│   ├── answer_runner.py    — generate_answer, build_user_prompt, load_system_prompt
│   ├── retrieval_runner.py — run_retrieval, query classification, 15 datasets routing
│   ├── db.py               — connection pool (SimpleConnectionPool 1..5)
│   └── ask_cli.py          — CLI-интерфейс для тестирования
├── main.py                 — FastAPI: /health, /api/ask, /api/ask/stream (SSE), static mount
├── Dockerfile              — python:3.12-slim, WORKDIR /app, COPY . ., healthcheck curl
├── .dockerignore           — исключает raw/, normalized/, .venv/, .git/ из build context
├── docker-compose.yml      — ⚠️ для FRESH deployment ТОЛЬКО, НЕ для VPS prod
├── requirements.txt        — openai, psycopg2-binary, fastapi, uvicorn
├── static/
│   └── index.html          — Web UI: streaming, ru/kz/en selector
├── docs/
│   ├── system_prompt_canonical_v1.md    — канонический system prompt (18 секций)
│   ├── retrieval_policy_v1.md           — retrieval routing policy
│   ├── red_team_hostile_25.md           — тестовый пакет (30 вопросов)
│   └── qa_results_template.md           — шаблон QA-отчёта
├── qa/
│   ├── run_full30.py       — 45 тестов (RT-01..30 ru, RT-31..38 kz, RT-39..45 en)
│   │                         ⚠️ Название историческое, реально 45 тестов
│   ├── run_top10.py        — 10 критических тестов
│   ├── evidence/           — все QA evidence файлы
│   └── comparative/        — сравнительный анализ (top10, S1-S4)
├── importers/              — import скрипты (import_all_remaining, import_norm_ru, etc)
├── scripts/                — extraction скрипты (extract → JSON)
├── normalized/             — JSON чанки (15 файлов)
├── raw/                    — исходные PDF/DOCX (~15MB)
│   ├── commentary/         — методички (рус/каз PDF)
│   ├── commentary_extra/   — доп. материалы (DOCX)
│   ├── deprecated/         — 1995 конституция (PDF)
│   ├── faq/                — FAQ брошюры (PDF)
│   ├── internal/           — оперрекомендации (DOCX)
│   └── norm/               — проект 2026 (DOCX)
├── manifests/              — ingestion manifest JSON
├── sql/                    — SQL-файлы (.gitkeep)
└── AUDIT_2026-03-13.md     — полная ревизия проекта
```

### API Endpoints (main.py)

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/health` | Liveness + DB check. Возвращает `{"status":"ok","db":"ok","model":"gpt-4.1-mini"}` |
| POST | `/api/ask` | Синхронный ответ. Body: `{"query":"..."}`. Response: `{answer, mode, lang, latency_ms}` |
| POST | `/api/ask/stream` | SSE-стриминг. Events: `meta`, `text` (delta), `done`, `error` |
| GET | `/` | Фронтенд (static/index.html) |

---

## Канонические документы

Source of truth для текущего chatbot-layer:

- `system_prompt_canonical_v1.md` — канонические правила answer behavior;
- `retrieval_policy_v1.md` — канонические правила retrieval routing и source-priority;
- `red_team_hostile_25.md` — тестовый пакет и rubric;
- `qa_results_template.md` — канонический шаблон QA-run, blocker register, fix plan и retest log.

Если между рабочими обсуждениями, временными заметками и этими файлами есть расхождение, приоритет имеют канонические документы в репозитории.

---

## Архитектура контура

### 1. Data layer
- raw files → extraction → normalization → import → SQL QA

### 2. Retrieval layer
- query classification → layer routing → exact lookup → broad retrieval
- historical / comparison handling → safe failure for weak retrieval

### 3. Answer layer
- grounded answer generation → source-priority enforcement
- anti-hallucination → no false completeness → no commentary-as-norm substitution
- neutral handling of political framing → anti-indirect-interpretation (few-shot hardened)
- no hidden-rules leakage

Все три слоя завершены и прошли QA.

---

## Что уже исправлено

### FAQ import fix
Часть FAQ-чанков хранила содержимое в `question`/`answer` вместо `text` → при импорте `body` пустой. Исправлено: importer берёт fallback из `question + answer`.

### Retrieval routing hotfix (56ea43a)
Запрос про `свободу слова` уходил в общие статьи вместо статьи 23. Исправлено: расширена нормализация, topical shortcut поднят выше.

### System prompt P0 fixes
4 P0-фикса: RT-03 (false completeness), RT-05 (effective_date), RT-08 (1995 leakage), RT-15 (political framing).

### answer_runner.py FIX-3 (fda0d68)
RT-30: убран empty-retrieval shortcut, LLM вызывается всегда для safe failure и meta-question handling.

### P1 RT-20 neutrality drift fix (9aaaffc)
Бот подыгрывал навязанной рамке через косвенные формулы. Исправлено: anti-indirect-interpretation rule + few-shot.

### Batch-1 (e1fb028)
RT-15 blocker, RT-20 negative context, SAFE_FAILURE_TEXT, banned constructions.

### Batch-2 (e050cd1)
Anti-false-completeness, hedge formulas, ban-list audit, checker upgrade.

### Batch-3 (9667ab2)
Docker, FastAPI (main.py), streaming SSE, frontend (static/index.html), kz/en тесты (RT-31..45).

---

## История коммитов

| SHA | Дата | Описание |
|---|---|---|
| `a5e840a` | 2026-03-13 12:37 | docs: full project audit |
| `7f68d6c` | 2026-03-13 12:35 | chore: add .dockerignore |
| `ca0cfdd` | 2026-03-13 12:10 | docs: README — infrastructure map |
| `90a63a3` | 2026-03-13 11:47 | docs: PROJECT_STATUS update |
| `9667ab2` | 2026-03-13 11:46 | **batch-3**: Docker, FastAPI, streaming, frontend, kz/en tests |
| `4217705` | 2026-03-13 11:38 | evidence: full30 30/30 clean pass (batch-2) |
| `e050cd1` | 2026-03-13 11:32 | **batch-2**: anti-false-completeness, hedge, ban-list |
| `e1fb028` | 2026-03-13 11:17 | **batch-1**: RT-15 blocker, RT-20, SAFE_FAILURE_TEXT |
| `918ab9b` | 2026-03-13 10:37 | system prompt v3 |
| `1285327` | 2026-03-13 09:52 | audit v2: language routing, pool, 15 datasets |
| `b73f56f` | 2026-03-13 09:20 | full30 evidence: 15 datasets, 1105 chunks, 30/30 |
| `fa172ec` | 2026-03-13 09:09 | faq_extra normalized JSON |

### Full30 run history

| Run file | Model | Score | Notes |
|----------|-------|-------|-------|
| full30_S3_20260312_2223.md | gpt-4o-mini | 29/30 | 1 P1 (RT-20) |
| full30_S3_20260313_0831.md | gpt-4o-mini | 29/30 | Pre-DB expansion |
| full30_S3_20260313_0837.md | gpt-4.1-mini | 30/30 | Pre-DB expansion |
| full30_S3_20260313_0840.md | gpt-4.1 | 9/30 | Rate limited |
| full30_S3_20260313_0917.md | gpt-4.1-mini | 30/30 | Expanded DB — initial GO |
| full30_S3_20260313_1000.md | gpt-4.1-mini | 30/30 | Post batch-1: prompt v3 |
| full30_S3_20260313_1120.md | gpt-4.1-mini | 29/30 | Batch-1 deploy, RT-22 warn |
| full30_S3_20260313_1134.md | gpt-4.1-mini | 30/30 | **Batch-2 clean pass** (127.3s) |

---

## Fresh-dialog handoff

Если работа переносится в новый диалог, стартовая точка:

1. **Прочитать этот README целиком** — тут все факты, инфраструктура, грабли.
2. `git log --oneline -5` — подтвердить текущий коммит.
3. `docker ps --format 'table {{.Names}}\t{{.Status}}'` — проверить контейнеры.
4. `ss -tlnp | grep 55432` — проверить что DB слушает.
5. `curl http://localhost:8000/health` — проверить API.
6. `docker exec constitution_api ls /app/app/` — проверить что внутри НАШИ файлы.
7. Решить направление следующей фазы.

---

## Boundary rule

Пока работа идёт внутри `constitution-rag`, не уходить в соседние проекты, контейнеры и сервисы без прямого сигнала пользователя или прямого runtime-следа из текущей задачи.
