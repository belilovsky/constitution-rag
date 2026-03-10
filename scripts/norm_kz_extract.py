#!/usr/bin/env python3
"""Extract norm_kz chunks from KRK-2026 Kazakh DOCX."""
import json, re, sys
try:
    from docx import Document
except ImportError:
    sys.exit("pip install python-docx")

INPUT  = "raw/norm/КРК 12.02.26 каз.docx"
OUTPUT = "norm_kz_chunks.json"

doc = Document(INPUT)
paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

sections_map = {
    "I":   "Конституциялық құрылыс негіздері",
    "II":  "Негізгі құқықтар, бостандықтар мен міндеттер",
    "III": "Президент",
    "IV":  "Құрылтай",
    "V":   "Үкімет",
    "VI":  "Қазақстан Халық Кеңесі",
    "VII": "Конституциялық Сот",
    "VIII":"Сот төрелігі. Прокуратура",
    "IX":  "Жергілікті басқару",
    "X":   "Өзгерістер",
    "XI":  "Қорытынды ережелер",
}

def norm_roman(s: str) -> str:
    s = s.strip()
    repl = {
        "І": "I",
        "Ⅱ": "II",
        "Ⅲ": "III",
        "Ⅳ": "IV",
        "Ⅴ": "V",
        "Ⅵ": "VI",
        "Ⅶ": "VII",
        "Ⅷ": "VIII",
        "Ⅸ": "IX",
        "Ⅹ": "X",
        "Ⅺ": "XI",
    }
    return repl.get(s, s)

chunks = []
current_section = "0"
current_section_title = "Кіріспе"
article_num = None
article_lines = []
preamble_lines = []

def flush_article():
    global article_num, article_lines, current_section, current_section_title, chunks
    if article_num is None:
        return
    text = "\n".join(article_lines).strip()
    chunks.append({
        "id": f"norm_kz_art{article_num}",
        "layer": "norm",
        "language": "kz",
        "document": "KRK-2026",
        "content_type": "article",
        "article_number": article_num,
        "article_title": f"{article_num}-бап",
        "section_number": current_section,
        "section_title": current_section_title,
        "text": text,
        "status": "active",
        "effective_date": "2026-07-01",
        "source_file": INPUT
    })

i = 0
while i < len(paras):
    line = paras[i]

    sec_match = re.match(r'^([IVXІVХ]+)\s+бөлім$', line, flags=re.IGNORECASE)
    if sec_match:
        roman = norm_roman(sec_match.group(1).upper())
        next_title = paras[i+1].strip() if i + 1 < len(paras) else sections_map.get(roman, "")
        current_section = roman
        current_section_title = next_title or sections_map.get(roman, "")
        if article_num is None:
            preamble_lines.append(line)
            if i + 1 < len(paras):
                preamble_lines.append(paras[i+1].strip())
            i += 2
            continue
        else:
            article_lines.append(line)
            if i + 1 < len(paras):
                article_lines.append(paras[i+1].strip())
            i += 2
            continue

    art_match = re.match(r'^(\d+)[\s-]*бап$', line, flags=re.IGNORECASE)
    if art_match:
        if article_num is None:
            preamble_text = "\n".join(preamble_lines).strip()
            if preamble_text:
                chunks.append({
                    "id": "norm_kz_preamble",
                    "layer": "norm",
                    "language": "kz",
                    "document": "KRK-2026",
                    "content_type": "preamble",
                    "article_number": 0,
                    "article_title": "Кіріспе",
                    "section_number": "0",
                    "section_title": "Кіріспе",
                    "text": preamble_text,
                    "status": "active",
                    "effective_date": "2026-07-01",
                    "source_file": INPUT
                })
        else:
            flush_article()

        article_num = int(art_match.group(1))
        article_lines = []
        i += 1
        continue

    if article_num is None:
        preamble_lines.append(line)
    else:
        article_lines.append(line)

    i += 1

if article_num is None:
    preamble_text = "\n".join(preamble_lines).strip()
    if preamble_text:
        chunks.append({
            "id": "norm_kz_preamble",
            "layer": "norm",
            "language": "kz",
            "document": "KRK-2026",
            "content_type": "preamble",
            "article_number": 0,
            "article_title": "Кіріспе",
            "section_number": "0",
            "section_title": "Кіріспе",
            "text": preamble_text,
            "status": "active",
            "effective_date": "2026-07-01",
            "source_file": INPUT
        })
else:
    flush_article()

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(chunks, f, ensure_ascii=False, indent=2)

print(f"Done: {len(chunks)} chunks -> {OUTPUT}")
