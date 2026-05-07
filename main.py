# main.py — точка входа
# Поддерживает два режима:
#   SINGLE_RUN_MODE=true  → запустился, отработал, вышел (для GitHub Actions)
#   по умолчанию          → while True + schedule (для VPS / локальной машины)

import schedule
import time
import requests
import os
from datetime import datetime, timedelta, date
import sys

from config import CHECK_INTERVAL_HOURS, HEALTHCHECK_URL, REQUEST_TIMEOUT
from parsers.tenders_kg import get_tenders as get_tenders_kg
from parsers.gov_kg import get_tenders as get_gov_kg
from parsers.okmot_kg import get_tenders as get_okmot_kg
from parsers.kumtor_kg import get_tenders as get_kumtor_kg
from core.filter import is_relevant
from core.database import init_db, is_seen, mark_seen, kv_set, kv_get, count_tenders_for_date
from integrations.sheets import init_sheets, add_tender
from integrations.telegram_bot import notify_tender, notify_error, handle_commands, broadcast

SINGLE_RUN_MODE = os.getenv("SINGLE_RUN_MODE", "false").lower() == "true"


def fetch_with_retry(parser_func, source_name, pages=2, retries=3, delay=30):
    """Запускает парсер с повторными попытками (до 3х) при ошибке."""
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            tenders = parser_func(pages=pages)
            if attempt > 1:
                print(f"[main] ✅ {source_name}: успех с попытки {attempt}")
            return tenders
        except Exception as e:
            last_error = e
            print(f"[main] ⚠️  {source_name}: попытка {attempt}/{retries} — {e}")
            if attempt < retries:
                time.sleep(delay)

    error_msg = f"Парсер {source_name} упал {retries} раз подряд: {last_error}"
    print(f"[main] ❌ {error_msg}")
    notify_error(error_msg)
    return []


def ping_healthcheck(status: str = ""):
    """Пингует healthchecks.io. Если URL не задан — молча пропускает."""
    if not HEALTHCHECK_URL:
        return
    try:
        url = f"{HEALTHCHECK_URL}/{status}" if status else HEALTHCHECK_URL
        requests.get(url, timeout=5)
    except Exception:
        pass


def run_parser():
    kv_set("parser:last_run_started", datetime.now().isoformat(timespec="seconds"))
    ping_healthcheck("start")

    print(f"\n{'=' * 50}")
    print(f"Запуск: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    print(f"{'=' * 50}")

    parsers = [
        ("tenders.kg",       get_tenders_kg),
        ("zakupki.gov.kg",   get_gov_kg),
        ("zakupki.okmot.kg", get_okmot_kg),
        ("kumtor.kg",        get_kumtor_kg),
    ]

    all_tenders = []
    for source_name, parser_func in parsers:
        tenders = fetch_with_retry(parser_func, source_name, pages=2)
        all_tenders.extend(tenders)

    print(f"\n[main] Всего собрано: {len(all_tenders)}")

    new_count = 0
    for tender in all_tenders:
        if is_seen(tender["id"]):
            continue
        if not is_relevant(tender["title"]):
            mark_seen(tender["id"], tender["source"],
                      title=tender.get("title", ""), url=tender.get("url", ""),
                      is_relevant=False)
            continue

        print(f"[main] ✅ {tender['title'][:70]}")
        try:
            add_tender(tender)
            notify_tender(tender)
            mark_seen(tender["id"], tender["source"],
                      title=tender.get("title", ""), url=tender.get("url", ""),
                      is_relevant=True)
            new_count += 1
            time.sleep(1)
        except Exception as e:
            print(f"[main] ❌ Ошибка сохранения: {e}")

    print(f"\n[main] Новых релевантных: {new_count}")
    kv_set("parser:last_run_finished", datetime.now().isoformat(timespec="seconds"))
    kv_set("parser:last_new_count", str(new_count))
    ping_healthcheck()  # success ping


def check_parser_health():
    """
    Проверяет не завис ли парсер. Алертит если > 6 ч без финиша.
    Вызывается ТОЛЬКО через schedule — не из while-loop напрямую.
    """
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
            if datetime.now() - datetime.fromisoformat(last_alert) <= timedelta(hours=6):
                return
        except Exception:
            pass

    hours = int((datetime.now() - last_dt).total_seconds() // 3600)
    notify_error(
        f"⚠️ Парсер не запускался уже {hours} ч.\n"
        f"Последний раз: {last_dt.strftime('%d.%m.%Y %H:%M')}"
    )
    kv_set("parser:health_last_alert", datetime.now().isoformat(timespec="seconds"))
    ping_healthcheck("fail")


def daily_summary():
    today = date.today()
    if kv_get("summary:last_date") == today.isoformat():
        return
    cnt = count_tenders_for_date(today)
    broadcast(f"🗓 <b>Сводка за сегодня</b>\nНайдено тендеров: <b>{cnt}</b>")
    kv_set("summary:last_date", today.isoformat())


def main():
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print("=" * 50)
    print("  Мониторинг тендеров запущен!")
    print(f"  {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    if SINGLE_RUN_MODE:
        print("  Режим: SINGLE RUN (GitHub Actions)")
    else:
        print("  Режим: CONTINUOUS (VPS / локально)")
    print("=" * 50)

    init_db()
    init_sheets()
    run_parser()

    # В GitHub Actions — один прогон и выходим
    if SINGLE_RUN_MODE:
        print("\n✅ Одиночный запуск завершён.")
        return

    # На VPS — расписание и бесконечный цикл
    schedule.every().day.at("08:00").do(run_parser)
    schedule.every().day.at("11:00").do(run_parser)
    schedule.every().day.at("14:00").do(run_parser)
    schedule.every().day.at("17:00").do(run_parser)
    schedule.every().day.at("02:00").do(run_parser)
    schedule.every(10).minutes.do(check_parser_health)
    schedule.every().day.at("09:00").do(daily_summary)

    print("\n⏳ Расписание: 02:00 / 08:00 / 11:00 / 14:00 / 17:00 Бишкек\n")
    while True:
        schedule.run_pending()
        handle_commands()
        time.sleep(5)


if __name__ == "__main__":
    main()
