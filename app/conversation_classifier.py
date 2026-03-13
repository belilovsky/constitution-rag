"""
Conversational query classifier.

Detects greetings, meta-questions, and other conversational queries
that should NOT go through retrieval pipeline.

Returns:
    - ("greeting", response_text)   — for hellos/hi/etc.
    - ("meta", None)                — for "what can you do?" type questions → let LLM answer with meta-system-prompt
    - ("followup", None)            — for "расскажи", "ещё", "продолжай" → needs history context, send to LLM
    - (None, None)                  — normal query → proceed with retrieval
"""

import re

_GREETING_PATTERNS = [
    r"^\s*(привет\w*|здравствуй\w*|приветик\w*|хай|хеллоу?|добрый\s*(день|утро|вечер)|доброе\s*утро|салам\w*|сәлем\w*|hello|hi|hey)\s*[!.?]*\s*$",
]

_META_PATTERNS = [
    # "что ты можешь / умеешь / знаешь / делаешь"
    r"(что\s+(ты\s+)?(можешь|умеешь|знаешь|делаешь))",
    # "что ты можешь предложить"
    r"(что\s+ты\s+мож\w+\s+предложить)",
    # "что за бот / что это за бот"
    r"(что\s+(это\s+)?(ты\s+)?за\s+бот)",
    # "кто ты / ты кто"
    r"(кто\s+ты|ты\s+кто)",
    # "как тебя зовут"
    r"(как\s+тебя\s+зовут)",
    # "расскажи о себе"
    r"(расскажи\s+о\s+себе)",
    # "чем помочь / чем ты можешь помочь"
    r"(чем\s+(ты\s+)?помо\w+)",
    # bare "помоги мне"
    r"(помоги\s+мне)$",
    # "что здесь можно"
    r"(что\s+здесь\s+можно)",
    # "как мне пользоваться / как пользоваться"
    r"(как\s+(мне\s+)?пользоваться)",
    # "как ты работаешь / как это работает / как работает бот"
    r"(как\s+(ты\s+)?работа\w+)",
    # "откуда ты / ты откуда"
    r"(откуда\s+ты|ты\s+откуда)",
    # "что у тебя есть / а что у тебя есть / что есть"
    r"(что\s+у\s+теб\w+\s+есть)",
    r"(что\s+у\s+теб\w+\s+етсь)",  # typo variant
    r"(что\s+есть\s+у\s+теб\w+)",
    # "а что у тебя" / "что у тебя"
    r"(что\s+у\s+теб)",
    # "что ты такое / что это такое"
    r"(что\s+ты\s+тако\w+)",
    # "для чего ты / зачем ты"
    r"(для\s+чего\s+ты|зачем\s+ты)",
    # "какие у тебя функции / возможности"
    r"(какие\s+у\s+теб\w+\s+(функци|возможност|способност))",
    # "что ты можешь рассказать"
    r"(что\s+ты\s+мож\w+\s+рассказ\w+)",
    # "о чём ты знаешь / о чем ты можешь рассказать"
    r"(о\s+ч[её]м\s+ты)",
    # "помощь" / "help" alone
    r"^\s*(помощь|help)\s*[!.?]*\s*$",
    # English
    r"(what\s+can\s+you\s+do)",
    r"(how\s+do\s+you\s+work)",
    r"(who\s+are\s+you)",
    r"(what\s+are\s+you)",
    r"(tell\s+me\s+about\s+yourself)",
]

# Short vague queries that retrieval can't handle well
_FOLLOWUP_PATTERNS = [
    r"^\s*(расскажи|ещё|еще|продолжай|дальше|подробнее|и\?|ну\??|давай)\s*[!.?]*\s*$",
    r"^\s*(а\s+что\s+ещ[её]|что\s+ещ[её])\s*[!.?]*\s*$",
]

# Short vague queries that clearly aren't about the constitution
# but don't match meta patterns either — treat as meta
_SHORT_VAGUE_MAX_WORDS = 5
_CONSTITUTION_MARKERS = [
    "конституц", "статья", "статей", "стать", "право", "свобод",
    "президент", "курултай", "правительств", "парламент", "суд",
    "гражданств", "референдум", "собрани", "объединен", "цензур",
    "норм", "закон", "полномоч", "раздел", "глав", "пункт",
    "1995", "2026", "казахстан",
]

GREETING_RESPONSES = {
    "ru": (
        "Привет! Я справочный бот по проекту Конституции Казахстана 2026 года. "
        "Могу рассказать о статьях, правах, полномочиях органов, сравнить с Конституцией 1995 года. "
        "Спрашивай — например: «Какие права гарантирует статья 23?» или «Чем отличается роль Президента от 1995 года?»"
    ),
    "kz": (
        "Сәлем! Мен Қазақстанның 2026 жылғы Конституция жобасы бойынша анықтама ботымын. "
        "Баптар, құқықтар, органдардың өкілеттіктері туралы айта аламын, 1995 жылғы Конституциямен салыстыра аламын. "
        "Сұрақ қойыңыз!"
    ),
    "en": (
        "Hi! I'm a reference bot for Kazakhstan's 2026 Constitution project. "
        "I can explain articles, rights, institutional powers, and compare with the 1995 Constitution. "
        "Try asking: \"What rights does Article 23 guarantee?\" or \"How has the President's role changed?\""
    ),
}

META_SYSTEM_ADDENDUM = """

ДОПОЛНИТЕЛЬНАЯ ИНСТРУКЦИЯ ДЛЯ ЭТОГО ЗАПРОСА:

Пользователь задал мета-вопрос (о тебе, о твоих возможностях, о том, как пользоваться ботом). 
Retrieval не выполнялся — ответь напрямую, кратко и дружелюбно.

Ты — справочный бот по проекту Конституции Казахстана 2026 года. Вот что ты умеешь:
- Разъяснять содержание статей проекта Конституции 2026 года
- Сравнивать нормы 2026 и 1995 годов (формат «было → стало»)
- Объяснять простыми словами сложные юридические формулировки
- Рассказывать о правах, свободах, полномочиях органов власти
- Отвечать на казахском, русском и английском языках

Примеры вопросов, которые можно задать:
- «Что говорит статья 23 о свободе слова?»
- «Сравни полномочия Президента в 1995 и 2026 годах»
- «Какие политические права гарантированы?»
- «Что изменилось в разделе о правительстве?»

Ответь коротко, тепло, предложи примеры вопросов. Не используй технические термины (retrieval, norm-layer и т.д.).
"""

FOLLOWUP_SYSTEM_ADDENDUM = """

ДОПОЛНИТЕЛЬНАЯ ИНСТРУКЦИЯ ДЛЯ ЭТОГО ЗАПРОСА:

Пользователь задал короткий уточняющий или продолжающий вопрос ("расскажи", "ещё", "продолжай", "подробнее"). 
Посмотри на историю диалога выше. Если история есть — продолжи предыдущую тему, дополни или углуби ответ.
Если истории нет или она пуста — вежливо попроси уточнить тему. 
Например: «О чём именно рассказать? Можешь спросить про конкретную статью, тему или право.»

Retrieval не выполнялся для этого запроса. Используй только то, что уже обсуждалось в истории.
Если в истории недостаточно данных для продолжения — скажи об этом прямо.
"""


def _has_constitution_topic(query_lower: str) -> bool:
    """Check if query mentions anything constitution-related."""
    for marker in _CONSTITUTION_MARKERS:
        if marker in query_lower:
            return True
    return False


def classify_conversational(query: str, lang: str = "ru") -> tuple[str | None, str | None]:
    """
    Classify query as conversational (greeting/meta/followup) or normal.

    Returns:
        (category, response_or_none)
        category: "greeting" | "meta" | "followup" | None
        response_or_none: pre-built response for greetings, None otherwise
    """
    q = query.strip()
    q_lower = q.lower().replace("ё", "е")

    # 1. Greeting detection
    for pattern in _GREETING_PATTERNS:
        if re.match(pattern, q_lower, re.IGNORECASE):
            return ("greeting", GREETING_RESPONSES.get(lang, GREETING_RESPONSES["ru"]))

    # 2. Followup detection (must be before meta to catch "расскажи" without topic)
    for pattern in _FOLLOWUP_PATTERNS:
        if re.match(pattern, q_lower, re.IGNORECASE):
            return ("followup", None)

    # 3. Meta-question detection (explicit patterns)
    for pattern in _META_PATTERNS:
        if re.search(pattern, q_lower, re.IGNORECASE):
            return ("meta", None)

    # 4. Short vague queries with no constitution topic → treat as meta
    #    Catches things like "а что у тебя етсь?", "ну и?", etc.
    words = q_lower.split()
    if len(words) <= _SHORT_VAGUE_MAX_WORDS and not _has_constitution_topic(q_lower):
        # Only if it doesn't look like a factual question with substance
        # Check if it's addressing the bot (mentions "ты", "тебя", "тебе", "у тебя")
        bot_markers = ["ты", "тебя", "тебе", "теб", "себя", "себе"]
        if any(m in q_lower for m in bot_markers):
            return ("meta", None)

    return (None, None)
