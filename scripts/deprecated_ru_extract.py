#!/usr/bin/env python3
"""Extract deprecated_ru chunks from Constitution 1995 RU PDF."""
import json, re, sys
try:
    import pdfplumber
except ImportError:
    sys.exit("pip install pdfplumber")

INPUT  = "raw/deprecated/1995 рус.pdf"
OUTPUT = "deprecated_ru_chunks.json"

with pdfplumber.open(INPUT) as pdf:
    full = "\n".join(page.extract_text() or "" for page in pdf.pages)

# Constitution 1995 RU uses "Статья N" format
pattern = r'(?=(?:^|\n)\s*Статья\s+(\d+)\b)'
parts = re.split(pattern, full)

chunks = []

# Preamble
preamble = parts[0].strip()
if preamble and len(preamble) > 50:
    chunks.append({
        "id": "deprecated_ru_preamble",
        "layer": "norm",
        "language": "ru",
        "document": "Constitution-1995",
        "content_type": "preamble",
        "article_number": 0,
        "article_title": "Преамбула",
        "section_number": "0",
        "section_title": "Преамбула",
        "text": preamble,
        "status": "deprecated",
        "effective_date": "1995-08-30",
        "deprecated_date": "2026-07-01",
        "deprecation_note": "Replaced by KRK-2026 (Constitutional Law of the Republic of Kazakhstan)",
        "source_file": INPUT
    })

sections_ru = {
    "I":    "Общие положения",
    "II":   "Человек и гражданин",
    "III":  "Президент",
    "IV":   "Парламент",
    "V":    "Правительство",
    "VI":   "Конституционный Суд",
    "VII":  "Суды и правосудие",
    "VIII": "Местное государственное управление и самоуправление",
    "IX":   "Заключительные и переходные положения",
}
current_section = "I"

i = 1
while i < len(parts) - 1:
    art_num = int(parts[i])
    art_text = parts[i+1].strip()

    # Detect section from "Раздел N." headers
    sec_match = re.search(r'Раздел\s+([IVX]+)', art_text[:200])
    if sec_match:
        current_section = sec_match.group(1)

    chunks.append({
        "id": f"deprecated_ru_art{art_num}",
        "layer": "norm",
        "language": "ru",
        "document": "Constitution-1995",
        "content_type": "article",
        "article_number": art_num,
        "article_title": f"Статья {art_num}",
        "section_number": current_section,
        "section_title": sections_ru.get(current_section, ""),
        "text": art_text,
        "status": "deprecated",
        "effective_date": "1995-08-30",
        "deprecated_date": "2026-07-01",
        "deprecation_note": "Replaced by KRK-2026 (Constitutional Law of the Republic of Kazakhstan)",
        "source_file": INPUT
    })
    i += 2

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(chunks, f, ensure_ascii=False, indent=2)

print(f"Done: {len(chunks)} chunks -> {OUTPUT}")
