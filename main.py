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
    load_system_prompt,
    build_user_prompt,
    get_client,
    get_model_name,
    SAFE_FAILURE_TEXT,
)
from app.retrieval_runner import run_retrieval, detect_language
from app.db import get_conn, put_conn, fetch_all
from app.faq_match import faq_lookup
from app.conversation_classifier import (
    classify_conversational,
    META_SYSTEM_ADDENDUM,
    FOLLOWUP_SYSTEM_ADDENDUM,
)
from app.intent_rewriter import rewrite_query

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
                    id          SERIAL PRIMARY KEY,
                    ts          TIMESTAMPTZ NOT NULL DEFAULT now(),
                    session_id  TEXT,
                    question    TEXT,
                    answer      TEXT,
                    latency_ms  INTEGER,
                    model       TEXT,
                    datasets    TEXT[],
                    chunks_used INTEGER
                )
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
    title="Constitution RAG",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static files ────────────────────────────────────────────────────

try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception:
    pass


@app.get("/", include_in_schema=False)
async def root():
    try:
        return FileResponse("static/index.html")
    except Exception:
        return JSONResponse({"status": "ok"})


# ── Models ──────────────────────────────────────────────────────────

class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)
    session_id: str | None = None
    history: list[dict] | None = None


class AskResponse(BaseModel):
    answer: str
    session_id: str
    datasets: list[str]
    chunks_used: int
    latency_ms: int


# ── Health ──────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    uptime = round(time.time() - _BOOT_TIME, 1)
    return {"status": "ok", "uptime_seconds": uptime}


# ── Helpers ─────────────────────────────────────────────────────────

def _log_query(
    session_id: str,
    question: str,
    answer: str,
    latency_ms: int,
    model: str,
    datasets: list[str],
    chunks_used: int,
) -> None:
    """Fire-and-forget DB insert (best-effort)."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO query_log
                    (session_id, question, answer, latency_ms, model, datasets, chunks_used)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (session_id, question, answer, latency_ms, model, datasets, chunks_used),
            )
        conn.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("query_log insert failed: %s", exc)
    finally:
        put_conn(conn)


# ── Core pipeline ────────────────────────────────────────────────────

async def _run_pipeline(req: AskRequest) -> dict:
    """
    Full pipeline:
      1. Classify conversational / followup
      2. Rewrite intent if needed
      3. FAQ lookup
      4. Retrieval
      5. LLM answer
    Returns a dict with all fields needed for AskResponse + streaming.
    """
    t0 = time.time()
    session_id = req.session_id or str(uuid.uuid4())
    question = req.question.strip()
    history = req.history or []

    # ── 1. Classify conversational ───────────────────────────────────
    clf = await classify_conversational(question, history)

    if clf["type"] == "meta":
        answer = clf["reply"]
        latency_ms = int((time.time() - t0) * 1000)
        _log_query(session_id, question, answer, latency_ms, "meta", [], 0)
        return {
            "answer": answer,
            "session_id": session_id,
            "datasets": [],
            "chunks_used": 0,
            "latency_ms": latency_ms,
            "system_addendum": META_SYSTEM_ADDENDUM,
            "rewritten_query": None,
        }

    system_addendum = ""
    if clf["type"] == "followup":
        system_addendum = FOLLOWUP_SYSTEM_ADDENDUM

    # ── 2. Rewrite intent ───────────────────────────────────────────
    rewritten = await rewrite_query(question, history)
    effective_query = rewritten if rewritten else question

    # ── 3. FAQ lookup ───────────────────────────────────────────────
    faq_lang = detect_language(question)
    faq_hit = faq_lookup(question, lang=faq_lang)
    if faq_hit:
        answer = faq_hit
        latency_ms = int((time.time() - t0) * 1000)
        _log_query(session_id, question, answer, latency_ms, "faq", [], 0)
        return {
            "answer": answer,
            "session_id": session_id,
            "datasets": [],
            "chunks_used": 0,
            "latency_ms": latency_ms,
            "system_addendum": system_addendum,
            "rewritten_query": rewritten,
        }

    # ── 4. Retrieval ────────────────────────────────────────────────
    chunks = await run_retrieval(effective_query)

    # ── 5. LLM answer ───────────────────────────────────────────────
    client = get_client()
    model = get_model_name()
    sys_prompt = load_system_prompt()
    if system_addendum:
        sys_prompt = sys_prompt + "\n\n" + system_addendum

    user_prompt = build_user_prompt(effective_query, chunks, history)

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )

    answer = response.choices[0].message.content or SAFE_FAILURE_TEXT
    datasets = sorted({c["dataset"] for c in chunks})
    chunks_used = len(chunks)
    latency_ms = int((time.time() - t0) * 1000)

    _log_query(session_id, question, answer, latency_ms, model, datasets, chunks_used)

    return {
        "answer": answer,
        "session_id": session_id,
        "datasets": datasets,
        "chunks_used": chunks_used,
        "latency_ms": latency_ms,
        "system_addendum": system_addendum,
        "rewritten_query": rewritten,
    }


# ── /api/ask ────────────────────────────────────────────────────────

@app.post("/api/ask", response_model=AskResponse)
async def ask(req: AskRequest, request: Request):
    """
    Synchronous answer endpoint.
    Runs the full pipeline and returns a single JSON response.
    """
    try:
        result = await _run_pipeline(req)
        return AskResponse(
            answer=result["answer"],
            session_id=result["session_id"],
            datasets=result["datasets"],
            chunks_used=result["chunks_used"],
            latency_ms=result["latency_ms"],
        )
    except Exception as exc:
        logger.exception("ask error: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )


# ── /api/ask/stream ──────────────────────────────────────────────────

@app.post("/api/ask/stream")
async def ask_stream(req: AskRequest, request: Request):
    """
    Streaming answer endpoint (Server-Sent Events).
    Runs classifier + rewriter + FAQ synchronously, then streams the LLM response.
    """
    t0 = time.time()
    session_id = req.session_id or str(uuid.uuid4())
    question = req.question.strip()
    history = req.history or []

    async def event_stream():
        try:
            # ── 1. Classify ──────────────────────────────────────────
            clf = await classify_conversational(question, history)

            if clf["type"] == "meta":
                answer = clf["reply"]
                latency_ms = int((time.time() - t0) * 1000)
                _log_query(session_id, question, answer, latency_ms, "meta", [], 0)
                yield f"data: {json.dumps({'token': answer, 'done': False})}\n\n"
                yield f"data: {json.dumps({'done': True, 'session_id': session_id, 'datasets': [], 'chunks_used': 0, 'latency_ms': latency_ms})}\n\n"
                return

            system_addendum = ""
            if clf["type"] == "followup":
                system_addendum = FOLLOWUP_SYSTEM_ADDENDUM

            # ── 2. Rewrite ───────────────────────────────────────────
            rewritten = await rewrite_query(question, history)
            effective_query = rewritten if rewritten else question

            # ── 3. FAQ ───────────────────────────────────────────────
            faq_lang = detect_language(question)
            faq_hit = faq_lookup(question, lang=faq_lang)
            if faq_hit:
                answer = faq_hit
                latency_ms = int((time.time() - t0) * 1000)
                _log_query(session_id, question, answer, latency_ms, "faq", [], 0)
                yield f"data: {json.dumps({'token': answer, 'done': False})}\n\n"
                yield f"data: {json.dumps({'done': True, 'session_id': session_id, 'datasets': [], 'chunks_used': 0, 'latency_ms': latency_ms})}\n\n"
                return

            # ── 4. Retrieval ────────────────────────────────────────
            chunks = await run_retrieval(effective_query)

            # ── 5. Stream LLM ───────────────────────────────────────
            client = get_client()
            model = get_model_name()
            sys_prompt = load_system_prompt()
            if system_addendum:
                sys_prompt = sys_prompt + "\n\n" + system_addendum

            user_prompt = build_user_prompt(effective_query, chunks, history)

            full_answer = ""
            stream = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                stream=True,
            )

            async for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    full_answer += delta
                    yield f"data: {json.dumps({'token': delta, 'done': False})}\n\n"

            datasets = sorted({c["dataset"] for c in chunks})
            chunks_used = len(chunks)
            latency_ms = int((time.time() - t0) * 1000)

            _log_query(session_id, question, full_answer, latency_ms, model, datasets, chunks_used)

            yield f"data: {json.dumps({'done': True, 'session_id': session_id, 'datasets': datasets, 'chunks_used': chunks_used, 'latency_ms': latency_ms})}\n\n"

        except Exception as exc:
            logger.exception("stream error: %s", exc)
            yield f"data: {json.dumps({'error': 'Internal server error', 'done': True})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ── /api/history ──────────────────────────────────────────────────────

@app.get("/api/history")
async def history(limit: int = 50):
    """Return the last `limit` rows from query_log."""
    rows = fetch_all(
        "SELECT ts, session_id, question, answer, latency_ms, model, datasets, chunks_used "
        "FROM query_log ORDER BY ts DESC LIMIT %s",
        (limit,),
    )
    return [
        {
            "ts": r[0].isoformat() if hasattr(r[0], "isoformat") else str(r[0]),
            "session_id": r[1],
            "question": r[2],
            "answer": r[3],
            "latency_ms": r[4],
            "model": r[5],
            "datasets": r[6],
            "chunks_used": r[7],
        }
        for r in rows
    ]
