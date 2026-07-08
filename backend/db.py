"""Thin sqlite3 data-access layer.

Provides a small, safe query API. All queries are parameterized. Rows come back
as dicts so handlers can serialize them directly to JSON.
"""
import sqlite3
import threading
from contextlib import contextmanager

import config

_local = threading.local()


def _connect():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_conn():
    """One connection per thread (the server is threaded)."""
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = _connect()
        _local.conn = conn
    return conn


def init_db():
    """Create tables from schema.sql if they don't exist."""
    with open(config.SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = f.read()
    conn = get_conn()
    conn.executescript(schema)
    conn.commit()


def query(sql, params=()):
    cur = get_conn().execute(sql, params)
    rows = cur.fetchall()
    return [dict(r) for r in rows]


def query_one(sql, params=()):
    cur = get_conn().execute(sql, params)
    row = cur.fetchone()
    return dict(row) if row else None


def execute(sql, params=()):
    """Run an INSERT/UPDATE/DELETE, commit, and return lastrowid."""
    conn = get_conn()
    cur = conn.execute(sql, params)
    conn.commit()
    return cur.lastrowid


@contextmanager
def transaction():
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
