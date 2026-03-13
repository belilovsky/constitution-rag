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
    r"(что\s+(ты\s+)?(можешь|умеешь|знаешь|делаешь))",
    r"(что\s+ты\s+мож\w+\s+предложить)",
    r"(что\s+(ты\s+)?за\s+бот)",
    r"(кто\s+ты|ты\s+кто)",
    r"(как\s+тебя\s+зовут)",
    r"(расскажи\s+о\s+себе)",
    r"(чем\s+(ты\s+)?помо\w+)",
    r"(помоги\s+мне)$",
    r"(что\s+здесь\s+можно)",
    r"(как\s+(мне\s+)?пользоваться)",
    r"(what\s+can\s+you\s+do)",
    r"(help\s*me?)$",
    r"(who\s+are\s+you)",
]

# Short vague queries that retrieval can't handle well
_FOLLOWUP_PATTERNS = [
    r"^\s*(расскажи|ещё|еще|продолжай|дальше|подробнее|и\?|ну\??|давай)\s*[!.?]*\s*$",
    r"^\s*(а\s+что\s+ещ[её]|что\s+ещ[её])\s*[!.?]*\s*$",
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


def classify_conversational(query: str, lang: str = "ru") -> tuple[str | None, str | None]:
    """
    Classify query as conversational (greeting/meta/followup) or normal.

    Returns:
        (category, response_or_none)
        category: "greeting" | "meta" | "followup" | None
        response_or_none: pre-built response for greetings, None otherwise
    """
    q = query.strip()
    q_lower = q.lower()

    # 1. Greeting detection
    for pattern in _GREETING_PATTERNS:
        if re.match(pattern, q_lower, re.IGNORECASE):
            return ("greeting", GREETING_RESPONSES.get(lang, GREETING_RESPONSES["ru"]))

    # 2. Followup detection (must be before meta to catch "расскажи" without topic)
    for pattern in _FOLLOWUP_PATTERNS:
        if re.match(pattern, q_lower, re.IGNORECASE):
            return ("followup", None)

    # 3. Meta-question detection
    for pattern in _META_PATTERNS:
        if re.search(pattern, q_lower, re.IGNORECASE):
            return ("meta", None)

    return (None, None)
