import re
from app.db import fetch_all


# ── Dataset registry (all 15 datasets) ──────────────────────────────
DOCS = {
    # Norm layer
    "norm_ru": "krk_2026_norm_ru",
    "norm_kz": "krk_2026_norm_kz",
    # Commentary layer (primary)
    "commentary_ru": "krk_2026_commentary_ru",
    "commentary_kz": "krk_2026_commentary_kz",
    # Civic-education sub-layer (secondary commentary)
    "ce_theses_ru": "krk_2026_ce_theses_ru",
    "ce_audiences_ru": "krk_2026_ce_audiences_ru",
    # FAQ layer
    "faq_ru": "krk_2026_faq_ru",
    "faq_kz": "krk_2026_faq_kz",
    "faq_extra_ru": "krk_2026_faq_extra_ru",
    "faq_extra_kz": "krk_2026_faq_extra_kz",
    "faq_extra_en": "krk_2026_faq_extra_en",
    # Comparison-only
    "ce_comparison_ru": "krk_2026_ce_comparison_ru",
    # Historical / deprecated
    "deprecated_ru": "krk_1995_deprecated_ru",
    "deprecated_kz": "krk_1995_deprecated_kz",
    # RESTRICTED — not used in ordinary retrieval
    # "ce_lines_ru": "krk_2026_ce_lines_ru",
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


# ── Language detection ──────────────────────────────────────────────
_CYRILLIC = re.compile(r"[а-яёА-ЯЁ]")
_KZ_SPECIFIC = re.compile(
    r"[ӘәҒғҚқҢңӨөҰұҮүҺһІі]"
    r"|(?:неге|қандай|қалай|бойынша|туралы|конституция[сн]|не\sдеген|мен\s)"
)


def detect_language(query: str) -> str:
    """Detect query language: 'kz', 'en', or 'ru' (default)."""
    if _KZ_SPECIFIC.search(query):
        return "kz"
    if not _CYRILLIC.search(query):
        # No Cyrillic at all → treat as English
        return "en"
    return "ru"


def lang_docs(lang: str) -> dict:
    """Return doc-key mapping appropriate for the detected language."""
    if lang == "kz":
        return {
            "norm": DOCS["norm_kz"],
            "commentary": DOCS["commentary_kz"],
            "faq": DOCS["faq_kz"],
            "faq_extra": DOCS["faq_extra_kz"],
            "deprecated": DOCS["deprecated_kz"],
            # ce_theses / ce_audiences / ce_comparison — only in RU
            "ce_theses": DOCS["ce_theses_ru"],
            "ce_audiences": DOCS["ce_audiences_ru"],
            "ce_comparison": DOCS["ce_comparison_ru"],
        }
    if lang == "en":
        return {
            # English has only faq_extra_en; fall back to RU for norm/commentary
            "norm": DOCS["norm_ru"],
            "commentary": DOCS["commentary_ru"],
            "faq": DOCS["faq_extra_en"],       # primary FAQ for EN
            "faq_extra": DOCS["faq_extra_en"],  # same
            "deprecated": DOCS["deprecated_ru"],
            "ce_theses": DOCS["ce_theses_ru"],
            "ce_audiences": DOCS["ce_audiences_ru"],
            "ce_comparison": DOCS["ce_comparison_ru"],
        }
    # default: ru
    return {
        "norm": DOCS["norm_ru"],
        "commentary": DOCS["commentary_ru"],
        "faq": DOCS["faq_ru"],
        "faq_extra": DOCS["faq_extra_ru"],
        "deprecated": DOCS["deprecated_ru"],
        "ce_theses": DOCS["ce_theses_ru"],
        "ce_audiences": DOCS["ce_audiences_ru"],
        "ce_comparison": DOCS["ce_comparison_ru"],
    }


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

    q = re.sub(r"[«»\\\"\"\"„(),.:;!?]", " ", q)
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


def retrieve_exact_article(article_number: int, doc_key: str = None, limit: int = 5):
    if doc_key is None:
        doc_key = DOCS["norm_ru"]
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


def retrieve_exact_point(article_number: int, point_number: int, doc_key: str = None, limit: int = 5):
    if doc_key is None:
        doc_key = DOCS["norm_ru"]
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

    # NOTE: score_parts and conditions are built from hardcoded keyword lists only —
    # never from user input. Do not add user-supplied strings to these lists.
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


def retrieve_topic_shortcut_2026(query: str, norm_key: str = None):
    if norm_key is None:
        norm_key = DOCS["norm_ru"]
    q = normalize_query(query)

    matched_articles = []
    for topic, article_numbers in TOPICAL_ARTICLE_MAP_2026.items():
        if topic in q:
            matched_articles.extend(article_numbers)

    if not matched_articles:
        return []

    matched_articles = sorted(set(matched_articles))
    return retrieve_articles_by_list(norm_key, matched_articles, per_article_limit=2)


def retrieve_topic_shortcut_1995(query: str, deprecated_key: str = None):
    if deprecated_key is None:
        deprecated_key = DOCS["deprecated_ru"]
    q = normalize_query(query)

    for topic, article_numbers in TOPICAL_ARTICLE_MAP_1995.items():
        if topic in q:
            return retrieve_articles_by_list(deprecated_key, article_numbers, per_article_limit=1)

    return []


def retrieve_change_explanation(query: str, ld: dict = None):
    if ld is None:
        ld = lang_docs("ru")
    norm_rows = retrieve_keyword_priority(query, ld["norm"], limit=5)
    if not norm_rows:
        norm_rows = retrieve_article_range(ld["norm"], 93, 94, limit=4)

    commentary_rows = retrieve_keyword_priority(query, ld["commentary"], limit=5)
    if not commentary_rows:
        commentary_rows = retrieve_fts(query, ld["commentary"], limit=5)

    if not commentary_rows:
        commentary_rows = retrieve_trgm(query, ld["commentary"], limit=5)

    return unique_rows(norm_rows[:3] + commentary_rows[:2])


def retrieve_political_rights_overview(norm_key: str = None):
    if norm_key is None:
        norm_key = DOCS["norm_ru"]
    return retrieve_articles_by_list(norm_key, POLITICAL_RIGHTS_OVERVIEW_ARTICLES, per_article_limit=1)


def _enrich_with_faq_extra(rows: list, query: str, ld: dict, max_extra: int = 2) -> list:
    """Add faq_extra results if they bring new content (not already in rows)."""
    faq_extra_key = ld.get("faq_extra")
    if not faq_extra_key:
        return rows
    # Skip if faq_extra == faq (English case)
    if faq_extra_key == ld.get("faq"):
        return rows
    extra = retrieve_fts(query, faq_extra_key, limit=max_extra)
    if not extra:
        extra = retrieve_trgm(query, faq_extra_key, limit=max_extra)
    return unique_rows(rows + extra[:max_extra])


def retrieve_broad(query: str, ld: dict = None):
    if ld is None:
        ld = lang_docs("ru")
    q = normalize_query(query)
    topics = canonical_topics(q)

    topic_rows = retrieve_topic_shortcut_2026(q, norm_key=ld["norm"])
    if topic_rows:
        return _enrich_with_faq_extra(topic_rows, q, ld)

    if "политические_права" in topics:
        rows = retrieve_political_rights_overview(norm_key=ld["norm"])
        if rows:
            return _enrich_with_faq_extra(rows, q, ld)

    if "права" in topics and any(x in q for x in ["свобода слова", "собрания", "участие в управлении"]):
        article_numbers = [23, 34, 35]
        rows = retrieve_articles_by_list(ld["norm"], article_numbers, per_article_limit=1)
        return _enrich_with_faq_extra(rows, q, ld)

    if "президент" in topics:
        return retrieve_article_range(ld["norm"], 42, 49, limit=8)

    if "правительство" in topics:
        return retrieve_article_range(ld["norm"], 63, 69, limit=8)

    keyword_rows = retrieve_keyword_priority(q, ld["norm"], limit=8)
    if keyword_rows:
        return _enrich_with_faq_extra(keyword_rows, q, ld)

    section_rows = retrieve_section_priority(q, ld["norm"], limit=8)
    if section_rows:
        return _enrich_with_faq_extra(section_rows, q, ld)

    rows = retrieve_fts(q, ld["norm"], limit=8)
    if rows:
        return _enrich_with_faq_extra(rows, q, ld)

    # Fallback: try faq_extra directly for broad queries
    faq_rows = retrieve_fts(q, ld.get("faq_extra", ld["faq"]), limit=5)
    if faq_rows:
        return faq_rows

    return []


def retrieve_ordinary(query: str, ld: dict = None):
    if ld is None:
        ld = lang_docs("ru")
    q = normalize_query(query)
    topics = canonical_topics(q)

    if is_probably_weak_query(q):
        return []

    topic_rows = retrieve_topic_shortcut_2026(q, norm_key=ld["norm"])
    if topic_rows:
        return _enrich_with_faq_extra(topic_rows, q, ld)

    if "политические_права" in topics:
        rows = retrieve_political_rights_overview(norm_key=ld["norm"])
        if rows:
            return _enrich_with_faq_extra(rows, q, ld)

    if "изменения" in topics:
        return retrieve_change_explanation(q, ld=ld)

    keyword_rows = retrieve_keyword_priority(q, ld["norm"], limit=5)
    if keyword_rows:
        return _enrich_with_faq_extra(keyword_rows, q, ld)

    section_rows = retrieve_section_priority(q, ld["norm"], limit=5)
    if section_rows:
        return _enrich_with_faq_extra(section_rows, q, ld)

    rows = retrieve_fts(q, ld["norm"], limit=5)
    if rows:
        return _enrich_with_faq_extra(rows, q, ld)

    # Fallback: try faq + faq_extra before giving up
    faq_rows = retrieve_fts(q, ld["faq"], limit=3)
    if not faq_rows:
        faq_extra_key = ld.get("faq_extra", ld["faq"])
        faq_rows = retrieve_fts(q, faq_extra_key, limit=3)
    if faq_rows:
        return faq_rows

    return []


def retrieve_explanation(query: str, ld: dict = None):
    if ld is None:
        ld = lang_docs("ru")
    q = normalize_query(query)
    topics = canonical_topics(q)

    if "изменения" in topics:
        return retrieve_change_explanation(q, ld=ld)

    norm_rows = retrieve_topic_shortcut_2026(q, norm_key=ld["norm"])
    if not norm_rows:
        norm_rows = retrieve_keyword_priority(q, ld["norm"], limit=3)
    if not norm_rows:
        norm_rows = retrieve_section_priority(q, ld["norm"], limit=3)
    if not norm_rows:
        norm_rows = retrieve_fts(q, ld["norm"], limit=3)

    commentary_rows = retrieve_keyword_priority(q, ld["commentary"], limit=2)
    if not commentary_rows:
        commentary_rows = retrieve_section_priority(q, ld["commentary"], limit=2)
    if not commentary_rows:
        commentary_rows = retrieve_fts(q, ld["commentary"], limit=2)

    # ── NEW: add civic-education theses as supporting context ──
    ce_theses_rows = retrieve_fts(q, ld["ce_theses"], limit=1)

    if norm_rows:
        base = unique_rows(norm_rows + commentary_rows + ce_theses_rows)
        return _enrich_with_faq_extra(base, q, ld)

    # Fallback to FAQ layer
    faq_rows = retrieve_fts(q, ld["faq"], limit=2)
    if not faq_rows:
        faq_rows = retrieve_fts(q, ld.get("faq_extra", ld["faq"]), limit=2)
    if faq_rows:
        return unique_rows(commentary_rows + ce_theses_rows + faq_rows)

    return unique_rows(commentary_rows + ce_theses_rows)


def retrieve_historical(query: str, ld: dict = None):
    if ld is None:
        ld = lang_docs("ru")
    q = normalize_query(query)

    topic_rows = retrieve_topic_shortcut_1995(q, deprecated_key=ld["deprecated"])
    if topic_rows:
        return topic_rows

    keyword_rows = retrieve_keyword_priority(q, ld["deprecated"], limit=5)
    if keyword_rows:
        return keyword_rows

    section_rows = retrieve_section_priority(q, ld["deprecated"], limit=5)
    if section_rows:
        return section_rows

    rows = retrieve_fts(q, ld["deprecated"], limit=5)
    if rows:
        return rows

    return []


def retrieve_comparison(query: str, ld: dict = None):
    if ld is None:
        ld = lang_docs("ru")
    q = normalize_query(query)
    topics = canonical_topics(q)

    # ── NEW: always include ce_comparison_ru as structured comparison ──
    ce_comp_rows = retrieve_fts(q, ld["ce_comparison"], limit=3)
    if not ce_comp_rows:
        ce_comp_rows = retrieve_trgm(q, ld["ce_comparison"], limit=2)

    if "президент" in topics:
        return {
            "2026": retrieve_article_range(ld["norm"], 42, 49, limit=4),
            "1995": retrieve_article_range(ld["deprecated"], 40, 48, limit=4),
            "comparison_table": ce_comp_rows,
        }

    if "правительство" in topics:
        return {
            "2026": retrieve_article_range(ld["norm"], 63, 69, limit=4),
            "1995": retrieve_article_range(ld["deprecated"], 64, 70, limit=4),
            "comparison_table": ce_comp_rows,
        }

    if "свобода_слова" in topics:
        return {
            "2026": retrieve_articles_by_list(ld["norm"], [23], per_article_limit=2),
            "1995": retrieve_keyword_priority("свобода слова цензура информация", ld["deprecated"], limit=3),
            "comparison_table": ce_comp_rows,
        }

    current_rows = retrieve_topic_shortcut_2026(q, norm_key=ld["norm"])
    if not current_rows:
        current_rows = retrieve_keyword_priority(q, ld["norm"], limit=4)
    if not current_rows:
        current_rows = retrieve_section_priority(q, ld["norm"], limit=4)
    if not current_rows:
        current_rows = retrieve_fts(q, ld["norm"], limit=4)

    historical_rows = retrieve_topic_shortcut_1995(q, deprecated_key=ld["deprecated"])
    if not historical_rows:
        historical_rows = retrieve_keyword_priority(q, ld["deprecated"], limit=4)
    if not historical_rows:
        historical_rows = retrieve_section_priority(q, ld["deprecated"], limit=4)
    if not historical_rows:
        historical_rows = retrieve_fts(q, ld["deprecated"], limit=4)

    return {
        "2026": unique_rows(current_rows),
        "1995": unique_rows(historical_rows),
        "comparison_table": ce_comp_rows,
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


def retrieve_mixed(query: str, ld: dict = None):
    if ld is None:
        ld = lang_docs("ru")
    parts = split_mixed_query(query)
    bundled = []

    for part in parts:
        part_rows = retrieve_ordinary(part, ld=ld)
        bundled.append({
            "subquery": part,
            "results": unique_rows(part_rows),
        })

    return bundled


def run_retrieval(query: str):
    lang = detect_language(query)
    ld = lang_docs(lang)
    mode = classify_query(query)

    if mode == "exact":
        point_number, article_number = extract_point_and_article(query)
        if point_number is not None and article_number is not None:
            return {
                "mode": mode,
                "lang": lang,
                "results": retrieve_exact_point(article_number, point_number, doc_key=ld["norm"]),
                "point_number": point_number,
                "article_number": article_number,
            }

        article_number = extract_article_number(query)
        if article_number is None:
            return {"mode": mode, "lang": lang, "results": []}

        return {
            "mode": mode,
            "lang": lang,
            "results": retrieve_exact_article(article_number, doc_key=ld["norm"]),
            "article_number": article_number,
        }

    if mode == "comparison":
        return {"mode": mode, "lang": lang, "results": retrieve_comparison(query, ld=ld)}

    if mode == "historical":
        return {"mode": mode, "lang": lang, "results": retrieve_historical(query, ld=ld)}

    if mode == "explanation":
        return {"mode": mode, "lang": lang, "results": retrieve_explanation(query, ld=ld)}

    if mode == "policy":
        return {"mode": mode, "lang": lang, "results": retrieve_policy_guard(query)}

    if mode == "mixed":
        return {"mode": mode, "lang": lang, "results": retrieve_mixed(query, ld=ld)}

    if mode == "broad":
        return {"mode": mode, "lang": lang, "results": retrieve_broad(query, ld=ld)}

    return {"mode": mode, "lang": lang, "results": retrieve_ordinary(query, ld=ld)}
