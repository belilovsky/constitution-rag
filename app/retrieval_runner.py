import re
from app.db import fetch_all


DOCS = {
    "norm_ru": "krk_2026_norm_ru",
    "commentary_ru": "krk_2026_commentary_ru",
    "faq_ru": "krk_2026_faq_ru",
    "deprecated_ru": "krk_1995_deprecated_ru",
}


def normalize_query(query: str) -> str:
    q = query.lower().strip()

    replacements = {
        "президента": "президент",
        "президенту": "президент",
        "президентом": "президент",
        "президенты": "президент",
        "полномочий": "полномочия",
        "полномочиями": "полномочия",
        "правительства": "правительство",
        "правительством": "правительство",
        "судами": "суд",
        "суда": "суд",
        "судах": "суд",
        "цензуры": "цензура",
        "цензурой": "цензура",
        "свободы слова": "свобода слова",
        "свободу слова": "свобода слова",
        "информацию": "информация",
        "изменилось": "изменения",
        "изменения": "изменения",
        "новеллы": "изменения",
        "новое": "изменения",
    }

    for src, dst in replacements.items():
        q = q.replace(src, dst)

    return q


def detect_section_hint(query: str):
    q = normalize_query(query)

    if "президент" in q:
        return "Президент"
    if "правительство" in q or "премьер-министр" in q or "премьер министр" in q:
        return "Правительство"
    if "суд" in q or "правосуд" in q or "судья" in q:
        return "Правосудие"
    if (
        "право" in q
        or "свобод" in q
        or "цензура" in q
        or "свобода слова" in q
        or "информация" in q
    ):
        return "Основные права, свободы и обязанности"
    return None


def classify_query(query: str) -> str:
    q = normalize_query(query)

    if re.search(r"\bстат\w*\s*\d+\b", q) or re.search(r"\bст\.\s*\d+\b", q):
        return "exact"
    if "1995" in q and "2026" in q:
        return "comparison"
    if any(x in q for x in ["сравни", "сравнение"]):
        return "comparison"
    if any(x in q for x in ["что изменилось", "изменения", "новая конституция", "новеллы"]):
        return "explanation"
    if any(x in q for x in ["простыми словами", "объясни проще", "объясни простыми словами", "faq"]):
        return "explanation"
    return "ordinary"


def extract_article_number(query: str):
    q = normalize_query(query)
    m = re.search(r"\b(?:стат\w*|ст\.)\s*(\d+)\b", q)
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


def retrieve_historical_range(doc_key: str, article_from: int, article_to: int, limit: int = 5):
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
      and (c.meta->>'article_number') ~ '^[0-9]+$'
      and ((c.meta->>'article_number')::int between %s and %s)
    order by c.chunk_index
    limit %s
    """
    return fetch_all(sql, (doc_key, article_from, article_to, limit))


def retrieve_historical_priority(query: str, doc_key: str, limit: int = 5):
    section_hint = detect_section_hint(query)

    if section_hint == "Президент":
        return retrieve_historical_range(doc_key, 40, 48, limit)

    if section_hint == "Правительство":
        return retrieve_historical_range(doc_key, 64, 70, limit)

    return []


def retrieve_section_priority(query: str, doc_key: str, limit: int = 5):
    section_hint = detect_section_hint(query)
    if not section_hint:
        return []

    sql = """
    select
      d.doc_key,
      d.status,
      c.chunk_index,
      c.heading,
      c.meta,
      c.body,
      case
        when coalesce(c.meta->>'section_title', '') ilike %s then 3
        when coalesce(c.heading, '') ilike %s then 2
        when c.body ilike %s then 1
        else 0
      end as priority_score
    from document_chunks c
    join documents d on d.id = c.document_id
    where d.doc_key = %s
      and (
        coalesce(c.meta->>'section_title', '') ilike %s
        or coalesce(c.heading, '') ilike %s
        or c.body ilike %s
      )
    order by priority_score desc, c.chunk_index
    limit %s
    """
    like = f"%{section_hint}%"
    return fetch_all(sql, (like, like, like, doc_key, like, like, like, limit))


def retrieve_keyword_priority(query: str, doc_key: str, limit: int = 5):
    q = normalize_query(query)

    keyword_groups = []

    if "цензура" in q or "свобода слова" in q or "информация" in q:
        keyword_groups.append(["цензура", "свобода слова", "информация"])

    if "изменения" in q and "конституция" in q:
        keyword_groups.append(["изменения", "референдум", "вступает в силу"])

    if not keyword_groups:
        return []

    conditions = []
    params = [doc_key]
    score_parts = []

    for group in keyword_groups:
        for kw in group:
            like = f"%{kw}%"
            conditions.append("c.body ilike %s")
            params.append(like)
            score_parts.append(f"case when c.body ilike %s then 1 else 0 end")
            params.append(like)

    sql = f"""
    select
      d.doc_key,
      d.status,
      c.chunk_index,
      c.heading,
      c.meta,
      c.body,
      ({' + '.join(score_parts)}) as keyword_score
    from document_chunks c
    join documents d on d.id = c.document_id
    where d.doc_key = %s
      and ({' or '.join(conditions)})
    order by keyword_score desc, c.chunk_index
    limit %s
    """
    params.append(limit)
    return fetch_all(sql, tuple(params))


def retrieve_fts(query: str, doc_key: str, limit: int = 5):
    q = normalize_query(query)
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
    return fetch_all(sql, (q, doc_key, q, limit))


def retrieve_trgm(query: str, doc_key: str, limit: int = 5):
    q = normalize_query(query)
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
    return fetch_all(sql, (q, q, doc_key, limit))


def retrieve_ordinary(query: str):
    q = normalize_query(query)

    if any(x in q for x in ["изменения", "новая конституция"]):
        return retrieve_explanation(query)

    section_rows = retrieve_section_priority(query, DOCS["norm_ru"], limit=5)
    if section_rows:
        return section_rows

    keyword_rows = retrieve_keyword_priority(query, DOCS["norm_ru"], limit=5)
    if keyword_rows:
        return keyword_rows

    rows = retrieve_fts(query, DOCS["norm_ru"], limit=5)
    if rows:
        return rows

    return retrieve_trgm(query, DOCS["norm_ru"], limit=5)


def retrieve_explanation(query: str):
    norm_rows = retrieve_keyword_priority(query, DOCS["norm_ru"], limit=3)
    if not norm_rows:
        norm_rows = retrieve_section_priority(query, DOCS["norm_ru"], limit=3)
    if not norm_rows:
        norm_rows = retrieve_fts(query, DOCS["norm_ru"], limit=3)
    if not norm_rows:
        norm_rows = retrieve_trgm(query, DOCS["norm_ru"], limit=3)

    commentary_rows = retrieve_keyword_priority(query, DOCS["commentary_ru"], limit=2)
    if not commentary_rows:
        commentary_rows = retrieve_section_priority(query, DOCS["commentary_ru"], limit=2)
    if not commentary_rows:
        commentary_rows = retrieve_fts(query, DOCS["commentary_ru"], limit=2)
    if not commentary_rows:
        commentary_rows = retrieve_trgm(query, DOCS["commentary_ru"], limit=2)

    if norm_rows:
        return norm_rows + commentary_rows

    faq_rows = retrieve_fts(query, DOCS["faq_ru"], limit=2)
    if not faq_rows:
        faq_rows = retrieve_trgm(query, DOCS["faq_ru"], limit=2)

    return commentary_rows + faq_rows


def retrieve_comparison(query: str):
    current_rows = retrieve_section_priority(query, DOCS["norm_ru"], limit=5)
    if not current_rows:
        current_rows = retrieve_keyword_priority(query, DOCS["norm_ru"], limit=5)
    if not current_rows:
        current_rows = retrieve_fts(query, DOCS["norm_ru"], limit=3)
    if not current_rows:
        current_rows = retrieve_trgm(query, DOCS["norm_ru"], limit=3)

    historical_rows = retrieve_historical_priority(query, DOCS["deprecated_ru"], limit=3)
    if not historical_rows:
        historical_rows = retrieve_keyword_priority(query, DOCS["deprecated_ru"], limit=3)
    if not historical_rows:
        historical_rows = retrieve_fts(query, DOCS["deprecated_ru"], limit=3)
    if not historical_rows:
        historical_rows = retrieve_trgm(query, DOCS["deprecated_ru"], limit=3)

    return {
        "2026": current_rows[:3],
        "1995": historical_rows,
    }


def run_retrieval(query: str):
    mode = classify_query(query)

    if mode == "exact":
        article_number = extract_article_number(query)
        if article_number is None:
            return {"mode": mode, "results": []}
        return {"mode": mode, "results": retrieve_exact_article(article_number)}

    if mode == "comparison":
        return {"mode": mode, "results": retrieve_comparison(query)}

    if mode == "explanation":
        return {"mode": mode, "results": retrieve_explanation(query)}

    return {"mode": mode, "results": retrieve_ordinary(query)}
