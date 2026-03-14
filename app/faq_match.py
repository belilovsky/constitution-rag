"""
FAQ instant-response cache.

If a user query closely matches a cached FAQ question,
returns the pre-generated answer instantly (no LLM call).

Matching uses normalized Levenshtein ratio (difflib).
Threshold: 0.82 (82% similarity).
"""

import json
import logging
import os
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

logger = logging.getLogger("constitution_rag")

_CACHE_PATH = Path(__file__).resolve().parent / "faq_cache.json"
_THRESHOLD = 0.82

_cache: list[dict[str, str]] | None = None


def _normalize(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\sа-яёәіңғүұқөһ]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _load_cache() -> list[dict[str, str]]:
    global _cache
    if _cache is not None:
        return _cache

    if not _CACHE_PATH.exists():
        _cache = []
        return _cache

    try:
        with open(_CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            logger.error("faq_cache.json is not a list, ignoring")
            _cache = []
        else:
            _cache = data
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to load faq_cache.json: %s", e)
        _cache = []

    return _cache


def reload_cache():
    """Force reload (e.g. after regenerating cache)."""
    global _cache
    _cache = None
    _load_cache()


def faq_lookup(query: str) -> dict[str, Any] | None:
    """
    Try to match query against FAQ cache.

    Returns dict with answer data if match found, None otherwise.
    Result format: {"answer": str, "mode": str, "source": "faq_cache", "score": float}
    """
    cache = _load_cache()
    if not cache:
        return None

    norm_query = _normalize(query)
    if len(norm_query) < 3:
        return None

    best_score = 0.0
    best_entry = None

    for entry in cache:
        cached_q = entry.get("q", "")
        norm_cached = _normalize(cached_q)

        score = SequenceMatcher(None, norm_query, norm_cached).ratio()

        if score > best_score:
            best_score = score
            best_entry = entry

    if best_score >= _THRESHOLD and best_entry and best_entry.get("a"):
        return {
            "answer": best_entry["a"],
            "mode": best_entry.get("mode", "faq_cache"),
            "source": "faq_cache",
            "score": round(best_score, 3),
            "matched_q": best_entry["q"],
        }

    return None
