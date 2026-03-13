#!/usr/bin/env python3
"""
Generate FAQ cache by running top-30 questions through the pipeline.
Run from repo root:  python scripts/generate_faq_cache.py
Output: app/faq_cache.json
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.answer_runner import generate_answer

QUESTIONS = [
    "Что такое новая Конституция 2026 года?",
    "Когда будет референдум по Конституции?",
    "Что говорится о свободе слова?",
    "Какие права есть у граждан в проекте?",
    "Чем новая Конституция отличается от старой?",
    "Что сказано о праве на мирные собрания?",
    "Какие полномочия у Президента?",
    "Что такое Курултай?",
    "Что такое Народный Совет?",
    "Когда вступает в силу новая Конституция?",
    "Можно ли лишить гражданства?",
    "Что сказано об образовании?",
    "Какие социальные права есть в проекте?",
    "Что говорится о языке?",
    "Зачем нужна новая Конституция?",
    "Что сказано о судебной системе?",
    "Какие экономические права есть?",
    "Что говорится о местном самоуправлении?",
    "Что сказано о правах детей?",
    "Как защищается частная собственность?",
    "Что говорится о свободе вероисповедания?",
    "Какие обязанности есть у граждан?",
    "Что сказано о СМИ и цензуре?",
    "Как изменится парламент?",
    "Что говорится о правах женщин?",
    "Кто разработал проект Конституции?",
    "Что сказано о защите персональных данных?",
    "Какие экологические права есть?",
    "Что говорится о труде и занятости?",
    "Как можно ознакомиться с полным текстом проекта?",
]


def main():
    results = []
    total = len(QUESTIONS)

    for i, q in enumerate(QUESTIONS, 1):
        print(f"[{i}/{total}] {q[:60]}...", end=" ", flush=True)
        t0 = time.time()

        try:
            result = generate_answer(q)
            elapsed = int((time.time() - t0) * 1000)
            answer = result.get("answer", "")
            mode = result.get("mode", "")

            results.append({
                "q": q,
                "a": answer,
                "mode": mode,
            })
            print(f"OK ({elapsed}ms, {len(answer)} chars)")

        except Exception as e:
            print(f"FAIL: {e}")
            results.append({
                "q": q,
                "a": "",
                "mode": "error",
            })

        time.sleep(0.3)

    # Save
    outpath = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "app",
        "faq_cache.json",
    )
    with open(outpath, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    ok = sum(1 for r in results if r["a"])
    print(f"\nDone: {ok}/{total} answers")
    print(f"Saved to: {outpath}")


if __name__ == "__main__":
    main()
