import os

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is not set. Check your .env file.")
    return value


def get_db_config():
    return {
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("DB_PORT", "55432")),
        "dbname": os.getenv("DB_NAME", "constitution_rag"),
        "user": os.getenv("DB_USER", "constitution_rag"),
        "password": _require_env("DB_PASSWORD"),
    }


# ── Connection pool (min 1, max 5 connections) ─────────────────────
_pool: SimpleConnectionPool | None = None


def _get_pool() -> SimpleConnectionPool:
    global _pool
    if _pool is None or _pool.closed:
        _pool = SimpleConnectionPool(1, 5, **get_db_config())
    return _pool


def get_conn():
    """Get a connection from the pool."""
    return _get_pool().getconn()


def put_conn(conn):
    """Return a connection to the pool."""
    try:
        _get_pool().putconn(conn)
    except Exception:
        pass


def fetch_all(sql, params=None):
    pool = _get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()
    finally:
        pool.putconn(conn)
