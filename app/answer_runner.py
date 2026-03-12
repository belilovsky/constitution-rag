import os
import json
from pathlib import Path
from openai import OpenAI
from app.retrieval_runner import run_retrieval

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "docs" / "system_prompt_canonical_v1.md"
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")
MAX_TOKENS = int(os.environ.get("OPENAI_MAX_TOKENS", "1200"))


def load_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


def format_chunk(row: dict) -> str:
    doc_key = row.get("doc_key", "")
    heading = row.get("heading") or ""
    meta = row.get("meta") or {}
    body = (row.get("body") or "").strip()
    article = meta.get("article_number") or meta.get("article")
    status = row.get("status", "")

    label = f"[{doc_key}]"
    if article:
        label += f" Статья {article}"
    if heading:
        label += f" | {heading}"
    if status:
        label += f" | статус: {status}"

    return f"{label}\n{body}"


def build_context(payload: dict) -> str:
    mode = payload.get("mode", "ordinary")
    results = payload.get("results", [])

    if mode == "comparison" and isinstance(results, dict):
        parts = []
        if results.get("2026"):
            parts.append("=== СЛОЙ 2026 ===")
            parts.extend(format_chunk(r) for r in results["2026"])
        if results.get("1995"):
            parts.append("=== СЛОЙ 1995 (historical/deprecated) ===")
            parts.extend(format_chunk(r) for r in results["1995"])
        return "\n\n".join(parts)

    if mode == "mixed" and isinstance(results, list):
        parts = []
        for bundle in results:
            subquery = bundle.get("subquery", "")
            rows = bundle.get("results", [])
            parts.append(f"--- подзапрос: {subquery} ---")
            parts.extend(format_chunk(r) for r in rows)
        return "\n\n".join(parts)

    if isinstance(results, list):
        return "\n\n".join(format_chunk(r) for r in results)

    return ""


def count_chunks(payload: dict) -> int:
    results = payload.get("results", [])
    if isinstance(results, list):
        if results and isinstance(results[0], dict) and "results" in results[0]:
            return sum(len(b.get("results", [])) for b in results)
        return len(results)
    if isinstance(results, dict):
        return len(results.get("2026", [])) + len(results.get("1995", []))
    return 0


def build_user_message(query: str, context: str, mode: str) -> str:
    if not context.strip():
        return (
            f"Вопрос: {query}\n\n"
            "[Контекст: по данному запросу релевантные материалы не найдены. "
            "Применяй safe failure формулу согласно системной инструкции.]"
        )
    return (
        f"Вопрос: {query}\n\n"
        f"Режим запроса: {mode}\n\n"
        f"Найденные материалы из базы знаний:\n\n{context}"
    )


def ask(query: str) -> dict:
    """Main entrypoint. Returns dict with answer, mode, chunk_count."""
    payload = run_retrieval(query)
    mode = payload.get("mode", "ordinary")
    context = build_context(payload)
    chunk_count = count_chunks(payload)

    system_prompt = load_system_prompt()
    user_message = build_user_message(query, context, mode)

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )

    answer = response.choices[0].message.content.strip()
    return {
        "query": query,
        "mode": mode,
        "chunk_count": chunk_count,
        "answer": answer,
    }
