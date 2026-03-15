# integrations/sheets.py — работа с Google Sheets

import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from config import GOOGLE_SHEET_ID, GOOGLE_CREDENTIALS, SHEET_COLUMNS, SHEET_ALL_TAB, SOURCES

# Права доступа которые запрашиваем у Google
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_client():
    """Подключается к Google Sheets"""
    import json, base64, os

    credentials_b64 = os.getenv("GOOGLE_CREDENTIALS_JSON")

    if credentials_b64:
        # Railway — декодируем из base64
        credentials_json = base64.b64decode(credentials_b64).decode("utf-8")
        info = json.loads(credentials_json)
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    else:
        # Локально — читаем из файла
        creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS, scopes=SCOPES)

    return gspread.authorize(creds)


def get_spreadsheet():
    """Открывает нашу таблицу по ID"""
    client = get_client()
    return client.open_by_key(GOOGLE_SHEET_ID)


def init_sheets():
    """
    Создаёт все нужные вкладки если их нет.
    Вызывается один раз при первом запуске.
    """
    spreadsheet = get_spreadsheet()
    existing_tabs = [ws.title for ws in spreadsheet.worksheets()]

    # Список всех нужных вкладок
    needed_tabs = [SHEET_ALL_TAB] + [s["sheet_tab"] for s in SOURCES.values()]

    for tab_name in needed_tabs:
        if tab_name not in existing_tabs:
            worksheet = spreadsheet.add_worksheet(title=tab_name, rows=1000, cols=20)
            print(f"[Sheets] Создана вкладка: {tab_name}")
        else:
            worksheet = spreadsheet.worksheet(tab_name)
            print(f"[Sheets] Вкладка уже есть: {tab_name}")

        # Добавляем заголовки если вкладка пустая
        current_data = worksheet.get_all_values()
        if not current_data:
            worksheet.append_row(SHEET_COLUMNS, value_input_option="RAW")
            print(f"[Sheets] Заголовки добавлены в: {tab_name}")

    print("[Sheets] Инициализация завершена")


def add_tender(tender: dict):
    """
    Добавляет один тендер в таблицу:
    - в сводную вкладку "Все тендеры"
    - в вкладку конкретного источника
    """
    spreadsheet = get_spreadsheet()

    # Формируем строку данных в порядке SHEET_COLUMNS
    row = [
        tender.get("found_at", ""),
        tender.get("title", ""),
        tender.get("customer", ""),
        tender.get("amount", ""),
        tender.get("deadline", ""),
        tender.get("source", ""),
        tender.get("url", ""),
        "🟢 Новый",  # статус по умолчанию
    ]

    # Добавляем в сводную вкладку
    all_tab = spreadsheet.worksheet(SHEET_ALL_TAB)
    all_tab.append_row(row, value_input_option="RAW")

    # Находим вкладку конкретного источника
    source_tab_name = None
    for source in SOURCES.values():
        if source["name"] == tender.get("source"):
            source_tab_name = source["sheet_tab"]
            break

    if source_tab_name:
        source_tab = spreadsheet.worksheet(source_tab_name)
        source_tab.append_row(row, value_input_option="RAW")

    print(f"[Sheets] Добавлен тендер: {tender.get('title', '')[:50]}")