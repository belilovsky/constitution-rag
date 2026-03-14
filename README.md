# constitution-rag

`constitution-rag` — рабочий репозиторий grounded чат-бота по конституционным материалам Республики Казахстан.

Ingestion, normalization, import в PostgreSQL и retrieval routing — подготовительный слой для chatbot-контура, который отвечает по найденным материалам, а не по «памяти модели».

---

## КРИТИЧЕСКАЯ ИНФОРМАЦИЯ ДЛЯ НОВОГО ДИАЛОГА / АССИСТЕНТА

> **Прочитай этот блок ЦЕЛИКОМ перед любыми действиями.**
> Здесь собраны все факты, которые терялись между сессиями.

### Инфраструктура VPS (srv1380923.hstgr.cloud, IP: 62.72.32.112)

| Компонент | Путь на VPS | Docker-контейнер | Порт | Docker-сеть |
|---|---|---|---|---|
| **PostgreSQL 16** (pgvector) | `/opt/constitution-rag/` | `constitution_rag_db` | 5432 (internal), 127.0.0.1:55432 (host) | `constitution-rag_default` |
| **FastAPI API** | `/root/constitution-rag/` | `constitution_rag_api` | 8000 (internal, NOT published) | `constitution_rag_net` + `constitution-rag_default` |
| **Nginx proxy (наш)** | — | `constitution_rag_nginx` | 8090→80 | `constitution_rag_net` |
| **ДРУГОЙ проект (НЕ ТРОГАТЬ)** | `/opt/constitution/app/` | `constitution_api` | via constitution_nginx:8080 | `constitution_net` |

**НИКОГДА не трогать** `/opt/constitution/app/` или контейнер `constitution_api` — это чужой проект.

### Публичный URL

```
http://62.72.32.112:8090/
```

Nginx проксирует к `constitution_rag_api:8000` внутри Docker-сети `constitution_rag_net`.

### Сетевая архитектура (КРИТИЧНО)

API-контейнер должен быть подключён к **ДВУМ** Docker-сетям:
- `constitution_rag_net` — для связи с Nginx
- `constitution-rag_default` — для связи с PostgreSQL

```bash
# Проверить сети:
docker inspect constitution_rag_api --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}'
# Ожидаем: constitution_rag_net constitution-rag_default

# Если не хватает сети:
docker network connect constitution-rag_default constitution_rag_api
docker network connect constitution_rag_net constitution_rag_api
```

### Docker volumes

Директория `docs/` монтируется как volume:
```
-v /root/constitution-rag/docs:/app/docs
```
Это значит, что для обновления system prompt НЕ нужно пересобирать образ — достаточно перезапустить контейнер.

FAQ cache (`faq_cache.json`) находится **внутри образа** по пути `/app/app/faq_cache.json` (36KB, 30 записей). Для обновления нужна пересборка.

### Правила управления контейнерами

```
⛔ НИКОГДА не запускать `docker compose up` из `/root/constitution-rag/`
   → docker-compose.yml для FRESH deployment ТОЛЬКО (создаёт и API, и DB)
   → на VPS БД уже живёт отдельно в /opt/constitution-rag/

✅ База данных:
   cd /opt/constitution-rag && docker compose up -d

✅ API (пересборка и перезапуск):
   cd /root/constitution-rag && git pull
   docker rm -f constitution_rag_api 2>/dev/null
   docker build --no-cache -t constitution_rag_api .
   docker run -d --name constitution_rag_api \
     --restart unless-stopped \
     --network constitution_rag_net \
     --env-file .env \
     -v /root/constitution-rag/docs:/app/docs \
     constitution_rag_api
   docker network connect constitution-rag_default constitution_rag_api

✅ Nginx:
   docker rm -f constitution_rag_nginx 2>/dev/null
   docker run -d --name constitution_rag_nginx \
     --restart unless-stopped \
     --network constitution_rag_net \
     -p 8090:80 \
     -v /root/constitution-rag/nginx.conf:/etc/nginx/nginx.conf:ro \
     nginx:alpine

⚠️ docker build --no-cache ОБЯЗАТЕЛЕН:
   Без --no-cache Docker может подхватить кэш чужого образа.
```

### .env файлы

| Файл | Для чего | Ключевые переменные |
|---|---|---|
| `/root/constitution-rag/.env` | API-контейнер (`--env-file`) | `OPENAI_API_KEY`, `OPENAI_MODEL=gpt-4.1-mini`, `DB_HOST=constitution_rag_db`, `DB_PORT=5432`, `DB_PASSWORD=...` |
| `/opt/constitution-rag/.env` | DB-контейнер (docker-compose) | `DATABASE_URL`, `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD` |

**ВАЖНО**: В `.env` для API `DB_HOST=constitution_rag_db` (имя контейнера в Docker-сети), `DB_PORT=5432` (внутренний порт). НЕ `127.0.0.1` и НЕ `55432`.

DB password: `ConstitutionRag_2026_Strong_Pass_Change_This`

### Файлы внутри Docker-образа

- `app/` — весь Python-код
- `main.py` — FastAPI entry point
- `requirements.txt` — зависимости
- `static/index.html` — фронтенд

**Монтируется volume** (не в образе):
- `docs/system_prompt_canonical_v1.md` — загружается `answer_runner.py` при старте

### Проверка после деплоя

```bash
# 1. Контейнеры запущены
docker ps --format 'table {{.Names}}\t{{.Status}}' | grep constitution_rag

# 2. Сети подключены
docker inspect constitution_rag_api --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}'
# Ожидаем: constitution_rag_net constitution-rag_default

# 3. Health
curl http://localhost:8090/health
# или изнутри:
docker exec constitution_rag_api curl -s http://localhost:8000/health
# Ожидаем: {"status":"ok","db":"ok","uptime_s":...,"model":"gpt-4.1-mini"}

# 4. Тест API
curl -s -X POST http://localhost:8090/api/ask \
  -H 'Content-Type: application/json' \
  -d '{"query":"Что говорится о свободе слова?"}' | python3 -m json.tool

# 5. Файлы внутри контейнера
docker exec constitution_rag_api ls /app/app/
# Ожидаем: __init__.py  answer_runner.py  conversation_classifier.py  db.py
#          faq_cache.json  faq_match.py  intent_rewriter.py  retrieval_runner.py
```

### Типичные грабли (уже наступали)

1. **`docker exec` показывает чужие файлы** → забыл `--no-cache` при build
2. **`/api/ask` возвращает 404** → эндпоинт `/api/ask`, не `/ask`
3. **Field name error** → поле называется `query`, НЕ `question`
4. **DB connection refused** → `constitution_rag_db` не запущен или API не подключён к сети `constitution-rag_default`
5. **Nginx 502** → API не подключён к `constitution_rag_net`
6. **"парламент" возвращает 0 chunks** → в normalize_query добавлены синонимы парламент→курултай
7. **Followup не работает** → нужен `history` в запросе + intent_rewriter

---

## Архитектура пайплайна обработки запросов

```
User query
  │
  ├─ 1. detect_language() → ru / kz / en
  │
  ├─ 2. classify_conversational() → greeting / smalltalk / meta / followup / null
  │     ├─ greeting/smalltalk → статический ответ (instant)
  │     ├─ meta → LLM без retrieval (system_prompt + META_SYSTEM_ADDENDUM)
  │     ├─ followup → LLM без retrieval (system_prompt + FOLLOWUP_SYSTEM_ADDENDUM + history)
  │     └─ null → продолжаем
  │
  ├─ 3. faq_lookup() → FAQ cache (только если нет history)
  │     ├─ match (score ≥ 0.82) → кэшированный ответ (instant)
  │     └─ no match → продолжаем
  │
  ├─ 4. rewrite_query() → Intent rewriter (LLM, ~0.5-1s)
  │     ├─ needs_retrieval=false → LLM без retrieval
  │     └─ needs_retrieval=true → продолжаем
  │
  └─ 5. run_retrieval(rewritten_query) → RAG pipeline
        ├─ classify_query() → exact / comparison / broad / ordinary / explanation / mixed
        ├─ route to appropriate retrieval function
        ├─ build_user_prompt(original_query, payload)
        └─ LLM with system_prompt + history + context → grounded answer
```

### Ключевые модули (app/)

| Файл | Назначение |
|---|---|
| `answer_runner.py` | Загрузка system prompt (cached), OpenAI client (singleton), build_user_prompt, format_row |
| `retrieval_runner.py` | run_retrieval, classify_query, normalize_query (с синонимами), 15+ retrieval функций |
| `conversation_classifier.py` | classify_conversational: greeting/smalltalk/meta/followup patterns |
| `intent_rewriter.py` | LLM-rewriter: переформулирует запрос с учётом history для лучшего retrieval |
| `faq_match.py` | FAQ cache: fuzzy matching (SequenceMatcher, threshold 0.82) |
| `db.py` | ThreadedConnectionPool (1-5), fetch_all с rollback |
| `faq_cache.json` | 30 предгенерированных FAQ-ответов |

### API Endpoints (main.py)

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/health` | Liveness + DB check. `{"status":"ok","db":"ok","model":"gpt-4.1-mini"}` |
| POST | `/api/ask` | Синхронный ответ. Body: `{"query":"...", "history":[...]}` |
| POST | `/api/ask/stream` | SSE-стриминг. Events: `meta`, `text` (delta), `done`, `error` |
| GET | `/` | Фронтенд (static/index.html) |

Request body:
```json
{
  "query": "Что говорится о свободе слова?",
  "history": [
    {"role": "user", "content": "Привет"},
    {"role": "assistant", "content": "Здравствуйте! ..."}
  ]
}
```

---

## База данных

### Состояние (2026-03-14)

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
| `krk_2026_faq_extra_ru` | 55 | ru | FAQ Extra | Расширенный |
| `krk_2026_faq_extra_kz` | 63 | kz | FAQ Extra | Расширенный |
| `krk_2026_faq_extra_en` | 53 | en | FAQ Extra | Расширенный |
| `krk_1995_deprecated_ru` | 103 | ru | Historical | Только comparison |
| `krk_1995_deprecated_kz` | 100 | kz | Historical | Только comparison |
| `krk_2026_ce_lines_ru` | 91 | ru | RESTRICTED | **НЕ используется** |

### Приоритет источников

```
norm > commentary > faq > historical/deprecated
```

`1995 deprecated` **не должен** подмешиваться как текущая норма.

---

## Структура репозитория

```
constitution-rag/
├── app/
│   ├── __init__.py             — package marker
│   ├── answer_runner.py        — build_user_prompt, load_system_prompt (cached), get_client (singleton)
│   ├── retrieval_runner.py     — run_retrieval, classify_query, normalize_query, 15 datasets routing
│   ├── conversation_classifier.py — greeting/smalltalk/meta/followup classifier
│   ├── intent_rewriter.py      — LLM query rewriter (cached client)
│   ├── faq_match.py            — FAQ fuzzy cache (SequenceMatcher, 0.82 threshold)
│   ├── faq_cache.json          — 30 pre-generated FAQ answers
│   └── db.py                   — ThreadedConnectionPool, fetch_all with rollback
├── main.py                     — FastAPI: /health, /api/ask, /api/ask/stream (SSE)
├── Dockerfile                  — python:3.12-slim, healthcheck curl
├── .dockerignore               — excludes raw/, normalized/, .venv/, .git/
├── docker-compose.yml          — ⚠️ для FRESH deployment ТОЛЬКО
├── nginx.conf                  — proxy_pass to api:8000, proxy_buffering off (SSE)
├── requirements.txt            — openai, psycopg2-binary, fastapi, uvicorn
├── static/
│   └── index.html              — Web UI: streaming, ru/kz/en selector
├── docs/
│   ├── system_prompt_canonical_v1.md    — канонический system prompt
│   ├── retrieval_policy_v1.md           — retrieval routing policy
│   ├── red_team_hostile_25.md           — тестовый пакет
│   └── qa_results_template.md           — шаблон QA-отчёта
├── qa/
│   ├── run_full30.py           — 45 тестов (RT-01..45)
│   ├── run_top10.py            — 10 критических тестов
│   └── evidence/               — QA evidence файлы
├── importers/                  — import скрипты
├── scripts/                    — extraction скрипты
├── normalized/                 — JSON чанки (15 файлов)
└── raw/                        — исходные PDF/DOCX
```

---

## Аудит и исправления (2026-03-14)

Проведён полный аудит кода. Найдено **37 issues**, все критические исправлены:

### Исправленные баги

| # | Файл | Проблема | Исправление |
|---|---|---|---|
| 1 | `main.py` | `/api/ask` не обрабатывал followup | Добавлен полный pipeline: classifier → FAQ → rewriter → retrieval |
| 2 | `main.py` | FAQ всегда возвращал `lang="ru"` | Используется `detect_language()` |
| 3 | `answer_runner.py` | Мёртвый `generate_answer()` (не вызывается) | Удалён |
| 4 | `main.py` | Двойной import `FileResponse` | Убран дубликат |
| 5 | `app/__init__.py` | Отсутствовал package marker | Создан |
| 6 | `db.py` | `SimpleConnectionPool` не потокобезопасен | → `ThreadedConnectionPool` + `threading.Lock` |
| 7 | `db.py` | `fetch_all` не делал rollback при ошибке | Добавлен `conn.rollback()` в except |
| 8 | `db.py` | `DB_PORT` default `55432` (хостовый порт) | → `5432` (внутренний Docker порт) |
| 9 | `faq_match.py` | `json.load` crash на битом JSON | Обёрнут в `try/except` |
| 10 | `intent_rewriter.py` | OpenAI client создаётся при каждом вызове | Cached singleton с `threading.Lock` |
| 11 | `answer_runner.py` | System prompt загружается каждый раз | Cached в `_system_prompt_cache` |
| 12 | `answer_runner.py` | OpenAI client создаётся каждый раз | Cached singleton `get_client()` |
| 13 | `retrieval_runner.py` | "парламент" не маппится на "курултай" | Добавлены синонимы (все падежи) |

---

## QA summary

- **Top-10 critical**: 10/10 pass
- **Full 30 red-team**: 30/30 pass (expanded DB, 15 sets, 1105 chunks)
- **Production model**: gpt-4.1-mini
- **Open P0**: 0
- **Open P1**: 0

---

## Fresh-dialog handoff

Если работа переносится в новый диалог:

1. **Прочитать этот README целиком**
2. `git log --oneline -5` — текущий коммит
3. `docker ps --format 'table {{.Names}}\t{{.Status}}'` — контейнеры
4. `docker inspect constitution_rag_api --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}'` — сети
5. `curl http://localhost:8090/health` — health check
6. `docker exec constitution_rag_api ls /app/app/` — файлы внутри
7. Решить направление работы

---

## Boundary rule

Работая внутри `constitution-rag`, не уходить в `/opt/constitution/app/`, контейнер `constitution_api` или сеть `constitution_net` без прямого указания пользователя.
