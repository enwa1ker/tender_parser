# core/database.py — память проекта
# Здесь храним ID тендеров которые уже видели, чтобы не дублировать

import sqlite3
import os
from datetime import datetime, date

# Путь к файлу базы данных — создастся автоматически рядом с этим файлом
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "seen_tenders.db")


def get_connection():
    """Открывает соединение с базой данных"""
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

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
            added_at    TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kv_store (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    # Добавляем столбцы если их нет (для старой базы)
    try:
        cursor.execute("ALTER TABLE seen_tenders ADD COLUMN title TEXT DEFAULT ''")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE seen_tenders ADD COLUMN url TEXT DEFAULT ''")
    except Exception:
        pass

    conn.commit()
    conn.close()
    print("База данных готова")


def is_seen(tender_id: str) -> bool:
    """
    Проверяет — видели ли мы уже этот тендер?
    Возвращает True если да, False если нет.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT 1 FROM seen_tenders WHERE tender_id = ?",
        (tender_id,)
    )
    result = cursor.fetchone()  # None если не найден, (1,) если найден

    conn.close()
    return result is not None  # превращаем в True/False


def mark_seen(tender_id: str, source: str, title: str = "", url: str = ""):
    """Запоминает тендер"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT OR IGNORE INTO seen_tenders (tender_id, source, added_at, title, url) VALUES (?, ?, ?, ?, ?)",
        (tender_id, source, datetime.now().strftime("%d.%m.%Y %H:%M"), title, url)
    )

    conn.commit()
    conn.close()


def get_stats() -> dict:
    """Возвращает статистику — сколько тендеров видели с каждого сайта"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT source, COUNT(*) 
        FROM seen_tenders 
        GROUP BY source
    """)
    rows = cursor.fetchall()

    conn.close()
    return {source: count for source, count in rows}

def get_last_tenders(limit: int = 10) -> list:
    """Возвращает последние N найденных тендеров"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT tender_id, source, added_at, title, url
        FROM seen_tenders
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id":       row[0],
            "source":   row[1],
            "found_at": row[2],
            "title":    row[3] if row[3] else "Без названия",
            "url":      row[4] if row[4] else "#",
        }
        for row in rows
    ]


def subscribe(chat_id: str) -> bool:
    """Добавляет чат в подписчики. Возвращает True если добавили (или уже был)."""
    chat_id = str(chat_id).strip()
    if not chat_id:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO subscribers (chat_id, added_at) VALUES (?, ?)",
        (chat_id, datetime.now().strftime("%d.%m.%Y %H:%M")),
    )
    conn.commit()
    conn.close()
    return True


def unsubscribe(chat_id: str) -> bool:
    """Удаляет чат из подписчиков. Возвращает True если удалили."""
    chat_id = str(chat_id).strip()
    if not chat_id:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM subscribers WHERE chat_id = ?", (chat_id,))
    changed = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return changed


def get_subscribers() -> list[str]:
    """Список chat_id подписчиков."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id FROM subscribers ORDER BY added_at ASC")
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]


def kv_get(key: str, default: str | None = None) -> str | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM kv_store WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else default


def kv_set(key: str, value: str) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO kv_store(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()
    conn.close()


def count_tenders_for_date(day: date) -> int:
    """Считает, сколько тендеров добавили в seen_tenders за дату (локально по added_at)."""
    day_str = day.strftime("%d.%m.%Y")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM seen_tenders WHERE added_at LIKE ?", (f"{day_str}%",))
    count = cursor.fetchone()[0]
    conn.close()
    return int(count)