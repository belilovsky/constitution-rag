import re
from app.db import fetch_all


# ── Dataset registry (all 15 datasets) ──────────────────────────────
DOCS = {
    # Norm layer
    "norm_ru": "krk_2026_norm_ru",
    "norm_kz": "krk_2026_norm_kz",
    # Commentary layer
    "comm_ru": "krk_2026_comm_ru",
    "comm_kz": "krk_2026_comm_kz",
    # Comparison layer
    "comp_ru": "krk_2026_comp_ru",
    "comp_kz": "krk_2026_comp_kz",
    # History layer
    "hist_ru": "krk_2026_hist_ru",
    "hist_kz": "krk_2026_hist_kz",
    # Practice layer
    "prac_ru": "krk_2026_prac_ru",
    "prac_kz": "krk_2026_prac_kz",
    # FAQ layer
    "faq_ru": "krk_2026_faq_ru",
    "faq_kz": "krk_2026_faq_kz",
    # Glossary layer
    "glos_ru": "krk_2026_glos_ru",
    "glos_kz": "krk_2026_glos_kz",
    # Index layer
    "indx_ru": "krk_2026_indx_ru",
}


# ── Language detection ───────────────────────────────────────────────
_KZ_CHARS = re.compile(r"[әіңғүұқөһ]", re.IGNORECASE)


def detect_language(text: str) -> str:
    """Return 'kz' if Kazakh script chars found, else 'ru'."""
    return "kz" if _KZ_CHARS.search(text) else "ru"


# ── Synonym expansion ───────────────────────────────────────────────

_SYNONYMS_RU: dict[str, list[str]] = {
    # Constitutional body names
    "конституционный суд":  ["конституционный совет"],
    "конституционный совет": ["конституционный суд"],
    "мажилис":  ["нижняя палата", "парламент"],
    "сенат":    ["верхняя палата", "парламент"],
    "парламент": ["мажилис", "сенат"],
    # Kyrgyz-specific synonyms
    "курултай": [
        "парламент",
        "Парламент",
        "ПАРЛАМЕНТ",
        "парламента",
        "Парламента",
        "парламенте",
        "Парламенте",
        "парламенту",
        "Парламенту",
        "парламентом",
        "Парламентом",
        "парламентов",
        "Парламентов",
    ],
    "парламент": [
        "курултай",
        "Курултай",
        "КУРУЛТАЙ",
        "курултая",
        "Курултая",
        "курултае",
        "Курултае",
        "курултаю",
        "Курултаю",
        "курултаем",
        "Курултаем",
        "курултаев",
        "Курултаев",
    ],
}

_SYNONYMS_KZ: dict[str, list[str]] = {
    "конституциялық сот":   ["конституциялық кеңес"],
    "конституциялық кеңес": ["конституциялық сот"],
    "мәжіліс": ["төменгі палата", "парламент"],
    "сенат":   ["жоғарғы палата", "парламент"],
    "парламент": ["мәжіліс", "сенат"],
}


def expand_synonyms(query: str, lang: str) -> list[str]:
    """
    Return a list of extra keyword strings derived from synonym expansion.
    Each entry is a phrase that should be OR-ed into the search.
    """
    syns = _SYNONYMS_RU if lang == "ru" else _SYNONYMS_KZ
    extras: list[str] = []
    q_lower = query.lower()
    for term, replacements in syns.items():
        if term in q_lower:
            extras.extend(replacements)
    return extras


# ── Retrieval ──────────────────────────────────────────────────────

TOP_K = int(os.environ.get("RETRIEVAL_TOP_K", "5"))
MIN_SCORE = float(os.environ.get("RETRIEVAL_MIN_SCORE", "0.25"))


async def run_retrieval(query: str, top_k: int = TOP_K) -> list[dict]:
    """
    Retrieve top-K chunks across all datasets.

    Strategy:
      1. Detect language
      2. Expand synonyms
      3. Query every dataset with pgvector cosine similarity
      4. Merge, deduplicate, sort by score, return top_k
    """
    lang = detect_language(query)
    synonym_extras = expand_synonyms(query, lang)

    # Build the list of query strings to run
    queries = [query] + synonym_extras

    all_chunks: list[dict] = []
    seen_ids: set[str] = set()

    for q in queries:
        for dataset_key, table in DOCS.items():
            try:
                rows = fetch_all(
                    f"""
                    SELECT id, content, metadata,
                           1 - (embedding <=> ai.openai_embed('text-embedding-3-small', %s)) AS score
                    FROM {table}
                    WHERE 1 - (embedding <=> ai.openai_embed('text-embedding-3-small', %s)) > %s
                    ORDER BY score DESC
                    LIMIT %s
                    """,
                    (q, q, MIN_SCORE, top_k),
                )
                for row in rows:
                    chunk_id = str(row[0])
                    if chunk_id not in seen_ids:
                        seen_ids.add(chunk_id)
                        all_chunks.append({
                            "id": chunk_id,
                            "content": row[1],
                            "metadata": row[2] or {},
                            "score": float(row[3]),
                            "dataset": dataset_key,
                        })
            except Exception as exc:  # noqa: BLE001
                logger.warning("retrieval error in %s: %s", table, exc)

    # Sort by score descending and return top_k
    all_chunks.sort(key=lambda c: c["score"], reverse=True)
    return all_chunks[:top_k]
