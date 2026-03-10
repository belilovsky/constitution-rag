#!/usr/bin/env python3
"""Extract faq_kz chunks from FAQ KZ PDF."""
import json, re, sys
try:
    import pdfplumber
except ImportError:
    sys.exit("pip install pdfplumber")

INPUT  = "raw/faq/26_02_14=QAZ_Өзекті сұрақтар мен жауаптар_А5_unlocked.pdf"
OUTPUT = "faq_kz_chunks.json"

with pdfplumber.open(INPUT) as pdf:
    full = "\n".join(page.extract_text() or "" for page in pdf.pages)

# Split by numbered questions: "1. ...", "2. ...", etc. at line start
# Skip TOC-style entries by requiring substantial text after number
pattern = r'(?=(?:^|\n)\s*(\d{1,2})\.\s+[А-ЯӘҒҚҢӨҰҮІа-яәғқңөұүі])'
parts = re.split(pattern, full)

chunks = []
seen_nums = set()

i = 1
while i < len(parts) - 1:
    q_num = int(parts[i])
    q_text = parts[i+1].strip()

    # Skip TOC entries (short) and duplicates
    if len(q_text) < 200 or q_num in seen_nums:
        i += 2
        continue

    seen_nums.add(q_num)

    # Split into question and answer
    lines = q_text.split("\n")
    question_lines = []
    answer_lines = []
    in_answer = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if question_lines and not in_answer:
                in_answer = True
            continue
        if not in_answer:
            question_lines.append(stripped)
        else:
            answer_lines.append(stripped)

    question = " ".join(question_lines)
    answer = "\n".join(answer_lines)

    # Clean up question: remove leading "N. "
    question = re.sub(r'^\d{1,2}\.\s*', '', question).strip()

    if not answer:
        answer = question
        question = f"FAQ #{q_num}"

    chunks.append({
        "id": f"faq_kz_{q_num}",
        "layer": "faq",
        "language": "kz",
        "document": "FAQ-KRK-2026",
        "content_type": "qa_pair",
        "question_number": q_num,
        "question": question,
        "answer": answer,
        "status": "active",
        "effective_date": "2026-07-01",
        "source_file": INPUT
    })
    i += 2

chunks.sort(key=lambda c: c["question_number"])

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(chunks, f, ensure_ascii=False, indent=2)

print(f"Done: {len(chunks)} chunks -> {OUTPUT}")
