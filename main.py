"""
constitution-rag — FastAPI application.

Endpoints:
    GET  /health          — liveness / readiness probe
    POST /api/ask         — synchronous answer (JSON)
    POST /api/ask/stream  — streaming answer (SSE)
"""

import os
import time
import uuid
import json
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.answer_runner import (
    generate_answer,
    load_system_prompt,
    build_user_prompt,
    get_client,
    get_model_name,
    SAFE_FAILURE_TEXT,
)
from app.retrieval_runner import run_retrieval
from app.db import get_conn, put_conn, fetch_all
from app.faq_match import faq_lookup
from app.conversation_classifier import (
    classify_conversational,
    META_SYSTEM_ADDENDUM,
    FOLLOWUP_SYSTEM_ADDENDUM,
)
from app.retrieval_runner import detect_language

logger = logging.getLogger("constitution_rag")


# ── Startup / shutdown ──────────────────────────────────────────────

_BOOT_TIME: float = 0.0


def _ensure_query_log_table():
    """Create query_log table if it does not exist."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS query_log (
                    id            BIGSERIAL PRIMARY KEY,
                    request_id    TEXT        NOT NULL,
                    ts            TIMESTAMPTZ NOT NULL DEFAULT now(),
                    query         TEXT        NOT NULL,
                    lang          TEXT,
                    mode          TEXT,
                    chunks_used   INT,
                    answer_len    INT,
                    latency_ms    INT,
                    model         TEXT,
                    error         TEXT
                );
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_query_log_ts
                    ON query_log (ts DESC);
            """)
        conn.commit()
    finally:
        put_conn(conn)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _BOOT_TIME
    _BOOT_TIME = time.time()
    _ensure_query_log_table()
    yield


app = FastAPI(
    title="constitution-rag",
    version="1.1.0",
    lifespan=lifespan,
)

# ── CORS ────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / response models ──────────────────────────────────────

class HistoryMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., max_length=4000)


class AskRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    history: list[HistoryMessage] = Field(
        default_factory=list,
        max_length=20,
        description="Previous conversation turns (max 20). Each: {role, content}.",
    )


class AskResponse(BaseModel):
    request_id: str
    query: str
    mode: str
    lang: str
    answer: str
    latency_ms: int


# ── Logging helper ──────────────────────────────────────────────────

def _log_query(
    request_id: str,
    query: str,
    lang: str | None,
    mode: str | None,
    chunks_used: int | None,
    answer_len: int | None,
    latency_ms: int | None,
    model: str | None,
    error: str | None = None,
):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO query_log
                    (request_id, query, lang, mode, chunks_used,
                     answer_len, latency_ms, model, error)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    request_id,
                    query[:2000],
                    lang,
                    mode,
                    chunks_used,
                    answer_len,
                    latency_ms,
                    model,
                    (error or "")[:500] if error else None,
                ),
            )
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        put_conn(conn)


def _count_chunks(payload: dict) -> int:
    """Count total retrieval chunks from any mode."""
    results = payload.get("results")
    if not results:
        return 0
    mode = payload.get("mode")
    if mode == "comparison":
        return (
            len(results.get("2026", []))
            + len(results.get("1995", []))
            + len(results.get("comparison_table", []))
        )
    if mode == "mixed":
        return sum(len(b.get("results", [])) for b in results)
    return len(results)


def _trim_history(history: list[HistoryMessage]) -> list[dict[str, str]]:
    """Convert history to OpenAI message format, keep last 10 turns max."""
    msgs = []
    for m in history[-10:]:
        msgs.append({
            "role": m.role,
            "content": m.content[:2000],
        })
    return msgs


# ── Health endpoint ─────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Liveness + basic readiness check."""
    db_ok = False
    try:
        rows = fetch_all("SELECT 1 AS ok")
        db_ok = bool(rows)
    except Exception:
        pass

    uptime_s = int(time.time() - _BOOT_TIME) if _BOOT_TIME else 0
    status = "ok" if db_ok else "degraded"
    return JSONResponse(
        status_code=200 if db_ok else 503,
        content={
            "status": status,
            "db": "ok" if db_ok else "unreachable",
            "uptime_s": uptime_s,
            "model": get_model_name(),
        },
    )


# ── Synchronous ask endpoint ───────────────────────────────────────

@app.post("/api/ask", response_model=AskResponse)
async def ask(req: AskRequest):
    request_id = uuid.uuid4().hex[:12]
    t0 = time.time()
    error_text = None

    try:
        # FAQ cache: instant response for common questions
        if not req.history:
            cached = faq_lookup(req.query)
            if cached:
                latency_ms = int((time.time() - t0) * 1000)
                _log_query(
                    request_id=request_id,
                    query=req.query,
                    lang="ru",
                    mode=f"faq_cache({cached['score']})",
                    chunks_used=0,
                    answer_len=len(cached["answer"]),
                    latency_ms=latency_ms,
                    model="cache",
                )
                return AskResponse(
                    request_id=request_id,
                    query=req.query,
                    mode=cached["mode"],
                    lang="ru",
                    answer=cached["answer"],
                    latency_ms=latency_ms,
                )

        history_msgs = _trim_history(req.history)
        result = await asyncio.to_thread(
            generate_answer, req.query, history_msgs
        )
        latency_ms = int((time.time() - t0) * 1000)

        payload = result.get("retrieval", {})
        _log_query(
            request_id=request_id,
            query=req.query,
            lang=result.get("lang"),
            mode=result.get("mode"),
            chunks_used=_count_chunks(payload),
            answer_len=len(result.get("answer", "")),
            latency_ms=latency_ms,
            model=get_model_name(),
        )

        return AskResponse(
            request_id=request_id,
            query=result["query"],
            mode=result["mode"],
            lang=result["lang"],
            answer=result["answer"],
            latency_ms=latency_ms,
        )

    except Exception as exc:
        latency_ms = int((time.time() - t0) * 1000)
        error_text = str(exc)[:500]
        logger.exception("Error in /api/ask [%s]: %s", request_id, error_text)
        _log_query(
            request_id=request_id,
            query=req.query,
            lang=None,
            mode=None,
            chunks_used=None,
            answer_len=None,
            latency_ms=latency_ms,
            model=get_model_name(),
            error=error_text,
        )
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "request_id": request_id},
        )


# ── Streaming ask endpoint (SSE) ───────────────────────────────────

@app.post("/api/ask/stream")
async def ask_stream(req: AskRequest):
    request_id = uuid.uuid4().hex[:12]

    async def event_generator():
        t0 = time.time()
        error_text = None
        full_answer = []

        try:
            lang = detect_language(req.query)

            # ── Conversational routing: greetings, meta, followup ──
            conv_type, conv_response = classify_conversational(req.query, lang)

            if conv_type == "greeting":
                # Instant greeting, no LLM or retrieval
                meta = {"request_id": request_id, "mode": "greeting", "lang": lang}
                yield f"event: meta\ndata: {json.dumps(meta, ensure_ascii=False)}\n\n"
                chunk_data = json.dumps({"text": conv_response}, ensure_ascii=False)
                yield f"event: text\ndata: {chunk_data}\n\n"
                latency_ms = int((time.time() - t0) * 1000)
                done = {"request_id": request_id, "latency_ms": latency_ms}
                yield f"event: done\ndata: {json.dumps(done)}\n\n"
                _log_query(
                    request_id=request_id, query=req.query,
                    lang=lang, mode="greeting", chunks_used=0,
                    answer_len=len(conv_response), latency_ms=latency_ms,
                    model="static",
                )
                return

            if conv_type in ("meta", "followup"):
                # LLM with special addendum, no retrieval
                sys_prompt = load_system_prompt()
                addendum = META_SYSTEM_ADDENDUM if conv_type == "meta" else FOLLOWUP_SYSTEM_ADDENDUM
                sys_prompt += addendum

                meta = {"request_id": request_id, "mode": conv_type, "lang": lang}
                yield f"event: meta\ndata: {json.dumps(meta, ensure_ascii=False)}\n\n"

                client = get_client()
                model = get_model_name()
                history_msgs = _trim_history(req.history)
                messages = [{"role": "system", "content": sys_prompt}]
                messages.extend(history_msgs)
                messages.append({"role": "user", "content": req.query})

                stream = client.responses.create(
                    model=model, input=messages,
                    temperature=0.3, stream=True,
                )
                for event in stream:
                    if hasattr(event, "type") and event.type == "response.output_text.delta":
                        delta = event.delta
                        if delta:
                            full_answer.append(delta)
                            chunk_data = json.dumps({"text": delta}, ensure_ascii=False)
                            yield f"event: text\ndata: {chunk_data}\n\n"

                answer_text = "".join(full_answer).strip()
                if not answer_text:
                    answer_text = SAFE_FAILURE_TEXT.get(lang, SAFE_FAILURE_TEXT["ru"])
                    fallback_data = json.dumps({"text": answer_text}, ensure_ascii=False)
                    yield f"event: text\ndata: {fallback_data}\n\n"

                latency_ms = int((time.time() - t0) * 1000)
                done = {"request_id": request_id, "latency_ms": latency_ms}
                yield f"event: done\ndata: {json.dumps(done)}\n\n"
                _log_query(
                    request_id=request_id, query=req.query,
                    lang=lang, mode=conv_type, chunks_used=0,
                    answer_len=len(answer_text), latency_ms=latency_ms,
                    model=model,
                )
                return

            # ── FAQ cache: instant response (only for first message, no history) ──
            if not req.history:
                cached = faq_lookup(req.query)
                if cached:
                    meta = {"request_id": request_id, "mode": cached["mode"], "lang": "ru"}
                    yield f"event: meta\ndata: {json.dumps(meta, ensure_ascii=False)}\n\n"
                    chunk_data = json.dumps({"text": cached["answer"]}, ensure_ascii=False)
                    yield f"event: text\ndata: {chunk_data}\n\n"
                    latency_ms = int((time.time() - t0) * 1000)
                    done = {"request_id": request_id, "latency_ms": latency_ms}
                    yield f"event: done\ndata: {json.dumps(done)}\n\n"
                    _log_query(
                        request_id=request_id, query=req.query,
                        lang="ru", mode=f"faq_cache({cached['score']})",
                        chunks_used=0, answer_len=len(cached["answer"]),
                        latency_ms=latency_ms, model="cache",
                    )
                    return

            # ── Normal retrieval path ──
            # 1. Retrieval (sync, in thread)
            payload = await asyncio.to_thread(run_retrieval, req.query)
            lang = payload.get("lang", "ru")
            mode = payload.get("mode", "unknown")

            # Send metadata event
            meta = {"request_id": request_id, "mode": mode, "lang": lang}
            yield f"event: meta\ndata: {json.dumps(meta, ensure_ascii=False)}\n\n"

            # 2. Build prompts
            system_prompt = load_system_prompt()
            user_prompt = build_user_prompt(req.query, payload)
            client = get_client()
            model = get_model_name()

            # 3. Build messages with history
            history_msgs = _trim_history(req.history)
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(history_msgs)
            messages.append({"role": "user", "content": user_prompt})

            # 4. Stream from OpenAI
            stream = client.responses.create(
                model=model,
                input=messages,
                temperature=0.1,
                stream=True,
            )

            for event in stream:
                if hasattr(event, "type") and event.type == "response.output_text.delta":
                    delta = event.delta
                    if delta:
                        full_answer.append(delta)
                        chunk_data = json.dumps({"text": delta}, ensure_ascii=False)
                        yield f"event: text\ndata: {chunk_data}\n\n"

            answer_text = "".join(full_answer).strip()
            if not answer_text:
                answer_text = SAFE_FAILURE_TEXT.get(lang, SAFE_FAILURE_TEXT["ru"])
                fallback_data = json.dumps({"text": answer_text}, ensure_ascii=False)
                yield f"event: text\ndata: {fallback_data}\n\n"

            latency_ms = int((time.time() - t0) * 1000)

            # Done event
            done = {"request_id": request_id, "latency_ms": latency_ms}
            yield f"event: done\ndata: {json.dumps(done)}\n\n"

            # Log
            _log_query(
                request_id=request_id,
                query=req.query,
                lang=lang,
                mode=mode,
                chunks_used=_count_chunks(payload),
                answer_len=len(answer_text),
                latency_ms=latency_ms,
                model=model,
            )

        except Exception as exc:
            latency_ms = int((time.time() - t0) * 1000)
            error_text = str(exc)[:500]
            logger.exception("Error in /api/ask/stream [%s]: %s", request_id, error_text)
            err_data = json.dumps({"error": error_text, "request_id": request_id})
            yield f"event: error\ndata: {err_data}\n\n"

            _log_query(
                request_id=request_id,
                query=req.query,
                lang=None,
                mode=None,
                chunks_used=None,
                answer_len=None,
                latency_ms=latency_ms,
                model=get_model_name(),
                error=error_text,
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── Static files (frontend) ────────────────────────────────────────

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    async def index():
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))
