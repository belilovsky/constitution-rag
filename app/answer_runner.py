import os
from pathlib import Path
from typing import Any

from openai import OpenAI

from app.retrieval_runner import run_retrieval, detect_language
from app.conversation_classifier import (
    classify_conversational,
    META_SYSTEM_ADDENDUM,
    FOLLOWUP_SYSTEM_ADDENDUM,
)
from app.intent_rewriter import rewrite_query


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
        "Ниже дан вопрос пользователя и найденные материалы по проекту constitution-rag.\n"
        "Отвечай только по найденным материалам. Не добавляй сведения от себя. "
        "Если данных недостаточно, скажи об этом прямо и кратко.\n\n"
    ),
    "kz": (
        "Төменде пайдаланушы сұрағы және constitution-rag жобасының материалдары берілген.\n"
        "Тек табылған материалдар бойынша жауап бер. Өзіңнен мәлімет қоспа. "
        "Деректер жеткіліксіз болса, тікелей және қысқаша айт.\n\n"
    ),
    "en": (
        "Below is the user's question and retrieved materials from the constitution-rag project.\n"
        "Answer only based on the retrieved materials. Do not add information on your own. "
        "If data is insufficient, say so directly and briefly.\n\n"
    ),
}


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
    return os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


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


def generate_answer(
    query: str,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Generate a grounded answer.

    Args:
        query: current user question.
        history: optional list of previous turns
                 [{"role": "user"|"assistant", "content": "..."}].
                 Used to give the LLM conversational context.
    """
    lang = detect_language(query)

    # ── Conversational routing: greetings, meta, followup ──
    conv_type, conv_response = classify_conversational(query, lang)

    if conv_type in ("greeting", "smalltalk"):
        # Instant response, no LLM needed
        return {
            "query": query,
            "mode": conv_type,
            "lang": lang,
            "answer": conv_response,
            "retrieval": {},
        }

    if conv_type == "meta":
        # Let LLM answer with special addendum, no retrieval
        system_prompt = load_system_prompt()
        system_prompt += META_SYSTEM_ADDENDUM

        client = get_client()
        model = get_model_name()

        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
        ]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": query})

        response = client.responses.create(
            model=model,
            input=messages,
            temperature=0.3,
        )

        answer_text = (response.output_text or "").strip()
        if not answer_text:
            answer_text = SAFE_FAILURE_TEXT.get(lang, SAFE_FAILURE_TEXT["ru"])

        return {
            "query": query,
            "mode": "meta",
            "lang": lang,
            "answer": answer_text,
            "retrieval": {},
        }

    # ── Intent rewriter: uses history to produce a clear retrieval query ──
    intent_result = rewrite_query(query, history)
    rewritten = intent_result["rewritten_query"]
    intent = intent_result["intent"]

    # If rewriter says no retrieval needed (smalltalk/meta detected by LLM)
    if not intent_result["needs_retrieval"]:
        if intent == "smalltalk":
            # LLM-detected smalltalk that classifier missed
            system_prompt = load_system_prompt()
            system_prompt += META_SYSTEM_ADDENDUM

            client = get_client()
            model = get_model_name()
            messages = [{"role": "system", "content": system_prompt}]
            if history:
                messages.extend(history)
            messages.append({"role": "user", "content": query})

            response = client.responses.create(
                model=model, input=messages, temperature=0.3,
            )
            answer_text = (response.output_text or "").strip()
            if not answer_text:
                answer_text = SAFE_FAILURE_TEXT.get(lang, SAFE_FAILURE_TEXT["ru"])

            return {
                "query": query,
                "mode": "smalltalk",
                "lang": lang,
                "answer": answer_text,
                "retrieval": {},
            }

    # ── Normal retrieval path (using rewritten query) ──
    payload = run_retrieval(rewritten)

    system_prompt = load_system_prompt()
    # Build user prompt with REWRITTEN query for retrieval context,
    # but include original query so LLM sees what user actually asked
    user_prompt = build_user_prompt(query, payload)

    client = get_client()
    model = get_model_name()

    # Build message list: system → history → current user prompt
    messages = [
        {"role": "system", "content": system_prompt},
    ]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_prompt})

    response = client.responses.create(
        model=model,
        input=messages,
        temperature=0.1,
    )

    answer_text = (response.output_text or "").strip()
    if not answer_text:
        answer_text = SAFE_FAILURE_TEXT.get(lang, SAFE_FAILURE_TEXT["ru"])

    return {
        "query": query,
        "mode": payload.get("mode", "unknown"),
        "lang": payload.get("lang", "ru"),
        "answer": answer_text,
        "retrieval": payload,
        "rewritten_query": rewritten,
        "intent": intent,
    }
