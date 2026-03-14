import os
import threading
from pathlib import Path
from typing import Any

from openai import OpenAI


BASE_DIR = Path(__file__).resolve().parent.parent
SYSTEM_PROMPT_PATH = BASE_DIR / "docs" / "system_prompt_canonical_v1.md"

SAFE_FAILURE_TEXT = {
    "ru": (
        "По этой теме в доступных материалах ничего не нашлось. "
        "Если уточнишь статью или тему — попробую снова."
    ),
    "kz": (
        "Бұл тақырып бойынша қол жетімді материалдардан ештеңе табылмады. "
        "Мақаланы немесе тақырыпты нақтыласаң — қайта іздеймін."
    ),
    "en": (
        "Nothing came up on this topic in the available materials. "
        "If you specify an article or topic, I can try again."
    ),
}

USER_PROMPT_TEMPLATE = {
    "ru": (
        "Ниже — вопрос и релевантные фрагменты из Конституции и сопутствующих документов.\n"
        "Дай полный, понятный и полезный ответ. "
        "Объединяй информацию из разных фрагментов в единый связный текст. "
        "Объясняй простым языком, избегай канцелярита. "
        "Не упоминай, что ты ищешь по материалам — отвечай как знающий эксперт. "
        "Не придумывай того, чего нет в контексте.\n\n"
    ),
    "kz": (
        "Төменде — сұрақ және Конституция мен қосымша құжаттардан алынған үзінділер.\n"
        "Толық, түсінікті және пайдалы жауап бер. "
        "Әр түрлі үзінділерден ақпаратты біріктіріп, байланыстыра жаз. "
        "Қарапайым тілмен түсіндір. "
        "Материалдардан іздейтініңді айтпа — білімді маман ретінде жауап бер. "
        "Контексте жоқ мәліметтерді ойдан шығарма.\n\n"
    ),
    "en": (
        "Below is the question and relevant excerpts from the Constitution and related documents.\n"
        "Give a complete, clear, and helpful answer. "
        "Synthesize information from different excerpts into a coherent response. "
        "Explain in plain language. "
        "Do not mention that you are searching materials — respond as a knowledgeable expert. "
        "Do not make up information not present in the context.\n\n"
    ),
}

# ── Cached singletons ──────────────────────────────────────────────

_system_prompt_cache: str | None = None
_client_cache: OpenAI | None = None
_client_lock = threading.Lock()


def load_system_prompt() -> str:
    """Load system prompt from file (cached after first read)."""
    global _system_prompt_cache
    if _system_prompt_cache is None:
        _system_prompt_cache = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()
    return _system_prompt_cache


def get_client() -> OpenAI:
    """Get OpenAI client (singleton, thread-safe)."""
    global _client_cache
    if _client_cache is None:
        with _client_lock:
            if _client_cache is None:
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise RuntimeError("OPENAI_API_KEY is not set")
                base_url = os.getenv("OPENAI_BASE_URL")
                if base_url:
                    _client_cache = OpenAI(api_key=api_key, base_url=base_url)
                else:
                    _client_cache = OpenAI(api_key=api_key)
    return _client_cache


def get_model_name() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


# ── Helpers ─────────────────────────────────────────────────────────

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
        rows.extend(results.get("comparison_table", []))
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

        # NEW: comparison table from ce_comparison_ru
        comp_table = results.get("comparison_table", [])
        if comp_table:
            parts.extend(["", "COMPARISON_TABLE (structured 1995↔2026 comparison, layer=comparison-table):"])
            for row in comp_table:
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
    lang = payload.get("lang", "ru")
    context_block = build_context_block(payload)
    template = USER_PROMPT_TEMPLATE.get(lang, USER_PROMPT_TEMPLATE["ru"])

    return (
        template
        + f"QUESTION:\n{query}\n\n"
        + f"{context_block}\n"
    )


def has_any_results(payload: dict[str, Any]) -> bool:
    return len(flatten_payload(payload)) > 0
