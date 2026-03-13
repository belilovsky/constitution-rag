"""
Import faq_extra normalized JSON (from constitution_my content.yaml)
into constitution-rag PostgreSQL.

Adds 3 new document sets:
  - faq_extra_ru (55 chunks) — expanded FAQ in Russian
  - faq_extra_kz (63 chunks) — expanded FAQ in Kazakh
  - faq_extra_en (53 chunks) — expanded FAQ in English

These supplement the existing faq_ru (15) and faq_kz (15) from the PDF brochure.
"""

import json
from pathlib import Path

import psycopg2
from psycopg2.extras import Json

DB = {
    "host": "127.0.0.1",
    "port": 55432,
    "dbname": "constitution_rag",
    "user": "constitution_rag",
    "password": "ConstitutionRag_2026_Strong_Pass_Change_This",
}

BASE = Path("/root/constitution-rag/normalized")

DOCS = [
    {
        "json_path": BASE / "faq_extra_ru_chunks.json",
        "source_type": "faq",
        "source_path": "normalized/faq_extra_ru_chunks.json",
        "doc_key": "krk_2026_faq_extra_ru",
        "title": "FAQ расширенный (constitution.my)",
        "language_code": "ru",
        "section_code": "faq",
        "status": "active",
        "notes": "55 FAQ cards from constitution.my — about, power, rights, history, myths, referendum, local, participation, practical",
    },
    {
        "json_path": BASE / "faq_extra_kz_chunks.json",
        "source_type": "faq",
        "source_path": "normalized/faq_extra_kz_chunks.json",
        "doc_key": "krk_2026_faq_extra_kz",
        "title": "FAQ кеңейтілген (constitution.my)",
        "language_code": "kz",
        "section_code": "faq",
        "status": "active",
        "notes": "63 FAQ cards from constitution.my in Kazakh",
    },
    {
        "json_path": BASE / "faq_extra_en_chunks.json",
        "source_type": "faq",
        "source_path": "normalized/faq_extra_en_chunks.json",
        "doc_key": "krk_2026_faq_extra_en",
        "title": "FAQ expanded (constitution.my)",
        "language_code": "en",
        "section_code": "faq",
        "status": "active",
        "notes": "53 FAQ cards from constitution.my in English",
    },
]


def main():
    conn = psycopg2.connect(**DB)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            for doc in DOCS:
                cur.execute("SELECT 1 FROM documents WHERE doc_key = %s", (doc["doc_key"],))
                if cur.fetchone():
                    print(f"SKIP already exists: {doc['doc_key']}")
                    continue

                data = json.loads(doc["json_path"].read_text(encoding="utf-8"))
                if not data:
                    print(f"SKIP empty: {doc['doc_key']}")
                    continue

                first = data[0]

                meta = {
                    "layer": first.get("layer"),
                    "document": first.get("document"),
                    "effective_date": first.get("effective_date"),
                    "source_file": first.get("source_file"),
                }

                cur.execute(
                    """
                    INSERT INTO import_runs (run_type, source_name, status, stats, notes)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        "json_import",
                        doc["doc_key"],
                        "started",
                        Json({"source_path": doc["source_path"]}),
                        doc["notes"],
                    ),
                )
                import_run_id = cur.fetchone()[0]

                cur.execute(
                    """
                    INSERT INTO documents
                    (source_type, source_path, doc_key, title, language_code, section_code,
                     adopted_at, published_at, status, meta)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        doc["source_type"],
                        doc["source_path"],
                        doc["doc_key"],
                        doc["title"],
                        doc["language_code"],
                        doc["section_code"],
                        None,
                        None,
                        doc["status"],
                        Json(meta),
                    ),
                )
                document_id = cur.fetchone()[0]

                inserted = 0
                for seq, item in enumerate(data, start=1):
                    body = item.get("text", "").strip()
                    heading = item.get("heading", "") or item.get("question", "") or item.get("id", "")

                    chunk_meta = {
                        "layer": item.get("layer"),
                        "document": item.get("document"),
                        "language": item.get("language"),
                        "effective_date": item.get("effective_date"),
                        "source_file": item.get("source_file"),
                        "section": item.get("section"),
                        "slug": item.get("slug"),
                        "question": item.get("question"),
                        "status": item.get("status"),
                        "source_id": item.get("id"),
                    }

                    cur.execute(
                        """
                        INSERT INTO document_chunks
                        (document_id, chunk_index, heading, body, tokens_count, char_count, meta)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            document_id,
                            seq,
                            heading,
                            body,
                            None,
                            len(body),
                            Json(chunk_meta),
                        ),
                    )
                    inserted += 1

                cur.execute(
                    """
                    UPDATE import_runs
                       SET status = %s,
                           finished_at = now(),
                           stats = %s
                     WHERE id = %s
                    """,
                    (
                        "finished",
                        Json(
                            {
                                "doc_key": doc["doc_key"],
                                "document_id": document_id,
                                "chunks_inserted": inserted,
                            }
                        ),
                        import_run_id,
                    ),
                )
                print(f"OK: {doc['doc_key']} document_id={document_id} chunks={inserted}")

        conn.commit()
        print("\nAll committed successfully.")
    except Exception as e:
        conn.rollback()
        print(f"\nROLLBACK: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
