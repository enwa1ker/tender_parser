# main.py — точка входа, собирает всё вместе

import schedule
import time
from datetime import datetime

from config import CHECK_INTERVAL_HOURS

from parsers.tenders_kg import get_tenders as get_tenders_kg
from parsers.gov_kg import get_tenders as get_gov_kg
from parsers.okmot_kg import get_tenders as get_okmot_kg
from parsers.kumtor_kg import get_tenders as get_kumtor_kg

from core.filter import is_relevant
from core.database import init_db, is_seen, mark_seen

from integrations.sheets import init_sheets, add_tender
from integrations.telegram_bot import notify_tender, notify_error, handle_commands


def run_parser():
    """
    Главная функция — запускает все парсеры,
    фильтрует тендеры и сохраняет новые.
    """
    print(f"\n{'='*50}")
    print(f"Запуск парсера: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    print(f"{'='*50}")

    # Собираем тендеры со всех источников
    all_tenders = []
    parsers = [
        ("tenders.kg",      get_tenders_kg),
        ("zakupki.gov.kg",  get_gov_kg),
        ("zakupki.okmot.kg",get_okmot_kg),
        ("kumtor.kg",       get_kumtor_kg),
    ]

    for source_name, parser_func in parsers:
        try:
            tenders = parser_func(pages=2)
            all_tenders.extend(tenders)
        except Exception as e:
            error_msg = f"Парсер {source_name} упал: {e}"
            print(f"[main] ❌ {error_msg}")
            notify_error(error_msg)

    print(f"\n[main] Всего собрано тендеров: {len(all_tenders)}")

    # Фильтруем и сохраняем новые
    new_count = 0

    for tender in all_tenders:
        # Пропускаем если уже видели
        if is_seen(tender["id"]):
            continue

        # Пропускаем если не по теме
        if not is_relevant(tender["title"]):
            mark_seen(tender["id"], tender["source"], title=tender.get("title", ""), url=tender.get("url", ""))  # запоминаем чтобы не проверять снова
            continue

        # Новый релевантный тендер!
        print(f"[main] ✅ Новый тендер: {tender['title'][:60]}")

        try:
            add_tender(tender)          # → Google Sheets
            notify_tender(tender)       # → Telegram
            mark_seen(tender["id"], tender["source"], title=tender.get("title", ""), url=tender.get("url", ""))  # → SQLite
            new_count += 1
            time.sleep(1)  # пауза между отправками
        except Exception as e:
            print(f"[main] ❌ Ошибка сохранения: {e}")

    print(f"\n[main] Новых релевантных тендеров: {new_count}")
    print(f"[main] Следующая проверка через {CHECK_INTERVAL_HOURS} часа")


def main():
    print("🚀 Мониторинг тендеров запущен!")
    print(f"Интервал проверки: каждые {CHECK_INTERVAL_HOURS} часа")

    # Инициализация при старте
    init_db()
    init_sheets()

    # Первый запуск сразу
    run_parser()

    # Затем по расписанию
    schedule.every(CHECK_INTERVAL_HOURS).hours.do(run_parser)

    print("\n⏳ Ожидаю следующей проверки... (Ctrl+C для остановки)")
    while True:
        schedule.run_pending()
        handle_commands()
        time.sleep(60)  # проверяем расписание каждую минуту


if __name__ == "__main__":
    main()

