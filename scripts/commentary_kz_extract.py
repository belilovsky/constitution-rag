#!/usr/bin/env python3
"""Extract commentary_kz chunks from Metodichka KZ PDF."""
import json, re, sys
try:
    import pdfplumber
except ImportError:
    sys.exit("pip install pdfplumber")

INPUT  = "raw/commentary/260218=Методичка финал каз.версия+.pdf"
OUTPUT = "commentary_kz_chunks.json"

with pdfplumber.open(INPUT) as pdf:
    full = "\n".join(page.extract_text() or "" for page in pdf.pages)

# Split by "N-бап" or "N бап" pattern (Kazakh article markers)
pattern = r'(?=(?:^|\n)\s*(\d+)[\s-]*[Бб]ап\b)'
parts = re.split(pattern, full)

chunks = []

# Intro / КІРІСПЕ
intro = parts[0].strip()
if intro and len(intro) > 100:
    chunks.append({
        "id": "commentary_kz_intro",
        "layer": "commentary",
        "language": "kz",
        "document": "Metodichka-KRK-2026",
        "content_type": "introduction",
        "article_number": 0,
        "article_title": "Кіріспе",
        "section_number": "0",
        "section_title": "Кіріспе",
        "text": intro,
        "status": "active",
        "effective_date": "2026-07-01",
        "source_file": INPUT
    })

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

current_section = "I"
i = 1
while i < len(parts) - 1:
    art_num = int(parts[i])
    art_text = parts[i+1].strip()

    for sec, title in sections_map.items():
        if title.lower() in art_text[:300].lower():
            current_section = sec
            break

    chunks.append({
        "id": f"commentary_kz_art{art_num}",
        "layer": "commentary",
        "language": "kz",
        "document": "Metodichka-KRK-2026",
        "content_type": "article_commentary",
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
