import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# Секретные данные — только из .env, никогда не хардкодим в коде
TELEGRAM_ADMIN_IDS = os.getenv("TELEGRAM_ADMIN_IDS", "").split(",")
TELEGRAM_BOT_TOKEN    = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_IDS     = os.getenv("TELEGRAM_CHAT_IDS", "").split(",")
TELEGRAM_ADMIN_IDS    = [x.strip() for x in os.getenv("TELEGRAM_ADMIN_IDS", "").split(",") if x.strip()]
GOOGLE_SHEET_ID       = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_CREDENTIALS    = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
CHECK_INTERVAL_HOURS  = int(os.getenv("CHECK_INTERVAL_HOURS", "3"))

KEYWORDS = [
    # Основные (электрика)
    "электромонтаж",
    "электропроводк",
    "электрощит",
    "электроснабжен",
    "электротовар",       # как раз поймали выше
    "электрооборудован",
    # Работы
    "монтаж электр",      # монтаж электрики/электрооборудования
    "прокладк кабел",     # прокладка кабеля/кабелей
    "кабельн",            # кабельные линии, кабельных сетей
    "электрик",           # электрика, электрики
    # Оборудование
    "трансформатор",
    "подстанци",
    "генератор",          # дизельгенератор, генераторная
    "заземлен",
    "освещен",            # освещение (уличное, внутреннее)
    "электролини",
]


# ── Названия вкладок в Google Sheets ────────────────────────────────────────
SHEET_ALL_TAB = "Все тендеры"

# ── Столбцы таблицы (порядок важен!) ────────────────────────────────────────
SHEET_COLUMNS = [
    "Дата добавления",
    "Название тендера",
    "Заказчик",
    "Сумма (сом)",
    "Дедлайн",
    "Источник",
    "Ссылка",
    "Статус",
]


# ── Источники данных ─────────────────────────────────────────────────────────
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