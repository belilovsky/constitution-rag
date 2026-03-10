#!/usr/bin/env python3
"""Extract norm_kz chunks from KRK-2026 Kazakh DOCX."""
import json, re, sys
try:
    from docx import Document
except ImportError:
    sys.exit("pip install python-docx")

INPUT  = "KRK-12.02.26-kaz.docx"
OUTPUT = "norm_kz_chunks.json"

doc = Document(INPUT)
full = "\n".join(p.text for p in doc.paragraphs)

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

# Split by **N-бап** or **N бап** patterns
pattern = r'(?=\*\*(\d+)[\s-]*[Бб]ап\b)'
parts = re.split(pattern, full)

chunks = []

# Preamble
preamble_text = parts[0].strip() if parts else ""
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

# Articles
current_section = "I"
i = 1
while i < len(parts) - 1:
    art_num = int(parts[i])
    art_text = parts[i+1].strip()
    # Remove leading **N-бап** / **N бап** header from text body
    art_text = re.sub(r'^\*\*\d+[\s-]*[Бб]ап\b[^*]*\*\*\s*', '', art_text).strip()

    # Determine section
    for sec, title in sections_map.items():
        if title.lower() in art_text[:200].lower():
            current_section = sec
            break

    chunks.append({
        "id": f"norm_kz_art{art_num}",
        "layer": "norm",
        "language": "kz",
        "document": "KRK-2026",
        "content_type": "article",
        "article_number": art_num,
        "article_title": f"{art_num}-бап",
        "section_number": current_section,
        "section_title": sections_map.get(current_section, ""),
        "text": art_text,
        "status": "active",
        "effective_date": "2026-07-01",
        "source_file": INPUT
    })
    i += 2

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(chunks, f, ensure_ascii=False, indent=2)

print(f"Done: {len(chunks)} chunks -> {OUTPUT}")
