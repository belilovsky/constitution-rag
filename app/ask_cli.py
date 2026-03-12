
import json
import sys
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


def main():
    if len(sys.argv) < 2:
        print("Usage: ./.venv/bin/python -m app.ask_cli 'Ваш вопрос'")
        sys.exit(1)

    query = sys.argv[1]
    payload = run_retrieval(query)

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

    for row in payload["results"]:
        print_row(row)


if __name__ == "__main__":
    main()
