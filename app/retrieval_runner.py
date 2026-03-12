import re
from app.db import fetch_all


DOCS = {
    "norm_ru": "krk_2026_norm_ru",
    "commentary_ru": "krk_2026_commentary_ru",
    "faq_ru": "krk_2026_faq_ru",
    "deprecated_ru": "krk_1995_deprecated_ru",
}

SAFE_FAILURE_PATTERNS = [
    "нейросет",
    "нейросети",
    "ai",
    "искусственный интеллект",
    "цифров",
    "цифровой суверенитет",
    "суверенитет нейросетей",
    "блокчейн",
    "blockchain",
    "token",
    "tokenization",
    "tokenized",
    "web3",
    "метавселен",
]

POLITICAL_RIGHTS_OVERVIEW_ARTICLES = [23, 26, 34, 35]

TOPICAL_ARTICLE_MAP_2026 = {
    "свобода слова": [23],
    "цензура": [23],
    "информация": [23],
    "мирные собрания": [34],
    "собрания": [34],
    "свобода объединений": [26],
    "объединений": [26],
    "участвовать в управлении": [35],
    "участие в управлении": [35],
    "избирать": [35],
    "быть избранным": [35],
    "референдум": [35],
    "лишение гражданства": [13],
    "гражданства": [13],
}

TOPICAL_ARTICLE_MAP_1995 = {
    "президент": list(range(40, 49)),
    "правительство": list(range(64, 71)),
}

MIXED_TOPIC_SPLITTERS = [
    " и ",
    " а также ",
    " при этом ",
]

BROAD_MARKERS = [
    "какие",
    "перечисли",
    "покажи все",
    "все статьи",
    "что предусмотрено",
    "что сказано о",
    "полностью перечисли",
]

EXPLANATION_MARKERS = [
    "простыми словами",
    "объясни проще",
    "объясни простыми словами",
    "faq",
]

COMPARISON_MARKERS = [
    "сравни",
    "сравнение",
    "было и стало",
    "чем отличается",
]

POLICY_GUARD_MARKERS = [
    "если в norm ничего нет",
    "можешь взять ответ из методички",
    "из методички",
]

POINT_PATTERNS = [
    r"\bпункт\w*\s*(\d+)\s*стат\w*\s*(\d+)\b",
    r"\bп\.\s*(\d+)\s*ст\.\s*(\d+)\b",
]

ARTICLE_PATTERNS = [
    r"\bстат\w*\s*(\d+)\b",
    r"\bст\.\s*(\d+)\b",
]


def normalize_query(query: str) -> str:
    q = query.lower().strip()
    q = q.replace("ё", "е")

    replacements = {
        "президента": "президент",
        "президенту": "президент",
        "президентом": "президент",
        "президенты": "президент",

        "полномочий": "полномочия",
        "полномочиями": "полномочия",

        "правительства": "правительство",
        "правительством": "правительство",
        "правительстве": "правительство",
        "правительству": "правительство",

        "судами": "суд",
        "суда": "суд",
        "судах": "суд",
        "судья": "суд",
        "судьи": "суд",

        "цензуры": "цензура",
        "цензурой": "цензура",

        "свободы слова": "свобода слова",
        "свободу слова": "свобода слова",
        "свободе слова": "свобода слова",
        "о свободе слова": "свобода слова",
        "к свободе слова": "свобода слова",

        "мирных собраний": "мирные собрания",
        "мирными собраниями": "мирные собрания",
        "мирным собраниям": "мирные собрания",
        "мирные собрания": "мирные собрания",
        "праве на мирные собрания": "мирные собрания",
        "о праве на мирные собрания": "мирные собрания",

        "собраний": "собрания",

        "информацию": "информация",
        "информации": "информация",

        "изменилось": "изменения",
        "изменения": "изменения",
        "новеллы": "изменения",
        "новое": "изменения",

        "действующая конституция 1995 года": "1995 конституция",
        "конституция 1995 года": "1995 конституция",
    }

    for src, dst in replacements.items():
        q = q.replace(src, dst)

    q = re.sub(r"[«»\"“”„(),.:;!?]", " ", q)
    q = re.sub(r"\s+", " ", q).strip()
    return q


def unique_rows(rows):
    seen = set()
    result = []
    for row in rows:
        key = (
            row.get("doc_key"),
            row.get("chunk_index"),
            row.get("heading"),
        )
        if key not in seen:
            seen.add(key)
            result.append(row)
    return result


def extract_article_number(query: str):
    q = normalize_query(query)
    for pattern in ARTICLE_PATTERNS:
        m = re.search(pattern, q)
        if m:
            return int(m.group(1))
    return None


def extract_point_and_article(query: str):
    q = normalize_query(query)
    for pattern in POINT_PATTERNS:
        m = re.search(pattern, q)
        if m:
            return int(m.group(1)), int(m.group(2))
    return None, None


def is_probably_weak_query(query: str) -> bool:
    q = normalize_query(query)
    return any(x in q for x in SAFE_FAILURE_PATTERNS)


def is_broad_query(query: str) -> bool:
    q = normalize_query(query)
    return any(x in q for x in BROAD_MARKERS) and any(
        x in q for x in [
            "прав",
            "свобод",
            "полномоч",
            "стать",
            "положени",
            "президент",
            "собрани",
            "свобода слова",
        ]
    )


def is_mixed_topic_query(query: str) -> bool:
    q = normalize_query(query)
    topic_hits = 0

    if any(x in q for x in ["прав", "свобод", "политические права"]):
        topic_hits += 1
    if "курултай" in q:
        topic_hits += 1
    if "президент" in q:
        topic_hits += 1
    if "правительство" in q:
        topic_hits += 1
    if "суд" in q or "правосуд" in q:
        topic_hits += 1

    return topic_hits >= 2 and any(s in q for s in MIXED_TOPIC_SPLITTERS)


def canonical_topics(query: str) -> set[str]:
    q = normalize_query(query)
    topics = set()

    if "президент" in q:
        topics.add("президент")
    if "правительство" in q or "премьер-министр" in q or "премьер министр" in q:
        topics.add("правительство")
    if "суд" in q or "правосуд" in q:
        topics.add("правосудие")
    if "курултай" in q:
        topics.add("курултай")

    if (
        "свобода слова" in q
        or "цензура" in q
        or "информация" in q
    ):
        topics.add("свобода_слова")

    if "мирные собрания" in q or "собрания" in q:
        topics.add("мирные_собрания")

    if "политические права" in q:
        topics.add("политические_права")

    if (
        "право" in q
        or "права" in q
        or "свобод" in q
        or "политические права" in q
    ):
        topics.add("права")

    if "изменения" in q or "новая конституция" in q or "новеллы" in q:
        topics.add("изменения")

    return topics


def classify_query(query: str) -> str:
    q = normalize_query(query)

    point_number, article_number = extract_point_and_article(q)
    if point_number is not None and article_number is not None:
        return "exact"

    if extract_article_number(q) is not None:
        return "exact"

    if any(x in q for x in POLICY_GUARD_MARKERS):
        return "policy"

    if "1995" in q and "2026" in q:
        return "comparison"

    if any(x in q for x in COMPARISON_MARKERS):
        return "comparison"

    if "1995" in q and any(x in q for x in ["конституция", "редакция", "действующая"]):
        return "historical"

    if any(x in q for x in EXPLANATION_MARKERS):
        return "explanation"

    if any(x in q for x in ["что изменилось", "изменения", "новая конституция", "новеллы"]):
        return "explanation"

    if is_mixed_topic_query(q):
        return "mixed"

    if is_broad_query(q):
        return "broad"

    return "ordinary"


def detect_section_hint(query: str):
    topics = canonical_topics(query)

    if "президент" in topics:
        return "Президент"
    if "правительство" in topics:
        return "Правительство"
    if "правосудие" in topics:
        return "Правосудие"
    if (
        "права" in topics
        or "политические_права" in topics
        or "свобода_слова" in topics
        or "мирные_собрания" in topics
    ):
        return "Основные права, свободы и обязанности"

    return None


def retrieve_exact_article(article_number: int, doc_key: str = DOCS["norm_ru"], limit: int = 5):
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


def retrieve_exact_point(article_number: int, point_number: int, doc_key: str = DOCS["norm_ru"], limit: int = 5):
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
    rows = fetch_all(sql, (doc_key, str(article_number), f"Статья {article_number}%", limit))
    return rows


def retrieve_article_range(doc_key: str, article_from: int, article_to: int, limit: int = 10):
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
    order by ((c.meta->>'article_number')::int), c.chunk_index
    limit %s
    """
    return fetch_all(sql, (doc_key, article_from, article_to, limit))


def retrieve_section_priority(query: str, doc_key: str, limit: int = 5):
    section_hint = detect_section_hint(query)
    if not section_hint:
        return []

    like = f"%{section_hint}%"
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
    return fetch_all(sql, (like, like, like, doc_key, like, like, like, limit))


def retrieve_keyword_priority(query: str, doc_key: str, limit: int = 5):
    q = normalize_query(query)
    keyword_groups = []

    if "цензура" in q or "свобода слова" in q or "информация" in q:
        keyword_groups.append(["цензура", "свобода слова", "информация"])

    if "мирные собрания" in q or "собрания" in q:
        keyword_groups.append(["мирные собрания", "собрания"])

    if "политические права" in q:
        keyword_groups.append([
            "свобода слова",
            "информация",
            "цензура",
            "свобода объединений",
            "мирные собрания",
            "участвовать в управлении",
            "избирать",
            "быть избранным",
            "референдум",
        ])

    if "изменения" in q and "конституция" in q:
        keyword_groups.append(["изменения", "референдум", "вступает в силу", "переходные положения"])

    if "лишение гражданства" in q or "гражданства" in q:
        keyword_groups.append(["лишен гражданства", "лишение гражданства", "гражданства"])

    if not keyword_groups:
        return []

    conditions = []
    score_parts = []
    condition_params = []
    score_params = []

    for group in keyword_groups:
        for kw in group:
            like = f"%{kw}%"
            conditions.append("(c.body ilike %s or coalesce(c.heading, '') ilike %s)")
            condition_params.extend([like, like])

    for group in keyword_groups:
        for kw in group:
            like = f"%{kw}%"
            score_parts.append(
                "(case when c.body ilike %s then 1 else 0 end + case when coalesce(c.heading, '') ilike %s then 2 else 0 end)"
            )
            score_params.extend([like, like])

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

    params = tuple(score_params + [doc_key] + condition_params + [limit])
    return fetch_all(sql, params)


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


def retrieve_articles_by_list(doc_key: str, article_numbers: list[int], per_article_limit: int = 2):
    rows = []
    for article_number in article_numbers:
        rows.extend(retrieve_exact_article(article_number, doc_key=doc_key, limit=per_article_limit))
    return unique_rows(rows)


def retrieve_topic_shortcut_2026(query: str):
    q = normalize_query(query)

    matched_articles = []
    for topic, article_numbers in TOPICAL_ARTICLE_MAP_2026.items():
        if topic in q:
            matched_articles.extend(article_numbers)

    if not matched_articles:
        return []

    matched_articles = sorted(set(matched_articles))
    return retrieve_articles_by_list(DOCS["norm_ru"], matched_articles, per_article_limit=2)


def retrieve_topic_shortcut_1995(query: str):
    q = normalize_query(query)

    for topic, article_numbers in TOPICAL_ARTICLE_MAP_1995.items():
        if topic in q:
            return retrieve_articles_by_list(DOCS["deprecated_ru"], article_numbers, per_article_limit=1)

    return []


def retrieve_change_explanation(query: str):
    norm_rows = retrieve_keyword_priority(query, DOCS["norm_ru"], limit=5)
    if not norm_rows:
        norm_rows = retrieve_article_range(DOCS["norm_ru"], 93, 94, limit=4)

    commentary_rows = retrieve_keyword_priority(query, DOCS["commentary_ru"], limit=5)
    if not commentary_rows:
        commentary_rows = retrieve_fts(query, DOCS["commentary_ru"], limit=5)

    if not commentary_rows:
        commentary_rows = retrieve_trgm(query, DOCS["commentary_ru"], limit=5)

    return unique_rows(norm_rows[:3] + commentary_rows[:2])


def retrieve_political_rights_overview():
    return retrieve_articles_by_list(DOCS["norm_ru"], POLITICAL_RIGHTS_OVERVIEW_ARTICLES, per_article_limit=1)


def retrieve_broad(query: str):
    q = normalize_query(query)
    topics = canonical_topics(q)

    topic_rows = retrieve_topic_shortcut_2026(q)
    if topic_rows:
        return topic_rows

    if "политические_права" in topics:
        rows = retrieve_political_rights_overview()
        if rows:
            return rows

    if "права" in topics and any(x in q for x in ["свобода слова", "собрания", "участие в управлении"]):
        article_numbers = [23, 34, 35]
        return retrieve_articles_by_list(DOCS["norm_ru"], article_numbers, per_article_limit=1)

    if "президент" in topics:
        return retrieve_article_range(DOCS["norm_ru"], 42, 49, limit=8)

    if "правительство" in topics:
        return retrieve_article_range(DOCS["norm_ru"], 63, 69, limit=8)

    keyword_rows = retrieve_keyword_priority(q, DOCS["norm_ru"], limit=8)
    if keyword_rows:
        return keyword_rows

    section_rows = retrieve_section_priority(q, DOCS["norm_ru"], limit=8)
    if section_rows:
        return section_rows

    rows = retrieve_fts(q, DOCS["norm_ru"], limit=8)
    if rows:
        return rows

    return []


def retrieve_ordinary(query: str):
    q = normalize_query(query)
    topics = canonical_topics(q)

    if is_probably_weak_query(q):
        return []

    topic_rows = retrieve_topic_shortcut_2026(q)
    if topic_rows:
        return topic_rows

    if "политические_права" in topics:
        rows = retrieve_political_rights_overview()
        if rows:
            return rows

    if "изменения" in topics:
        return retrieve_change_explanation(q)

    keyword_rows = retrieve_keyword_priority(q, DOCS["norm_ru"], limit=5)
    if keyword_rows:
        return keyword_rows

    section_rows = retrieve_section_priority(q, DOCS["norm_ru"], limit=5)
    if section_rows:
        return section_rows

    rows = retrieve_fts(q, DOCS["norm_ru"], limit=5)
    if rows:
        return rows

    return []


def retrieve_explanation(query: str):
    q = normalize_query(query)
    topics = canonical_topics(q)

    if "изменения" in topics:
        return retrieve_change_explanation(q)

    norm_rows = retrieve_topic_shortcut_2026(q)
    if not norm_rows:
        norm_rows = retrieve_keyword_priority(q, DOCS["norm_ru"], limit=3)
    if not norm_rows:
        norm_rows = retrieve_section_priority(q, DOCS["norm_ru"], limit=3)
    if not norm_rows:
        norm_rows = retrieve_fts(q, DOCS["norm_ru"], limit=3)

    commentary_rows = retrieve_keyword_priority(q, DOCS["commentary_ru"], limit=2)
    if not commentary_rows:
        commentary_rows = retrieve_section_priority(q, DOCS["commentary_ru"], limit=2)
    if not commentary_rows:
        commentary_rows = retrieve_fts(q, DOCS["commentary_ru"], limit=2)

    if norm_rows:
        return unique_rows(norm_rows + commentary_rows)

    faq_rows = retrieve_fts(q, DOCS["faq_ru"], limit=2)
    if faq_rows:
        return unique_rows(commentary_rows + faq_rows)

    return commentary_rows


def retrieve_historical(query: str):
    q = normalize_query(query)

    topic_rows = retrieve_topic_shortcut_1995(q)
    if topic_rows:
        return topic_rows

    keyword_rows = retrieve_keyword_priority(q, DOCS["deprecated_ru"], limit=5)
    if keyword_rows:
        return keyword_rows

    section_rows = retrieve_section_priority(q, DOCS["deprecated_ru"], limit=5)
    if section_rows:
        return section_rows

    rows = retrieve_fts(q, DOCS["deprecated_ru"], limit=5)
    if rows:
        return rows

    return []


def retrieve_comparison(query: str):
    q = normalize_query(query)
    topics = canonical_topics(q)

    if "президент" in topics:
        return {
            "2026": retrieve_article_range(DOCS["norm_ru"], 42, 49, limit=4),
            "1995": retrieve_article_range(DOCS["deprecated_ru"], 40, 48, limit=4),
        }

    if "правительство" in topics:
        return {
            "2026": retrieve_article_range(DOCS["norm_ru"], 63, 69, limit=4),
            "1995": retrieve_article_range(DOCS["deprecated_ru"], 64, 70, limit=4),
        }

    if "свобода_слова" in topics:
        return {
            "2026": retrieve_articles_by_list(DOCS["norm_ru"], [23], per_article_limit=2),
            "1995": retrieve_keyword_priority("свобода слова цензура информация", DOCS["deprecated_ru"], limit=3),
        }

    current_rows = retrieve_topic_shortcut_2026(q)
    if not current_rows:
        current_rows = retrieve_keyword_priority(q, DOCS["norm_ru"], limit=4)
    if not current_rows:
        current_rows = retrieve_section_priority(q, DOCS["norm_ru"], limit=4)
    if not current_rows:
        current_rows = retrieve_fts(q, DOCS["norm_ru"], limit=4)

    historical_rows = retrieve_topic_shortcut_1995(q)
    if not historical_rows:
        historical_rows = retrieve_keyword_priority(q, DOCS["deprecated_ru"], limit=4)
    if not historical_rows:
        historical_rows = retrieve_section_priority(q, DOCS["deprecated_ru"], limit=4)
    if not historical_rows:
        historical_rows = retrieve_fts(q, DOCS["deprecated_ru"], limit=4)

    return {
        "2026": unique_rows(current_rows),
        "1995": unique_rows(historical_rows),
    }


def retrieve_policy_guard(query: str):
    return []


def split_mixed_query(query: str):
    q = normalize_query(query)
    for splitter in MIXED_TOPIC_SPLITTERS:
        if splitter in q:
            parts = [part.strip() for part in q.split(splitter) if part.strip()]
            if len(parts) >= 2:
                return parts[:3]
    return [q]


def retrieve_mixed(query: str):
    parts = split_mixed_query(query)
    bundled = []

    for part in parts:
        part_rows = retrieve_ordinary(part)
        bundled.append({
            "subquery": part,
            "results": unique_rows(part_rows),
        })

    return bundled


def run_retrieval(query: str):
    mode = classify_query(query)

    if mode == "exact":
        point_number, article_number = extract_point_and_article(query)
        if point_number is not None and article_number is not None:
            return {
                "mode": mode,
                "results": retrieve_exact_point(article_number, point_number),
                "point_number": point_number,
                "article_number": article_number,
            }

        article_number = extract_article_number(query)
        if article_number is None:
            return {"mode": mode, "results": []}

        return {
            "mode": mode,
            "results": retrieve_exact_article(article_number),
            "article_number": article_number,
        }

    if mode == "comparison":
        return {"mode": mode, "results": retrieve_comparison(query)}

    if mode == "historical":
        return {"mode": mode, "results": retrieve_historical(query)}

    if mode == "explanation":
        return {"mode": mode, "results": retrieve_explanation(query)}

    if mode == "policy":
        return {"mode": mode, "results": retrieve_policy_guard(query)}

    if mode == "mixed":
        return {"mode": mode, "results": retrieve_mixed(query)}

    if mode == "broad":
        return {"mode": mode, "results": retrieve_broad(query)}

    return {"mode": mode, "results": retrieve_ordinary(query)}
