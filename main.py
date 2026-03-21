# main.py — точка входа, собирает всё вместе

import schedule
import time
from datetime import datetime
import sys
from datetime import timedelta, date

from config import CHECK_INTERVAL_HOURS

from parsers.tenders_kg import get_tenders as get_tenders_kg
from parsers.gov_kg import get_tenders as get_gov_kg
from parsers.okmot_kg import get_tenders as get_okmot_kg
from parsers.kumtor_kg import get_tenders as get_kumtor_kg

from core.filter import is_relevant
from core.database import init_db, is_seen, mark_seen, kv_set, kv_get, count_tenders_for_date

from integrations.sheets import init_sheets, add_tender
from integrations.telegram_bot import notify_tender, notify_error, handle_commands, broadcast


def run_parser():
    kv_set("parser:last_run_started", datetime.now().isoformat(timespec="seconds"))
    print(f"\n{'='*50}")
    print(f"Запуск парсера: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    print(f"{'='*50}")

    all_tenders = []
    parsers = [
        ("tenders.kg",       get_tenders_kg),
        ("zakupki.gov.kg",   get_gov_kg),
        ("zakupki.okmot.kg", get_okmot_kg),
        ("kumtor.kg",        get_kumtor_kg),
    ]

    for source_name, parser_func in parsers:
        try:
            tenders = parser_func(pages=2)
            all_tenders.extend(tenders)
        except Exception as e:
            error_msg = f"Парсер {source_name} упал: {e}"
            print(f"[main] [ERR] {error_msg}")
            notify_error(error_msg)

    print(f"\n[main] Всего собрано тендеров: {len(all_tenders)}")

    new_count = 0

    for tender in all_tenders:
        if is_seen(tender["id"]):
            continue

        if not is_relevant(tender["title"]):
            mark_seen(
                tender["id"], tender["source"],
                title=tender.get("title", ""),
                url=tender.get("url", ""),
                is_relevant=False
            )
            continue

        print(f"[main] [OK] Новый тендер: {tender['title'][:60]}")

        try:
            add_tender(tender)
            notify_tender(tender)
            mark_seen(
                tender["id"], tender["source"],
                title=tender.get("title", ""),
                url=tender.get("url", ""),
                is_relevant=True
            )
            new_count += 1
            time.sleep(1)
        except Exception as e:
            print(f"[main] ❌ Ошибка сохранения: {e}")

    print(f"\n[main] Новых релевантных тендеров: {new_count}")
    print(f"[main] Следующая проверка через {CHECK_INTERVAL_HOURS} часа")
    kv_set("parser:last_run_finished", datetime.now().isoformat(timespec="seconds"))


def check_parser_health():
    last_finished = kv_get("parser:last_run_finished")
    if not last_finished:
        return
    try:
        last_dt = datetime.fromisoformat(last_finished)
    except Exception:
        return

    if datetime.now() - last_dt <= timedelta(hours=6):
        return

    last_alert = kv_get("parser:health_last_alert")
    if last_alert:
        try:
            last_alert_dt = datetime.fromisoformat(last_alert)
            if datetime.now() - last_alert_dt <= timedelta(hours=6):
                return
        except Exception:
            pass

    hours = int((datetime.now() - last_dt).total_seconds() // 3600)
    notify_error(f"Парсер не запускался уже {hours} ч. (последний раз: {last_dt.strftime('%d.%m.%Y %H:%M')})")
    kv_set("parser:health_last_alert", datetime.now().isoformat(timespec="seconds"))


def daily_summary():
    today = date.today()
    key = "summary:last_date"
    if kv_get(key) == today.isoformat():
        return
    cnt = count_tenders_for_date(today)
    broadcast(f"🗓 <b>Сводка за сегодня</b>\n\nНайдено тендеров: <b>{cnt}</b>")
    kv_set(key, today.isoformat())


def main():
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print("Мониторинг тендеров запущен!")
    print(f"Интервал проверки: каждые {CHECK_INTERVAL_HOURS} часа")

    init_db()
    init_sheets()
    run_parser()

    schedule.every(CHECK_INTERVAL_HOURS).hours.do(run_parser)
    schedule.every(10).minutes.do(check_parser_health)
    schedule.every().day.at("09:00").do(daily_summary)

    print("\n⏳ Ожидаю следующей проверки... (Ctrl+C для остановки)")
    while True:
        schedule.run_pending()
        handle_commands()
        check_parser_health()
        time.sleep(5)


if __name__ == "__main__":
    main()