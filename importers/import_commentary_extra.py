"""
Import commentary_extra normalized JSON into constitution-rag PostgreSQL.

Adds 4 new document sets:
  - commentary_extra_audiences_ru (151 chunks) — target audience commentary
  - commentary_extra_lines_ru (91 chunks) — referendum lines + counter-arguments + NK lines
  - commentary_extra_theses_ru (38 chunks) — key aspects + commission theses
  - commentary_extra_comparison_ru (9 chunks) — 1995 vs 2026 comparison

Follows the same schema as import_all_remaining.py.
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
        "json_path": BASE / "commentary_extra_audiences_ru_chunks.json",
        "source_type": "commentary",
        "source_path": "normalized/commentary_extra_audiences_ru_chunks.json",
        "doc_key": "krk_2026_ce_audiences_ru",
        "title": "Линии комментирования по целевым аудиториям",
        "language_code": "ru",
        "section_code": "commentary",
        "status": "active",
        "notes": "8 target audience commentary docs — госслужащие, журналисты, молодёжь, правозащитники, бизнес, преподаватели, религиозные, нацпатриоты",
    },
    {
        "json_path": BASE / "commentary_extra_lines_ru_chunks.json",
        "source_type": "commentary",
        "source_path": "normalized/commentary_extra_lines_ru_chunks.json",
        "doc_key": "krk_2026_ce_lines_ru",
        "title": "Линии комментирования и контраргументы",
        "language_code": "ru",
        "section_code": "commentary",
        "status": "active",
        "notes": "Referendum lines + counter-arguments + NK commentary lines",
    },
    {
        "json_path": BASE / "commentary_extra_theses_ru_chunks.json",
        "source_type": "commentary",
        "source_path": "normalized/commentary_extra_theses_ru_chunks.json",
        "doc_key": "krk_2026_ce_theses_ru",
        "title": "Ключевые аспекты и тезисы Конституционной комиссии",
        "language_code": "ru",
        "section_code": "commentary",
        "status": "active",
        "notes": "Key constitutional novellas + commission theses",
    },
    {
        "json_path": BASE / "commentary_extra_comparison_ru_chunks.json",
        "source_type": "commentary",
        "source_path": "normalized/commentary_extra_comparison_ru_chunks.json",
        "doc_key": "krk_2026_ce_comparison_ru",
        "title": "Сравнение Конституций 1995 и 2026",
        "language_code": "ru",
        "section_code": "commentary",
        "status": "active",
        "notes": "Side-by-side comparison table: old vs new constitution",
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
                    "sub_group": first.get("sub_group"),
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
                    heading = item.get("heading", "") or item.get("id", "")

                    chunk_meta = {
                        "layer": item.get("layer"),
                        "document": item.get("document"),
                        "language": item.get("language"),
                        "effective_date": item.get("effective_date"),
                        "source_file": item.get("source_file"),
                        "sub_group": item.get("sub_group"),
                        "audience": item.get("audience"),
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
