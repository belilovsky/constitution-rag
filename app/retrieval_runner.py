import re
from app.db import fetch_all


DOCS = {
    "norm_ru": "krk_2026_norm_ru",
    "commentary_ru": "krk_2026_commentary_ru",
    "faq_ru": "krk_2026_faq_ru",
    "deprecated_ru": "krk_1995_deprecated_ru",
}


def classify_query(query: str) -> str:
    q = query.lower()

    if re.search(r"(статья|ст\.)\s*\d+", q):
        return "exact"
    if "1995" in q and "2026" in q:
        return "comparison"
    if any(x in q for x in ["сравни", "сравнение"]):
        return "comparison"
    if any(x in q for x in ["простыми словами", "объясни проще", "объясни простыми словами", "faq"]):
        return "explanation"
    return "ordinary"


def extract_article_number(query: str):
    m = re.search(r"(?:статья|ст\.)\s*(\d+)", query.lower())
    return int(m.group(1)) if m else None


def retrieve_exact_article(article_number: int, doc_key: str = DOCS["norm_ru"], limit: int = 3):
    sql = """
    select
      d.doc_key,
      d.status,
      c.chunk_index,
      c.heading,
      c.meta,
      c.body
    from document_chunks c
    join documents d on d.id = c.document_id
    where d.doc_key = %s
      and (
        (c.meta->>'article_number') = %s
        or c.heading ilike %s
      )
    order by c.chunk_index
    limit %s
    """
    return fetch_all(sql, (doc_key, str(article_number), f"Статья {article_number}%", limit))


def retrieve_fts(query: str, doc_key: str, limit: int = 5):
    sql = """
    select
      d.doc_key,
      d.status,
      c.chunk_index,
      c.heading,
      c.meta,
      c.body,
      ts_rank(c.body_tsv, plainto_tsquery('simple', %s)) as rank
    from document_chunks c
    join documents d on d.id = c.document_id
    where d.doc_key = %s
      and c.body_tsv @@ plainto_tsquery('simple', %s)
    order by rank desc, c.chunk_index
    limit %s
    """
    return fetch_all(sql, (query, doc_key, query, limit))


def retrieve_trgm(query: str, doc_key: str, limit: int = 5):
    sql = """
    select
      d.doc_key,
      d.status,
      c.chunk_index,
      c.heading,
      c.meta,
      c.body,
      greatest(
        similarity(coalesce(c.heading, ''), %s),
        similarity(c.body, %s)
      ) as sim
    from document_chunks c
    join documents d on d.id = c.document_id
    where d.doc_key = %s
    order by sim desc, c.chunk_index
    limit %s
    """
    return fetch_all(sql, (query, query, doc_key, limit))


def retrieve_ordinary(query: str):
    rows = retrieve_fts(query, DOCS["norm_ru"], limit=5)
    if rows:
        return rows
    return retrieve_trgm(query, DOCS["norm_ru"], limit=5)


def retrieve_explanation(query: str):
    norm_rows = retrieve_fts(query, DOCS["norm_ru"], limit=3)
    commentary_rows = retrieve_fts(query, DOCS["commentary_ru"], limit=2)
    if norm_rows:
        return norm_rows + commentary_rows
    faq_rows = retrieve_fts(query, DOCS["faq_ru"], limit=2)
    return commentary_rows + faq_rows


def retrieve_comparison(query: str):
    current_rows = retrieve_fts(query, DOCS["norm_ru"], limit=3)
    historical_rows = retrieve_fts(query, DOCS["deprecated_ru"], limit=3)
    return {
        "2026": current_rows,
        "1995": historical_rows,
    }


def run_retrieval(query: str):
    mode = classify_query(query)

    if mode == "exact":
        article_number = extract_article_number(query)
        rows = retrieve_exact_article(article_number) if article_number is not None else []
        if not rows:
            rows = retrieve_ordinary(query)
        return {"mode": mode, "results": rows}

    if mode == "comparison":
        return {"mode": mode, "results": retrieve_comparison(query)}

    if mode == "explanation":
        return {"mode": mode, "results": retrieve_explanation(query)}

    return {"mode": mode, "results": retrieve_ordinary(query)}
