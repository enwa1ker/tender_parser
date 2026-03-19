# core/database.py — память проекта

import os
from datetime import datetime, date

# Определяем какую базу использовать
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Railway — используем PostgreSQL
    import psycopg2
    import psycopg2.extras

    def get_connection():
        return psycopg2.connect(DATABASE_URL)
else:
    # Локально — используем SQLite
    import sqlite3
    DB_PATH = os.path.join(os.path.dirname(__file__), "..", "seen_tenders.db")

    def get_connection():
        return sqlite3.connect(DB_PATH)


def _is_pg():
    return bool(DATABASE_URL)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    if _is_pg():
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS seen_tenders (
                id          SERIAL PRIMARY KEY,
                tender_id   TEXT NOT NULL UNIQUE,
                source      TEXT NOT NULL,
                added_at    TEXT NOT NULL,
                title       TEXT DEFAULT '',
                url         TEXT DEFAULT ''
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscribers (
                chat_id     TEXT PRIMARY KEY,
                added_at    TEXT NOT NULL,
                username    TEXT DEFAULT ''
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kv_store (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
    else:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS seen_tenders (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                tender_id   TEXT NOT NULL UNIQUE,
                source      TEXT NOT NULL,
                added_at    TEXT NOT NULL,
                title       TEXT DEFAULT '',
                url         TEXT DEFAULT ''
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscribers (
                chat_id     TEXT PRIMARY KEY,
                added_at    TEXT NOT NULL,
                username    TEXT DEFAULT ''
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kv_store (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        # Миграция для старой базы
        for col in ["title", "url"]:
            try:
                cursor.execute(f"ALTER TABLE seen_tenders ADD COLUMN {col} TEXT DEFAULT ''")
            except Exception:
                pass
        try:
            cursor.execute("ALTER TABLE subscribers ADD COLUMN username TEXT DEFAULT ''")
        except Exception:
            pass

    conn.commit()
    conn.close()
    print("База данных готова")


def is_seen(tender_id: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM seen_tenders WHERE tender_id = %s" if _is_pg()
                   else "SELECT 1 FROM seen_tenders WHERE tender_id = ?", (tender_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def mark_seen(tender_id: str, source: str, title: str = "", url: str = ""):
    conn = get_connection()
    cursor = conn.cursor()
    if _is_pg():
        cursor.execute(
            "INSERT INTO seen_tenders (tender_id, source, added_at, title, url) "
            "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (tender_id) DO NOTHING",
            (tender_id, source, datetime.now().strftime("%d.%m.%Y %H:%M"), title, url)
        )
    else:
        cursor.execute(
            "INSERT OR IGNORE INTO seen_tenders (tender_id, source, added_at, title, url) "
            "VALUES (?, ?, ?, ?, ?)",
            (tender_id, source, datetime.now().strftime("%d.%m.%Y %H:%M"), title, url)
        )
    conn.commit()
    conn.close()


def get_stats() -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT source, COUNT(*) FROM seen_tenders GROUP BY source")
    rows = cursor.fetchall()
    conn.close()
    return {source: count for source, count in rows}


def get_last_tenders(limit: int = 10) -> list:
    conn = get_connection()
    cursor = conn.cursor()
    q = "SELECT tender_id, source, added_at, title, url FROM seen_tenders ORDER BY id DESC LIMIT %s" \
        if _is_pg() else \
        "SELECT tender_id, source, added_at, title, url FROM seen_tenders ORDER BY id DESC LIMIT ?"
    cursor.execute(q, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [
        {"id": r[0], "source": r[1], "found_at": r[2],
         "title": r[3] or "Без названия", "url": r[4] or "#"}
        for r in rows
    ]


def subscribe(chat_id: str, username: str = "") -> bool:
    chat_id = str(chat_id).strip()
    if not chat_id:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    if _is_pg():
        cursor.execute(
            "INSERT INTO subscribers (chat_id, added_at, username) VALUES (%s, %s, %s) "
            "ON CONFLICT (chat_id) DO UPDATE SET username = EXCLUDED.username",
            (chat_id, datetime.now().strftime("%d.%m.%Y %H:%M"), username)
        )
    else:
        cursor.execute(
            "INSERT INTO subscribers (chat_id, added_at, username) VALUES (?, ?, ?) "
            "ON CONFLICT(chat_id) DO UPDATE SET username = excluded.username",
            (chat_id, datetime.now().strftime("%d.%m.%Y %H:%M"), username)
        )
    conn.commit()
    conn.close()
    return True


def unsubscribe(chat_id: str) -> bool:
    chat_id = str(chat_id).strip()
    if not chat_id:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM subscribers WHERE chat_id = %s" if _is_pg()
        else "DELETE FROM subscribers WHERE chat_id = ?",
        (chat_id,)
    )
    changed = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return changed


def get_subscribers() -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id, username, added_at FROM subscribers ORDER BY added_at ASC")
    rows = cursor.fetchall()
    conn.close()
    return [{"chat_id": r[0], "username": r[1] or "", "added_at": r[2]} for r in rows]


def kv_get(key: str, default=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT value FROM kv_store WHERE key = %s" if _is_pg()
        else "SELECT value FROM kv_store WHERE key = ?",
        (key,)
    )
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else default


def kv_set(key: str, value: str) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    if _is_pg():
        cursor.execute(
            "INSERT INTO kv_store(key, value) VALUES(%s, %s) "
            "ON CONFLICT(key) DO UPDATE SET value = EXCLUDED.value",
            (key, value)
        )
    else:
        cursor.execute(
            "INSERT INTO kv_store(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value)
        )
    conn.commit()
    conn.close()


def count_tenders_for_date(day: date) -> int:
    day_str = day.strftime("%d.%m.%Y")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM seen_tenders WHERE added_at LIKE %s" if _is_pg()
        else "SELECT COUNT(*) FROM seen_tenders WHERE added_at LIKE ?",
        (f"{day_str}%",)
    )
    count = cursor.fetchone()[0]
    conn.close()
    return int(count)