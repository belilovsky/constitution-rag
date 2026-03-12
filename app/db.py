import os

import psycopg2
from psycopg2.extras import RealDictCursor


def get_db_config():
    return {
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("DB_PORT", "55432")),
        "dbname": os.getenv("DB_NAME", "constitution_rag"),
        "user": os.getenv("DB_USER", "constitution_rag"),
        "password": os.getenv("DB_PASSWORD", "ConstitutionRag_2026_Strong_Pass_Change_This"),
    }


def get_conn():
    return psycopg2.connect(**get_db_config())


def fetch_all(sql, params=None):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()
