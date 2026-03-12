import psycopg2
from psycopg2.extras import RealDictCursor

DB = {
    "host": "127.0.0.1",
    "port": 55432,
    "dbname": "constitution_rag",
    "user": "constitution_rag",
    "password": "ConstitutionRag_2026_Strong_Pass_Change_This",
}


def get_conn():
    return psycopg2.connect(**DB)


def fetch_all(sql, params=None):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()
