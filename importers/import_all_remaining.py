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
        "json_path": BASE / "norm_kz_chunks.json",
        "source_type": "normative",
        "source_path": "normalized/norm_kz_chunks.json",
        "doc_key": "krk_2026_norm_kz",
        "title": "КРК-2026",
        "language_code": "kz",
        "section_code": "constitution",
        "status": "active",
        "notes": "Production import of norm_kz",
    },
    {
        "json_path": BASE / "commentary_ru_chunks.json",
        "source_type": "commentary",
        "source_path": "normalized/commentary_ru_chunks.json",
        "doc_key": "krk_2026_commentary_ru",
        "title": "КРК-2026 комментарий",
        "language_code": "ru",
        "section_code": "commentary",
        "status": "active",
        "notes": "Production import of commentary_ru",
    },
    {
        "json_path": BASE / "commentary_kz_chunks.json",
        "source_type": "commentary",
        "source_path": "normalized/commentary_kz_chunks.json",
        "doc_key": "krk_2026_commentary_kz",
        "title": "КРК-2026 түсіндірме",
        "language_code": "kz",
        "section_code": "commentary",
        "status": "active",
        "notes": "Production import of commentary_kz",
    },
    {
        "json_path": BASE / "faq_ru_chunks.json",
        "source_type": "faq",
        "source_path": "normalized/faq_ru_chunks.json",
        "doc_key": "krk_2026_faq_ru",
        "title": "КРК-2026 FAQ",
        "language_code": "ru",
        "section_code": "faq",
        "status": "active",
        "notes": "Production import of faq_ru",
    },
    {
        "json_path": BASE / "faq_kz_chunks.json",
        "source_type": "faq",
        "source_path": "normalized/faq_kz_chunks.json",
        "doc_key": "krk_2026_faq_kz",
        "title": "КРК-2026 FAQ",
        "language_code": "kz",
        "section_code": "faq",
        "status": "active",
        "notes": "Production import of faq_kz",
    },
    {
        "json_path": BASE / "deprecated_ru_chunks.json",
        "source_type": "normative",
        "source_path": "normalized/deprecated_ru_chunks.json",
        "doc_key": "krk_1995_deprecated_ru",
        "title": "Конституция РК 1995",
        "language_code": "ru",
        "section_code": "constitution",
        "status": "deprecated",
        "notes": "Production import of deprecated_ru",
    },
    {
        "json_path": BASE / "deprecated_kz_chunks.json",
        "source_type": "normative",
        "source_path": "normalized/deprecated_kz_chunks.json",
        "doc_key": "krk_1995_deprecated_kz",
        "title": "Қазақстан Республикасы Конституциясы 1995",
        "language_code": "kz",
        "section_code": "constitution",
        "status": "deprecated",
        "notes": "Production import of deprecated_kz",
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
                    heading = item.get("article_title") or item.get("section_title") or item.get("id")
                    meta = {
                        "layer": item.get("layer"),
                        "document": item.get("document"),
                        "language": item.get("language"),
                        "article_number": item.get("article_number"),
                        "article_title": item.get("article_title"),
                        "section_number": item.get("section_number"),
                        "section_title": item.get("section_title"),
                        "effective_date": item.get("effective_date"),
                        "deprecated_date": item.get("deprecated_date"),
                        "deprecation_note": item.get("deprecation_note"),
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
                            seq,
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
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    main()
