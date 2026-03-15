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
    """
    Создаёт таблицу если её ещё нет.
    Вызывается один раз при запуске программы.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS seen_tenders (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            tender_id   TEXT NOT NULL UNIQUE,  -- уникальный ID тендера с сайта
            source      TEXT NOT NULL,          -- откуда (gov_kg, tenders_kg ...)
            added_at    TEXT NOT NULL           -- когда мы его нашли
        )
    """)

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


def mark_seen(tender_id: str, source: str):
    """
    Запоминает тендер — помечает его как просмотренный.
    После этого is_seen() для него вернёт True.
    """
    from datetime import datetime

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT OR IGNORE INTO seen_tenders (tender_id, source, added_at) VALUES (?, ?, ?)",
        (tender_id, source, datetime.now().strftime("%d.%m.%Y %H:%M"))
    )
    # INSERT OR IGNORE — если такой ID уже есть, просто пропускает без ошибки

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
