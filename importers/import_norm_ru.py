import json
from pathlib import Path

import psycopg2
from psycopg2.extras import Json

DB = {
    "host": "127.0.0.1",
    "port": 5432,
    "dbname": "constitution_rag",
    "user": "constitution_rag",
    "password": "ConstitutionRag_2026_Strong_Pass_Change_This",
}

JSON_PATH = Path("/work/normalized/norm_ru_chunks.json")

DOC = {
    "source_type": "normative",
    "source_path": "normalized/norm_ru_chunks.json",
    "doc_key": "krk_2026_norm_ru",
    "title": "КРК-2026",
    "language_code": "ru",
    "section_code": "constitution",
    "adopted_at": None,
    "published_at": None,
    "status": "active",
    "meta": {
        "layer": "norm",
        "document": "КРК-2026",
        "effective_date": "2026-07-01",
        "source_file": "КРК 12.02.26 рус.docx",
    },
}


def main():
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))

    conn = psycopg2.connect(**DB)
    conn.autocommit = False

    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM documents WHERE doc_key = %s",
                (DOC["doc_key"],),
            )
            if cur.fetchone():
                raise RuntimeError(
                    "documents.doc_key 'krk_2026_norm_ru' already exists"
                )

            cur.execute(
                """
                INSERT INTO import_runs (run_type, source_name, status, stats, notes)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    "json_import",
                    DOC["doc_key"],
                    "started",
                    Json({"source_path": DOC["source_path"]}),
                    "First production import of norm_ru",
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
                    DOC["source_type"],
                    DOC["source_path"],
                    DOC["doc_key"],
                    DOC["title"],
                    DOC["language_code"],
                    DOC["section_code"],
                    DOC["adopted_at"],
                    DOC["published_at"],
                    DOC["status"],
                    Json(DOC["meta"]),
                ),
            )
            document_id = cur.fetchone()[0]

            inserted = 0
            for item in data:
                body = item["text"].strip()
                heading = item.get("article_title")
                chunk_index = int(item["article_number"])

                meta = {
                    "layer": item.get("layer"),
                    "document": item.get("document"),
                    "language": item.get("language"),
                    "article_number": item.get("article_number"),
                    "article_title": item.get("article_title"),
                    "section_number": item.get("section_number"),
                    "section_title": item.get("section_title"),
                    "effective_date": item.get("effective_date"),
                    "status": item.get("status"),
                    "source_file": item.get("source_file"),
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
                        chunk_index,
                        heading,
                        body,
                        None,
                        len(body),
                        Json(meta),
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
                            "doc_key": DOC["doc_key"],
                            "document_id": document_id,
                            "chunks_inserted": inserted,
                        }
                    ),
                    import_run_id,
                ),
            )

        conn.commit()
        print(f"OK: inserted document_id={document_id}, chunks={inserted}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
