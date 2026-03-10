#!/usr/bin/env python3
"""Extract deprecated_kz chunks from Constitution 1995 KZ PDF."""
import json, re, sys
try:
    import pdfplumber
except ImportError:
    sys.exit("pip install pdfplumber")

INPUT  = "raw/deprecated/1995 қаз.pdf"
OUTPUT = "deprecated_kz_chunks.json"

with pdfplumber.open(INPUT) as pdf:
    full = "\n".join(page.extract_text() or "" for page in pdf.pages)

# Constitution 1995 KZ uses "N-бап" format (e.g., "1-бап", "2-бап")
pattern = r'(?=(?:^|\n)\s*(\d+)-бап\b)'
parts = re.split(pattern, full)

chunks = []

# Preamble
preamble = parts[0].strip()
if preamble and len(preamble) > 50:
    chunks.append({
        "id": "deprecated_kz_preamble",
        "layer": "norm",
        "language": "kz",
        "document": "Constitution-1995",
        "content_type": "preamble",
        "article_number": 0,
        "article_title": "Кіріспе",
        "section_number": "0",
        "section_title": "Кіріспе",
        "text": preamble,
        "status": "deprecated",
        "effective_date": "1995-08-30",
        "deprecated_date": "2026-07-01",
        "deprecation_note": "Replaced by KRK-2026 (Constitutional Law of the Republic of Kazakhstan)",
        "source_file": INPUT
    })

sections_kz = ["I","II","III","IV","V","VI","VII","VIII","IX"]
current_section = "I"

i = 1
while i < len(parts) - 1:
    art_num = int(parts[i])
    art_text = parts[i+1].strip()

    # Detect section changes from "N бөлім" headers
    sec_match = re.search(r'([IVX]+)\s+бөлім', art_text[:200])
    if sec_match:
        current_section = sec_match.group(1)

    chunks.append({
        "id": f"deprecated_kz_art{art_num}",
        "layer": "norm",
        "language": "kz",
        "document": "Constitution-1995",
        "content_type": "article",
        "article_number": art_num,
        "article_title": f"{art_num}-бап",
        "section_number": current_section,
        "section_title": "",
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
