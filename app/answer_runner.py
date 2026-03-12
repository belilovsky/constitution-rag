import os
from pathlib import Path
from typing import Any

from openai import OpenAI

from app.retrieval_runner import run_retrieval


BASE_DIR = Path(__file__).resolve().parent.parent
SYSTEM_PROMPT_PATH = BASE_DIR / "docs" / "system_prompt_canonical_v1.md"

SAFE_FAILURE_TEXT = (
    "По запросу не найдено релевантных материалов в базе знаний. "
    "Пожалуйста, уточните статью, тему или формулировку вопроса."
)


def load_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()


def get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    base_url = os.getenv("OPENAI_BASE_URL")
    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url)

    return OpenAI(api_key=api_key)


def get_model_name() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def clip_text(text: str, limit: int = 4000) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def format_row(row: dict[str, Any]) -> str:
    doc_key = row.get("doc_key", "")
    status = row.get("status", "")
    heading = row.get("heading", "")
    chunk_index = row.get("chunk_index", "")
    meta = row.get("meta") or {}
    body = clip_text(row.get("body", ""), limit=4000)

    lines = [
        f"doc_key: {doc_key}",
        f"status: {status}",
        f"chunk_index: {chunk_index}",
        f"heading: {heading}",
        f"meta: {meta}",
        "body:",
        body,
    ]
    return "\n".join(lines)


def flatten_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    mode = payload.get("mode")
    results = payload.get("results")

    if not results:
        return []

    if mode == "comparison":
        rows = []
        rows.extend(results.get("2026", []))
        rows.extend(results.get("1995", []))
        return rows

    if mode == "mixed":
        rows = []
        for bundle in results:
            rows.extend(bundle.get("results", []))
        return rows

    return results


def build_context_block(payload: dict[str, Any]) -> str:
    mode = payload.get("mode")
    results = payload.get("results")

    if not results:
        return "RETRIEVAL_MODE: empty\n\nRETRIEVED_CONTEXT:\n(нет найденных материалов)"

    if mode == "comparison":
        parts = ["RETRIEVAL_MODE: comparison", "", "CONTEXT_2026:"]
        for row in results.get("2026", []):
            parts.append("----")
            parts.append(format_row(row))

        parts.extend(["", "CONTEXT_1995:"])
        for row in results.get("1995", []):
            parts.append("----")
            parts.append(format_row(row))

        return "\n".join(parts)

    if mode == "mixed":
        parts = ["RETRIEVAL_MODE: mixed"]
        for idx, bundle in enumerate(results, start=1):
            parts.extend(
                [
                    "",
                    f"SUBQUERY_{idx}: {bundle.get('subquery', '')}",
                ]
            )
            for row in bundle.get("results", []):
                parts.append("----")
                parts.append(format_row(row))
        return "\n".join(parts)

    parts = [f"RETRIEVAL_MODE: {mode}", "", "RETRIEVED_CONTEXT:"]
    for row in results:
        parts.append("----")
        parts.append(format_row(row))
    return "\n".join(parts)


def build_user_prompt(query: str, payload: dict[str, Any]) -> str:
    context_block = build_context_block(payload)

    return (
        "Ниже дан вопрос пользователя и retrieved context из базы знаний проекта constitution-rag.\n"
        "Отвечай только по найденным материалам. Не добавляй сведения от себя. "
        "Если данных недостаточно, скажи об этом прямо и кратко.\n\n"
        f"QUESTION:\n{query}\n\n"
        f"{context_block}\n"
    )


def has_any_results(payload: dict[str, Any]) -> bool:
    return len(flatten_payload(payload)) > 0


def generate_answer(query: str) -> dict[str, Any]:
    payload = run_retrieval(query)

    # Always call LLM -- even with empty retrieval.
    # System prompt has rules for safe failure, meta-questions,
    # role-switch handling that require LLM judgment.
    system_prompt = load_system_prompt()
    user_prompt = build_user_prompt(query, payload)

    client = get_client()
    model = get_model_name()

    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
    )

    answer_text = (response.output_text or "").strip()
    if not answer_text:
        answer_text = SAFE_FAILURE_TEXT

    return {
        "query": query,
        "mode": payload.get("mode", "unknown"),
        "answer": answer_text,
        "retrieval": payload,
    }
