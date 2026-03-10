#!/usr/bin/env python3
"""Extract commentary_ru chunks from Metodichka RU PDF."""
import json, re, sys
try:
    import pdfplumber
except ImportError:
    sys.exit("pip install pdfplumber")

INPUT  = "26_02_14-RUS_Metodichka-Konstituciya_A5_unlocked.pdf"
OUTPUT = "commentary_ru_chunks.json"

with pdfplumber.open(INPUT) as pdf:
    full = "\n".join(page.extract_text() or "" for page in pdf.pages)

# Split by "Статья N" pattern
pattern = r'(?=(?:^|\n)\s*Статья\s+(\d+)\b)'
parts = re.split(pattern, full)

chunks = []

# Intro / preamble commentary (before first article)
intro = parts[0].strip()
if intro and len(intro) > 100:
    chunks.append({
        "id": "commentary_ru_intro",
        "layer": "commentary",
        "language": "ru",
        "document": "Metodichka-KRK-2026",
        "content_type": "introduction",
        "article_number": 0,
        "article_title": "Введение",
        "section_number": "0",
        "section_title": "Введение",
        "text": intro,
        "status": "active",
        "effective_date": "2026-07-01",
        "source_file": INPUT
    })

sections_map = {
    "I":    "Основы конституционного строя",
    "II":   "Основные права, свободы и обязанности",
    "III":  "Президент",
    "IV":   "Курултай",
    "V":    "Правительство",
    "VI":   "Қазақстан Халық Кеңесі",
    "VII":  "Конституционный Суд",
    "VIII": "Правосудие. Прокуратура",
    "IX":   "Местное управление",
    "X":    "Изменения",
    "XI":   "Заключительные положения",
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
        "id": f"commentary_ru_art{art_num}",
        "layer": "commentary",
        "language": "ru",
        "document": "Metodichka-KRK-2026",
        "content_type": "article_commentary",
        "article_number": art_num,
        "article_title": f"Статья {art_num}",
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
