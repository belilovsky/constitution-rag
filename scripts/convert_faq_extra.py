"""
Convert constitution_my content.yaml FAQ cards into normalized JSON
for import into constitution-rag PostgreSQL.

Input: content_parsed.json (171 cards, 3 languages)
Output:
  - normalized/faq_extra_ru_chunks.json (55 cards)
  - normalized/faq_extra_kz_chunks.json (63 cards)
  - normalized/faq_extra_en_chunks.json (53 cards)

Each card becomes one chunk with:
  - question as heading
  - short + answer + facts merged as body text
  - section, slug, kind in meta
"""

import json
import re
from pathlib import Path

INPUT = Path("content_parsed.json")
OUT_DIR = Path("normalized")
OUT_DIR.mkdir(exist_ok=True)

LAYER = "faq"
EFFECTIVE_DATE = "2026-03-15"

LANG_MAP = {
    "ru": "ru",
    "kk": "kz",  # content.yaml uses "kk", DB uses "kz"
    "en": "en",
}


def clean(text: str) -> str:
    """Normalize whitespace."""
    text = text.strip()
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def card_to_chunk(card: dict, seq: int, lang_code: str) -> dict:
    """Convert a single FAQ card to a normalized chunk."""
    slug = card.get("slug", "")
    question = clean(card.get("question", ""))
    short = clean(card.get("short", ""))
    section = card.get("section", "")

    blocks = card.get("blocks") or {}
    answer = clean(blocks.get("answer", ""))
    facts = clean(blocks.get("facts", ""))

    # Build body: short answer + detailed answer + key facts
    body_parts = []
    if short:
        body_parts.append(short)
    if answer:
        body_parts.append(answer)
    if facts:
        body_parts.append(f"Ключевые факты:\n{facts}" if lang_code == "ru"
                         else f"Негізгі фактілер:\n{facts}" if lang_code == "kz"
                         else f"Key facts:\n{facts}")

    body = "\n\n".join(body_parts)

    chunk_id = f"faq_extra_{lang_code}_{slug}"

    return {
        "id": chunk_id,
        "layer": LAYER,
        "document": "faq_extra",
        "language": lang_code,
        "effective_date": EFFECTIVE_DATE,
        "source_file": "content.yaml",
        "section": section,
        "slug": slug,
        "question": question,
        "heading": question,
        "text": body,
        "seq": seq,
        "status": "active",
    }


def main():
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    print(f"Loaded: {len(data)} cards")

    # Group by language
    by_lang = {}
    for card in data:
        lang = card.get("lang", "ru")
        db_lang = LANG_MAP.get(lang, lang)
        by_lang.setdefault(db_lang, []).append(card)

    for lang_code, cards in sorted(by_lang.items()):
        chunks = []
        for seq, card in enumerate(cards, 1):
            chunk = card_to_chunk(card, seq, lang_code)
            chunks.append(chunk)

        outpath = OUT_DIR / f"faq_extra_{lang_code}_chunks.json"
        with open(outpath, "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)

        # Stats
        lengths = [len(c["text"]) for c in chunks]
        empty = sum(1 for l in lengths if l < 10)
        print(f"  {lang_code}: {len(chunks)} chunks, "
              f"min={min(lengths)}, max={max(lengths)}, avg={sum(lengths)//len(lengths)}, "
              f"empty={empty}, file={outpath.stat().st_size/1024:.1f} KB")

    total = sum(len(cards) for cards in by_lang.values())
    print(f"\nTotal: {total} chunks across {len(by_lang)} languages")


if __name__ == "__main__":
    main()
