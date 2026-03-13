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

# Smalltalk that should get a friendly response without retrieval
_SMALLTALK_PATTERNS = [
    r"^\s*(как\s+(у тебя\s+)?дела|как\s+жизнь|как\s+поживаешь|как\s+ты|как\s+сам)\s*[!.?]*\s*$",
    r"^\s*(спасибо|благодар\w+|thank\w*|рахмет\w*)\s*[!.?]*\s*$",
    r"^\s*(пока|до\s*свидания|bye|прощай|увидимся|бай)\s*[!.?]*\s*$",
    r"^\s*(ок|окей|okay|ладно|понятно|ясно|хорошо|класс|круто|отлично|супер)\s*[!.?]*\s*$",
    r"^\s*(да|нет|не|ага|угу|неа)\s*[!.?]*\s*$",
]

SMALLTALK_RESPONSES = {
    "greeting_back": {
        "ru": "У меня всё отлично, спасибо! Готов помочь с вопросами по Конституции. Что интересует?",
        "kz": "Бәрі жақсы, рахмет! Конституция бойынша сұрақтарға көмектесуге дайынмын. Не қызықтырады?",
        "en": "I'm doing great, thanks! Ready to help with Constitution questions. What interests you?",
    },
    "thanks": {
        "ru": "Пожалуйста! Если есть ещё вопросы по Конституции — спрашивай.",
        "kz": "Оқасы жоқ! Конституция бойынша сұрақтар болса — сұраңыз.",
        "en": "You're welcome! Feel free to ask more about the Constitution.",
    },
    "bye": {
        "ru": "До встречи! Если появятся вопросы по Конституции — возвращайся.",
        "kz": "Сау болыңыз! Конституция бойынша сұрақтар болса — қайта оралыңыз.",
        "en": "Goodbye! Come back if you have more Constitution questions.",
    },
    "acknowledgment": {
        "ru": "Хорошо! Если хочешь узнать что-то по Конституции — спрашивай.",
        "kz": "Жақсы! Конституция бойынша білгің келсе — сұра.",
        "en": "Got it! Feel free to ask about the Constitution.",
    },
}

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


def _detect_smalltalk_type(q_lower: str) -> str | None:
    """Detect specific smalltalk sub-type for appropriate response."""
    if re.match(r"^\s*(как\s+(у тебя\s+)?дела|как\s+жизнь|как\s+поживаешь|как\s+ты|как\s+сам)\s*[!.?]*\s*$", q_lower):
        return "greeting_back"
    if re.match(r"^\s*(спасибо|благодар\w+|thank\w*|рахмет\w*)\s*[!.?]*\s*$", q_lower):
        return "thanks"
    if re.match(r"^\s*(пока|до\s*свидания|bye|прощай|увидимся|бай|goodbye)\s*[!.?]*\s*$", q_lower):
        return "bye"
    if re.match(r"^\s*(ок|окей|okay|ладно|понятно|ясно|хорошо|класс|круто|отлично|супер|да|ага|угу)\s*[!.?]*\s*$", q_lower):
        return "acknowledgment"
    return None


def classify_conversational(query: str, lang: str = "ru") -> tuple[str | None, str | None]:
    """
    Classify query as conversational (greeting/smalltalk/meta/followup) or normal.

    Returns:
        (category, response_or_none)
        category: "greeting" | "smalltalk" | "meta" | "followup" | None
        response_or_none: pre-built response for greetings/smalltalk, None otherwise
    """
    q = query.strip()
    q_lower = q.lower().replace("ё", "е")

    # 1. Greeting detection
    for pattern in _GREETING_PATTERNS:
        if re.match(pattern, q_lower, re.IGNORECASE):
            return ("greeting", GREETING_RESPONSES.get(lang, GREETING_RESPONSES["ru"]))

    # 2. Smalltalk detection (как дела, спасибо, пока, ок)
    smalltalk_type = _detect_smalltalk_type(q_lower)
    if smalltalk_type:
        responses = SMALLTALK_RESPONSES.get(smalltalk_type, SMALLTALK_RESPONSES["acknowledgment"])
        return ("smalltalk", responses.get(lang, responses["ru"]))

    # 3. Followup detection (must be before meta to catch "расскажи" without topic)
    for pattern in _FOLLOWUP_PATTERNS:
        if re.match(pattern, q_lower, re.IGNORECASE):
            return ("followup", None)

    # 4. Meta-question detection (explicit patterns)
    for pattern in _META_PATTERNS:
        if re.search(pattern, q_lower, re.IGNORECASE):
            return ("meta", None)

    # 5. Short vague queries with no constitution topic → treat as meta
    words = q_lower.split()
    if len(words) <= _SHORT_VAGUE_MAX_WORDS and not _has_constitution_topic(q_lower):
        bot_markers = ["ты", "тебя", "тебе", "теб", "себя", "себе"]
        if any(m in q_lower for m in bot_markers):
            return ("meta", None)

    return (None, None)
