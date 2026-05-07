import os
from dotenv import load_dotenv

load_dotenv()

# ── Telegram ─────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_IDS  = [x.strip() for x in os.getenv("TELEGRAM_CHAT_IDS", "").split(",") if x.strip()]
TELEGRAM_ADMIN_IDS = [x.strip() for x in os.getenv("TELEGRAM_ADMIN_IDS", "").split(",") if x.strip()]

# ── Google Sheets ─────────────────────────────────────────────────────────────
GOOGLE_SHEET_ID   = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")

# ── Расписание ────────────────────────────────────────────────────────────────
# Используется только как fallback — основное расписание задаётся в main.py
CHECK_INTERVAL_HOURS = int(os.getenv("CHECK_INTERVAL_HOURS", "3"))

# ── HTTP настройки ────────────────────────────────────────────────────────────
# Таймаут на все requests.get() во всех парсерах.
# Добавь REQUEST_TIMEOUT во все парсеры: requests.get(url, timeout=REQUEST_TIMEOUT)
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "15"))

# ── Мониторинг (healthchecks.io) ──────────────────────────────────────────────
# 1. Зарегистрируйся на https://healthchecks.io (бесплатно)
# 2. Создай новый check, скопируй URL вида https://hc-ping.com/xxxxxxxx-xxxx-...
# 3. Добавь в .env: HEALTHCHECK_URL=https://hc-ping.com/твой-uuid
# Если не задан — мониторинг через healthchecks молча отключается
HEALTHCHECK_URL = os.getenv("HEALTHCHECK_URL", "")

# ── Ключевые слова фильтрации ─────────────────────────────────────────────────
KEYWORDS = [
    "электротехн",
    "электроустановк",
    "электродвигател",
    "электромонтаж",
    "электропроводк",
    "электрощит",
    "электроснабжен",
    "электротовар",
    "электрооборудован",
    "монтаж электр",
    "прокладк кабел",
    "кабельн",
    "электрик",
    "трансформатор",
    "подстанци",
    "генератор",
    "заземлен",
    "освещен",
    "электролини",
    "электросеть",
    "электрическая",
]

# ── Google Sheets — названия вкладок и столбцы ────────────────────────────────
SHEET_ALL_TAB = "Все тендеры"

SHEET_COLUMNS = [
    "Дата добавления",
    "Название тендера",
    "Заказчик",
    "Сумма (сом)",
    "Дедлайн",
    "Дней до дедлайна",
    "Источник",
    "Ссылка",
    "Статус",
]

# ── Источники данных ──────────────────────────────────────────────────────────
SOURCES = {
    "gov_kg": {
        "name": "zakupki.gov.kg",
        "url": "http://zakupki.gov.kg/popp/",
        "sheet_tab": "zakupki.gov.kg",
    },
    "okmot_kg": {
        "name": "zakupki.okmot.kg",
        "url": "https://zakupki.okmot.kg/popp/",
        "sheet_tab": "zakupki.okmot.kg",
    },
    "tenders_kg": {
        "name": "tenders.kg",
        "url": "https://www.tenders.kg/Announcements_list.php?f=all",
        "sheet_tab": "tenders.kg",
    },
    "kumtor_kg": {
        "name": "kumtor.kg",
        "url": "https://www.kumtor.kg/ru/category/procurement/",
        "sheet_tab": "kumtor.kg",
    },
}
