"""
db.py
-----
Database connection helper.
- If DATABASE_URL is set (Render/Supabase/Postgres), uses psycopg2 (PostgreSQL).
- Otherwise, falls back to SQLite for local development.

PostgreSQL uses %s placeholders; SQLite uses ?.
We normalise to %s throughout this module so app.py can use one syntax.
"""

import os
import sqlite3
from flask import g

DATABASE_URL = os.getenv("DATABASE_URL")  # Set on Render / Supabase
IS_POSTGRES = bool(DATABASE_URL)

# ── PostgreSQL ──────────────────────────────────────────────────────────────
if IS_POSTGRES:
    import psycopg2
    import psycopg2.extras  # for RealDictCursor

    def get_db():
        """Return a per-request PostgreSQL connection."""
        db = getattr(g, "_database", None)
        if db is None:
            db = g._database = psycopg2.connect(
                DATABASE_URL,
                cursor_factory=psycopg2.extras.RealDictCursor,
                sslmode="require",
            )
        return db

    def query_db(query, args=(), one=False, commit=False):
        """Execute a query and optionally fetch results."""
        conn = get_db()
        cur = conn.cursor()
        cur.execute(query, args)
        if commit:
            conn.commit()
            return None
        rv = cur.fetchone() if one else cur.fetchall()
        return rv

    def close_connection(exception):
        db = getattr(g, "_database", None)
        if db is not None:
            db.close()

    def init_db():
        """Create tables (idempotent) on PostgreSQL."""
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                cash_balance REAL DEFAULT 1000000.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS favorites (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                ticker TEXT NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, ticker)
            );

            CREATE TABLE IF NOT EXISTS search_history (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                ticker TEXT NOT NULL,
                searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS portfolio_transactions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                ticker TEXT NOT NULL,
                action TEXT NOT NULL,
                shares INTEGER NOT NULL,
                price REAL NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        print("✅ PostgreSQL tables initialised.")

    # Placeholder style for PostgreSQL
    PH = "%s"

# ── SQLite (local dev) ───────────────────────────────────────────────────────
else:
    _DB_PATH = os.path.join(os.path.dirname(__file__), "database", "db.sqlite3")

    class _Row(sqlite3.Row):
        """Thin wrapper so .keys() works like pg RealDictCursor."""
        pass

    def get_db():
        db = getattr(g, "_database", None)
        if db is None:
            os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
            db = g._database = sqlite3.connect(_DB_PATH)
            db.row_factory = sqlite3.Row
        return db

    def query_db(query, args=(), one=False, commit=False):
        # Translate %s → ? for SQLite
        query = query.replace("%s", "?")
        conn = get_db()
        cur = conn.execute(query, args)
        if commit:
            conn.commit()
            return None
        rv = cur.fetchone() if one else cur.fetchall()
        return rv

    def close_connection(exception):
        db = getattr(g, "_database", None)
        if db is not None:
            db.close()

    def init_db():
        os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
        conn = sqlite3.connect(_DB_PATH)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                cash_balance REAL DEFAULT 1000000.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(user_id, ticker)
            );
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS portfolio_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                action TEXT NOT NULL,
                shares INTEGER NOT NULL,
                price REAL NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)
        # migration guard
        try:
            conn.execute("ALTER TABLE users ADD COLUMN cash_balance REAL DEFAULT 1000000.0")
        except Exception:
            pass
        conn.commit()
        conn.close()
        print("✅ SQLite DB initialised.")

    PH = "?"
