#!/usr/bin/env python3
"""
Диагностический скрипт — запускается в начале каждого Actions job.
Проверяет доступность всех сайтов и печатает результат.
"""
import requests
import urllib3
import sys

urllib3.disable_warnings()

SITES = [
    ("kumtor.kg",          "https://www.kumtor.kg/ru/category/procurement/"),
    ("tenders.kg",         "https://www.tenders.kg/Announcements_list.php?f=all"),
    ("zakupki.okmot.kg",   "https://zakupki.okmot.kg/popp/view/order/list.xhtml"),
    ("goszakupki.okmot.kg","https://goszakupki.okmot.kg/public/home"),
    ("osoo.kg (резерв)",   "https://www.osoo.kg/tender/"),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9",
}

print("\n" + "="*55)
print("  Проверка доступности сайтов")
print("="*55)

all_ok = True
for name, url in SITES:
    try:
        r = requests.get(url, headers=HEADERS, timeout=10, verify=False)
        status = "✅" if r.status_code == 200 else "⚠️ "
        if r.status_code != 200:
            all_ok = False
        print(f"  {status} {name:<28} HTTP {r.status_code}  ({len(r.text):,} байт)")
    except Exception as e:
        all_ok = False
        print(f"  ❌ {name:<28} {str(e)[:40]}")

print("="*55 + "\n")

if not all_ok:
    print("⚠️  Некоторые сайты недоступны — парсер продолжит работу с доступными.")

sys.exit(0)  # Не падаем — просто информация
