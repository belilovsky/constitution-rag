"""
Intent rewriter — the "brain" layer between user input and retrieval.

Takes the raw user query + conversation history and produces:
1. A rewritten search query optimized for retrieval
2. A detected intent (comparison, explanation, exact, etc.)
3. Whether retrieval is needed at all

Uses a fast, cheap LLM call (gpt-4.1-mini with low max_tokens).
This adds ~0.5-1s latency but dramatically improves quality for:
- Follow-up questions ("чем это лучше?", "а в 1995?", "подробнее")
- Vague queries ("расскажи что нового", "что интересного")
- Context-dependent queries that reference previous answers
"""

import json
import logging
from typing import Any

from app.answer_runner import get_client, get_model_name

logger = logging.getLogger("constitution_rag")

REWRITER_SYSTEM_PROMPT = """Ты — модуль переформулировки запросов для справочного бота по Конституции Казахстана.

Твоя задача: получить текущий вопрос пользователя и историю диалога, и выдать ОДИН JSON-объект:

{
  "rewritten_query": "...",
  "intent": "...",
  "needs_retrieval": true/false,
  "note": "..."
}

Поля:
- rewritten_query: чёткий, явный вопрос для поиска по базе конституционных текстов. 
  Если пользователь говорит "чем это лучше?" после обсуждения статьи 22 — перепиши как "Сравни статью 22 Конституции 2026 и Конституции 1995 года".
  Если пользователь говорит "расскажи что нового" — перепиши как "Какие основные изменения в проекте Конституции 2026 года по сравнению с 1995 годом".
  Если пользователь говорит "подробнее" — расшифруй из истории, о чём шла речь, и сформулируй конкретный запрос.
  Всегда пиши rewritten_query на русском.

- intent: один из вариантов:
  "exact" — запрос конкретной статьи/пункта
  "comparison" — сравнение 1995 vs 2026
  "explanation" — объяснение, обзор, что нового
  "broad" — широкий обзор темы
  "ordinary" — обычный вопрос по содержанию
  "smalltalk" — светская беседа, не про конституцию (как дела, спасибо, пока)
  "meta" — вопрос о боте (что ты умеешь, как работаешь)

- needs_retrieval: true если нужен поиск по базе, false для smalltalk/meta

- note: короткая заметка (1 предложение) о том, что ты понял из контекста. Это помогает для отладки.

Правила:
1. Если в истории обсуждалась конкретная статья и пользователь спрашивает "а раньше?" / "чем отличается?" / "чем лучше?" — это comparison по той же статье.
2. Если вопрос очень короткий ("ещё", "дальше", "подробнее") и есть история — продолжи тему из истории.
3. Если вопрос не про конституцию и не мета — это smalltalk.
4. Для smalltalk rewritten_query = оригинальный вопрос, needs_retrieval = false.
5. Не добавляй информации, которой нет в вопросе и истории.
6. Отвечай ТОЛЬКО JSON, без пояснений, без markdown."""


def rewrite_query(
    query: str,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """
    Rewrite user query using conversation history for better retrieval.

    Returns dict with keys:
        rewritten_query: str
        intent: str
        needs_retrieval: bool
        note: str
    """
    client = get_client()
    model = get_model_name()

    # Build messages: system + last few history turns + current query
    messages = [{"role": "system", "content": REWRITER_SYSTEM_PROMPT}]

    # Include last 6 messages of history for context
    if history:
        for msg in history[-6:]:
            messages.append(msg)

    messages.append({
        "role": "user",
        "content": f"Текущий вопрос пользователя: {query}",
    })

    try:
        response = client.responses.create(
            model=model,
            input=messages,
            temperature=0.0,
            max_output_tokens=300,
        )

        text = (response.output_text or "").strip()

        # Try to parse JSON
        # Handle cases where model wraps in ```json ... ```
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        result = json.loads(text)

        # Validate required fields
        return {
            "rewritten_query": result.get("rewritten_query", query),
            "intent": result.get("intent", "ordinary"),
            "needs_retrieval": result.get("needs_retrieval", True),
            "note": result.get("note", ""),
        }

    except Exception as e:
        logger.warning("Intent rewriter failed: %s — falling back to original query", e)
        # Fallback: return original query as-is
        return {
            "rewritten_query": query,
            "intent": "ordinary",
            "needs_retrieval": True,
            "note": f"rewriter_error: {e}",
        }
