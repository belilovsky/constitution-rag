import json
import sys

from app.answer_runner import generate_answer
from app.retrieval_runner import run_retrieval


def print_row(row):
    print("----")
    print(f"doc_key: {row.get('doc_key')}")
    print(f"status: {row.get('status')}")
    print(f"chunk_index: {row.get('chunk_index')}")
    print(f"heading: {row.get('heading')}")
    print(f"meta: {json.dumps(row.get('meta', {}), ensure_ascii=False)}")
    body = (row.get("body") or "").strip()
    print(f"body: {body[:1200]}")


def print_retrieval_payload(query: str, payload: dict):
    print(f"query: {query}")
    print(f"mode: {payload['mode']}")

    if payload["mode"] == "comparison":
        print("\n=== 2026 ===")
        for row in payload["results"]["2026"]:
            print_row(row)

        print("\n=== 1995 ===")
        for row in payload["results"]["1995"]:
            print_row(row)
        return

    if payload["mode"] == "mixed":
        for idx, bundle in enumerate(payload["results"], start=1):
            print(f"\n=== subquery {idx}: {bundle.get('subquery', '')} ===")
            for row in bundle.get("results", []):
                print_row(row)
        return

    for row in payload["results"]:
        print_row(row)


def print_answer_payload(result: dict):
    print(f"query: {result['query']}")
    print(f"mode: {result['mode']}")
    print("\n=== answer ===")
    print(result["answer"])
    print("\n=== retrieval_snapshot ===")
    print_retrieval_payload(result["query"], result["retrieval"])


def parse_args(argv: list[str]):
    if len(argv) < 2:
        print("Usage:")
        print("  ./.venv/bin/python -m app.ask_cli 'Ваш вопрос'")
        print("  ./.venv/bin/python -m app.ask_cli answer 'Ваш вопрос'")
        print("  ./.venv/bin/python -m app.ask_cli retrieve 'Ваш вопрос'")
        sys.exit(1)

    first = argv[1].strip().lower()

    if first in {"answer", "retrieve"}:
        if len(argv) < 3:
            print(f"Usage: ./.venv/bin/python -m app.ask_cli {first} 'Ваш вопрос'")
            sys.exit(1)
        return first, argv[2]

    return "answer", argv[1]


def main():
    mode, query = parse_args(sys.argv)

    if mode == "retrieve":
        payload = run_retrieval(query)
        print_retrieval_payload(query, payload)
        return

    result = generate_answer(query)
    print_answer_payload(result)


if __name__ == "__main__":
    main()
