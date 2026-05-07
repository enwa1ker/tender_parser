#!/usr/bin/env python3
"""
Диагностика всей системы: бот, БД, подписчики, фильтр.
Запуск: python3 check_bot.py
"""
import os, sys, sqlite3, glob, requests
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv(dotenv_path='.env')

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_IDS = os.getenv("TELEGRAM_CHAT_IDS", "")
ADMIN_IDS = os.getenv("TELEGRAM_ADMIN_IDS", "")
SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")

SEP = "=" * 55

# ── 1. Переменные окружения ───────────────────────────────
print(f"\n{SEP}")
print("  1. Переменные окружения")
print(SEP)
print(f"  TELEGRAM_BOT_TOKEN : {'✅ ' + TOKEN[:20] + '...' if TOKEN else '❌ НЕТ'}")
print(f"  TELEGRAM_CHAT_IDS  : {'✅ ' + CHAT_IDS if CHAT_IDS else '❌ ПУСТО'}")
print(f"  TELEGRAM_ADMIN_IDS : {'✅ ' + ADMIN_IDS if ADMIN_IDS else '⚠️  не задан'}")
print(f"  GOOGLE_SHEET_ID    : {'✅ ' + SHEET_ID[:20] if SHEET_ID else '❌ НЕТ'}")

# ── 2. Telegram бот ───────────────────────────────────────
print(f"\n{SEP}")
print("  2. Telegram бот")
print(SEP)
if TOKEN:
    try:
        r = requests.get(f"https://api.telegram.org/bot{TOKEN}/getMe", timeout=10)
        if r.status_code == 200:
            bot = r.json()["result"]
            print(f"  ✅ Бот: @{bot['username']} ({bot['first_name']})")
        else:
            print(f"  ❌ Ошибка getMe: {r.status_code} {r.text}")
    except Exception as e:
        print(f"  ❌ Нет соединения: {e}")
else:
    print("  ❌ Токен не задан")

# ── 3. Тест отправки сообщения ────────────────────────────
print(f"\n{SEP}")
print("  3. Тест отправки сообщения")
print(SEP)
if TOKEN and CHAT_IDS:
    for cid in CHAT_IDS.split(","):
        cid = cid.strip()
        try:
            r = requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                json={"chat_id": cid, "text": "✅ Диагностика: бот работает нормально!", "parse_mode": "HTML"},
                timeout=10
            )
            if r.status_code == 200:
                print(f"  ✅ chat_id {cid} — сообщение отправлено")
            else:
                print(f"  ❌ chat_id {cid} — {r.status_code}: {r.json().get('description','')}")
        except Exception as e:
            print(f"  ❌ chat_id {cid} — {e}")
else:
    print("  ❌ Токен или CHAT_IDS не заданы")

# ── 4. База данных ────────────────────────────────────────
print(f"\n{SEP}")
print("  4. База данных")
print(SEP)
dbs = glob.glob("*.db") + glob.glob("**/*.db", recursive=True)
if not dbs:
    print("  ⚠️  БД не найдена (создастся при первом запуске)")
else:
    for db_path in dbs:
        print(f"  📁 {db_path}")
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r[0] for r in cur.fetchall()]

            # Тендеры
            if "seen_tenders" in tables:
                cur.execute("SELECT COUNT(*) FROM seen_tenders")
                total = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM seen_tenders WHERE is_relevant=1")
                relevant = cur.fetchone()[0]
                print(f"     seen_tenders: {total} всего, {relevant} релевантных")

            # Подписчики
            if "subscribers" in tables:
                cur.execute("SELECT * FROM subscribers")
                subs = cur.fetchall()
                if subs:
                    print(f"     subscribers: {len(subs)} подписчиков")
                    for s in subs:
                        print(f"       • {s}")
                else:
                    print(f"     ⚠️  subscribers: пусто — нужно написать /start боту")

            conn.close()
        except Exception as e:
            print(f"     ❌ Ошибка: {e}")

# ── 5. Тест фильтра ───────────────────────────────────────
print(f"\n{SEP}")
print("  5. Тест фильтра ключевых слов")
print(SEP)
try:
    from core.filter import is_relevant
    tests = [
        ("ЗАПРОС КОТИРОВОК НА ПОСТАВКУ ЭЛЕКТРОТЕХНИЧЕСКИХ ТОВАРОВ", True),
        ("Строительство ЛЭП 110 кВ", True),
        ("Монтаж КТП-630 кВА", True),
        ("ПОСТАВКА КАБЕЛЬНОЙ ПРОДУКЦИИ", True),
        ("Проектирование подстанции 35/10 кВ", True),
        ("Поставка продуктов питания", False),
        ("Ремонт автодороги", False),
    ]
    ok = sum(1 for t, exp in tests if is_relevant(t) == exp)
    print(f"  {'✅' if ok == len(tests) else '⚠️ '} Фильтр: {ok}/{len(tests)} тестов прошло")
    for title, expected in tests:
        result = is_relevant(title)
        icon = "✅" if result == expected else "❌"
        print(f"     {icon} [{'+' if result else '-'}] {title[:50]}")
except Exception as e:
    print(f"  ❌ Ошибка импорта фильтра: {e}")

print(f"\n{SEP}")
print("  Диагностика завершена")
print(SEP + "\n")
