# core/database.py — память проекта
# Здесь храним ID тендеров которые уже видели, чтобы не дублировать

import sqlite3
import os

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
    from datetime import datetime

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